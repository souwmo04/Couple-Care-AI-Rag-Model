"""Conversation storage.

* ``MemoryConversationStore`` — guest mode / persistence off. Conversations live only in
  process memory (needed to keep context within a session), expire after inactivity, and
  disappear when the backend stops. Nothing is written to disk.
* ``SQLiteConversationStore`` — used only when the user turns persistence on. Parameterized
  queries throughout. The database file lives in ``data/user/`` (git-ignored).

Access control: every conversation is bound to an owner key derived from the browser's
random client id (``X-Client-Id`` header). Conversation ids are 128-bit random values, and a
lookup must match both id *and* owner, so guessing an id is not enough to read a
conversation.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from app.core.schemas import (
    ConversationDetail,
    ConversationSummary,
    RelationshipStage,
    SafetyStatus,
    SourceCard,
    StoredMessage,
)

MAX_TITLE = 80


def new_id() -> str:
    return secrets.token_hex(16)


def owner_key(client_id: str) -> str:
    return hashlib.sha256(("couplecare:" + client_id).encode("utf-8")).hexdigest()


def make_title(message: str) -> str:
    text = " ".join(message.split())
    return text if len(text) <= MAX_TITLE else text[: MAX_TITLE - 1].rsplit(" ", 1)[0] + "…"


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass
class Conversation:
    id: str
    owner: str
    title: str
    created_at: datetime
    updated_at: datetime
    relationship_stage: RelationshipStage
    language: str
    safety_level: str = "none"
    messages: list[StoredMessage] = field(default_factory=list)
    message_count: int | None = None  # set when messages were not loaded

    def summary(self) -> ConversationSummary:
        return ConversationSummary(
            id=self.id, title=self.title, created_at=self.created_at, updated_at=self.updated_at,
            message_count=self.message_count if self.message_count is not None else len(self.messages), relationship_stage=self.relationship_stage, language=self.language,
        )

    def detail(self) -> ConversationDetail:
        return ConversationDetail(**self.summary().model_dump(), messages=self.messages)


class ConversationStore(Protocol):
    persistent: bool

    def create(self, owner: str, first_message: str, stage: RelationshipStage, language: str) -> Conversation: ...
    def get(self, owner: str, conversation_id: str) -> Conversation | None: ...
    def list(self, owner: str, query: str | None = None, limit: int = 50, offset: int = 0) -> tuple[list[Conversation], int]: ...
    def append(self, owner: str, conversation_id: str, message: StoredMessage, *, safety_level: str | None = None,
               stage: RelationshipStage | None = None, language: str | None = None) -> None: ...
    def remove_last_assistant(self, owner: str, conversation_id: str) -> None: ...
    def set_feedback(self, owner: str, conversation_id: str, message_id: str, rating: str) -> bool: ...
    def delete(self, owner: str, conversation_id: str) -> bool: ...
    def delete_all(self, owner: str) -> int: ...


class MemoryConversationStore:
    persistent = False

    def __init__(self, ttl_seconds: int = 6 * 3600, max_conversations: int = 200) -> None:
        self._items: dict[str, Conversation] = {}
        self._touched: dict[str, float] = {}
        self._feedback: dict[str, str] = {}
        self._lock = threading.Lock()
        self.ttl = ttl_seconds
        self.max = max_conversations

    def _evict(self) -> None:
        cutoff = time.monotonic() - self.ttl
        for cid in [c for c, t in self._touched.items() if t < cutoff]:
            self._items.pop(cid, None)
            self._touched.pop(cid, None)
        while len(self._items) > self.max:
            oldest = min(self._touched, key=self._touched.get)  # type: ignore[arg-type]
            self._items.pop(oldest, None)
            self._touched.pop(oldest, None)

    def create(self, owner: str, first_message: str, stage: RelationshipStage, language: str) -> Conversation:
        now = _now()
        conv = Conversation(new_id(), owner, make_title(first_message), now, now, stage, language)
        with self._lock:
            self._evict()
            self._items[conv.id] = conv
            self._touched[conv.id] = time.monotonic()
        return conv

    def get(self, owner: str, conversation_id: str) -> Conversation | None:
        with self._lock:
            conv = self._items.get(conversation_id)
            if conv is None or not secrets.compare_digest(conv.owner, owner):
                return None
            self._touched[conversation_id] = time.monotonic()
            return conv

    def list(self, owner: str, query: str | None = None, limit: int = 50, offset: int = 0) -> tuple[list[Conversation], int]:
        with self._lock:
            self._evict()
            items = [c for c in self._items.values() if c.owner == owner]
        if query:
            q = query.lower()
            items = [c for c in items if q in c.title.lower() or any(q in m.content.lower() for m in c.messages)]
        items.sort(key=lambda c: c.updated_at, reverse=True)
        return items[offset : offset + limit], len(items)

    def append(self, owner: str, conversation_id: str, message: StoredMessage, *, safety_level: str | None = None,
               stage: RelationshipStage | None = None, language: str | None = None) -> None:
        conv = self.get(owner, conversation_id)
        if conv is None:
            return
        with self._lock:
            conv.messages.append(message)
            conv.updated_at = _now()
            if safety_level:
                conv.safety_level = safety_level
            if stage:
                conv.relationship_stage = stage
            if language:
                conv.language = language

    def remove_last_assistant(self, owner: str, conversation_id: str) -> None:
        conv = self.get(owner, conversation_id)
        if conv and conv.messages and conv.messages[-1].role == "assistant":
            with self._lock:
                conv.messages.pop()

    def set_feedback(self, owner: str, conversation_id: str, message_id: str, rating: str) -> bool:
        conv = self.get(owner, conversation_id)
        if conv is None or not any(m.id == message_id and m.role == "assistant" for m in conv.messages):
            return False
        self._feedback[message_id] = rating
        return True

    def delete(self, owner: str, conversation_id: str) -> bool:
        with self._lock:
            conv = self._items.get(conversation_id)
            if conv is None or conv.owner != owner:
                return False
            del self._items[conversation_id]
            self._touched.pop(conversation_id, None)
            return True

    def delete_all(self, owner: str) -> int:
        with self._lock:
            ids = [cid for cid, c in self._items.items() if c.owner == owner]
            for cid in ids:
                self._items.pop(cid, None)
                self._touched.pop(cid, None)
            return len(ids)


SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    owner TEXT NOT NULL,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    relationship_stage TEXT NOT NULL,
    language TEXT NOT NULL,
    safety_level TEXT NOT NULL DEFAULT 'none'
);
CREATE INDEX IF NOT EXISTS idx_conversations_owner ON conversations(owner, updated_at);
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    seq INTEGER NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    payload TEXT NOT NULL DEFAULT '{}',
    feedback TEXT
);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, seq);
"""


class SQLiteConversationStore:
    persistent = True

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.executescript(SCHEMA)

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # -- helpers ---------------------------------------------------------------------
    def _row_to_conv(self, row: sqlite3.Row, with_messages: bool) -> Conversation:
        conv = Conversation(
            id=row["id"], owner=row["owner"], title=row["title"],
            created_at=datetime.fromisoformat(row["created_at"]), updated_at=datetime.fromisoformat(row["updated_at"]),
            relationship_stage=RelationshipStage(row["relationship_stage"]), language=row["language"],
            safety_level=row["safety_level"],
        )
        if with_messages:
            rows = self._conn.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY seq", (conv.id,)
            ).fetchall()
            conv.messages = [self._row_to_message(r) for r in rows]
        else:
            count = self._conn.execute("SELECT COUNT(*) FROM messages WHERE conversation_id = ?", (conv.id,)).fetchone()[0]
            conv.message_count = int(count)
        return conv

    @staticmethod
    def _row_to_message(row: sqlite3.Row) -> StoredMessage:
        payload = json.loads(row["payload"] or "{}")
        return StoredMessage(
            id=row["id"], role=row["role"], content=row["content"], created_at=datetime.fromisoformat(row["created_at"]),
            sources=[SourceCard(**s) for s in payload.get("sources", [])],
            safety=SafetyStatus(**payload["safety"]) if payload.get("safety") else None,
            language=payload.get("language"), grounded=payload.get("grounded"), generated=payload.get("generated"),
        )

    # -- API -------------------------------------------------------------------------
    def create(self, owner: str, first_message: str, stage: RelationshipStage, language: str) -> Conversation:
        now = _now()
        conv = Conversation(new_id(), owner, make_title(first_message), now, now, stage, language)
        with self._lock:
            self._conn.execute(
                "INSERT INTO conversations (id, owner, title, created_at, updated_at, relationship_stage, language) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (conv.id, owner, conv.title, now.isoformat(), now.isoformat(), stage.value, language),
            )
        return conv

    def get(self, owner: str, conversation_id: str) -> Conversation | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM conversations WHERE id = ? AND owner = ?", (conversation_id, owner)
            ).fetchone()
            return self._row_to_conv(row, with_messages=True) if row else None

    def list(self, owner: str, query: str | None = None, limit: int = 50, offset: int = 0) -> tuple[list[Conversation], int]:
        with self._lock:
            if query:
                like = "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
                where = ("WHERE c.owner = ? AND (c.title LIKE ? ESCAPE '\\' OR EXISTS (SELECT 1 FROM messages m "
                         "WHERE m.conversation_id = c.id AND m.content LIKE ? ESCAPE '\\'))")
                params: tuple = (owner, like, like)
            else:
                where, params = "WHERE c.owner = ?", (owner,)
            total = self._conn.execute(f"SELECT COUNT(*) FROM conversations c {where}", params).fetchone()[0]  # noqa: S608
            rows = self._conn.execute(
                f"SELECT c.* FROM conversations c {where} ORDER BY c.updated_at DESC LIMIT ? OFFSET ?",  # noqa: S608
                (*params, limit, offset),
            ).fetchall()
            return [self._row_to_conv(r, with_messages=False) for r in rows], int(total)

    def append(self, owner: str, conversation_id: str, message: StoredMessage, *, safety_level: str | None = None,
               stage: RelationshipStage | None = None, language: str | None = None) -> None:
        payload = json.dumps({
            "sources": [s.model_dump() for s in message.sources],
            "safety": message.safety.model_dump() if message.safety else None,
            "language": message.language, "grounded": message.grounded, "generated": message.generated,
        }, ensure_ascii=False)
        now = _now().isoformat()
        with self._lock:
            owned = self._conn.execute(
                "SELECT 1 FROM conversations WHERE id = ? AND owner = ?", (conversation_id, owner)
            ).fetchone()
            if not owned:
                return
            seq = self._conn.execute(
                "SELECT COALESCE(MAX(seq), 0) + 1 FROM messages WHERE conversation_id = ?", (conversation_id,)
            ).fetchone()[0]
            self._conn.execute("BEGIN")
            try:
                self._conn.execute(
                    "INSERT INTO messages (id, conversation_id, seq, role, content, created_at, payload) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (message.id, conversation_id, seq, message.role, message.content, message.created_at.isoformat(), payload),
                )
                self._conn.execute(
                    "UPDATE conversations SET updated_at = ?, safety_level = COALESCE(?, safety_level), "
                    "relationship_stage = COALESCE(?, relationship_stage), language = COALESCE(?, language) WHERE id = ?",
                    (now, safety_level, stage.value if stage else None, language, conversation_id),
                )
                self._conn.execute("COMMIT")
            except Exception:
                self._conn.execute("ROLLBACK")
                raise

    def remove_last_assistant(self, owner: str, conversation_id: str) -> None:
        with self._lock:
            self._conn.execute(
                "DELETE FROM messages WHERE id = (SELECT m.id FROM messages m JOIN conversations c ON c.id = m.conversation_id "
                "WHERE m.conversation_id = ? AND c.owner = ? ORDER BY m.seq DESC LIMIT 1) AND role = 'assistant'",
                (conversation_id, owner),
            )

    def set_feedback(self, owner: str, conversation_id: str, message_id: str, rating: str) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "UPDATE messages SET feedback = ? WHERE id = ? AND role = 'assistant' AND conversation_id = "
                "(SELECT id FROM conversations WHERE id = ? AND owner = ?)",
                (rating, message_id, conversation_id, owner),
            )
            return cur.rowcount > 0

    def delete(self, owner: str, conversation_id: str) -> bool:
        with self._lock:
            cur = self._conn.execute("DELETE FROM conversations WHERE id = ? AND owner = ?", (conversation_id, owner))
            return cur.rowcount > 0

    def delete_all(self, owner: str) -> int:
        with self._lock:
            cur = self._conn.execute("DELETE FROM conversations WHERE owner = ?", (owner,))
            self._conn.execute("VACUUM")
            return cur.rowcount

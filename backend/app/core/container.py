"""Service container: builds and holds long-lived services for the app (dependency injection)."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.config import Settings
from app.generation.llm_client import ChatModel, OpenAICompatibleClient
from app.retrieval.embeddings import EmbedderHolder
from app.retrieval.index_store import load_bundle
from app.retrieval.reranker import Reranker
from app.retrieval.retriever import Retriever
from app.safety.classifier import SafetyEnsemble
from app.safety.escalation import allowed_numbers, load_directory
from app.storage.sessions import ConversationStore, MemoryConversationStore, SQLiteConversationStore
from app.storage.settings_store import SettingsStore

log = logging.getLogger("couplecare.container")


@dataclass
class RebuildState:
    status: str = "idle"  # idle | running | succeeded | failed
    started_at: str | None = None
    finished_at: str | None = None
    message: str | None = None
    version: str | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)


class Container:
    def __init__(self, settings: Settings, *, llm: ChatModel | None = None, embedder: EmbedderHolder | None = None,
                 load_embedder: bool = True) -> None:
        self.settings = settings
        self.settings_store = SettingsStore(settings)
        self.embedder = embedder or EmbedderHolder(settings.embedding_backend, settings.embedding_model,
                                                   settings.embedding_device)
        self.reranker = Reranker(settings.reranker_model)
        self.retriever = Retriever(self.embedder, self.reranker)
        self.safety = SafetyEnsemble()
        self.support_directory = load_directory(settings.support_directory_path)
        self.allowed_numbers = allowed_numbers(self.support_directory)
        self._llm = llm
        self.memory_store = MemoryConversationStore()
        self._sqlite: SQLiteConversationStore | None = None
        self._sqlite_lock = threading.Lock()
        self.rebuild = RebuildState()
        self.index_error: str | None = None
        self.started_at = datetime.now(UTC)
        self.reload_index()
        if load_embedder and embedder is None:
            self.embedder.load_in_background()

    # -- model -----------------------------------------------------------------------
    def llm(self) -> ChatModel:
        if self._llm is not None:
            return self._llm
        runtime = self.settings_store.get()
        return OpenAICompatibleClient(
            self.settings.llm_base_url, runtime.model_id,
            timeout=self.settings.llm_timeout_seconds, connect_timeout=self.settings.llm_connect_timeout_seconds,
        )

    # -- storage ---------------------------------------------------------------------
    def store(self) -> ConversationStore:
        """SQLite only when persistence is enabled; otherwise the in-memory guest store."""
        if not self.settings_store.get().persistence_enabled:
            return self.memory_store
        with self._sqlite_lock:
            if self._sqlite is None:
                self._sqlite = SQLiteConversationStore(self.settings.sqlite_path)
            return self._sqlite

    def sqlite_if_exists(self) -> SQLiteConversationStore | None:
        """Open the database only if it already exists (used for deletion while persistence is off)."""
        with self._sqlite_lock:
            if self._sqlite is None and self.settings.sqlite_path.exists():
                self._sqlite = SQLiteConversationStore(self.settings.sqlite_path)
            return self._sqlite

    # -- index -----------------------------------------------------------------------
    def reload_index(self) -> None:
        try:
            self.retriever.set_bundle(load_bundle(self.settings.index_dir))
            self.index_error = None
        except Exception as exc:  # noqa: BLE001 - surface as status
            self.index_error = type(exc).__name__
            log.warning("index_load_failed", extra={"error_type": type(exc).__name__})
            self.retriever.set_bundle(None)

    def index_state(self) -> str:
        if self.rebuild.status == "running":
            return "building"
        if self.index_error:
            return "error"
        return "ready" if self.retriever.bundle else "missing"

    def close(self) -> None:
        if self._sqlite is not None:
            self._sqlite.close()

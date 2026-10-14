"""Conversation persistence, deletion and settings tests."""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.schemas import RelationshipStage, StoredMessage
from app.storage.sessions import MemoryConversationStore, SQLiteConversationStore, new_id, owner_key

LISTENING_Q = "My partner feels unheard. How can I practise reflective listening at a calm moment?"


def _msg(role: str, content: str) -> StoredMessage:
    return StoredMessage(id=new_id(), role=role, content=content, created_at=datetime.now(UTC))


def test_ids_are_random_128_bit_hex() -> None:
    ids = {new_id() for _ in range(200)}
    assert len(ids) == 200 and all(len(i) == 32 for i in ids)


def test_sqlite_store_roundtrip_and_isolation(tmp_path) -> None:
    store = SQLiteConversationStore(tmp_path / "c.sqlite3")
    alice, bob = owner_key("alice-client-000000"), owner_key("bob-client-00000000")
    conv = store.create(alice, "We keep arguing about money", RelationshipStage.MARRIED, "en")
    store.append(alice, conv.id, _msg("user", "We keep arguing about money"))
    store.append(alice, conv.id, _msg("assistant", "That sounds stressful."))
    store.append(bob, conv.id, _msg("user", "injected"))  # wrong owner: ignored
    loaded = store.get(alice, conv.id)
    assert loaded and [m.content for m in loaded.messages] == ["We keep arguing about money", "That sounds stressful."]
    assert store.get(bob, conv.id) is None
    items, total = store.list(alice)
    assert total == 1 and items[0].summary().message_count == 2
    assert store.list(alice, query="money")[1] == 1
    assert store.list(alice, query="100%_")[1] == 0  # LIKE wildcards are escaped
    assert store.delete(bob, conv.id) is False
    assert store.delete(alice, conv.id) is True
    assert store.get(alice, conv.id) is None
    store.close()


def test_sqlite_delete_all_only_affects_owner(tmp_path) -> None:
    store = SQLiteConversationStore(tmp_path / "c.sqlite3")
    a, b = owner_key("a-client-0000000000"), owner_key("b-client-0000000000")
    for _ in range(3):
        store.create(a, "x", RelationshipStage.DATING, "en")
    store.create(b, "y", RelationshipStage.DATING, "en")
    assert store.delete_all(a) == 3
    assert store.list(b)[1] == 1
    store.close()


def test_memory_store_expires(monkeypatch) -> None:
    store = MemoryConversationStore(ttl_seconds=10)
    owner = owner_key("mem-client-000000000")
    conv = store.create(owner, "hello", RelationshipStage.UNSPECIFIED, "en")
    import app.storage.sessions as sessions

    real = sessions.time.monotonic
    monkeypatch.setattr(sessions.time, "monotonic", lambda: real() + 60)
    store._evict()
    assert store.get(owner, conv.id) is None


def test_guest_mode_writes_nothing_to_disk(client, settings) -> None:
    client.post("/api/chat", json={"message": LISTENING_Q})
    assert not settings.sqlite_path.exists()
    assert client.get("/api/conversations").json()["persistence_enabled"] is False


def test_persistence_enabled_survives_new_container(client, settings) -> None:
    client.put("/api/settings", json={"persistence_enabled": True})
    conv = client.post("/api/chat", json={"message": LISTENING_Q}).json()["conversation_id"]
    assert settings.sqlite_path.exists()
    store = SQLiteConversationStore(settings.sqlite_path)
    rows = store.list(owner_key("test-client-0123456789abcdef"))[0]
    assert [r.id for r in rows] == [conv]
    store.close()


def test_delete_one_and_all_via_api(client) -> None:
    client.put("/api/settings", json={"persistence_enabled": True})
    first = client.post("/api/chat", json={"message": LISTENING_Q}).json()["conversation_id"]
    client.post("/api/chat", json={"message": "We feel distant lately, what can we do together?"})
    assert client.get("/api/conversations").json()["total"] == 2
    assert client.delete(f"/api/conversations/{first}").status_code == 204
    assert client.get(f"/api/conversations/{first}").status_code == 404
    assert client.request("DELETE", "/api/conversations", json={"confirm": "DELETE ALL"}).json()["deleted"] == 1
    assert client.get("/api/conversations").json()["total"] == 0


def test_delete_all_clears_disk_even_after_persistence_turned_off(client, settings) -> None:
    client.put("/api/settings", json={"persistence_enabled": True})
    client.post("/api/chat", json={"message": LISTENING_Q})
    client.put("/api/settings", json={"persistence_enabled": False})
    assert client.request("DELETE", "/api/conversations", json={"confirm": "DELETE ALL"}).json()["deleted"] >= 1
    store = SQLiteConversationStore(settings.sqlite_path)
    assert store.list(owner_key("test-client-0123456789abcdef"))[1] == 0
    store.close()


def test_conversation_search(client) -> None:
    client.post("/api/chat", json={"message": LISTENING_Q})
    client.post("/api/chat", json={"message": "My mother-in-law criticises my household every day"})
    res = client.get("/api/conversations", params={"q": "mother-in-law"}).json()
    assert res["total"] == 1 and "mother-in-law" in res["items"][0]["title"]


# --------------------------------------------------------------------------- settings


def test_settings_defaults_and_limits(client) -> None:
    body = client.get("/api/settings").json()
    assert body["values"]["persistence_enabled"] is False
    assert body["values"]["support_region"] == "unspecified"
    assert body["limits"]["temperature"] == {"min": 0.0, "max": 1.2}
    assert [m["id"] for m in body["models"]] == ["qwen3-4b-instruct-2507"]


def test_settings_update_validated(client) -> None:
    assert client.put("/api/settings", json={"temperature": 0.3}).json()["values"]["temperature"] == 0.3
    bad = client.put("/api/settings", json={"temperature": 5})
    assert bad.status_code == 400 and bad.json()["error"]["code"] == "invalid_settings"
    assert client.put("/api/settings", json={"model_id": "gpt-4"}).json()["error"]["code"] == "unknown_model"
    assert client.put("/api/settings", json={"llm_base_url": "http://evil"}).status_code == 422
    assert client.put("/api/settings", json={"support_region": "ZZ"}).status_code == 400


def test_settings_persist_and_reset(client, settings) -> None:
    client.put("/api/settings", json={"retrieval_top_k": 6})
    assert settings.runtime_settings_path.exists()
    assert client.post("/api/settings/reset").json()["values"]["retrieval_top_k"] == 4
    assert not settings.runtime_settings_path.exists()


def test_corrupt_settings_file_falls_back_to_defaults(settings) -> None:
    from app.storage.settings_store import SettingsStore

    settings.user_dir.mkdir(parents=True, exist_ok=True)
    settings.runtime_settings_path.write_text('{"temperature": 99, "evil": true}', encoding="utf-8")
    assert SettingsStore(settings).get().temperature == 0.6

"""Request validation, limits and security behaviour."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_empty_and_blank_messages_rejected(client) -> None:
    for message in ["", "   \n  "]:
        res = client.post("/api/chat", json={"message": message})
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "validation_error"


def test_too_long_message_rejected(client) -> None:
    res = client.post("/api/chat", json={"message": "a" * 4001})
    assert res.status_code == 422


def test_validation_errors_do_not_echo_input(client) -> None:
    secret = "my very private story " * 300
    res = client.post("/api/chat", json={"message": secret})
    assert "private story" not in res.text


def test_unknown_fields_rejected(client) -> None:
    res = client.post("/api/chat", json={"message": "hello", "model_url": "http://evil.example"})
    assert res.status_code == 422


def test_invalid_enums_rejected(client) -> None:
    assert client.post("/api/chat", json={"message": "hi", "language": "fr"}).status_code == 422
    assert client.post("/api/chat", json={"message": "hi", "relationship_stage": "situationship"}).status_code == 422


def test_invalid_conversation_id_rejected(client) -> None:
    assert client.post("/api/chat", json={"message": "hi", "conversation_id": "../../etc/passwd"}).status_code == 422
    assert client.get("/api/conversations/not-a-valid-id").status_code == 422


def test_missing_client_id_rejected(settings, container) -> None:
    with TestClient(create_app(settings, container)) as anonymous:
        res = anonymous.post("/api/chat", json={"message": "hello"})
        assert res.status_code == 400 and res.json()["error"]["code"] == "missing_client_id"
        assert anonymous.get("/api/conversations", headers={"X-Client-Id": "bad id!"}).status_code == 400


def test_oversized_body_rejected(client) -> None:
    res = client.post("/api/chat", content=b"{" + b" " * (70 * 1024) + b"}", headers={"Content-Type": "application/json"})
    assert res.status_code == 413
    assert res.json()["error"]["code"] == "payload_too_large"


def test_security_headers_present(client) -> None:
    res = client.get("/api/health")
    assert res.headers["x-content-type-options"] == "nosniff"
    assert res.headers["cache-control"] == "no-store"


def test_cors_only_allows_local_frontend(client) -> None:
    ok = client.options("/api/health", headers={"Origin": "http://127.0.0.1:5173", "Access-Control-Request-Method": "GET"})
    assert ok.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"
    bad = client.options("/api/health", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in bad.headers


def test_delete_all_requires_confirmation(client) -> None:
    assert client.request("DELETE", "/api/conversations", json={}).status_code == 422
    assert client.request("DELETE", "/api/conversations", json={"confirm": "yes"}).status_code == 422
    assert client.request("DELETE", "/api/conversations", json={"confirm": "DELETE ALL"}).status_code == 200


def test_unknown_route_is_structured_404(client) -> None:
    res = client.get("/api/does-not-exist")
    assert res.status_code == 404 and res.json()["error"]["code"] == "not_found"

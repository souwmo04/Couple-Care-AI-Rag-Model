"""End-to-end API tests for chat with a fake model server."""

from __future__ import annotations

import json

from app.errors import ModelTimeoutError
from tests.conftest import CLIENT_ID, OTHER_CLIENT_ID, FakeChatModel

LISTENING_Q = "My partner feels unheard. How can I practise reflective listening at a calm moment?"


def test_health_reports_components(client) -> None:
    body = client.get("/api/health").json()
    assert body["model_server"] == "online"
    assert body["index"] == "ready"
    assert body["embeddings"] == "fallback"
    assert body["status"] == "degraded"  # hashing embedder is not a real semantic model
    assert body["version"]


def test_model_status(client) -> None:
    body = client.get("/api/model/status").json()
    assert body["configured"] is True and body["reachable"] is True
    assert body["model_id"] == "qwen3-4b-instruct-2507"


def test_grounded_chat_returns_validated_sources(client, fake_llm) -> None:
    fake_llm.answer = "Try reflective listening [S1]. Also pick a calm moment [S9]."
    res = client.post("/api/chat", json={"message": LISTENING_Q, "language": "auto", "relationship_stage": "dating"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["generated"] is True and body["grounded"] is True
    assert "[S9]" not in body["answer"]  # fabricated citation removed
    assert body["sources"] and body["sources"][0]["citation_id"] == "S1" and body["sources"][0]["cited"] is True
    assert body["detected_language"] == "en" and body["response_language"] == "en"
    assert body["safety"]["level"] == "none"
    assert len(body["conversation_id"]) == 32
    # The model received the retrieved passage labels and the stage context.
    system, *_rest, user = fake_llm.calls[-1]
    assert "[S1]" in user.content and "dating" in system.content


def test_off_topic_chat_is_ungrounded(client, fake_llm) -> None:
    fake_llm.answer = "General thought [S1]."
    body = client.post("/api/chat", json={"message": "zzqx flurble wibble quantum"}).json()
    assert body["grounded"] is False and body["sources"] == []
    assert "[S1]" not in body["answer"]
    assert "No sufficiently relevant passages" in fake_llm.calls[-1][-1].content


def test_bangla_message_gets_bangla_instruction(client, fake_llm) -> None:
    body = client.post("/api/chat", json={"message": "ঝগড়া খুব উত্তপ্ত হয়ে যায়, আমরা কী করব?"}).json()
    assert body["detected_language"] == "bn" and body["response_language"] == "bn"
    assert "Bengali script" in fake_llm.calls[-1][0].content


def test_explicit_language_overrides_detection(client, fake_llm) -> None:
    body = client.post("/api/chat", json={"message": LISTENING_Q, "language": "banglish"}).json()
    assert body["response_language"] == "banglish"
    assert "Roman" in fake_llm.calls[-1][0].content


def test_urgent_safety_skips_generation(client, fake_llm) -> None:
    body = client.post("/api/chat", json={"message": "He is outside my door right now with a knife"}).json()
    assert body["safety"]["level"] == "urgent"
    assert body["generated"] is False and body["model_id"] is None
    assert "emergency" in body["answer"].lower()
    assert fake_llm.calls == []


def test_banglish_self_harm_uses_banglish_template(client, fake_llm) -> None:
    body = client.post("/api/chat", json={"message": "amar more jete icche kore, ar parchi na"}).json()
    assert body["safety"]["level"] == "urgent" and body["response_language"] == "banglish"
    assert "chatbot" in body["answer"] and fake_llm.calls == []


def test_surveillance_request_declined(client, fake_llm) -> None:
    body = client.post("/api/chat", json={"message": "How can I read my wife's WhatsApp messages secretly?"}).json()
    assert body["safety"]["level"] == "declined" and body["generated"] is False
    assert body["safety"]["resources"] == []
    assert fake_llm.calls == []


def test_violence_disclosure_constrains_generation_and_filters_output(client, fake_llm) -> None:
    fake_llm.answer = "I'm sorry this happened. You might try couples counselling. Reach out to someone you trust."
    body = client.post("/api/chat", json={"message": "My husband slapped me yesterday"}).json()
    assert body["safety"]["level"] == "support"
    assert "counselling" not in body["answer"]
    assert "do NOT suggest couples counselling" in fake_llm.calls[-1][0].content


def test_support_resources_only_after_region_selected(client) -> None:
    body = client.post("/api/chat", json={"message": "My husband slapped me yesterday"}).json()
    assert body["safety"]["resources"] == []
    client.put("/api/settings", json={"support_region": "BD"})
    body = client.post("/api/chat", json={"message": "My husband slapped me yesterday"}).json()
    contacts = {r["contact"] for r in body["safety"]["resources"]}
    assert "999" in contacts


def test_model_offline_returns_503_and_clear_error(client, fake_llm) -> None:
    fake_llm.online = False
    res = client.post("/api/chat", json={"message": LISTENING_Q})
    assert res.status_code == 503
    assert res.json()["error"]["code"] == "model_offline" and res.json()["error"]["retryable"] is True


def test_model_timeout_returns_504(client, fake_llm) -> None:
    fake_llm.error = ModelTimeoutError("The local model took too long to respond.")
    res = client.post("/api/chat", json={"message": LISTENING_Q})
    assert res.status_code == 504 and res.json()["error"]["code"] == "model_timeout"


def test_conversation_context_is_carried(client, fake_llm) -> None:
    first = client.post("/api/chat", json={"message": LISTENING_Q}).json()
    client.post(
        "/api/chat", json={"message": "What exactly should I say?", "conversation_id": first["conversation_id"]}
    )
    messages = fake_llm.calls[-1]
    roles = [m.role for m in messages]
    assert roles[:3] == ["system", "user", "assistant"]
    assert messages[1].content == LISTENING_Q
    assert "What exactly should I say?" in messages[-1].content


def test_regenerate_replaces_last_answer(client, fake_llm) -> None:
    first = client.post("/api/chat", json={"message": LISTENING_Q}).json()
    fake_llm.answer = "A different answer [S1]."
    again = client.post(
        "/api/chat", json={"message": LISTENING_Q, "conversation_id": first["conversation_id"], "regenerate": True}
    ).json()
    assert again["answer"].startswith("A different answer")
    detail = client.get(f"/api/conversations/{first['conversation_id']}").json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]
    assert detail["messages"][1]["content"].startswith("A different answer")


def test_unknown_conversation_is_404(client) -> None:
    res = client.post("/api/chat", json={"message": "hello there", "conversation_id": "0" * 32})
    assert res.status_code == 404


def test_streaming_chat_emits_meta_delta_done(client, fake_llm) -> None:
    fake_llm.answer = "Try reflective listening [S1]. Your husband is clearly a narcissist. Keep it calm."
    with client.stream("POST", "/api/chat/stream", json={"message": LISTENING_Q}) as res:
        assert res.status_code == 200
        raw = "".join(res.iter_text())
    events = [json.loads(line[5:]) for line in raw.splitlines() if line.startswith("data:")]
    kinds = [e["event"] for e in events]
    assert kinds[0] == "meta" and kinds[-1] == "done" and "delta" in kinds
    streamed = "".join(e["text"] for e in events if e["event"] == "delta")
    assert "narcissist" not in streamed  # filtered before it was ever sent
    final = events[-1]["response"]
    assert final["generated"] is True and "narcissist" not in final["answer"]


def test_streaming_validation_error_is_http_error(client) -> None:
    res = client.post("/api/chat/stream", json={"message": "hi", "conversation_id": "f" * 32})
    assert res.status_code == 404


def test_conversations_are_isolated_between_clients(client) -> None:
    conv = client.post("/api/chat", json={"message": LISTENING_Q}).json()["conversation_id"]
    other = {"X-Client-Id": OTHER_CLIENT_ID}
    assert client.get(f"/api/conversations/{conv}", headers=other).status_code == 404
    assert client.delete(f"/api/conversations/{conv}", headers=other).status_code == 404
    assert client.get("/api/conversations", headers=other).json()["total"] == 0
    assert client.get(f"/api/conversations/{conv}", headers={"X-Client-Id": CLIENT_ID}).status_code == 200


def test_feedback_is_recorded(client) -> None:
    body = client.post("/api/chat", json={"message": LISTENING_Q}).json()
    url = f"/api/conversations/{body['conversation_id']}/messages/{body['message_id']}/feedback"
    assert client.post(url, json={"rating": "helpful"}).status_code == 204
    assert client.post(url, json={"rating": "amazing"}).status_code == 422


def test_fake_model_never_used_for_template_flag() -> None:
    # Guard: FakeChatModel defaults are distinct from safety templates.
    assert "emergency" not in FakeChatModel().answer.lower()


def test_truncated_answer_is_trimmed_to_last_sentence() -> None:
    from app.core.orchestrator import trim_incomplete_sentence

    assert trim_incomplete_sentence("প্রথম বাক্য। দ্বিতীয় বাক্য [S1]। তৃতীয় বাক্য অসম") == "প্রথম বাক্য। দ্বিতীয় বাক্য [S1]।"
    assert trim_incomplete_sentence("Done. Also this [S2].") == "Done. Also this [S2]."
    assert trim_incomplete_sentence("Try a break.\n\n- **Name it**") == "Try a break."
    assert trim_incomplete_sentence("no punctuation at all") == "no punctuation at all"
    assert trim_incomplete_sentence('He said "stop."') == 'He said "stop."'


def test_bangla_reply_gets_larger_output_allowance(client, fake_llm) -> None:
    client.post("/api/chat", json={"message": "ঝগড়া খুব উত্তপ্ত হয়ে যায়, আমরা কী করব?"})
    client.post("/api/chat", json={"message": LISTENING_Q})
    assert fake_llm.params[-2].max_tokens > fake_llm.params[-1].max_tokens

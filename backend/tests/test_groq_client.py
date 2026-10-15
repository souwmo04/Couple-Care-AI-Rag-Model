"""Opt-in Groq cloud mode: client behaviour (httpx.MockTransport, nothing leaves the machine) and wiring."""

from __future__ import annotations

import json

import httpx
import pytest

from app.config import Settings
from app.core.container import Container
from app.errors import ModelOfflineError, ModelResponseError
from app.generation import llm_client
from app.generation.llm_client import ChatMessage, GenerationParams, GroqClient

MESSAGES = [ChatMessage("user", "hi")]


def groq(handler, *, key: str | None = "test-key", model: str = "openai/gpt-oss-120b") -> GroqClient:
    return GroqClient(key, model, timeout=5, connect_timeout=1, transport=httpx.MockTransport(handler))


@pytest.fixture(autouse=True)
def _clear_status_cache():
    llm_client._groq_status_cache.clear()
    yield
    llm_client._groq_status_cache.clear()


async def test_sends_key_to_fixed_groq_endpoint_and_hides_reasoning() -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "Hello", "reasoning": "secret"}}]})

    out = await groq(handler).complete(MESSAGES, GenerationParams(max_tokens=500))
    assert out == "Hello"
    assert seen["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert seen["auth"] == "Bearer test-key"
    body = seen["body"]
    assert body["model"] == "openai/gpt-oss-120b"
    assert body["include_reasoning"] is False and body["reasoning_effort"] == "low"
    assert body["max_tokens"] == 500 + 1024


async def test_non_reasoning_model_gets_plain_payload() -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    await groq(handler, model="llama-3.3-70b-versatile").complete(MESSAGES, GenerationParams(max_tokens=300))
    assert "include_reasoning" not in seen and seen["max_tokens"] == 300


@pytest.mark.parametrize(
    ("status", "error", "code"),
    [
        (401, ModelOfflineError, "model_auth"),
        (429, ModelOfflineError, "model_rate_limited"),
        (404, ModelResponseError, None),
        (500, ModelResponseError, None),
    ],  # fmt: skip
)
async def test_errors_are_explained(status: int, error: type, code: str | None) -> None:
    with pytest.raises(error) as exc:
        await groq(lambda _: httpx.Response(status, json={"error": {}})).complete(MESSAGES, GenerationParams())
    if code:
        assert exc.value.code == code


async def test_missing_key_fails_without_any_request() -> None:
    def handler(_: httpx.Request) -> httpx.Response:  # pragma: no cover - must not be called
        raise AssertionError("no request expected")

    client = groq(handler, key=None)
    with pytest.raises(ModelOfflineError):
        await client.complete(MESSAGES, GenerationParams())
    info = await client.server_info()
    assert not info.reachable and "COUPLECARE_GROQ_API_KEY" in (info.detail or "")


async def test_status_is_cached_to_save_quota() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(200, json={"id": "openai/gpt-oss-120b", "context_window": 131072})

    client = groq(handler)
    first = await client.server_info()
    second = await client.server_info()
    assert first.reachable and first.context_length == 131072 and second.reachable
    assert calls == ["/openai/v1/models/openai/gpt-oss-120b"]


async def test_bad_key_status() -> None:
    info = await groq(lambda _: httpx.Response(401)).server_info()
    assert not info.reachable and "rejected" in (info.detail or "")


def test_container_uses_groq_only_when_opted_in(tmp_path) -> None:
    base = {"user_dir": tmp_path, "embedding_backend": "hashing"}
    local = Container(Settings(**base), load_embedder=False)
    assert not isinstance(local.llm(), GroqClient)
    cloud = Container(Settings(**base, llm_provider="groq", groq_api_key="k", groq_model="llama-3.3-70b-versatile"),
                      load_embedder=False)  # fmt: skip
    assert isinstance(cloud.llm(), GroqClient)
    assert cloud.active_model_id() == "groq:llama-3.3-70b-versatile"


def test_groq_key_is_secret() -> None:
    settings = Settings(llm_provider="groq", groq_api_key="super-secret")
    assert "super-secret" not in repr(settings) and "super-secret" not in settings.model_dump_json()


def test_groq_model_name_is_validated() -> None:
    with pytest.raises(ValueError):
        Settings(groq_model="bad model; rm -rf")

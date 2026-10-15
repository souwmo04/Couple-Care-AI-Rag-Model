"""Opt-in Groq cloud mode: client behaviour (httpx.MockTransport, nothing leaves the machine) and wiring."""

from __future__ import annotations

import json

import httpx
import pytest

from app.config import Settings
from app.core.container import Container
from app.errors import ModelOfflineError, ModelResponseError
from app.generation import llm_client
from app.generation.llm_client import ChatMessage, FallbackChatModel, GenerationParams, GroqClient

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
    assert body["max_tokens"] == 500 + 300


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
    local = Container(Settings(_env_file=None, **base), load_embedder=False)
    assert not isinstance(local.llm(), (GroqClient, FallbackChatModel))
    groq_settings = {"llm_provider": "groq", "groq_api_key": "k", "groq_model": "llama-3.3-70b-versatile"}
    cloud = Container(Settings(_env_file=None, **base, **groq_settings), load_embedder=False)
    model = cloud.llm()
    assert isinstance(model, FallbackChatModel) and isinstance(model.primary, GroqClient)
    assert model.primary.max_retry_wait == 10.0  # switch to local quickly instead of waiting long
    assert cloud.active_model_id() == "groq:llama-3.3-70b-versatile"
    strict = Container(
        Settings(_env_file=None, **base, **groq_settings, groq_fallback_local=False), load_embedder=False
    )
    assert isinstance(strict.llm(), GroqClient)


class FakeModel:
    def __init__(self, text: str | None = None, error: Exception | None = None, partial: str | None = None) -> None:
        self.text, self.error, self.partial, self.calls = text, error, partial, 0

    async def complete(self, messages, params) -> str:
        self.calls += 1
        if self.error:
            raise self.error
        return self.text or ""

    async def stream(self, messages, params):
        self.calls += 1
        if self.partial:
            yield self.partial
        if self.error:
            raise self.error
        yield self.text or ""

    async def server_info(self):  # pragma: no cover - not used here
        raise NotImplementedError


async def test_fallback_answers_locally_when_cloud_is_rate_limited() -> None:
    limited = llm_client.RateLimitedError("limit", 120)
    model = FallbackChatModel(FakeModel(error=limited), FakeModel(text="local answer"))
    assert await model.complete(MESSAGES, GenerationParams()) == "local answer"
    assert model.fallback_used and model.fallback_reason == "rate_limited"


async def test_fallback_not_used_when_cloud_works() -> None:
    local = FakeModel(text="local")
    model = FallbackChatModel(FakeModel(text="cloud answer"), local)
    assert await model.complete(MESSAGES, GenerationParams()) == "cloud answer"
    assert not model.fallback_used and local.calls == 0


async def test_fallback_stream_and_original_error_when_both_fail() -> None:
    model = FallbackChatModel(FakeModel(error=ModelOfflineError("net down")), FakeModel(text="from local"))
    assert [d async for d in model.stream(MESSAGES, GenerationParams())] == ["from local"]
    assert model.fallback_reason == "unavailable"
    both = FallbackChatModel(
        FakeModel(error=llm_client.RateLimitedError("limit", None)), FakeModel(error=ModelOfflineError("off"))
    )
    with pytest.raises(ModelOfflineError) as exc:
        await both.complete(MESSAGES, GenerationParams())
    assert exc.value.code == "model_rate_limited"  # the user sees why the cloud failed, not the fallback's error


async def test_fallback_never_splices_a_half_streamed_reply() -> None:
    model = FallbackChatModel(
        FakeModel(partial="Half a sentence", error=ModelOfflineError("dropped")), FakeModel(text="x")
    )
    with pytest.raises(ModelOfflineError):
        _ = [d async for d in model.stream(MESSAGES, GenerationParams())]
    assert not model.fallback_used


def test_groq_key_is_secret() -> None:
    settings = Settings(_env_file=None, llm_provider="groq", groq_api_key="super-secret")
    assert "super-secret" not in repr(settings) and "super-secret" not in settings.model_dump_json()


def test_groq_model_name_is_validated() -> None:
    with pytest.raises(ValueError):
        Settings(_env_file=None, groq_model="bad model; rm -rf")


async def test_rate_limit_waits_and_retries(monkeypatch) -> None:
    waits: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        waits.append(seconds)

    monkeypatch.setattr(llm_client.asyncio, "sleep", fake_sleep)
    calls = iter([
        httpx.Response(429, headers={"x-ratelimit-reset-tokens": "2.5s"}),
        httpx.Response(200, json={"choices": [{"message": {"content": "after waiting"}}]}),
    ])  # fmt: skip
    out = await groq(lambda _: next(calls)).complete(MESSAGES, GenerationParams())
    assert out == "after waiting" and waits == [3.0]


async def test_rate_limit_with_long_wait_is_reported(monkeypatch) -> None:
    async def fake_sleep(_: float) -> None:  # pragma: no cover - must not wait
        raise AssertionError("should not wait")

    monkeypatch.setattr(llm_client.asyncio, "sleep", fake_sleep)
    with pytest.raises(ModelOfflineError) as exc:
        await groq(lambda _: httpx.Response(429, headers={"retry-after": "120"})).complete(MESSAGES, GenerationParams())
    assert exc.value.code == "model_rate_limited"


def test_retry_wait_parsing() -> None:
    assert llm_client._retry_wait_seconds(httpx.Response(429, headers={"retry-after": "7"})) == 7
    assert llm_client._retry_wait_seconds(httpx.Response(429, headers={"x-ratelimit-reset-tokens": "1m2.5s"})) == 62.5
    assert llm_client._retry_wait_seconds(httpx.Response(429)) is None


async def test_output_reservation_is_capped_for_the_free_tier() -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    # A Bangla allowance sized for the local tokenizer (e.g. 1750) must not be reserved in full.
    await groq(handler).complete(MESSAGES, GenerationParams(max_tokens=1750))
    assert seen["max_tokens"] == llm_client.GROQ_MAX_OUTPUT_TOKENS + llm_client.GROQ_REASONING_TOKENS


async def test_chat_reply_reports_local_fallback(settings) -> None:
    from app.core.orchestrator import Orchestrator
    from app.core.schemas import ChatRequest
    from tests.conftest import FakeChatModel, make_container

    cloud_down = FakeChatModel(error=llm_client.RateLimitedError("limit", None))
    container = make_container(settings, llm=FallbackChatModel(cloud_down, FakeChatModel("Local guidance [S1].")))
    reply = await Orchestrator(container).respond(ChatRequest(message="My partner does not listen to me"), owner="o")
    assert reply.generated and reply.answer.startswith("Local guidance")
    assert reply.fallback_reason == "rate_limited"
    assert reply.model_id == container.settings_store.get().model_id  # the local model, not groq:…

"""Model adapter tests using httpx.MockTransport (no real server)."""

from __future__ import annotations

import json

import httpx
import pytest

from app.errors import ModelOfflineError, ModelResponseError, ModelTimeoutError
from app.generation.llm_client import ChatMessage, GenerationParams, OpenAICompatibleClient, strip_reasoning

MESSAGES = [ChatMessage("user", "hi")]


def client_with(handler) -> OpenAICompatibleClient:
    return OpenAICompatibleClient(
        "http://127.0.0.1:8080", "m", timeout=5, connect_timeout=1, transport=httpx.MockTransport(handler)
    )


async def test_complete_returns_content_and_sends_params() -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": "Hello there"}}]})

    out = await client_with(handler).complete(MESSAGES, GenerationParams(temperature=0.2, max_tokens=50))
    assert out == "Hello there"
    assert seen["temperature"] == 0.2 and seen["max_tokens"] == 50 and seen["stream"] is False


async def test_reasoning_block_is_stripped() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "<think>secret plan</think>Answer"}}]})

    assert await client_with(handler).complete(MESSAGES, GenerationParams()) == "Answer"


def test_strip_unterminated_reasoning() -> None:
    assert strip_reasoning("Visible<think>never closed") == "Visible"


async def test_connection_refused_maps_to_offline() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(ModelOfflineError):
        await client_with(handler).complete(MESSAGES, GenerationParams())


async def test_read_timeout_maps_to_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(ModelTimeoutError):
        await client_with(handler).complete(MESSAGES, GenerationParams())


async def test_server_error_maps_to_model_error() -> None:
    with pytest.raises(ModelResponseError):
        await client_with(lambda r: httpx.Response(500, text="boom")).complete(MESSAGES, GenerationParams())


async def test_out_of_memory_is_explained() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="ggml_cuda: CUDA error: out of memory")

    with pytest.raises(ModelResponseError) as info:
        await client_with(handler).complete(MESSAGES, GenerationParams())
    assert info.value.code == "model_out_of_memory"
    assert "GPU memory" in info.value.message


async def test_loading_server_is_reported_offline() -> None:
    with pytest.raises(ModelOfflineError):
        await client_with(lambda r: httpx.Response(503, json={"error": "loading"})).complete(
            MESSAGES, GenerationParams()
        )


async def test_malformed_body_is_model_error() -> None:
    with pytest.raises(ModelResponseError):
        await client_with(lambda r: httpx.Response(200, json={"nope": 1})).complete(MESSAGES, GenerationParams())


async def test_stream_yields_deltas() -> None:
    body = (
        "".join(f"data: {json.dumps({'choices': [{'delta': {'content': t}}]})}\n\n" for t in ["Hel", "lo", "!"])
        + "data: [DONE]\n\n"
    )

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=body, headers={"content-type": "text/event-stream"})

    chunks = [c async for c in client_with(handler).stream(MESSAGES, GenerationParams())]
    assert "".join(chunks) == "Hello!"


async def test_server_info_online_and_offline() -> None:
    def online(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "qwen.gguf", "meta": {"n_ctx_train": 32768}}]})
        return httpx.Response(200, json={"default_generation_settings": {"n_ctx": 4096}})

    info = await client_with(online).server_info()
    assert info.reachable and info.model == "qwen.gguf" and info.context_length == 4096

    def offline(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    info = await client_with(offline).server_info()
    assert not info.reachable and info.detail


def test_settings_reject_non_loopback_model_url() -> None:
    from pydantic import ValidationError

    from app.config import Settings

    with pytest.raises(ValidationError):
        Settings(_env_file=None, llm_base_url="http://example.com:8080")
    with pytest.raises(ValidationError):
        Settings(_env_file=None, host="0.0.0.0")  # noqa: S104
    assert Settings(_env_file=None, llm_base_url="http://localhost:8080").llm_base_url == "http://localhost:8080"


async def test_api_key_file_is_sent_as_bearer(tmp_path) -> None:
    key = tmp_path / "server.key"
    key.write_text("abc123\n", encoding="utf-8")
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    c = OpenAICompatibleClient("http://127.0.0.1:18080", "m", timeout=5, connect_timeout=1,
                               transport=httpx.MockTransport(handler), api_key_file=key)  # fmt: skip
    assert await c.complete(MESSAGES, GenerationParams()) == "ok"
    assert seen["auth"] == "Bearer abc123"


async def test_rejected_key_is_reported_clearly() -> None:
    with pytest.raises(ModelOfflineError) as info:
        await client_with(lambda r: httpx.Response(401, json={"error": "invalid key"})).complete(
            MESSAGES, GenerationParams()
        )
    assert info.value.code == "model_auth"

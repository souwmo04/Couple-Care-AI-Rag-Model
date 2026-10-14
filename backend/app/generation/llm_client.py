"""Model adapter for local, OpenAI-compatible chat servers (llama.cpp ``llama-server``).

The backend talks to the generator only through ``ChatModel``, so swapping the model
family (Qwen3, Gemma 3, Llama 3.2) is a configuration change: llama.cpp applies each
GGUF's embedded chat template server-side via ``/v1/chat/completions``.

Error mapping:
    connection refused / DNS / connect timeout → ModelOfflineError (503)
    read timeout                                → ModelTimeoutError (504)
    HTTP 5xx / malformed body / OOM text        → ModelResponseError (502)
"""

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.errors import ModelOfflineError, ModelResponseError, ModelTimeoutError

THINK_RE = re.compile(r"<think>.*?</think>\s*", re.DOTALL | re.IGNORECASE)
OOM_HINTS = ("out of memory", "cudaMalloc failed", "failed to allocate", "CUDA error")


@dataclass(slots=True)
class ChatMessage:
    role: str
    content: str


@dataclass(slots=True)
class GenerationParams:
    temperature: float = 0.6
    max_tokens: int = 700
    top_p: float = 0.9
    stop: tuple[str, ...] = ()


@dataclass(slots=True)
class ServerInfo:
    reachable: bool
    model: str | None = None
    context_length: int | None = None
    detail: str | None = None


class ChatModel(Protocol):
    async def complete(self, messages: list[ChatMessage], params: GenerationParams) -> str: ...

    def stream(self, messages: list[ChatMessage], params: GenerationParams) -> AsyncIterator[str]: ...

    async def server_info(self) -> ServerInfo: ...


def strip_reasoning(text: str) -> str:
    """Remove any hidden-reasoning block some chat templates emit; it is never shown to users."""
    text = THINK_RE.sub("", text)
    # An unterminated <think> (e.g. truncated output) — drop everything from it.
    idx = text.lower().find("<think>")
    return (text[:idx] if idx >= 0 else text).strip()


def _oom_message(body: str) -> str | None:
    lowered = body.lower()
    if any(h.lower() in lowered for h in OOM_HINTS):
        return (
            "The local model ran out of GPU memory. Lower the context size or the number of GPU "
            "layers (-ngl) in the model-server launch script, or use a smaller quantization."
        )
    return None


class OpenAICompatibleClient:
    def __init__(
        self,
        base_url: str,
        model_id: str,
        *,
        timeout: float,
        connect_timeout: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_id = model_id
        self._timeout = httpx.Timeout(timeout, connect=connect_timeout)
        self._transport = transport

    def _client(self, timeout: httpx.Timeout | None = None) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.base_url, timeout=timeout or self._timeout, transport=self._transport)

    def _payload(self, messages: list[ChatMessage], params: GenerationParams, stream: bool) -> dict:
        payload: dict = {
            "model": self.model_id,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": params.temperature,
            "top_p": params.top_p,
            "max_tokens": params.max_tokens,
            "stream": stream,
        }
        if params.stop:
            payload["stop"] = list(params.stop)
        return payload

    @staticmethod
    def _raise_for(response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        body = response.text[:2000]
        oom = _oom_message(body)
        if oom:
            raise ModelResponseError(oom, code="model_out_of_memory")
        if response.status_code == 503:
            raise ModelOfflineError("The local model server is still loading the model. Try again shortly.")
        raise ModelResponseError(f"The local model server returned an error (HTTP {response.status_code}).")

    async def complete(self, messages: list[ChatMessage], params: GenerationParams) -> str:
        try:
            async with self._client() as client:
                response = await client.post("/v1/chat/completions", json=self._payload(messages, params, False))
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            raise ModelOfflineError("The local model server is not running or not reachable.") from exc
        except httpx.TimeoutException as exc:
            raise ModelTimeoutError("The local model took too long to respond.") from exc
        except httpx.HTTPError as exc:
            raise ModelOfflineError("Could not communicate with the local model server.") from exc
        self._raise_for(response)
        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ModelResponseError("The local model server returned an unexpected response.") from exc
        if not isinstance(content, str):
            raise ModelResponseError("The local model server returned an empty response.")
        return strip_reasoning(content)

    async def stream(self, messages: list[ChatMessage], params: GenerationParams) -> AsyncIterator[str]:
        try:
            async with (
                self._client() as client,
                client.stream("POST", "/v1/chat/completions", json=self._payload(messages, params, True)) as response,
            ):
                if response.status_code >= 400:
                    await response.aread()
                    self._raise_for(response)
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        delta = json.loads(data)["choices"][0].get("delta", {}).get("content")
                    except (ValueError, KeyError, IndexError, TypeError):
                        continue
                    if delta:
                        yield delta
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            raise ModelOfflineError("The local model server is not running or not reachable.") from exc
        except httpx.TimeoutException as exc:
            raise ModelTimeoutError("The local model took too long to respond.") from exc
        except httpx.HTTPError as exc:
            raise ModelOfflineError("Could not communicate with the local model server.") from exc

    async def server_info(self) -> ServerInfo:
        quick = httpx.Timeout(3.0, connect=1.5)
        try:
            async with self._client(quick) as client:
                health = await client.get("/health")
                if health.status_code == 503:
                    return ServerInfo(False, detail="Model server is starting and still loading the model.")
                if health.status_code >= 400:
                    return ServerInfo(False, detail=f"Model server health check failed (HTTP {health.status_code}).")
                model_name = None
                context = None
                try:
                    models = (await client.get("/v1/models")).json()
                    first = (models.get("data") or [{}])[0]
                    model_name = first.get("id")
                    meta = first.get("meta") or {}
                    context = meta.get("n_ctx_train")
                except (httpx.HTTPError, ValueError, AttributeError, IndexError):
                    pass
                try:
                    props = (await client.get("/props")).json()
                    context = props.get("default_generation_settings", {}).get("n_ctx") or context
                except (httpx.HTTPError, ValueError, AttributeError):
                    pass
                return ServerInfo(True, model=model_name, context_length=context)
        except httpx.HTTPError:
            return ServerInfo(False, detail="Model server is not running or not reachable.")

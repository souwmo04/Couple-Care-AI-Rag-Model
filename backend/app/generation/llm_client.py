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

import asyncio
import json
import re
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
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
        api_key_file: Path | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_id = model_id
        self._timeout = httpx.Timeout(timeout, connect=connect_timeout)
        self._transport = transport
        self._api_key_file = api_key_file

    def _headers(self) -> dict[str, str]:
        """Bearer key written by scripts/start-model.ps1. Read per request so a restarted server's
        new key is picked up; without it, any web page could use the local model via the browser."""
        if self._api_key_file and self._api_key_file.exists():
            key = self._api_key_file.read_text(encoding="utf-8").strip()
            if key:
                return {"Authorization": f"Bearer {key}"}
        return {}

    def _client(self, timeout: httpx.Timeout | None = None) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url, timeout=timeout or self._timeout, transport=self._transport, headers=self._headers()
        )

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
        if response.status_code == 401:
            raise ModelOfflineError(
                "The local model server rejected the request (API key mismatch). "
                "Restart it with scripts\\start-model.ps1.",
                code="model_auth",
            )
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


# ----------------------------------------------------------------------------- cloud (opt-in)

GROQ_BASE_URL = "https://api.groq.com/openai"  # fixed: cloud mode can only ever talk to Groq
GROQ_STATUS_TTL_SECONDS = 60.0
# The free tier allows ~8k tokens/minute for gpt-oss-120b (≈2 chat turns). When Groq says how long to wait,
# wait (up to this long) and retry instead of failing the user's message.
GROQ_MAX_RETRY_WAIT_SECONDS = 30.0
GROQ_RETRIES = 2
# Reply budget for Groq (measured 2026-10-15: completions 450–660 tokens incl. low-effort reasoning).
GROQ_MAX_OUTPUT_TOKENS = 800
GROQ_REASONING_TOKENS = 300
_DURATION_RE = re.compile(r"(?:(\d+(?:\.\d+)?)m)?(?:(\d+(?:\.\d+)?)s)?$")


def _retry_wait_seconds(response: httpx.Response) -> float | None:
    """Seconds to wait from ``retry-after`` (seconds) or ``x-ratelimit-reset-tokens`` ("48.2s", "1m2s")."""
    value = response.headers.get("retry-after")
    if value:
        try:
            return float(value)
        except ValueError:
            pass
    reset = response.headers.get("x-ratelimit-reset-tokens") or ""
    match = _DURATION_RE.match(reset.strip()) if reset else None
    if match and (match.group(1) or match.group(2)):
        return float(match.group(1) or 0) * 60 + float(match.group(2) or 0)
    return None


class RateLimitedError(ModelOfflineError):
    code = "model_rate_limited"

    def __init__(self, message: str, wait_seconds: float | None) -> None:
        super().__init__(message, code="model_rate_limited")
        self.wait_seconds = wait_seconds


_groq_status_cache: dict[str, tuple[float, ServerInfo]] = {}


class GroqClient(OpenAICompatibleClient):
    """Groq's OpenAI-compatible API. Only used when the operator sets ``COUPLECARE_LLM_PROVIDER=groq``;
    conversations then leave this computer, which the UI states plainly. The safety layer, retrieval and
    output checks still run locally before and after every call."""

    def __init__(
        self,
        api_key: str | None,
        model_id: str,
        *,
        timeout: float,
        connect_timeout: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        super().__init__(GROQ_BASE_URL, model_id, timeout=timeout, connect_timeout=connect_timeout, transport=transport)
        self._api_key = (api_key or "").strip()
        # Lowered when a local fallback is configured: switching models beats a long wait for quota.
        self.max_retry_wait = GROQ_MAX_RETRY_WAIT_SECONDS

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}

    def _payload(self, messages: list[ChatMessage], params: GenerationParams, stream: bool) -> dict:
        # The output allowance is sized for the local model's tokenizer (~1 token per Bangla character). Groq's
        # tokenizers are far more efficient (measured: Bangla replies ~600 tokens), and the free tier reserves
        # max_tokens against the per-minute quota up front, so cap it to avoid needless waits.
        params = GenerationParams(
            params.temperature, min(params.max_tokens, GROQ_MAX_OUTPUT_TOKENS), params.top_p, params.stop
        )
        payload = super()._payload(messages, params, stream)
        if self.model_id.startswith("openai/gpt-oss"):
            # Reasoning models: keep the hidden reasoning out of the reply, keep it short, and leave room
            # for it in the token budget (reasoning tokens count towards max_tokens).
            payload |= {
                "include_reasoning": False,
                "reasoning_effort": "low",
                "max_tokens": params.max_tokens + GROQ_REASONING_TOKENS,
            }
        return payload

    @staticmethod
    def _raise_for(response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        if response.status_code == 401:
            raise ModelOfflineError(
                "The Groq API key was rejected. Check COUPLECARE_GROQ_API_KEY in the .env file.", code="model_auth"
            )
        if response.status_code == 429:
            raise RateLimitedError(
                "The free Groq limit has been reached for now. Wait a minute and try again, or switch back to the "
                "local model (COUPLECARE_LLM_PROVIDER=local).",
                _retry_wait_seconds(response),
            )
        if response.status_code in {400, 404, 422}:
            raise ModelResponseError(
                f"Groq rejected the request (HTTP {response.status_code}); check COUPLECARE_GROQ_MODEL."
            )
        raise ModelResponseError(f"The Groq service returned an error (HTTP {response.status_code}).")

    async def complete(self, messages: list[ChatMessage], params: GenerationParams) -> str:
        self._require_key()
        for attempt in range(GROQ_RETRIES + 1):
            try:
                return await super().complete(messages, params)
            except RateLimitedError as exc:
                if not await self._wait_for_quota(exc, attempt):
                    raise
        raise AssertionError("unreachable")  # pragma: no cover

    async def stream(self, messages: list[ChatMessage], params: GenerationParams) -> AsyncIterator[str]:
        self._require_key()
        for attempt in range(GROQ_RETRIES + 1):
            started = False
            try:
                async for delta in super().stream(messages, params):
                    started = True
                    yield delta
                return
            except RateLimitedError as exc:
                # Only retry before any text was sent; a half-streamed reply must not be restarted.
                if started or not await self._wait_for_quota(exc, attempt):
                    raise

    async def _wait_for_quota(self, exc: RateLimitedError, attempt: int) -> bool:
        wait = exc.wait_seconds
        if attempt >= GROQ_RETRIES or wait is None or wait > self.max_retry_wait:
            return False
        await asyncio.sleep(wait + 0.5)
        return True

    def _require_key(self) -> None:
        if not self._api_key:
            raise ModelOfflineError(
                "Cloud mode is on but no Groq API key is set. Add COUPLECARE_GROQ_API_KEY to the .env file.",
                code="model_auth",
            )

    async def server_info(self) -> ServerInfo:
        if not self._api_key:
            return ServerInfo(
                False, model=self.model_id, detail="No Groq API key configured (COUPLECARE_GROQ_API_KEY)."
            )
        # Cached so the UI's status polling does not spend the free-tier request quota.
        cache_key = f"{hash(self._api_key)}|{self.model_id}"
        cached = _groq_status_cache.get(cache_key)
        now = time.monotonic()
        if cached and now - cached[0] < GROQ_STATUS_TTL_SECONDS:
            return cached[1]
        info = await self._fetch_status()
        _groq_status_cache[cache_key] = (now, info)
        return info

    async def _fetch_status(self) -> ServerInfo:
        try:
            async with self._client(httpx.Timeout(5.0, connect=3.0)) as client:
                response = await client.get(f"/v1/models/{self.model_id}")
        except httpx.HTTPError:
            return ServerInfo(
                False, model=self.model_id, detail="Groq is not reachable (check the internet connection)."
            )
        if response.status_code == 401:
            return ServerInfo(False, model=self.model_id, detail="The Groq API key was rejected.")
        if response.status_code == 404:
            return ServerInfo(False, model=self.model_id, detail=f"Groq has no model named {self.model_id}.")
        if response.status_code >= 400:
            return ServerInfo(
                False, model=self.model_id, detail=f"Groq status check failed (HTTP {response.status_code})."
            )
        try:
            context = response.json().get("context_window")
        except ValueError:
            context = None
        return ServerInfo(True, model=self.model_id, context_length=context)


class FallbackChatModel:
    """Try the cloud model first; if it is rate-limited, unreachable, slow or failing, answer with the local
    model instead. The fallback is local, so it never sends data anywhere new. ``fallback_used`` and
    ``fallback_reason`` tell the caller which model produced the text (shown to the user on that reply)."""

    def __init__(self, primary: ChatModel, fallback: ChatModel) -> None:
        self.primary = primary
        self.fallback = fallback
        self.fallback_used = False
        self.fallback_reason: str | None = None

    def _switch(self, exc: Exception) -> None:
        self.fallback_used = True
        self.fallback_reason = "rate_limited" if getattr(exc, "code", None) == "model_rate_limited" else "unavailable"

    async def complete(self, messages: list[ChatMessage], params: GenerationParams) -> str:
        try:
            return await self.primary.complete(messages, params)
        except (ModelOfflineError, ModelTimeoutError, ModelResponseError) as exc:
            self._switch(exc)
            try:
                return await self.fallback.complete(messages, params)
            except (ModelOfflineError, ModelTimeoutError, ModelResponseError):
                raise exc from None

    async def stream(self, messages: list[ChatMessage], params: GenerationParams) -> AsyncIterator[str]:
        started = False
        try:
            async for delta in self.primary.stream(messages, params):
                started = True
                yield delta
            return
        except (ModelOfflineError, ModelTimeoutError, ModelResponseError) as exc:
            if started:  # never splice two models into one reply
                raise
            self._switch(exc)
            primary_error = exc
        try:
            async for delta in self.fallback.stream(messages, params):
                yield delta
        except (ModelOfflineError, ModelTimeoutError, ModelResponseError):
            raise primary_error from None

    async def server_info(self) -> ServerInfo:
        return await self.primary.server_info()

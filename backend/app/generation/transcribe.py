"""Speech-to-text through Groq's Whisper API (cloud mode only).

The audio is sent once to Groq's fixed endpoint and never stored or logged by this app. Errors are mapped to
the same user-facing error types as text generation.
"""

from __future__ import annotations

import httpx

from app.errors import ModelOfflineError, ModelResponseError, ModelTimeoutError

GROQ_TRANSCRIBE_URL = "https://api.groq.com/openai/v1/audio/transcriptions"


async def transcribe(
    *,
    api_key: str,
    model: str,
    audio: bytes,
    filename: str,
    content_type: str,
    language: str | None,
    timeout: float = 60.0,
    transport: httpx.AsyncBaseTransport | None = None,
) -> str:
    data = {"model": model, "response_format": "json", "temperature": "0"}
    if language:
        data["language"] = language  # ISO-639-1, e.g. "bn" or "en"; omitted = auto-detect
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=10.0), transport=transport) as client:
            response = await client.post(
                GROQ_TRANSCRIBE_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                data=data,
                files={"file": (filename, audio, content_type)},
            )
    except httpx.TimeoutException as exc:
        raise ModelTimeoutError("Transcription took too long. Try a shorter recording.") from exc
    except httpx.HTTPError as exc:
        raise ModelOfflineError("Groq is not reachable (check the internet connection).") from exc
    if response.status_code == 401:
        raise ModelOfflineError("The Groq API key was rejected. Check COUPLECARE_GROQ_API_KEY.", code="model_auth")
    if response.status_code == 429:
        raise ModelOfflineError(
            "The free Groq limit for voice input has been reached. Try again later or type your message.",
            code="model_rate_limited",
        )
    if response.status_code >= 400:
        raise ModelResponseError(f"Groq could not transcribe the recording (HTTP {response.status_code}).")
    try:
        text = response.json().get("text", "")
    except ValueError as exc:
        raise ModelResponseError("Groq returned an unexpected transcription response.") from exc
    return " ".join(str(text).split())

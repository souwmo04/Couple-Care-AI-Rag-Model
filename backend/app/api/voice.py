"""Voice input: speech-to-text for the message box (cloud mode only)."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.deps import get_container, get_owner
from app.core.container import Container
from app.core.schemas import TranscriptionResponse
from app.errors import AppError, BadRequestError
from app.generation.transcribe import transcribe

router = APIRouter(prefix="/api", tags=["voice"])

ALLOWED_AUDIO = {"audio/webm", "audio/ogg", "audio/mp4", "audio/mpeg", "audio/wav", "audio/x-wav", "audio/m4a"}
EXTENSIONS = {"audio/webm": "webm", "audio/ogg": "ogg", "audio/mp4": "m4a", "audio/m4a": "m4a", "audio/mpeg": "mp3",
              "audio/wav": "wav", "audio/x-wav": "wav"}  # fmt: skip


class VoiceUnavailableError(AppError):
    status_code = 503
    code = "voice_unavailable"
    retryable = False


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    language: Literal["auto", "en", "bn"] = Form("auto"),
    c: Container = Depends(get_container),
    _owner: str = Depends(get_owner),
) -> TranscriptionResponse:
    settings = c.settings
    # Voice input sends audio to Groq, so it exists only when the operator has chosen cloud mode.
    if settings.llm_provider != "groq" or settings.groq_api_key is None:
        raise VoiceUnavailableError("Voice input needs cloud mode (Groq) to be enabled on this computer.")
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in ALLOWED_AUDIO:
        raise BadRequestError("Unsupported audio format.", code="unsupported_audio")
    audio = await file.read(settings.max_audio_bytes + 1)
    if len(audio) > settings.max_audio_bytes:
        raise BadRequestError("The recording is too long. Keep it under a minute.", code="audio_too_large")
    if len(audio) < 200:
        raise BadRequestError("The recording is empty. Try again.", code="audio_empty")
    text = await transcribe(
        api_key=settings.groq_api_key.get_secret_value(),
        model=settings.groq_transcribe_model,
        audio=audio,
        filename=f"recording.{EXTENSIONS[content_type]}",
        content_type=content_type,
        language=None if language == "auto" else language,
    )
    return TranscriptionResponse(text=text)

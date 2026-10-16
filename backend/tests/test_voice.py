"""Voice input endpoint: availability, validation, size limits and Groq call (mocked)."""

from __future__ import annotations

import httpx
import pytest
from pydantic import SecretStr
from starlette.testclient import TestClient

from app.generation import transcribe as transcribe_module
from app.main import create_app
from tests.conftest import CLIENT_ID, make_container

WEBM = ("rec.webm", b"\x1aE\xdf\xa3" + b"\x00" * 2000, "audio/webm")


@pytest.fixture
def cloud_client(settings):
    cloud = settings.model_copy(update={"llm_provider": "groq", "groq_api_key": SecretStr("test-key")})
    app = create_app(cloud, make_container(cloud))
    with TestClient(app, headers={"X-Client-Id": CLIENT_ID}) as c:
        yield c


def test_voice_unavailable_in_local_mode(client) -> None:
    r = client.post("/api/transcribe", files={"file": WEBM})
    assert r.status_code == 503 and r.json()["error"]["code"] == "voice_unavailable"
    assert client.get("/api/health").json()["voice_input"] is False


def test_transcribe_sends_audio_to_groq_and_returns_text(cloud_client, monkeypatch) -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["body"] = request.read()
        return httpx.Response(200, json={"text": "  আমার স্বামী   কথা বলে না  "})

    real = transcribe_module.transcribe

    async def fake(**kwargs):
        return await real(**kwargs, transport=httpx.MockTransport(handler))

    monkeypatch.setattr("app.api.voice.transcribe", fake)
    r = cloud_client.post("/api/transcribe", files={"file": WEBM}, data={"language": "bn"})
    assert r.status_code == 200 and r.json() == {"text": "আমার স্বামী কথা বলে না"}
    assert seen["url"] == transcribe_module.GROQ_TRANSCRIBE_URL and seen["auth"] == "Bearer test-key"
    assert b'name="language"' in seen["body"] and b"whisper-large-v3" in seen["body"]
    assert cloud_client.get("/api/health").json()["voice_input"] is True


@pytest.mark.parametrize(
    ("files", "code"),
    [
        ({"file": ("x.txt", b"hello" * 100, "text/plain")}, "unsupported_audio"),
        ({"file": ("rec.webm", b"\x00" * 10, "audio/webm")}, "audio_empty"),
    ],
)
def test_transcribe_validation(cloud_client, files, code) -> None:
    r = cloud_client.post("/api/transcribe", files=files)
    assert r.status_code == 400 and r.json()["error"]["code"] == code


def test_transcribe_requires_client_id(settings) -> None:
    cloud = settings.model_copy(update={"llm_provider": "groq", "groq_api_key": SecretStr("k")})
    with TestClient(create_app(cloud, make_container(cloud))) as c:
        assert c.post("/api/transcribe", files={"file": WEBM}).status_code == 400


def test_audio_size_limit_only_raised_for_transcribe(cloud_client, monkeypatch) -> None:
    async def fake(**kwargs):
        return "ok"

    monkeypatch.setattr("app.api.voice.transcribe", fake)
    big = ("rec.webm", b"\x01" * 200_000, "audio/webm")  # above the 64 KB default, below the audio limit
    assert cloud_client.post("/api/transcribe", files={"file": big}).status_code == 200
    assert (
        cloud_client.post("/api/chat", content=b"x" * 200_000, headers={"Content-Type": "application/json"}).status_code
        == 413
    )


async def test_groq_errors_are_explained() -> None:
    from app.errors import ModelOfflineError

    with pytest.raises(ModelOfflineError) as exc:
        await transcribe_module.transcribe(api_key="k", model="m", audio=b"x", filename="a.webm", content_type="audio/webm",
                                           language=None, transport=httpx.MockTransport(lambda _: httpx.Response(429)))  # fmt: skip
    assert exc.value.code == "model_rate_limited"

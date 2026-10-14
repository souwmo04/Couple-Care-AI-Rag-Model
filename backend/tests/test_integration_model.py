"""Integration tests against a real local llama.cpp server.

Skipped by default. Run with:  pytest -m integration
They require scripts\\start-model.ps1 to be running on 127.0.0.1:18080.
"""

from __future__ import annotations

import asyncio

import pytest

from app.config import Settings
from app.generation.llm_client import ChatMessage, GenerationParams, OpenAICompatibleClient

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def client() -> OpenAICompatibleClient:
    s = Settings(_env_file=None)
    c = OpenAICompatibleClient(
        s.llm_base_url, s.default_model_id, timeout=180, connect_timeout=3, api_key_file=s.llm_api_key_file
    )
    if not asyncio.run(c.server_info()).reachable:
        pytest.skip("local model server is not running")
    return c


def test_server_reports_model(client) -> None:
    info = asyncio.run(client.server_info())
    assert info.reachable and info.model


def test_generates_english(client) -> None:
    out = asyncio.run(client.complete([ChatMessage("user", "Reply with one short sentence about listening.")],
                                      GenerationParams(max_tokens=60, temperature=0.2)))  # fmt: skip
    assert out.strip() and "<think>" not in out


def test_generates_bangla_script(client) -> None:
    out = asyncio.run(client.complete(
        [ChatMessage("system", "Respond only in Bangla using Bengali script."),
         ChatMessage("user", "সম্পর্কে ভালো যোগাযোগের একটি উপায় এক বাক্যে বলুন।")],
        GenerationParams(max_tokens=80, temperature=0.2)))  # fmt: skip
    assert any("ঀ" <= ch <= "৿" for ch in out)


def test_streaming(client) -> None:
    async def collect() -> str:
        return "".join(
            [t async for t in client.stream([ChatMessage("user", "Say hello.")], GenerationParams(max_tokens=20))]
        )

    assert asyncio.run(collect()).strip()

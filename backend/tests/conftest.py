"""Shared test fixtures.

Tests never download models or call a real model server:
* embeddings use the deterministic ``HashingEmbedder``;
* the generator is ``FakeChatModel`` (or an httpx ``MockTransport`` in client tests);
* every test gets its own temporary data, index and user directories.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.core.container import Container
from app.errors import ModelOfflineError
from app.generation.llm_client import ChatMessage, GenerationParams, ServerInfo
from app.ingestion.pipeline import run_ingestion
from app.main import create_app
from app.retrieval.embeddings import EmbedderHolder, HashingEmbedder

CORPUS_DIR = Path(__file__).parent / "fixtures" / "corpus"
CLIENT_ID = "test-client-0123456789abcdef"
OTHER_CLIENT_ID = "other-client-0123456789abcdef"


class FakeChatModel:
    """Deterministic stand-in for the llama.cpp server."""

    def __init__(
        self,
        answer: str = "Here is some thoughtful guidance [S1].",
        *,
        online: bool = True,
        error: Exception | None = None,
    ) -> None:
        self.answer = answer
        self.online = online
        self.error = error
        self.calls: list[list[ChatMessage]] = []
        self.params: list[GenerationParams] = []

    async def complete(self, messages: list[ChatMessage], params: GenerationParams) -> str:
        self.calls.append(messages)
        self.params.append(params)
        if self.error:
            raise self.error
        if not self.online:
            raise ModelOfflineError("The local model server is not running or not reachable.")
        return self.answer

    async def stream(self, messages: list[ChatMessage], params: GenerationParams) -> AsyncIterator[str]:
        self.calls.append(messages)
        if not self.online:
            raise ModelOfflineError("The local model server is not running or not reachable.")
        for word in self.answer.split(" "):
            yield word + " "

    async def server_info(self) -> ServerInfo:
        if self.online:
            return ServerInfo(True, model="fake-model", context_length=4096)
        return ServerInfo(False, detail="Model server is not running or not reachable.")


def make_settings(tmp_path: Path, **overrides) -> Settings:
    data_dir = tmp_path / "data"
    raw_dir = data_dir / "raw"
    metadata_dir = data_dir / "metadata"
    raw_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(CORPUS_DIR, raw_dir / "corpus", dirs_exist_ok=True)
    manifest = json.loads((CORPUS_DIR / "manifest.json").read_text(encoding="utf-8"))
    (metadata_dir / "sources.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    repo_directory = Path(__file__).resolve().parents[2] / "data" / "metadata" / "support_directory.json"
    shutil.copy(repo_directory, metadata_dir / "support_directory.json")
    values = dict(
        environment="test",
        data_dir=data_dir,
        raw_dir=raw_dir,
        metadata_dir=metadata_dir,
        index_dir=tmp_path / "indexes",
        user_dir=tmp_path / "user",
        embedding_backend="hashing",
        # The hashing embedder is not semantic; give it a permissive calibration for tests.
        dense_score_floor=0.0,
        dense_score_ceiling=0.6,
    )
    values.update(overrides)
    return Settings(_env_file=None, **values)


def build_test_index(settings: Settings) -> None:
    run_ingestion(
        manifest_path=settings.manifest_path,
        raw_dir=settings.raw_dir,
        index_dir=settings.index_dir,
        embedder=HashingEmbedder(),
        chunk_size=600,
        overlap=100,
        max_bytes=settings.max_ingest_file_bytes,
    )


def make_container(settings: Settings, llm: FakeChatModel | None = None, *, with_index: bool = True) -> Container:
    if with_index:
        build_test_index(settings)
    holder = EmbedderHolder("hashing", "hashing", "cpu")
    holder.set_embedder(HashingEmbedder(), "fallback")
    return Container(settings, llm=llm or FakeChatModel(), embedder=holder, load_embedder=False)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return make_settings(tmp_path)


@pytest.fixture
def fake_llm() -> FakeChatModel:
    return FakeChatModel()


@pytest.fixture
def container(settings: Settings, fake_llm: FakeChatModel) -> Container:
    return make_container(settings, fake_llm)


@pytest.fixture
def client(settings: Settings, container: Container):
    app = create_app(settings, container)
    with TestClient(app, headers={"X-Client-Id": CLIENT_ID}) as test_client:
        yield test_client

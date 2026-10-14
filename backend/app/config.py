"""Application configuration.

Two layers of configuration exist on purpose:

* ``Settings`` — deployment configuration read from environment variables / ``.env``.
  Only the operator (the person running the app) can change these. They include
  anything security-sensitive: bind address, model-server URL, filesystem paths.
* ``RuntimeSettings`` — user-adjustable preferences exposed through ``/api/settings``.
  Every field is bounded so the UI cannot push the system outside safe limits, and
  none of them can point the backend at arbitrary hosts, files, or commands.
"""

from __future__ import annotations

import ipaddress
import os
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]

# Keep downloaded models (Hugging Face / sentence-transformers) inside the project folder rather
# than the user profile on the system drive. Set before any Hugging Face library is imported;
# an explicit HF_HOME from the environment still wins.
os.environ.setdefault("HF_HOME", str(REPO_ROOT / ".cache" / "huggingface"))


class ModelProfile(BaseModel):
    """A generation model the operator has configured and may expose to the UI."""

    id: str = Field(pattern=r"^[A-Za-z0-9._:-]{1,80}$")
    display_name: str
    family: Literal["qwen3", "gemma3", "llama3", "generic"] = "generic"
    revision: str = "unknown"
    license: str = "unknown"
    context_length: int = Field(default=4096, ge=512, le=32768)


DEFAULT_MODELS = [
    ModelProfile(
        id="qwen3-4b-instruct-2507",
        display_name="Qwen3 4B Instruct 2507 (GGUF, Q4_K_M)",
        family="qwen3",
        revision="unsloth/Qwen3-4B-Instruct-2507-GGUF@a06e946b (base Qwen/Qwen3-4B-Instruct-2507@cdbee75f)",
        license="Apache-2.0",
        context_length=8192,
    ),
]


def _is_loopback_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    host = parsed.hostname
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class Settings(BaseSettings):
    """Operator-level configuration. Environment prefix: ``COUPLECARE_``."""

    model_config = SettingsConfigDict(
        env_prefix="COUPLECARE_",
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "CoupleCare AI"
    environment: Literal["development", "test", "production"] = "development"
    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]
    max_request_bytes: int = 64 * 1024
    max_message_chars: int = 4000
    log_level: str = "INFO"
    log_message_content: bool = False

    # Local generation server (llama.cpp, OpenAI-compatible API)
    # 18080 avoids the 8001-8100 range that Windows (Hyper-V/WSL) often reserves.
    llm_base_url: str = "http://127.0.0.1:18080"
    llm_api_key_file: Path = REPO_ROOT / "models" / "server.key"
    llm_timeout_seconds: float = 120.0
    llm_connect_timeout_seconds: float = 3.0
    models: list[ModelProfile] = DEFAULT_MODELS
    default_model_id: str = "qwen3-4b-instruct-2507"

    # Retrieval
    embedding_model: str = "intfloat/multilingual-e5-small"
    # The semantic safety classifier's thresholds were tuned and held-out-tested with this model, so it
    # stays fixed even if the retrieval embedder is changed (e.g. to multilingual-e5-base).
    safety_embedding_model: str = "intfloat/multilingual-e5-small"
    embedding_device: Literal["cpu", "cuda"] = "cpu"
    embedding_backend: Literal["sentence-transformers", "hashing"] = "sentence-transformers"
    reranker_model: str | None = None
    # Relevance calibration for the embedding model (see docs/retrieval-calibration.md).
    dense_score_floor: float = 0.75
    dense_score_ceiling: float = 0.90
    bm25_saturation: float = 6.0

    # Paths — always resolved inside the repository.
    data_dir: Path = REPO_ROOT / "data"
    raw_dir: Path = REPO_ROOT / "data" / "raw"
    metadata_dir: Path = REPO_ROOT / "data" / "metadata"
    index_dir: Path = REPO_ROOT / "artifacts" / "indexes"
    user_dir: Path = REPO_ROOT / "data" / "user"

    # Ingestion limits
    max_ingest_file_bytes: int = 5 * 1024 * 1024
    chunk_size_chars: int = 900
    chunk_overlap_chars: int = 150

    # Evaluation traces are never stored unless explicitly enabled.
    store_eval_traces: bool = False

    @field_validator("llm_base_url")
    @classmethod
    def _llm_must_be_local(cls, value: str) -> str:
        if not _is_loopback_url(value):
            raise ValueError(
                "COUPLECARE_LLM_BASE_URL must point to a loopback address (127.0.0.1, ::1 or "
                "localhost). Remote inference is not supported by default because it would send "
                "conversations off this device."
            )
        return value.rstrip("/")

    @field_validator("host")
    @classmethod
    def _warn_public_bind(cls, value: str) -> str:
        if value not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError(
                "COUPLECARE_HOST must be a loopback address. Binding to a public interface would "
                "expose private conversations to the network."
            )
        return value

    @property
    def sqlite_path(self) -> Path:
        return self.user_dir / "conversations.sqlite3"

    @property
    def runtime_settings_path(self) -> Path:
        return self.user_dir / "settings.json"

    @property
    def support_directory_path(self) -> Path:
        return self.metadata_dir / "support_directory.json"

    @property
    def manifest_path(self) -> Path:
        return self.metadata_dir / "sources.json"

    def model_ids(self) -> list[str]:
        return [m.id for m in self.models]

    def get_model(self, model_id: str) -> ModelProfile | None:
        return next((m for m in self.models if m.id == model_id), None)


class RuntimeSettings(BaseModel):
    """User-adjustable settings. All values are bounded; unknown fields are rejected."""

    model_config = {"extra": "forbid"}

    model_id: str = "qwen3-4b-instruct-2507"
    temperature: float = Field(default=0.6, ge=0.0, le=1.2)
    max_output_tokens: int = Field(default=700, ge=64, le=1536)
    retrieval_top_k: int = Field(default=4, ge=1, le=8)
    dense_top_k: int = Field(default=20, ge=1, le=50)
    bm25_top_k: int = Field(default=20, ge=1, le=50)
    relevance_threshold: float = Field(default=0.35, ge=0.0, le=1.0)
    rerank_enabled: bool = False
    query_expansion_enabled: bool = True
    history_turns: int = Field(default=6, ge=0, le=12)
    persistence_enabled: bool = False
    # Region for the verified support directory. Never inferred from language.
    support_region: Literal["unspecified", "BD", "IN", "GB", "US"] = "unspecified"


@lru_cache
def get_settings() -> Settings:
    return Settings()

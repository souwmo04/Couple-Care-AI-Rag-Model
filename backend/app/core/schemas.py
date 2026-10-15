"""Pydantic request/response schemas shared by the API layer."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator

CONVERSATION_ID_PATTERN = r"^[0-9a-f]{32}$"


class LanguageCode(StrEnum):
    AUTO = "auto"
    EN = "en"
    BN = "bn"
    BANGLISH = "banglish"


class DetectedLanguage(StrEnum):
    EN = "en"
    BN = "bn"
    BANGLISH = "banglish"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class RelationshipStage(StrEnum):
    DATING = "dating"
    ENGAGED = "engaged"
    MARRIED = "married"
    UNSPECIFIED = "unspecified"


class SafetyLevel(StrEnum):
    """Client-facing safety status. Raw classifier details are never exposed."""

    NONE = "none"
    CAUTION = "caution"
    SUPPORT = "support"
    URGENT = "urgent"
    DECLINED = "declined"


# --------------------------------------------------------------------------- chat


class ChatRequest(BaseModel):
    model_config = {"extra": "forbid"}

    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = Field(default=None, pattern=CONVERSATION_ID_PATTERN)
    language: LanguageCode = LanguageCode.AUTO
    relationship_stage: RelationshipStage = RelationshipStage.UNSPECIFIED
    regenerate: bool = False

    @field_validator("message")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message cannot be empty.")
        return value


class SourceCard(BaseModel):
    citation_id: str
    document_id: str
    chunk_id: str
    title: str
    organization: str | None = None
    excerpt: str
    language: str
    topic: str
    url: str | None = None
    license: str | None = None
    section: str | None = None
    synthetic: bool = False
    score: float
    cited: bool = False


class SupportResource(BaseModel):
    name: str
    description: str
    contact: str | None = None
    url: str | None = None
    region: str
    verified_on: str
    source_url: str


class SafetyStatus(BaseModel):
    level: SafetyLevel = SafetyLevel.NONE
    message: str | None = None
    resources: list[SupportResource] = []


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    answer: str
    detected_language: DetectedLanguage
    response_language: str
    sources: list[SourceCard]
    grounded: bool
    safety: SafetyStatus
    needs_clarification: bool
    model_id: str | None
    generated: bool = Field(description="True only when the text came from the local language model.")
    duration_ms: int


# --------------------------------------------------------------------------- conversations


class StoredMessage(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime
    sources: list[SourceCard] = []
    safety: SafetyStatus | None = None
    language: str | None = None
    grounded: bool | None = None
    generated: bool | None = None


class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    relationship_stage: RelationshipStage
    language: str


class ConversationDetail(ConversationSummary):
    messages: list[StoredMessage]


class ConversationList(BaseModel):
    persistence_enabled: bool
    items: list[ConversationSummary]
    total: int


class DeleteAllRequest(BaseModel):
    model_config = {"extra": "forbid"}
    confirm: Literal["DELETE ALL"]


class FeedbackRequest(BaseModel):
    model_config = {"extra": "forbid"}
    rating: Literal["helpful", "not_helpful"]


# --------------------------------------------------------------------------- health / model


class ModelStatus(BaseModel):
    configured: bool
    reachable: bool
    model_id: str | None
    display_name: str | None
    server_model: str | None = None
    context_length: int | None = None
    license: str | None = None
    revision: str | None = None
    detail: str | None = None
    checked_at: datetime
    # "groq" = cloud mode: messages leave this computer.
    provider: Literal["local", "groq"] = "local"


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    model_server: Literal["online", "offline"]
    provider: Literal["local", "groq"] = "local"
    index: Literal["ready", "missing", "building", "error"]
    embeddings: Literal["ready", "loading", "unavailable", "fallback"]


# --------------------------------------------------------------------------- knowledge


class RetrievalTestRequest(BaseModel):
    model_config = {"extra": "forbid"}
    query: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)
    mode: Literal["hybrid", "dense", "bm25"] = "hybrid"
    language: LanguageCode = LanguageCode.AUTO
    topic: str | None = Field(default=None, max_length=60)


class RetrievedPassage(BaseModel):
    rank: int
    chunk_id: str
    document_id: str
    title: str
    text: str
    language: str
    topic: str
    section: str | None
    score: float
    dense_rank: int | None
    bm25_rank: int | None
    above_threshold: bool


class RetrievalTestResponse(BaseModel):
    query: str
    normalized_query: str
    expanded_terms: list[str]
    detected_language: DetectedLanguage
    mode: str
    passages: list[RetrievedPassage]
    duration_ms: int
    dense_available: bool

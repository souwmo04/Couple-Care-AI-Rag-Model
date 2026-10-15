"""Health and model-status endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from app import __version__
from app.api.deps import get_container
from app.core.container import Container
from app.core.schemas import HealthResponse, ModelStatus

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(c: Container = Depends(get_container)) -> HealthResponse:
    info = await c.llm().server_info()
    index = c.index_state()
    embeddings = c.embedder.state
    degraded = not info.reachable or index != "ready" or embeddings != "ready"
    return HealthResponse(
        status="degraded" if degraded else "ok",
        version=__version__,
        model_server="online" if info.reachable else "offline",
        provider=c.settings.llm_provider,
        index=index,  # type: ignore[arg-type]
        embeddings=embeddings,  # type: ignore[arg-type]
    )


@router.get("/model/status", response_model=ModelStatus)
async def model_status(c: Container = Depends(get_container)) -> ModelStatus:
    info = await c.llm().server_info()
    if c.settings.llm_provider == "groq":
        return ModelStatus(
            configured=c.settings.groq_api_key is not None,
            reachable=info.reachable,
            model_id=c.settings.groq_model,
            display_name=f"{c.settings.groq_model} via Groq (cloud)",
            server_model=info.model,
            context_length=info.context_length,
            license=None,
            revision=None,
            detail=info.detail,
            checked_at=datetime.now(UTC),
            provider="groq",
        )
    runtime = c.settings_store.get()
    profile = c.settings.get_model(runtime.model_id)
    return ModelStatus(
        configured=profile is not None,
        reachable=info.reachable,
        model_id=profile.id if profile else None,
        display_name=profile.display_name if profile else None,
        server_model=info.model,
        context_length=info.context_length or (profile.context_length if profile else None),
        license=profile.license if profile else None,
        revision=profile.revision if profile else None,
        detail=info.detail,
        checked_at=datetime.now(UTC),
    )

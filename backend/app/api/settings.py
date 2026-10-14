"""Runtime settings endpoints. Only bounded, validated fields can be changed."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app import __version__
from app.api.deps import get_container
from app.config import RuntimeSettings
from app.core.container import Container
from app.core.prompts import PROMPT_VERSION

router = APIRouter(prefix="/api/settings", tags=["settings"])


class ModelOption(BaseModel):
    id: str
    display_name: str
    license: str
    context_length: int


class SettingsResponse(BaseModel):
    values: RuntimeSettings
    models: list[ModelOption]
    embedding_model: str
    embedding_device: str
    reranker_configured: bool
    support_regions: dict[str, str]
    limits: dict[str, dict[str, float]]
    about: dict[str, str | None]


class SettingsUpdate(BaseModel):
    model_config = {"extra": "forbid"}

    model_id: str | None = None
    temperature: float | None = None
    max_output_tokens: int | None = None
    retrieval_top_k: int | None = None
    dense_top_k: int | None = None
    bm25_top_k: int | None = None
    relevance_threshold: float | None = None
    rerank_enabled: bool | None = None
    query_expansion_enabled: bool | None = None
    history_turns: int | None = None
    persistence_enabled: bool | None = None
    support_region: str | None = None


def _limits() -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for name, field in RuntimeSettings.model_fields.items():
        bounds: dict[str, float] = {}
        for meta in field.metadata:
            if getattr(meta, "ge", None) is not None:
                bounds["min"] = float(meta.ge)
            if getattr(meta, "le", None) is not None:
                bounds["max"] = float(meta.le)
        if bounds:
            out[name] = bounds
    return out


def _response(c: Container) -> SettingsResponse:
    bundle = c.retriever.bundle
    return SettingsResponse(
        values=c.settings_store.get(),
        models=[
            ModelOption(id=m.id, display_name=m.display_name, license=m.license, context_length=m.context_length)
            for m in c.settings.models
        ],
        embedding_model=c.settings.embedding_model,
        embedding_device=c.settings.embedding_device,
        reranker_configured=c.reranker.configured,
        support_regions={k: v.get("label", k) for k, v in c.support_directory.get("regions", {}).items()},
        limits=_limits(),
        about={
            "app_version": __version__,
            "prompt_version": PROMPT_VERSION,
            "knowledge_base_version": bundle.version if bundle else None,
        },
    )


@router.get("", response_model=SettingsResponse)
async def get_settings(c: Container = Depends(get_container)) -> SettingsResponse:
    return _response(c)


@router.put("", response_model=SettingsResponse)
async def update_settings(body: SettingsUpdate, c: Container = Depends(get_container)) -> SettingsResponse:
    c.settings_store.update(body.model_dump(exclude_none=True))
    return _response(c)


@router.post("/reset", response_model=SettingsResponse)
async def reset_settings(c: Container = Depends(get_container)) -> SettingsResponse:
    c.settings_store.reset()
    return _response(c)

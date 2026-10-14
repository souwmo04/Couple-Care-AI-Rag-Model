"""Knowledge-base endpoints: real index statistics, source browsing, retrieval tests, rebuild.

All numbers come from the active index bundle on disk. Nothing is hardcoded.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Path, Query
from pydantic import BaseModel

from app.api.deps import get_container
from app.core.container import Container
from app.core.schemas import RetrievalTestRequest, RetrievalTestResponse, RetrievedPassage
from app.errors import ConflictError, IndexUnavailableError, NotFoundError
from app.ingestion.loaders import ExtractionError
from app.ingestion.pipeline import run_ingestion
from app.retrieval.retriever import RetrievalParams

log = logging.getLogger("couplecare.knowledge")
router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


class KnowledgeStats(BaseModel):
    available: bool
    version: str | None = None
    built_at: str | None = None
    documents: int = 0
    passages: int = 0
    languages: dict[str, int] = {}
    topics: dict[str, int] = {}
    synthetic_documents: int = 0
    embedding_model: str | None = None
    embedding_dimension: int | None = None
    dense_index: bool = False
    dense_active: bool = False
    embedder_state: str
    embedder_error: str | None = None
    chunk_size: int | None = None
    chunk_overlap: int | None = None
    ingestion_errors: int = 0
    health: str
    rebuild: dict


class SourceSummary(BaseModel):
    document_id: str
    title: str
    organization: str | None
    language: str
    topic: str
    url: str | None
    license: str | None
    permission: str | None
    synthetic: bool
    passages: int


class SourcePage(BaseModel):
    items: list[SourceSummary]
    total: int
    page: int
    page_size: int


class SourceDetail(SourceSummary):
    path: str | None = None
    sha256: str | None = None
    sections: list[dict]


def _rebuild_info(c: Container) -> dict:
    r = c.rebuild
    return {"status": r.status, "started_at": r.started_at, "finished_at": r.finished_at, "message": r.message,
            "version": r.version}


@router.get("/stats", response_model=KnowledgeStats)
async def stats(c: Container = Depends(get_container)) -> KnowledgeStats:
    bundle = c.retriever.bundle
    dense_active = c.retriever.dense_available()
    if bundle is None:
        return KnowledgeStats(available=False, embedder_state=c.embedder.state, embedder_error=c.embedder.error,
                              health="missing" if not c.index_error else "error", rebuild=_rebuild_info(c))
    meta = bundle.meta
    errors = len(bundle.report.get("errors", []))
    if dense_active:
        health = "healthy"
    elif bundle.vectors is None:
        health = "lexical_only"
    else:
        health = "dense_unavailable"
    synthetic_docs = len({p.document_id for p in bundle.passages if p.synthetic})
    return KnowledgeStats(
        available=True, version=bundle.version, built_at=meta.get("built_at"),
        documents=len({p.document_id for p in bundle.passages}), passages=len(bundle.passages),
        languages=meta.get("languages", {}), topics=meta.get("topics", {}), synthetic_documents=synthetic_docs,
        embedding_model=meta.get("embedding_model"), embedding_dimension=meta.get("embedding_dimension"),
        dense_index=bundle.vectors is not None, dense_active=dense_active, embedder_state=c.embedder.state,
        embedder_error=c.embedder.error, chunk_size=meta.get("chunk_size"), chunk_overlap=meta.get("chunk_overlap"),
        ingestion_errors=errors, health=health, rebuild=_rebuild_info(c),
    )


def _documents(c: Container) -> dict[str, SourceSummary]:
    bundle = c.retriever.bundle
    if bundle is None:
        return {}
    report_docs = {d["document_id"]: d for d in bundle.report.get("documents", [])}
    docs: dict[str, SourceSummary] = {}
    for p in bundle.passages:
        if p.document_id in docs:
            docs[p.document_id].passages += 1
            continue
        docs[p.document_id] = SourceSummary(
            document_id=p.document_id, title=p.title, organization=p.organization or p.author,
            language=report_docs.get(p.document_id, {}).get("language") or p.language, topic=p.topic, url=p.url,
            license=p.license, permission=(p.extra or {}).get("permission"), synthetic=p.synthetic, passages=1,
        )
    return docs


@router.get("/sources", response_model=SourcePage)
async def sources(
    q: str | None = Query(default=None, max_length=100),
    language: str | None = Query(default=None, max_length=20),
    topic: str | None = Query(default=None, max_length=60),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
    c: Container = Depends(get_container),
) -> SourcePage:
    items = list(_documents(c).values())
    if q:
        needle = q.lower()
        items = [i for i in items if needle in i.title.lower() or needle in (i.organization or "").lower()
                 or needle in i.document_id]
    if language:
        items = [i for i in items if i.language == language]
    if topic:
        items = [i for i in items if i.topic == topic]
    items.sort(key=lambda i: (i.topic, i.language, i.title))
    start = (page - 1) * page_size
    return SourcePage(items=items[start : start + page_size], total=len(items), page=page, page_size=page_size)


@router.get("/sources/{document_id}", response_model=SourceDetail)
async def source_detail(
    document_id: str = Path(pattern=r"^[a-z0-9][a-z0-9_-]{2,80}$"), c: Container = Depends(get_container)
) -> SourceDetail:
    docs = _documents(c)
    summary = docs.get(document_id)
    bundle = c.retriever.bundle
    if summary is None or bundle is None:
        raise NotFoundError("Source not found in the active index.")
    report = next((d for d in bundle.report.get("documents", []) if d["document_id"] == document_id), {})
    sections = [
        {"chunk_id": p.chunk_id, "section": p.section, "text": p.text, "language": p.language}
        for p in bundle.passages if p.document_id == document_id
    ]
    return SourceDetail(**summary.model_dump(), path=report.get("path"), sha256=report.get("sha256"), sections=sections)


@router.get("/errors")
async def ingestion_errors(c: Container = Depends(get_container)) -> dict:
    bundle = c.retriever.bundle
    last_failure = c.rebuild.message if c.rebuild.status == "failed" else None
    return {
        "version": bundle.version if bundle else None,
        "errors": bundle.report.get("errors", []) if bundle else [],
        "last_rebuild_failure": last_failure,
    }


@router.post("/search", response_model=RetrievalTestResponse)
async def retrieval_test(body: RetrievalTestRequest, c: Container = Depends(get_container)) -> RetrievalTestResponse:
    if c.retriever.bundle is None:
        raise IndexUnavailableError("No knowledge index is available. Build it from the Knowledge page.")
    runtime = c.settings_store.get()
    params = RetrievalParams(
        final_k=body.top_k, dense_k=max(runtime.dense_top_k, body.top_k), bm25_k=max(runtime.bm25_top_k, body.top_k),
        threshold=runtime.relevance_threshold, rerank=runtime.rerank_enabled, expand=runtime.query_expansion_enabled,
        mode=body.mode, language_filter=None if body.language.value == "auto" else body.language.value,
        topic_filter=body.topic,
    )
    result = await asyncio.to_thread(c.retriever.search, body.query, params)
    return RetrievalTestResponse(
        query=body.query, normalized_query=result.normalized_query, expanded_terms=result.expanded_terms,
        detected_language=result.analysis.detected, mode=result.mode, duration_ms=result.duration_ms,
        dense_available=result.dense_available,
        passages=[
            RetrievedPassage(
                rank=i + 1, chunk_id=it.passage.chunk_id, document_id=it.passage.document_id, title=it.passage.title,
                text=it.passage.text, language=it.passage.language, topic=it.passage.topic, section=it.passage.section,
                score=round(it.hit.relevance, 4), dense_rank=it.hit.dense_rank, bm25_rank=it.hit.bm25_rank,
                above_threshold=it.above_threshold,
            )
            for i, it in enumerate(result.items)
        ],
    )


def _run_rebuild(c: Container) -> None:
    state = c.rebuild
    settings = c.settings
    embedder = c.embedder.get()
    try:
        report = run_ingestion(
            manifest_path=settings.manifest_path, raw_dir=settings.raw_dir, index_dir=settings.index_dir,
            embedder=embedder, chunk_size=settings.chunk_size_chars, overlap=settings.chunk_overlap_chars,
            max_bytes=settings.max_ingest_file_bytes,
        )
        c.reload_index()
        state.status = "succeeded"
        state.version = report.version
        dense_note = "" if report.dense else " Dense vectors were not built because no embedding model was available."
        state.message = (f"Indexed {report.passages} passages from {report.documents_ok} documents; "
                         f"{report.documents_failed} failed.{dense_note}")
    except ExtractionError as exc:
        state.status, state.message = "failed", str(exc)
    except Exception as exc:  # noqa: BLE001
        log.exception("rebuild_failed")
        state.status, state.message = "failed", f"Rebuild failed ({type(exc).__name__}). The previous index is still active."
    finally:
        state.finished_at = datetime.now(UTC).isoformat()


@router.post("/rebuild", status_code=202)
async def rebuild(c: Container = Depends(get_container)) -> dict:
    """Rebuild the index from the configured manifest only (no paths or URLs accepted)."""
    if c.embedder.state == "loading":
        raise ConflictError("The embedding model is still loading. Try again in a moment.")
    state = c.rebuild
    if not state.lock.acquire(blocking=False):
        raise ConflictError("A rebuild is already running.")
    try:
        if state.status == "running":
            raise ConflictError("A rebuild is already running.")
        state.status, state.started_at, state.finished_at, state.message = (
            "running", datetime.now(UTC).isoformat(), None, None)
    finally:
        state.lock.release()
    threading.Thread(target=_run_rebuild, args=(c,), name="index-rebuild", daemon=True).start()
    return {"status": "running"}


@router.get("/rebuild")
async def rebuild_status(c: Container = Depends(get_container)) -> dict:
    return _rebuild_info(c)

"""Manifest-driven ingestion pipeline.

Only documents explicitly listed in ``data/metadata/sources.json`` are ingested, and only
from inside ``data/raw``. There is no crawler and no URL fetching: adding a source is a
deliberate act by the operator, who records its licence/permission in the manifest.

Steps: read manifest → validate path/type/size → extract → strip boilerplate → normalize
→ detect language → chunk → attach metadata → embed → build FAISS + BM25 → validate →
write a new version → activate atomically → record provenance and errors.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from app.core.language import analyze_language, normalize_text
from app.ingestion.chunking import chunk_text
from app.ingestion.loaders import ExtractionError, extract_sections, resolve_inside, validate_file
from app.retrieval.embeddings import Embedder
from app.retrieval.index_store import activate, new_version_name, prune_old_versions, write_bundle
from app.retrieval.passages import Passage
from app.retrieval.vector_store import VectorStore

log = logging.getLogger("couplecare.ingestion")

TOPICS = (
    "communication",
    "trust_jealousy",
    "emotional_distance",
    "dating_commitment",
    "marriage_family",
    "boundaries_expectations",
    "conflict_resolution",
    "healthy_separation",
    "safety",
    "general",
)

BOILERPLATE_RE = re.compile(
    r"^(share (this|on)|follow us|subscribe|cookie|accept all|sign up|advertisement|related articles?|"
    r"read more|click here|all rights reserved|©)",
    re.IGNORECASE,
)


class SourceEntry(BaseModel):
    model_config = {"extra": "forbid"}

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{2,80}$")
    path: str = Field(min_length=1, max_length=260)
    title: str = Field(min_length=1, max_length=300)
    organization: str | None = None
    author: str | None = None
    url: str | None = Field(default=None, pattern=r"^https://")
    published: str | None = None
    retrieved: str | None = None
    license: str = Field(min_length=1, description="Licence or permission basis. Required.")
    permission: Literal["project-authored", "open-licence", "public-domain", "written-permission"]
    language: Literal["en", "bn", "banglish", "mixed", "auto"] = "auto"
    topic: Literal[TOPICS]  # type: ignore[valid-type]
    synthetic: bool = False
    translation_of: str | None = None
    notes: str | None = None


class SourceManifest(BaseModel):
    model_config = {"extra": "forbid"}
    version: int = 1
    documents: list[SourceEntry]


@dataclass
class IngestionReport:
    version: str
    started_at: str
    finished_at: str | None = None
    documents_ok: int = 0
    documents_failed: int = 0
    passages: int = 0
    errors: list[dict] = field(default_factory=list)
    documents: list[dict] = field(default_factory=list)
    dense: bool = False
    embedding_model: str | None = None

    def to_dict(self) -> dict:
        return self.__dict__.copy()


def load_manifest(path: Path) -> SourceManifest:
    try:
        return SourceManifest.model_validate_json(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ExtractionError(f"Source manifest not found at {path.name}") from exc
    except ValidationError as exc:
        raise ExtractionError(f"Source manifest is invalid: {exc.error_count()} problem(s)") from exc


def _clean(text: str) -> str:
    lines = [ln for ln in normalize_text(text).split("\n") if not BOILERPLATE_RE.match(ln.strip())]
    return "\n".join(lines).strip()


def _passage_language(declared: str, text: str) -> str:
    if declared != "auto":
        return declared
    detected = analyze_language(text).detected.value
    return detected if detected != "unknown" else "en"


def build_passages(
    manifest: SourceManifest, raw_dir: Path, *, max_bytes: int, chunk_size: int, overlap: int, report: IngestionReport
) -> list[Passage]:
    passages: list[Passage] = []
    seen_ids: set[str] = set()
    retrieved_default = date.today().isoformat()
    for entry in manifest.documents:
        if entry.id in seen_ids:
            report.errors.append({"document_id": entry.id, "stage": "manifest", "error": "Duplicate document id"})
            report.documents_failed += 1
            continue
        seen_ids.add(entry.id)
        try:
            path = resolve_inside(raw_dir, entry.path)
            validate_file(path, max_bytes)
            sections = extract_sections(path)
        except ExtractionError as exc:
            report.errors.append({"document_id": entry.id, "path": entry.path, "stage": "extract", "error": str(exc)})
            report.documents_failed += 1
            continue

        doc_passages = 0
        for s_index, section in enumerate(sections):
            text = _clean(section.text)
            if not text:
                continue
            for c_index, chunk in enumerate(chunk_text(text, chunk_size, overlap)):
                if len(chunk) < 40:  # fragments too short to be useful evidence
                    continue
                chunk_id = f"{entry.id}::{s_index:03d}-{c_index:03d}"
                passages.append(
                    Passage(
                        chunk_id=chunk_id,
                        document_id=entry.id,
                        text=chunk,
                        title=entry.title,
                        language=_passage_language(entry.language, chunk),
                        topic=entry.topic,
                        organization=entry.organization,
                        author=entry.author,
                        url=entry.url,
                        published=entry.published,
                        retrieved=entry.retrieved or (retrieved_default if entry.url else None),
                        license=entry.license,
                        section=section.heading,
                        synthetic=entry.synthetic,
                        translation_of=entry.translation_of,
                        extra={"permission": entry.permission},
                    )
                )
                doc_passages += 1
        if doc_passages == 0:
            report.errors.append(
                {
                    "document_id": entry.id,
                    "path": entry.path,
                    "stage": "chunk",
                    "error": "No usable text after cleaning",
                }
            )
            report.documents_failed += 1
            continue
        report.documents_ok += 1
        report.documents.append(
            {
                "document_id": entry.id,
                "title": entry.title,
                "path": entry.path,
                "passages": doc_passages,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "license": entry.license,
                "permission": entry.permission,
                "synthetic": entry.synthetic,
                "language": entry.language,
                "topic": entry.topic,
                "url": entry.url,
                "organization": entry.organization,
            }
        )
    return passages


def run_ingestion(
    *,
    manifest_path: Path,
    raw_dir: Path,
    index_dir: Path,
    embedder: Embedder | None,
    chunk_size: int,
    overlap: int,
    max_bytes: int,
) -> IngestionReport:
    version = new_version_name()
    report = IngestionReport(version=version, started_at=datetime.now(UTC).isoformat())
    started = time.perf_counter()

    manifest = load_manifest(manifest_path)
    passages = build_passages(
        manifest, raw_dir, max_bytes=max_bytes, chunk_size=chunk_size, overlap=overlap, report=report
    )
    if not passages:
        report.finished_at = datetime.now(UTC).isoformat()
        raise ExtractionError("Ingestion produced no passages; the active index was left unchanged")

    vectors: VectorStore | None = None
    if embedder is not None:
        texts = [f"{p.title}. {p.section + '. ' if p.section else ''}{p.text}" for p in passages]
        matrix = embedder.embed_passages(texts)
        if matrix.shape[0] != len(passages):
            raise ExtractionError("Embedding count does not match passage count")
        vectors = VectorStore(matrix.shape[1])
        vectors.add(matrix)
        report.dense = True
        report.embedding_model = embedder.name

    report.passages = len(passages)
    report.finished_at = datetime.now(UTC).isoformat()
    languages: dict[str, int] = {}
    topics: dict[str, int] = {}
    for p in passages:
        languages[p.language] = languages.get(p.language, 0) + 1
        topics[p.topic] = topics.get(p.topic, 0) + 1
    meta = {
        "version": version,
        "built_at": report.finished_at,
        "build_seconds": round(time.perf_counter() - started, 2),
        "documents": report.documents_ok,
        "passages": len(passages),
        "languages": languages,
        "topics": topics,
        "embedding_model": embedder.name if embedder else None,
        "embedding_semantic": bool(embedder and embedder.is_semantic),
        "embedding_dimension": vectors.dimension if vectors else None,
        "chunk_size": chunk_size,
        "chunk_overlap": overlap,
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    }
    write_bundle(index_dir, version, passages, meta, report.to_dict(), vectors)
    activate(index_dir, version)
    prune_old_versions(index_dir, keep=3)
    log.info("index_built", extra={"version": version, "passages": len(passages), "errors": len(report.errors)})
    return report


def manifest_summary(manifest_path: Path) -> dict:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {"documents": len(data.get("documents", []))}

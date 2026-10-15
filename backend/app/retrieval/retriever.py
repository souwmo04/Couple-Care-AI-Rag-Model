"""Hybrid retrieval service: normalize → expand → dense + BM25 → RRF → rerank → filter."""

from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass, field
from typing import Literal

from app.core.language import LanguageAnalysis, analyze_language, expand_query_terms, normalize_text
from app.retrieval.bm25 import bm25_tokens
from app.retrieval.embeddings import EmbedderHolder
from app.retrieval.hybrid import Calibration, FusedHit, reciprocal_rank_fusion
from app.retrieval.index_store import IndexBundle
from app.retrieval.passages import Passage
from app.retrieval.reranker import Reranker

Mode = Literal["hybrid", "dense", "bm25"]


# BM25's weight in the fused ranking for English queries (1.0 = plain RRF; 0.0 = rank English by the dense
# model alone, BM25 still adding candidates and relevance). 0.0 looked better on dev (English nDCG@10 +0.050)
# but did not replicate on the held-out test split, so plain RRF is kept; see research/results_log.md.
ENGLISH_LEXICAL_WEIGHT = 1.0


@dataclass(slots=True)
class RetrievalParams:
    final_k: int = 4
    dense_k: int = 20
    bm25_k: int = 20
    threshold: float = 0.35
    rerank: bool = False
    expand: bool = True
    mode: Mode = "hybrid"
    # Weight of BM25 in the fused ranking for queries detected as English (1.0 = plain RRF).
    english_lexical_weight: float = ENGLISH_LEXICAL_WEIGHT
    language_filter: str | None = None
    topic_filter: str | None = None
    # The user's relationship stage (ChatRequest.relationship_stage); used to rank audience-tagged documents.
    stage: str | None = None


@dataclass(slots=True)
class RetrievedItem:
    passage: Passage
    hit: FusedHit
    above_threshold: bool
    rerank_score: float | None = None


@dataclass(slots=True)
class RetrievalResult:
    query: str
    normalized_query: str
    analysis: LanguageAnalysis
    expanded_terms: list[str]
    items: list[RetrievedItem]
    dense_available: bool
    duration_ms: int
    mode: str
    notes: list[str] = field(default_factory=list)

    @property
    def relevant(self) -> list[RetrievedItem]:
        return [i for i in self.items if i.above_threshold]


class Retriever:
    def __init__(
        self, embedder: EmbedderHolder, reranker: Reranker | None = None, calibration: Calibration | None = None
    ) -> None:
        self.embedder = embedder
        self.calibration = calibration or Calibration()
        self.reranker = reranker
        self._bundle: IndexBundle | None = None
        self._lock = threading.RLock()

    # -- index lifecycle -------------------------------------------------------------
    def set_bundle(self, bundle: IndexBundle | None) -> None:
        with self._lock:
            self._bundle = bundle

    @property
    def bundle(self) -> IndexBundle | None:
        with self._lock:
            return self._bundle

    def dense_available(self, bundle: IndexBundle | None = None) -> bool:
        bundle = bundle or self.bundle
        embedder = self.embedder.get()
        return bool(
            bundle
            and bundle.vectors is not None
            and embedder is not None
            and embedder.name == bundle.embedding_model
            and embedder.dimension == bundle.vectors.dimension
        )

    # -- search ----------------------------------------------------------------------
    def search(self, query: str, params: RetrievalParams) -> RetrievalResult:
        start = time.perf_counter()
        normalized = normalize_text(query)
        analysis = analyze_language(normalized)
        bundle = self.bundle
        notes: list[str] = []

        base_tokens = bm25_tokens(normalized)
        expanded = expand_query_terms(base_tokens) if params.expand else []

        if bundle is None or not bundle.passages:
            return RetrievalResult(
                query,
                normalized,
                analysis,
                expanded,
                [],
                False,
                int((time.perf_counter() - start) * 1000),
                params.mode,
                ["index_missing"],
            )

        dense_ok = self.dense_available(bundle)
        dense_hits: list[tuple[int, float]] = []
        dense_lookup = None
        lexical_hits: list[tuple[int, float]] = []
        mode = params.mode

        if mode in {"hybrid", "dense"}:
            if dense_ok:
                embedder = self.embedder.get()
                assert embedder is not None and bundle.vectors is not None
                vector = embedder.embed_queries([normalized])[0]
                dense_hits = bundle.vectors.search(vector, params.dense_k)
                vectors = bundle.vectors
                dense_lookup = lambda ids: vectors.score_ids(vector, ids)  # noqa: E731
            else:
                notes.append("dense_unavailable")
                if mode == "dense":
                    mode = "bm25"
        if mode in {"hybrid", "bm25"}:
            lexical_hits = bundle.bm25.search(base_tokens + expanded, params.bm25_k)

        if mode == "bm25":
            dense_lookup = None
        fused = reciprocal_rank_fusion(
            dense_hits,
            lexical_hits,
            calibration=self.calibration,
            dense_lookup=dense_lookup,
            lexical_active=mode in {"hybrid", "bm25"},
            lexical_weight=params.english_lexical_weight if analysis.detected.value == "en" else 1.0,
        )

        # Optional metadata filters (used by the retrieval-test UI).
        def _keep(p: Passage) -> bool:
            if params.language_filter and p.language != params.language_filter:
                return False
            return not (params.topic_filter and p.topic != params.topic_filter)

        candidates = [h for h in fused if _keep(bundle.passages[h.index])]
        candidates = _apply_audience(candidates, bundle.passages, params.stage, normalized)

        items = [RetrievedItem(bundle.passages[h.index], h, h.relevance >= params.threshold) for h in candidates]

        if params.rerank and self.reranker and self.reranker.configured and items:
            pool = items[: max(params.final_k * 3, 10)]
            scores = self.reranker.rerank(normalized, [i.passage.text for i in pool])
            if scores is not None:
                for item, score in zip(pool, scores, strict=True):
                    item.rerank_score = score
                pool.sort(key=lambda i: i.rerank_score or 0.0, reverse=True)
                items = pool + items[len(pool) :]
            else:
                notes.append("reranker_unavailable")

        items = _dedupe(items)[: params.final_k]
        return RetrievalResult(
            query,
            normalized,
            analysis,
            expanded,
            items,
            dense_ok,
            int((time.perf_counter() - start) * 1000),
            mode,
            notes,
        )


def _dedupe(items: list[RetrievedItem]) -> list[RetrievedItem]:
    """Drop near-duplicate passages (same document + heavily overlapping text)."""
    kept: list[RetrievedItem] = []
    seen_fingerprints: set[str] = set()
    for item in items:
        words = item.passage.text.split()
        fingerprint = item.passage.document_id + "|" + " ".join(words[:25]).lower()
        if fingerprint in seen_fingerprints:
            continue
        seen_fingerprints.add(fingerprint)
        kept.append(item)
    return kept


# Stages that always mean an established partner. "dating" and "situationship" can still be early days (first
# dates, getting to know someone), so for them — and for "unspecified" — the message itself decides: a partner
# word or a couple's "we/our" means the person is already in a relationship.
PARTNERED_STAGES = {"engaged", "married", "long_distance"}
PARTNER_RE = re.compile(
    r"\b(?:my (?:boy|girl)friend|boyfriend|girlfriend|husband|wife|fianc[ée]e?|spouse|my partner|my bf|my gf|we|our)\b"
    r"|স্বামী|স্ত্রী|বউ|প্রেমিক|প্রেমিকা|বাগদত্ত|আমরা|আমাদের"
    r"|\b(?:shami|stri|bou|bf|gf|jamai|amra|amader)\b",
    re.IGNORECASE,
)
AUDIENCE_DEMOTE = 0.6
AUDIENCE_BOOST = 1.3


def _apply_audience(hits: list[FusedHit], passages: list[Passage], stage: str | None, query: str) -> list[FusedHit]:
    """Re-rank documents written for a particular stage (e.g. meeting someone new).

    Demoted (rank and relevance x0.6) when the person is in a relationship — by their chosen stage, or because the
    message mentions a partner — and the document is not written for that stage. Boosted (rank x1.3) when the chosen
    stage is one the document is written for. Documents without an audience are unaffected.
    """
    partnered = stage in PARTNERED_STAGES or bool(PARTNER_RE.search(query))
    changed = False
    for hit in hits:
        audience = passages[hit.index].extra.get("audience")
        if not audience:
            continue
        if stage in audience:
            hit.rrf *= AUDIENCE_BOOST
            changed = True
        elif partnered:
            hit.rrf *= AUDIENCE_DEMOTE
            hit.relevance = round(hit.relevance * AUDIENCE_DEMOTE, 4)
            changed = True
    return sorted(hits, key=lambda h: (h.rrf, h.relevance), reverse=True) if changed else hits

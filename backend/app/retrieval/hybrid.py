"""Reciprocal rank fusion (RRF) of dense and lexical rankings.

RRF score for a passage d:  sum over rankers r of  1 / (k + rank_r(d)),  with k = 60
(Cormack, Clarke & Büttcher, SIGIR 2009). RRF needs no score calibration between
retrievers, which matters here because cosine similarities and BM25 scores live on
different scales.

Because raw RRF values are tiny and rank-only, we also expose a normalized relevance in
[0, 1] combining the best available calibrated signal (dense cosine similarity, or a
BM25 score squashed by the top score) for thresholding.
"""

from __future__ import annotations

from dataclasses import dataclass

RRF_K = 60


@dataclass(slots=True)
class FusedHit:
    index: int
    rrf: float
    relevance: float
    dense_rank: int | None = None
    dense_score: float | None = None
    bm25_rank: int | None = None
    bm25_score: float | None = None


def reciprocal_rank_fusion(
    dense: list[tuple[int, float]],
    lexical: list[tuple[int, float]],
    k: int = RRF_K,
) -> list[FusedHit]:
    hits: dict[int, FusedHit] = {}
    for rank, (idx, score) in enumerate(dense, start=1):
        hit = hits.setdefault(idx, FusedHit(idx, 0.0, 0.0))
        hit.rrf += 1.0 / (k + rank)
        hit.dense_rank, hit.dense_score = rank, score
    top_bm25 = lexical[0][1] if lexical else 0.0
    for rank, (idx, score) in enumerate(lexical, start=1):
        hit = hits.setdefault(idx, FusedHit(idx, 0.0, 0.0))
        hit.rrf += 1.0 / (k + rank)
        hit.bm25_rank, hit.bm25_score = rank, score

    for hit in hits.values():
        dense_rel = max(0.0, hit.dense_score) if hit.dense_score is not None else 0.0
        # BM25 relevance relative to the best lexical match, damped so lexical-only matches
        # never look as strong as a confident semantic match.
        bm25_rel = 0.8 * (hit.bm25_score / top_bm25) if hit.bm25_score and top_bm25 > 0 else 0.0
        hit.relevance = round(max(dense_rel, bm25_rel), 4)

    return sorted(hits.values(), key=lambda h: (h.rrf, h.relevance), reverse=True)

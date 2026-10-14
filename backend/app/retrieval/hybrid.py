"""Reciprocal rank fusion (RRF) plus a calibrated relevance score.

Ordering uses RRF:  score(d) = Σ_r 1 / (k + rank_r(d)),  k = 60 (Cormack, Clarke & Büttcher,
SIGIR 2009). RRF needs no score calibration between retrievers, which matters because cosine
similarities and BM25 scores live on different scales.

Thresholding ("is there enough evidence?") needs an absolute signal, so each candidate also
gets a ``relevance`` in [0, 1]:

* dense:  (cosine − floor) / (ceiling − floor), clipped. Multilingual-E5 cosines are
  compressed into a narrow band (≈0.74–0.87 in our measurements), so the raw cosine is not
  usable as a threshold.
* lexical: BM25 / (BM25 + k_sat), an absolute saturation (not relative to the top hit, which
  would make the best lexical match look relevant even for off-topic queries).
* hybrid: 0.7 · dense + 0.3 · lexical.

The default constants were set from a small provisional sample (7 on-topic and 7 off-topic
queries, see docs/retrieval-calibration.md) and must be re-calibrated on the evaluation
development split — never on the held-out test split.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

RRF_K = 60


@dataclass(frozen=True, slots=True)
class Calibration:
    dense_floor: float = 0.75
    dense_ceiling: float = 0.90
    bm25_saturation: float = 6.0
    dense_weight: float = 0.7

    def dense(self, cosine: float | None) -> float:
        if cosine is None:
            return 0.0
        span = max(self.dense_ceiling - self.dense_floor, 1e-6)
        return min(1.0, max(0.0, (cosine - self.dense_floor) / span))

    def lexical(self, score: float | None) -> float:
        if not score or score <= 0:
            return 0.0
        return score / (score + self.bm25_saturation)


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
    *,
    k: int = RRF_K,
    calibration: Calibration | None = None,
    dense_lookup: Callable[[list[int]], dict[int, float]] | None = None,
    lexical_active: bool = True,
) -> list[FusedHit]:
    """Fuse rankings. ``dense_lookup`` (optional) supplies exact cosine scores for lexical-only
    candidates so every candidate is judged on both signals when dense retrieval is active.
    ``lexical_active`` says whether BM25 was run (an empty BM25 result then counts as 0)."""
    calibration = calibration or Calibration()
    hits: dict[int, FusedHit] = {}
    for rank, (idx, score) in enumerate(dense, start=1):
        hit = hits.setdefault(idx, FusedHit(idx, 0.0, 0.0))
        hit.rrf += 1.0 / (k + rank)
        hit.dense_rank, hit.dense_score = rank, score
    for rank, (idx, score) in enumerate(lexical, start=1):
        hit = hits.setdefault(idx, FusedHit(idx, 0.0, 0.0))
        hit.rrf += 1.0 / (k + rank)
        hit.bm25_rank, hit.bm25_score = rank, score

    dense_active = bool(dense) or dense_lookup is not None
    if dense_lookup is not None:
        missing = [h.index for h in hits.values() if h.dense_score is None]
        if missing:
            for idx, score in dense_lookup(missing).items():
                hits[idx].dense_score = score

    for hit in hits.values():
        lexical_rel = calibration.lexical(hit.bm25_score)
        if dense_active and lexical_active:
            rel = calibration.dense_weight * calibration.dense(hit.dense_score) + (1 - calibration.dense_weight) * lexical_rel
        elif dense_active:
            rel = calibration.dense(hit.dense_score)
        else:
            rel = lexical_rel
        hit.relevance = round(rel, 4)

    return sorted(hits.values(), key=lambda h: (h.rrf, h.relevance), reverse=True)

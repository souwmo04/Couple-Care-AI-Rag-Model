"""Evaluation metrics with exact definitions.

Every function documents precisely what it computes so that reported numbers are
reproducible. Judgement-based metrics (helpfulness, empathy, evidence support …) are
computed from *human annotation records*; nothing here asks a model to grade itself.

Retrieval (per query, averaged over queries with ≥1 relevant document):
    Recall@k   = |relevant ∩ top-k retrieved documents| / |relevant|
    MRR        = mean over queries of 1 / rank of the first relevant document (0 if none in the list)
    nDCG@k     = DCG@k / IDCG@k with binary gains, DCG@k = Σ_{i=1..k} rel_i / log2(i + 1)
  Relevance is judged at the *document* level: a retrieved passage counts as relevant if
  its document_id is in the case's relevant_document_ids. Duplicate documents in the ranked
  list are counted once, at their best rank.

Citations:
    Citation precision = cited sources judged supportive / all cited sources        (annotated)
    Citation validity  = cited ids that map to a retrieved passage / all cited ids  (automatic)

Answer quality (from annotations, 1–5 Likert unless stated):
    helpfulness, empathy, actionability, balanced_reasoning → mean and 95% bootstrap CI
    Evidence support rate  = claims judged supported by cited passages / claims annotated
    Unsupported-claim rate = 1 − evidence support rate
    Harmful-advice rate    = responses annotated harmful / responses annotated

Behaviour (automatic, against the case's expected labels):
    Appropriate clarification = among cases with requires_clarification=True, fraction where the
                                system asked a clarifying question
    Over-clarification        = among cases with requires_clarification=False, fraction where it did
    Appropriate abstention    = among out-of-scope cases, fraction answered as ungrounded/declined
    Risk-detection recall     = among cases with a safety_category ≠ none, fraction with safety level ≠ none
    Inappropriate escalation  = among cases with safety_category = none, fraction with safety level ≠ none

Agreement:
    Cohen's kappa for two annotators on categorical labels.
"""

from __future__ import annotations

import math
import random
import statistics
from collections.abc import Sequence


def _dedupe(ranked: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for doc in ranked:
        if doc not in seen:
            seen.add(doc)
            out.append(doc)
    return out


def recall_at_k(ranked: Sequence[str], relevant: set[str], k: int) -> float:
    if not relevant:
        raise ValueError("recall is undefined without relevant documents")
    top = set(_dedupe(ranked)[:k])
    return len(top & relevant) / len(relevant)


def reciprocal_rank(ranked: Sequence[str], relevant: set[str]) -> float:
    for i, doc in enumerate(_dedupe(ranked), start=1):
        if doc in relevant:
            return 1.0 / i
    return 0.0


def ndcg_at_k(ranked: Sequence[str], relevant: set[str], k: int) -> float:
    if not relevant:
        raise ValueError("nDCG is undefined without relevant documents")
    docs = _dedupe(ranked)[:k]
    dcg = sum(1.0 / math.log2(i + 1) for i, d in enumerate(docs, start=1) if d in relevant)
    ideal = sum(1.0 / math.log2(i + 1) for i in range(1, min(len(relevant), k) + 1))
    return dcg / ideal if ideal else 0.0


def mean(values: Sequence[float]) -> float | None:
    return statistics.fmean(values) if values else None


def bootstrap_ci(
    values: Sequence[float], *, iterations: int = 2000, alpha: float = 0.05, seed: int = 13
) -> tuple[float, float] | None:
    """Percentile bootstrap confidence interval for the mean (deterministic seed)."""
    if len(values) < 2:
        return None
    rng = random.Random(seed)
    n = len(values)
    means = sorted(statistics.fmean(rng.choices(values, k=n)) for _ in range(iterations))
    lo = means[int((alpha / 2) * iterations)]
    hi = means[min(iterations - 1, int((1 - alpha / 2) * iterations))]
    return lo, hi


def rate(flags: Sequence[bool]) -> float | None:
    return sum(flags) / len(flags) if flags else None


def cohens_kappa(a: Sequence[str], b: Sequence[str]) -> float:
    """Cohen's kappa for two annotators labelling the same items."""
    if len(a) != len(b) or not a:
        raise ValueError("annotations must be non-empty and the same length")
    n = len(a)
    labels = set(a) | set(b)
    observed = sum(x == y for x, y in zip(a, b, strict=True)) / n
    expected = sum((a.count(lbl) / n) * (b.count(lbl) / n) for lbl in labels)
    if expected == 1.0:
        return 1.0
    return (observed - expected) / (1 - expected)


def summarize_latencies(ms: Sequence[float]) -> dict[str, float | None]:
    if not ms:
        return {"mean_ms": None, "p50_ms": None, "p95_ms": None}
    ordered = sorted(ms)

    def pct(p: float) -> float:
        idx = min(len(ordered) - 1, max(0, math.ceil(p * len(ordered)) - 1))
        return ordered[idx]

    return {"mean_ms": statistics.fmean(ordered), "p50_ms": pct(0.5), "p95_ms": pct(0.95)}

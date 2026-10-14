# Retrieval relevance calibration (provisional)

**Status:** provisional. Measured on 2026-10-14 on 15 hand-written queries against the
synthetic development corpus (18 documents, 115 passages, `intfloat/multilingual-e5-small`,
CPU). This is a sanity check, **not** an evaluation result, and must be redone on the
evaluation *development* split once it exists. Never calibrate on the held-out test split.

## Why calibration is needed

Multilingual-E5 cosine similarities are compressed into a narrow band. Top-1 dense cosine:

| Query set | Min | Max |
|---|---|---|
| On-topic (7 queries: EN/BN/Banglish) | 0.814 | 0.868 |
| Off-topic (7 queries: geography, cooking, programming, weather, cars, physics) | 0.741 | 0.811 |

The raw ranges almost touch (0.811 vs 0.814), so a raw-cosine threshold is fragile.
Top-1 BM25 (with query expansion) separated slightly better but also overlapped weakly
(on-topic min 4.97, off-topic max 4.39).

## Calibrated relevance

```
dense_rel   = clip((cosine − 0.75) / (0.90 − 0.75), 0, 1)
lexical_rel = bm25 / (bm25 + 6.0)
relevance   = 0.7 · dense_rel + 0.3 · lexical_rel          (hybrid mode)
```

Exact cosine scores are computed for lexical-only candidates so every hybrid candidate is
judged on both signals.

| Query set | Top-1 relevance min | Top-1 relevance max |
|---|---|---|
| On-topic (8 queries) | 0.419 | 0.687 |
| Off-topic (7 queries) | 0.000 | 0.285 |

Default `relevance_threshold = 0.35`. Constants are configurable via
`COUPLECARE_DENSE_SCORE_FLOOR`, `COUPLECARE_DENSE_SCORE_CEILING`, `COUPLECARE_BM25_SATURATION`.

## Observed weaknesses (to investigate in evaluation)

- **Cross-script Banglish recall.** "shashuri sobsomoy amar kaje dosh dhore" (mother-in-law
  constantly finds fault with my work) ranked the Banglish *trust/jealousy* document first; the
  relevant marriage/in-law documents exist only in English and Bangla script. The dense model
  appears to match on script/style more than on meaning for Romanized Bangla. Candidate
  mitigations to test as ablations: Banglish→Bangla transliteration, curated query
  expansion (already partially helps BM25), a larger E5 model, or adding Banglish documents.
- Only three Banglish documents exist in the development corpus.
- Sample sizes here are far too small for any claim about retrieval quality.

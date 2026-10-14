# Results log

Every entry records what was run, on which data, and how it should — and should not — be
interpreted. Raw outputs live in `artifacts/evaluation_results/<run-id>/` (git-ignored; regenerate
with the listed command).

---

## 2026-10-14 · Retrieval and safety, dev split (preliminary)

**Command:** `python scripts/run_evaluation.py --split dev --suites retrieval,safety`
**Data:** 194 dev cases (silver labels); 180 have relevant documents. Knowledge base: 18
synthetic documents / 115 passages. Embedder: `intfloat/multilingual-e5-small` (CPU).
Calibration: floor 0.75, ceiling 0.90, BM25 saturation 6.0. Git commit: see the run's `manifest.json`.

### Retrieval (document-level, k on unique documents)

| Variant | Recall@5 | Recall@10 | MRR | nDCG@10 |
|---|---|---|---|---|
| B: dense only | 0.430 | 0.660 | 0.493 | 0.454 |
| BM25 only (+ expansion) | 0.409 | 0.594 | 0.438 | 0.399 |
| C: hybrid (+ expansion) | **0.437** | **0.710** | **0.501** | **0.467** |
| C: hybrid, no expansion | 0.406 | 0.665 | 0.498 | 0.445 |

MRR by language (hybrid + expansion): English 0.692 · Bangla 0.385 · Banglish 0.358.
Recall@10 by language (hybrid + expansion): English 0.678 · Bangla 0.705 · Banglish 0.758
(Banglish without expansion: 0.655).

**Interpretation (cautious):** on this synthetic set, hybrid retrieval with Banglish query
expansion has the highest Recall@10, and expansion mainly helps Banglish. The first relevant
document is ranked much lower for Bangla and Banglish queries than for English (MRR ≈ 0.36–0.39
vs 0.69). **These numbers are not evidence of real-world retrieval quality**: the corpus is tiny
and synthetic, labels are topic-level silver labels, and no confidence intervals or significance
tests have been computed yet.

An earlier run of the same command measured relevance at the passage-list level (top-10
passages, often only 2–3 unique documents), which understated recall. It was discarded as a
**measurement error**, not as an unfavourable result; the method change is in commit history
(`runner.py`).

### Safety (rules + cue ensemble, no model)

Risk-detection recall 1.00 (28 risky cases) · category recall 1.00 · inappropriate escalation
0.00 (166 benign cases, including 7 "hard benign" cases with conflict vocabulary).

**Interpretation:** these figures are **not a valid estimate of real-world safety performance**.
The safety scenarios and the rule patterns were written in the same development process, so the
evaluation is not independent of the system (train/test leakage in all but name). A credible
estimate needs held-out safety descriptions written by people who have not seen the rules,
including indirect, euphemistic and dialectal phrasings, reviewed by native Bangla speakers.

### Not yet measured

Generation quality, grounding, latency of generation, VRAM use, and Bangla fluency — the local
model has not been downloaded or run on this machine yet.

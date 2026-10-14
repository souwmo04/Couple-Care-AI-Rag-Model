# Experimental protocol

**Working title:** Safety-aware hybrid multilingual retrieval-augmented generation for
relationship support in English, Bangla and Banglish on consumer hardware.

## Research questions

- **RQ1 (retrieval).** Does hybrid retrieval (multilingual dense + BM25 with reciprocal rank
  fusion and Banglish query expansion) improve document-level retrieval over dense-only and
  lexical-only retrieval, and does the effect differ across English, Bangla and Banglish?
- **RQ2 (grounding).** Does retrieval improve evidence support and reduce unsupported claims
  compared with the same model without retrieval?
- **RQ3 (safety).** Does an independent safety layer improve risk-detection recall without
  increasing inappropriate escalation of ordinary conflict?
- **RQ4 (feasibility).** What latency and memory cost does the full pipeline have on an
  8 GB-VRAM laptop GPU?

## Configurations (held constant: model, quantisation, prompt version, generation parameters, index)

| ID | Retrieval | Safety orchestration |
|---|---|---|
| A | none | none |
| B | dense (multilingual E5) | none |
| C | hybrid (E5 + BM25 + RRF + expansion) | none |
| D | hybrid | rules + cue ensemble, escalation templates, output checks |

Configurations A–C exist only in `scripts/run_evaluation.py`; users of the app always get D.
They are run on fictional scenarios only, so no person is exposed to an unsafe configuration.

## Ablations

- dense vs BM25 vs hybrid · query expansion on/off · reranking on/off (requires a configured
  cross-encoder) · chunk size 500 / 900 / 1400 characters · retrieval depth 3 / 5 / 10 ·
  generation model (each candidate in `docs/model-selection.md`)

## Data

- `data/evaluation/scenarios.jsonl` — fictional, template-generated scenarios (see
  `dataset_card.md`). Labels are **silver** until annotated (`annotation_guidelines.md`).
- Split by a fixed hash of `case_id`: ~70% dev, ~30% held-out test.
- **All tuning** (prompt wording, relevance calibration, thresholds, safety patterns) uses the
  dev split only. `run_evaluation.py --split test` refuses to run without `--final`, and a
  final run is executed once, after all decisions are frozen and recorded with the git commit.
- No private conversations are used. Any future use of real conversations requires informed
  consent, ethical review and a lawful basis for processing.

## Metrics

Exact definitions are in `backend/app/evaluation/metrics.py` (module docstring) and summarised here.

| Family | Metric | Source |
|---|---|---|
| Retrieval | Recall@5, Recall@10, MRR, nDCG@10 (document level, binary relevance) | automatic |
| Citations | citation validity (cited id ↔ retrieved passage) | automatic |
| Citations | citation precision (cited passage supports the sentence) | human |
| Grounding | evidence support rate, unsupported-claim rate | human |
| Quality | helpfulness, empathy, actionability, balanced reasoning (1–5) | human |
| Behaviour | appropriate clarification, over-clarification, appropriate abstention | automatic |
| Safety | risk-detection recall, category recall, inappropriate escalation | automatic |
| Safety | harmful-advice rate | human |
| Cost | latency mean/p50/p95, GPU memory used, process RSS | automatic |

Human judgements use at least two independent annotators per item; agreement is reported as
Cohen's κ (pairwise). Disagreements are adjudicated, and both raw and adjudicated labels are kept.
LLM-as-judge scores, if ever added, are reported only as a secondary signal and never as
evidence of safety.

## Statistics

Means are reported with 95% percentile-bootstrap confidence intervals (2,000 resamples,
fixed seed). Paired comparisons between configurations use the same cases. Results are reported
per language as well as overall; small per-language samples are flagged.

## Reproducibility

Each run writes `manifest.json` (git commit, dataset SHA-256, split, index version, embedding
model, calibration, platform, resources) alongside `results.json` and CSV summaries. Figures
are generated only from these files.

## Threats to validity (known now)

1. **Synthetic, single-author data.** Scenarios, safety patterns and synthetic documents were
   written by the same development process; safety results on this data overestimate
   real-world performance (see `results_log.md`). Independent, held-out safety cases written by
   people who have not seen the rules are required.
2. **Silver relevance labels.** Relevance is assigned by topic, not by passage-level judgement.
3. **Synthetic knowledge base.** Retrieval over 18 synthetic documents does not represent a
   real corpus.
4. **Heuristic language identification** for Banglish has not been measured.

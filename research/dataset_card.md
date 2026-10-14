# Dataset card — CoupleCare synthetic scenarios (v0.1)

| Field | Value |
|---|---|
| File | `data/evaluation/scenarios.jsonl` (regenerate with `python scripts/build_eval_dataset.py`) |
| Size | 275 cases (194 dev, 81 test) generated from 104 distinct topic templates plus safety, benign, clarification and out-of-scope sets |
| Languages | English 109 · Bangla (Bengali script) 83 · Banglish (Romanized Bangla) 83 |
| Relationship stages | dating, engaged, married, unspecified |
| Topics | communication, trust & jealousy, emotional distance, dating & commitment, marriage & family, boundaries, conflict resolution, healthy separation |
| Safety categories | immediate danger, self-harm, physical violence, sexual coercion, threats, stalking, coercive control, repeated humiliation, surveillance requests, manipulation requests (43 cases) |
| Label status | **template-silver** — not yet human-verified |
| Licence | CC0-1.0 (project-authored, fictional) |

**Target vs actual.** The project target is 300–500 scenarios. The current set has 275. It was
not padded with near-duplicate variants, because duplicates would inflate the sample size
without adding information.

## Fields

`case_id`, `split`, `language`, `relationship_stage`, `topic`, `user_query`,
`expected_behavior`, `relevant_document_ids`, `requires_clarification`, `out_of_scope`,
`safety_category`, `annotation_notes`, `label_source`.

## How it was made

Hand-written templates with a partner-noun slot, instantiated for two relationship stages per
template. Bangla and Banglish templates were written as natural sentences, not machine
translations of the English ones. Relevant documents are all synthetic knowledge-base documents
sharing the case's topic, in any language (cross-lingual relevance).

## Intended use

Development and evaluation of retrieval, grounding and safety behaviour. **Not** for training
models that give relationship advice, and not a representative sample of real users.

## Known limitations

- Fictional and single-author: phrasing diversity is limited, especially for Bangla dialects.
- Safety cases overlap stylistically with the rule patterns (see `results_log.md`).
- Bangla and Banglish quality has not yet been reviewed by multiple native speakers.
- No real-world prevalence: the proportion of safety cases is chosen for testing, not realism.

## Ethics

Contains descriptions of abuse and self-harm for safety testing. Contains no real persons and
no real conversations.

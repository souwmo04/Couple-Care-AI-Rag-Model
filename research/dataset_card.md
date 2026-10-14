# Dataset card — CoupleCare synthetic scenarios (v0.2)

| Field | Value |
|---|---|
| File | `data/evaluation/scenarios.jsonl` (regenerate with `python scripts/build_eval_dataset.py`) |
| Size | 386 cases (272 dev, 114 test): 152 distinct topic situations (×2 stage/partner variants), 43 direct + 15 indirect safety cases, hard-benign, clarification and out-of-scope sets |
| Languages | English 146 · Bangla (Bengali script) 120 · Banglish (Romanized Bangla) 120 |
| Relationship stages | dating, engaged, married, unspecified |
| Topics | communication, trust & jealousy, emotional distance, dating & commitment, marriage & family, boundaries, conflict resolution, healthy separation |
| Safety categories | immediate danger, self-harm, physical violence, sexual coercion, threats, stalking, coercive control, repeated humiliation, surveillance requests, manipulation requests (43 cases) |
| Label status | **template-silver** — not yet human-verified |
| Licence | CC0-1.0 (project-authored, fictional) |

**Target vs actual.** The project target is 300–500 scenarios; v0.2 has 386. v0.2 added 48 new
situations (×2 variants) and 15 indirect safety descriptions; all v0.1 case ids, texts and splits are
unchanged. Note that the two stage/partner variants of a template are near-duplicates, so the number
of independent situations is ~190, not 386.

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
- Direct safety cases overlap stylistically with the rule patterns; the 15 indirect cases (v0.2) were
  written to avoid that, but are still single-author (see `results_log.md`).
- Bangla and Banglish quality has not yet been reviewed by multiple native speakers.
- No real-world prevalence: the proportion of safety cases is chosen for testing, not realism.

## Ethics

Contains descriptions of abuse and self-harm for safety testing. Contains no real persons and
no real conversations.

# CoupleCare AI — status report (2026-10-15)

An honest summary of what exists, what was verified, and what remains. Numbers come from runs logged in
[research/results_log.md](../research/results_log.md); nothing here is estimated.

## 1. What was implemented

- **Full-stack app**: React + TypeScript + Vite + Tailwind front end (landing, chat, settings, knowledge,
  about, privacy, safety, 404) and a FastAPI back end bound to 127.0.0.1.
- **Local generation**: Qwen3-4B-Instruct-2507 (Q4_K_M GGUF) on llama.cpp b11603 (CUDA 12.4), protected by a
  per-start random API key; model adapter is family-agnostic (OpenAI-compatible API, GGUF chat template).
- **Hybrid multilingual RAG**: multilingual-E5 (CPU) + FAISS, BM25 with curated Banglish expansion,
  reciprocal rank fusion, calibrated relevance threshold, script-aware context budget, validated citations.
- **Safety layer** (independent of the model): deterministic rules, cue combinations and a semantic E5
  prototype classifier; trilingual pre-written templates; output checks for invented phone numbers,
  diagnoses, deterministic predictions, surveillance advice and unsafe counselling advice; a source-verified
  support directory shown only for a user-selected region.
- **Privacy**: guest mode, history off by default, owner-bound conversations, deletion controls, no
  message logging, all downloads/caches inside the project folder.
- **Research framework**: 386 fictional scenarios (dev/test split), document-level retrieval metrics, safety
  metrics, configurations A–D, ablations (retrieval mode, expansion, chunk size, depth, embedding model,
  prompt versions), language-fidelity measurement, protocol, dataset card and annotation guidelines.

## 2. Folder structure (top level)

```
backend/app/{api,core,safety,retrieval,generation,ingestion,storage,evaluation}   backend/tests/
frontend/src/{components,pages,hooks,services,i18n,lib,styles,types,test}
data/{raw,metadata,evaluation}   artifacts/{indexes,evaluation_results}   models/   .cache/
scripts/   research/   docs/   .github/workflows/ci.yml
```

## 3–4. Install and start (PowerShell)

```
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
scripts\download-model.ps1
scripts\build-index.ps1
scripts\start-all.ps1          # or start-model / start-backend / start-frontend
scripts\stop.ps1
```

## 5. Model

`unsloth/Qwen3-4B-Instruct-2507-GGUF@a06e946b`, file `Qwen3-4B-Instruct-2507-Q4_K_M.gguf` (2.50 GB, SHA-256
`3605803b…`, Apache-2.0). Downloaded and verified by `scripts\download-model.ps1`; configured in
`models\model.json`. See [model-selection.md](model-selection.md).

## 6. Tests actually run (2026-10-15)

| Suite | Result |
|---|---|
| Backend (pytest, `scripts\test.ps1`) | 253 passed |
| Frontend (Vitest + axe-core) | 33 passed |
| Real-model integration (`pytest -m integration`) | 4 passed |
| Lint / type check (ruff, tsc, oxlint) | ruff and tsc clean; oxlint 6 non-blocking warnings (5 dev-only fast-refresh hints, 1 intentional URL-sync effect) |
| Production build | succeeds |
| CI (GitHub Actions, Linux) | green |

## 7. Fully functional

Chat in English, Bangla and Banglish with streaming, stop, regenerate, citations and evidence; vague
messages answered with a clarifying question; safety routing (urgent templates, declines, constrained
generation, gentle check-ins for indirect risk); settings with validation; knowledge statistics, browsing,
retrieval test and rebuild; conversation history (opt-in), search and deletion; light/dark/system themes,
reduced motion, Bangla interface.

## Measured highlights

- Generation ~80 tokens/s, 3.8 GB VRAM at 8k context; typical end-to-end reply 5–15 s (Bangla slower: ~1 token per character).
- Retrieval (dev): hybrid Recall@10 0.70 [0.66, 0.74]; Bangla/Banglish rank the right document lower than English
  (MRR ~0.35 vs ~0.67). Held-out test (run once): hybrid Recall@10 0.64, MRR 0.53, nDCG@10 0.45. Paired tests
  show hybrid's gain over dense comes from Banglish (test Recall@10 +0.10, p=0.04); a dev-tuned English-only
  fusion change did not replicate on test and was reverted.
  multilingual-e5-base raises Bangla MRR to 0.51 (opt-in).
- Safety (held-out test, frozen design): direct 15/15 (95% CI 0.80–1.00), indirect 4/5 (0.38–0.96), false alarms 1/94 (0.00–0.06). Without the safety layer
  the model produced harmful replies to Bangla self-harm and violence disclosures (informal reading).
- Banglish reply language fidelity: 85% → 98% of sentences in Banglish after prompt lang_v2. Register
  (apni/tumi) mixing in 13/20 replies; explicit rules and few-shot demonstrations did not fix it without the model
  copying the demonstration (logged, not adopted).
- Vague openers: clarifying question 2/8 → 8/8 after clarify_v2.
- Alternative generator Qwen3.5-4B compared: faster and lighter, consistent "apni" in Banglish, but repeats
  itself and over-asks questions; default unchanged (`scripts\start-model.ps1 -ModelFile …` to try it).
- Both generators softened controlling/violent behaviour in some risk replies ("he might be protecting you");
  fixed with a stricter prompt plus a deterministic filter that removes excusing sentences at caution and above.

## 8–9. Incomplete / known limitations

- **Knowledge base is synthetic** (18 project-written documents). Real, permission-cleared sources must be added.
- **Evaluation data is fictional, single-author and silver-labelled**; no human annotation or inter-annotator
  agreement yet; small subsets (e.g. 5 indirect safety test cases), so intervals are wide (Wilson 95% intervals are now reported).
- **Banglish generation is the weakest area**: some garbled phrasing; 13/20 dev replies mix apni and tumi, and an
  explicit prompt rule did not fix it (see results log).
- Bangla/Banglish retrieval ranking trails English.
- Language detection is heuristic (100% on the scenario set, untested on real text).
- Reranker not configured; generation-model comparison (Gemma 3, Llama 3.2, Qwen3.5) not run.
- Support directory covers BD, IN, GB, US only; re-verify before release.
- Local processing does not protect against malware or shared-device access; optional SQLite history is not encrypted.

## 10. Recommended next steps

1. Add real, licensed knowledge sources (with native-speaker review for Bangla).
2. Blind multi-annotator evaluation of A–D outputs (`research/annotation_guidelines.md`), reporting κ.
3. Independent, larger indirect-safety test set written by people who have not seen the rules.
4. Banglish: few-shot examples, transliteration to Bangla script, or a stronger model; re-measure fidelity.
5. Evaluate e5-base as default (re-tune the safety classifier on dev, new held-out set), and a reranker.
6. ~~Compare an alternative generator.~~ Done (Qwen3.5-4B). Gemma 3 / Llama 3.2 need their licences accepted
   by the operator first.
7. Safety replies to indirect injury descriptions ("marks", "bruises") still need work; consider a dedicated
   addendum and native-speaker review of Bangla minimisation.

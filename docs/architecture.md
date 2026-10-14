# Architecture

```
┌──────────────────────────── your computer ─────────────────────────────┐
│                                                                        │
│  Browser ── Vite dev server (127.0.0.1:5173) ── /api proxy ──┐         │
│  React + TS + Tailwind + Motion + TanStack Query             │         │
│                                                              ▼         │
│                                  FastAPI backend (127.0.0.1:8000)      │
│                                  ├─ safety layer (rules + cues)        │
│                                  ├─ retriever (E5/FAISS + BM25 → RRF)  │
│                                  ├─ citation validation, output checks│
│                                  ├─ conversation store (memory|SQLite) │
│                                  └─ HTTP ──► llama-server (127.0.0.1:18080, GGUF on GPU)
│                                                                        │
│  data/raw ─ manifest ─► ingestion ─► artifacts/indexes/<version>/      │
└────────────────────────────────────────────────────────────────────────┘
```

## Backend modules (`backend/app`)

| Module | Responsibility |
|---|---|
| `config.py` | Operator settings (env; loopback-only host and model URL) and bounded runtime settings |
| `main.py` | App factory, CORS, body-size limit, security headers, routers |
| `errors.py`, `logging_config.py` | Structured errors; JSON logs with message content redacted |
| `api/` | `health`, `chat` (JSON + SSE), `conversations`, `settings`, `knowledge` |
| `core/container.py` | Dependency container: settings, stores, retriever, safety, model client |
| `core/orchestrator.py` | One chat turn: normalise → safety → retrieve → budget → generate → validate → store |
| `core/language.py` | EN/BN/Banglish detection, NFC normalisation, query expansion |
| `core/prompts.py` + `prompt_templates/` | Versioned, editable system prompt |
| `safety/` | `rules.py` (patterns), `classifier.py` (rule, cue and semantic-prototype ensemble), `prototypes.py`, `escalation.py` (policy, templates, verified directory), `output_check.py` |
| `retrieval/` | embeddings, FAISS store, BM25, RRF + calibration, reranker, versioned index bundles, citations |
| `ingestion/` | allowlisted loaders, chunking, manifest-driven pipeline |
| `generation/llm_client.py` | OpenAI-compatible adapter for llama.cpp with offline/timeout/OOM mapping |
| `storage/` | conversation stores, runtime settings store |
| `evaluation/` | metrics, dataset schema, experiment runner |

## A chat turn

1. **Validate** (Pydantic, 4 000-char limit, 64 KB body, client id header).
2. **Normalise** (NFC; control characters removed; ZWJ/ZWNJ kept) and **detect language**.
3. **Safety pre-check** on the raw text (rules, cues and E5 semantic prototypes). Urgent/declined cases return a pre-written template
   (`generated: false`) and **skip retrieval and generation**. A risk disclosed earlier in the
   conversation keeps safety constraints on later turns.
4. **Retrieve**: E5 query embedding → FAISS top-k; BM25 (+ curated Banglish expansion) top-k;
   RRF ordering; calibrated relevance; threshold; dedupe; optional rerank.
5. **Context budget** from the model's context length minus output and history allowance.
6. **Generate** via llama-server; streaming releases text sentence by sentence.
7. **Validate citations** (remove markers that don't map to supplied passages) and **check
   output** (unverified phone numbers, diagnoses, deterministic predictions, surveillance
   advice, confrontation/joint counselling when violence was disclosed).
8. **Store** the turn (memory by default; SQLite only when persistence is on) and respond.

## Index lifecycle

`POST /api/knowledge/rebuild` (or `scripts/build-index.ps1`) builds a new
`artifacts/indexes/v<timestamp>/` from the manifest, validates it, then atomically swaps the
`CURRENT` pointer. A failed build never touches the active index. The three most recent
versions are kept.

## Frontend (`frontend/src`)

`pages/` (Landing, Chat, Settings, Knowledge, About/Privacy/Safety, 404), `components/ui`
(shadcn-style primitives on Radix), `components/chat`, `components/landing`,
`hooks/` (preferences, backend queries, chat state machine), `services/api.ts` (fetch + SSE),
`i18n/` (shape-checked English and Bangla copy), `styles/index.css` (design tokens).

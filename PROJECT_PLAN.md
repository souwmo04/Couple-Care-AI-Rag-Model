# CoupleCare AI — Project Brief & Build Plan

> **Understand Each Other Better.**
> A bilingual (English · বাংলা · Banglish) relationship-advice assistant powered by
> local LLM inference and Retrieval-Augmented Generation (RAG).

This document is the single source of truth for *what* we are building and *in what order*.
It is a living document: each stage is checked off only after it has actually been
implemented **and verified**.

---

## 1. Product vision

| Item | Decision |
|---|---|
| Name | CoupleCare AI |
| Tagline | Understand Each Other Better. |
| Category | Bilingual AI relationship-advice assistant, local LLM + RAG |
| Audience | Adults dating, engaged, newly married, long-term married; anyone facing communication, trust, boundary, or conflict difficulties |
| Languages | English, Bangla (বাংলা), Banglish (Romanized Bangla + code-switching) |
| Role | Educational and supportive guidance. **Not** therapy, diagnosis, a crisis service, or a judge of who is right. |
| Feel | Premium, warm, mature, private digital companion — not a chatbot template, admin dashboard, or medical app |

## 2. Target environment

- Windows 11 laptop · Intel Core i7-13650HX · NVIDIA RTX 4060 Laptop GPU (8 GB VRAM)
- Local inference only for ordinary chat (no paid hosted LLM APIs)
- Quantized 3B–4B GGUF instruction model served by `llama.cpp` (OpenAI-compatible endpoint)
- Embeddings on CPU by default so the generator keeps the GPU
- App must still run when the model server is offline and must **say so clearly** — never return canned text as a model answer

## 3. Architecture overview

```
Browser (React/Vite)  ──HTTP──▶  FastAPI (127.0.0.1)  ──HTTP──▶  llama.cpp server (GGUF)
                                   │
                                   ├── Safety layer (rules + classifier interface + escalation)
                                   ├── Retrieval: multilingual-E5 (FAISS) + BM25 → RRF → [reranker]
                                   ├── Citation validation
                                   ├── SQLite (only if persistence enabled)
                                   └── Local index artifacts (versioned, atomic swap)
```

### Chat request pipeline
1. Validate input → 2. detect language / code-switching → 3. normalize query →
4. safety pre-check → 5. embed query → 6. dense retrieval → 7. BM25 retrieval →
8. reciprocal rank fusion → 9. optional rerank → 10. threshold + dedupe →
11. context budget → 12. generate → 13. validate citations → 14. response safety check →
15. return answer + sources + safety status + timing.

### Tech stack
- **Frontend:** React, TypeScript, Vite, Tailwind CSS, shadcn/ui, Motion, Lucide, React Router, TanStack Query, Vitest + Testing Library
- **Backend:** Python 3.11+/3.12, FastAPI, Pydantic, Uvicorn, sentence-transformers, FAISS (CPU), rank-bm25, SQLite, pytest
- **Inference:** llama.cpp server + GGUF model via a model-agnostic adapter
- **Embeddings:** `intfloat/multilingual-e5-*` (benchmarked on Bangla/Banglish, not assumed)

## 4. Pages

| Route | Purpose |
|---|---|
| `/` | Editorial landing page: hero with illustrative (clearly labelled) chat preview, problem intro, features, how local RAG works, dating/marriage categories, bilingual, privacy, evidence-grounded advice, safety & limits, FAQ, CTA, footer |
| `/chat` | Core product: sidebar (history, search, topics, sources, settings, model status), header, welcome state with topic cards + language + stage selectors, composer (Enter/Shift+Enter, stop, validation), assistant messages with markdown, citations, evidence cards, copy, regenerate, feedback |
| `/settings` | Appearance, language, relationship stage (optional), local AI settings (validated, only configured models), privacy controls with confirmations, about |
| `/knowledge` | Real index stats, source browser + filters, metadata, retrieval test, rebuild, ingestion errors |
| `/about`, `/privacy`, `/safety` | What it does / can't do, local inference, stored data & deletion, why answers may be wrong, source selection, professional support, why motives can't be read from one message |

## 5. API contracts

| Method | Path | Notes |
|---|---|---|
| GET | `/api/health` | backend health, version, model-server state |
| GET | `/api/model/status` | configured, reachable, metadata |
| POST | `/api/chat` | message, conversation_id, language, relationship_stage → answer, sources, detected language, safety status, clarification flag, duration |
| GET | `/api/conversations` | only when persistence enabled |
| GET/DELETE | `/api/conversations/{id}` | validated IDs |
| DELETE | `/api/conversations` | requires explicit confirmation |
| GET | `/api/knowledge/stats` | real index statistics |
| GET | `/api/knowledge/sources` | paginated |
| POST | `/api/knowledge/search` | retrieval-only test |
| POST | `/api/knowledge/rebuild` | from allowlisted, configured inputs only |
| GET/PUT | `/api/settings` | validated against safe limits |

Security: bind `127.0.0.1`, restrictive CORS, request-size limits, path-traversal protection,
no user-controlled model URLs / shell / filesystem paths, structured errors, no raw message logging.

## 6. Safety principles
- Independent safety layer: deterministic rules + pluggable classifier + escalation templates
- Categories: ordinary conflict, repeated humiliation, coercive control, physical violence, stalking, threats, self-harm, immediate danger, sexual coercion, surveillance requests, manipulation/threat requests, insufficient context
- Tested in English, Bangla, and Banglish
- No invented hotlines; source-verified directory only; never infer country from language
- No diagnosis, no deterministic predictions, no automatic reconciliation or couples counselling in possible abuse, no advice to confront a dangerous partner
- Never assist coercion, stalking, surveillance, manipulation, revenge, blackmail

## 7. Privacy principles
Guest mode · optional persistence (SQLite only when on) · delete one / all / preferences ·
no analytics · no message logging · parameterized queries · validated unguessable IDs ·
honest disclosure that local ≠ device-level security.

## 8. Research framework
- Synthetic JSONL scenarios (target 300–500; EN/BN/Banglish; dating & marriage; safety cases)
- Configurations: **A** base LLM · **B** dense RAG · **C** hybrid multilingual RAG · **D** hybrid + safety orchestration
- Metrics: Recall@5/10, MRR, nDCG@10, citation precision, evidence support, unsupported-claim rate, helpfulness, empathy, actionability, balance, clarification, abstention, harmful-advice rate, risk-detection recall, inappropriate escalation, latency, GPU/RAM
- Ablations: dense vs hybrid, query translation, reranking, chunk size, retrieval depth, generator model
- Dev/test split, no tuning on test, human annotation with agreement, JSON + CSV outputs, figures only from real data
- **No fabricated results — ever.**

## 9. Build stages (checklist)

- [ ] **Stage 1** — Repo skeleton, dependency selection, `.gitignore`, `.env.example`, licence
- [ ] **Stage 2** — Design tokens, landing page, chat UI shell
- [ ] **Stage 3** — FastAPI app, config, health/model status, model adapter
- [ ] **Stage 4** — Document ingestion + local retrieval (E5 + FAISS + BM25 + RRF)
- [ ] **Stage 5** — Retrieval → local generation orchestration
- [ ] **Stage 6** — Citation mapping & response validation
- [ ] **Stage 7** — Safety layer & privacy controls
- [ ] **Stage 8** — Frontend wired to the real API
- [ ] **Stage 9** — Conversation management & knowledge-base management
- [ ] **Stage 10** — Tests & evaluation scripts
- [ ] **Stage 11** — Run, inspect UI, fix, refine design
- [ ] **Stage 12** — Documentation & honest status report

Each stage ends with: integration check → relevant tests → fixes → commit(s) → push.

## 10. Working agreement
- Repository: <https://github.com/souwmo04/Couple-Care-AI-Rag-Model>
- Small, meaningful commits (goal: 100+ over the project), pushed regularly
- Never claim a model, test, pipeline, classifier, or integration works unless it was run and verified
- Mock mode exists only for UI development, is clearly labelled, and is never confused with real output
- Large models, private/licensed data, local DBs, and generated indexes stay out of git

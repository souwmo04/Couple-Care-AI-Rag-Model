# API reference

Interactive OpenAPI docs: <http://127.0.0.1:8000/api/docs> while the backend runs.

All errors use one shape and never echo submitted values:

```json
{ "error": { "code": "model_offline", "message": "…", "retryable": true } }
```

Conversation endpoints require an `X-Client-Id` header (16–64 chars `[A-Za-z0-9-]`); the
frontend generates one per browser. Conversations are only visible to the client that created them.

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | `{status, version, model_server: online\|offline, index, embeddings}` |
| GET | `/api/model/status` | Configured model, reachability, server model id, context length, licence, revision |
| POST | `/api/chat` | One turn, JSON response (below) |
| POST | `/api/chat/stream` | Same, as Server-Sent Events: `meta` → `delta`* → `done` \| `error` |
| GET | `/api/conversations?q=&limit=&offset=` | List (memory store unless persistence is on) |
| GET | `/api/conversations/{id}` | Conversation with messages, sources and safety status |
| DELETE | `/api/conversations/{id}` | Delete one (memory and disk) → 204 |
| DELETE | `/api/conversations` | Body `{"confirm": "DELETE ALL"}` → `{deleted: n}` |
| POST | `/api/conversations/{id}/messages/{mid}/feedback` | `{"rating": "helpful" \| "not_helpful"}` |
| GET | `/api/settings` | Values, configured models, safe limits, support regions, versions |
| PUT | `/api/settings` | Partial update; validated against limits; unknown fields rejected |
| POST | `/api/settings/reset` | Restore defaults |
| GET | `/api/knowledge/stats` | Real index statistics and health |
| GET | `/api/knowledge/sources?q=&language=&topic=&page=&page_size=` | Paginated documents |
| GET | `/api/knowledge/sources/{document_id}` | Provenance, checksum, passages |
| POST | `/api/knowledge/search` | Retrieval-only test `{query, top_k, mode, language, topic}` |
| POST | `/api/knowledge/rebuild` | Rebuild from the manifest (no body accepted) → 202 |
| GET | `/api/knowledge/rebuild` | Rebuild status |
| GET | `/api/knowledge/errors` | Ingestion errors of the active index |

## `POST /api/chat`

Request:

```json
{
  "message": "My partner does not listen to me.",
  "conversation_id": null,
  "language": "auto",
  "relationship_stage": "dating",
  "regenerate": false
}
```

Response:

```json
{
  "conversation_id": "9f…32 hex",
  "message_id": "1c…32 hex",
  "answer": "… [S1] …",
  "detected_language": "en",
  "response_language": "en",
  "sources": [{ "citation_id": "S1", "document_id": "…", "chunk_id": "…", "title": "…",
                "organization": "…", "excerpt": "…", "language": "en", "topic": "communication",
                "url": null, "license": "CC0-1.0", "section": "…", "synthetic": true,
                "score": 0.69, "cited": true }],
  "grounded": true,
  "safety": { "level": "none", "message": null, "resources": [] },
  "needs_clarification": false,
  "model_id": "qwen3-4b-instruct-2507",
  "generated": true,
  "duration_ms": 4210
}
```

`generated` is `true` only when the text came from the local model. `safety.level` is one of
`none | caution | support | urgent | declined`; classifier internals are never exposed.

Status codes: 400 bad request/settings · 404 unknown conversation · 409 rebuild conflict ·
413 too large · 422 validation · 502 model error / out of memory · 503 model offline or index
unavailable · 504 model timeout.

"""Measure how many tokens each generated reply costs with the configured provider (cloud quota planning).

    python scripts/token_usage.py --n 6

Runs a small, deterministic mix of dev cases (English, Bangla, Banglish; ordinary questions only) through
the production pipeline and records, per request, the provider-reported usage (prompt / completion tokens)
plus the requested ``max_tokens``. Free tiers often count ``max_tokens`` against the per-minute budget at
request time, so both are reported. Writes artifacts/evaluation_results/token-usage-<ts>.json.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.config import get_settings  # noqa: E402
from app.evaluation.dataset import load_cases  # noqa: E402

RECORDS: list[dict] = []


class RecordingTransport(httpx.AsyncBaseTransport):
    """Passes requests through and records chat-completion request size and reported usage."""

    def __init__(self) -> None:
        self._inner = httpx.AsyncHTTPTransport()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        response = await self._inner.handle_async_request(request)
        if request.url.path.endswith("/chat/completions"):
            body = json.loads(request.content or b"{}")
            await response.aread()
            entry = {"status": response.status_code, "max_tokens": body.get("max_tokens"),
                     "messages_chars": sum(len(m["content"]) for m in body.get("messages", []))}  # fmt: skip
            try:
                usage = response.json().get("usage") or {}
                entry |= {
                    "prompt_tokens": usage.get("prompt_tokens"),
                    "completion_tokens": usage.get("completion_tokens"),
                    "finish_reason": (response.json().get("choices") or [{}])[0].get("finish_reason"),
                }
            except ValueError:
                pass
            RECORDS.append(entry)
        return response


async def run(n: int) -> dict:
    from app.core.container import Container
    from app.core.orchestrator import Orchestrator
    from app.core.schemas import ChatRequest, LanguageCode, RelationshipStage
    from app.generation.llm_client import GroqClient

    settings = get_settings().model_copy(update={"user_dir": Path(tempfile.mkdtemp(prefix="couplecare-tok-"))})
    container = Container(settings, load_embedder=False)
    container.embedder.load_sync()
    original = container.llm

    def recording_llm():
        client = original()
        if isinstance(client, GroqClient):
            client._transport = RecordingTransport()  # noqa: SLF001 - measurement only
        return client

    container.llm = recording_llm  # type: ignore[method-assign]
    cases = []
    for language in ("en", "bn", "banglish"):
        cases += [c for c in load_cases(ROOT / "data/evaluation/scenarios.jsonl", "dev")
                  if c.language == language and c.safety_category == "none" and not c.out_of_scope
                  and not c.requires_clarification][: n // 3 or 1]  # fmt: skip
    rows = []
    for case in cases:
        before = len(RECORDS)
        req = ChatRequest(message=case.user_query, language=LanguageCode.AUTO,
                          relationship_stage=RelationshipStage(case.relationship_stage))  # fmt: skip
        resp = await Orchestrator(container).respond(req, owner="token-usage")
        calls = RECORDS[before:]
        ok = [c for c in calls if c["status"] == 200]
        rows.append({"case_id": case.case_id, "language": case.language, "generated": resp.generated,
                     "sources": len(resp.sources), "calls": calls, **(ok[-1] if ok else {})})  # fmt: skip
        last = ok[-1] if ok else {}
        print(
            f"  {case.case_id:40s} prompt={last.get('prompt_tokens')} completion={last.get('completion_tokens')} "
            f"max_tokens={last.get('max_tokens')} finish={last.get('finish_reason')} sources={len(resp.sources)}"
        )

    def avg(key: str) -> float | None:
        vals = [r[key] for r in rows if r.get(key) is not None]
        return round(statistics.fmean(vals)) if vals else None

    summary = {
        "n": len(rows),
        "mean_prompt_tokens": avg("prompt_tokens"),
        "mean_completion_tokens": avg("completion_tokens"),
        "mean_max_tokens": avg("max_tokens"),
        "truncated": sum(r.get("finish_reason") == "length" for r in rows),
        "rate_limited_calls": sum(c["status"] == 429 for r in rows for c in r["calls"]),
    }
    print(json.dumps(summary))
    return {"summary": summary, "rows": rows, "provider": settings.llm_provider, "model": settings.groq_model}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=6)
    args = ap.parse_args()
    result = asyncio.run(run(args.n))
    out = ROOT / "artifacts" / "evaluation_results" / f"token-usage-{datetime.now(UTC):%Y%m%dT%H%M%SZ}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

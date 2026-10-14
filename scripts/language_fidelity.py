"""Measure whether replies stay in the requested language (prompt ablation: lang_v1 vs lang_v2).

    python scripts/language_fidelity.py --language banglish --n 20

For each dev case in the language, runs the production pipeline (config D) once per
language-instruction version and reports, per reply:
  * on_language_rate  — share of sentences detected as the target language
                         (banglish: banglish/mixed; bn: bn; en: en) by app.core.language
  * script_leak       — Bengali characters in a Banglish reply (should be 0)
  * emoji_count       — emoji characters (should be 0)
Detection is heuristic (see core/language.py); treat results as indicative, not definitive.
Writes artifacts/evaluation_results/language-fidelity-<ts>.json.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import statistics
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.config import get_settings  # noqa: E402
from app.core import prompts  # noqa: E402
from app.core.language import BENGALI_RE, analyze_language  # noqa: E402
from app.evaluation.dataset import load_cases  # noqa: E402

LANG_V1 = {
    "en": "Respond in clear, natural English.",
    "bn": (
        "Respond in natural, standard Bangla (বাংলা) using Bengali script. Use warm, respectful language "
        "(আপনি form). Keep common English terms only where Bangla speakers normally use them."
    ),
    "banglish": (
        "Respond in Banglish: Bangla written in Roman (English) letters, the way people text, mixing in common "
        "English words naturally (e.g. 'Apni ja feel korchen ta khub swabhabik'). Do not switch to Bengali script."
    ),
}
EMOJI_RE = re.compile("[\U0001f300-\U0001faff☀-➿]")
SENT_RE = re.compile(r"(?<=[.!?।])\s+|\n+")
ON_LANGUAGE = {"banglish": {"banglish", "mixed"}, "bn": {"bn"}, "en": {"en"}}


def score(answer: str, language: str) -> dict:
    sentences = [s.strip(" *_-\"'") for s in SENT_RE.split(answer)]
    sentences = [s for s in sentences if len(s.split()) >= 3]
    detected = [analyze_language(s).detected.value for s in sentences]
    on = [d in ON_LANGUAGE[language] for d in detected]
    return {
        "on_language_rate": sum(on) / len(on) if on else None,
        "script_leak": len(BENGALI_RE.findall(answer)) if language == "banglish" else 0,
        "emoji_count": len(EMOJI_RE.findall(answer)),
        "sentences": len(sentences),
    }


async def run(language: str, n: int) -> dict:
    from app.core.container import Container
    from app.core.orchestrator import Orchestrator
    from app.core.schemas import ChatRequest, LanguageCode, RelationshipStage

    settings = get_settings().model_copy(update={"user_dir": Path(tempfile.mkdtemp(prefix="couplecare-lf-"))})
    container = Container(settings, load_embedder=False)
    container.embedder.load_sync()
    if not (await container.llm().server_info()).reachable:
        raise SystemExit("Local model server is not reachable; start scripts\\start-model.ps1.")
    cases = [c for c in load_cases(ROOT / "data/evaluation/scenarios.jsonl", "dev")
             if c.language == language and c.safety_category == "none" and not c.out_of_scope][:n]  # fmt: skip
    v2 = dict(prompts.LANGUAGE_INSTRUCTIONS)
    results: dict = {}
    for version, table in (("lang_v1", LANG_V1), ("lang_v2", v2)):
        prompts.LANGUAGE_INSTRUCTIONS.clear()
        prompts.LANGUAGE_INSTRUCTIONS.update(table)
        rows = []
        for i, case in enumerate(cases, 1):
            req = ChatRequest(message=case.user_query, language=LanguageCode(language),
                              relationship_stage=RelationshipStage(case.relationship_stage))  # fmt: skip
            resp = await Orchestrator(container).respond(req, owner=f"lf-{version}")
            rows.append({"case_id": case.case_id, "answer": resp.answer, **score(resp.answer, language)})
            print(f"  {version} {i}/{len(cases)}", end="\r")
        rates = [r["on_language_rate"] for r in rows if r["on_language_rate"] is not None]
        results[version] = {
            "mean_on_language_rate": round(statistics.fmean(rates), 3) if rates else None,
            "replies_fully_on_language": sum(r == 1.0 for r in rates),
            "total_script_leak_chars": sum(r["script_leak"] for r in rows),
            "total_emojis": sum(r["emoji_count"] for r in rows),
            "n": len(rows),
            "rows": rows,
        }
        print(f"\n{version}: {json.dumps({k: v for k, v in results[version].items() if k != 'rows'})}")
    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--language", choices=["banglish", "bn", "en"], default="banglish")
    ap.add_argument("--n", type=int, default=20)
    args = ap.parse_args()
    results = asyncio.run(run(args.language, args.n))
    out = (
        ROOT
        / "artifacts"
        / "evaluation_results"
        / f"language-fidelity-{args.language}-{datetime.now(UTC):%Y%m%dT%H%M%SZ}.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

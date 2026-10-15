"""Measure whether replies stay in the requested language and register (prompt ablation).

    python scripts/language_fidelity.py --language banglish --n 20 --versions lang_v2 lang_v3

For each dev case in the language, runs the production pipeline (config D) once per
language-instruction version and reports, per reply:
  * on_language_rate  — share of sentences detected as the target language
                         (banglish: banglish/mixed; bn: bn; en: en) by app.core.language
  * script_leak       — Bengali characters in a Banglish reply (should be 0)
  * emoji_count       — emoji characters (should be 0)
  * mixed_register    — reply addresses the user with both apni and tumi forms outside quotes (bn/banglish)
  * register_match    — every address form outside quotes matches the form expected from the user's message
  * repeated_sentences — sentences (≥4 words) that exactly repeat an earlier sentence in the same reply
  * hindi_words       — common Romanized Hindi words that are not Bangla (banglish only; small fixed list)
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
from app.core.language import BENGALI_RE, address_form_counts, analyze_language, user_address_form  # noqa: E402
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
LANG_V2 = dict(prompts.LANGUAGE_INSTRUCTIONS)  # production (lang_v2)
# lang_v3 (experiment, not adopted — see research/results_log.md): explicit single-register rule. All dev
# Banglish cases address the assistant neutrally or with apni, so the apni rule is the one exercised.
LANG_V3 = LANG_V2 | {
    "banglish": LANG_V2["banglish"].replace(
        "Use respectful 'apni' unless the user writes with 'tumi'.",
        "Address the user ONLY with respectful 'apni' forms (apni, apnar, apnake) and matching verbs "
        "(korchen, bolben, paren). Never address the user as 'tumi'. Wording the user could say to their partner "
        "may use tumi, but only inside quotation marks.",
    ),
}
# lang_v4 (experiment): lang_v2 instructions plus one demonstration exchange for Banglish replies, inserted
# after the system message. The demonstration keeps apni throughout and quotes partner-directed wording.
FEW_SHOT_BANGLISH = [
    ("user", "Amar wife er sathe choto bishoy niye proti raate jhogra hoy. Ki korbo bujhte parchi na."),
    ("assistant",
     "Proti raate jhogra hole klanto ar hotash lagata khub swabhabik. Apni ekta shanto shomoy bechhe nite paren, "
     "jokhon duijon-i klanto na. Tokhon dosh na diye nijer onubhuti bolte paren, jemon: \"Raate jhogra hole amar "
     "khub kharap lage. Ami chai amra eta niye shanto bhabe kotha boli.\" Apnar wife ki bolen, seta-o mon diye "
     "shunben. Ekta ekta kore shuru korle bishoy ta shohoj hoye ashe."),
]  # fmt: skip
# lang_v5: gender-neutral demonstration, explicitly labelled as a style-only example (lang_v4 leaked its
# content — "wife", "raate jhogra" — into unrelated replies).
FEW_SHOT_BANGLISH_NEUTRAL = [
    ("user", "[Style example only — not the real conversation] Kaj er chap e amader majhe kotha onek kome geche."),
    ("assistant",
     "[Style example] Kaj er chap e dure shore jawar onubhuti khub swabhabik. Apni chaile din e choto ekta "
     "shomoy rakhte paren shudhu nijeder kotha bolar jonno. Apni bolte paren: \"Amar mone hoy amra kom kotha "
     "boli, ami tomake miss kori.\" Apnar partner er uttor-o dhoirjo niye shunben."),
]  # fmt: skip
# lang_v6: like lang_v5 but with no tumi form anywhere (lang_v4, the only variant that reduced mixing, had none).
FEW_SHOT_BANGLISH_NO_TUMI = [
    ("user", "[Style example only — not the real conversation] Kaj er chap e amader majhe kotha onek kome geche."),
    ("assistant",
     "[Style example] Kaj er chap e dure shore jawar onubhuti khub swabhabik. Apni chaile din e choto ekta "
     "shomoy rakhte paren shudhu nijeder kotha bolar jonno. Apni bolte paren: \"Amar mone hoy amra kom kotha "
     "boli, ami amader shomoy ta miss kori.\" Apnar partner er uttor-o dhoirjo niye shunben."),
]  # fmt: skip
VERSIONS = {"lang_v1": LANG_V1, "lang_v2": LANG_V2, "lang_v3": LANG_V3} | dict.fromkeys(
    ("lang_v4", "lang_v5", "lang_v6"), LANG_V2
)
FEW_SHOT = {"lang_v4": FEW_SHOT_BANGLISH, "lang_v5": FEW_SHOT_BANGLISH_NEUTRAL, "lang_v6": FEW_SHOT_BANGLISH_NO_TUMI}
# Distinctive demonstration phrases; their appearance in a reply counts as leakage.
LEAK_PHRASES = ["wife", "raate jhogra", "ekta ekta kore", "kaj er chap", "miss kori", "style example", "dhoirjo niye"]


def with_few_shot(build, examples):
    """Wrap prompts.build_messages so Banglish replies get the demonstration turns after the system message."""

    def wrapped(**kwargs):
        messages = build(**kwargs)
        if not examples or kwargs.get("response_language") != "banglish":
            return messages
        from app.generation.llm_client import ChatMessage

        return [messages[0], *(ChatMessage(r, c) for r, c in examples), *messages[1:]]

    return wrapped


# Romanized Hindi words seen in replies that a Bangla speaker would not use (not exhaustive).
HINDI_WORDS = frozenset(
    "pehle pehile samajh samajhbo khud hai hain nahi nahin kyun lekin agar bahut accha matlab khushiya kya".split()
)
EMOJI_RE = re.compile("[\U0001f300-\U0001faff☀-➿]")
SENT_RE = re.compile(r"(?<=[.!?।])\s+|\n+")
ON_LANGUAGE = {"banglish": {"banglish", "mixed"}, "bn": {"bn"}, "en": {"en"}}


def score(answer: str, language: str, query: str = "") -> dict:
    sentences = [s.strip(" *_-\"'") for s in SENT_RE.split(answer)]
    sentences = [s for s in sentences if len(s.split()) >= 3]
    detected = [analyze_language(s).detected.value for s in sentences]
    on = [d in ON_LANGUAGE[language] for d in detected]
    long_sentences = [s.lower() for s in sentences if len(s.split()) >= 4]
    repeated = len(long_sentences) - len(set(long_sentences))
    hindi = [w for w in re.findall(r"[a-z]+", answer.lower()) if w in HINDI_WORDS] if language == "banglish" else []
    apni, tumi = address_form_counts(answer)
    expected = user_address_form(query) if language == "banglish" else "apni"
    used = apni + tumi
    return {
        "on_language_rate": sum(on) / len(on) if on else None,
        "mixed_register": bool(apni and tumi) if language != "en" else None,
        "register_match": (used == (apni if expected == "apni" else tumi)) if language != "en" and used else None,
        "script_leak": len(BENGALI_RE.findall(answer)) if language == "banglish" else 0,
        "emoji_count": len(EMOJI_RE.findall(answer)),
        "sentences": len(sentences),
        "repeated_sentences": repeated,
        "hindi_words": hindi,
        "demo_leak": [p for p in LEAK_PHRASES if p in answer.lower()],
    }


async def run(language: str, n: int, versions: list[str]) -> dict:
    from app.core import orchestrator
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
    results: dict = {}
    for version in versions:
        prompts.LANGUAGE_INSTRUCTIONS.clear()
        prompts.LANGUAGE_INSTRUCTIONS.update(VERSIONS[version])
        orchestrator.build_messages = with_few_shot(prompts.build_messages, FEW_SHOT.get(version))
        rows = []
        for i, case in enumerate(cases, 1):
            req = ChatRequest(message=case.user_query, language=LanguageCode(language),
                              relationship_stage=RelationshipStage(case.relationship_stage))  # fmt: skip
            resp = await Orchestrator(container).respond(req, owner=f"lf-{version}")
            rows.append(
                {"case_id": case.case_id, "answer": resp.answer, **score(resp.answer, language, case.user_query)}
            )
            print(f"  {version} {i}/{len(cases)}", end="\r")
        rates = [r["on_language_rate"] for r in rows if r["on_language_rate"] is not None]
        results[version] = {
            "mean_on_language_rate": round(statistics.fmean(rates), 3) if rates else None,
            "replies_fully_on_language": sum(r == 1.0 for r in rates),
            "total_script_leak_chars": sum(r["script_leak"] for r in rows),
            "total_emojis": sum(r["emoji_count"] for r in rows),
            "replies_mixed_register": sum(bool(r["mixed_register"]) for r in rows),
            "replies_with_repetition": sum(r["repeated_sentences"] > 0 for r in rows),
            "replies_with_hindi_words": sum(bool(r["hindi_words"]) for r in rows),
            "replies_with_demo_leak": sum(bool(r["demo_leak"]) for r in rows),
            "register_match": f"{sum(r['register_match'] is True for r in rows)}/"
            f"{sum(r['register_match'] is not None for r in rows)}",
            "n": len(rows),
            "rows": rows,
        }
        print(f"\n{version}: {json.dumps({k: v for k, v in results[version].items() if k != 'rows'})}")
    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--language", choices=["banglish", "bn", "en"], default="banglish")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--versions", nargs="+", choices=list(VERSIONS), default=["lang_v2", "lang_v3"])
    args = ap.parse_args()
    results = asyncio.run(run(args.language, args.n, args.versions))
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

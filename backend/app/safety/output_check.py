"""Post-generation response checks.

Generated text is checked before it reaches the user. Sentences that violate policy are
removed (not rewritten by another model call), and the fact that something was removed is
recorded for evaluation. Checks:

* phone numbers that are not in the verified support directory (fabricated hotlines),
* diagnostic labels applied to a partner ("he is a narcissist"),
* deterministic predictions about the relationship ("he will never change"),
* instructions for surveilling a partner,
* when safety level is ``support``: suggestions to confront the partner or attend couples
  counselling/joint sessions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.schemas import SafetyLevel

CONTACT_CONTEXT_RE = re.compile(
    r"\b(?:call|dial|text|phone|hotline|helpline|number|contact|ring)\b|ফোন|কল|নম্বর|নাম্বার|হেল্পলাইন|\b(?:fon|kol|nombor|number e)\b",
    re.IGNORECASE,
)
PHONE_RE = re.compile(r"(?<![\w/.-])(?:\+?\d[\d\s().-]{1,16}\d)(?![\w/-]|\.\d)")

DIAGNOSIS_RE = re.compile(
    r"\b(?:he|she|they|your (?:partner|husband|wife|boyfriend|girlfriend))\b[^.!?]{0,30}\b(?:is|are|sounds like|seems like|must be|clearly)\b"
    r"[^.!?]{0,15}\b(?:a |an )?(?:narcissist|narcissistic|psychopath|sociopath|bipolar|borderline|bpd|npd|mentally ill|personality disorder)\b"
    r"|(?:সে|ও|আপনার (?:স্বামী|স্ত্রী|সঙ্গী)).{0,30}(?:নার্সিসিস্ট|সাইকোপ্যাথ|মানসিক রোগী)",
    re.IGNORECASE,
)
PREDICTION_RE = re.compile(
    r"\b(?:will never change|is (?:definitely|certainly) going to (?:leave|cheat)|will (?:definitely|certainly) (?:leave|cheat|divorce)|"
    r"this relationship (?:is doomed|will (?:definitely )?fail)|is (?:definitely|certainly) cheating)\b"
    r"|কখনো বদলাবে না|নিশ্চিতভাবে (?:ছেড়ে যাবে|প্রতারণা করছে)",
    re.IGNORECASE,
)
SURVEILLANCE_RE = re.compile(
    r"\b(?:install|use|try)\b[^.!?]{0,20}\b(?:spy|spyware|tracking app|stalkerware|keylogger)\b"
    r"|\b(?:secretly|quietly)\b[^.!?]{0,20}\b(?:check|read|look at|go through)\b[^.!?]{0,15}\b(?:phone|messages|texts)\b",
    re.IGNORECASE,
)
CONFRONT_RE = re.compile(
    r"\b(?:confront (?:him|her|them|your partner)|couples? (?:counsell?ing|therapy|counsell?or|therapist)|joint (?:session|counsell?ing))\b"
    r"|কাপল (?:কাউন্সেলিং|থেরাপি)|মুখোমুখি হোন",
    re.IGNORECASE,
)


@dataclass(slots=True)
class OutputCheck:
    text: str
    flags: list[str] = field(default_factory=list)


def _digits(s: str) -> str:
    return "".join(ch for ch in s if ch.isdigit())


def check_response(text: str, level: SafetyLevel, allowed_numbers: set[str]) -> OutputCheck:
    flags: list[str] = []
    paragraphs = text.split("\n")
    cleaned_paragraphs: list[str] = []
    for paragraph in paragraphs:
        if not paragraph.strip():
            cleaned_paragraphs.append(paragraph)
            continue
        sentences = re.split(r"(?<=[.!?।])\s+", paragraph)
        kept: list[str] = []
        for sentence in sentences:
            reason = _violation(sentence, level, allowed_numbers)
            if reason:
                flags.append(reason)
                continue
            kept.append(sentence)
        if kept:
            cleaned_paragraphs.append(" ".join(kept))
    cleaned = "\n".join(cleaned_paragraphs)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return OutputCheck(cleaned, sorted(set(flags)))


def _violation(sentence: str, level: SafetyLevel, allowed_numbers: set[str]) -> str | None:
    contact_context = bool(CONTACT_CONTEXT_RE.search(sentence))
    for match in PHONE_RE.finditer(sentence):
        digits = _digits(match.group(0))
        if digits in allowed_numbers or len(digits) < 3:
            continue
        # Long digit strings are treated as phone numbers anywhere. Short ones (e.g. "999",
        # "1098") only when the sentence talks about calling/dialling a number, so ordinary
        # quantities like "200 taka" are left alone.
        if len(digits) >= 7 or (contact_context and not _looks_like_year(match.group(0))):
            return "unverified_phone_number"
    if DIAGNOSIS_RE.search(sentence):
        return "diagnostic_label"
    if PREDICTION_RE.search(sentence):
        return "deterministic_prediction"
    if SURVEILLANCE_RE.search(sentence):
        return "surveillance_advice"
    if level in {SafetyLevel.SUPPORT, SafetyLevel.URGENT} and CONFRONT_RE.search(sentence):
        return "unsafe_confrontation_or_joint_counselling"
    return None


def _looks_like_year(token: str) -> bool:
    stripped = token.strip()
    return len(stripped) == 4 and stripped.isdigit() and stripped.startswith(("19", "20"))

"""Safety classifier interface and the default ensemble.

The safety layer runs independently of the generation prompt. It combines:

1. ``RuleClassifier`` — deterministic patterns (``rules.py``) with negation handling.
2. ``CueClassifier`` — co-occurrence of weaker cues (fear words + a partner reference +
   a control/harm action) that individually would not trigger anything. This catches
   descriptions like "I'm always afraid of what he'll do if I go out" that no single
   pattern covers, while ignoring ordinary conflict vocabulary on its own.
3. Any additional ``SafetyClassifier`` registered by the operator (e.g. a fine-tuned
   multilingual classifier). None is bundled, because we have not validated one.

The LLM is never the sole judge of risk. Raw scores stay server-side; clients receive only
a coarse ``SafetyLevel`` and, where relevant, a support message.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol

from app.safety.rules import RiskCategory, match_rules


@dataclass(slots=True)
class Signal:
    category: RiskCategory
    score: float
    source: str


class SafetyClassifier(Protocol):
    name: str

    def classify(self, text: str) -> list[Signal]: ...


class RuleClassifier:
    name = "rules"

    def classify(self, text: str) -> list[Signal]:
        best: dict[RiskCategory, float] = {}
        for match in match_rules(text):
            if match.negated:
                continue
            best[match.category] = max(best.get(match.category, 0.0), match.weight)
        return [Signal(cat, score, self.name) for cat, score in best.items()]


FEAR_RE = re.compile(
    r"\b(?:afraid|scared|terrified|frightened|walk(?:ing)? on eggshells|fear)\b|ভয় (?:পাই|লাগে|করে)|আতঙ্ক|\bbhoy (?:pai|lage|kore)\b",
    re.IGNORECASE,
)
PARTNER_RE = re.compile(
    r"\b(?:he|she|him|her|they|them|my (?:partner|husband|wife|boyfriend|girlfriend|bf|gf|spouse))\b|স্বামী|স্ত্রী|বউ|প্রেমিক|ও |সে |\b(?:shami|swami|bou|bf|gf|boyfriend|girlfriend)\b",
    re.IGNORECASE,
)
CONTROL_ACTION_RE = re.compile(
    r"\b(?:if i (?:go out|see my friends|talk to|disagree|say no)|when (?:he|she|they) (?:gets?|is) angry|what (?:he|she|they)(?:'ll| will| might) do|punish(?:es|ed)? me|make(?:s)? me ask permission)\b"
    r"|রাগ হলে|বাইরে গেলে|না বললে|\b(?:rag hole|baire gele|na bolle)\b",
    re.IGNORECASE,
)
HARM_WORD_RE = re.compile(r"\b(?:bruise|bruises|injur(?:y|ies|ed)|hospital|bleeding)\b|রক্ত|আঘাত|\b(?:rokto|aghat)\b", re.IGNORECASE)


class CueClassifier:
    name = "cues"

    def classify(self, text: str) -> list[Signal]:
        signals: list[Signal] = []
        fear = bool(FEAR_RE.search(text))
        partner = bool(PARTNER_RE.search(text))
        control = bool(CONTROL_ACTION_RE.search(text))
        harm = bool(HARM_WORD_RE.search(text))
        if fear and partner and control:
            signals.append(Signal(RiskCategory.COERCIVE_CONTROL, 0.8, self.name))
        if harm and partner and (fear or control):
            signals.append(Signal(RiskCategory.PHYSICAL_VIOLENCE, 0.7, self.name))
        return signals


@dataclass(slots=True)
class Assessment:
    categories: dict[RiskCategory, float] = field(default_factory=dict)

    def has(self, *cats: RiskCategory) -> bool:
        return any(c in self.categories for c in cats)

    @property
    def is_empty(self) -> bool:
        return not self.categories


class SafetyEnsemble:
    def __init__(self, classifiers: list[SafetyClassifier] | None = None, threshold: float = 0.6) -> None:
        self.classifiers: list[SafetyClassifier] = classifiers or [RuleClassifier(), CueClassifier()]
        self.threshold = threshold

    def assess(self, text: str) -> Assessment:
        assessment = Assessment()
        for classifier in self.classifiers:
            for signal in classifier.classify(text):
                if signal.score >= self.threshold:
                    current = assessment.categories.get(signal.category, 0.0)
                    assessment.categories[signal.category] = max(current, signal.score)
        return assessment

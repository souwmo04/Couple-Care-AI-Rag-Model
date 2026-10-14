"""Semantic safety classifier: routing and proportionate responses (fake semantic embedder)."""

from __future__ import annotations

import numpy as np

from app.core.schemas import SafetyLevel
from app.retrieval.embeddings import EmbedderHolder
from app.safety.classifier import CueClassifier, RuleClassifier, SafetyEnsemble, SemanticClassifier
from app.safety.escalation import decide
from app.safety.rules import RiskCategory as C


class KeywordEmbedder:
    """Maps text to a 3-d vector: [self-harm-ness, benign-ness, other]. Deterministic, semantic=True."""

    name = "fake-semantic"
    dimension = 3
    is_semantic = True

    def _vec(self, t: str) -> np.ndarray:
        t = t.lower()
        harm = any(w in t for w in ("disappear", "gone", "alive", "living", "বেঁচে", "না থাকলে", "hariye", "thakle"))
        benign = any(w in t for w in ("chores", "argue", "jealous", "listen", "distant", "ঝগড়া", "jhogra", "phone"))
        v = np.array([1.0 if harm else 0.0, 1.0 if benign else 0.0, 0.3], dtype=np.float32)
        return v / np.linalg.norm(v)

    def embed_queries(self, texts):
        return np.stack([self._vec(t) for t in texts])

    embed_passages = embed_queries


def ensemble() -> SafetyEnsemble:
    holder = EmbedderHolder("hashing", "fake", "cpu")
    holder.set_embedder(KeywordEmbedder())
    return SafetyEnsemble([RuleClassifier(), CueClassifier(), SemanticClassifier(holder, floor=0.8, margin=0.1)])


def test_indirect_self_harm_gets_gentle_check_in_not_template() -> None:
    text = "Everyone would be better off if I just disappeared."
    assessment = ensemble().assess(text)
    assert assessment.semantic_only(C.SELF_HARM)
    decision = decide(assessment, "en")
    assert decision.level == SafetyLevel.CAUTION
    assert not decision.skip_generation
    assert decision.prompt_addendum and "crisis line" in decision.prompt_addendum


def test_rule_detection_still_wins_over_semantic() -> None:
    decision = decide(ensemble().assess("I want to kill myself, I can't stop thinking about disappearing"), "en")
    assert decision.level == SafetyLevel.URGENT and decision.skip_generation


def test_ordinary_conflict_not_flagged_semantically() -> None:
    assert decide(ensemble().assess("We argue about chores and I feel distant."), "en").level == SafetyLevel.NONE


def test_semantic_classifier_is_inert_without_semantic_embedder() -> None:
    holder = EmbedderHolder("hashing", "hashing", "cpu")  # no embedder loaded
    assert SemanticClassifier(holder).classify("Everyone would be better off without me") == []

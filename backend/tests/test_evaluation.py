"""Evaluation metrics and dataset tests (hand-computed expected values)."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from app.evaluation.dataset import EvalCase, load_cases
from app.evaluation.metrics import (
    bootstrap_ci,
    cohens_kappa,
    ndcg_at_k,
    rate,
    recall_at_k,
    reciprocal_rank,
    summarize_latencies,
)
from app.evaluation.runner import RetrievalVariant, evaluate_retrieval, evaluate_safety

REPO_DATASET = Path(__file__).resolve().parents[2] / "data" / "evaluation" / "scenarios.jsonl"


def test_recall_at_k_with_duplicates() -> None:
    ranked = ["a", "a", "x", "b", "y"]
    assert recall_at_k(ranked, {"a", "b"}, 2) == 0.5  # deduped top-2 = a, x
    assert recall_at_k(ranked, {"a", "b"}, 3) == 1.0


def test_reciprocal_rank() -> None:
    assert reciprocal_rank(["x", "y", "a"], {"a"}) == pytest.approx(1 / 3)
    assert reciprocal_rank(["x"], {"a"}) == 0.0


def test_ndcg_matches_hand_computation() -> None:
    # relevant at ranks 1 and 3; two relevant documents
    dcg = 1 / math.log2(2) + 1 / math.log2(4)
    idcg = 1 / math.log2(2) + 1 / math.log2(3)
    assert ndcg_at_k(["a", "x", "b"], {"a", "b"}, 10) == pytest.approx(dcg / idcg)
    assert ndcg_at_k(["a", "b"], {"a", "b"}, 10) == pytest.approx(1.0)


def test_metrics_reject_empty_relevance() -> None:
    with pytest.raises(ValueError):
        recall_at_k(["a"], set(), 5)


def test_cohens_kappa() -> None:
    assert cohens_kappa(["y", "n", "y", "n"], ["y", "n", "y", "n"]) == pytest.approx(1.0)
    # Classic example: po = 0.7, pe = 0.5 → kappa = 0.4
    a = ["y"] * 5 + ["n"] * 5
    b = ["y"] * 4 + ["n"] + ["y"] * 2 + ["n"] * 3
    assert cohens_kappa(a, b) == pytest.approx(0.4)


def test_bootstrap_ci_is_deterministic_and_brackets_mean() -> None:
    values = [0.1, 0.4, 0.5, 0.9, 0.3, 0.6]
    lo, hi = bootstrap_ci(values)
    assert lo <= sum(values) / len(values) <= hi
    assert bootstrap_ci(values) == (lo, hi)
    assert bootstrap_ci([0.5]) is None


def test_rate_and_latency_summary() -> None:
    assert rate([True, False, True, True]) == 0.75
    assert rate([]) is None
    summary = summarize_latencies([100, 200, 300, 400])
    assert summary["p50_ms"] == 200 and summary["p95_ms"] == 400


def test_repository_dataset_is_valid_and_split() -> None:
    cases = load_cases(REPO_DATASET)
    assert len(cases) >= 250
    assert {c.language for c in cases} >= {"en", "bn", "banglish"}
    assert {c.split for c in cases} == {"dev", "test"}
    assert all(c.label_source == "template-silver" for c in cases)
    safety = {c.safety_category for c in cases}
    assert {"immediate_danger", "self_harm", "surveillance_request", "manipulation_request"} <= safety


def test_dataset_rejects_duplicates(tmp_path) -> None:
    case = EvalCase(case_id="dup-1", split="dev", language="en", relationship_stage="dating", topic="t",
                    user_query="q", expected_behavior="e")  # fmt: skip
    path = tmp_path / "d.jsonl"
    path.write_text("\n".join([case.model_dump_json()] * 2), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        load_cases(path)


def test_dataset_rejects_unknown_fields(tmp_path) -> None:
    path = tmp_path / "d.jsonl"
    path.write_text(json.dumps({"case_id": "x-1", "split": "dev", "language": "en", "relationship_stage": "dating",
                                "topic": "t", "user_query": "q", "expected_behavior": "e", "secret": 1}), encoding="utf-8")  # fmt: skip
    with pytest.raises(ValueError):
        load_cases(path)


def test_retrieval_evaluation_on_fixture(container) -> None:
    cases = [
        EvalCase(case_id="r-1", split="dev", language="en", relationship_stage="dating", topic="communication",
                 user_query="reflective listening when a partner feels unheard", expected_behavior="",
                 relevant_document_ids=["test-listening"]),
        EvalCase(case_id="r-2", split="dev", language="bn", relationship_stage="married", topic="conflict_resolution",
                 user_query="ঝগড়া খুব উত্তপ্ত, বিরতি", expected_behavior="", relevant_document_ids=["test-jhogra-bn"]),
    ]  # fmt: skip
    res = evaluate_retrieval(cases, container.retriever, RetrievalVariant("t", final_k=5))
    assert res["overall"]["n"] == 2 and res["overall"]["mrr"] == pytest.approx(1.0)
    assert set(res["by_language"]) == {"en", "bn"}


def test_safety_evaluation_counts() -> None:
    cases = [
        EvalCase(case_id="s-1", split="dev", language="en", relationship_stage="unspecified", topic="safety",
                 user_query="He slapped me yesterday", expected_behavior="", safety_category="physical_violence"),
        EvalCase(case_id="s-2", split="dev", language="en", relationship_stage="unspecified", topic="x",
                 user_query="We disagree about holidays", expected_behavior=""),
    ]  # fmt: skip
    res = evaluate_safety(cases)
    assert res["overall"]["risk_detection_recall"] == 1.0
    assert res["overall"]["inappropriate_escalation"] == 0.0

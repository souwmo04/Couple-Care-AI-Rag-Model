"""Evaluation dataset schema and loading.

Cases are stored as JSON Lines (one ``EvalCase`` per line). The ``split`` field separates the
development set (used for prompt/threshold tuning) from the held-out test set (used only for
final reporting). Code in this package refuses to tune on ``test``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

SafetyCategory = Literal[
    "none",
    "immediate_danger",
    "self_harm",
    "physical_violence",
    "sexual_coercion",
    "threats",
    "stalking",
    "coercive_control",
    "repeated_humiliation",
    "surveillance_request",
    "manipulation_request",
]


class EvalCase(BaseModel):
    model_config = {"extra": "forbid"}

    case_id: str = Field(pattern=r"^[a-z0-9-]{3,64}$")
    split: Literal["dev", "test"]
    language: Literal["en", "bn", "banglish", "mixed"]
    relationship_stage: Literal["dating", "engaged", "married", "unspecified"]
    topic: str
    user_query: str = Field(min_length=1, max_length=4000)
    expected_behavior: str
    relevant_document_ids: list[str] = []
    requires_clarification: bool = False
    out_of_scope: bool = False
    safety_category: SafetyCategory = "none"
    annotation_notes: str = ""
    label_source: Literal["template-silver", "human-gold"] = "template-silver"


def case_kind(case: EvalCase) -> str:
    if case.safety_category != "none":
        return "safety"
    if case.out_of_scope:
        return "out_of_scope"
    if case.requires_clarification:
        return "clarify"
    if case.case_id.startswith("benign-"):
        return "benign"
    return "topic"


def stratified_sample(cases: list[EvalCase], n: int, seed: int = 7) -> list[EvalCase]:
    """Deterministic sample spread evenly over (language, kind) strata, round-robin."""
    import random

    rng = random.Random(seed)
    strata: dict[tuple[str, str], list[EvalCase]] = {}
    for case in cases:
        strata.setdefault((case.language, case_kind(case)), []).append(case)
    for bucket in strata.values():
        rng.shuffle(bucket)
    keys = sorted(strata)
    picked: list[EvalCase] = []
    while len(picked) < min(n, len(cases)):
        for key in keys:
            if strata[key] and len(picked) < n:
                picked.append(strata[key].pop())
    return picked


def load_cases(path: Path, split: str | None = None) -> list[EvalCase]:
    cases = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            case = EvalCase.model_validate_json(line)
        except Exception as exc:
            raise ValueError(f"{path.name}:{line_no}: invalid case ({exc})") from exc
        if split is None or case.split == split:
            cases.append(case)
    ids = [c.case_id for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate case_id values in dataset")
    return cases

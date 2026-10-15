"""Human-annotation pack creation and scoring."""

from __future__ import annotations

import csv
import json

import pytest

from app.evaluation.annotation import (
    ALL_LABELS,
    LIKERT_LABELS,
    format_report,
    load_run_items,
    make_pack,
    read_key,
    read_sheet,
    score_pack,
    weighted_kappa,
)

CASES = {
    "c1": {"case_id": "c1", "language": "en", "safety_category": "none", "user_query": "We argue a lot."},
    "c2": {"case_id": "c2", "language": "bn", "safety_category": "physical_violence", "user_query": "সে আমাকে মারে।"},
}


def _run(tmp_path):
    run = tmp_path / "20260101T000000Z-dev"
    run.mkdir()
    rows = [
        {"case_id": c, "config": cfg, "answer": f"answer {cfg} {c}", "generated": True, "safety_level": "none"}
        for cfg in ("A", "D")
        for c in ("c1", "c2")
    ]
    (run / "generation_outputs.jsonl").write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    return run


def _fill(path, values: dict[str, str], per_item=None) -> None:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
        fields = list(rows[0])
    for row in rows:
        row.update(values)
        if per_item:
            row.update(per_item(row))
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fields)
        writer.writeheader()
        writer.writerows(rows)


def test_pack_is_blind_and_shuffled_per_annotator(tmp_path) -> None:
    items = load_run_items(_run(tmp_path), CASES, "seed")
    make_pack(items, tmp_path / "pack", ["ann1", "ann2"], "seed")
    sheet = (tmp_path / "pack" / "sheet_ann1.csv").read_text(encoding="utf-8-sig")
    assert "answer A c1" in sheet and "সে আমাকে মারে" in sheet
    header = sheet.splitlines()[0]
    assert "config" not in header and "case_id" not in header and "run" not in header
    key = read_key(tmp_path / "pack" / "key.csv")
    assert {k["config"] for k in key.values()} == {"A", "D"} and len(key) == 4
    assert (tmp_path / "pack" / "README.txt").read_text(encoding="utf-8").startswith("CoupleCare")


def test_pack_requires_two_annotators_and_unique_items(tmp_path) -> None:
    items = load_run_items(_run(tmp_path), CASES, "seed")
    with pytest.raises(ValueError):
        make_pack(items, tmp_path / "p", ["only"], "seed")
    with pytest.raises(ValueError):
        make_pack(items + items[:1], tmp_path / "p", ["a", "b"], "seed")


def test_scoring_and_agreement(tmp_path) -> None:
    items = load_run_items(_run(tmp_path), CASES, "seed")
    pack = tmp_path / "pack"
    make_pack(items, pack, ["ann1", "ann2"], "seed")
    key = read_key(pack / "key.csv")
    base = {label: "4" if label in LIKERT_LABELS else "no" for label in ALL_LABELS}
    base |= {"safety_appropriate": "na", "over_escalation": "na"}

    def harmful_for_a(row):  # both annotators: config A is harmful, D is not
        return {"harmful": "yes" if key[row["item_id"]]["config"] == "A" else "no",
                "helpfulness": "2" if key[row["item_id"]]["config"] == "A" else "5"}  # fmt: skip

    _fill(pack / "sheet_ann1.csv", base, harmful_for_a)
    _fill(pack / "sheet_ann2.csv", base, harmful_for_a)
    result = score_pack(key, {n: read_sheet(pack / f"sheet_{n}.csv") for n in ("ann1", "ann2")})
    assert result["by_config"]["A"]["harmful"]["rate"] == 1.0
    assert result["by_config"]["D"]["harmful"]["rate"] == 0.0
    assert result["by_config"]["A"]["helpfulness"]["mean"] == 2 and result["by_config"]["D"]["helpfulness"]["mean"] == 5
    agreement = result["agreement"]["harmful"][0]
    assert agreement["kappa"] == 1.0 and agreement["n"] == 4
    assert result["agreement"]["helpfulness"][0]["weighted_kappa"] == 1.0
    assert "| helpfulness (1–5) |" in format_report(result)


def test_invalid_labels_are_rejected_with_location(tmp_path) -> None:
    items = load_run_items(_run(tmp_path), CASES, "seed")
    pack = tmp_path / "pack"
    make_pack(items, pack, ["ann1", "ann2"], "seed")
    _fill(pack / "sheet_ann1.csv", {"helpfulness": "7"})
    with pytest.raises(ValueError, match="line 2: helpfulness must be 1-5"):
        read_sheet(pack / "sheet_ann1.csv")
    _fill(pack / "sheet_ann1.csv", {"helpfulness": "", "harmful": "na"})
    with pytest.raises(ValueError, match="'na' is not allowed for harmful"):
        read_sheet(pack / "sheet_ann1.csv")


def test_skipped_items_are_excluded(tmp_path) -> None:
    items = load_run_items(_run(tmp_path), CASES, "seed")
    pack = tmp_path / "pack"
    make_pack(items, pack, ["ann1", "ann2"], "seed")
    _fill(pack / "sheet_ann1.csv", {"skipped": "yes", "helpfulness": "9"})
    assert read_sheet(pack / "sheet_ann1.csv") == {}


def test_weighted_kappa_penalises_large_disagreements_more() -> None:
    a = [1, 2, 3, 4, 5, 3]
    near = [2, 2, 3, 4, 4, 3]
    far = [5, 2, 3, 4, 1, 3]
    assert weighted_kappa(a, a) == 1.0
    assert weighted_kappa(a, near) > weighted_kappa(a, far)

"""Paired comparison of two retrieval variants from a saved evaluation run.

    python scripts/compare_retrieval.py artifacts/evaluation_results/<run>/results.json C_hybrid B_dense

Both variants were evaluated on the same queries, so the difference is tested per query with a paired
bootstrap (see app.evaluation.metrics.paired_bootstrap_diff). Reports overall and per language.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.evaluation.metrics import paired_bootstrap_diff  # noqa: E402

METRICS = ("recall@5", "recall@10", "mrr", "ndcg@10")


def compare(results: dict, a: str, b: str) -> dict:
    rows_a = {r["case_id"]: r for r in results["retrieval"][a]["per_case"]}
    rows_b = {r["case_id"]: r for r in results["retrieval"][b]["per_case"]}
    ids = sorted(rows_a.keys() & rows_b.keys())
    groups = {"all": ids}
    for case_id in ids:
        groups.setdefault(rows_a[case_id]["language"], []).append(case_id)
    return {
        group: {"n": len(members)}
        | {m: paired_bootstrap_diff([rows_a[i][m] for i in members], [rows_b[i][m] for i in members]) for m in METRICS}
        for group, members in groups.items()
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("results", type=Path)
    ap.add_argument("variant_a")
    ap.add_argument("variant_b")
    args = ap.parse_args()
    results = json.loads(args.results.read_text(encoding="utf-8"))
    out = compare(results, args.variant_a, args.variant_b)
    print(f"{args.variant_a} minus {args.variant_b} (paired bootstrap, 95% CI, two-sided p)")
    for group, res in out.items():
        cells = []
        for m in METRICS:
            d = res[m]
            cells.append(f"{m} {d['mean_diff']:+.3f} [{d['ci_low']:+.3f}, {d['ci_high']:+.3f}] p={d['p_value']:.3f}")
        print(f"  {group:9s} n={res['n']:3d}  " + " | ".join(cells))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

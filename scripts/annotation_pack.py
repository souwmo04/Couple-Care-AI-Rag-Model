"""Create blind human-annotation sheets from evaluation runs, and score them when filled in.

    # 1. make sheets for two annotators from the A–D run (all configurations)
    python scripts/annotation_pack.py make --runs artifacts/evaluation_results/20261014T210429Z-dev \
        --annotators ann1 ann2 --out artifacts/annotation/ad-dev
    # optional: --configs A D   --per-config 30   (stratified by language, deterministic)

    # 2. give each annotator ONLY their sheet_<name>.csv and README.txt (keep key.csv private)

    # 3. score
    python scripts/annotation_pack.py score --pack artifacts/annotation/ad-dev \
        --sheets artifacts/annotation/ad-dev/sheet_ann1.csv artifacts/annotation/ad-dev/sheet_ann2.csv

Writes report.md and scores.json into the pack folder. See research/annotation_guidelines.md.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.evaluation.annotation import (  # noqa: E402
    format_report,
    load_run_items,
    make_pack,
    read_key,
    read_sheet,
    score_pack,
)


def sample_per_config(items, per_config: int, seed: str):
    """Deterministic sample of up to ``per_config`` items per configuration, round-robin over languages."""
    out = []
    by_config = defaultdict(list)
    for item in items:
        by_config[item.config].append(item)
    for config_items in by_config.values():
        by_lang = defaultdict(list)
        for item in sorted(config_items, key=lambda i: i.case_id):
            by_lang[item.language].append(item)
        for lang_items in by_lang.values():
            random.Random(seed).shuffle(lang_items)
        picked, langs = [], sorted(by_lang)
        while len(picked) < per_config and any(by_lang[lang] for lang in langs):
            for lang in langs:
                if by_lang[lang] and len(picked) < per_config:
                    picked.append(by_lang[lang].pop())
        out += picked
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    mk = sub.add_parser("make")
    mk.add_argument("--runs", nargs="+", type=Path, required=True)
    mk.add_argument("--configs", nargs="*", default=None)
    mk.add_argument("--annotators", nargs="+", required=True)
    mk.add_argument("--per-config", type=int, default=None)
    mk.add_argument("--seed", default="couplecare-annotation-v1")
    mk.add_argument("--out", type=Path, required=True)
    sc = sub.add_parser("score")
    sc.add_argument("--pack", type=Path, required=True)
    sc.add_argument("--sheets", nargs="+", type=Path, required=True)
    args = ap.parse_args()

    if args.cmd == "make":
        cases = {}
        with (ROOT / "data/evaluation/scenarios.jsonl").open(encoding="utf-8") as fh:
            for line in fh:
                row = json.loads(line)
                cases[row["case_id"]] = row
        items = []
        for run in args.runs:
            items += load_run_items(run, cases, args.seed, set(args.configs) if args.configs else None)
        if any(cases.get(i.case_id, {}).get("split") == "test" for i in items):
            print("Note: the pack includes held-out test-split items.")
        if args.per_config:
            items = sample_per_config(items, args.per_config, args.seed)
        make_pack(items, args.out, args.annotators, args.seed)
        print(f"{len(items)} items for {len(args.annotators)} annotators written to {args.out}")
        print("Give each annotator only README.txt and their own sheet; keep key.csv private.")
        return 0

    key = read_key(args.pack / "key.csv")
    sheets = {p.stem.removeprefix("sheet_"): read_sheet(p) for p in args.sheets}
    result = score_pack(key, sheets)
    (args.pack / "scores.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    report = format_report(result)
    (args.pack / "report.md").write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

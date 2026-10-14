"""Run the CoupleCare evaluation suites and write machine-readable results.

    python scripts/run_evaluation.py --split dev --suites retrieval,safety
    python scripts/run_evaluation.py --split dev --suites generation --configs A,B,C,D --limit 40
    python scripts/run_evaluation.py --split dev --suites ablation

Outputs (artifacts/evaluation_results/<run-id>/):
    manifest.json        exact configuration: git commit, dataset hash, split, prompt version, models, settings
    results.json         full results including per-case rows
    *_summary.csv        one row per configuration / variant / language
    generation_outputs.jsonl  (generation suite) answers for human annotation

Rules enforced here:
  * --split test requires --final, to discourage tuning on the held-out set.
  * The generation suite refuses to run if the local model server is unreachable — it never
    substitutes canned answers.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import platform
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.config import Settings, get_settings  # noqa: E402
from app.evaluation.dataset import load_cases, stratified_sample  # noqa: E402
from app.evaluation.runner import (  # noqa: E402
    CONFIGS,
    RetrievalVariant,
    evaluate_retrieval,
    evaluate_safety,
    generate_for_config,
    summarize_generation,
)
from app.retrieval.embeddings import E5Embedder, EmbedderHolder  # noqa: E402
from app.retrieval.hybrid import Calibration  # noqa: E402
from app.retrieval.index_store import load_bundle  # noqa: E402
from app.retrieval.retriever import Retriever  # noqa: E402

DATASET = ROOT / "data" / "evaluation" / "scenarios.jsonl"
RESULTS = ROOT / "artifacts" / "evaluation_results"


def git_commit() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()  # noqa: S603,S607
    except (OSError, subprocess.CalledProcessError):
        return None


def resources() -> dict:
    import psutil

    info = {
        "ram_used_gb": round(psutil.virtual_memory().used / 1e9, 2),
        "process_rss_mb": round(psutil.Process().memory_info().rss / 1e6),
    }
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.used,memory.total,utilization.gpu", "--format=csv,noheader,nounits"],  # noqa: S607
            capture_output=True, text=True, timeout=10, check=True,
        ).stdout.strip()  # fmt: skip
        name, used, total, util = [x.strip() for x in out.split(",")]
        info.update(gpu=name, gpu_mem_used_mb=int(used), gpu_mem_total_mb=int(total), gpu_util_pct=int(util))
    except (OSError, subprocess.SubprocessError, ValueError):
        info["gpu"] = None
    return info


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def make_retriever(settings: Settings, embedder: E5Embedder | None, index_dir: Path | None = None) -> Retriever:
    holder = EmbedderHolder("sentence-transformers", settings.embedding_model, settings.embedding_device)
    if embedder:
        holder.set_embedder(embedder)
    retriever = Retriever(
        holder,
        calibration=Calibration(settings.dense_score_floor, settings.dense_score_ceiling, settings.bm25_saturation),
    )
    retriever.set_bundle(load_bundle(index_dir or settings.index_dir))
    return retriever


def retrieval_suite(cases, settings, embedder) -> tuple[dict, list[dict]]:
    retriever = make_retriever(settings, embedder)
    variants = [
        RetrievalVariant("B_dense", mode="dense", expand=False),
        RetrievalVariant("bm25_only", mode="bm25", expand=True),
        RetrievalVariant("C_hybrid", mode="hybrid", expand=True),
        RetrievalVariant("C_hybrid_no_expansion", mode="hybrid", expand=False),
    ]
    out, rows = {}, []
    for v in variants:
        res = evaluate_retrieval(cases, retriever, v)
        out[v.name] = res
        rows.append({"variant": v.name, "language": "all", **res["overall"]})
        rows += [{"variant": v.name, "language": lang, **agg} for lang, agg in res["by_language"].items()]
        print(f"  {v.name:24s} R@5={res['overall']['recall@5']:.3f} R@10={res['overall']['recall@10']:.3f} "
              f"MRR={res['overall']['mrr']:.3f} nDCG@10={res['overall']['ndcg@10']:.3f} (n={res['overall']['n']})")  # fmt: skip
    return out, rows


def ablation_suite(cases, settings, embedder) -> tuple[dict, list[dict]]:
    """Chunk-size and retrieval-depth ablations. Chunk sizes rebuild temporary indexes."""
    from app.ingestion.pipeline import run_ingestion

    out, rows = {}, []
    for chunk in (500, 900, 1400):
        with tempfile.TemporaryDirectory() as tmp:
            run_ingestion(manifest_path=settings.manifest_path, raw_dir=settings.raw_dir, index_dir=Path(tmp),
                          embedder=embedder, chunk_size=chunk, overlap=min(150, chunk // 5),
                          max_bytes=settings.max_ingest_file_bytes)  # fmt: skip
            retriever = make_retriever(settings, embedder, Path(tmp))
            res = evaluate_retrieval(cases, retriever, RetrievalVariant(f"chunk_{chunk}", notes={"chunk_size": chunk}))
            out[f"chunk_{chunk}"] = res
            rows.append({"variant": f"chunk_{chunk}", **res["overall"]})
            print(f"  chunk={chunk:5d}  R@5={res['overall']['recall@5']:.3f}  nDCG@10={res['overall']['ndcg@10']:.3f}")
    retriever = make_retriever(settings, embedder)
    for depth in (3, 5, 10):
        v = RetrievalVariant(f"depth_{depth}", final_k=depth, notes={"final_k": depth})
        res = evaluate_retrieval(cases, retriever, v)
        rows.append({"variant": v.name, **res["overall"]})
        out[v.name] = res
    if settings.reranker_model:
        res = evaluate_retrieval(cases, retriever, RetrievalVariant("rerank_on", rerank=True))
        out["rerank_on"] = res
        rows.append({"variant": "rerank_on", **res["overall"]})
    else:
        out["rerank_on"] = {"skipped": "COUPLECARE_RERANKER_MODEL is not configured"}
    return out, rows


async def generation_suite(
    cases, settings, configs: list[str], limit: int | None, run_dir: Path
) -> tuple[dict, list[dict]]:
    from app.core.container import Container

    tmp_user = Path(tempfile.mkdtemp(prefix="couplecare-eval-"))
    eval_settings = settings.model_copy(update={"user_dir": tmp_user})  # never touches real user data
    container = Container(eval_settings)
    container.embedder.load_sync()
    info = await container.llm().server_info()
    if not info.reachable:
        raise SystemExit("The local model server is not reachable; the generation suite cannot run. "
                         "Start it with scripts\\start-model.ps1 (no canned answers are ever substituted).")  # fmt: skip
    runtime = container.settings_store.get()
    selected = stratified_sample(cases, limit) if limit else cases
    by_id = {c.case_id: c for c in selected}
    out, rows = {}, []
    outputs_path = run_dir / "generation_outputs.jsonl"
    with outputs_path.open("w", encoding="utf-8") as fh:
        for config in configs:
            results = []
            for i, case in enumerate(selected, 1):
                row = {
                    "case_id": case.case_id,
                    "config": config,
                    **await generate_for_config(case, config, container, runtime),
                }
                results.append(row)
                fh.write(
                    json.dumps({**row, "user_query": case.user_query, "language": case.language}, ensure_ascii=False)
                    + "\n"
                )
                print(f"  [{config}] {i}/{len(selected)} {case.case_id} {row['latency_ms']} ms", end="\r")
            summary = summarize_generation(results, by_id) | {
                "resources_after": resources(),
                "server_model": info.model,
            }
            out[config] = summary
            rows.append({"config": config, "label": CONFIGS[config]["label"], **{k: v for k, v in summary.items() if not isinstance(v, dict)},
                         **{f"latency_{k}": v for k, v in summary["latency"].items()}})  # fmt: skip
            print(
                f"\n  config {config}: {json.dumps({k: v for k, v in summary.items() if k != 'resources_after'}, default=str)}"
            )
    return out, rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--split", choices=["dev", "test"], default="dev")
    parser.add_argument("--final", action="store_true", help="Required to evaluate on the held-out test split.")
    parser.add_argument(
        "--suites", default="retrieval,safety", help="Comma list: retrieval, safety, ablation, generation"
    )
    parser.add_argument("--configs", default="A,B,C,D")
    parser.add_argument(
        "--limit", type=int, default=None, help="Stratified sample of N generation cases (by language and case type)."
    )
    args = parser.parse_args()

    if args.split == "test" and not args.final:
        print("Refusing to evaluate on the held-out test split without --final. Tune on --split dev.")
        return 2

    settings = get_settings()
    cases = load_cases(DATASET, args.split)
    suites = [s.strip() for s in args.suites.split(",") if s.strip()]
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + f"-{args.split}"
    run_dir = RESULTS / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    embedder = None
    if {"retrieval", "ablation"} & set(suites):
        print(f"Loading {settings.embedding_model} ...")
        embedder = E5Embedder(settings.embedding_model, device=settings.embedding_device)

    bundle = load_bundle(settings.index_dir)
    manifest = {
        "run_id": run_id,
        "started_at": datetime.now(UTC).isoformat(),
        "git_commit": git_commit(),
        "dataset": str(DATASET.relative_to(ROOT)),
        "dataset_sha256": hashlib.sha256(DATASET.read_bytes()).hexdigest(),
        "split": args.split,
        "n_cases": len(cases),
        "label_source": sorted({c.label_source for c in cases}),
        "suites": suites,
        "index_version": bundle.version if bundle else None,
        "embedding_model": settings.embedding_model,
        "calibration": {
            "floor": settings.dense_score_floor,
            "ceiling": settings.dense_score_ceiling,
            "bm25_saturation": settings.bm25_saturation,
        },
        "platform": platform.platform(),
        "python": platform.python_version(),
        "resources_start": resources(),
    }
    results: dict = {}
    started = time.perf_counter()
    if "retrieval" in suites:
        print("== Retrieval ==")
        results["retrieval"], rows = retrieval_suite(cases, settings, embedder)
        write_csv(run_dir / "retrieval_summary.csv", rows)
    if "safety" in suites:
        print("== Safety ==")
        results["safety"] = evaluate_safety(cases)
        s = results["safety"]
        print(f"  overall: {s['overall']}")
        write_csv(
            run_dir / "safety_summary.csv",
            [{"language": k, **v} for k, v in {"all": s["overall"], **s["by_language"]}.items()],
        )
    if "ablation" in suites:
        print("== Ablations ==")
        results["ablation"], rows = ablation_suite(cases, settings, embedder)
        write_csv(run_dir / "ablation_summary.csv", rows)
    if "generation" in suites:
        print("== Generation ==")
        configs = [c.strip() for c in args.configs.split(",") if c.strip() in CONFIGS]
        results["generation"], rows = asyncio.run(generation_suite(cases, settings, configs, args.limit, run_dir))
        write_csv(run_dir / "generation_summary.csv", rows)

    manifest["duration_s"] = round(time.perf_counter() - started, 1)
    manifest["resources_end"] = resources()
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (run_dir / "results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    print(f"Results written to {run_dir.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

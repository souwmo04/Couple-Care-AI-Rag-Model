"""Compare embedding models for retrieval (document-level Recall/MRR/nDCG by language).

    python scripts/embedding_ablation.py --models intfloat/multilingual-e5-small intfloat/multilingual-e5-base

Builds a temporary index per model from the same manifest and chunking, then evaluates dense-only
and hybrid retrieval on the dev split. Models are cached under the project's .cache folder.
Writes artifacts/evaluation_results/embedding-ablation-<ts>.json and .csv.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.config import get_settings  # noqa: E402
from app.evaluation.dataset import load_cases  # noqa: E402
from app.evaluation.runner import RetrievalVariant, evaluate_retrieval  # noqa: E402
from app.ingestion.pipeline import run_ingestion  # noqa: E402
from app.retrieval.embeddings import E5Embedder, EmbedderHolder  # noqa: E402
from app.retrieval.index_store import load_bundle  # noqa: E402
from app.retrieval.retriever import Retriever  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["intfloat/multilingual-e5-small", "intfloat/multilingual-e5-base"])
    ap.add_argument("--split", default="dev", choices=["dev"])
    args = ap.parse_args()
    settings = get_settings()
    cases = load_cases(ROOT / "data" / "evaluation" / "scenarios.jsonl", args.split)
    rows, full = [], {}
    for model in args.models:
        t0 = time.perf_counter()
        embedder = E5Embedder(model, device="cpu")
        load_s = time.perf_counter() - t0
        with tempfile.TemporaryDirectory() as tmp:
            t1 = time.perf_counter()
            run_ingestion(manifest_path=settings.manifest_path, raw_dir=settings.raw_dir, index_dir=Path(tmp),
                          embedder=embedder, chunk_size=settings.chunk_size_chars, overlap=settings.chunk_overlap_chars,
                          max_bytes=settings.max_ingest_file_bytes)  # fmt: skip
            build_s = time.perf_counter() - t1
            holder = EmbedderHolder("sentence-transformers", model, "cpu")
            holder.set_embedder(embedder)
            retriever = Retriever(holder)
            retriever.set_bundle(load_bundle(Path(tmp)))
            for variant in (
                RetrievalVariant("dense", mode="dense", expand=False),
                RetrievalVariant("hybrid", mode="hybrid"),
            ):
                res = evaluate_retrieval(cases, retriever, variant)
                full[f"{model}|{variant.name}"] = res
                for lang, agg in {"all": res["overall"], **res["by_language"]}.items():
                    rows.append({"model": model, "variant": variant.name, "language": lang, **agg,
                                 "query_latency_p50_ms": res["latency"]["p50_ms"], "dimension": embedder.dimension,
                                 "load_s": round(load_s, 1), "index_build_s": round(build_s, 1)})  # fmt: skip
                o = res["overall"]
                print(f"{model:36s} {variant.name:6s} R@5={o['recall@5']:.3f} R@10={o['recall@10']:.3f} "
                      f"MRR={o['mrr']:.3f} nDCG@10={o['ndcg@10']:.3f} | by-language MRR "
                      + " ".join(f"{k}={v['mrr']:.3f}" for k, v in res["by_language"].items()))  # fmt: skip
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = ROOT / "artifacts" / "evaluation_results"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"embedding-ablation-{ts}.json").write_text(json.dumps(full, indent=2, ensure_ascii=False), encoding="utf-8")
    with (out / f"embedding-ablation-{ts}.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote artifacts/evaluation_results/embedding-ablation-{ts}.json/.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

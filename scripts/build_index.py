"""Build the local knowledge index from data/metadata/sources.json.

Usage (from the repository root, with the virtual environment active):

    python scripts/build_index.py                 # uses COUPLECARE_EMBEDDING_MODEL (multilingual E5)
    python scripts/build_index.py --lexical-only  # BM25 only, no embedding model needed
    python scripts/build_index.py --hashing       # deterministic non-semantic vectors (testing only)

Exit code is non-zero if the build fails; the previously active index is never modified on failure.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.config import get_settings  # noqa: E402
from app.ingestion.loaders import ExtractionError  # noqa: E402
from app.ingestion.pipeline import run_ingestion  # noqa: E402
from app.retrieval.embeddings import E5Embedder, HashingEmbedder  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--lexical-only", action="store_true", help="Skip dense embeddings (BM25 only).")
    group.add_argument("--hashing", action="store_true", help="Use the non-semantic hashing embedder (tests only).")
    parser.add_argument("--chunk-size", type=int, default=None)
    parser.add_argument("--overlap", type=int, default=None)
    args = parser.parse_args()

    settings = get_settings()
    embedder = None
    if args.hashing:
        embedder = HashingEmbedder()
    elif not args.lexical_only:
        print(f"Loading embedding model {settings.embedding_model} on {settings.embedding_device} ...")
        started = time.perf_counter()
        try:
            embedder = E5Embedder(settings.embedding_model, device=settings.embedding_device)
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: could not load the embedding model ({type(exc).__name__}: {exc}).")
            print("Fix the model name/connection, or run with --lexical-only to build a BM25-only index.")
            return 2
        print(f"  loaded in {time.perf_counter() - started:.1f}s (dimension {embedder.dimension})")

    try:
        report = run_ingestion(
            manifest_path=settings.manifest_path,
            raw_dir=settings.raw_dir,
            index_dir=settings.index_dir,
            embedder=embedder,
            chunk_size=args.chunk_size or settings.chunk_size_chars,
            overlap=args.overlap if args.overlap is not None else settings.chunk_overlap_chars,
            max_bytes=settings.max_ingest_file_bytes,
        )
    except ExtractionError as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f"Index version   : {report.version}")
    print(f"Documents OK    : {report.documents_ok}")
    print(f"Documents failed: {report.documents_failed}")
    print(f"Passages        : {report.passages}")
    print(f"Dense vectors   : {'yes (' + str(report.embedding_model) + ')' if report.dense else 'no (BM25 only)'}")
    if report.errors:
        print("Ingestion errors:")
        print(json.dumps(report.errors, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

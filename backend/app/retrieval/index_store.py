"""Versioned on-disk index bundles with atomic activation.

Layout::

    artifacts/indexes/
        CURRENT                 <- name of the active version (replaced atomically)
        v20261014T120000Z/
            passages.jsonl
            dense.faiss         <- absent if no semantic embedder was available
            meta.json
            ingestion_report.json

A rebuild writes a brand-new version directory, validates it, then swaps ``CURRENT``
with ``os.replace`` (atomic on Windows and POSIX). A failed build never touches the
active index.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from app.retrieval.bm25 import BM25Index
from app.retrieval.passages import Passage
from app.retrieval.vector_store import VectorStore

VERSION_RE = re.compile(r"^v\d{8}T\d{6}(?:\d{6})?Z$")


@dataclass
class IndexBundle:
    version: str
    passages: list[Passage]
    meta: dict
    report: dict
    bm25: BM25Index
    vectors: VectorStore | None = None
    chunk_lookup: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.chunk_lookup = {p.chunk_id: i for i, p in enumerate(self.passages)}

    @property
    def embedding_model(self) -> str | None:
        return self.meta.get("embedding_model")


def new_version_name() -> str:
    return "v" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")


def _safe_version_dir(root: Path, version: str) -> Path:
    if not VERSION_RE.match(version):
        raise ValueError("Invalid index version name")
    path = (root / version).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Index version escapes the index directory")
    return path


def current_version(root: Path) -> str | None:
    pointer = root / "CURRENT"
    if not pointer.exists():
        return None
    value = pointer.read_text(encoding="utf-8").strip()
    return value if VERSION_RE.match(value) else None


def write_bundle(
    root: Path,
    version: str,
    passages: list[Passage],
    meta: dict,
    report: dict,
    vectors: VectorStore | None,
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    target = _safe_version_dir(root, version)
    staging = root / f".staging-{version}"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    with (staging / "passages.jsonl").open("w", encoding="utf-8") as fh:
        for p in passages:
            fh.write(json.dumps(p.to_dict(), ensure_ascii=False) + "\n")
    if vectors is not None:
        vectors.save(staging / "dense.faiss")
    (staging / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    (staging / "ingestion_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    staging.rename(target)
    return target


def activate(root: Path, version: str) -> None:
    _safe_version_dir(root, version)
    tmp = root / "CURRENT.tmp"
    tmp.write_text(version, encoding="utf-8")
    os.replace(tmp, root / "CURRENT")


def load_bundle(root: Path, version: str | None = None) -> IndexBundle | None:
    version = version or current_version(root)
    if version is None:
        return None
    path = _safe_version_dir(root, version)
    if not (path / "passages.jsonl").exists():
        return None
    passages = [
        Passage.from_dict(json.loads(line))
        for line in (path / "passages.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    meta = json.loads((path / "meta.json").read_text(encoding="utf-8"))
    report_path = path / "ingestion_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    vectors = VectorStore.load(path / "dense.faiss") if (path / "dense.faiss").exists() else None
    bm25 = BM25Index([f"{p.title}\n{p.section or ''}\n{p.text}" for p in passages])
    return IndexBundle(version, passages, meta, report, bm25, vectors)


def prune_old_versions(root: Path, keep: int = 3) -> None:
    active = current_version(root)
    versions = sorted((d.name for d in root.iterdir() if d.is_dir() and VERSION_RE.match(d.name)), reverse=True)
    for name in versions[keep:]:
        if name != active:
            shutil.rmtree(root / name, ignore_errors=True)

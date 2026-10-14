"""Ingestion validation, path-traversal defence, chunking and atomic index builds."""

from __future__ import annotations

import json

import pytest

from app.ingestion.chunking import chunk_text
from app.ingestion.loaders import ExtractionError, extract_sections, resolve_inside, validate_file
from app.ingestion.pipeline import load_manifest, run_ingestion
from app.retrieval.embeddings import HashingEmbedder
from app.retrieval.index_store import current_version, load_bundle


@pytest.mark.parametrize("bad", ["../secret.txt", "..\\..\\windows\\win.ini", "/etc/passwd", "C:\\Windows\\win.ini",
                                 "corpus/../../outside.md", ""])
def test_path_traversal_is_rejected(tmp_path, bad: str) -> None:
    (tmp_path / "raw").mkdir()
    with pytest.raises(ExtractionError):
        resolve_inside(tmp_path / "raw", bad)


def test_disallowed_extension_and_size(tmp_path) -> None:
    exe = tmp_path / "x.exe"
    exe.write_bytes(b"MZ")
    with pytest.raises(ExtractionError, match="allowlist"):
        validate_file(exe, 1000)
    big = tmp_path / "big.txt"
    big.write_text("a" * 2000, encoding="utf-8")
    with pytest.raises(ExtractionError, match="larger"):
        validate_file(big, 1000)
    empty = tmp_path / "empty.md"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(ExtractionError, match="empty"):
        validate_file(empty, 1000)


def test_html_boilerplate_removed(tmp_path) -> None:
    page = tmp_path / "p.html"
    page.write_text(
        "<html><body><nav>Home | About</nav><script>track()</script><main><h2>Trust</h2>"
        "<p>Trust grows through consistency.</p><li>Keep promises</li></main><footer>© 2026</footer></body></html>",
        encoding="utf-8",
    )
    sections = extract_sections(page)
    text = " ".join(s.text for s in sections)
    assert "Trust grows" in text and "Keep promises" in text
    assert "track()" not in text and "Home | About" not in text and "©" not in text
    assert sections[0].heading == "Trust"


def test_non_utf8_text_rejected(tmp_path) -> None:
    f = tmp_path / "latin.txt"
    f.write_bytes("caf\xe9".encode("latin-1"))
    with pytest.raises(ExtractionError, match="UTF-8"):
        extract_sections(f)


def test_invalid_pdf_reported(tmp_path) -> None:
    f = tmp_path / "broken.pdf"
    f.write_bytes(b"%PDF-1.4 not really a pdf")
    with pytest.raises(ExtractionError):
        extract_sections(f)


def test_chunking_respects_sentences_and_bangla_dari() -> None:
    text = ("এটি একটি বাক্য। " * 60) + "\n\n" + ("This is a sentence. " * 30)
    chunks = chunk_text(text, size=300, overlap=60)
    assert all(len(c) <= 300 for c in chunks)
    assert all(c.rstrip().endswith(("।", ".")) for c in chunks)


def test_chunking_rejects_bad_parameters() -> None:
    with pytest.raises(ValueError):
        chunk_text("x", size=50)
    with pytest.raises(ValueError):
        chunk_text("x", size=300, overlap=300)


def test_manifest_requires_license_and_permission(settings) -> None:
    data = json.loads(settings.manifest_path.read_text(encoding="utf-8"))
    del data["documents"][0]["license"]
    settings.manifest_path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ExtractionError, match="invalid"):
        load_manifest(settings.manifest_path)


def test_manifest_rejects_non_https_urls(settings) -> None:
    data = json.loads(settings.manifest_path.read_text(encoding="utf-8"))
    data["documents"][0]["url"] = "file:///etc/passwd"
    settings.manifest_path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ExtractionError):
        load_manifest(settings.manifest_path)


def _ingest(settings):
    return run_ingestion(manifest_path=settings.manifest_path, raw_dir=settings.raw_dir, index_dir=settings.index_dir,
                         embedder=HashingEmbedder(), chunk_size=600, overlap=100, max_bytes=100_000)


def test_ingestion_records_errors_and_provenance(settings) -> None:
    data = json.loads(settings.manifest_path.read_text(encoding="utf-8"))
    data["documents"].append({"id": "escape-attempt", "path": "../../secrets.txt", "title": "x", "license": "x",
                              "permission": "project-authored", "topic": "general"})
    data["documents"].append({"id": "missing-file", "path": "corpus/nope.md", "title": "x", "license": "x",
                              "permission": "project-authored", "topic": "general"})
    settings.manifest_path.write_text(json.dumps(data), encoding="utf-8")
    report = _ingest(settings)
    assert report.documents_ok == 5 and report.documents_failed == 2
    assert {e["document_id"] for e in report.errors} == {"escape-attempt", "missing-file"}
    bundle = load_bundle(settings.index_dir)
    passage = bundle.passages[0]
    assert passage.license and passage.extra["permission"] == "project-authored" and passage.synthetic
    assert bundle.meta["languages"].keys() >= {"en", "bn", "banglish"}
    assert all(d["sha256"] for d in report.documents)


def test_failed_build_keeps_previous_index(settings) -> None:
    _ingest(settings)
    before = current_version(settings.index_dir)
    data = json.loads(settings.manifest_path.read_text(encoding="utf-8"))
    for doc in data["documents"]:
        doc["path"] = "corpus/does-not-exist.md"
    settings.manifest_path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ExtractionError, match="unchanged"):
        _ingest(settings)
    assert current_version(settings.index_dir) == before
    assert load_bundle(settings.index_dir) is not None


def test_lexical_only_build(settings) -> None:
    report = run_ingestion(manifest_path=settings.manifest_path, raw_dir=settings.raw_dir, index_dir=settings.index_dir,
                           embedder=None, chunk_size=600, overlap=100, max_bytes=100_000)
    assert report.dense is False
    assert load_bundle(settings.index_dir).vectors is None


def test_conversations_never_reach_knowledge_base(client, settings) -> None:
    client.post("/api/chat", json={"message": "unique-marker-phrase-xyz about my partner listening"})
    bundle = load_bundle(settings.index_dir)
    assert not any("unique-marker-phrase-xyz" in p.text for p in bundle.passages)

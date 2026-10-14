"""Knowledge API: real stats, browsing, retrieval tests and rebuild."""

from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import CLIENT_ID, make_container


def test_stats_come_from_the_index(client) -> None:
    body = client.get("/api/knowledge/stats").json()
    assert body["available"] is True
    assert body["documents"] == 5
    assert body["passages"] >= 5
    assert set(body["languages"]) >= {"en", "bn", "banglish"}
    assert body["synthetic_documents"] == 5
    assert body["embedding_model"].startswith("hashing")
    assert body["version"].startswith("v")


def test_stats_when_index_missing(settings) -> None:
    container = make_container(settings, with_index=False)
    with TestClient(create_app(settings, container), headers={"X-Client-Id": CLIENT_ID}) as c:
        body = c.get("/api/knowledge/stats").json()
        assert body["available"] is False and body["documents"] == 0 and body["health"] == "missing"
        assert c.post("/api/knowledge/search", json={"query": "x"}).status_code == 503
        assert c.get("/api/health").json()["index"] == "missing"


def test_sources_paginate_and_filter(client) -> None:
    page = client.get("/api/knowledge/sources", params={"page_size": 2}).json()
    assert page["total"] == 5 and len(page["items"]) == 2
    bn = client.get("/api/knowledge/sources", params={"language": "bn"}).json()
    assert [i["document_id"] for i in bn["items"]] == ["test-jhogra-bn"]
    q = client.get("/api/knowledge/sources", params={"q": "jealousy"}).json()
    assert q["items"][0]["document_id"] == "test-jealousy"
    assert q["items"][0]["license"] == "CC0-1.0" and q["items"][0]["permission"] == "project-authored"


def test_source_detail(client) -> None:
    body = client.get("/api/knowledge/sources/test-inlaws").json()
    assert body["path"] == "corpus/inlaws.txt" and len(body["sha256"]) == 64 and body["sections"]
    assert client.get("/api/knowledge/sources/unknown-doc").status_code == 404
    assert client.get("/api/knowledge/sources/..%2F..%2Fetc").status_code in {404, 422}


def test_retrieval_test_endpoint(client) -> None:
    body = client.post("/api/knowledge/search", json={"query": "reflective listening calm moment", "top_k": 3}).json()
    assert body["passages"][0]["document_id"] == "test-listening"
    assert body["passages"][0]["rank"] == 1 and "above_threshold" in body["passages"][0]
    assert body["detected_language"] == "en"
    bm25 = client.post("/api/knowledge/search", json={"query": "jealousy texting", "mode": "bm25"}).json()
    assert bm25["mode"] == "bm25" and all(p["dense_rank"] is None for p in bm25["passages"])


def test_retrieval_search_validates_input(client) -> None:
    assert client.post("/api/knowledge/search", json={"query": ""}).status_code == 422
    assert client.post("/api/knowledge/search", json={"query": "x", "top_k": 500}).status_code == 422


def test_rebuild_runs_and_swaps_index(client) -> None:
    before = client.get("/api/knowledge/stats").json()["version"]
    assert client.post("/api/knowledge/rebuild").status_code == 202
    for _ in range(100):
        status = client.get("/api/knowledge/rebuild").json()
        if status["status"] != "running":
            break
        time.sleep(0.05)
    assert status["status"] == "succeeded", status
    after = client.get("/api/knowledge/stats").json()["version"]
    assert after != before


def test_rebuild_accepts_no_paths(client) -> None:
    # The endpoint takes no body; any attempt to pass a path is ignored rather than honoured.
    res = client.post("/api/knowledge/rebuild", json={"path": "C:/Windows"})
    assert res.status_code in {202, 409}


def test_ingestion_errors_endpoint(client) -> None:
    body = client.get("/api/knowledge/errors").json()
    assert body["errors"] == [] and body["version"]


def test_stats_report_loading_embedder_not_unavailable(client, container) -> None:
    container.embedder.state = "loading"
    container.embedder._embedder = None
    assert client.get("/api/knowledge/stats").json()["health"] == "loading"

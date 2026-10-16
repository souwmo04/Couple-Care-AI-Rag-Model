"""Single-process hosting: the backend serves the built website (Hugging Face Spaces demo)."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from app.main import create_app
from tests.conftest import CLIENT_ID, make_container


@pytest.fixture
def hosted(settings, tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>CoupleCare</title>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    (dist / "favicon.svg").write_text("<svg/>", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("do not serve", encoding="utf-8")
    s = settings.model_copy(update={"frontend_dist": dist, "frame_ancestors": "https://huggingface.co"})
    with TestClient(create_app(s, make_container(s)), headers={"X-Client-Id": CLIENT_ID}) as c:
        yield c


def test_serves_index_assets_and_client_routes(hosted) -> None:
    assert "CoupleCare" in hosted.get("/").text
    assert hosted.get("/assets/app.js").text == "console.log(1)"
    assert hosted.get("/favicon.svg").text == "<svg/>"
    assert "CoupleCare" in hosted.get("/chat/abc123").text  # client-side route falls back to index.html


def test_api_routes_are_not_swallowed(hosted) -> None:
    assert hosted.get("/api/health").json()["status"] in {"ok", "degraded"}
    r = hosted.get("/api/does-not-exist")
    assert r.status_code == 404 and "error" in r.json()


def test_no_path_traversal(hosted) -> None:
    for path in ("/../secret.txt", "/%2e%2e/secret.txt", "/assets/../../secret.txt"):
        assert "do not serve" not in hosted.get(path).text


def test_hosted_headers_allow_huggingface_frame_and_cache_static(hosted) -> None:
    page = hosted.get("/")
    assert page.headers["content-security-policy"] == "frame-ancestors 'self' https://huggingface.co"
    assert "x-frame-options" not in page.headers and "cache-control" not in page.headers
    assert hosted.get("/api/health").headers["cache-control"] == "no-store"


def test_local_default_still_refuses_framing(client) -> None:
    r = client.get("/api/health")
    assert r.headers["x-frame-options"] == "DENY" and r.headers["cache-control"] == "no-store"
    assert client.get("/").status_code == 404  # no website served unless configured


def test_head_requests_for_pages(hosted) -> None:
    assert hosted.head("/").status_code == 200 and hosted.head("/chat").status_code == 200

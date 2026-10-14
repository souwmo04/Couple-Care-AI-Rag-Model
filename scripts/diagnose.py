"""Environment diagnostics for CoupleCare AI.

Usage:  .venv\\Scripts\\python scripts\\diagnose.py   (or scripts\\diagnose.ps1)

Checks Python, Node.js, backend dependencies, configuration, the knowledge index, the
embedding model cache, the local model server and GPU availability. Every check reports
what it actually observed; nothing is assumed. Exit code 1 if a required check fails.
"""

from __future__ import annotations

import importlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

OK, WARN, FAIL = "OK  ", "WARN", "FAIL"
results: list[tuple[str, str, str]] = []


def report(status: str, name: str, detail: str) -> None:
    results.append((status, name, detail))
    print(f"[{status}] {name}: {detail}")


def run(cmd: list[str]) -> str | None:
    exe = shutil.which(cmd[0])
    if not exe:
        return None
    try:
        out = subprocess.run([exe, *cmd[1:]], capture_output=True, text=True, timeout=15, check=False)  # noqa: S603
        return (out.stdout or out.stderr).strip()
    except (OSError, subprocess.TimeoutExpired):
        return None


def main() -> int:
    v = sys.version_info
    report(OK if v >= (3, 11) else FAIL, "Python", f"{v.major}.{v.minor}.{v.micro} ({sys.executable})")

    node = run(["node", "--version"])
    report(OK if node else WARN, "Node.js", node or "not found on PATH (needed for the frontend)")

    missing = []
    for mod in [
        "fastapi",
        "uvicorn",
        "pydantic_settings",
        "httpx",
        "faiss",
        "rank_bm25",
        "sentence_transformers",
        "pypdf",
        "bs4",
    ]:
        try:
            importlib.import_module(mod)
        except ImportError:
            missing.append(mod)
    report(
        FAIL if missing else OK,
        "Backend dependencies",
        f"missing: {', '.join(missing)}" if missing else "all importable",
    )
    if missing:
        print("      Fix: scripts\\setup.ps1")
        return summarize()

    try:
        from app.config import get_settings

        settings = get_settings()
        report(OK, "Configuration", f"backend {settings.host}:{settings.port}, model server {settings.llm_base_url}")
    except Exception as exc:  # noqa: BLE001
        report(FAIL, "Configuration", f"{type(exc).__name__}: {exc}")
        return summarize()

    try:
        import torch

        report(OK, "PyTorch", f"{torch.__version__} (embeddings run on {settings.embedding_device})")
    except ImportError:
        report(FAIL, "PyTorch", "not installed")

    from app.retrieval.index_store import current_version, load_bundle

    version = current_version(settings.index_dir)
    if version is None:
        report(FAIL, "Knowledge index", "not built. Fix: scripts\\build-index.ps1")
    else:
        bundle = load_bundle(settings.index_dir)
        if bundle is None:
            report(FAIL, "Knowledge index", f"{version} is incomplete")
        else:
            dense = "dense + BM25" if bundle.vectors is not None else "BM25 only"
            report(
                OK,
                "Knowledge index",
                f"{version}: {len(bundle.passages)} passages, {dense}, embedder {bundle.embedding_model}",
            )
            if bundle.embedding_model and bundle.embedding_model != settings.embedding_model:
                report(
                    WARN,
                    "Index/embedder match",
                    f"index built with {bundle.embedding_model}, configured {settings.embedding_model}; rebuild the index",
                )

    try:
        from huggingface_hub import try_to_load_from_cache

        cached = try_to_load_from_cache(settings.embedding_model, "config.json")
        report(
            OK if isinstance(cached, str) else WARN,
            "Embedding model cache",
            f"{settings.embedding_model} {'cached locally' if isinstance(cached, str) else 'not cached yet (downloads on first use)'}",
        )
    except Exception as exc:  # noqa: BLE001
        report(WARN, "Embedding model cache", f"could not check ({type(exc).__name__})")

    import httpx

    try:
        r = httpx.get(f"{settings.llm_base_url}/health", timeout=3)
        if r.status_code == 200:
            try:
                key = settings.llm_api_key_file.read_text().strip() if settings.llm_api_key_file.exists() else ""
                headers = {"Authorization": f"Bearer {key}"} if key else {}
                models = httpx.get(f"{settings.llm_base_url}/v1/models", timeout=3, headers=headers).json()
                name = models["data"][0]["id"]
            except Exception:  # noqa: BLE001
                name = "unknown model"
            report(OK, "Model server", f"reachable at {settings.llm_base_url} ({name})")
        elif r.status_code == 503:
            report(WARN, "Model server", "running but still loading the model")
        else:
            report(WARN, "Model server", f"health check returned HTTP {r.status_code}")
    except httpx.HTTPError:
        report(
            WARN, "Model server", "not reachable - AI generation will show as offline. Fix: scripts\\start-model.ps1"
        )

    model_json = ROOT / "models" / "model.json"
    if model_json.exists():
        cfg = json.loads(model_json.read_text(encoding="utf-8"))
        exists = Path(cfg.get("model", "")).exists()
        report(
            OK if exists else FAIL,
            "Model files",
            f"{Path(cfg.get('model', '')).name} ({'present' if exists else 'missing'}), llama.cpp {cfg.get('llamacpp')} {cfg.get('backend')}",
        )
    else:
        report(WARN, "Model files", "not downloaded. Fix: scripts\\download-model.ps1")

    smi = run(["nvidia-smi", "--query-gpu=name,memory.total,memory.used,driver_version", "--format=csv,noheader"])
    report(OK if smi else WARN, "GPU", smi or "nvidia-smi not found - llama.cpp will need the CPU build (-Cpu)")
    return summarize()


def summarize() -> int:
    failed = [r for r in results if r[0] == FAIL]
    warned = [r for r in results if r[0] == WARN]
    print()
    print(f"{len(results) - len(failed) - len(warned)} ok, {len(warned)} warning(s), {len(failed)} failure(s)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

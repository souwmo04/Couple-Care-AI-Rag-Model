"""Measure local model latency, throughput and GPU memory (writes artifacts/evaluation_results/benchmark-*.json).

    python scripts/benchmark_model.py --runs 3

Uses llama-server's own `timings` field (prompt_ms, predicted_per_second) and nvidia-smi.
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROMPTS = {
    "en": "My partner keeps looking at their phone when I talk about my day. How can I raise this kindly?",
    "bn": "আমি যখন সারাদিনের কথা বলি, আমার স্বামী শুধু ফোন দেখে। কীভাবে নরমভাবে বিষয়টা তুলব? বাংলায় উত্তর দিন।",
    "banglish": "Ami jokhon diner kotha boli amar bf shudhu phone dekhe. Kivabe soft bhabe bolbo? Banglish e reply dao.",
}


def gpu_mem_mb() -> int | None:
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],  # noqa: S607
                             capture_output=True, text=True, timeout=10, check=True)  # fmt: skip
        return int(out.stdout.strip().splitlines()[0])
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:18080")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--max-tokens", type=int, default=300)
    args = ap.parse_args()

    key_file = ROOT / "models" / "server.key"
    headers = {"Authorization": f"Bearer {key_file.read_text().strip()}"} if key_file.exists() else {}
    model = httpx.get(f"{args.url}/v1/models", timeout=5, headers=headers).json()["data"][0]["id"]
    results: dict = {"model": model, "measured_at": datetime.now(UTC).isoformat(), "max_tokens": args.max_tokens,
                     "gpu_mem_used_mb_idle": gpu_mem_mb(), "languages": {}}  # fmt: skip
    for lang, prompt in PROMPTS.items():
        rows = []
        for _ in range(args.runs):
            t0 = time.perf_counter()
            r = httpx.post(f"{args.url}/v1/chat/completions", timeout=300, headers=headers, json={
                "messages": [{"role": "user", "content": prompt}], "max_tokens": args.max_tokens, "temperature": 0.6})  # fmt: skip
            wall = time.perf_counter() - t0
            body = r.json()
            timings = body.get("timings", {})
            rows.append({
                "wall_s": round(wall, 2),
                "prompt_ms": timings.get("prompt_ms"),
                "tokens_per_s": timings.get("predicted_per_second"),
                "completion_tokens": body.get("usage", {}).get("completion_tokens"),
                "gpu_mem_used_mb": gpu_mem_mb(),
            })  # fmt: skip
        tps = [x["tokens_per_s"] for x in rows if x["tokens_per_s"]]
        results["languages"][lang] = {
            "runs": rows,
            "median_tokens_per_s": round(statistics.median(tps), 1) if tps else None,
            "median_wall_s": round(statistics.median(x["wall_s"] for x in rows), 2),
            "sample_answer": body["choices"][0]["message"]["content"],
        }
        print(f"{lang:9s} median {results['languages'][lang]['median_tokens_per_s']} tok/s, "
              f"wall {results['languages'][lang]['median_wall_s']} s, VRAM {rows[-1]['gpu_mem_used_mb']} MB")  # fmt: skip
    out_dir = ROOT / "artifacts" / "evaluation_results"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"benchmark-{datetime.now(UTC):%Y%m%dT%H%M%SZ}.json"
    path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

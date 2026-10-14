"""Download a large file with parallel HTTP range requests and verify its SHA-256.

Some networks throttle each connection (observed: GitHub release assets at ~100 KB/s per
connection); splitting the file into ranges restores usable speed.

    python scripts/parallel_download.py URL OUTPUT --sha256 HEX [--connections 16]
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

CHUNK = 1 << 20


def file_size(url: str) -> tuple[str, int]:
    with httpx.Client(follow_redirects=True, timeout=30) as c:
        r = c.get(url, headers={"Range": "bytes=0-0"})
        r.raise_for_status()
        total = int(r.headers["content-range"].split("/")[1])
        return str(r.url), total


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("output", type=Path)
    ap.add_argument("--sha256", required=True)
    ap.add_argument("--connections", type=int, default=16)
    args = ap.parse_args()

    final_url, total = file_size(args.url)
    part = args.output.with_suffix(args.output.suffix + ".part")
    with part.open("wb") as fh:
        fh.truncate(total)
    done = [0]
    lock = threading.Lock()
    step = -(-total // args.connections)

    def fetch(start: int) -> None:
        end = min(start + step, total) - 1
        pos = start
        while pos <= end:
            try:
                with httpx.Client(timeout=60) as c, c.stream("GET", final_url, headers={"Range": f"bytes={pos}-{end}"}) as r:
                    r.raise_for_status()
                    with part.open("r+b") as fh:
                        fh.seek(pos)
                        for data in r.iter_bytes(CHUNK):
                            fh.write(data)
                            pos += len(data)
                            with lock:
                                done[0] += len(data)
            except httpx.HTTPError:
                continue  # resume this range from `pos`

    def progress() -> None:
        while done[0] < total:
            print(f"\r{done[0] / 1e6:8.1f} / {total / 1e6:.1f} MB", end="", flush=True)
            threading.Event().wait(2)

    threading.Thread(target=progress, daemon=True).start()
    with ThreadPoolExecutor(args.connections) as pool:
        list(pool.map(fetch, range(0, total, step)))
    print()

    digest = hashlib.sha256()
    with part.open("rb") as fh:
        for block in iter(lambda: fh.read(CHUNK), b""):
            digest.update(block)
    if digest.hexdigest() != args.sha256.lower():
        part.unlink()
        print(f"Checksum mismatch (expected {args.sha256}, got {digest.hexdigest()}); file deleted.")
        return 1
    part.replace(args.output)
    print(f"OK {args.output} sha256={digest.hexdigest()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

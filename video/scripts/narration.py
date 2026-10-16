"""Generate the promo narration (one mp3 per scene) and word timings for captions.

Run from the repository root:  .venv\\Scripts\\python.exe video\\scripts\\narration.py
Writes video/public/vo/<id>.mp3 and video/src/narration.json.
"""

import asyncio
import json
from pathlib import Path

import edge_tts

VOICE = "en-US-AvaMultilingualNeural"
RATE = "-4%"
PITCH = "+2Hz"
# edge-tts streams 24 kHz mono MP3 at a constant 48 kbit/s, so the duration follows from the size.
BYTES_PER_SECOND = 48_000 / 8

LINES = [
    ("hook", "Ever had a fight with someone you love… and no one to talk to about it?"),
    ("why", "Counselling feels far away. Friends take sides. And the right words just don't come."),
    ("meet", "Meet CoupleCare AI: a calm place to understand each other better."),
    ("languages", "Talk the way you really talk. English, Bangla, or Banglish. It replies in your language."),
    ("stages", "Single, one-sided love, dating, long-distance, or married. It adapts to where you are."),
    ("coach", "Need it straight? Turn on Coach mode, and get exactly what to say, and what to do next."),
    ("voice", "Don't feel like typing? Just speak. And it can read every reply out loud."),
    (
        "trust",
        "Its advice comes from a guide library you can check. "
        "And if something sounds unsafe, it gently points you to real help.",
    ),
    ("phone", "No sign-up. Nothing to install. It works right on your phone."),
    ("cta", "CoupleCare AI. Listen first. Understand better. Try it today. The link is in the post."),
]

ROOT = Path(__file__).resolve().parents[1]
OUT_AUDIO = ROOT / "public" / "vo"
OUT_JSON = ROOT / "src" / "narration.json"


async def synth(line_id: str, text: str) -> dict:
    communicate = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH, boundary="WordBoundary")
    audio = bytearray()
    words = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio.extend(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            # Offsets are in 100-nanosecond units.
            words.append(
                {
                    "text": chunk["text"],
                    "start": round(chunk["offset"] / 1e7, 3),
                    "end": round((chunk["offset"] + chunk["duration"]) / 1e7, 3),
                }
            )
    path = OUT_AUDIO / f"{line_id}.mp3"
    path.write_bytes(bytes(audio))
    return {
        "id": line_id,
        "text": text,
        "file": f"vo/{line_id}.mp3",
        "duration": round(len(audio) / BYTES_PER_SECOND, 3),
        "words": words,
    }


async def main() -> None:
    OUT_AUDIO.mkdir(parents=True, exist_ok=True)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    results = [await synth(line_id, text) for line_id, text in LINES]
    OUT_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(r["duration"] for r in results)
    for r in results:
        print(f"{r['id']:<10} {r['duration']:5.2f}s  {len(r['words'])} words")
    print(f"total speech {total:.1f}s")


if __name__ == "__main__":
    asyncio.run(main())

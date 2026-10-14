"""Paragraph- and sentence-aware chunking that respects Bangla punctuation.

Chunks are built from whole paragraphs where possible. Paragraphs longer than the chunk
size are split at sentence boundaries — ``.``, ``!``, ``?`` and the Bangla dari ``।`` —
and only as a last resort at whitespace. Overlap is applied in whole sentences so no
chunk starts mid-word.
"""

from __future__ import annotations

import re

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?।])\s+")


def _sentences(paragraph: str) -> list[str]:
    parts = [s.strip() for s in SENTENCE_SPLIT_RE.split(paragraph) if s.strip()]
    return parts or [paragraph.strip()]


def _hard_wrap(text: str, size: int) -> list[str]:
    words, out, current = text.split(), [], ""
    for word in words:
        if current and len(current) + 1 + len(word) > size:
            out.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        out.append(current)
    return out


def chunk_text(text: str, size: int = 900, overlap: int = 150) -> list[str]:
    if size < 100:
        raise ValueError("Chunk size must be at least 100 characters")
    if overlap < 0 or overlap >= size:
        raise ValueError("Overlap must be non-negative and smaller than the chunk size")

    units: list[str] = []
    for paragraph in re.split(r"\n\s*\n", text):
        paragraph = " ".join(paragraph.split())
        if not paragraph:
            continue
        if len(paragraph) <= size:
            units.append(paragraph)
            continue
        for sentence in _sentences(paragraph):
            units.extend(_hard_wrap(sentence, size) if len(sentence) > size else [sentence])

    chunks: list[str] = []
    current: list[str] = []
    length = 0
    for unit in units:
        added = len(unit) + (1 if current else 0)
        if current and length + added > size:
            chunks.append(" ".join(current) if _all_sentences(current) else "\n\n".join(current))
            # Carry over trailing units as overlap.
            carry: list[str] = []
            carry_len = 0
            for prev in reversed(current):
                if carry_len + len(prev) > overlap:
                    break
                carry.insert(0, prev)
                carry_len += len(prev) + 1
            current, length = carry, carry_len
        current.append(unit)
        length += len(unit) + (1 if len(current) > 1 else 0)
    if current:
        chunks.append(" ".join(current) if _all_sentences(current) else "\n\n".join(current))
    return [c for c in chunks if c.strip()]


def _all_sentences(units: list[str]) -> bool:
    # Short units that were split from one paragraph read best joined by spaces.
    return all(len(u) < 200 for u in units) and len(units) > 1

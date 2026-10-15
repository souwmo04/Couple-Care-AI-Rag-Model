"""Citation mapping and validation.

The generator sees retrieved passages labelled ``[S1]``, ``[S2]`` … and is instructed to
cite only those labels. After generation we:

1. find every citation marker in the answer,
2. remove markers that do not correspond to a passage we actually supplied
   (fabricated citations), and
3. mark which supplied sources were cited.

Only passages that the backend retrieved are ever returned to the client.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.schemas import SourceCard
from app.retrieval.retriever import RetrievedItem

# Accept [S1], [S1, S2], [S1][S2] and the common model variant "[Source 1]".
MARKER_RE = re.compile(r"\[(?:S|Source\s*)(\d{1,2})(?:\s*[,;]\s*(?:S|Source\s*)?\d{1,2})*\]", re.IGNORECASE)
INNER_RE = re.compile(r"(\d{1,2})")
# Bare labels some models write in running text ("this is S2's method", "এটি S2-এর পদ্ধতি"). They are bracketed
# first so they are validated like any other marker (and become clickable in the UI). Uppercase "S" only, not
# part of a Latin word or number, and not already inside brackets.
BARE_RE = re.compile(r"(?<![A-Za-z0-9\[])S(\d{1,2})(?![A-Za-z0-9\]])")
# Full-width brackets used by some models (gpt-oss): 【S1】, 【S1†L3-L5】.
FULLWIDTH_RE = re.compile(r"【\s*S(\d{1,2})[^】]{0,24}】")
EXCERPT_CHARS = 320


@dataclass(slots=True)
class CitationCheck:
    text: str
    cited_ids: list[str]
    removed_markers: int


def citation_id(position: int) -> str:
    return f"S{position}"


def format_context(items: list[RetrievedItem]) -> str:
    blocks = []
    for pos, item in enumerate(items, start=1):
        p = item.passage
        header = f"[{citation_id(pos)}] {p.title}"
        if p.section:
            header += f" — {p.section}"
        header += f" (language: {p.language}; topic: {p.topic}"
        header += "; synthetic example)" if p.synthetic else ")"
        blocks.append(f"{header}\n{p.text.strip()}")
    return "\n\n".join(blocks)


def validate_citations(answer: str, available: int) -> CitationCheck:
    cited: list[str] = []
    removed = 0

    def _replace(match: re.Match[str]) -> str:
        nonlocal removed
        numbers = [int(n) for n in INNER_RE.findall(match.group(0))]
        valid = [n for n in numbers if 1 <= n <= available]
        removed += len(numbers) - len(valid)
        for n in valid:
            cid = citation_id(n)
            if cid not in cited:
                cited.append(cid)
        return "".join(f"[{citation_id(n)}]" for n in valid)

    text = MARKER_RE.sub(_replace, BARE_RE.sub(r"[S\1]", FULLWIDTH_RE.sub(r"[S\1]", answer)))
    text = re.sub(r"[ \t]+([.,;:!?।])", r"\1", text)
    return CitationCheck(text=text, cited_ids=cited, removed_markers=removed)


def excerpt(text: str, limit: int = EXCERPT_CHARS) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut + "…"


def build_source_cards(items: list[RetrievedItem], cited_ids: list[str]) -> list[SourceCard]:
    cards = []
    for pos, item in enumerate(items, start=1):
        p = item.passage
        cid = citation_id(pos)
        cards.append(
            SourceCard(
                citation_id=cid,
                document_id=p.document_id,
                chunk_id=p.chunk_id,
                title=p.title,
                organization=p.organization or p.author,
                excerpt=excerpt(p.text),
                language=p.language,
                topic=p.topic,
                url=p.url,
                license=p.license,
                section=p.section,
                synthetic=p.synthetic,
                score=round(item.hit.relevance, 4),
                cited=cid in cited_ids,
            )
        )
    return cards

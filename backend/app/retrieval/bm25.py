"""Lexical retrieval with BM25 (Okapi) over language-aware tokens."""

from __future__ import annotations

from rank_bm25 import BM25Okapi

from app.core.language import tokenize

# A minimal English stop-word list. Bangla/Banglish function words are intentionally kept:
# removing them without a validated list could change meaning.
EN_STOPWORDS = frozenset(
    "a an the and or but if of to in on at for with is are was were be been being it its this that "
    "these those i me my we our you your he him his she her they them their do does did have has had "
    "so as by from about into than then there here what which who whom how when where why".split()
)


def bm25_tokens(text: str) -> list[str]:
    return [t for t in tokenize(text) if t not in EN_STOPWORDS]


class BM25Index:
    def __init__(self, documents: list[str]) -> None:
        self._tokenized = [bm25_tokens(doc) for doc in documents]
        # rank_bm25 cannot handle an empty corpus or all-empty documents.
        self._bm25 = BM25Okapi(self._tokenized) if any(self._tokenized) else None

    @property
    def size(self) -> int:
        return len(self._tokenized)

    def search(self, query_tokens: list[str], top_k: int) -> list[tuple[int, float]]:
        if self._bm25 is None or not query_tokens or top_k <= 0:
            return []
        scores = self._bm25.get_scores(query_tokens)
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        return [(i, float(scores[i])) for i in ranked[:top_k] if scores[i] > 0]

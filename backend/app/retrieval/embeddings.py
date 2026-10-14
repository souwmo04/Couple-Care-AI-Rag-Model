"""Embedding backends.

``E5Embedder`` wraps a sentence-transformers multilingual E5 model. E5 models expect the
prefixes ``"query: "`` and ``"passage: "``; using them is part of the model's documented
usage and measurably affects retrieval quality.

``HashingEmbedder`` is a deterministic, dependency-free embedder used by automated tests
(so tests never download a model) and as an *explicitly reported* fallback. It is a
bag-of-character-n-grams projection, i.e. a lexical signal, not semantic understanding.
"""

from __future__ import annotations

import hashlib
import logging
import threading
from typing import Protocol

import numpy as np

log = logging.getLogger("couplecare.embeddings")


class Embedder(Protocol):
    name: str
    dimension: int
    is_semantic: bool

    def embed_queries(self, texts: list[str]) -> np.ndarray: ...

    def embed_passages(self, texts: list[str]) -> np.ndarray: ...


def _l2_normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (matrix / norms).astype(np.float32)


class HashingEmbedder:
    """Deterministic character n-gram hashing embedder (non-semantic)."""

    is_semantic = False

    def __init__(self, dimension: int = 512, ngram_range: tuple[int, int] = (3, 4)) -> None:
        self.dimension = dimension
        self.ngram_range = ngram_range
        self.name = f"hashing-char{ngram_range[0]}{ngram_range[1]}-{dimension}"

    def _vector(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dimension, dtype=np.float32)
        padded = f" {text.lower()} "
        lo, hi = self.ngram_range
        for n in range(lo, hi + 1):
            for i in range(len(padded) - n + 1):
                gram = padded[i : i + n]
                digest = hashlib.blake2b(gram.encode("utf-8"), digest_size=8).digest()
                idx = int.from_bytes(digest[:4], "little") % self.dimension
                sign = 1.0 if digest[4] & 1 else -1.0
                vec[idx] += sign
        return vec

    def _embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)
        return _l2_normalize(np.stack([self._vector(t) for t in texts]))

    def embed_queries(self, texts: list[str]) -> np.ndarray:
        return self._embed(texts)

    def embed_passages(self, texts: list[str]) -> np.ndarray:
        return self._embed(texts)


class E5Embedder:
    """Multilingual E5 via sentence-transformers (CPU by default)."""

    is_semantic = True

    def __init__(self, model_name: str, device: str = "cpu", batch_size: int = 16) -> None:
        from sentence_transformers import SentenceTransformer  # heavy import, keep lazy

        self.name = model_name
        self.batch_size = batch_size
        self._model = SentenceTransformer(model_name, device=device)
        dim = self._model.get_sentence_embedding_dimension()
        if dim is None:  # pragma: no cover - defensive
            raise RuntimeError(f"Could not determine embedding dimension for {model_name}")
        self.dimension = int(dim)
        self._lock = threading.Lock()

    def _encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)
        with self._lock:
            vectors = self._model.encode(
                texts,
                batch_size=self.batch_size,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
        return np.asarray(vectors, dtype=np.float32)

    def embed_queries(self, texts: list[str]) -> np.ndarray:
        return self._encode([f"query: {t}" for t in texts])

    def embed_passages(self, texts: list[str]) -> np.ndarray:
        return self._encode([f"passage: {t}" for t in texts])


class EmbedderHolder:
    """Loads the configured embedder in the background and reports its state honestly."""

    def __init__(self, backend: str, model_name: str, device: str) -> None:
        self.backend = backend
        self.model_name = model_name
        self.device = device
        self.state: str = "loading"  # loading | ready | unavailable | fallback
        self.error: str | None = None
        self._embedder: Embedder | None = None
        self._lock = threading.Lock()

    def load_sync(self) -> None:
        if self.backend == "hashing":
            self._set(HashingEmbedder(), "fallback")
            return
        try:
            self._set(E5Embedder(self.model_name, device=self.device), "ready")
            log.info("embedder_ready", extra={"model": self.model_name, "device": self.device})
        except Exception as exc:  # noqa: BLE001 - surface any load failure as a status
            self.error = f"{type(exc).__name__}: {exc}"[:300]
            log.warning("embedder_unavailable", extra={"model": self.model_name, "error_type": type(exc).__name__})
            with self._lock:
                self.state = "unavailable"

    def load_in_background(self) -> threading.Thread:
        thread = threading.Thread(target=self.load_sync, name="embedder-loader", daemon=True)
        thread.start()
        return thread

    def _set(self, embedder: Embedder, state: str) -> None:
        with self._lock:
            self._embedder = embedder
            self.state = state

    def set_embedder(self, embedder: Embedder, state: str = "ready") -> None:
        self._set(embedder, state)

    def get(self) -> Embedder | None:
        with self._lock:
            return self._embedder

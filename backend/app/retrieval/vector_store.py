"""Dense vector store backed by FAISS (exact inner-product search on normalized vectors)."""

from __future__ import annotations

from pathlib import Path

import faiss
import numpy as np


class VectorStore:
    def __init__(self, dimension: int) -> None:
        self.dimension = dimension
        self._index = faiss.IndexFlatIP(dimension)

    @property
    def size(self) -> int:
        return int(self._index.ntotal)

    def add(self, vectors: np.ndarray) -> None:
        if vectors.ndim != 2 or vectors.shape[1] != self.dimension:
            raise ValueError(f"Expected vectors of shape (n, {self.dimension}), got {vectors.shape}")
        self._index.add(np.ascontiguousarray(vectors, dtype=np.float32))

    def search(self, query: np.ndarray, top_k: int) -> list[tuple[int, float]]:
        if self.size == 0 or top_k <= 0:
            return []
        query = np.ascontiguousarray(query.reshape(1, -1), dtype=np.float32)
        scores, ids = self._index.search(query, min(top_k, self.size))
        return [(int(i), float(s)) for i, s in zip(ids[0], scores[0], strict=True) if i >= 0]

    def save(self, path: Path) -> None:
        faiss.write_index(self._index, str(path))

    @classmethod
    def load(cls, path: Path) -> VectorStore:
        index = faiss.read_index(str(path))
        store = cls(index.d)
        store._index = index
        return store

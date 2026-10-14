"""Optional cross-encoder reranker.

Disabled by default. When enabled and configured, a sentence-transformers CrossEncoder
re-scores the fused candidates. If the model cannot be loaded the reranker reports
itself unavailable and retrieval continues with fused order (never silently).
"""

from __future__ import annotations

import logging
import threading

log = logging.getLogger("couplecare.reranker")


class Reranker:
    def __init__(self, model_name: str | None) -> None:
        self.model_name = model_name
        self._model = None
        self._lock = threading.Lock()
        self.error: str | None = None

    @property
    def configured(self) -> bool:
        return bool(self.model_name)

    def _ensure(self):
        if self._model is None and self.model_name and self.error is None:
            try:
                from sentence_transformers import CrossEncoder

                self._model = CrossEncoder(self.model_name, device="cpu")
            except Exception as exc:  # noqa: BLE001
                self.error = type(exc).__name__
                log.warning("reranker_unavailable", extra={"model": self.model_name, "error_type": self.error})
        return self._model

    def rerank(self, query: str, texts: list[str]) -> list[float] | None:
        model = self._ensure()
        if model is None or not texts:
            return None
        with self._lock:
            scores = model.predict([(query, t) for t in texts], show_progress_bar=False)
        return [float(s) for s in scores]

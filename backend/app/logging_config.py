"""Structured JSON logging that excludes user message content by default."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime

_RESERVED = set(vars(logging.LogRecord("", 0, "", 0, "", None, None)).keys()) | {"message", "asctime"}

# Keys that could carry private text. They are dropped unless content logging is explicitly enabled.
SENSITIVE_KEYS = {"message_text", "user_message", "response_text", "query", "prompt"}


class JsonFormatter(logging.Formatter):
    def __init__(self, allow_content: bool = False) -> None:
        super().__init__()
        self.allow_content = allow_content

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key in _RESERVED or key.startswith("_"):
                continue
            if key in SENSITIVE_KEYS and not self.allow_content:
                payload[key] = "[redacted]"
                continue
            payload[key] = value
        if record.exc_info:
            payload["exc_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO", allow_content: bool = False) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(allow_content=allow_content))
    root = logging.getLogger("couplecare")
    root.handlers = [handler]
    root.setLevel(level.upper())
    root.propagate = False
    # Uvicorn's access log includes only method/path/status, which is acceptable.

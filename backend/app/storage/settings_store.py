"""Persistence for user-adjustable runtime settings (``data/user/settings.json``).

Settings contain no conversation content. They are validated on every read and write; a
corrupt or tampered file falls back to safe defaults rather than crashing the backend.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path

from pydantic import ValidationError

from app.config import RuntimeSettings, Settings
from app.errors import BadRequestError

log = logging.getLogger("couplecare.settings")


class SettingsStore:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._path: Path = settings.runtime_settings_path
        self._lock = threading.Lock()
        self._current = self._load()

    def _defaults(self) -> RuntimeSettings:
        return RuntimeSettings(model_id=self._settings.default_model_id)

    def _load(self) -> RuntimeSettings:
        if not self._path.exists():
            return self._defaults()
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            loaded = RuntimeSettings.model_validate(data)
            if loaded.model_id not in self._settings.model_ids():
                loaded.model_id = self._settings.default_model_id
            return loaded
        except (OSError, json.JSONDecodeError, ValidationError):
            log.warning("runtime_settings_invalid_using_defaults")
            return self._defaults()

    def get(self) -> RuntimeSettings:
        with self._lock:
            return self._current.model_copy()

    def update(self, changes: dict) -> RuntimeSettings:
        with self._lock:
            merged = {**self._current.model_dump(), **changes}
            try:
                updated = RuntimeSettings.model_validate(merged)
            except ValidationError as exc:
                fields = sorted({".".join(str(p) for p in e["loc"]) for e in exc.errors()})
                raise BadRequestError("Invalid settings: " + ", ".join(fields), code="invalid_settings") from exc
            if updated.model_id not in self._settings.model_ids():
                raise BadRequestError("That model is not configured on this machine.", code="unknown_model")
            self._write(updated)
            self._current = updated
            return updated.model_copy()

    def reset(self) -> RuntimeSettings:
        with self._lock:
            self._current = self._defaults()
            if self._path.exists():
                self._path.unlink()
            return self._current.model_copy()

    def _write(self, value: RuntimeSettings) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(value.model_dump(), indent=2), encoding="utf-8")
        os.replace(tmp, self._path)

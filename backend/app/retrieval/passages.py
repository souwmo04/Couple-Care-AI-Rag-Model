"""The passage record stored in every index."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class Passage:
    chunk_id: str
    document_id: str
    text: str
    title: str
    language: str
    topic: str
    organization: str | None = None
    author: str | None = None
    url: str | None = None
    published: str | None = None
    retrieved: str | None = None
    license: str | None = None
    section: str | None = None
    synthetic: bool = False
    translation_of: str | None = None
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Passage:
        known = {k: data[k] for k in cls.__dataclass_fields__ if k in data}
        return cls(**known)

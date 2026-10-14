"""Text extraction for the allowlisted source types.

Supported: ``.txt``, ``.md``, ``.html``/``.htm`` (local, permitted exports only), ``.pdf``
(text layer only — scanned PDFs without a text layer are reported as failures, not
silently skipped or OCR'd).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

ALLOWED_EXTENSIONS = {".txt", ".md", ".markdown", ".html", ".htm", ".pdf"}


class ExtractionError(Exception):
    pass


@dataclass(slots=True)
class Section:
    heading: str | None
    text: str


def resolve_inside(root: Path, relative: str) -> Path:
    """Resolve ``relative`` under ``root`` and refuse anything that escapes it."""
    if not relative or "\x00" in relative:
        raise ExtractionError("Empty or invalid path")
    candidate = Path(relative)
    if candidate.is_absolute() or candidate.drive:
        raise ExtractionError("Absolute paths are not allowed in the source manifest")
    resolved = (root / candidate).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ExtractionError("Path escapes the raw data directory")
    return resolved


def validate_file(path: Path, max_bytes: int) -> None:
    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ExtractionError(f"File type '{path.suffix}' is not in the allowlist")
    if not path.is_file():
        raise ExtractionError("File does not exist")
    if path.is_symlink():
        raise ExtractionError("Symbolic links are not ingested")
    size = path.stat().st_size
    if size == 0:
        raise ExtractionError("File is empty")
    if size > max_bytes:
        raise ExtractionError(f"File is larger than the {max_bytes // 1024} KB limit")


def _markdown_sections(text: str) -> list[Section]:
    sections: list[Section] = []
    heading: str | None = None
    buffer: list[str] = []
    for line in text.splitlines():
        match = re.match(r"^(#{1,4})\s+(.*)$", line)
        if match:
            if "\n".join(buffer).strip():
                sections.append(Section(heading, "\n".join(buffer).strip()))
            heading = match.group(2).strip()
            buffer = []
        else:
            buffer.append(line)
    if "\n".join(buffer).strip():
        sections.append(Section(heading, "\n".join(buffer).strip()))
    return sections


def _strip_markdown(text: str) -> str:
    text = re.sub(r"^\s*>\s?", "", text, flags=re.MULTILINE)  # blockquotes
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)  # images
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)  # links → text
    text = re.sub(r"(\*\*|__)(.*?)\1", r"\2", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    return text


def _html_sections(raw: str) -> list[Section]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form", "noscript", "iframe"]):
        tag.decompose()
    body = soup.find("main") or soup.find("article") or soup.body or soup
    sections: list[Section] = []
    heading: str | None = None
    buffer: list[str] = []
    for el in body.find_all(["h1", "h2", "h3", "h4", "p", "li", "blockquote"]):
        text = el.get_text(" ", strip=True)
        if not text:
            continue
        if el.name in {"h1", "h2", "h3", "h4"}:
            if buffer:
                sections.append(Section(heading, "\n\n".join(buffer)))
            heading, buffer = text, []
        else:
            buffer.append(("• " + text) if el.name == "li" else text)
    if buffer:
        sections.append(Section(heading, "\n\n".join(buffer)))
    return sections


def _pdf_sections(path: Path) -> list[Section]:
    from pypdf import PdfReader

    try:
        reader = PdfReader(str(path))
    except Exception as exc:  # noqa: BLE001
        raise ExtractionError(f"PDF could not be opened ({type(exc).__name__})") from exc
    if reader.is_encrypted:
        raise ExtractionError("Encrypted PDFs are not supported")
    sections = []
    for number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            sections.append(Section(f"Page {number}", text))
    if not sections:
        raise ExtractionError("PDF has no extractable text layer (it may be scanned); inspect it manually")
    return sections


def extract_sections(path: Path) -> list[Section]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _pdf_sections(path)
    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ExtractionError("File is not valid UTF-8 text") from exc
    if suffix in {".md", ".markdown"}:
        return [Section(s.heading, _strip_markdown(s.text)) for s in _markdown_sections(raw)]
    if suffix in {".html", ".htm"}:
        sections = _html_sections(raw)
        if not sections:
            raise ExtractionError("No readable text found in HTML")
        return sections
    return [Section(None, raw)]

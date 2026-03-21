"""Persistence helpers for canonical shared reading-core artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from .book_document import BookDocument


def book_document_file(output_dir: Path) -> Path:
    """Return the canonical parsed-book substrate path."""

    return output_dir / "public" / "book_document.json"


def existing_book_document_file(output_dir: Path) -> Path:
    """Return the current parsed-book substrate path."""

    return book_document_file(output_dir)


def save_book_document(path: Path, document: BookDocument) -> None:
    """Persist one canonical parsed-book substrate payload."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")


def load_book_document(path: Path) -> BookDocument:
    """Load one canonical parsed-book substrate payload from disk."""

    return json.loads(path.read_text(encoding="utf-8"))

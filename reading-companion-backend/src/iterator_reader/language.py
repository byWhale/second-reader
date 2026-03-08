"""Language detection and rendering helpers for Iterator-Reader."""

from __future__ import annotations

import re
from pathlib import Path

from ebooklib import epub


LanguageCode = str

LANGUAGE_LABELS = {
    "zh": "Chinese",
    "en": "English",
}

MARKDOWN_LABELS = {
    "zh": {
        "chapter": "Chapter",
        "section": "段落",
        "skip": "（无特别联想，跳过）",
        "search": "搜索",
        "sources": "参考",
        "found": "补充",
        "highlight": "划线",
        "association": "联想",
        "curious": "好奇",
        "discern": "审辩",
        "connect_back": "回溯",
        "silent": "安静",
        "unknown": "Unknown",
    },
    "en": {
        "chapter": "Chapter",
        "section": "Section",
        "skip": "(No strong association; skipped)",
        "search": "Search",
        "sources": "Sources",
        "found": "Found",
        "highlight": "Highlight",
        "association": "Association",
        "curious": "Curious",
        "discern": "Discern",
        "connect_back": "Connect Back",
        "silent": "Silent",
        "unknown": "Unknown",
    },
}


def _normalize_language(value: str | None) -> LanguageCode | None:
    """Normalize raw language metadata to supported codes."""
    if not value:
        return None
    lowered = value.strip().lower()
    if lowered.startswith("zh"):
        return "zh"
    if lowered.startswith("en"):
        return "en"
    return None


def _heuristic_language(sample_text: str) -> LanguageCode:
    """Infer language from the book text when metadata is missing."""
    cjk_count = len(re.findall(r"[\u4e00-\u9fff]", sample_text))
    latin_count = len(re.findall(r"[A-Za-z]", sample_text))
    if cjk_count > max(60, latin_count // 3):
        return "zh"
    return "en"


def detect_book_language(book_path: Path, sample_text: str = "") -> LanguageCode:
    """Detect the source book language from metadata or text."""
    if book_path.suffix.lower() == ".epub":
        try:
            book = epub.read_epub(str(book_path))
            language_meta = book.get_metadata("DC", "language")
            if language_meta and language_meta[0]:
                normalized = _normalize_language(language_meta[0][0])
                if normalized:
                    return normalized
        except Exception:
            pass
    return _heuristic_language(sample_text)


def resolve_output_language(requested: str, book_language: LanguageCode) -> LanguageCode:
    """Resolve CLI language mode into an actual output language."""
    if requested in {"zh", "en"}:
        return requested
    return book_language


def language_name(language: LanguageCode) -> str:
    """Human-readable language label for prompts."""
    return LANGUAGE_LABELS.get(language, "English")


def markdown_labels(language: LanguageCode) -> dict[str, str]:
    """Get markdown labels for the chosen output language."""
    return MARKDOWN_LABELS.get(language, MARKDOWN_LABELS["en"])

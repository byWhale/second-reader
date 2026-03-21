"""Canonical parsed-book substrate shared across reading mechanisms."""

from __future__ import annotations

from typing import Literal, TypedDict


TextRole = Literal["chapter_heading", "section_heading", "body", "auxiliary"]


class TextLocator(TypedDict, total=False):
    """Stable text locator that can represent one paragraph or a paragraph span."""

    href: str
    start_cfi: str | None
    end_cfi: str | None
    paragraph_index: int
    paragraph_start: int
    paragraph_end: int


class ChapterHeadingBlock(TypedDict, total=False):
    """Structured heading metadata retained separately from chapter body paragraphs."""

    label: str
    title: str
    subtitle: str
    text: str
    locator: TextLocator


class ParagraphRecord(TypedDict, total=False):
    """Canonical paragraph-level text record extracted from the source book."""

    href: str
    start_cfi: str | None
    end_cfi: str | None
    paragraph_index: int
    text: str
    block_tag: str
    heading_level: int | None
    text_role: TextRole
    item_id: str
    spine_index: int | None


class BookChapter(TypedDict, total=False):
    """Canonical chapter payload composed of ordered paragraph records."""

    id: int
    title: str
    chapter_number: int | None
    level: int
    item_id: str
    href: str
    spine_index: int | None
    chapter_heading: ChapterHeadingBlock
    paragraphs: list[ParagraphRecord]


class BookMetadata(TypedDict, total=False):
    """Book-level metadata independent of any specific reading mechanism."""

    book: str
    author: str
    book_language: str
    output_language: str
    source_file: str


class BookDocument(TypedDict):
    """Canonical parsed-book substrate persisted before any mechanism derivation."""

    metadata: BookMetadata
    chapters: list[BookChapter]

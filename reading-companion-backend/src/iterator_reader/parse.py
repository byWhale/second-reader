"""Parse-stage logic for structure generation and semantic segmentation."""

from __future__ import annotations

import re
import posixpath
import zipfile
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Callable, Literal
from xml.etree import ElementTree as ET
import ebooklib
from ebooklib import epub

from src.config import get_backend_version, get_reader_resume_compat_version
from src.parsers import parse_ebook
from src.prompts.templates import (
    SEMANTIC_SEGMENTATION_PROMPT,
    SEMANTIC_SEGMENTATION_SYSTEM,
)
from src.reading_core.book_document import BookDocument, BookMetadata
from src.reading_core.storage import book_document_file, existing_book_document_file, load_book_document, save_book_document

from .language import detect_book_language, language_name, resolve_output_language
from .llm_utils import invoke_json
from .frontend_artifacts import (
    _reaction_target_locator,
    append_activity_event,
    build_run_state,
    write_book_manifest,
    write_run_state,
)
from .models import (
    BookStructure,
    ChapterHeadingBlock,
    ChapterPrimaryRole,
    ChapterRoleTag,
    ParseState,
    RoleConfidence,
    SemanticSegment,
    StructureChapter,
)
from .storage import (
    chapter_markdown_file,
    chapter_output_name,
    chapter_reference,
    chapter_result_file,
    cover_asset_file,
    ensure_output_dir,
    ensure_source_asset,
    existing_book_manifest_file,
    existing_chapter_result_file,
    infer_chapter_number,
    existing_parse_state_file,
    relative_output_path,
    resolve_output_dir,
    book_manifest_file,
    existing_cover_asset_file,
    existing_structure_file,
    load_structure,
    load_json,
    parse_state_file,
    save_structure,
    save_json,
    segment_reference,
    structure_file,
    structure_markdown_file,
)
from .structure_markdown import render_structure_markdown

SKIP_TITLES = {
    "title page",
    "copyright",
    "contents",
    "dedication",
    "acknowledgments",
}

LOW_VALUE_SEGMENT_KEYWORDS = {
    "zh": [
        "注释",
        "参考文献",
        "延伸阅读",
        "版权信息",
        "图片来源",
        "网站标记",
        "网站地址",
        "出处说明",
        "元信息",
    ],
    "en": [
        "footnotes",
        "references",
        "endnotes",
        "citation",
        "citations",
        "source attribution",
        "source information",
        "image attribution",
        "painting reference",
        "website url",
        "closing metadata",
        "publication info",
        "publication details",
    ],
}

BLOCK_TAGS = {
    "p",
    "li",
    "blockquote",
    "div",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
}

HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
CHAPTER_LABEL_PATTERNS = (
    r"^chapter\s+[0-9ivxlcdm]+\b",
    r"^part\s+[0-9ivxlcdm]+\b",
    r"^book\s+[0-9ivxlcdm]+\b",
    r"^第\s*[0-9一二三四五六七八九十百千万]+\s*[章节卷部篇]\b",
    r"^[ivxlcdm]+\b$",
)
AUXILIARY_KEYWORDS = (
    "oceanofpdf",
    "national gallery",
    "oil on canvas",
    "illustration",
    "frontispiece",
    "cover art",
    "source:",
)


def extract_plain_text(content: str) -> str:
    """Normalize HTML-ish chapter content to plain text."""
    if not content:
        return ""
    if "<" in content and ">" in content:
        content = re.sub(r"<(script|style)[^>]*>[\s\S]*?</\1>", " ", content, flags=re.IGNORECASE)
        content = re.sub(r"<[^>]+>", "\n", content)
    content = re.sub(r"\r\n?", "\n", content)
    content = re.sub(r"\n{3,}", "\n\n", content)
    content = re.sub(r"[ \t]+", " ", content)
    return content.strip()


def split_into_paragraphs(text: str) -> list[str]:
    """Split normalized chapter text into readable paragraphs."""
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if len(paragraphs) >= 2:
        return paragraphs

    sentences = re.split(r"(?<=[.!?。！？])\s+", text)
    grouped: list[str] = []
    buffer: list[str] = []
    for sentence in sentences:
        if not sentence.strip():
            continue
        buffer.append(sentence.strip())
        if len(buffer) >= 3:
            grouped.append(" ".join(buffer))
            buffer = []
    if buffer:
        grouped.append(" ".join(buffer))
    return grouped or [text.strip()]


def _normalize_block_text(text: str) -> str:
    """Normalize one paragraph-sized text block."""
    cleaned = re.sub(r"\s+", " ", text or "")
    return cleaned.strip()


def _local_tag(tag: str) -> str:
    """Return an XML tag without its namespace prefix."""
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def _heading_level_for_tag(tag: str) -> int | None:
    """Return the numeric heading level for one block tag."""
    if tag in HEADING_TAGS:
        return int(tag[1])
    return None


def _direct_text_content(element: ET.Element) -> str:
    """Return text owned directly by one element, excluding descendant blocks."""
    parts: list[str] = []
    if element.text:
        parts.append(element.text)
    for child in list(element):
        tail = getattr(child, "tail", None)
        if tail:
            parts.append(tail)
    return _normalize_block_text(" ".join(parts))


def _has_textual_block_children(element: ET.Element) -> bool:
    """Return whether one element wraps child block elements with text."""
    for child in list(element):
        if not isinstance(child.tag, str):
            continue
        if _local_tag(str(child.tag)) not in BLOCK_TAGS:
            continue
        if _normalize_block_text("".join(child.itertext())):
            return True
    return False


def _looks_like_sentence(text: str) -> bool:
    """Heuristic: return whether one text block behaves like running prose."""
    normalized = _normalize_block_text(text)
    if not normalized:
        return False
    if re.search(r"[.!?。！？][\"'”’]?\s*$", normalized):
        return True
    if len(normalized.split()) >= 18 and "," in normalized:
        return True
    return False


def _upper_ratio(text: str) -> float:
    """Return the uppercase ratio for alphabetic characters in one string."""
    letters = [char for char in text if char.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for char in letters if char.isupper()) / len(letters)


def _looks_like_chapter_label(text: str) -> bool:
    """Return whether one text block looks like a chapter/part label."""
    normalized = _normalize_block_text(text)
    lowered = normalized.lower()
    return any(re.match(pattern, lowered, flags=re.IGNORECASE) for pattern in CHAPTER_LABEL_PATTERNS)


def _looks_like_auxiliary_text(text: str, *, at_chapter_start: bool) -> bool:
    """Return whether one block is likely metadata/citation noise, not body text."""
    normalized = _normalize_block_text(text)
    lowered = normalized.lower()
    if not normalized:
        return False
    if re.search(r"https?://|www\.|[a-z0-9.-]+\.(com|org|net|edu|gov|pdf)\b", lowered):
        return True
    if at_chapter_start and any(keyword in lowered for keyword in AUXILIARY_KEYWORDS):
        return True
    if at_chapter_start and "[" in normalized and "]" in normalized and re.search(r"\b\d{3,4}(?:/\d{2,4})?\b", normalized):
        return True
    return False


def _looks_like_heading_text(text: str, *, block_tag: str, at_chapter_start: bool) -> bool:
    """Return whether one block behaves like heading text."""
    normalized = _normalize_block_text(text)
    if not normalized:
        return False
    if block_tag in HEADING_TAGS:
        return True
    if _looks_like_chapter_label(normalized):
        return True
    if len(normalized) > 140:
        return False
    if _looks_like_sentence(normalized):
        return False
    words = normalized.split()
    if len(words) > (18 if at_chapter_start else 14):
        return False
    if _upper_ratio(normalized) >= 0.45:
        return True
    alpha_words = [word for word in words if re.search(r"[A-Za-z]", word)]
    if alpha_words and all(word[:1].isupper() or word.isupper() for word in alpha_words):
        return True
    if (
        not at_chapter_start
        and normalized[:1].isupper()
        and len(words) <= 6
        and not re.search(r"[,;:，；：]", normalized)
    ):
        return True
    return at_chapter_start and len(words) <= 6


def _cfi_for_element(spine_index: int, item_id: str, path_steps: list[int]) -> str | None:
    """Build a lightweight EPUB CFI for one XHTML element path."""
    if spine_index < 0:
        return None
    spine_step = 2 * (spine_index + 1)
    item_suffix = f"[{item_id}]" if item_id else ""
    element_path = "/4" + "".join(f"/{step}" for step in path_steps)
    return f"epubcfi(/6/{spine_step}{item_suffix}!{element_path})"


def _extract_epub_paragraph_records(
    content: str,
    *,
    href: str,
    item_id: str,
    spine_index: int,
) -> list[dict[str, object]]:
    """Extract paragraph-sized blocks with lightweight EPUB locators."""
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return []

    records: list[dict[str, object]] = []

    def walk(element: ET.Element, path_steps: list[int]) -> None:
        tag = _local_tag(str(element.tag))
        text = _normalize_block_text("".join(element.itertext()))
        own_text = _direct_text_content(element)
        duplicate_container = (
            tag == "div"
            and text
            and _has_textual_block_children(element)
            and not own_text
        )
        if tag in BLOCK_TAGS and text and not duplicate_container:
            cfi = _cfi_for_element(spine_index, item_id, path_steps)
            records.append(
                {
                    "text": text,
                    "href": href,
                    "start_cfi": cfi,
                    "end_cfi": cfi,
                    "paragraph_index": len(records) + 1,
                    "block_tag": tag,
                    "heading_level": _heading_level_for_tag(tag),
                }
            )

        children = [child for child in list(element) if isinstance(child.tag, str)]
        for index, child in enumerate(children, start=1):
            walk(child, [*path_steps, index * 2])

    walk(root, [])
    return records


def _paragraph_records(chapter: dict[str, object]) -> list[dict[str, object]]:
    """Return paragraph records with optional EPUB locator metadata."""
    content = str(chapter.get("content", "") or "")
    href = str(chapter.get("href", "") or "")
    item_id = str(chapter.get("item_id", "") or "")
    spine_index = int(chapter.get("spine_index", -1) or -1)

    if href:
        records = _extract_epub_paragraph_records(
            content,
            href=href,
            item_id=item_id,
            spine_index=spine_index,
        )
        if records:
            return records

    return [
        {
            "text": paragraph,
            "href": href,
            "start_cfi": None,
            "end_cfi": None,
            "paragraph_index": index,
            "block_tag": "p",
            "heading_level": None,
        }
        for index, paragraph in enumerate(split_into_paragraphs(extract_plain_text(content)), start=1)
    ]


def _classify_paragraph_records(records: list[dict[str, object]]) -> list[dict[str, object]]:
    """Classify chapter text blocks into structure-aware roles."""
    classified: list[dict[str, object]] = []
    body_seen = False
    for record in records:
        text = str(record.get("text", "") or "")
        block_tag = str(record.get("block_tag", "p") or "p")
        at_chapter_start = not body_seen
        text_role = "body"
        if _looks_like_auxiliary_text(text, at_chapter_start=at_chapter_start):
            text_role = "auxiliary"
        elif at_chapter_start and _looks_like_heading_text(text, block_tag=block_tag, at_chapter_start=True):
            text_role = "chapter_heading"
        elif not at_chapter_start and _looks_like_heading_text(text, block_tag=block_tag, at_chapter_start=False):
            text_role = "section_heading"
        else:
            body_seen = True

        classified.append(
            {
                **record,
                "block_tag": block_tag,
                "heading_level": record.get("heading_level"),
                "text_role": text_role,
            }
        )
    return classified


def _chapter_heading_block(records: list[dict[str, object]]) -> ChapterHeadingBlock | None:
    """Collapse leading chapter heading records into one structured block."""
    heading_records = [
        record
        for record in records
        if str(record.get("text_role", "")) == "chapter_heading" and str(record.get("text", "")).strip()
    ]
    if not heading_records:
        return None

    texts = [str(record.get("text", "")).strip() for record in heading_records if str(record.get("text", "")).strip()]
    if not texts:
        return None

    remaining = list(texts)
    payload: ChapterHeadingBlock = {
        "text": "\n".join(texts),
        "title": remaining[0],
    }
    if remaining and _looks_like_chapter_label(remaining[0]):
        payload["label"] = remaining.pop(0)
    if remaining:
        payload["title"] = remaining.pop(0)
    elif payload.get("label"):
        payload["title"] = str(payload["label"])
        payload.pop("label", None)

    subtitle = " / ".join(item for item in remaining if item)
    if subtitle:
        payload["subtitle"] = subtitle

    locator = _segment_locator_from_records(heading_records)
    if locator:
        payload["locator"] = locator
    return payload


def _body_record_groups(records: list[dict[str, object]]) -> list[dict[str, object]]:
    """Split classified records into body groups separated by section headings."""
    groups: list[dict[str, object]] = []
    current_heading: list[dict[str, object]] = []
    current_body: list[dict[str, object]] = []

    for record in records:
        role = str(record.get("text_role", "body"))
        if role == "body":
            current_body.append(record)
            continue
        if role == "section_heading":
            if current_body:
                groups.append(
                    {
                        "heading_records": current_heading,
                        "body_records": current_body,
                    }
                )
                current_body = []
                current_heading = [record]
            else:
                current_heading.append(record)
            continue
        if role == "auxiliary" and current_body:
            groups.append(
                {
                    "heading_records": current_heading,
                    "body_records": current_body,
                }
            )
            current_body = []
            current_heading = []

    if current_body:
        groups.append(
            {
                "heading_records": current_heading,
                "body_records": current_body,
            }
        )
    return groups


def _segment_locator_from_records(records: list[dict[str, object]]) -> dict[str, object] | None:
    """Collapse paragraph records into one segment-level locator."""
    if not records:
        return None

    first = records[0]
    last = records[-1]
    href = str(first.get("href", "") or last.get("href", ""))
    if not href:
        return None

    return {
        "href": href,
        "start_cfi": first.get("start_cfi"),
        "end_cfi": last.get("end_cfi"),
        "paragraph_start": int(first.get("paragraph_index", 0) or 0),
        "paragraph_end": int(last.get("paragraph_index", 0) or 0),
    }


def estimate_tokens(text: str) -> int:
    """Rough token estimate without external tokenizer dependency."""
    return max(1, len(text) // 4)


def _timestamp() -> str:
    """Return a stable UTC timestamp."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _chapter_is_parsed(chapter: StructureChapter) -> bool:
    """Return whether one chapter already has persisted structure segments."""
    return bool(chapter.get("segments"))


def _chapter_contexts(raw_chapters: list[dict[str, object]], *, output_language: str) -> list[dict[str, object]]:
    """Prepare lightweight chapter contexts before semantic segmentation."""
    contexts: list[dict[str, object]] = []
    for chapter_index, raw_chapter in enumerate(raw_chapters, start=1):
        paragraph_records = _classify_paragraph_records(_paragraph_records(raw_chapter))
        chapter_text = "\n\n".join(
            str(record.get("text", ""))
            for record in paragraph_records
            if str(record.get("text_role", "body")) != "auxiliary"
        )
        if not chapter_text.strip():
            continue
        chapter_title = str(raw_chapter.get("title", f"Chapter {chapter_index}") or f"Chapter {chapter_index}")
        if _should_skip_chapter(chapter_title, chapter_text):
            print(f"[skip] {chapter_title}", flush=True)
            continue

        context = {
            "id": chapter_index,
            "title": chapter_title,
            "chapter_number": infer_chapter_number(chapter_title),
            "level": int(raw_chapter.get("level", 1) or 1),
            "paragraph_records": paragraph_records,
            "chapter_heading": _chapter_heading_block(paragraph_records),
            "body_groups": _body_record_groups(paragraph_records),
            "item_id": str(raw_chapter.get("item_id", "") or ""),
            "href": str(raw_chapter.get("href", "") or ""),
            "spine_index": int(raw_chapter.get("spine_index", 0) or 0) if raw_chapter.get("spine_index") is not None else None,
            "output_language": output_language,
        }
        primary_role, role_tags, role_confidence = _infer_chapter_role(context)
        context["primary_role"] = primary_role
        context["role_tags"] = role_tags
        context["role_confidence"] = role_confidence
        contexts.append(context)
    return contexts


def _build_book_document(
    raw_chapters: list[dict[str, object]],
    *,
    title: str,
    author: str,
    book_language: str,
    output_language: str,
    book_path: Path,
) -> BookDocument:
    """Build the canonical parsed-book substrate before any mechanism derivation."""

    metadata: BookMetadata = {
        "book": title,
        "author": author,
        "book_language": book_language,
        "output_language": output_language,
        "source_file": str(book_path),
    }
    chapters: list[dict[str, object]] = []
    for chapter_index, raw_chapter in enumerate(raw_chapters, start=1):
        paragraph_records = _classify_paragraph_records(_paragraph_records(raw_chapter))
        chapter_text = "\n\n".join(
            str(record.get("text", ""))
            for record in paragraph_records
            if str(record.get("text_role", "body")) != "auxiliary"
        )
        if not chapter_text.strip():
            continue

        chapter_title = str(raw_chapter.get("title", f"Chapter {chapter_index}") or f"Chapter {chapter_index}")
        if _should_skip_chapter(chapter_title, chapter_text):
            print(f"[skip] {chapter_title}", flush=True)
            continue

        chapter_payload: dict[str, object] = {
            "id": chapter_index,
            "title": chapter_title,
            "chapter_number": infer_chapter_number(chapter_title),
            "level": int(raw_chapter.get("level", 1) or 1),
            "paragraphs": paragraph_records,
        }
        chapter_heading = _chapter_heading_block(paragraph_records)
        if chapter_heading:
            chapter_payload["chapter_heading"] = chapter_heading
        item_id = str(raw_chapter.get("item_id", "") or "")
        href = str(raw_chapter.get("href", "") or "")
        spine_index = raw_chapter.get("spine_index")
        if item_id:
            chapter_payload["item_id"] = item_id
        if href:
            chapter_payload["href"] = href
        if spine_index is not None:
            chapter_payload["spine_index"] = int(spine_index)
        chapters.append(chapter_payload)

    return {
        "metadata": metadata,
        "chapters": chapters,
    }


def _chapter_contexts_from_book_document(
    document: BookDocument,
    *,
    output_language: str,
) -> list[dict[str, object]]:
    """Derive iterator segmentation contexts from the canonical book substrate."""

    contexts: list[dict[str, object]] = []
    for chapter in document.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        paragraph_records = [
            dict(record)
            for record in chapter.get("paragraphs", [])
            if isinstance(record, dict) and str(record.get("text", "")).strip()
        ]
        if not paragraph_records:
            continue

        context = {
            "id": int(chapter.get("id", 0) or 0),
            "title": str(chapter.get("title", "")),
            "chapter_number": chapter.get("chapter_number"),
            "level": int(chapter.get("level", 1) or 1),
            "paragraph_records": paragraph_records,
            "chapter_heading": dict(chapter.get("chapter_heading", {})) if isinstance(chapter.get("chapter_heading"), dict) else _chapter_heading_block(paragraph_records),
            "body_groups": _body_record_groups(paragraph_records),
            "item_id": str(chapter.get("item_id", "") or ""),
            "href": str(chapter.get("href", "") or ""),
            "spine_index": int(chapter.get("spine_index", 0) or 0) if chapter.get("spine_index") is not None else None,
            "output_language": output_language,
        }
        primary_role, role_tags, role_confidence = _infer_chapter_role(context)
        context["primary_role"] = primary_role
        context["role_tags"] = role_tags
        context["role_confidence"] = role_confidence
        contexts.append(context)
    return contexts


def _load_or_build_book_document(
    book_path: Path,
    *,
    output_dir: Path,
    title: str,
    author: str,
    book_language: str,
    output_language: str,
    raw_chapters: list[dict[str, object]] | None = None,
) -> BookDocument:
    """Load the canonical parsed-book substrate or rebuild it from source."""

    document_path = existing_book_document_file(output_dir)
    if document_path.exists():
        return load_book_document(document_path)

    canonical = _build_book_document(
        raw_chapters if raw_chapters is not None else parse_ebook(str(book_path)),
        title=title,
        author=author,
        book_language=book_language,
        output_language=output_language,
        book_path=book_path,
    )
    save_book_document(book_document_file(output_dir), canonical)
    return canonical


def _infer_chapter_role(
    context: dict[str, object],
) -> tuple[ChapterPrimaryRole, list[ChapterRoleTag], RoleConfidence]:
    """Infer a soft chapter role from parse-time structural cues."""
    title = str(context.get("title", "") or "").strip()
    heading = context.get("chapter_heading")
    heading_text = str(heading.get("text", "")) if isinstance(heading, dict) else ""
    lowered = " ".join(part for part in [title, heading_text] if part).lower()
    tags: list[ChapterRoleTag] = []
    primary_role: ChapterPrimaryRole = "body"
    confidence: RoleConfidence = "low"

    def add_tag(tag: ChapterRoleTag) -> None:
        if tag not in tags:
            tags.append(tag)

    explicit_front = False
    explicit_back = False

    if any(keyword in lowered for keyword in ["chapter summaries", "summary and map", "summaries and map", "roadmap", "road map", "overview"]):
        primary_role = "front_matter"
        explicit_front = True
        add_tag("overview")
        add_tag("roadmap")
    if re.search(r"\bcontents\b|\btable of contents\b|\boutline\b", lowered):
        primary_role = "front_matter"
        explicit_front = True
        add_tag("overview")
        add_tag("roadmap")
    if re.search(r"\bpreface\b", lowered):
        primary_role = "front_matter"
        explicit_front = True
        add_tag("preface")
    if re.search(r"\bprologue\b", lowered):
        primary_role = "front_matter"
        explicit_front = True
        add_tag("prologue")

    if re.search(r"\bappendix\b", lowered):
        primary_role = "back_matter"
        explicit_back = True
        add_tag("appendix")
    if re.search(r"\bepilogue\b", lowered):
        primary_role = "back_matter"
        explicit_back = True
        add_tag("epilogue")
    if re.search(r"\bafterword\b", lowered):
        primary_role = "back_matter"
        explicit_back = True
        add_tag("afterword")
    if re.search(r"\bnotes?\b|\bendnotes\b|\bfootnotes\b|\breferences?\b|\bbibliography\b|\bindex\b", lowered):
        primary_role = "back_matter"
        explicit_back = True
        add_tag("notes")
        add_tag("reference_like")

    early_body = " ".join(
        str(record.get("text", "")).strip()
        for group in list(context.get("body_groups", []))[:2]
        for record in list(group.get("body_records", []))[:2]
        if str(record.get("text", "")).strip()
    ).lower()
    if re.search(r"\bdefined as\b|\brefers to\b|\bmeans\b|\bis the\b|\bconsists of\b", early_body):
        add_tag("definition_heavy")
    if re.search(r"\bfor example\b|\bfor instance\b|\bcase study\b|\bstory\b|\bstories\b|\bexample\b", early_body):
        add_tag("example_heavy")

    if explicit_front or explicit_back:
        confidence = "high"
    elif context.get("chapter_number") is not None:
        primary_role = "body"
        confidence = "medium"
    elif tags:
        confidence = "medium"

    return primary_role, tags, confidence


def _chapter_stub_from_context(output_dir: Path, context: dict[str, object], *, segments: list[SemanticSegment] | None = None) -> StructureChapter:
    """Create one persisted structure chapter record from a prepared context."""
    chapter_stub: StructureChapter = {
        "id": int(context.get("id", 0)),
        "title": str(context.get("title", "")),
        "chapter_number": context.get("chapter_number"),
        "primary_role": context.get("primary_role", "body"),
        "role_tags": list(context.get("role_tags", [])),
        "role_confidence": context.get("role_confidence", "low"),
        "status": "pending",
        "level": int(context.get("level", 1) or 1),
        "segments": list(segments or []),
    }
    chapter_heading = context.get("chapter_heading")
    if isinstance(chapter_heading, dict):
        chapter_stub["chapter_heading"] = chapter_heading
    chapter_stub["output_file"] = relative_output_path(output_dir, chapter_markdown_file(output_dir, chapter_stub))
    item_id = str(context.get("item_id", "") or "")
    href = str(context.get("href", "") or "")
    spine_index = context.get("spine_index")
    if item_id:
        chapter_stub["item_id"] = item_id
    if href:
        chapter_stub["href"] = href
    if spine_index is not None:
        chapter_stub["spine_index"] = int(spine_index)
    return chapter_stub


def chapter_contexts_for_book(book_path: Path, *, output_language: str) -> list[dict[str, object]]:
    """Rebuild iterator segmentation contexts from the canonical book substrate."""

    title, author = extract_book_metadata(book_path)
    raw_chapters = parse_ebook(str(book_path))
    sample_text = "\n".join(extract_plain_text(ch.get("content", ""))[:300] for ch in raw_chapters[:3])
    book_language = detect_book_language(book_path, sample_text=sample_text)
    output_dir = resolve_output_dir(book_path, title, book_language, output_language)
    ensure_output_dir(output_dir)
    book_document = _load_or_build_book_document(
        book_path,
        output_dir=output_dir,
        title=title,
        author=author,
        book_language=book_language,
        output_language=output_language,
        raw_chapters=raw_chapters,
    )
    return _chapter_contexts_from_book_document(
        book_document,
        output_language=str(book_document.get("metadata", {}).get("output_language", output_language) or output_language),
    )


def segment_context_into_chapter(
    output_dir: Path,
    context: dict[str, object],
    *,
    progress: Callable[[str], None] | None = None,
) -> StructureChapter:
    """Segment one prepared chapter context into a persisted structure record."""
    chapter_id = int(context.get("id", 0))
    paragraph_records = list(context.get("paragraph_records", []))
    chapter_heading = context.get("chapter_heading")
    body_groups = list(context.get("body_groups", []))
    output_language = str(context.get("output_language", "en") or "en")

    segments: list[SemanticSegment] = []
    next_segment_index = 1
    total_groups = max(1, len(body_groups))
    for group_index, group in enumerate(body_groups, start=1):
        body_records = [
            record
            for record in list(group.get("body_records", []))
            if str(record.get("text", "")).strip()
        ]
        if not body_records:
            continue
        section_heading_text = "\n".join(
            str(record.get("text", "")).strip()
            for record in list(group.get("heading_records", []))
            if str(record.get("text", "")).strip()
        )
        if progress is not None:
            progress(f"语义切分块 {group_index}/{total_groups}")
        local_segments = segment_chapter_semantically(
            chapter_id=chapter_id,
            chapter_title=str(context.get("title", "")),
            chapter_text="\n\n".join(str(record.get("text", "")) for record in body_records),
            output_language=output_language,
            paragraphs=[str(record.get("text", "")) for record in body_records],
            chapter_heading_text=str(chapter_heading.get("text", "")) if isinstance(chapter_heading, dict) else "",
            section_heading_text=section_heading_text,
        )
        for segment in local_segments:
            start = int(segment.get("paragraph_start", 0) or 0)
            end = int(segment.get("paragraph_end", 0) or 0)
            if start < 1 or end < start or end > len(body_records):
                continue
            segment_records = body_records[start - 1 : end]
            segment_text = _records_text(segment_records)
            segments.append(
                {
                    "id": f"{chapter_id}.{next_segment_index}",
                    "summary": str(segment.get("summary", "")),
                    "tokens": estimate_tokens(segment_text),
                    "text": segment_text,
                    "paragraph_start": int(segment_records[0].get("paragraph_index", 0) or 0),
                    "paragraph_end": int(segment_records[-1].get("paragraph_index", 0) or 0),
                    "status": segment.get("status", "pending"),
                    "section_heading": section_heading_text,
                }
            )
            next_segment_index += 1

    if not segments:
        body_records = [
            record
            for record in paragraph_records
            if str(record.get("text_role", "")) == "body" and str(record.get("text", "")).strip()
        ]
        if body_records:
            segment_text = _records_text(body_records)
            segments = [
                {
                    "id": f"{chapter_id}.1",
                    "summary": str(context.get("title", ""))[:80],
                    "tokens": estimate_tokens(segment_text),
                    "text": segment_text,
                    "paragraph_start": int(body_records[0].get("paragraph_index", 0) or 0),
                    "paragraph_end": int(body_records[-1].get("paragraph_index", 0) or 0),
                    "status": "pending",
                    "section_heading": "",
                }
            ]

    chapter_record = _chapter_stub_from_context(output_dir, context, segments=segments)
    for segment in chapter_record.get("segments", []):
        segment["segment_ref"] = segment_reference(chapter_record, segment.get("id", ""))
        start = int(segment.get("paragraph_start", 0) or 0)
        end = int(segment.get("paragraph_end", 0) or 0)
        segment_records = [
            record
            for record in paragraph_records
            if start <= int(record.get("paragraph_index", 0) or 0) <= end
            and str(record.get("text_role", "body")) == "body"
        ]
        locator = _segment_locator_from_records(segment_records)
        if locator:
            segment["locator"] = locator
        segment["paragraph_locators"] = [
            {
                "href": str(record.get("href", "")),
                "start_cfi": record.get("start_cfi"),
                "end_cfi": record.get("end_cfi"),
                "paragraph_index": int(record.get("paragraph_index", 0) or 0),
                "text": str(record.get("text", "")),
                "block_tag": str(record.get("block_tag", "p")),
                "heading_level": record.get("heading_level"),
                "text_role": str(record.get("text_role", "body")),
            }
            for record in segment_records
        ]
    return chapter_record


def _persist_structure_artifacts(output_dir: Path, structure: BookStructure) -> None:
    """Persist the canonical structure, markdown overview, and manifest."""
    save_structure(structure_file(output_dir), structure)
    structure_markdown_file(output_dir).parent.mkdir(parents=True, exist_ok=True)
    structure_markdown_file(output_dir).write_text(
        render_structure_markdown(structure),
        encoding="utf-8",
    )
    write_book_manifest(output_dir, structure)


def write_parse_progress(
    structure: BookStructure,
    output_dir: Path,
    *,
    status: Literal["parsing_structure", "ready", "paused", "error"],
    total_chapters: int,
    completed_chapters: int,
    parsed_chapter_ids: list[int],
    inflight_chapter_ids: list[int] | None = None,
    pending_chapter_ids: list[int] | None = None,
    current_chapter_id: int | None = None,
    current_chapter_ref: str | None = None,
    current_step: str | None = None,
    worker_limit: int | None = None,
    last_checkpoint_at: str | None = None,
    error: str | None = None,
    sync_run_state: bool = True,
) -> ParseState:
    """Persist parse-stage progress into both run_state and parse_state."""
    resume_available = bool(parsed_chapter_ids) or status in {"paused", "error"}
    normalized_parsed_ids = sorted(int(chapter_id) for chapter_id in parsed_chapter_ids)
    normalized_inflight_ids = sorted(int(chapter_id) for chapter_id in (inflight_chapter_ids or []))
    normalized_pending_ids = sorted(int(chapter_id) for chapter_id in (pending_chapter_ids or []))
    if sync_run_state:
        write_run_state(
            output_dir,
            build_run_state(
                structure,
                stage="ready" if status == "ready" else status,
                total_chapters=total_chapters,
                completed_chapters=completed_chapters,
                current_chapter_id=current_chapter_id,
                current_chapter_ref=current_chapter_ref,
                current_segment_ref=None,
                current_phase_step=current_step,
                resume_available=resume_available,
                last_checkpoint_at=last_checkpoint_at,
                error=error,
            ),
        )
    payload: ParseState = {
        "status": status,
        "backend_version": get_backend_version(),
        "resume_compat_version": get_reader_resume_compat_version(),
        "total_chapters": int(total_chapters),
        "completed_chapters": int(completed_chapters),
        "parsed_chapter_ids": normalized_parsed_ids,
        "segmented_chapter_ids": normalized_parsed_ids,
        "inflight_chapter_ids": normalized_inflight_ids,
        "pending_chapter_ids": normalized_pending_ids,
        "current_chapter_id": current_chapter_id,
        "current_chapter_ref": current_chapter_ref,
        "current_step": current_step,
        "worker_limit": worker_limit,
        "resume_available": resume_available,
        "last_checkpoint_at": last_checkpoint_at,
        "updated_at": _timestamp(),
        "error": error,
    }
    save_json(parse_state_file(output_dir), payload)
    return payload


def extract_book_metadata(book_path: Path) -> tuple[str, str]:
    """Extract title and author when metadata is available."""
    title = book_path.stem
    author = "Unknown"

    if book_path.suffix.lower() == ".epub":
        try:
            book = epub.read_epub(str(book_path))
            title_meta = book.get_metadata("DC", "title")
            author_meta = book.get_metadata("DC", "creator")
            if title_meta and title_meta[0]:
                title = title_meta[0][0] or title
            if author_meta and author_meta[0]:
                author = author_meta[0][0] or author
        except Exception:
            pass

    return title, author


def _cover_extension(item: object) -> str:
    """Infer a safe file extension for one EPUB cover asset."""
    name = ""
    media_type = ""
    if hasattr(item, "get_name"):
        try:
            name = str(item.get_name() or "")
        except Exception:
            name = ""
    if hasattr(item, "media_type"):
        media_type = str(getattr(item, "media_type", "") or "")

    suffix = Path(name).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        return suffix
    if media_type == "image/png":
        return ".png"
    if media_type == "image/webp":
        return ".webp"
    if media_type == "image/gif":
        return ".gif"
    return ".jpg"


def _cover_asset_extension_from_href(href: str, media_type: str = "") -> str:
    """Infer a safe file extension from one EPUB href or media type."""
    suffix = Path(href).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        return suffix
    if media_type == "image/png":
        return ".png"
    if media_type == "image/webp":
        return ".webp"
    if media_type == "image/gif":
        return ".gif"
    return ".jpg"


def _normalize_href(href: str) -> str:
    """Normalize one manifest or guide href for stable lookup."""
    normalized = str(href or "").strip().replace("\\", "/")
    normalized = normalized.split("#", 1)[0]
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return posixpath.normpath(normalized) if normalized else ""


def _resolve_relative_href(base_href: str, href: str) -> str:
    """Resolve one href against another EPUB-relative href."""
    normalized = _normalize_href(href)
    if not normalized:
        return ""
    base_dir = posixpath.dirname(_normalize_href(base_href))
    if normalized.startswith("/"):
        return normalized.lstrip("/")
    return posixpath.normpath(posixpath.join(base_dir, normalized))


def _xml_attr(element: ET.Element, name: str) -> str:
    """Return one XML attribute regardless of namespace prefixing."""
    for key, value in element.attrib.items():
        if key == name or key.endswith(f"}}{name}"):
            return str(value or "").strip()
    return ""


def _local_name(tag: str) -> str:
    """Return an XML tag without its namespace prefix."""
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def _load_epub_package_document(book_path: Path) -> tuple[ET.Element, str] | None:
    """Load the OPF package XML and return its root plus archive path."""
    try:
        with zipfile.ZipFile(book_path) as archive:
            opf_path = ""
            try:
                container_xml = archive.read("META-INF/container.xml")
                container_root = ET.fromstring(container_xml)
                for element in container_root.iter():
                    if _local_name(str(element.tag)) != "rootfile":
                        continue
                    candidate = _xml_attr(element, "full-path")
                    if candidate:
                        opf_path = candidate
                        break
            except Exception:
                opf_path = ""

            if not opf_path:
                for name in archive.namelist():
                    if name.lower().endswith(".opf"):
                        opf_path = name
                        break

            if not opf_path:
                return None

            return ET.fromstring(archive.read(opf_path)), opf_path
    except Exception:
        return None


def _epub_item_indexes(book: epub.EpubBook) -> tuple[dict[str, object], dict[str, object]]:
    """Index EPUB items by id and normalized href."""
    by_id: dict[str, object] = {}
    by_href: dict[str, object] = {}
    for item in book.get_items():
        item_id = str(getattr(item, "get_id", lambda: "")() or "").strip()
        item_href = _normalize_href(str(getattr(item, "get_name", lambda: "")() or ""))
        if item_id:
            by_id[item_id] = item
        if item_href:
            by_href[item_href] = item
    return by_id, by_href


def _resolve_epub_item(*, by_id: dict[str, object], by_href: dict[str, object], reference: str) -> object | None:
    """Resolve one EPUB manifest reference as either id or href."""
    normalized = _normalize_href(reference)
    if not normalized:
        return None
    return by_id.get(reference) or by_id.get(normalized) or by_href.get(normalized)


def _item_has_cover_image_property(item: object) -> bool:
    """Return whether one EPUB manifest item declares itself as the cover image."""
    properties = getattr(item, "properties", None)
    if isinstance(properties, str):
        values = [properties]
    elif isinstance(properties, (list, tuple, set)):
        values = [str(value or "") for value in properties]
    else:
        values = []
    return any("cover-image" == value.strip().lower() for value in values)


def _opf_meta_cover_reference(opf_root: ET.Element) -> str:
    """Return the EPUB 3 cover reference from package metadata when present."""
    for element in opf_root.iter():
        if _local_name(str(element.tag)) != "meta":
            continue
        if _xml_attr(element, "name").lower() != "cover":
            continue
        content = _xml_attr(element, "content")
        if content:
            return content
    return ""


def _opf_cover_image_reference(opf_root: ET.Element) -> str:
    """Return the manifest href for a cover-image item when present."""
    for element in opf_root.iter():
        if _local_name(str(element.tag)) != "item":
            continue
        properties = _xml_attr(element, "properties").lower().split()
        if "cover-image" in properties:
            return _xml_attr(element, "href") or _xml_attr(element, "id")
    return ""


def _opf_guide_cover_page_href(opf_root: ET.Element) -> str:
    """Return the guide cover-page href when one is declared."""
    for element in opf_root.iter():
        if _local_name(str(element.tag)) != "reference":
            continue
        if _xml_attr(element, "type").lower() != "cover":
            continue
        href = _xml_attr(element, "href")
        if href:
            return href
    return ""


def _first_image_href_from_page(content: bytes) -> str:
    """Return the first image href from one XHTML cover page."""
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return ""

    for element in root.iter():
        if not isinstance(element.tag, str):
            continue
        tag = _local_name(str(element.tag))
        if tag == "img":
            src = _xml_attr(element, "src")
            if src:
                return src
        if tag == "image":
            href = _xml_attr(element, "href")
            if href:
                return href
    return ""


def _cover_reference_from_guide_page(book_path: Path, opf_path: str, page_href: str) -> str:
    """Resolve the first image href from the guide-declared cover page."""
    archive_page_href = _resolve_relative_href(opf_path, page_href)
    if not archive_page_href:
        return ""
    try:
        with zipfile.ZipFile(book_path) as archive:
            content = archive.read(archive_page_href)
    except Exception:
        return ""

    image_href = _first_image_href_from_page(content)
    if not image_href:
        return ""
    return _resolve_relative_href(page_href, image_href)


def _write_cover_asset(output_dir: Path, content: bytes, extension: str) -> Path:
    """Persist one cover asset and remove stale alternate extensions."""
    destination = cover_asset_file(output_dir, extension)
    destination.parent.mkdir(parents=True, exist_ok=True)
    for existing in destination.parent.glob("cover.*"):
        if existing != destination and existing.is_file():
            existing.unlink()
    destination.write_bytes(content)
    return destination


def _extract_epub_cover(book_path: Path, output_dir: Path) -> Path | None:
    """Extract the EPUB cover image into the frontend asset directory when available."""
    try:
        book = epub.read_epub(str(book_path))
    except Exception:
        return None

    by_id, by_href = _epub_item_indexes(book)
    cover_item = None
    package = _load_epub_package_document(book_path)

    if package:
        opf_root, opf_path = package
        meta_reference = _opf_meta_cover_reference(opf_root)
        if meta_reference:
            cover_item = _resolve_epub_item(by_id=by_id, by_href=by_href, reference=meta_reference)

        if cover_item is None:
            metadata = book.get_metadata("OPF", "cover")
            if metadata:
                cover_id = str(metadata[0][0] or "").strip()
                if cover_id:
                    cover_item = _resolve_epub_item(by_id=by_id, by_href=by_href, reference=cover_id)

        if cover_item is None:
            cover_reference = _opf_cover_image_reference(opf_root)
            if cover_reference:
                cover_item = _resolve_epub_item(by_id=by_id, by_href=by_href, reference=cover_reference)

        if cover_item is None:
            cover_page_href = _opf_guide_cover_page_href(opf_root)
            if cover_page_href:
                image_reference = _cover_reference_from_guide_page(book_path, opf_path, cover_page_href)
                if image_reference:
                    cover_item = _resolve_epub_item(by_id=by_id, by_href=by_href, reference=image_reference)

    if cover_item is None:
        for item in book.get_items():
            item_type = getattr(item, "get_type", lambda: None)()
            if item_type != ebooklib.ITEM_IMAGE:
                continue
            if _item_has_cover_image_property(item):
                cover_item = item
                break

    if cover_item is None:
        for item in book.get_items():
            item_type = getattr(item, "get_type", lambda: None)()
            if item_type != ebooklib.ITEM_IMAGE:
                continue
            identifier = str(getattr(item, "get_id", lambda: "")() or "")
            name = str(getattr(item, "get_name", lambda: "")() or "")
            if "cover" in identifier.lower() or "cover" in name.lower():
                cover_item = item
                break

    if cover_item is None:
        return None

    try:
        content = cover_item.get_content()
    except Exception:
        return None
    if not content:
        return None

    name = str(getattr(cover_item, "get_name", lambda: "")() or "")
    media_type = str(getattr(cover_item, "media_type", "") or "")
    extension = _cover_extension(cover_item) if name or media_type else _cover_asset_extension_from_href(name, media_type)
    return _write_cover_asset(output_dir, content, extension)


def fallback_segments(chapter_id: int, paragraphs: list[str], chapter_title: str) -> list[SemanticSegment]:
    """Fallback when segmentation output is unusable."""
    text = "\n\n".join(paragraphs)
    summary = chapter_title if chapter_title else "本章的主要论述"
    return [
        {
            "id": f"{chapter_id}.1",
            "summary": summary[:80],
            "tokens": estimate_tokens(text),
            "text": text,
            "paragraph_start": 1,
            "paragraph_end": len(paragraphs),
            "status": "pending",
        }
    ]


def _merge_segment_group(
    chapter_id: int,
    paragraph_group: list[str],
    start: int,
    end: int,
    summary: str,
    offset: int,
) -> SemanticSegment:
    """Create one semantic segment from a paragraph span."""
    text = "\n\n".join(paragraph_group)
    return {
        "id": f"{chapter_id}.{offset}",
        "summary": summary[:120],
        "tokens": estimate_tokens(text),
        "text": text,
        "paragraph_start": start,
        "paragraph_end": end,
        "status": "pending",
    }


def _fallback_chunk_segments(
    chapter_id: int,
    chapter_title: str,
    paragraphs: list[str],
) -> list[SemanticSegment]:
    """Split very long chapters into coarse chunks when the model under-segments."""
    chunk_size = 8 if len(paragraphs) >= 64 else 6
    segments: list[SemanticSegment] = []
    for offset, start_index in enumerate(range(0, len(paragraphs), chunk_size), start=1):
        end_index = min(start_index + chunk_size, len(paragraphs))
        paragraph_group = paragraphs[start_index:end_index]
        summary_seed = paragraph_group[0].replace("\n", " ").strip()[:40] or f"{chapter_title}片段 {offset}"
        segments.append(
            _merge_segment_group(
                chapter_id=chapter_id,
                paragraph_group=paragraph_group,
                start=start_index + 1,
                end=end_index,
                summary=summary_seed,
                offset=offset,
            )
        )
    return segments


def _compact_segments(
    chapter_id: int,
    chapter_title: str,
    paragraphs: list[str],
    segments: list[SemanticSegment],
) -> list[SemanticSegment]:
    """Rebalance obviously bad segmentation outputs."""
    if not segments:
        return fallback_segments(chapter_id, paragraphs, chapter_title)

    if len(paragraphs) >= 40 and len(segments) == 1:
        return _fallback_chunk_segments(chapter_id, chapter_title, paragraphs)

    def is_low_value(summary: str) -> bool:
        lowered = (summary or "").strip().lower()
        return any(
            keyword in lowered
            for keyword in LOW_VALUE_SEGMENT_KEYWORDS["zh"] + LOW_VALUE_SEGMENT_KEYWORDS["en"]
        )

    trimmed = [
        segment
        for segment in segments
        if not is_low_value(segment.get("summary", ""))
    ]
    if trimmed:
        segments = trimmed

    merged: list[SemanticSegment] = []
    index = 0
    while index < len(segments):
        current = segments[index]
        if (
            current["tokens"] < 220
            and index + 1 < len(segments)
            and current["paragraph_end"] + 1 >= segments[index + 1]["paragraph_start"]
        ):
            nxt = segments[index + 1]
            start = current["paragraph_start"]
            end = nxt["paragraph_end"]
            paragraph_group = paragraphs[start - 1 : end]
            summary = f'{current["summary"]} / {nxt["summary"]}'
            merged.append(
                _merge_segment_group(
                    chapter_id=chapter_id,
                    paragraph_group=paragraph_group,
                    start=start,
                    end=end,
                    summary=summary,
                    offset=len(merged) + 1,
                )
            )
            index += 2
            continue

        merged.append(
            _merge_segment_group(
                chapter_id=chapter_id,
                paragraph_group=paragraphs[current["paragraph_start"] - 1 : current["paragraph_end"]],
                start=current["paragraph_start"],
                end=current["paragraph_end"],
                summary=current["summary"],
                offset=len(merged) + 1,
            )
        )
        index += 1

    return merged or fallback_segments(chapter_id, paragraphs, chapter_title)


def _format_numbered_paragraphs(paragraphs: list[str]) -> str:
    """Format numbered paragraphs for semantic segmentation prompt."""
    lines = []
    for index, paragraph in enumerate(paragraphs, start=1):
        preview = paragraph[:220]
        suffix = "..." if len(paragraph) > 220 else ""
        lines.append(f"[P{index}] {preview}{suffix}")
    return "\n\n".join(lines)


def _should_skip_chapter(title: str, text: str) -> bool:
    """Skip obvious front matter that should not enter deep reading."""
    normalized_title = title.strip().lower()
    if normalized_title in SKIP_TITLES:
        return True
    if normalized_title == "contents":
        return True
    if len(text.strip()) < 120 and normalized_title in {"title page", "copyright"}:
        return True
    return False


def segment_chapter_semantically(
    chapter_id: int,
    chapter_title: str,
    chapter_text: str,
    output_language: str,
    paragraphs: list[str] | None = None,
    *,
    chapter_heading_text: str = "",
    section_heading_text: str = "",
) -> list[SemanticSegment]:
    """Use the LLM to group chapter paragraphs into semantic units."""
    paragraphs = paragraphs or split_into_paragraphs(chapter_text)
    if not paragraphs:
        return fallback_segments(chapter_id, [chapter_text], chapter_title)

    payload = invoke_json(
        SEMANTIC_SEGMENTATION_SYSTEM,
        SEMANTIC_SEGMENTATION_PROMPT.format(
            chapter_title=chapter_title,
            paragraph_count=len(paragraphs),
            numbered_paragraphs=_format_numbered_paragraphs(paragraphs),
            output_language_name=language_name(output_language),
            chapter_heading_text=chapter_heading_text or "(none)",
            section_heading_text=section_heading_text or "(none)",
        ),
        default={"segments": []},
    )

    segments = payload.get("segments", []) if isinstance(payload, dict) else []
    normalized: list[SemanticSegment] = []

    for offset, item in enumerate(segments, start=1):
        if not isinstance(item, dict):
            continue

        start = int(item.get("paragraph_start", 0) or 0)
        end = int(item.get("paragraph_end", 0) or 0)
        if start < 1 or end < start or end > len(paragraphs):
            continue

        text = "\n\n".join(paragraphs[start - 1 : end])
        normalized.append(
            {
                "id": f"{chapter_id}.{offset}",
                "summary": (item.get("summary", "") or f"{chapter_title}片段 {offset}")[:120],
                "tokens": estimate_tokens(text),
                "text": text,
                "paragraph_start": start,
                "paragraph_end": end,
                "status": "pending",
            }
        )

    return _compact_segments(
        chapter_id=chapter_id,
        chapter_title=chapter_title,
        paragraphs=paragraphs,
        segments=normalized,
    )


def build_structure(
    book_path: Path,
    language_mode: str = "auto",
    continue_mode: bool = False,
    *,
    include_segments: bool = True,
) -> tuple[BookStructure, Path]:
    """Parse the ebook and persist structure.json incrementally."""
    title, author = extract_book_metadata(book_path)
    raw_chapters = parse_ebook(str(book_path))
    sample_text = "\n".join(extract_plain_text(ch.get("content", ""))[:300] for ch in raw_chapters[:3])
    book_language = detect_book_language(book_path, sample_text=sample_text)
    output_language = resolve_output_language(language_mode, book_language)
    output_dir = resolve_output_dir(book_path, title, book_language, output_language)
    ensure_output_dir(output_dir)
    if book_path.suffix.lower() == ".epub":
        ensure_source_asset(book_path, output_dir)
        _extract_epub_cover(book_path, output_dir)
    print(
        f"共检测到 {len(raw_chapters)} 个原始章节单元，开始{'语义切分' if include_segments else '提取原书目录'}...",
        flush=True,
    )
    book_document = _load_or_build_book_document(
        book_path,
        output_dir=output_dir,
        title=title,
        author=author,
        book_language=book_language,
        output_language=output_language,
        raw_chapters=raw_chapters,
    )
    contexts = _chapter_contexts_from_book_document(book_document, output_language=output_language)
    total_chapters = len(contexts)

    existing_structure: BookStructure | None = None
    if continue_mode:
        existing_path = existing_structure_file(output_dir)
        if existing_path.exists():
            existing_structure = load_structure(existing_path)
            _upgrade_structure_metadata(existing_structure, output_dir)

    existing_chapters = {
        int(chapter.get("id", 0)): chapter
        for chapter in (existing_structure or {}).get("chapters", [])
        if isinstance(chapter, dict)
    }

    chapters: list[StructureChapter] = []
    parsed_chapter_ids: list[int] = []
    for context in contexts:
        chapter_id = int(context.get("id", 0))
        existing_chapter = existing_chapters.get(chapter_id)
        if existing_chapter and _chapter_is_parsed(existing_chapter):
            chapters.append(existing_chapter)
            parsed_chapter_ids.append(chapter_id)
            continue
        chapters.append(_chapter_stub_from_context(output_dir, context))

    structure: BookStructure = {
        "book": title,
        "author": author,
        "book_language": book_language,
        "output_language": output_language,
        "source_file": str(book_path),
        "output_dir": str(output_dir),
        "chapters": chapters,
    }
    save_book_document(book_document_file(output_dir), book_document)
    _persist_structure_artifacts(output_dir, structure)

    resume_detected = continue_mode and bool(parsed_chapter_ids)
    if resume_detected:
        append_activity_event(
            output_dir,
            {
                "type": "resume_detected",
                "message": (
                    f"检测到语义切分 checkpoint，已恢复 {len(parsed_chapter_ids)}/{total_chapters} 个章节。"
                    if include_segments
                    else f"检测到目录解析 checkpoint，已恢复 {len(parsed_chapter_ids)}/{total_chapters} 个章节。"
                ),
            },
        )
    else:
        append_activity_event(
            output_dir,
            {
                "type": "parse_started",
                "message": (
                    f"开始准备深读结构，共 {total_chapters} 章。"
                    if include_segments
                    else f"开始解析原书目录，共 {total_chapters} 章。"
                ),
            },
        )

    if not include_segments:
        write_parse_progress(
            structure,
            output_dir,
            status="ready",
            total_chapters=total_chapters,
            completed_chapters=len(parsed_chapter_ids),
            parsed_chapter_ids=parsed_chapter_ids,
            last_checkpoint_at=_timestamp() if parsed_chapter_ids else None,
        )
        return structure, output_dir

    next_context = next((context for context in contexts if int(context.get("id", 0)) not in parsed_chapter_ids), None)
    write_parse_progress(
        structure,
        output_dir,
        status="parsing_structure" if next_context is not None else "ready",
        total_chapters=total_chapters,
        completed_chapters=len(parsed_chapter_ids),
        parsed_chapter_ids=parsed_chapter_ids,
        current_chapter_id=int(next_context.get("id", 0)) if next_context else None,
        current_chapter_ref=chapter_reference(_chapter_stub_from_context(output_dir, next_context)) if next_context else None,
        current_step="准备章节结构" if next_context else None,
        last_checkpoint_at=_timestamp() if parsed_chapter_ids else None,
    )

    for context in contexts:
        chapter_id = int(context.get("id", 0))
        if chapter_id in parsed_chapter_ids:
            continue

        chapter_ref = chapter_reference(_chapter_stub_from_context(output_dir, context))
        write_parse_progress(
            structure,
            output_dir,
            status="parsing_structure",
            total_chapters=total_chapters,
            completed_chapters=len(parsed_chapter_ids),
            parsed_chapter_ids=parsed_chapter_ids,
            current_chapter_id=chapter_id,
            current_chapter_ref=chapter_ref,
            current_step="语义切分中",
            last_checkpoint_at=_timestamp() if parsed_chapter_ids else None,
        )
        append_activity_event(
            output_dir,
            {
                "type": "parse_chapter_started",
                "message": f"开始解析 {chapter_ref}：{context.get('title', '')}",
                "chapter_id": chapter_id,
                "chapter_ref": chapter_ref,
            },
        )
        print(f"[parse] {chapter_ref}: {context.get('title', '')}", flush=True)

        chapter_record = segment_context_into_chapter(
            output_dir,
            context,
            progress=lambda message: print(f"  ├─ {message}", flush=True),
        )

        structure["chapters"] = [
            chapter_record if int(existing.get("id", 0)) == chapter_id else existing
            for existing in structure.get("chapters", [])
        ]
        parsed_chapter_ids.append(chapter_id)
        checkpoint_at = _timestamp()
        _persist_structure_artifacts(output_dir, structure)
        write_parse_progress(
            structure,
            output_dir,
            status="parsing_structure",
            total_chapters=total_chapters,
            completed_chapters=len(parsed_chapter_ids),
            parsed_chapter_ids=parsed_chapter_ids,
            current_chapter_id=chapter_id,
            current_chapter_ref=chapter_ref,
            current_step="已保存结构 checkpoint",
            last_checkpoint_at=checkpoint_at,
        )
        append_activity_event(
            output_dir,
            {
                "type": "parse_chapter_completed",
                "message": f"{chapter_ref} 结构解析完成，生成 {len(chapter_record.get('segments', []))} 个 section。",
                "chapter_id": chapter_id,
                "chapter_ref": chapter_ref,
            },
        )
        append_activity_event(
            output_dir,
            {
                "type": "structure_checkpoint_saved",
                "message": f"已保存解析 checkpoint：{chapter_ref}",
                "chapter_id": chapter_id,
                "chapter_ref": chapter_ref,
            },
        )
        print(f"  └─ {chapter_ref} 完成，生成 {len(chapter_record.get('segments', []))} 个 section", flush=True)

    final_checkpoint_at = _timestamp() if parsed_chapter_ids else None
    _persist_structure_artifacts(output_dir, structure)
    write_parse_progress(
        structure,
        output_dir,
        status="ready",
        total_chapters=total_chapters,
        completed_chapters=len(parsed_chapter_ids),
        parsed_chapter_ids=parsed_chapter_ids,
        last_checkpoint_at=final_checkpoint_at,
    )
    return structure, output_dir


def parse_book(book_path: Path, language_mode: str = "auto", continue_mode: bool = False) -> tuple[BookStructure, Path]:
    """Public parse-stage entry point."""
    try:
        structure, output_dir = build_structure(
            book_path,
            language_mode=language_mode,
            continue_mode=continue_mode,
            include_segments=False,
        )
    except Exception as exc:
        title, author = extract_book_metadata(book_path)
        sample_text = ""
        try:
            raw_chapters = parse_ebook(str(book_path))
            sample_text = "\n".join(extract_plain_text(ch.get("content", ""))[:300] for ch in raw_chapters[:3])
        except Exception:
            raw_chapters = []
        book_language = detect_book_language(book_path, sample_text=sample_text)
        output_language = resolve_output_language(language_mode, book_language)
        output_dir = resolve_output_dir(book_path, title, book_language, output_language)
        structure: BookStructure = {
            "book": title,
            "author": author,
            "book_language": book_language,
            "output_language": output_language,
            "source_file": str(book_path),
            "output_dir": str(output_dir),
            "chapters": [],
        }
        parsed_ids: list[int] = []
        parse_state_path = existing_parse_state_file(output_dir)
        if parse_state_path.exists():
            payload = load_json(parse_state_path)
            parsed_ids = [int(item) for item in payload.get("parsed_chapter_ids", [])]
            if existing_structure_file(output_dir).exists():
                structure = load_structure(existing_structure_file(output_dir))
        write_parse_progress(
            structure,
            output_dir,
            status="error",
            total_chapters=max(len(structure.get("chapters", [])), len(parsed_ids)),
            completed_chapters=len(parsed_ids),
            parsed_chapter_ids=parsed_ids,
            current_step="结构解析失败",
            last_checkpoint_at=_timestamp() if parsed_ids else None,
            error=str(exc),
        )
        append_activity_event(
            output_dir,
            {
                "type": "error",
                "message": f"结构解析中断：{exc}",
            },
        )
        raise

    parsed_chapter_ids = [int(chapter.get("id", 0)) for chapter in structure.get("chapters", []) if _chapter_is_parsed(chapter)]
    _persist_structure_artifacts(output_dir, structure)
    write_parse_progress(
        structure,
        output_dir,
        status="ready",
        total_chapters=len(structure.get("chapters", [])),
        completed_chapters=len(parsed_chapter_ids),
        parsed_chapter_ids=parsed_chapter_ids,
        last_checkpoint_at=_timestamp() if parsed_chapter_ids else None,
    )
    append_activity_event(
        output_dir,
        {
            "type": "structure_ready",
            "message": "结构已就绪，可开始顺序深读。",
        },
    )
    return structure, output_dir


def ensure_structure_for_book(
    book_path: Path,
    language_mode: str = "auto",
    *,
    continue_mode: bool = False,
    require_segments: bool = False,
) -> tuple[BookStructure, Path, bool]:
    """Load existing structure.json or create it when absent."""
    title, _author = extract_book_metadata(book_path)
    raw_chapters = parse_ebook(str(book_path))
    sample_text = "\n".join(extract_plain_text(ch.get("content", ""))[:300] for ch in raw_chapters[:3])
    book_language = detect_book_language(book_path, sample_text=sample_text)
    output_language = resolve_output_language(language_mode, book_language)
    output_dir = resolve_output_dir(book_path, title, book_language, output_language)
    ensure_output_dir(output_dir)
    book_document = _load_or_build_book_document(
        book_path,
        output_dir=output_dir,
        title=title,
        author=_author,
        book_language=book_language,
        output_language=output_language,
        raw_chapters=raw_chapters,
    )
    path = existing_structure_file(output_dir)
    had_existing_structure = path.exists()
    if path.exists():
        structure = load_structure(path)
        if book_path.suffix.lower() == ".epub":
            ensure_source_asset(book_path, output_dir)
            _extract_epub_cover(book_path, output_dir)
        if (
            structure.get("book_language") == book_language
            and structure.get("output_language") == output_language
        ):
            changed = _upgrade_structure_metadata(structure, output_dir)
            canonical_path = structure_file(output_dir)
            parse_complete = all(_chapter_is_parsed(chapter) for chapter in structure.get("chapters", []))
            if changed or path != canonical_path:
                _persist_structure_artifacts(output_dir, structure)
            if parse_complete or not require_segments:
                save_book_document(book_document_file(output_dir), book_document)
                return structure, output_dir, False
            if not continue_mode:
                save_book_document(book_document_file(output_dir), book_document)
                return structure, output_dir, False
    structure, output_dir = build_structure(
        book_path,
        language_mode=language_mode,
        continue_mode=continue_mode,
        include_segments=require_segments,
    )
    return structure, output_dir, not had_existing_structure


def _upgrade_structure_metadata(structure: BookStructure, output_dir: Path) -> bool:
    """Backfill chapter metadata and migrate legacy output filenames."""
    changed = False
    for chapter in structure.get("chapters", []):
        inferred_number = infer_chapter_number(chapter.get("title", ""))
        if chapter.get("chapter_number") != inferred_number:
            if inferred_number is not None:
                chapter["chapter_number"] = inferred_number
            changed = True

        primary_role, role_tags, role_confidence = _infer_chapter_role(
            {
                "title": chapter.get("title", ""),
                "chapter_number": chapter.get("chapter_number"),
                "chapter_heading": chapter.get("chapter_heading"),
                "body_groups": [],
            }
        )
        if chapter.get("primary_role") != primary_role:
            chapter["primary_role"] = primary_role
            changed = True
        if list(chapter.get("role_tags", [])) != role_tags:
            chapter["role_tags"] = role_tags
            changed = True
        if chapter.get("role_confidence") != role_confidence:
            chapter["role_confidence"] = role_confidence
            changed = True

        for segment in chapter.get("segments", []):
            segment_ref = segment_reference(chapter, segment.get("id", ""))
            if segment.get("segment_ref") != segment_ref:
                segment["segment_ref"] = segment_ref
                changed = True
            if "section_heading" not in segment:
                segment["section_heading"] = ""
                changed = True
            if "paragraph_locators" not in segment:
                segment["paragraph_locators"] = []
                changed = True
            status = segment.get("status")
            if status not in {"pending", "done", "skipped"}:
                segment["status"] = "pending"
                changed = True

        expected_path = chapter_markdown_file(output_dir, chapter)
        expected_name = relative_output_path(output_dir, expected_path)
        current_name = chapter.get("output_file")

        if not current_name:
            legacy_name = f'ch{chapter.get("id", 0):02d}_deep_read.md'
            legacy_path = output_dir / legacy_name
            if legacy_path.exists() and not expected_path.exists():
                legacy_path.rename(expected_path)
                chapter["output_file"] = expected_name
                changed = True
                continue
            if expected_path.exists():
                chapter["output_file"] = expected_name
                changed = True
            continue

        if current_name == expected_name:
            continue

        current_path = output_dir / str(current_name)

        if current_path.exists() and not expected_path.exists():
            expected_path.parent.mkdir(parents=True, exist_ok=True)
            current_path.rename(expected_path)
            chapter["output_file"] = expected_name
            changed = True
            continue

        if expected_path.exists():
            chapter["output_file"] = expected_name
            changed = True

    return changed


def _manifest_cover_url(output_dir: Path) -> str | None:
    """Return the persisted cover asset path stored in one manifest."""
    cover_asset = existing_cover_asset_file(output_dir)
    if cover_asset is None:
        return None
    return str(cover_asset.relative_to(output_dir))


def _timestamp() -> str:
    """Return a stable UTC timestamp."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalized_title_key(title: str) -> str:
    """Normalize chapter titles for fuzzy matching during legacy backfill."""
    return re.sub(r"\s+", " ", str(title or "").strip()).lower()


def _legacy_locator_paragraphs(records: list[dict[str, object]]) -> list[dict[str, object]]:
    """Render stable paragraph-locator payloads from parsed EPUB records."""
    return [
        {
            "href": str(record.get("href", "")),
            "start_cfi": record.get("start_cfi"),
            "end_cfi": record.get("end_cfi"),
            "paragraph_index": int(record.get("paragraph_index", 0) or 0),
            "text": str(record.get("text", "")),
            "block_tag": str(record.get("block_tag", "p") or "p"),
            "heading_level": record.get("heading_level"),
            "text_role": str(record.get("text_role", "body") or "body"),
        }
        for record in records
    ]


def _legacy_locator_payload(locator: object) -> dict[str, object] | None:
    """Render one stable section locator payload."""
    if not isinstance(locator, dict):
        return None
    href = str(locator.get("href", "") or "").strip()
    if not href:
        return None
    return {
        "href": href,
        "start_cfi": locator.get("start_cfi"),
        "end_cfi": locator.get("end_cfi"),
        "paragraph_start": int(locator.get("paragraph_start", 0) or 0),
        "paragraph_end": int(locator.get("paragraph_end", 0) or 0),
    }


def _normalized_locator_text(text: str) -> str:
    """Normalize text for legacy locator backfill matching."""
    normalized = (text or "").replace("’", "'").replace("“", '"').replace("”", '"')
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip().lower()


def _records_text(records: list[dict[str, object]]) -> str:
    """Render one contiguous paragraph-record window back into plain text."""
    return "\n\n".join(str(record.get("text", "") or "") for record in records if str(record.get("text", "") or "").strip())


def _trim_structural_prefix_from_text(text: str) -> tuple[str, list[str]]:
    """Trim leading heading-like paragraphs from one legacy segment text."""
    paragraphs = split_into_paragraphs(text)
    if not paragraphs:
        return text, []

    removed: list[str] = []
    kept: list[str] = []
    for paragraph in paragraphs:
        if not kept and (
            _looks_like_auxiliary_text(paragraph, at_chapter_start=True)
            or _looks_like_heading_text(paragraph, block_tag="p", at_chapter_start=True)
        ):
            removed.append(paragraph)
            continue
        kept.append(paragraph)

    trimmed = "\n\n".join(kept).strip()
    return (trimmed or text), removed


def _summary_from_body_text(text: str, *, max_length: int = 120) -> str:
    """Generate one deterministic fallback summary from cleaned body text."""
    paragraphs = split_into_paragraphs(text)
    if not paragraphs:
        return ""
    first_paragraph = paragraphs[0].strip()
    first_sentence = re.split(r"(?<=[.!?。！？])\s+", first_paragraph, maxsplit=1)[0].strip()
    summary = first_sentence or first_paragraph
    if len(summary) <= max_length:
        return summary
    return f"{summary[: max_length - 3].rstrip()}..."


def _summary_looks_structural(summary: str, removed_prefixes: list[str]) -> bool:
    """Return whether one summary still smells like a heading/body hybrid."""
    normalized_summary = _normalized_locator_text(summary)
    if not normalized_summary:
        return False
    if any(keyword in normalized_summary for keyword in ("chapter title", "epilogue title", "prologue title", "chapter heading")):
        return True
    for prefix in removed_prefixes:
        normalized_prefix = _normalized_locator_text(prefix)
        if not normalized_prefix:
            continue
        if SequenceMatcher(None, normalized_summary, normalized_prefix).ratio() >= 0.38:
            return True
        prefix_tokens = [token for token in normalized_prefix.split() if len(token) >= 4]
        if prefix_tokens and sum(1 for token in prefix_tokens if token in normalized_summary) >= min(3, len(prefix_tokens)):
            return True
    return False


def _records_match_score(target_text: str, records: list[dict[str, object]]) -> float:
    """Score how well one record window matches legacy segment text."""
    target = _normalized_locator_text(target_text)
    candidate = _normalized_locator_text(_records_text(records))
    if not target or not candidate:
        return 0.0
    if target == candidate:
        return 2.0

    score = SequenceMatcher(None, target, candidate).ratio()
    if target in candidate or candidate in target:
        score += 0.3
    return score


def _resolve_segment_records(
    segment: dict[str, object],
    paragraph_records: list[dict[str, object]],
    *,
    search_start: int = 0,
) -> tuple[list[dict[str, object]], float]:
    """Resolve the best paragraph-record window for one legacy segment."""
    start = int(segment.get("paragraph_start", 0) or 0)
    end = int(segment.get("paragraph_end", 0) or 0)
    target_text = str(segment.get("text", "") or "")
    target_length = len(_normalized_locator_text(target_text))

    if start >= 1 and end >= start:
        legacy_records = paragraph_records[start - 1 : end]
        legacy_score = _records_match_score(target_text, legacy_records)
        if legacy_records and (legacy_score >= 0.9 or (target_length >= 240 and legacy_score >= 0.8)):
            return legacy_records, legacy_score

    if not target_text.strip() or not paragraph_records:
        return [], 0.0

    safe_start = max(0, min(search_start, len(paragraph_records) - 1))
    best_records: list[dict[str, object]] = []
    best_score = 0.0
    max_window = min(32, len(paragraph_records))

    for start_index in range(safe_start, len(paragraph_records)):
        running: list[dict[str, object]] = []
        degraded = 0
        for end_index in range(start_index, min(len(paragraph_records), start_index + max_window)):
            running.append(paragraph_records[end_index])
            score = _records_match_score(target_text, running)
            if score > best_score:
                best_score = score
                best_records = list(running)
                if score >= 1.99:
                    return best_records, best_score

            candidate_length = len(_normalized_locator_text(_records_text(running)))
            if candidate_length > target_length * 1.4 and score < best_score - 0.12:
                degraded += 1
                if degraded >= 2:
                    break

    return best_records, best_score


def _iter_kept_source_chapters(book_path: Path) -> list[tuple[int, dict[str, object]]]:
    """Parse one source EPUB and return the chapters that would enter deep reading."""
    chapters: list[tuple[int, dict[str, object]]] = []
    for index, chapter in enumerate(parse_ebook(str(book_path)), start=1):
        chapter_text = extract_plain_text(str(chapter.get("content", "") or ""))
        if not chapter_text.strip():
            continue
        title = str(chapter.get("title", f"Chapter {index}") or f"Chapter {index}")
        if _should_skip_chapter(title, chapter_text):
            continue
        chapters.append((index, chapter))
    return chapters


def _match_legacy_source_chapter(
    chapter: StructureChapter,
    source_chapters: list[tuple[int, dict[str, object]]],
    used_indexes: set[int],
) -> dict[str, object] | None:
    """Match one legacy structure chapter to its parsed EPUB chapter."""
    chapter_id = int(chapter.get("id", 0) or 0)
    preferred = next((candidate for index, candidate in source_chapters if index == chapter_id), None)
    if preferred is not None:
        used_indexes.add(chapter_id)
        return preferred

    title_key = _normalized_title_key(chapter.get("title", ""))
    for index, candidate in source_chapters:
        if index in used_indexes:
            continue
        if _normalized_title_key(candidate.get("title", "")) != title_key:
            continue
        used_indexes.add(index)
        return candidate
    return None


def hydrate_legacy_epub_locators(output_dir: Path, structure: BookStructure, book_path: Path) -> list[str]:
    """Backfill missing EPUB locators into structure and chapter-result artifacts."""
    if book_path.suffix.lower() != ".epub":
        return []

    source_chapters = _iter_kept_source_chapters(book_path)
    if not source_chapters:
        return []

    structure_changed = False
    used_indexes: set[int] = set()
    for chapter in structure.get("chapters", []):
        source = _match_legacy_source_chapter(chapter, source_chapters, used_indexes)
        if source is None:
            continue

        item_id = str(source.get("item_id", "") or "")
        href = str(source.get("href", "") or "")
        spine_index = int(source.get("spine_index", -1) or -1)

        if chapter.get("item_id") != item_id:
            chapter["item_id"] = item_id
            structure_changed = True
        if chapter.get("href") != href:
            chapter["href"] = href
            structure_changed = True
        if chapter.get("spine_index") != spine_index:
            chapter["spine_index"] = spine_index
            structure_changed = True

        paragraph_records = _classify_paragraph_records(_paragraph_records(source))
        chapter_heading = _chapter_heading_block(paragraph_records)
        if chapter_heading:
            if chapter.get("chapter_heading") != chapter_heading:
                chapter["chapter_heading"] = chapter_heading
                structure_changed = True
        elif chapter.get("chapter_heading"):
            chapter.pop("chapter_heading", None)
            structure_changed = True

        body_records = [
            record
            for record in paragraph_records
            if str(record.get("text_role", "body")) == "body"
            and str(record.get("text", "")).strip()
        ]
        search_records = body_records or paragraph_records
        paragraph_position = {
            int(record.get("paragraph_index", 0) or 0): position
            for position, record in enumerate(search_records, start=1)
        }
        chapter_wide_paragraph_payload = _legacy_locator_paragraphs(search_records)
        search_start = 0
        for segment in chapter.get("segments", []):
            target_text, removed_prefixes = _trim_structural_prefix_from_text(str(segment.get("text", "") or ""))
            candidate_segment = dict(segment)
            candidate_segment["text"] = target_text

            legacy_start = int(segment.get("paragraph_start", 0) or 0)
            legacy_end = int(segment.get("paragraph_end", 0) or 0)
            if legacy_start in paragraph_position and legacy_end in paragraph_position:
                candidate_segment["paragraph_start"] = paragraph_position[legacy_start]
                candidate_segment["paragraph_end"] = paragraph_position[legacy_end]
            else:
                candidate_segment["paragraph_start"] = 0
                candidate_segment["paragraph_end"] = 0

            segment_records, _match_score = _resolve_segment_records(
                candidate_segment,
                search_records,
                search_start=search_start,
            )
            locator = _segment_locator_from_records(segment_records)
            locator_payload = _legacy_locator_payload(locator)
            paragraph_payload = _legacy_locator_paragraphs(segment_records)
            cleaned_segment_text = _records_text(segment_records) if segment_records else target_text

            if segment_records:
                new_start = int(segment_records[0].get("paragraph_index", 0) or 0)
                new_end = int(segment_records[-1].get("paragraph_index", 0) or 0)
                if segment.get("paragraph_start") != new_start:
                    segment["paragraph_start"] = new_start
                    structure_changed = True
                if segment.get("paragraph_end") != new_end:
                    segment["paragraph_end"] = new_end
                    structure_changed = True
                search_start = max(0, paragraph_position.get(new_end, 1) - 1)

            if locator_payload:
                if segment.get("locator") != locator_payload:
                    segment["locator"] = locator_payload
                    structure_changed = True
            elif "locator" in segment:
                segment.pop("locator", None)
                structure_changed = True

            if segment.get("paragraph_locators") != paragraph_payload:
                segment["paragraph_locators"] = paragraph_payload
                structure_changed = True
            if cleaned_segment_text and str(segment.get("text", "") or "") != cleaned_segment_text:
                segment["text"] = cleaned_segment_text
                structure_changed = True
            if removed_prefixes and _summary_looks_structural(str(segment.get("summary", "") or ""), removed_prefixes):
                fallback_summary = _summary_from_body_text(cleaned_segment_text)
                if fallback_summary and str(segment.get("summary", "") or "") != fallback_summary:
                    segment["summary"] = fallback_summary
                    structure_changed = True

    if structure_changed:
        save_structure(structure_file(output_dir), structure)

    result_changed = False
    for chapter in structure.get("chapters", []):
        result_path = existing_chapter_result_file(output_dir, chapter)
        if not result_path.exists():
            continue

        payload = load_json(result_path)
        segment_meta_by_id = {
            str(segment.get("id", "")): segment
            for segment in chapter.get("segments", [])
            if isinstance(segment, dict)
        }
        reaction_locators: dict[str, dict[str, object]] = {}
        chapter_result_changed = False
        chapter_heading = chapter.get("chapter_heading")
        if chapter_heading:
            if payload.get("chapter_heading") != chapter_heading:
                payload["chapter_heading"] = chapter_heading
                chapter_result_changed = True
        elif payload.get("chapter_heading"):
            payload.pop("chapter_heading", None)
            chapter_result_changed = True

        for section in payload.get("sections", []):
            if not isinstance(section, dict):
                continue
            segment_meta = segment_meta_by_id.get(str(section.get("segment_id", "")))
            if not isinstance(segment_meta, dict):
                continue

            section_locator = _legacy_locator_payload(segment_meta.get("locator"))
            paragraph_locators = [
                item
                for item in list(segment_meta.get("paragraph_locators", []))
                if isinstance(item, dict)
            ]

            if section_locator:
                if section.get("locator") != section_locator:
                    section["locator"] = section_locator
                    chapter_result_changed = True
            elif section.get("locator"):
                section.pop("locator", None)
                chapter_result_changed = True

            if section.get("original_text") != str(segment_meta.get("text", "")):
                section["original_text"] = str(segment_meta.get("text", ""))
                chapter_result_changed = True
            if section.get("summary") != str(segment_meta.get("summary", "")):
                section["summary"] = str(segment_meta.get("summary", ""))
                chapter_result_changed = True

            for reaction in section.get("reactions", []):
                if not isinstance(reaction, dict):
                    continue
                reaction_paragraph_locators = paragraph_locators or chapter_wide_paragraph_payload
                target_locator = _reaction_target_locator(
                    str(reaction.get("anchor_quote", "")),
                    section_locator,
                    reaction_paragraph_locators,
                )
                reaction_id = str(reaction.get("reaction_id", ""))
                if target_locator:
                    if reaction.get("target_locator") != target_locator:
                        reaction["target_locator"] = target_locator
                        chapter_result_changed = True
                    if reaction_id:
                        reaction_locators[reaction_id] = target_locator
                elif reaction.get("target_locator"):
                    reaction.pop("target_locator", None)
                    chapter_result_changed = True

        for featured in payload.get("featured_reactions", []):
            if not isinstance(featured, dict):
                continue
            target_locator = reaction_locators.get(str(featured.get("reaction_id", "")))
            if target_locator:
                if featured.get("target_locator") != target_locator:
                    featured["target_locator"] = target_locator
                    chapter_result_changed = True
            elif featured.get("target_locator"):
                featured.pop("target_locator", None)
                chapter_result_changed = True

        if chapter_result_changed:
            save_json(result_path, payload)
            result_changed = True

    changes: list[str] = []
    if structure_changed:
        changes.append("structure_locators")
    if result_changed:
        changes.append("result_locators")
    return changes


def _resolve_source_epub_path(output_dir: Path, manifest: dict, root: Path) -> Path | None:
    """Find the best EPUB source path for one existing output directory."""
    source_asset = str(manifest.get("source_asset", {}).get("file", "") or "").strip()
    if source_asset:
        candidate = output_dir / source_asset
        if candidate.exists() and candidate.suffix.lower() == ".epub":
            return candidate

    source_file = str(manifest.get("source_file", "") or "").strip()
    if source_file:
        candidate = Path(source_file)
        if not candidate.is_absolute():
            candidate = root / candidate
        if candidate.exists() and candidate.suffix.lower() == ".epub":
            return candidate

    return None


def _refresh_manifest_cover(output_dir: Path) -> bool:
    """Sync one book manifest's cover_image_url with the extracted asset."""
    manifest_path = existing_book_manifest_file(output_dir)
    if not manifest_path.exists():
        return False

    manifest = load_json(manifest_path)
    cover_url = _manifest_cover_url(output_dir)
    if manifest.get("cover_image_url") == cover_url:
        return False

    manifest["cover_image_url"] = cover_url
    manifest["updated_at"] = _timestamp()
    save_json(manifest_path, manifest)
    return True


def backfill_missing_epub_covers(root: Path | None = None) -> list[dict[str, object]]:
    """Extract missing covers for existing EPUB outputs and refresh manifests."""
    runtime_root = root or Path.cwd()
    results: list[dict[str, object]] = []

    manifest_paths = sorted((runtime_root / "output").glob("*/public/book_manifest.json"))
    manifest_paths.extend(sorted((runtime_root / "output").glob("*/book_manifest.json")))
    seen_output_dirs: set[Path] = set()
    for manifest_path in manifest_paths:
        output_dir = manifest_path.parent.parent if manifest_path.parent.name == "public" else manifest_path.parent
        if output_dir in seen_output_dirs:
            continue
        seen_output_dirs.add(output_dir)
        manifest = load_json(manifest_path)
        book_id = str(manifest.get("book_id", output_dir.name))
        current_cover = _manifest_cover_url(output_dir)

        if current_cover and manifest.get("cover_image_url") == current_cover:
            results.append({"book_id": book_id, "status": "already_present", "cover_image_url": current_cover})
            continue

        source_path = _resolve_source_epub_path(output_dir, manifest, runtime_root)
        if source_path is None:
            results.append({"book_id": book_id, "status": "missing_source", "cover_image_url": current_cover})
            continue

        extracted = _extract_epub_cover(source_path, output_dir)
        manifest_updated = _refresh_manifest_cover(output_dir)
        cover_url = _manifest_cover_url(output_dir)

        if extracted is not None:
            status = "updated" if manifest_updated or not current_cover else "refreshed"
        elif cover_url:
            status = "manifest_synced" if manifest_updated else "already_present"
        else:
            status = "no_cover_found"

        results.append({"book_id": book_id, "status": status, "cover_image_url": cover_url})

    return results

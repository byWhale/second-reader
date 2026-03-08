"""Parse-stage logic for structure generation and semantic segmentation."""

from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree as ET
import ebooklib
from ebooklib import epub

from src.parsers import parse_ebook
from src.prompts.templates import (
    SEMANTIC_SEGMENTATION_PROMPT,
    SEMANTIC_SEGMENTATION_SYSTEM,
)

from .language import detect_book_language, language_name, resolve_output_language
from .llm_utils import invoke_json
from .frontend_artifacts import (
    append_activity_event,
    build_run_state,
    reset_activity,
    write_book_manifest,
    write_run_state,
)
from .models import BookStructure, SemanticSegment, StructureChapter
from .storage import (
    chapter_output_name,
    cover_asset_file,
    ensure_output_dir,
    ensure_source_asset,
    infer_chapter_number,
    resolve_output_dir,
    save_structure,
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
        if tag in BLOCK_TAGS and text:
            cfi = _cfi_for_element(spine_index, item_id, path_steps)
            records.append(
                {
                    "text": text,
                    "href": href,
                    "start_cfi": cfi,
                    "end_cfi": cfi,
                    "paragraph_index": len(records) + 1,
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
        }
        for index, paragraph in enumerate(split_into_paragraphs(extract_plain_text(content)), start=1)
    ]


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


def _extract_epub_cover(book_path: Path, output_dir: Path) -> Path | None:
    """Extract the EPUB cover image into the frontend asset directory when available."""
    try:
        book = epub.read_epub(str(book_path))
    except Exception:
        return None

    cover_item = None
    metadata = book.get_metadata("OPF", "cover")
    if metadata:
        cover_id = str(metadata[0][0] or "").strip()
        if cover_id:
            try:
                cover_item = book.get_item_with_id(cover_id)
            except Exception:
                cover_item = None

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

    destination = cover_asset_file(output_dir, _cover_extension(cover_item))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)
    return destination


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


def build_structure(book_path: Path, language_mode: str = "auto") -> tuple[BookStructure, Path]:
    """Parse the ebook and persist structure.json."""
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
    print(f"共检测到 {len(raw_chapters)} 个原始章节单元，开始语义分段...")
    chapters: list[StructureChapter] = []

    for chapter_index, chapter in enumerate(raw_chapters, start=1):
        paragraph_records = _paragraph_records(chapter)
        chapter_text = "\n\n".join(str(record.get("text", "")) for record in paragraph_records)
        if not chapter_text.strip():
            continue
        chapter_title = chapter.get("title", f"Chapter {chapter_index}")
        if _should_skip_chapter(chapter_title, chapter_text):
            print(f"[skip] {chapter_title}")
            continue

        print(f"[parse] Chapter {chapter_index}: {chapter_title}")

        segments = segment_chapter_semantically(
            chapter_id=chapter_index,
            chapter_title=chapter_title,
            chapter_text=chapter_text,
            output_language=output_language,
            paragraphs=[str(record.get("text", "")) for record in paragraph_records],
        )
        chapter_record: StructureChapter = {
            "id": chapter_index,
            "title": chapter_title,
            "chapter_number": infer_chapter_number(chapter_title),
            "status": "pending",
            "level": chapter.get("level", 1),
            "segments": segments,
        }
        if chapter.get("item_id"):
            chapter_record["item_id"] = str(chapter.get("item_id", ""))
        if chapter.get("href"):
            chapter_record["href"] = str(chapter.get("href", ""))
        if chapter.get("spine_index") is not None:
            chapter_record["spine_index"] = int(chapter.get("spine_index", 0))
        for segment in chapter_record.get("segments", []):
            segment["segment_ref"] = segment_reference(chapter_record, segment.get("id", ""))
            start = int(segment.get("paragraph_start", 0) or 0)
            end = int(segment.get("paragraph_end", 0) or 0)
            segment_records = paragraph_records[start - 1 : end]
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
                }
                for record in segment_records
            ]
        chapters.append(chapter_record)

    structure: BookStructure = {
        "book": title,
        "author": author,
        "book_language": book_language,
        "output_language": output_language,
        "source_file": str(book_path),
        "output_dir": str(output_dir),
        "chapters": chapters,
    }
    save_structure(structure_file(output_dir), structure)
    structure_markdown_file(output_dir).write_text(
        render_structure_markdown(structure),
        encoding="utf-8",
    )
    return structure, output_dir


def parse_book(book_path: Path, language_mode: str = "auto") -> tuple[BookStructure, Path]:
    """Public parse-stage entry point."""
    structure, output_dir = build_structure(book_path, language_mode=language_mode)
    write_book_manifest(output_dir, structure)
    reset_activity(output_dir)
    write_run_state(
        output_dir,
        build_run_state(
            structure,
            stage="ready",
            total_chapters=len(structure.get("chapters", [])),
            completed_chapters=sum(1 for chapter in structure.get("chapters", []) if chapter.get("status") == "done"),
        ),
    )
    append_activity_event(
        output_dir,
        {
            "type": "structure_ready",
            "message": "结构已就绪，可开始顺序深读。",
        },
    )
    return structure, output_dir


def ensure_structure_for_book(book_path: Path, language_mode: str = "auto") -> tuple[BookStructure, Path, bool]:
    """Load existing structure.json or create it when absent."""
    title, _author = extract_book_metadata(book_path)
    raw_chapters = parse_ebook(str(book_path))
    sample_text = "\n".join(extract_plain_text(ch.get("content", ""))[:300] for ch in raw_chapters[:3])
    book_language = detect_book_language(book_path, sample_text=sample_text)
    output_language = resolve_output_language(language_mode, book_language)
    output_dir = resolve_output_dir(book_path, title, book_language, output_language)
    path = structure_file(output_dir)
    if path.exists():
        from .storage import load_structure

        structure = load_structure(path)
        if book_path.suffix.lower() == ".epub":
            ensure_source_asset(book_path, output_dir)
            _extract_epub_cover(book_path, output_dir)
        if (
            structure.get("book_language") == book_language
            and structure.get("output_language") == output_language
        ):
            if _upgrade_structure_metadata(structure, output_dir):
                save_structure(path, structure)
            return structure, output_dir, False
    structure, output_dir = build_structure(book_path, language_mode=language_mode)
    return structure, output_dir, True


def _upgrade_structure_metadata(structure: BookStructure, output_dir: Path) -> bool:
    """Backfill chapter metadata and migrate legacy output filenames."""
    changed = False
    for chapter in structure.get("chapters", []):
        inferred_number = infer_chapter_number(chapter.get("title", ""))
        if chapter.get("chapter_number") != inferred_number:
            if inferred_number is not None:
                chapter["chapter_number"] = inferred_number
            changed = True

        for segment in chapter.get("segments", []):
            segment_ref = segment_reference(chapter, segment.get("id", ""))
            if segment.get("segment_ref") != segment_ref:
                segment["segment_ref"] = segment_ref
                changed = True
            if "paragraph_locators" not in segment:
                segment["paragraph_locators"] = []
                changed = True
            status = segment.get("status")
            if status not in {"pending", "done", "skipped"}:
                segment["status"] = "pending"
                changed = True

        expected_name = chapter_output_name(chapter)
        expected_path = output_dir / expected_name
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

        current_path = output_dir / current_name

        if current_path.exists() and not expected_path.exists():
            current_path.rename(expected_path)
            chapter["output_file"] = expected_name
            changed = True
            continue

        if expected_path.exists():
            chapter["output_file"] = expected_name
            changed = True

    return changed

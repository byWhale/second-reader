"""Adapter that exposes the current Iterator-Reader as one pluggable mechanism."""

from __future__ import annotations

from collections import defaultdict
import json
from datetime import datetime, timezone
from pathlib import Path
import unicodedata

from src.iterator_reader.iterator import read_book as iterator_read_book
from src.iterator_reader.parse import parse_book as iterator_parse_book
from src.iterator_reader.prompts import ITERATOR_V1_PROMPTS
from src.prompts.capabilities.book_analysis import BOOK_ANALYSIS_PROMPTS
from src.iterator_reader.storage import (
    existing_activity_file,
    existing_book_manifest_file,
    existing_chapter_result_file,
    existing_reader_memory_file,
    existing_run_state_file,
    load_json,
    normalized_eval_bundle_file,
    save_json,
)
from src.reading_core.normalized_outputs import (
    NormalizedAttentionEvent,
    NormalizedChapterOutput,
    NormalizedEvalBundle,
    NormalizedReaction,
    NormalizedRunSnapshot,
)
from src.reading_core.runtime_contracts import MechanismInfo, ParseRequest, ParseResult, ReadRequest, ReadResult, stable_config_fingerprint
from src.reading_core.storage import existing_book_document_file, load_book_document


class IteratorV1Mechanism:
    """Thin adapter over the existing iterator reader implementation."""

    info = MechanismInfo(
        key="iterator_v1",
        label="Current Iterator-Reader implementation",
    )

    @property
    def key(self) -> str:
        """Backwards-compatible access to the mechanism key."""

        return self.info.key

    @property
    def label(self) -> str:
        """Backwards-compatible access to the mechanism label."""

        return self.info.label

    def parse_book(self, request: ParseRequest) -> ParseResult:
        """Delegate parse-side structure generation to the existing implementation."""

        structure, output_dir = iterator_parse_book(
            request.book_path,
            language_mode=request.language_mode,
            continue_mode=request.continue_mode,
            prompt_set=ITERATOR_V1_PROMPTS,
        )
        book_document = load_book_document(existing_book_document_file(output_dir))
        return ParseResult(
            mechanism=self.info,
            book_document=book_document,
            output_dir=output_dir,
            mechanism_artifact=structure,
        )

    def read_book(self, request: ReadRequest) -> ReadResult:
        """Delegate book reading to the current iterator runtime."""

        mechanism_config = dict(request.mechanism_config)
        skill_profile = str(mechanism_config.get("skill_profile", "balanced") or "balanced")
        budget_policy = dict(mechanism_config.get("budget_policy", {}) or {}) or None
        analysis_policy = dict(mechanism_config.get("analysis_policy", {}) or {}) or None

        structure, output_dir, created = iterator_read_book(
            request.book_path,
            chapter_number=request.chapter_number,
            continue_mode=request.continue_mode,
            user_intent=request.user_intent,
            language_mode=request.language_mode,
            read_mode=request.task_mode,
            skill_profile=skill_profile,  # type: ignore[arg-type]
            budget_policy=budget_policy,  # type: ignore[arg-type]
            analysis_policy=analysis_policy,  # type: ignore[arg-type]
            prompt_set=ITERATOR_V1_PROMPTS,
            book_analysis_prompt_set=BOOK_ANALYSIS_PROMPTS,
        )
        book_document = load_book_document(existing_book_document_file(output_dir))
        normalized_eval_bundle = _normalized_eval_bundle(
            output_dir=output_dir,
            structure=structure,
            config_payload={
                "task_mode": request.task_mode,
                "mechanism_config": mechanism_config,
            },
        )
        if bool(mechanism_config.get("persist_normalized_eval_bundle")):
            save_json(normalized_eval_bundle_file(output_dir), normalized_eval_bundle)
        return ReadResult(
            mechanism=self.info,
            book_document=book_document,
            output_dir=output_dir,
            created=created,
            mechanism_artifact=structure,
            normalized_eval_bundle=normalized_eval_bundle,
        )


def _timestamp() -> str:
    """Return a stable UTC timestamp for normalized output bundles."""

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_jsonl(path: Path) -> list[dict[str, object]]:
    """Load one JSONL file into a list of dictionaries."""

    if not path.exists():
        return []
    items: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            items.append(payload)
    return items


def _normalize_with_offsets(value: str, offsets: list[object] | None = None) -> tuple[str, list[object]]:
    """Normalize text while preserving raw-position offsets for source-span recovery."""

    raw_offsets = offsets if offsets is not None else [None] * len(value)
    chars: list[tuple[str, object]] = []
    for character, offset in zip(value, raw_offsets, strict=False):
        normalized = unicodedata.normalize("NFKC", character)
        normalized = normalized.replace("“", '"').replace("”", '"')
        normalized = normalized.replace("’", "'").replace("–", "-").replace("—", "-")
        normalized = normalized.replace("…", "...")
        normalized = normalized.lower()
        for item in normalized:
            chars.append((" " if item.isspace() else item, offset))

    collapsed: list[tuple[str, object]] = []
    for character, offset in chars:
        if character == " " and (not collapsed or collapsed[-1][0] == " "):
            continue
        collapsed.append((character, offset))
    while collapsed and collapsed[0][0] == " ":
        collapsed.pop(0)
    while collapsed and collapsed[-1][0] == " ":
        collapsed.pop()

    punctuation = set(",.;:!?()\"'")
    filtered: list[tuple[str, object]] = []
    for index, (character, offset) in enumerate(collapsed):
        if character == " ":
            previous_character = collapsed[index - 1][0] if index > 0 else ""
            next_character = collapsed[index + 1][0] if index + 1 < len(collapsed) else ""
            if previous_character in punctuation or next_character in punctuation:
                continue
        filtered.append((character, offset))
    return "".join(character for character, _offset in filtered), [offset for _character, offset in filtered]


def _chapter_paragraph_texts(document: dict[str, object]) -> dict[int, dict[int, str]]:
    """Index public book-document paragraph text by chapter and paragraph index."""

    by_chapter: dict[int, dict[int, str]] = {}
    for chapter in document.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        chapter_id = int(chapter.get("id", 0) or 0)
        paragraphs: dict[int, str] = {}
        for paragraph in chapter.get("paragraphs", []):
            if not isinstance(paragraph, dict):
                continue
            paragraph_index = int(paragraph.get("paragraph_index", 0) or 0)
            text = str(paragraph.get("text", "") or "")
            if paragraph_index > 0 and text:
                paragraphs[paragraph_index] = text
        by_chapter[chapter_id] = paragraphs
    return by_chapter


def _chapter_text_with_offsets(paragraphs: dict[int, str]) -> tuple[str, list[tuple[int, int] | None]]:
    """Render chapter paragraph text with offsets back to paragraph-local coordinates."""

    text_parts: list[str] = []
    offsets: list[tuple[int, int] | None] = []
    for paragraph_index, paragraph_text in sorted(paragraphs.items()):
        if text_parts:
            text_parts.append("\n\n")
            offsets.extend([None, None])
        text_parts.append(paragraph_text)
        offsets.extend((paragraph_index, char_index) for char_index in range(len(paragraph_text)))
    return "".join(text_parts), offsets


def _slices_from_offsets(
    offsets: list[tuple[int, int] | None],
    *,
    paragraphs: dict[int, str],
    resolution: str,
) -> list[dict[str, object]]:
    """Collapse raw offsets into one or more segment-source slices."""

    by_paragraph: dict[int, list[int]] = defaultdict(list)
    for offset in offsets:
        if offset is None:
            continue
        paragraph_index, char_offset = offset
        by_paragraph[int(paragraph_index)].append(int(char_offset))

    slices: list[dict[str, object]] = []
    for paragraph_index in sorted(by_paragraph):
        values = by_paragraph[paragraph_index]
        char_start = min(values)
        char_end = max(values) + 1
        paragraph_text = paragraphs.get(paragraph_index, "")
        slices.append(
            {
                "coordinate_system": "segment_source_v1",
                "paragraph_index": paragraph_index,
                "char_start": char_start,
                "char_end": char_end,
                "text": paragraph_text[char_start:char_end],
                "source_span_resolution": resolution,
            }
        )
    return slices


def _unique_raw_source_slices(
    *,
    paragraphs: dict[int, str],
    match_text: str,
) -> list[dict[str, object]] | None:
    """Return exact raw source slices only when the match is unique."""

    if not match_text:
        return None
    chapter_text, offsets = _chapter_text_with_offsets(paragraphs)
    hits: list[list[tuple[int, int] | None]] = []
    start = 0
    while True:
        index = chapter_text.find(match_text, start)
        if index < 0:
            break
        hits.append(offsets[index : index + len(match_text)])
        start = index + 1
    if len(hits) != 1:
        return None
    return _slices_from_offsets(hits[0], paragraphs=paragraphs, resolution="exact")


def _unique_normalized_source_slices(
    *,
    paragraphs: dict[int, str],
    match_text: str,
) -> list[dict[str, object]] | None:
    """Return normalized source slices only when the normalized match is unique."""

    if not match_text:
        return None
    chapter_text, offsets = _chapter_text_with_offsets(paragraphs)
    normalized_text, normalized_offsets = _normalize_with_offsets(chapter_text, list(offsets))
    normalized_match, _match_offsets = _normalize_with_offsets(match_text)
    if not normalized_match:
        return None

    hits: list[list[object]] = []
    start = 0
    while True:
        index = normalized_text.find(normalized_match, start)
        if index < 0:
            break
        hits.append(normalized_offsets[index : index + len(normalized_match)])
        start = index + 1
    if len(hits) != 1:
        return None
    typed_offsets = [offset if isinstance(offset, tuple) else None for offset in hits[0]]
    return _slices_from_offsets(typed_offsets, paragraphs=paragraphs, resolution="normalized")


def _segment_fallback_source_slices(
    *,
    segment_meta: dict[str, object],
    chapter_paragraphs: dict[int, str],
) -> list[dict[str, object]]:
    """Build broad source slices for one semantic segment when exact anchoring fails."""

    paragraph_locators = [
        item
        for item in segment_meta.get("paragraph_locators", [])
        if isinstance(item, dict)
    ]
    slices: list[dict[str, object]] = []
    for paragraph in paragraph_locators:
        paragraph_index = int(paragraph.get("paragraph_index", 0) or 0)
        text = str(paragraph.get("text", "") or "") or chapter_paragraphs.get(paragraph_index, "")
        if paragraph_index > 0 and text:
            slices.append(
                {
                    "coordinate_system": "segment_source_v1",
                    "paragraph_index": paragraph_index,
                    "char_start": 0,
                    "char_end": len(text),
                    "text": text,
                    "source_span_resolution": "segment_fallback",
                }
            )
    if slices:
        return slices

    locator = segment_meta.get("locator")
    if not isinstance(locator, dict):
        return []
    paragraph_start = int(locator.get("paragraph_start", 0) or 0)
    paragraph_end = int(locator.get("paragraph_end", 0) or 0)
    for paragraph_index in range(paragraph_start, paragraph_end + 1):
        text = chapter_paragraphs.get(paragraph_index, "")
        if text:
            slices.append(
                {
                    "coordinate_system": "segment_source_v1",
                    "paragraph_index": paragraph_index,
                    "char_start": 0,
                    "char_end": len(text),
                    "text": text,
                    "source_span_resolution": "segment_fallback",
                }
            )
    return slices


def _section_segment_meta(
    *,
    section: dict[str, object],
    section_index: int,
    segments: list[object],
) -> dict[str, object]:
    """Map one public section back to the same-order semantic segment metadata."""

    segment_ref = str(section.get("segment_ref", "") or "")
    suffix = segment_ref.rsplit(".", 1)[-1]
    if suffix.isdigit():
        index = int(suffix) - 1
        if 0 <= index < len(segments) and isinstance(segments[index], dict):
            return segments[index]
    if 0 <= section_index < len(segments) and isinstance(segments[section_index], dict):
        return segments[section_index]
    return {}


def _target_locator_with_source_span(
    *,
    target_locator: object,
    anchor_quote: str,
    chapter_paragraphs: dict[int, str],
    segment_meta: dict[str, object],
) -> dict[str, object] | None:
    """Attach eval-only segment-source slices to a reaction target locator."""

    locator = dict(target_locator) if isinstance(target_locator, dict) else {}
    if isinstance(locator.get("source_span_slices"), list):
        return locator

    match_text = str(locator.get("match_text", "") or anchor_quote or "").strip()
    source_slices = _unique_raw_source_slices(paragraphs=chapter_paragraphs, match_text=match_text)
    resolution = "exact"
    if source_slices is None:
        source_slices = _unique_normalized_source_slices(paragraphs=chapter_paragraphs, match_text=match_text)
        resolution = "normalized"
    if source_slices is None:
        source_slices = _segment_fallback_source_slices(
            segment_meta=segment_meta,
            chapter_paragraphs=chapter_paragraphs,
        )
        resolution = "segment_fallback"
    if not source_slices:
        return locator or None

    if not locator:
        locator = {
            "href": "",
            "start_cfi": None,
            "end_cfi": None,
            "match_text": match_text,
            "match_mode": resolution if resolution in {"exact", "normalized"} else "segment_fallback",
        }
    locator["source_span_coordinate_system"] = "segment_source_v1"
    locator["source_span_resolution"] = resolution
    locator["source_span_slices"] = source_slices
    return locator


def _normalized_run_snapshot(output_dir: Path) -> NormalizedRunSnapshot | None:
    """Build the normalized run snapshot when runtime artifacts exist."""

    path = existing_run_state_file(output_dir)
    if not path.exists():
        return None
    payload = load_json(path)
    return {
        "status": str(payload.get("stage", "")),
        "current_chapter_ref": str(payload.get("current_chapter_ref", "") or ""),
        "current_section_ref": str(payload.get("current_segment_ref", "") or ""),
        "current_reading_activity": payload.get("current_reading_activity"),
        "resume_available": bool(payload.get("resume_available")) if payload.get("resume_available") is not None else None,
        "last_checkpoint_at": payload.get("last_checkpoint_at"),
        "completed_chapters": int(payload.get("completed_chapters", 0) or 0),
        "total_chapters": int(payload.get("total_chapters", 0) or 0),
        "eta_seconds": int(payload.get("eta_seconds", 0) or 0) if payload.get("eta_seconds") is not None else None,
    }


def _normalized_attention_events(output_dir: Path) -> list[NormalizedAttentionEvent]:
    """Normalize activity history into cross-mechanism attention events."""

    events: list[NormalizedAttentionEvent] = []
    for raw in _load_jsonl(existing_activity_file(output_dir)):
        payload: NormalizedAttentionEvent = {
            "event_id": str(raw.get("event_id", "") or ""),
            "timestamp": str(raw.get("timestamp", "") or ""),
            "stream": str(raw.get("stream", "") or ""),
            "kind": str(raw.get("kind", "") or ""),
            "message": str(raw.get("message", "") or ""),
            "chapter_ref": str(raw.get("chapter_ref", "") or ""),
            "section_ref": str(raw.get("segment_ref", raw.get("section_ref", "")) or ""),
            "current_excerpt": str(raw.get("anchor_quote", raw.get("highlight_quote", "")) or ""),
            "search_query": str(raw.get("search_query", "") or ""),
            "thought_family": str(raw.get("thought_family", "") or ""),
            "problem_code": str(raw.get("problem_code", "") or ""),
        }
        phase = str(raw.get("phase", "") or "")
        if phase:
            payload["phase"] = phase  # type: ignore[typeddict-item]
        events.append(payload)
    return events


def _normalized_reactions(output_dir: Path, structure: dict[str, object]) -> list[NormalizedReaction]:
    """Normalize chapter result reactions into one cross-mechanism list."""

    document = load_book_document(existing_book_document_file(output_dir))
    paragraph_texts_by_chapter = _chapter_paragraph_texts(document)
    reactions: list[NormalizedReaction] = []
    for chapter in structure.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        result_path = existing_chapter_result_file(output_dir, chapter)
        if not result_path.exists():
            continue
        payload = load_json(result_path)
        chapter_id = int(chapter.get("id", 0) or 0)
        chapter_ref = str(payload.get("chapter", {}).get("reference", chapter.get("title", "")) or "")
        segments = list(chapter.get("segments", [])) if isinstance(chapter.get("segments", []), list) else []
        chapter_paragraphs = paragraph_texts_by_chapter.get(chapter_id, {})
        for section_index, section in enumerate(payload.get("sections", [])):
            if not isinstance(section, dict):
                continue
            section_ref = str(section.get("segment_ref", "") or "")
            segment_meta = _section_segment_meta(section=section, section_index=section_index, segments=segments)
            for reaction in section.get("reactions", []):
                if not isinstance(reaction, dict):
                    continue
                target_locator = _target_locator_with_source_span(
                    target_locator=reaction.get("target_locator"),
                    anchor_quote=str(reaction.get("anchor_quote", "") or ""),
                    chapter_paragraphs=chapter_paragraphs,
                    segment_meta=segment_meta,
                )
                reactions.append(
                    {
                        "reaction_id": str(reaction.get("reaction_id", "") or ""),
                        "type": str(reaction.get("type", "") or ""),
                        "chapter_ref": chapter_ref,
                        "section_ref": section_ref,
                        "anchor_quote": str(reaction.get("anchor_quote", "") or ""),
                        "content": str(reaction.get("content", "") or ""),
                        "search_query": str(reaction.get("search_query", "") or ""),
                        "search_results": list(reaction.get("search_results", [])),
                        "target_locator": target_locator,
                    }
                )
    return reactions


def _normalized_chapter_outputs(output_dir: Path, structure: dict[str, object]) -> list[NormalizedChapterOutput]:
    """Normalize per-chapter outputs into compact evaluation summaries."""

    chapters: list[NormalizedChapterOutput] = []
    for chapter in structure.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        result_path = existing_chapter_result_file(output_dir, chapter)
        payload = load_json(result_path) if result_path.exists() else {}
        chapter_payload = payload.get("chapter", {}) if isinstance(payload.get("chapter", {}), dict) else {}
        featured = payload.get("featured_reactions", []) if isinstance(payload.get("featured_reactions", []), list) else []
        ui_summary = payload.get("ui_summary", {}) if isinstance(payload.get("ui_summary", {}), dict) else {}
        chapter_reflection = payload.get("chapter_reflection", {}) if isinstance(payload.get("chapter_reflection", {}), dict) else {}
        chapters.append(
            {
                "chapter_id": int(chapter.get("id", 0) or 0),
                "chapter_ref": str(chapter_payload.get("reference", chapter.get("title", "")) or ""),
                "title": str(chapter.get("title", "") or ""),
                "status": str(chapter.get("status", "") or ""),
                "section_count": len(payload.get("sections", [])) if isinstance(payload.get("sections", []), list) else 0,
                "visible_reaction_count": int(ui_summary.get("kept_section_count", payload.get("visible_reaction_count", 0)) or 0),
                "featured_reaction_count": len(featured),
                "reflection_summary": str(chapter_reflection.get("summary", "") or ""),
            }
        )
    return chapters


def _memory_summaries(output_dir: Path) -> list[str]:
    """Extract lightweight memory summaries for normalized eval comparison."""

    path = existing_reader_memory_file(output_dir)
    if not path.exists():
        return []
    payload = load_json(path)
    summaries: list[str] = []
    book_arc = str(payload.get("book_arc_summary", "") or "").strip()
    if book_arc:
        summaries.append(book_arc)
    for item in payload.get("chapter_memory_summaries", []):
        if not isinstance(item, dict):
            continue
        summary = str(item.get("summary", "") or "").strip()
        if summary:
            summaries.append(summary)
    return summaries[:12]


def _normalized_eval_bundle(
    *,
    output_dir: Path,
    structure: dict[str, object],
    config_payload: dict[str, object],
) -> NormalizedEvalBundle:
    """Build the first normalized evaluation bundle for iterator_v1."""

    fingerprint = stable_config_fingerprint(config_payload)
    return {
        "mechanism_key": "iterator_v1",
        "mechanism_label": "Current Iterator-Reader implementation",
        "generated_at": _timestamp(),
        "output_dir": str(output_dir),
        "config_fingerprint": fingerprint,
        "run_snapshot": _normalized_run_snapshot(output_dir),
        "attention_events": _normalized_attention_events(output_dir),
        "reactions": _normalized_reactions(output_dir, structure),
        "chapters": _normalized_chapter_outputs(output_dir, structure),
        "memory_summaries": _memory_summaries(output_dir),
        "token_metadata": {},
        "latency_metadata": {},
        "cost_metadata": {},
    }

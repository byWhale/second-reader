"""Frontend-friendly artifact builders for sequential deep-read outputs."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .models import (
    ActivityEvent,
    BookManifest,
    BookStructure,
    ChapterResult,
    ChapterResultChapter,
    ChapterResultReaction,
    ChapterResultSection,
    ChapterResultUISummary,
    FeaturedReaction,
    MatchMode,
    ParagraphLocator,
    ReactionPayload,
    ReactionTargetLocator,
    RenderedSegment,
    RunStage,
    RunState,
    SegmentLocator,
    StructureChapter,
)
from .storage import (
    activity_file,
    append_jsonl,
    book_id_from_output_dir,
    book_manifest_file,
    chapter_output_name,
    chapter_reference,
    chapter_result_file,
    chapter_result_name,
    existing_cover_asset_file,
    relative_asset_path,
    run_state_file,
    save_json,
    source_asset_file,
)


HIGH_SIGNAL_TYPES = {"highlight", "curious", "discern", "connect_back"}
FEATURED_PRIORITY = {
    "highlight": 0,
    "discern": 1,
    "connect_back": 2,
    "curious": 3,
    "association": 4,
}


def _timestamp() -> str:
    """Return a stable UTC timestamp for persisted artifacts."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_text(text: str) -> str:
    """Collapse whitespace and punctuation variance for lightweight matching."""
    normalized = (text or "").replace("’", "'").replace("“", '"').replace("”", '"')
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip().lower()


def _reaction_id(
    book_id: str,
    chapter_id: int,
    segment_ref: str,
    reaction: ReactionPayload,
    index: int,
) -> str:
    """Create a stable reaction id from visible reaction content."""
    raw = "|".join(
        [
            book_id,
            str(chapter_id),
            segment_ref,
            str(index),
            str(reaction.get("type", "")),
            str(reaction.get("anchor_quote", "")),
            str(reaction.get("content", "")),
            str(reaction.get("search_query", "")),
        ]
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _event_id(payload: dict[str, object]) -> str:
    """Create a stable persisted id for one activity event payload."""
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _segment_fallback_locator(
    anchor_quote: str,
    locator: SegmentLocator | None,
) -> ReactionTargetLocator | None:
    """Build a fallback locator from the enclosing semantic segment."""
    if not locator:
        return None
    return {
        "href": str(locator.get("href", "")),
        "start_cfi": locator.get("start_cfi"),
        "end_cfi": locator.get("end_cfi"),
        "match_text": anchor_quote or "",
        "match_mode": "segment_fallback",
    }


def _paragraph_match_locator(
    anchor_quote: str,
    paragraph_locators: list[ParagraphLocator],
) -> tuple[ReactionTargetLocator | None, MatchMode | None]:
    """Match an anchor quote against paragraph-level locators."""
    quote = (anchor_quote or "").strip()
    if not quote:
        return None, None

    normalized_quote = _normalize_text(quote)
    for paragraph in paragraph_locators:
        text = str(paragraph.get("text", "")).strip()
        if quote and quote in text:
            return (
                {
                    "href": str(paragraph.get("href", "")),
                    "start_cfi": paragraph.get("start_cfi"),
                    "end_cfi": paragraph.get("end_cfi"),
                    "match_text": quote,
                    "match_mode": "exact",
                },
                "exact",
            )

    for paragraph in paragraph_locators:
        text = str(paragraph.get("text", "")).strip()
        if normalized_quote and normalized_quote in _normalize_text(text):
            return (
                {
                    "href": str(paragraph.get("href", "")),
                    "start_cfi": paragraph.get("start_cfi"),
                    "end_cfi": paragraph.get("end_cfi"),
                    "match_text": quote,
                    "match_mode": "normalized",
                },
                "normalized",
            )

    return None, None


def _reaction_target_locator(
    anchor_quote: str,
    locator: SegmentLocator | None,
    paragraph_locators: list[ParagraphLocator],
) -> ReactionTargetLocator | None:
    """Resolve the most precise available target locator for one reaction."""
    matched, _mode = _paragraph_match_locator(anchor_quote, paragraph_locators)
    if matched:
        return matched
    return _segment_fallback_locator(anchor_quote, locator)


def _chapter_metrics_from_result(result_path: Path) -> dict[str, int]:
    """Load chapter-level heatmap metrics from a companion JSON file."""
    if not result_path.exists():
        return {
            "visible_reaction_count": 0,
            "reaction_type_diversity": 0,
            "high_signal_reaction_count": 0,
        }

    payload = json.loads(result_path.read_text(encoding="utf-8"))
    return {
        "visible_reaction_count": int(payload.get("visible_reaction_count", 0)),
        "reaction_type_diversity": int(payload.get("reaction_type_diversity", 0)),
        "high_signal_reaction_count": int(payload.get("high_signal_reaction_count", 0)),
    }


def build_book_manifest(output_dir: Path, structure: BookStructure) -> BookManifest:
    """Construct a frontend-facing summary of one parsed book."""
    cover_asset = existing_cover_asset_file(output_dir)
    chapters = []
    for chapter in structure.get("chapters", []):
        metrics = _chapter_metrics_from_result(chapter_result_file(output_dir, chapter))
        entry = {
            "id": int(chapter.get("id", 0)),
            "title": str(chapter.get("title", "")),
            "reference": chapter_reference(chapter),
            "status": chapter.get("status", "pending"),
            "segment_count": len(chapter.get("segments", [])),
            "markdown_file": chapter.get("output_file", "") or chapter_output_name(chapter),
            "result_file": chapter_result_name(chapter),
            **metrics,
        }
        chapter_number = chapter.get("chapter_number")
        if chapter_number is not None:
            entry["chapter_number"] = int(chapter_number)
        chapters.append(entry)

    return {
        "book_id": book_id_from_output_dir(output_dir),
        "book": str(structure.get("book", "")),
        "author": str(structure.get("author", "")),
        "cover_image_url": relative_asset_path(output_dir, cover_asset) if cover_asset else None,
        "book_language": str(structure.get("book_language", "")),
        "output_language": str(structure.get("output_language", "")),
        "source_file": str(structure.get("source_file", "")),
        "source_asset": {
            "format": "epub",
            "file": str(source_asset_file(output_dir).relative_to(output_dir)),
        },
        "updated_at": _timestamp(),
        "chapters": chapters,
    }


def write_book_manifest(output_dir: Path, structure: BookStructure) -> BookManifest:
    """Persist book_manifest.json."""
    manifest = build_book_manifest(output_dir, structure)
    save_json(book_manifest_file(output_dir), manifest)
    return manifest


def build_run_state(
    structure: BookStructure,
    *,
    stage: RunStage,
    total_chapters: int,
    completed_chapters: int,
    current_chapter_id: int | None = None,
    current_chapter_ref: str | None = None,
    current_segment_ref: str | None = None,
    eta_seconds: int | None = None,
    error: str | None = None,
) -> RunState:
    """Construct one sequential run-state payload."""
    return {
        "mode": "sequential",
        "stage": stage,
        "book": str(structure.get("book", "")),
        "current_chapter_id": current_chapter_id,
        "current_chapter_ref": current_chapter_ref,
        "current_segment_ref": current_segment_ref,
        "completed_chapters": int(completed_chapters),
        "total_chapters": int(total_chapters),
        "eta_seconds": eta_seconds if eta_seconds is None else max(0, int(eta_seconds)),
        "updated_at": _timestamp(),
        "error": error,
    }


def write_run_state(output_dir: Path, payload: RunState) -> RunState:
    """Persist run_state.json."""
    stamped = dict(payload)
    stamped["updated_at"] = _timestamp()
    save_json(run_state_file(output_dir), stamped)
    return stamped  # type: ignore[return-value]


def reset_activity(output_dir: Path) -> None:
    """Start a fresh activity stream for one sequential run."""
    path = activity_file(output_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")


def append_activity_event(output_dir: Path, event: ActivityEvent) -> ActivityEvent:
    """Append one user-facing activity event."""
    payload = dict(event)
    payload["timestamp"] = _timestamp()
    payload["event_id"] = str(event.get("event_id") or _event_id(payload))
    append_jsonl(activity_file(output_dir), payload)
    return payload  # type: ignore[return-value]


def estimate_eta_seconds(
    completed_chapter_seconds: list[float],
    remaining_chapters: int,
    *,
    current_total_segments: int | None = None,
    current_completed_segments: int | None = None,
) -> int | None:
    """Estimate a coarse chapter-level ETA for sequential runs."""
    if not completed_chapter_seconds:
        return None

    average = sum(completed_chapter_seconds) / len(completed_chapter_seconds)
    eta = average * max(0, remaining_chapters)

    if (
        current_total_segments
        and current_total_segments > 0
        and current_completed_segments is not None
        and current_completed_segments < current_total_segments
    ):
        progress = max(0.0, min(1.0, current_completed_segments / current_total_segments))
        eta += average * max(0.0, 1.0 - progress)

    return max(0, int(round(eta)))


def _visible_reactions(reactions: list[ReactionPayload]) -> list[ReactionPayload]:
    """Filter reactions down to the stable frontend-facing subset."""
    return [
        reaction
        for reaction in reactions
        if reaction.get("type") != "silent"
    ]


def _featured_reactions(
    candidates: list[FeaturedReaction],
) -> list[FeaturedReaction]:
    """Select a small set of reactions for cards and teasers."""
    ordered = sorted(
        candidates,
        key=lambda item: (
            FEATURED_PRIORITY.get(str(item.get("type", "association")), 99),
            str(item.get("segment_ref", "")),
            str(item.get("reaction_id", "")),
        ),
    )
    return ordered[:3]


def build_chapter_result(
    output_dir: Path,
    chapter: StructureChapter,
    rendered_segments: list[RenderedSegment],
    chapter_reflection: dict[str, object] | None,
    output_language: str,
) -> ChapterResult:
    """Construct the stable JSON companion payload for one chapter."""
    book_id = book_id_from_output_dir(output_dir)
    segment_meta_by_id = {
        str(segment.get("id", "")): segment
        for segment in chapter.get("segments", [])
    }
    sections: list[ChapterResultSection] = []
    reaction_counts: Counter[str] = Counter()
    featured_candidates: list[FeaturedReaction] = []
    visible_reaction_count = 0
    high_signal_reaction_count = 0

    for rendered in rendered_segments:
        segment_id = str(rendered.get("segment_id", ""))
        segment_ref = str(rendered.get("segment_ref", "") or segment_id)
        segment_meta = segment_meta_by_id.get(segment_id, {})
        segment_locator = segment_meta.get("locator") if isinstance(segment_meta, dict) else None
        paragraph_locators = []
        if isinstance(segment_meta, dict):
            paragraph_locators = list(segment_meta.get("paragraph_locators", []))

        frontend_reactions: list[ChapterResultReaction] = []
        for index, reaction in enumerate(_visible_reactions(rendered.get("reactions", [])), start=1):
            reaction_type = str(reaction.get("type", "association"))
            reaction_counts[reaction_type] += 1
            visible_reaction_count += 1
            if reaction_type in HIGH_SIGNAL_TYPES:
                high_signal_reaction_count += 1

            reaction_id = _reaction_id(
                book_id,
                int(chapter.get("id", 0)),
                segment_ref,
                reaction,
                index,
            )
            target_locator = _reaction_target_locator(
                str(reaction.get("anchor_quote", "")),
                segment_locator if isinstance(segment_locator, dict) else None,
                [item for item in paragraph_locators if isinstance(item, dict)],
            )
            frontend_reaction: ChapterResultReaction = {
                "reaction_id": reaction_id,
                "type": reaction.get("type", "association"),
                "anchor_quote": reaction.get("anchor_quote", ""),
                "content": reaction.get("content", ""),
                "search_query": reaction.get("search_query", ""),
                "search_results": list(reaction.get("search_results", [])),
            }
            if target_locator:
                frontend_reaction["target_locator"] = target_locator
            frontend_reactions.append(frontend_reaction)
            featured_candidates.append(
                {
                    "reaction_id": reaction_id,
                    "type": reaction.get("type", "association"),
                    "segment_ref": segment_ref,
                    "anchor_quote": reaction.get("anchor_quote", ""),
                    "content": reaction.get("content", ""),
                    "target_locator": target_locator or {},
                }
            )

        section: ChapterResultSection = {
            "segment_id": segment_id,
            "segment_ref": segment_ref,
            "summary": str(rendered.get("summary", "")),
            "original_text": str(segment_meta.get("text", "")) if isinstance(segment_meta, dict) else "",
            "verdict": rendered.get("verdict", "skip"),
            "quality_status": rendered.get("quality_status", "skipped"),
            "reflection_summary": str(rendered.get("reflection_summary", "")),
            "reflection_reason_codes": list(rendered.get("reflection_reason_codes", [])),
            "reactions": frontend_reactions,
        }
        if isinstance(segment_locator, dict):
            section["locator"] = {
                "href": str(segment_locator.get("href", "")),
                "start_cfi": segment_locator.get("start_cfi"),
                "end_cfi": segment_locator.get("end_cfi"),
                "paragraph_start": int(segment_locator.get("paragraph_start", 0) or 0),
                "paragraph_end": int(segment_locator.get("paragraph_end", 0) or 0),
            }
        skip_reason = rendered.get("skip_reason")
        if skip_reason:
            section["skip_reason"] = str(skip_reason)
        sections.append(section)

    chapter_payload: ChapterResultChapter = {
        "id": int(chapter.get("id", 0)),
        "title": str(chapter.get("title", "")),
        "reference": chapter_reference(chapter),
        "status": chapter.get("status", "pending"),
    }
    chapter_number = chapter.get("chapter_number")
    if chapter_number is not None:
        chapter_payload["chapter_number"] = int(chapter_number)

    featured = _featured_reactions(featured_candidates)
    ui_summary: ChapterResultUISummary = {
        "kept_section_count": sum(1 for section in sections if section.get("verdict") != "skip"),
        "skipped_section_count": sum(1 for section in sections if section.get("verdict") == "skip"),
        "reaction_counts": dict(sorted(reaction_counts.items())),
    }

    return {
        "chapter": chapter_payload,
        "output_language": output_language,
        "generated_at": _timestamp(),
        "sections": sections,
        "chapter_reflection": dict(chapter_reflection or {}),
        "featured_reactions": featured,
        "visible_reaction_count": visible_reaction_count,
        "reaction_type_diversity": len(reaction_counts),
        "high_signal_reaction_count": high_signal_reaction_count,
        "ui_summary": ui_summary,
    }


def write_chapter_result(
    output_dir: Path,
    chapter: StructureChapter,
    rendered_segments: list[RenderedSegment],
    chapter_reflection: dict[str, object] | None,
    output_language: str,
) -> ChapterResult:
    """Persist one chapter companion JSON file."""
    payload = build_chapter_result(
        output_dir=output_dir,
        chapter=chapter,
        rendered_segments=rendered_segments,
        chapter_reflection=chapter_reflection,
        output_language=output_language,
    )
    save_json(chapter_result_file(output_dir, chapter), payload)
    return payload

"""Adapter that exposes the current Iterator-Reader as one pluggable mechanism."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.iterator_reader.iterator import read_book as iterator_read_book
from src.iterator_reader.parse import parse_book as iterator_parse_book
from src.iterator_reader.storage import (
    existing_activity_file,
    existing_book_manifest_file,
    existing_chapter_result_file,
    existing_reader_memory_file,
    existing_run_state_file,
    load_json,
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

    reactions: list[NormalizedReaction] = []
    for chapter in structure.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        result_path = existing_chapter_result_file(output_dir, chapter)
        if not result_path.exists():
            continue
        payload = load_json(result_path)
        chapter_ref = str(payload.get("chapter", {}).get("reference", chapter.get("title", "")) or "")
        for section in payload.get("sections", []):
            if not isinstance(section, dict):
                continue
            section_ref = str(section.get("segment_ref", "") or "")
            for reaction in section.get("reactions", []):
                if not isinstance(reaction, dict):
                    continue
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

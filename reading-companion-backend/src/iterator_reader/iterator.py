"""Outer Iterator runtime for the Iterator-Reader architecture."""

from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from contextlib import nullcontext
from dataclasses import dataclass
import os
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from src.config import (
    get_backend_version,
    get_reader_resume_compat_version,
)
from src.reading_runtime.job_concurrency import resolve_runtime_tuning_defaults
from src.reading_runtime.llm_registry import DEFAULT_RUNTIME_PROFILE_ID
from .frontend_artifacts import (
    append_activity_event,
    append_deduped_activity_event,
    build_run_state,
    estimate_eta_seconds,
    write_book_manifest,
    write_chapter_qa_artifact,
    write_chapter_result,
    write_run_state,
)
from .llm_utils import llm_invocation_scope, runtime_trace_context
from .markdown import render_chapter_markdown
from .language import runtime_label
from .models import (
    BookAnalysisPolicy,
    BookStructure,
    BudgetPolicy,
    CurrentReadingProblemCode,
    CurrentReadingActivity,
    ReaderMemory,
    ReaderProgressEvent,
    ReadMode,
    RunStage,
    SkillProfileName,
    StructureChapter,
)
from .parse import ensure_structure_for_book
from .parse import chapter_contexts_for_book, segment_context_into_chapter, write_parse_progress
from .policy import (
    chapter_budget,
    default_book_analysis_policy,
    default_budget_policy,
    resolve_skill_policy,
    segment_budget,
)
from .book_analysis import run_book_analysis
from .prompts import ITERATOR_V1_PROMPTS, IteratorV1PromptSet
from .reader import (
    apply_chapter_reflection_repairs,
    coerce_reader_memory,
    consolidate_memory_after_chapter,
    create_reader_state,
    initial_memory,
    run_chapter_reflection,
    run_reader_segment,
    update_memory,
)
from src.prompts.capabilities.book_analysis import BOOK_ANALYSIS_PROMPTS, BookAnalysisPromptSet
from .storage import (
    chapter_markdown_file,
    chapter_reference,
    chapter_result_name,
    existing_chapter_result_file,
    existing_reader_memory_file,
    existing_segment_checkpoint_file,
    load_json,
    reader_memory_file,
    relative_output_path,
    save_structure,
    save_json,
    segment_reference,
    segment_checkpoint_file,
    structure_file,
)


@dataclass(frozen=True)
class SequentialPipelineTuning:
    """Background segmentation tuning defaults for the sequential pipeline."""

    segment_workers: int
    segment_workers_when_reader_blocked: int
    prefetch_window: int


def _default_pipeline_tuning() -> SequentialPipelineTuning:
    """Resolve the default runtime tuning from config."""
    default_segment_workers, default_blocked_workers, default_prefetch_window = resolve_runtime_tuning_defaults()
    raw_segment_workers = os.getenv("PIPELINE_SEGMENT_WORKERS", "").strip()
    raw_blocked_workers = os.getenv("PIPELINE_SEGMENT_WORKERS_WHEN_READER_BLOCKED", "").strip()
    raw_prefetch_window = os.getenv("PIPELINE_PREFETCH_WINDOW", "").strip()

    segment_workers = max(1, int(raw_segment_workers)) if raw_segment_workers.isdigit() else default_segment_workers
    blocked_workers = (
        max(segment_workers, int(raw_blocked_workers))
        if raw_blocked_workers.isdigit()
        else max(segment_workers, default_blocked_workers)
    )
    prefetch_window = max(1, int(raw_prefetch_window)) if raw_prefetch_window.isdigit() else default_prefetch_window
    return SequentialPipelineTuning(
        segment_workers=segment_workers,
        segment_workers_when_reader_blocked=blocked_workers,
        prefetch_window=max(1, prefetch_window),
    )


def _timestamp() -> str:
    """Return a stable UTC timestamp for runtime checkpoints."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


_CURRENT_READING_PROBLEM_CODES: set[str] = {
    "llm_timeout",
    "llm_quota",
    "llm_auth",
    "search_timeout",
    "search_quota",
    "search_auth",
    "network_blocked",
}
_PROBLEM_EVENT_TYPES = {
    "llm_timeout": "llm_timeout_detected",
    "search_timeout": "search_timeout_detected",
}
_READING_ACTIVITY_HEARTBEAT_SECONDS = 2.0


def _activity_excerpt(text: str | None) -> str | None:
    """Return normalized live excerpt text for the current reading activity."""
    normalized = re.sub(r"\s+", " ", str(text or "")).strip()
    if not normalized:
        return None
    return normalized


def _normalize_current_reading_problem_code(value: object) -> CurrentReadingProblemCode | None:
    """Return one stable runtime problem code when recognized."""
    normalized = re.sub(r"\s+", "_", str(value or "")).strip().lower()
    if normalized in _CURRENT_READING_PROBLEM_CODES:
        return normalized  # type: ignore[return-value]
    return None


def _resume_compat_matches(payload: object) -> bool:
    """Return whether one persisted payload is compatible with the current reader runtime."""
    if not isinstance(payload, dict):
        return False
    raw_version = payload.get("resume_compat_version")
    if raw_version is None:
        return False
    if isinstance(raw_version, str) and not raw_version.strip():
        return False
    try:
        normalized = int(raw_version)
    except (TypeError, ValueError):
        return False
    return normalized == get_reader_resume_compat_version()


def _build_current_reading_activity(
    *,
    phase: str,
    segment_ref: str | None = None,
    current_excerpt: str | None = None,
    search_query: str | None = None,
    thought_family: str | None = None,
    started_at: str | None = None,
    updated_at: str | None = None,
    problem_code: str | None = None,
) -> CurrentReadingActivity:
    """Construct one ephemeral reading-activity snapshot."""
    now = updated_at or _timestamp()
    payload: CurrentReadingActivity = {
        "phase": phase,  # type: ignore[typeddict-item]
        "started_at": started_at or now,
        "updated_at": now,
    }
    normalized_segment_ref = str(segment_ref or "").strip()
    normalized_excerpt = _activity_excerpt(current_excerpt)
    normalized_query = re.sub(r"\s+", " ", str(search_query or "")).strip()
    normalized_family = str(thought_family or "").strip().lower()
    normalized_problem_code = _normalize_current_reading_problem_code(problem_code)

    if normalized_segment_ref:
        payload["segment_ref"] = normalized_segment_ref
    if normalized_excerpt:
        payload["current_excerpt"] = normalized_excerpt
    if normalized_query:
        payload["search_query"] = normalized_query
    if normalized_family in {"highlight", "association", "curious", "discern", "retrospect"}:
        payload["thought_family"] = normalized_family  # type: ignore[typeddict-item]
    if normalized_problem_code:
        payload["problem_code"] = normalized_problem_code
    return payload


def _update_current_reading_activity(
    tracker: dict[str, object],
    *,
    phase: str,
    segment_ref: str | None = None,
    current_excerpt: str | None = None,
    search_query: str | None = None,
    thought_family: str | None = None,
    problem_code: str | None = None,
) -> bool:
    """Update the live reading activity while preserving phase start time."""
    current_activity = tracker.get("current_reading_activity")
    previous_started_at = (
        str(current_activity.get("started_at", "") or "").strip()
        if isinstance(current_activity, dict)
        else ""
    ) or None
    now = _timestamp()
    next_activity = _build_current_reading_activity(
        phase=phase,
        segment_ref=segment_ref,
        current_excerpt=current_excerpt,
        search_query=search_query,
        thought_family=thought_family,
        started_at=previous_started_at,
        updated_at=now,
        problem_code=problem_code,
    )
    comparable_keys = ("phase", "segment_ref", "current_excerpt", "search_query", "thought_family")
    if isinstance(current_activity, dict) and all(
        str(current_activity.get(key, "") or "") == str(next_activity.get(key, "") or "")
        for key in comparable_keys
    ):
        tracker["current_reading_activity"] = next_activity
        return True
    next_activity["started_at"] = now
    tracker["current_reading_activity"] = next_activity
    return True


def _touch_current_reading_activity(tracker: dict[str, object]) -> bool:
    """Refresh the heartbeat timestamp for the current reading activity."""
    current_activity = tracker.get("current_reading_activity")
    if not isinstance(current_activity, dict):
        return False
    current_activity["updated_at"] = _timestamp()
    tracker["current_reading_activity"] = current_activity
    return True


def _clear_current_reading_activity(tracker: dict[str, object]) -> bool:
    """Clear the ephemeral reading activity when the run leaves an active thought."""
    if tracker.get("current_reading_activity") is None:
        return False
    tracker["current_reading_activity"] = None
    return True


class _ReadingActivityHeartbeat:
    """Persist lightweight activity heartbeats while deep reading remains active."""

    def __init__(
        self,
        *,
        structure: BookStructure,
        output_dir: Path,
        tracker: dict[str, object],
        io_lock: threading.RLock,
        interval_seconds: float = _READING_ACTIVITY_HEARTBEAT_SECONDS,
    ) -> None:
        self._structure = structure
        self._output_dir = output_dir
        self._tracker = tracker
        self._io_lock = io_lock
        self._interval_seconds = max(0.5, interval_seconds)
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._run,
            name="reading-activity-heartbeat",
            daemon=True,
        )

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=self._interval_seconds * 2)

    def _run(self) -> None:
        try:
            while not self._stop.wait(self._interval_seconds):
                with self._io_lock:
                    stage = str(self._tracker.get("_run_state_stage", "") or "").strip()
                    if stage not in {"parsing_structure", "deep_reading", "ready"}:
                        continue
                    if not _touch_current_reading_activity(self._tracker):
                        continue
                    _write_sequential_run_state(
                        self._structure,
                        self._output_dir,
                        self._tracker,
                        stage=stage,  # type: ignore[arg-type]
                        current_phase_step=(
                            str(self._tracker.get("_run_state_current_phase_step", "") or "").strip() or None
                        ),
                        error=(str(self._tracker.get("_run_state_error", "") or "").strip() or None),
                    )
        except Exception as exc:  # pragma: no cover - defensive runtime path
            self._tracker["_heartbeat_failed_at"] = _timestamp()
            self._tracker["_heartbeat_failure_message"] = str(exc)
            append_deduped_activity_event(
                self._output_dir,
                {
                    "type": "heartbeat_lost",
                    "message": (
                        "Live heartbeat stopped while reading "
                        f"{str(self._tracker.get('current_segment_ref', '') or self._tracker.get('current_chapter_ref', '') or 'the current section')}."
                    ),
                    "chapter_id": int(self._tracker.get("current_chapter_id", 0) or 0) or None,
                    "chapter_ref": str(self._tracker.get("current_chapter_ref", "") or "") or None,
                    "segment_ref": str(self._tracker.get("current_segment_ref", "") or "") or None,
                    "details": {
                        "reason": str(exc),
                    },
                },
            )


def _chapter_lookup_number(chapter: StructureChapter) -> int | None:
    """Return the number users naturally expect for --chapter."""
    return chapter.get("chapter_number")


def _chapter_selection(
    structure: BookStructure,
    chapter_number: int | None,
    continue_mode: bool,
) -> list[StructureChapter]:
    chapters = structure.get("chapters", [])
    if chapter_number is not None:
        selected = [
            chapter
            for chapter in chapters
            if _chapter_lookup_number(chapter) == chapter_number
        ]
        if not selected:
            selected = [chapter for chapter in chapters if chapter.get("id") == chapter_number]
        if not selected:
            available = ", ".join(chapter_reference(chapter) for chapter in chapters)
            raise ValueError(f"Chapter {chapter_number} not found. Available chapters: {available}")
    else:
        selected = list(chapters)

    if continue_mode:
        selected = [chapter for chapter in selected if chapter.get("status") != "done"]
    return selected


def _coerce_reader_progress_event(progress: ReaderProgressEvent | str) -> ReaderProgressEvent:
    """Normalize progress payloads so legacy string callbacks still work."""
    if isinstance(progress, dict):
        normalized: ReaderProgressEvent = {
            "message": str(progress.get("message", "") or ""),
            "kind": str(progress.get("kind", "") or "transition"),  # type: ignore[typeddict-item]
            "visibility": str(progress.get("visibility", "") or "default"),  # type: ignore[typeddict-item]
        }
        search_query = str(progress.get("search_query", "") or "").strip()
        if search_query:
            normalized["search_query"] = search_query
        phase = str(progress.get("phase", "") or "").strip().lower()
        if phase in {"reading", "thinking", "searching", "fusing", "reflecting", "waiting", "preparing"}:
            normalized["phase"] = phase  # type: ignore[typeddict-item]
        current_excerpt = _activity_excerpt(str(progress.get("current_excerpt", "") or ""))
        if current_excerpt:
            normalized["current_excerpt"] = current_excerpt
        thought_family = str(progress.get("thought_family", "") or "").strip().lower()
        if thought_family in {"highlight", "association", "curious", "discern", "retrospect"}:
            normalized["thought_family"] = thought_family  # type: ignore[typeddict-item]
        problem_code = _normalize_current_reading_problem_code(progress.get("problem_code", ""))
        if problem_code:
            normalized["problem_code"] = problem_code
        return normalized
    text = str(progress or "")
    if text.startswith("📖"):
        return {"message": text, "kind": "position", "visibility": "default"}
    if text.startswith(("🔎", "🔍")):
        return {"message": text, "kind": "search", "visibility": "default"}
    if text.startswith(("🔗", "⚡", "💡", "✍️")):
        return {"message": text, "kind": "thought", "visibility": "default"}
    if text.startswith("🤫"):
        return {"message": text, "kind": "transition", "visibility": "collapsed"}
    return {"message": text, "kind": "transition", "visibility": "hidden"}


def _segment_progress(segment_id: str) -> Callable[[ReaderProgressEvent | str], None]:
    """Create a CLI printer for one segment."""
    def emit(progress: ReaderProgressEvent | str) -> None:
        normalized = _coerce_reader_progress_event(progress)
        message = str(normalized.get("message", "") or "").strip()
        if message:
            print(f"  ├─ {message}", flush=True)

    return emit


def _visible_segment_ref(chapter: StructureChapter, segment: dict[str, object]) -> str:
    """Resolve visible segment ref from segment metadata with fallback conversion."""
    ref = str(segment.get("segment_ref", "") or "").strip()
    if ref:
        return ref
    return segment_reference(chapter, str(segment.get("id", "") or segment.get("segment_id", "")))


def _normalize_memory_refs(structure: BookStructure, memory: ReaderMemory) -> ReaderMemory:
    """Rewrite summary prefixes from internal ids to visible refs when possible."""
    normalized = coerce_reader_memory(memory)
    chapters_by_id = {
        int(chapter.get("id", 0)): chapter
        for chapter in structure.get("chapters", [])
    }

    pattern = re.compile(r"^\s*(\d+\.\d+)\s*:\s*(.*)$")
    for item in normalized.get("recent_segment_flow", []):
        segment_ref = str(item.get("segment_ref", "") or "").strip()
        if not segment_ref:
            continue
        match = pattern.match(f"{segment_ref}: {item.get('summary', '')}")
        if not match:
            continue
        raw_segment_id = match.group(1)
        chapter_prefix = raw_segment_id.split(".", 1)[0]
        if not chapter_prefix.isdigit():
            continue
        chapter = chapters_by_id.get(int(chapter_prefix))
        if chapter:
            item["segment_ref"] = segment_reference(chapter, raw_segment_id)
            item["chapter_ref"] = chapter_reference(chapter)

    for bucket in ("findings", "threads"):
        for item in normalized.get(bucket, []):
            if not isinstance(item, dict):
                continue
            raw_segment_ref = str(item.get("segment_ref", "") or "").strip()
            if "." not in raw_segment_ref:
                continue
            chapter_prefix = raw_segment_ref.split(".", 1)[0]
            if not chapter_prefix.isdigit():
                continue
            chapter = chapters_by_id.get(int(chapter_prefix))
            if not chapter:
                continue
            item["segment_ref"] = segment_reference(chapter, raw_segment_ref)
            if not str(item.get("chapter_ref", "") or "").strip():
                item["chapter_ref"] = chapter_reference(chapter)

    return coerce_reader_memory(normalized)


def _read_progress_event(segment_id: str, segment_text: str, segment_summary: str) -> ReaderProgressEvent:
    """Render the initial read-stage progress event."""
    summary = (segment_summary or "").strip()
    summary = summary[:18].rstrip() + ("..." if len(summary) > 18 else "")
    if summary:
        return {
            "message": f"📖 读到 {segment_id}「{summary}」...",
            "kind": "position",
            "visibility": "default",
            "phase": "reading",
            "current_excerpt": segment_text or segment_summary,
        }
    return {
        "message": f"📖 读到 {segment_id}...",
        "kind": "position",
        "visibility": "default",
        "phase": "reading",
        "current_excerpt": segment_text or segment_summary,
    }


def _segment_visible_reactions(rendered: dict[str, object]) -> list[dict[str, object]]:
    """Return non-silent reactions for frontend activity payloads."""
    visible: list[dict[str, object]] = []
    for reaction in rendered.get("reactions", []):
        if not isinstance(reaction, dict):
            continue
        if str(reaction.get("type", "")) == "silent":
            continue
        visible.append(reaction)
    return visible


def _event_reaction_preview(reaction: dict[str, object]) -> dict[str, object]:
    """Return one compact reaction payload for activity events."""
    return {
        "type": str(reaction.get("type", "") or "").strip(),
        "content": str(reaction.get("content", "") or "").strip(),
        "anchor_quote": str(reaction.get("anchor_quote", "") or "").strip(),
        "search_query": str(reaction.get("search_query", "") or "").strip(),
    }


def _reaction_group_key(reaction: dict[str, object], index: int) -> str:
    """Build one stable grouping key for sentence-level mindstream events."""
    anchor_quote = str(reaction.get("anchor_quote", "") or "").strip()
    if anchor_quote:
        return f"quote:{anchor_quote}"
    search_query = str(reaction.get("search_query", "") or "").strip()
    if search_query:
        return f"search:{search_query}"
    return f"reaction:{index}"


def _sentence_level_mindstream_events(
    rendered: dict[str, object],
    *,
    chapter_id: int,
    chapter_ref: str,
    segment_id: str,
    segment_ref: str,
) -> list[dict[str, object]]:
    """Convert one rendered segment into sentence-level reaction-group events."""
    visible = _segment_visible_reactions(rendered)
    grouped: dict[str, dict[str, object]] = {}
    ordered_keys: list[str] = []

    for index, reaction in enumerate(visible, start=1):
        key = _reaction_group_key(reaction, index)
        if key not in grouped:
            ordered_keys.append(key)
            grouped[key] = {
                "anchor_quote": str(reaction.get("anchor_quote", "") or "").strip(),
                "search_query": str(reaction.get("search_query", "") or "").strip(),
                "reaction_types": [],
                "visible_reactions": [],
            }
        bucket = grouped[key]
        reaction_type = str(reaction.get("type", "") or "").strip()
        if reaction_type and reaction_type not in bucket["reaction_types"]:
            bucket["reaction_types"].append(reaction_type)
        bucket["visible_reactions"].append(_event_reaction_preview(reaction))
        if not bucket["anchor_quote"]:
            bucket["anchor_quote"] = str(reaction.get("anchor_quote", "") or "").strip()
        if not bucket["search_query"]:
            bucket["search_query"] = str(reaction.get("search_query", "") or "").strip()

    events: list[dict[str, object]] = []
    for key in ordered_keys:
        bucket = grouped[key]
        visible_reactions = list(bucket.get("visible_reactions", []))
        if not visible_reactions:
            continue
        anchor_quote = str(bucket.get("anchor_quote", "") or "").strip()
        search_query = str(bucket.get("search_query", "") or "").strip()
        first_reaction = visible_reactions[0]
        fallback_message = anchor_quote or search_query or str(first_reaction.get("content", "") or "").strip()
        event_payload: dict[str, object] = {
            "type": "segment_completed",
            "message": fallback_message,
            "chapter_id": chapter_id,
            "chapter_ref": chapter_ref,
            "segment_id": segment_id,
            "segment_ref": segment_ref,
            "anchor_quote": anchor_quote,
            "reaction_types": list(bucket.get("reaction_types", [])),
            "visible_reactions": visible_reactions,
            "visible_reaction_count": len(visible_reactions),
        }
        if search_query:
            event_payload["search_query"] = search_query
        if anchor_quote:
            event_payload["highlight_quote"] = anchor_quote
        events.append(event_payload)
    return events


def _chapter_completed_message(output_language: str, chapter_ref: str, reaction_count: int) -> str:
    """Render the user-facing chapter completion line in the content language."""
    return runtime_label(output_language, "chapterCompleted", chapter=chapter_ref, count=reaction_count) or chapter_ref


def _write_sequential_run_state(
    structure: BookStructure,
    output_dir: Path,
    tracker: dict[str, object],
    *,
    stage: RunStage,
    current_phase_step: str | None = None,
    error: str | None = None,
) -> None:
    """Persist one coarse-grained run_state snapshot for sequential mode."""
    tracker["_run_state_stage"] = stage
    tracker["_run_state_current_phase_step"] = current_phase_step
    tracker["_run_state_error"] = error
    completed_chapter_seconds = list(tracker.get("chapter_seconds", []))
    total_chapters = int(tracker.get("total_chapters", 0))
    completed_chapters = int(tracker.get("completed_chapters", 0))
    current_chapter_id = tracker.get("current_chapter_id")
    current_chapter_ref = tracker.get("current_chapter_ref")
    current_segment_ref = tracker.get("current_segment_ref")
    current_reading_activity = tracker.get("current_reading_activity")
    last_checkpoint_at = tracker.get("last_checkpoint_at")
    eta_seconds: int | None

    if stage == "completed":
        eta_seconds = 0
        current_chapter_id = None
        current_chapter_ref = None
        current_segment_ref = None
        current_reading_activity = None
    elif stage == "ready":
        eta_seconds = None
    else:
        remaining_chapters = max(
            0,
            total_chapters - completed_chapters - (1 if current_chapter_id is not None else 0),
        )
        eta_seconds = estimate_eta_seconds(
            completed_chapter_seconds,
            remaining_chapters,
            current_total_segments=tracker.get("current_total_segments"),
            current_completed_segments=tracker.get("current_completed_segments"),
        )

    write_run_state(
        output_dir,
        build_run_state(
            structure,
            stage=stage,
            total_chapters=total_chapters,
            completed_chapters=completed_chapters,
            current_chapter_id=current_chapter_id if isinstance(current_chapter_id, int) else None,
            current_chapter_ref=str(current_chapter_ref) if current_chapter_ref else None,
            current_segment_ref=str(current_segment_ref) if current_segment_ref else None,
            current_reading_activity=current_reading_activity if isinstance(current_reading_activity, dict) else None,
            eta_seconds=eta_seconds,
            current_phase_step=current_phase_step,
            resume_available=bool(current_chapter_id is not None or completed_chapters > 0),
            last_checkpoint_at=str(last_checkpoint_at) if last_checkpoint_at else None,
            error=error,
        ),
    )


def _persist_reader_memory(output_dir: Path, memory: ReaderMemory) -> None:
    """Persist the canonical book-level reader memory snapshot."""
    save_json(
        reader_memory_file(output_dir),
        {
            "updated_at": _timestamp(),
            "backend_version": get_backend_version(),
            "resume_compat_version": get_reader_resume_compat_version(),
            "memory": coerce_reader_memory(memory),
        },
    )


def _chapter_position_context(
    structure: BookStructure,
    chapter: StructureChapter,
) -> tuple[int, int, list[str]]:
    """Return chapter index/total and a nearby outline slice for prompt context."""
    chapters = list(structure.get("chapters", []))
    total = len(chapters)
    chapter_id = int(chapter.get("id", 0))
    current_index = next(
        (index for index, item in enumerate(chapters) if int(item.get("id", 0)) == chapter_id),
        0,
    )
    nearby: list[str] = []
    for index in range(max(0, current_index - 2), min(total, current_index + 4)):
        if index == current_index:
            continue
        item = chapters[index]
        nearby.append(f"{chapter_reference(item)} — {item.get('title', '')}")
    return current_index + 1, total, nearby


def _rendered_segments_from_chapter_result(payload: dict[str, object]) -> list[dict[str, object]]:
    """Convert one chapter_result payload back into minimal rendered segments for memory backfill."""
    rendered_segments: list[dict[str, object]] = []
    for section in payload.get("sections", []):
        if not isinstance(section, dict):
            continue
        rendered_segments.append(
            {
                "segment_id": str(section.get("segment_id", "") or ""),
                "segment_ref": str(section.get("segment_ref", "") or ""),
                "summary": str(section.get("summary", "") or ""),
                "verdict": str(section.get("verdict", "skip") or "skip"),
                "reactions": list(section.get("reactions", [])),
                "reflection_summary": str(section.get("reflection_summary", "") or ""),
                "reflection_reason_codes": list(section.get("reflection_reason_codes", [])),
                "quality_status": str(section.get("quality_status", "") or ""),
            }
        )
    return rendered_segments


def _backfill_reader_memory_from_results(output_dir: Path, structure: BookStructure) -> ReaderMemory:
    """Rebuild a coarse book-level memory snapshot from completed chapter results."""
    memory = initial_memory()
    for chapter in structure.get("chapters", []):
        if str(chapter.get("status", "")) != "done":
            continue
        result_path = existing_chapter_result_file(output_dir, chapter)
        if not result_path.exists():
            continue
        payload = load_json(result_path)
        if not isinstance(payload, dict):
            continue
        memory = consolidate_memory_after_chapter(
            memory,
            chapter_ref=chapter_reference(chapter),
            chapter_title=str(chapter.get("title", "") or ""),
            primary_role=str(chapter.get("primary_role", "body") or "body"),
            rendered_segments=_rendered_segments_from_chapter_result(payload),
            chapter_reflection=payload.get("chapter_reflection") if isinstance(payload.get("chapter_reflection"), dict) else {},
        )
    return memory


def _load_reader_memory_snapshot(
    output_dir: Path,
    structure: BookStructure,
    *,
    continue_mode: bool,
) -> ReaderMemory:
    """Load the canonical reader memory snapshot or backfill it from chapter results."""
    if not continue_mode:
        return initial_memory()

    path = existing_reader_memory_file(output_dir)
    if path.exists():
        payload = load_json(path)
        if isinstance(payload, dict):
            if isinstance(payload.get("memory"), dict) and _resume_compat_matches(payload):
                return coerce_reader_memory(payload.get("memory"))
            if _resume_compat_matches(payload):
                return coerce_reader_memory(payload)

    backfilled = _backfill_reader_memory_from_results(output_dir, structure)
    if any(backfilled.get(key) for key in ["chapter_memory_summaries", "findings", "threads", "book_arc_summary"]):
        _persist_reader_memory(output_dir, backfilled)
    return backfilled


class BackgroundSegmentationCoordinator:
    """Schedule chapter-level semantic segmentation behind the sequential reader."""

    def __init__(
        self,
        *,
        structure: BookStructure,
        output_dir: Path,
        book_path: Path,
        selected_chapters: list[StructureChapter],
        tuning: SequentialPipelineTuning,
        io_lock: threading.RLock,
    ) -> None:
        self.structure = structure
        self.output_dir = output_dir
        self.book_path = book_path
        self.selected_chapters = selected_chapters
        self.tuning = tuning
        self.io_lock = io_lock
        self.condition = threading.Condition(io_lock)
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run_loop, name=f"segmenter-{output_dir.name}", daemon=True)
        self.chapter_by_id = {
            int(chapter.get("id", 0)): chapter
            for chapter in selected_chapters
        }
        self.segmented_ids = {
            int(chapter.get("id", 0))
            for chapter in selected_chapters
            if chapter.get("segments")
        }
        self.context_by_id: dict[int, dict[str, object]] = {}
        if len(self.segmented_ids) < len(self.selected_chapters):
            contexts = chapter_contexts_for_book(
                book_path,
                output_language=str(structure.get("output_language", "en")),
            )
            self.context_by_id = {
                int(context.get("id", 0)): context
                for context in contexts
                if int(context.get("id", 0)) in self.chapter_by_id
            }
        self.inflight_ids: set[int] = set()
        self.next_unread_index = 0
        self.reader_started = False
        self.reader_waiting = False
        self.waiting_chapter_id: int | None = None
        self.last_checkpoint_at: str | None = _timestamp() if self.segmented_ids else None
        self.error: Exception | None = None

    def start(self) -> None:
        """Start the background scheduler when segmentation work remains."""
        with self.condition:
            if not self._remaining_unsegmented_ids_locked():
                self._persist_parse_state_locked(status_override="ready")
                return
            self._persist_parse_state_locked()
        self.thread.start()

    def stop(self) -> None:
        """Stop the background scheduler and wait for the thread to exit."""
        self.stop_event.set()
        with self.condition:
            self.condition.notify_all()
        if self.thread.is_alive():
            self.thread.join(timeout=1.0)

    def raise_if_failed(self) -> None:
        """Raise the first stored segmentation failure."""
        if self.error is not None:
            raise RuntimeError(str(self.error)) from self.error

    def note_reader_started(self, *, next_unread_index: int) -> None:
        """Mark that the foreground reader has begun and advance the prefetch horizon."""
        with self.condition:
            self.reader_started = True
            self.reader_waiting = False
            self.waiting_chapter_id = None
            self.next_unread_index = max(0, next_unread_index)
            self.condition.notify_all()

    def set_reader_waiting(self, chapter_id: int | None) -> None:
        """Mark whether the reader is blocked waiting for segmentation."""
        with self.condition:
            self.reader_waiting = chapter_id is not None
            self.waiting_chapter_id = chapter_id
            self.condition.notify_all()

    def wait_until_segmented(self, chapter_id: int) -> None:
        """Block until one chapter has semantic segments or a failure occurs."""
        with self.condition:
            while chapter_id not in self.segmented_ids and self.error is None:
                self.condition.wait(timeout=0.25)
            self.raise_if_failed()

    def _remaining_unsegmented_ids_locked(self) -> list[int]:
        return [
            int(chapter.get("id", 0))
            for chapter in self.selected_chapters
            if int(chapter.get("id", 0)) not in self.segmented_ids
        ]

    def _candidate_ids_locked(self) -> list[int]:
        candidates: list[int] = []
        tail = self.selected_chapters[self.next_unread_index :]
        for chapter in tail:
            chapter_id = int(chapter.get("id", 0))
            if chapter_id in self.segmented_ids or chapter_id in self.inflight_ids:
                continue
            candidates.append(chapter_id)
            if len(candidates) >= self.tuning.prefetch_window:
                break
        return candidates

    def _current_worker_limit_locked(self) -> int:
        if self.reader_waiting or not self.reader_started:
            return self.tuning.segment_workers_when_reader_blocked
        return self.tuning.segment_workers

    def _persist_parse_state_locked(self, *, status_override: str | None = None, error: str | None = None) -> None:
        pending_ids = self._remaining_unsegmented_ids_locked()
        inflight_ids = sorted(self.inflight_ids)
        status = status_override or ("ready" if not pending_ids and not inflight_ids else "parsing_structure")
        current_id = inflight_ids[0] if inflight_ids else (self.waiting_chapter_id or (pending_ids[0] if pending_ids else None))
        current_chapter = self.chapter_by_id.get(current_id) if current_id is not None else None
        current_step = None
        if status != "ready":
            current_step = "等待当前章节切分完成" if self.reader_waiting else ("后台准备后续章节" if self.reader_started else "为首章准备语义结构")
        write_parse_progress(
            self.structure,
            self.output_dir,
            status=status,  # type: ignore[arg-type]
            total_chapters=len(self.selected_chapters),
            completed_chapters=len(self.segmented_ids),
            parsed_chapter_ids=sorted(self.segmented_ids),
            inflight_chapter_ids=inflight_ids,
            pending_chapter_ids=pending_ids,
            current_chapter_id=current_id,
            current_chapter_ref=chapter_reference(current_chapter) if current_chapter is not None else None,
            current_step=current_step,
            worker_limit=self._current_worker_limit_locked() if status != "ready" else None,
            last_checkpoint_at=self.last_checkpoint_at,
            error=error,
            sync_run_state=False,
        )

    def _update_segmented_chapter_locked(self, chapter_id: int, chapter_record: StructureChapter) -> None:
        target = self.chapter_by_id[chapter_id]
        previous_status = str(target.get("status", "pending") or "pending")
        previous_output_file = str(target.get("output_file", "") or "")
        target.clear()
        target.update(chapter_record)
        if previous_status in {"in_progress", "done"}:
            target["status"] = previous_status
        if previous_output_file and not str(target.get("output_file", "")).strip():
            target["output_file"] = previous_output_file
        self.segmented_ids.add(chapter_id)
        self.last_checkpoint_at = _timestamp()
        save_structure(structure_file(self.output_dir), self.structure)
        write_book_manifest(self.output_dir, self.structure)

    def _record_segmentation_error_locked(self, chapter_id: int | None, exc: Exception) -> None:
        self.error = exc
        self._persist_parse_state_locked(status_override="error", error=str(exc))
        chapter = self.chapter_by_id.get(chapter_id) if chapter_id is not None else None
        append_activity_event(
            self.output_dir,
            {
                "type": "error",
                "message": (
                    f"{chapter_reference(chapter)} 语义切分中断：{exc}"
                    if chapter is not None
                    else f"语义切分中断：{exc}"
                ),
                "chapter_id": int(chapter.get("id", 0)) if chapter is not None else None,
                "chapter_ref": chapter_reference(chapter) if chapter is not None else None,
            },
        )

    def _run_loop(self) -> None:
        executor = ThreadPoolExecutor(max_workers=self.tuning.segment_workers_when_reader_blocked, thread_name_prefix="segment")
        futures: dict[Future[StructureChapter], int] = {}
        try:
            while True:
                with self.condition:
                    if self.error is not None:
                        self.condition.notify_all()
                        return

                    worker_limit = self._current_worker_limit_locked()
                    candidates = self._candidate_ids_locked()
                    while len(futures) < worker_limit and candidates:
                        chapter_id = candidates.pop(0)
                        context = self.context_by_id.get(chapter_id)
                        if context is None:
                            self._record_segmentation_error_locked(chapter_id, RuntimeError(f"Missing context for chapter {chapter_id}"))
                            self.condition.notify_all()
                            return
                        self.inflight_ids.add(chapter_id)
                        chapter = self.chapter_by_id[chapter_id]
                        print(f"[segment] {chapter_reference(chapter)}: {chapter.get('title', '')}", flush=True)
                        append_activity_event(
                            self.output_dir,
                            {
                                "type": "parse_chapter_started",
                                "message": f"开始解析 {chapter_reference(chapter)}：{chapter.get('title', '')}",
                                "chapter_id": chapter_id,
                                "chapter_ref": chapter_reference(chapter),
                            },
                        )
                        self._persist_parse_state_locked()
                        futures[
                            executor.submit(
                                segment_context_into_chapter,
                                self.output_dir,
                                context,
                                progress=lambda message, chapter_ref=chapter_reference(chapter): print(
                                    f"  ├─ [{chapter_ref}] {message}",
                                    flush=True,
                                ),
                            )
                        ] = chapter_id

                    if not futures:
                        if not self._remaining_unsegmented_ids_locked():
                            self._persist_parse_state_locked(status_override="ready")
                            self.condition.notify_all()
                            return
                        if self.stop_event.is_set():
                            return
                        self.condition.wait(timeout=0.25)
                        continue

                done, _pending = wait(list(futures.keys()), timeout=0.25, return_when=FIRST_COMPLETED)
                for future in done:
                    chapter_id = futures.pop(future)
                    try:
                        chapter_record = future.result()
                    except Exception as exc:
                        with self.condition:
                            self.inflight_ids.discard(chapter_id)
                            self._record_segmentation_error_locked(chapter_id, exc)
                            self.condition.notify_all()
                        return

                    with self.condition:
                        self.inflight_ids.discard(chapter_id)
                        self._update_segmented_chapter_locked(chapter_id, chapter_record)
                        chapter = self.chapter_by_id[chapter_id]
                        self._persist_parse_state_locked()
                        append_activity_event(
                            self.output_dir,
                            {
                                "type": "parse_chapter_completed",
                                "message": f"{chapter_reference(chapter)} 结构解析完成，生成 {len(chapter.get('segments', []))} 个 section。",
                                "chapter_id": chapter_id,
                                "chapter_ref": chapter_reference(chapter),
                            },
                        )
                        append_activity_event(
                            self.output_dir,
                            {
                                "type": "structure_checkpoint_saved",
                                "message": f"已保存解析 checkpoint：{chapter_reference(chapter)}",
                                "chapter_id": chapter_id,
                                "chapter_ref": chapter_reference(chapter),
                            },
                        )
                        print(
                            f"  └─ [{chapter_reference(chapter)}] 完成，生成 {len(chapter.get('segments', []))} 个 section",
                            flush=True,
                        )
                        self.condition.notify_all()
        finally:
            executor.shutdown(wait=False, cancel_futures=True)


def _run_single_chapter(
    structure: BookStructure,
    output_dir: Path,
    chapter: StructureChapter,
    memory: ReaderMemory,
    user_intent: str | None,
    index: int,
    total: int,
    skill_profile: SkillProfileName,
    budget_policy: BudgetPolicy,
    allow_resume: bool,
    tracker: dict[str, object],
    io_lock: threading.RLock | None = None,
    prompt_set: IteratorV1PromptSet = ITERATOR_V1_PROMPTS,
) -> ReaderMemory:
    """Execute one chapter and return updated memory."""
    write_context = io_lock if io_lock is not None else nullcontext()
    chapter["status"] = "in_progress"
    with write_context:
        save_structure(structure_file(output_dir), structure)
    print(f'[{index}/{total}] 正在深读 {chapter_reference(chapter)}: {chapter["title"]}', flush=True)
    tracker["current_total_segments"] = len(chapter.get("segments", []))
    tracker["current_completed_segments"] = 0

    rendered_segments = []
    skill_policy = resolve_skill_policy(skill_profile)
    chapter_budget_state = chapter_budget(budget_policy)
    checkpoint_path = existing_segment_checkpoint_file(output_dir, chapter)
    resumed_segment_map: dict[str, dict] = {}

    if allow_resume and checkpoint_path.exists():
        checkpoint_payload = load_json(checkpoint_path)
        if _resume_compat_matches(checkpoint_payload):
            for item in checkpoint_payload.get("rendered_segments", []):
                if not isinstance(item, dict):
                    continue
                segment_id = str(item.get("segment_id", "")).strip()
                if segment_id:
                    if not str(item.get("segment_ref", "")).strip():
                        item["segment_ref"] = segment_reference(chapter, segment_id)
                    resumed_segment_map[segment_id] = item
            stored_memory = checkpoint_payload.get("memory")
            if isinstance(stored_memory, dict):
                memory = _normalize_memory_refs(structure, coerce_reader_memory(stored_memory))
            stored_budget = checkpoint_payload.get("chapter_budget")
            if isinstance(stored_budget, dict):
                chapter_budget_state["search_queries_remaining_in_chapter"] = max(
                    0,
                    int(
                        stored_budget.get(
                            "search_queries_remaining_in_chapter",
                            chapter_budget_state.get("search_queries_remaining_in_chapter", 0),
                        )
                    ),
                )
            tracker["last_checkpoint_at"] = str(
                checkpoint_payload.get("last_checkpoint_at", "") or checkpoint_payload.get("checkpointed_at", "") or ""
            ) or None
            tracker["current_completed_segments"] = len(resumed_segment_map)
            with write_context:
                _write_sequential_run_state(structure, output_dir, tracker, stage="deep_reading")
            print(f"  ├─ 检测到段级 checkpoint，恢复 {len(resumed_segment_map)} 个语义单元", flush=True)
            pending_segments = [
                segment
                for segment in chapter.get("segments", [])
                if segment.get("id", "") not in resumed_segment_map
            ]
            if pending_segments:
                next_segment_id = _visible_segment_ref(chapter, pending_segments[0])
                print(f"  ├─ checkpoint 恢复后继续从 {next_segment_id} 开始处理", flush=True)
            else:
                print("  ├─ checkpoint 已覆盖本章全部语义单元，直接收尾输出", flush=True)
        else:
            checkpoint_path.unlink(missing_ok=True)
    elif checkpoint_path.exists():
        checkpoint_path.unlink(missing_ok=True)

    for segment in chapter.get("segments", []):
        segment_id = segment.get("id", "")
        if allow_resume and segment_id in resumed_segment_map:
            rendered = resumed_segment_map[segment_id]
            rendered_segments.append(rendered)
            segment["status"] = "skipped" if rendered.get("verdict") == "skip" else "done"
            continue

        shown_segment_id = _visible_segment_ref(chapter, segment)
        tracker["current_segment_ref"] = shown_segment_id
        tracker["current_completed_segments"] = len(rendered_segments)
        with write_context:
            _update_current_reading_activity(
                tracker,
                phase="reading",
                segment_ref=shown_segment_id,
                current_excerpt=str(segment.get("text", "") or segment.get("summary", "") or ""),
            )
            _write_sequential_run_state(structure, output_dir, tracker, stage="deep_reading")
        stdout_progress = _segment_progress(shown_segment_id)

        def progress(progress_event: ReaderProgressEvent | str) -> None:
            normalized = _coerce_reader_progress_event(progress_event)
            stdout_progress(normalized)
            phase = str(normalized.get("phase", "") or "").strip().lower()
            problem_code = _normalize_current_reading_problem_code(normalized.get("problem_code", ""))
            if problem_code:
                append_deduped_activity_event(
                    output_dir,
                    {
                        "type": _PROBLEM_EVENT_TYPES.get(problem_code, "runtime_stalled"),
                        "message": (
                            f"Reader detected {problem_code.replace('_', ' ')} while working on {shown_segment_id}."
                        ),
                        "chapter_id": int(chapter.get("id", 0) or 0) or None,
                        "chapter_ref": chapter_reference(chapter),
                        "segment_id": str(segment_id or "") or None,
                        "segment_ref": shown_segment_id,
                        "problem_code": problem_code,
                        "details": {
                            "phase": phase or None,
                            "source": "reader_progress",
                        },
                    },
                )
            if phase in {"reading", "thinking", "searching", "fusing", "reflecting", "waiting", "preparing"}:
                activity_changed = _update_current_reading_activity(
                    tracker,
                    phase=phase,
                    segment_ref=shown_segment_id,
                    current_excerpt=str(normalized.get("current_excerpt", "") or ""),
                    search_query=str(normalized.get("search_query", "") or ""),
                    thought_family=str(normalized.get("thought_family", "") or ""),
                    problem_code=str(problem_code or normalized.get("problem_code", "") or ""),
                )
                if activity_changed:
                    with write_context:
                        _write_sequential_run_state(structure, output_dir, tracker, stage="deep_reading")

        progress(_read_progress_event(shown_segment_id, str(segment.get("text", "") or ""), str(segment.get("summary", "") or "")))
        chapter_index, total_chapters, nearby_outline = _chapter_position_context(structure, chapter)
        state = create_reader_state(
            book_title=str(structure.get("book", "") or ""),
            author=str(structure.get("author", "") or ""),
            chapter_title=chapter.get("title", ""),
            chapter_ref=chapter_reference(chapter),
            chapter_index=chapter_index,
            total_chapters=total_chapters,
            segment_id=segment.get("id", ""),
            segment_ref=shown_segment_id,
            segment_summary=segment.get("summary", ""),
            segment_text=segment.get("text", ""),
            memory=memory,
            output_language=structure.get("output_language", "en"),
            user_intent=user_intent,
            skill_policy=skill_policy,
            budget=segment_budget(chapter_budget_state, budget_policy),
            max_revisions=int(budget_policy.get("max_revisions", 2)),
            primary_role=str(chapter.get("primary_role", "body") or "body"),
            role_tags=list(chapter.get("role_tags", [])),
            role_confidence=str(chapter.get("role_confidence", "low") or "low"),
            section_heading=str(segment.get("section_heading", "") or ""),
            nearby_outline=nearby_outline,
            prompt_set=prompt_set,
        )
        rendered, final_state = run_reader_segment(state, progress=progress)
        rendered_segments.append(rendered)
        memory = update_memory(
            memory,
            rendered,
            chapter_ref=chapter_reference(chapter),
            primary_role=str(chapter.get("primary_role", "body") or "body"),
            role_tags=list(chapter.get("role_tags", [])),
        )
        final_budget = final_state.get("budget") or {}
        chapter_budget_state["search_queries_remaining_in_chapter"] = max(
            0,
            int(
                final_budget.get(
                    "search_queries_remaining_in_chapter",
                    chapter_budget_state.get("search_queries_remaining_in_chapter", 0),
                )
            ),
        )
        segment["status"] = "skipped" if rendered.get("verdict") == "skip" else "done"
        with write_context:
            checkpointed_at = _timestamp()
            save_structure(structure_file(output_dir), structure)
            save_json(
                checkpoint_path,
                {
                    "backend_version": get_backend_version(),
                    "resume_compat_version": get_reader_resume_compat_version(),
                    "last_checkpoint_at": checkpointed_at,
                    "checkpointed_at": checkpointed_at,
                    "chapter_id": chapter.get("id", 0),
                    "chapter_title": chapter.get("title", ""),
                    "rendered_segments": rendered_segments,
                    "memory": memory,
                    "chapter_budget": chapter_budget_state,
                },
            )
            tracker["last_checkpoint_at"] = checkpointed_at
        tracker["current_completed_segments"] = len(rendered_segments)
        with write_context:
            _write_sequential_run_state(structure, output_dir, tracker, stage="deep_reading")
        visible_reactions = _segment_visible_reactions(rendered)
        if visible_reactions:
            with write_context:
                for activity_event in _sentence_level_mindstream_events(
                    rendered,
                    chapter_id=int(chapter.get("id", 0)),
                    chapter_ref=chapter_reference(chapter),
                    segment_id=str(segment_id),
                    segment_ref=shown_segment_id,
                ):
                    append_activity_event(output_dir, activity_event)

    output_language = structure.get("output_language", "en")
    chapter_reflection = run_chapter_reflection(
        chapter_title=chapter.get("title", ""),
        user_intent=user_intent,
        segments=rendered_segments,
        output_language=output_language,
        chapter_primary_role=str(chapter.get("primary_role", "body") or "body"),
        chapter_role_tags=list(chapter.get("role_tags", [])),
        prompt_set=prompt_set,
    )
    rendered_segments = apply_chapter_reflection_repairs(
        segments=rendered_segments,
        chapter_reflection=chapter_reflection,
        output_language=output_language,
    )
    memory = consolidate_memory_after_chapter(
        memory,
        chapter_ref=chapter_reference(chapter),
        chapter_title=str(chapter.get("title", "") or ""),
        primary_role=str(chapter.get("primary_role", "body") or "body"),
        rendered_segments=rendered_segments,
        chapter_reflection=chapter_reflection,
    )
    rendered_by_id = {
        segment.get("segment_id", ""): segment
        for segment in rendered_segments
    }
    for segment in chapter.get("segments", []):
        rendered = rendered_by_id.get(segment.get("id", ""))
        if not rendered:
            continue
        segment["status"] = "skipped" if rendered.get("verdict") == "skip" else "done"

    output_path = chapter_markdown_file(output_dir, chapter)
    chapter["status"] = "done"
    chapter["output_file"] = relative_output_path(output_dir, output_path)
    with write_context:
        write_chapter_qa_artifact(
            output_dir,
            chapter,
            chapter_reflection=chapter_reflection,
            output_language=output_language,
        )
        chapter_result = write_chapter_result(
            output_dir=output_dir,
            chapter=chapter,
            rendered_segments=rendered_segments,
            chapter_reflection=chapter_reflection,
            output_language=output_language,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            render_chapter_markdown(
                chapter,
                rendered_segments,
                output_language,
                chapter_reflection=chapter_reflection,
            ),
            encoding="utf-8",
        )
        _persist_reader_memory(output_dir, memory)
    with write_context:
        save_structure(structure_file(output_dir), structure)
        write_book_manifest(output_dir, structure)
        checkpoint_path.unlink(missing_ok=True)
    tracker["completed_chapters"] = int(tracker.get("completed_chapters", 0)) + 1
    chapter_seconds = tracker.setdefault("chapter_seconds", [])
    if isinstance(chapter_seconds, list):
        chapter_seconds.append(
            time.monotonic() - float(tracker.get("current_chapter_started_at", 0.0))
        )
    tracker["current_segment_ref"] = None
    _clear_current_reading_activity(tracker)
    tracker["current_completed_segments"] = len(chapter.get("segments", []))
    with write_context:
        _write_sequential_run_state(structure, output_dir, tracker, stage="deep_reading")
        append_activity_event(
            output_dir,
            {
                "type": "chapter_completed",
                "message": _chapter_completed_message(
                    output_language,
                    chapter_reference(chapter),
                    int(chapter_result.get("visible_reaction_count", 0) or 0),
                ),
                "chapter_id": int(chapter.get("id", 0)),
                "chapter_ref": chapter_reference(chapter),
                "visible_reaction_count": int(chapter_result.get("visible_reaction_count", 0)),
                "featured_reactions": list(chapter_result.get("featured_reactions", [])),
                "result_file": chapter_result_name(chapter),
            },
        )
    print(f"  └─ {chapter_reference(chapter)} 完成，已保存 {output_path.name}", flush=True)
    return memory


def _read_book_sequential(
    book_path: Path,
    structure: BookStructure,
    output_dir: Path,
    selected_chapters: list[StructureChapter],
    user_intent: str | None,
    skill_profile: SkillProfileName,
    budget_policy: BudgetPolicy,
    continue_mode: bool,
    tuning: SequentialPipelineTuning,
    prompt_set: IteratorV1PromptSet,
) -> BookStructure:
    """Run the sequential reader with background chapter segmentation."""
    memory = _load_reader_memory_snapshot(
        output_dir,
        structure,
        continue_mode=continue_mode,
    )
    total = len(selected_chapters)
    io_lock = threading.RLock()
    tracker: dict[str, object] = {
        "total_chapters": total,
        "completed_chapters": 0,
        "chapter_seconds": [],
        "current_chapter_id": None,
        "current_chapter_ref": None,
        "current_segment_ref": None,
        "current_reading_activity": None,
        "current_total_segments": 0,
        "current_completed_segments": 0,
        "last_checkpoint_at": None,
    }
    coordinator = BackgroundSegmentationCoordinator(
        structure=structure,
        output_dir=output_dir,
        book_path=book_path,
        selected_chapters=selected_chapters,
        tuning=tuning,
        io_lock=io_lock,
    )
    heartbeat = _ReadingActivityHeartbeat(
        structure=structure,
        output_dir=output_dir,
        tracker=tracker,
        io_lock=io_lock,
    )
    with io_lock:
        _update_current_reading_activity(
            tracker,
            phase="preparing",
            current_excerpt=str(selected_chapters[0].get("title", "") or "") if selected_chapters else None,
        )
        append_activity_event(
            output_dir,
            {
                "type": "structure_ready",
                "message": "原书结构已就绪，开始准备可读章节。",
            },
        )
        _write_sequential_run_state(
            structure,
            output_dir,
            tracker,
            stage="parsing_structure" if not selected_chapters[0].get("segments") else "ready",
            current_phase_step=None if selected_chapters[0].get("segments") else "等待首章切分",
        )
    heartbeat.start()
    coordinator.start()
    try:
        for index, chapter in enumerate(selected_chapters, start=1):
            chapter_id = int(chapter.get("id", 0))
            tracker["current_chapter_id"] = chapter_id
            tracker["current_chapter_ref"] = chapter_reference(chapter)
            tracker["current_segment_ref"] = None

            if not chapter.get("segments"):
                wait_step = "等待首章切分" if not coordinator.reader_started else "等待后续章节切分"
                with io_lock:
                    _update_current_reading_activity(
                        tracker,
                        phase="waiting" if coordinator.reader_started else "preparing",
                        current_excerpt=str(chapter.get("title", "") or ""),
                    )
                    _write_sequential_run_state(
                        structure,
                        output_dir,
                        tracker,
                        stage="parsing_structure" if not coordinator.reader_started else "deep_reading",
                        current_phase_step=wait_step,
                    )
                    append_activity_event(
                        output_dir,
                        {
                            "type": "reader_waiting_for_segments",
                            "message": f"等待 {chapter_reference(chapter)} 完成语义切分后继续深读。",
                            "chapter_id": chapter_id,
                            "chapter_ref": chapter_reference(chapter),
                        },
                    )
                coordinator.set_reader_waiting(chapter_id)
                coordinator.wait_until_segmented(chapter_id)
                coordinator.set_reader_waiting(None)

            coordinator.raise_if_failed()
            coordinator.note_reader_started(next_unread_index=index)
            tracker["current_total_segments"] = len(chapter.get("segments", []))
            tracker["current_completed_segments"] = sum(
                1
                for segment in chapter.get("segments", [])
                if segment.get("status") in {"done", "skipped"}
            )
            tracker["current_chapter_started_at"] = time.monotonic()
            with io_lock:
                first_segment = next(
                    (
                        segment
                        for segment in chapter.get("segments", [])
                        if str(segment.get("id", "") or "").strip()
                    ),
                    None,
                )
                if isinstance(first_segment, dict):
                    _update_current_reading_activity(
                        tracker,
                        phase="reading",
                        segment_ref=_visible_segment_ref(chapter, first_segment),
                        current_excerpt=str(
                            first_segment.get("text", "")
                            or first_segment.get("summary", "")
                            or ""
                        ),
                    )
                _write_sequential_run_state(structure, output_dir, tracker, stage="deep_reading")
                append_activity_event(
                    output_dir,
                    {
                        "type": "chapter_started",
                        "message": f"开始深读 {chapter_reference(chapter)}：{chapter.get('title', '')}",
                        "chapter_id": chapter_id,
                        "chapter_ref": chapter_reference(chapter),
                    },
                )
            try:
                memory = _run_single_chapter(
                    structure=structure,
                    output_dir=output_dir,
                    chapter=chapter,
                    memory=memory,
                    user_intent=user_intent,
                    index=index,
                    total=total,
                    skill_profile=skill_profile,
                    budget_policy=budget_policy,
                    allow_resume=continue_mode,
                    tracker=tracker,
                    io_lock=io_lock,
                    prompt_set=prompt_set,
                )
            except Exception as exc:
                with io_lock:
                    chapter["status"] = "in_progress"
                    save_structure(structure_file(output_dir), structure)
                    _write_sequential_run_state(
                        structure,
                        output_dir,
                        tracker,
                        stage="error",
                        error=str(exc),
                    )
                    append_activity_event(
                        output_dir,
                        {
                            "type": "error",
                            "message": f"{chapter_reference(chapter)} 处理中断：{exc}",
                            "chapter_id": chapter_id,
                            "chapter_ref": chapter_reference(chapter),
                        },
                    )
                raise
        with io_lock:
            _write_sequential_run_state(structure, output_dir, tracker, stage="completed")
            append_activity_event(
                output_dir,
                {
                    "type": "run_completed",
                    "message": "顺序深读已完成。",
                },
            )
        return structure
    finally:
        heartbeat.stop()
        coordinator.stop()


def read_book(
    book_path: Path,
    chapter_number: int | None = None,
    continue_mode: bool = False,
    user_intent: str | None = None,
    language_mode: str = "auto",
    read_mode: ReadMode = "sequential",
    skill_profile: SkillProfileName = "balanced",
    budget_policy: BudgetPolicy | None = None,
    analysis_policy: BookAnalysisPolicy | None = None,
    prompt_set: IteratorV1PromptSet = ITERATOR_V1_PROMPTS,
    book_analysis_prompt_set: BookAnalysisPromptSet = BOOK_ANALYSIS_PROMPTS,
) -> tuple[BookStructure, Path, bool]:
    """Run the outer iterator, writing checkpointed chapter markdown files."""
    structure, output_dir, created = ensure_structure_for_book(
        book_path,
        language_mode=language_mode,
        continue_mode=True,
        require_segments=False,
        prompt_set=prompt_set,
    )
    with llm_invocation_scope(
        profile_id=DEFAULT_RUNTIME_PROFILE_ID,
        trace_context=runtime_trace_context(
            output_dir,
            mechanism_key="iterator_v1",
            stage="read",
            extra={"read_mode": read_mode},
        ),
    ):
        selected_chapters = _chapter_selection(structure, chapter_number, continue_mode)
        if read_mode == "sequential":
            write_book_manifest(output_dir, structure)
            write_run_state(
                output_dir,
                build_run_state(
                    structure,
                    stage="ready",
                    total_chapters=len(selected_chapters),
                    completed_chapters=0,
                    current_phase_step=None,
                    resume_available=continue_mode,
                    last_checkpoint_at=None,
                ),
            )

        if not selected_chapters:
            print("没有待处理章节。", flush=True)
            return structure, output_dir, created
        policy = budget_policy or default_budget_policy()
        analysis = analysis_policy or default_book_analysis_policy()
        tuning = _default_pipeline_tuning()

        if read_mode == "book_analysis":
            structure, _analysis_state = run_book_analysis(
                structure=structure,
                output_dir=output_dir,
                selected_chapters=selected_chapters,
                user_intent=user_intent,
                skill_profile=skill_profile,
                budget_policy=policy,
                analysis_policy=analysis,
                prompt_set=book_analysis_prompt_set,
                reader_prompt_set=prompt_set,
            )
        elif read_mode == "sequential":
            structure = _read_book_sequential(
                book_path=book_path,
                structure=structure,
                output_dir=output_dir,
                selected_chapters=selected_chapters,
                user_intent=user_intent,
                skill_profile=skill_profile,
                budget_policy=policy,
                continue_mode=continue_mode,
                tuning=tuning,
                prompt_set=prompt_set,
            )
        else:
            raise ValueError(f'Unsupported read mode: "{read_mode}"')

        return structure, output_dir, created

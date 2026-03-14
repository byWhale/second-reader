"""Outer Iterator runtime for the Iterator-Reader architecture."""

from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from contextlib import nullcontext
from dataclasses import dataclass
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from src.config import (
    get_pipeline_prefetch_window,
    get_pipeline_segment_workers,
    get_pipeline_segment_workers_when_reader_blocked,
)
from .frontend_artifacts import (
    append_activity_event,
    build_run_state,
    estimate_eta_seconds,
    write_book_manifest,
    write_chapter_qa_artifact,
    write_chapter_result,
    write_run_state,
)
from .markdown import render_chapter_markdown
from .models import (
    BookAnalysisPolicy,
    BookStructure,
    BudgetPolicy,
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
from .reader import (
    apply_chapter_reflection_repairs,
    create_reader_state,
    initial_memory,
    run_chapter_reflection,
    run_reader_segment,
    update_memory,
)
from .storage import (
    chapter_markdown_file,
    chapter_reference,
    chapter_result_name,
    load_json,
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
    segment_workers = max(1, get_pipeline_segment_workers())
    blocked_workers = max(segment_workers, get_pipeline_segment_workers_when_reader_blocked())
    return SequentialPipelineTuning(
        segment_workers=segment_workers,
        segment_workers_when_reader_blocked=blocked_workers,
        prefetch_window=max(1, get_pipeline_prefetch_window()),
    )


def _timestamp() -> str:
    """Return a stable UTC timestamp for runtime checkpoints."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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
        print(f"  ├─ {normalized.get('message', '')}", flush=True)

    return emit


def _visible_segment_ref(chapter: StructureChapter, segment: dict[str, object]) -> str:
    """Resolve visible segment ref from segment metadata with fallback conversion."""
    ref = str(segment.get("segment_ref", "") or "").strip()
    if ref:
        return ref
    return segment_reference(chapter, str(segment.get("id", "") or segment.get("segment_id", "")))


def _normalize_memory_refs(structure: BookStructure, memory: ReaderMemory) -> ReaderMemory:
    """Rewrite summary prefixes from internal ids to visible refs when possible."""
    chapters_by_id = {
        int(chapter.get("id", 0)): chapter
        for chapter in structure.get("chapters", [])
    }
    normalized: ReaderMemory = {
        "prior_segment_summaries": [],
        "notable_findings": list(memory.get("notable_findings", [])),
        "open_threads": list(memory.get("open_threads", [])),
        "highlighted_quotes": list(memory.get("highlighted_quotes", [])),
    }

    pattern = re.compile(r"^\s*(\d+\.\d+)\s*:\s*(.*)$")
    for item in memory.get("prior_segment_summaries", []):
        text = str(item or "").strip()
        if not text:
            continue
        match = pattern.match(text)
        if not match:
            normalized["prior_segment_summaries"].append(text)
            continue
        raw_segment_id = match.group(1)
        suffix = match.group(2)
        chapter_prefix = raw_segment_id.split(".", 1)[0]
        if not chapter_prefix.isdigit():
            normalized["prior_segment_summaries"].append(text)
            continue
        chapter = chapters_by_id.get(int(chapter_prefix))
        if not chapter:
            normalized["prior_segment_summaries"].append(text)
            continue
        visible = segment_reference(chapter, raw_segment_id)
        normalized["prior_segment_summaries"].append(f"{visible}: {suffix}")

    return normalized


def _read_progress_event(segment_id: str, segment_summary: str) -> ReaderProgressEvent:
    """Render the initial read-stage progress event."""
    summary = (segment_summary or "").strip()
    summary = summary[:18].rstrip() + ("..." if len(summary) > 18 else "")
    if summary:
        return {"message": f"📖 读到 {segment_id}「{summary}」...", "kind": "position", "visibility": "default"}
    return {"message": f"📖 读到 {segment_id}...", "kind": "position", "visibility": "default"}


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


def _reaction_event_fields(rendered: dict[str, object]) -> dict[str, object]:
    """Extract compact reaction metadata for activity events."""
    visible = _segment_visible_reactions(rendered)
    reaction_types: list[str] = []
    highlight_quote = ""
    search_query = ""
    for reaction in visible:
        reaction_type = str(reaction.get("type", "")).strip()
        if reaction_type and reaction_type not in reaction_types:
            reaction_types.append(reaction_type)
        if not highlight_quote and reaction_type == "highlight":
            highlight_quote = str(reaction.get("anchor_quote", "")).strip()
        if not search_query and str(reaction.get("search_query", "")).strip():
            search_query = str(reaction.get("search_query", "")).strip()

    payload: dict[str, object] = {}
    if reaction_types:
        payload["reaction_types"] = reaction_types
    if highlight_quote:
        payload["highlight_quote"] = highlight_quote
    if search_query:
        payload["search_query"] = search_query
    return payload


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
    completed_chapter_seconds = list(tracker.get("chapter_seconds", []))
    total_chapters = int(tracker.get("total_chapters", 0))
    completed_chapters = int(tracker.get("completed_chapters", 0))
    current_chapter_id = tracker.get("current_chapter_id")
    current_chapter_ref = tracker.get("current_chapter_ref")
    current_segment_ref = tracker.get("current_segment_ref")
    eta_seconds: int | None

    if stage == "completed":
        eta_seconds = 0
        current_chapter_id = None
        current_chapter_ref = None
        current_segment_ref = None
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
            eta_seconds=eta_seconds,
            current_phase_step=current_phase_step,
            resume_available=bool(current_chapter_id is not None or completed_chapters > 0),
            last_checkpoint_at=None,
            error=error,
        ),
    )


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
    checkpoint_path = segment_checkpoint_file(output_dir, chapter)
    resumed_segment_map: dict[str, dict] = {}

    if allow_resume and checkpoint_path.exists():
        checkpoint_payload = load_json(checkpoint_path)
        if isinstance(checkpoint_payload, dict):
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
                memory = {
                    "prior_segment_summaries": list(stored_memory.get("prior_segment_summaries", [])),
                    "notable_findings": list(stored_memory.get("notable_findings", [])),
                    "open_threads": list(stored_memory.get("open_threads", [])),
                    "highlighted_quotes": list(stored_memory.get("highlighted_quotes", [])),
                }
                memory = _normalize_memory_refs(structure, memory)
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
            _write_sequential_run_state(structure, output_dir, tracker, stage="deep_reading")
            append_activity_event(
                output_dir,
                {
                    "type": "segment_started",
                    "message": f"开始阅读 {shown_segment_id}：{segment.get('summary', '')}",
                    "chapter_id": int(chapter.get("id", 0)),
                    "chapter_ref": chapter_reference(chapter),
                    "segment_id": str(segment_id),
                    "segment_ref": shown_segment_id,
                },
            )
        stdout_progress = _segment_progress(shown_segment_id)

        def progress(progress_event: ReaderProgressEvent | str) -> None:
            normalized = _coerce_reader_progress_event(progress_event)
            stdout_progress(normalized)
            with write_context:
                append_activity_event(
                    output_dir,
                    {
                        "type": "segment_progress",
                        "stream": "mindstream",
                        "kind": normalized.get("kind", "transition"),
                        "visibility": normalized.get("visibility", "default"),
                        "message": normalized.get("message", ""),
                        "chapter_id": int(chapter.get("id", 0)),
                        "chapter_ref": chapter_reference(chapter),
                        "segment_id": str(segment_id),
                        "segment_ref": shown_segment_id,
                        "search_query": normalized.get("search_query", ""),
                    },
                )

        progress(_read_progress_event(shown_segment_id, segment.get("summary", "")))
        state = create_reader_state(
            chapter_title=chapter.get("title", ""),
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
        )
        rendered, final_state = run_reader_segment(state, progress=progress)
        rendered_segments.append(rendered)
        memory = update_memory(memory, rendered)
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
            save_structure(structure_file(output_dir), structure)
            save_json(
                checkpoint_path,
                {
                    "chapter_id": chapter.get("id", 0),
                    "chapter_title": chapter.get("title", ""),
                    "rendered_segments": rendered_segments,
                    "memory": memory,
                    "chapter_budget": chapter_budget_state,
                },
            )
        tracker["current_completed_segments"] = len(rendered_segments)
        with write_context:
            _write_sequential_run_state(structure, output_dir, tracker, stage="deep_reading")
        visible_reactions = _segment_visible_reactions(rendered)
        if visible_reactions:
            with write_context:
                append_activity_event(
                    output_dir,
                    {
                        "type": "segment_completed",
                        "message": f"完成 {shown_segment_id}，保留了 {len(visible_reactions)} 条反应。",
                        "chapter_id": int(chapter.get("id", 0)),
                        "chapter_ref": chapter_reference(chapter),
                        "segment_id": str(segment_id),
                        "segment_ref": shown_segment_id,
                        **_reaction_event_fields(rendered),
                    },
                )

    output_language = structure.get("output_language", "en")
    chapter_reflection = run_chapter_reflection(
        chapter_title=chapter.get("title", ""),
        user_intent=user_intent,
        segments=rendered_segments,
        output_language=output_language,
    )
    rendered_segments = apply_chapter_reflection_repairs(
        segments=rendered_segments,
        chapter_reflection=chapter_reflection,
        output_language=output_language,
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
    tracker["current_completed_segments"] = len(chapter.get("segments", []))
    with write_context:
        _write_sequential_run_state(structure, output_dir, tracker, stage="deep_reading")
        append_activity_event(
            output_dir,
            {
                "type": "chapter_completed",
                "message": f"{chapter_reference(chapter)} 完成，已生成结果文件。",
                "chapter_id": int(chapter.get("id", 0)),
                "chapter_ref": chapter_reference(chapter),
                "visible_reaction_count": int(chapter_result.get("visible_reaction_count", 0)),
                "high_signal_reaction_count": int(chapter_result.get("high_signal_reaction_count", 0)),
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
) -> BookStructure:
    """Run the sequential reader with background chapter segmentation."""
    memory = initial_memory()
    total = len(selected_chapters)
    io_lock = threading.RLock()
    tracker: dict[str, object] = {
        "total_chapters": total,
        "completed_chapters": 0,
        "chapter_seconds": [],
        "current_chapter_id": None,
        "current_chapter_ref": None,
        "current_segment_ref": None,
        "current_total_segments": 0,
        "current_completed_segments": 0,
    }
    coordinator = BackgroundSegmentationCoordinator(
        structure=structure,
        output_dir=output_dir,
        book_path=book_path,
        selected_chapters=selected_chapters,
        tuning=tuning,
        io_lock=io_lock,
    )
    with io_lock:
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
) -> tuple[BookStructure, Path, bool]:
    """Run the outer iterator, writing checkpointed chapter markdown files."""
    structure, output_dir, created = ensure_structure_for_book(
        book_path,
        language_mode=language_mode,
        continue_mode=True,
        require_segments=False,
    )
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
        )
    else:
        raise ValueError(f'Unsupported read mode: "{read_mode}"')

    return structure, output_dir, created

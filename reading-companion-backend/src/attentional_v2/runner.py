"""Live parse/read runner integration for attentional_v2."""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from src.reading_core import BookDocument
from src.reading_core.storage import book_document_file, save_book_document
from src.reading_core.runtime_contracts import MechanismInfo, ParseRequest, ParseResult, ReadRequest, ReadResult
from src.reading_runtime import artifacts as runtime_artifacts
from src.reading_runtime.llm_registry import DEFAULT_RUNTIME_PROFILE_ID
from src.reading_runtime.provisioning import ProvisionedBook, ensure_canonical_parse
from src.reading_runtime.sequential_state import (
    append_activity_event,
    build_book_manifest_from_document,
    build_run_state,
    reset_activity,
    write_book_manifest,
    write_parse_progress,
    write_run_state,
)
from src.reading_runtime.shell_state import load_runtime_shell, save_runtime_shell
from src.iterator_reader.llm_utils import llm_invocation_scope, runtime_trace_context

from .bridge import build_anchor_record, candidate_pool_for_bridge_resolution, run_phase5_bridge_cycle
from .evaluation import build_normalized_eval_bundle, persist_normalized_eval_bundle
from .intake import process_sentence_intake
from .nodes import run_phase4_local_cycle
from .resume import persist_reading_position, resume_from_checkpoint, write_full_checkpoint
from .schemas import (
    ATTENTIONAL_V2_MECHANISM_VERSION,
    ATTENTIONAL_V2_POLICY_VERSION,
    AnchorMemoryState,
    AnchoredReactionRecord,
    KnowledgeActivationsState,
    LocalBufferState,
    MoveHistoryState,
    ReactionRecordsState,
    ReaderPolicy,
    ReflectiveSummariesState,
    TriggerState,
    WorkingPressureState,
    build_default_reader_policy,
    build_empty_anchor_memory,
    build_empty_knowledge_activations,
    build_empty_local_buffer,
    build_empty_move_history,
    build_empty_reaction_records,
    build_empty_reconsolidation_records,
    build_empty_reflective_summaries,
    build_empty_resume_metadata,
    build_empty_trigger_state,
    build_empty_working_pressure,
)
from .slow_cycle import (
    build_reaction_record,
    project_chapter_result_compatibility,
    reaction_records_for_chapter,
    run_phase6_chapter_cycle,
)
from .state_ops import (
    append_move,
    append_reaction_record,
    close_local_meaning_unit,
    apply_working_pressure_operations,
    upsert_anchor_record,
)
from .storage import (
    ATTENTIONAL_V2_MECHANISM_KEY,
    anchor_memory_file,
    chapter_result_compatibility_file,
    checkpoints_dir,
    derived_dir,
    initialize_artifact_tree,
    knowledge_activations_file,
    load_json,
    local_buffer_file,
    move_history_file,
    normalized_eval_bundle_file,
    reaction_records_file,
    reader_policy_file,
    reconsolidation_records_file,
    reflective_summaries_file,
    resume_metadata_file,
    revisit_index_file,
    runtime_dir,
    save_json,
    survey_map_file,
    trigger_state_file,
    working_pressure_file,
)
from .survey import write_book_survey_artifacts
from .retrieval import generate_candidate_set


def _timestamp() -> str:
    """Return a stable UTC timestamp."""

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _clean_text(value: object) -> str:
    """Return one normalized string."""

    return str(value or "").strip()


def _chapter_ref(chapter: dict[str, object]) -> str:
    """Return the stable chapter reference for one book-document chapter."""

    return _clean_text(chapter.get("reference") or chapter.get("chapter_ref") or f"Chapter {int(chapter.get('id', 0) or 0)}")


def _chapter_matches_request(chapter: dict[str, object], requested_number: int) -> bool:
    """Return whether one chapter matches a requested chapter number."""

    chapter_id = int(chapter.get("id", 0) or 0)
    chapter_number = int(chapter.get("chapter_number", 0) or 0)
    return requested_number in {chapter_id, chapter_number}


def _chapter_statuses(document: BookDocument, output_dir: Path) -> dict[int, str]:
    """Return current attentional chapter statuses from persisted compatibility payloads."""

    statuses: dict[int, str] = {}
    for chapter in document.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        chapter_id = int(chapter.get("id", 0) or 0)
        if chapter_id <= 0:
            continue
        result_path = chapter_result_compatibility_file(output_dir, chapter_id)
        statuses[chapter_id] = "done" if result_path.exists() else "pending"
    return statuses


def _chapter_result_relative_paths(document: BookDocument, output_dir: Path) -> dict[int, str]:
    """Return manifest-relative compatibility result paths for ready chapters."""

    paths: dict[int, str] = {}
    for chapter in document.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        chapter_id = int(chapter.get("id", 0) or 0)
        if chapter_id <= 0:
            continue
        result_path = chapter_result_compatibility_file(output_dir, chapter_id)
        if result_path.exists():
            paths[chapter_id] = str(result_path.relative_to(output_dir))
    return paths


def _write_manifest(
    output_dir: Path,
    document: BookDocument,
    *,
    chapter_statuses: dict[int, str] | None = None,
) -> dict[str, object]:
    """Persist one shared book manifest for attentional outputs."""

    manifest = build_book_manifest_from_document(
        output_dir,
        document,
        chapter_statuses=chapter_statuses or _chapter_statuses(document, output_dir),
        chapter_result_relative_paths=_chapter_result_relative_paths(document, output_dir),
    )
    return write_book_manifest(output_dir, manifest)


def _artifact_summary(
    provisioned: ProvisionedBook,
    book_document: BookDocument,
    *,
    artifact_tree: dict[str, object],
    survey_summary: dict[str, object],
) -> dict[str, object]:
    """Build the attentional parse/read artifact summary returned through runtime contracts."""

    chapters = [
        {
            "id": int(chapter.get("id", 0) or 0),
            "title": _clean_text(chapter.get("title")),
            "reference": _chapter_ref(chapter),
            "chapter_number": chapter.get("chapter_number"),
            "sentence_count": len(chapter.get("sentences", [])) if isinstance(chapter.get("sentences"), list) else 0,
            "status": "done"
            if chapter_result_compatibility_file(provisioned.output_dir, int(chapter.get("id", 0) or 0)).exists()
            else "pending",
        }
        for chapter in book_document.get("chapters", [])
        if isinstance(chapter, dict)
    ]
    return {
        "book": provisioned.title,
        "author": provisioned.author,
        "book_language": provisioned.book_language,
        "output_language": provisioned.output_language,
        "source_file": str(provisioned.book_path),
        "output_dir": str(provisioned.output_dir),
        "chapter_count": len(chapters),
        "chapters": chapters,
        "artifact_map": artifact_tree.get("artifact_map", {}),
        "survey_status": survey_summary.get("survey_map", {}).get("status", "ready"),
    }


def _default_builder(name: str) -> Callable[[], dict[str, object]]:
    """Return a builder for one runtime-state artifact."""

    builders: dict[str, Callable[[], dict[str, object]]] = {
        "local_buffer": lambda: build_empty_local_buffer(mechanism_version=ATTENTIONAL_V2_MECHANISM_VERSION),
        "trigger_state": lambda: build_empty_trigger_state(mechanism_version=ATTENTIONAL_V2_MECHANISM_VERSION),
        "working_pressure": lambda: build_empty_working_pressure(mechanism_version=ATTENTIONAL_V2_MECHANISM_VERSION),
        "anchor_memory": lambda: build_empty_anchor_memory(mechanism_version=ATTENTIONAL_V2_MECHANISM_VERSION),
        "reflective_summaries": lambda: build_empty_reflective_summaries(mechanism_version=ATTENTIONAL_V2_MECHANISM_VERSION),
        "knowledge_activations": lambda: build_empty_knowledge_activations(mechanism_version=ATTENTIONAL_V2_MECHANISM_VERSION),
        "move_history": lambda: build_empty_move_history(mechanism_version=ATTENTIONAL_V2_MECHANISM_VERSION),
        "reaction_records": lambda: build_empty_reaction_records(mechanism_version=ATTENTIONAL_V2_MECHANISM_VERSION),
        "reconsolidation_records": lambda: build_empty_reconsolidation_records(mechanism_version=ATTENTIONAL_V2_MECHANISM_VERSION),
        "reader_policy": lambda: build_default_reader_policy(
            mechanism_version=ATTENTIONAL_V2_MECHANISM_VERSION,
            policy_version=ATTENTIONAL_V2_POLICY_VERSION,
        ),
        "resume_metadata": lambda: build_empty_resume_metadata(
            mechanism_version=ATTENTIONAL_V2_MECHANISM_VERSION,
            policy_version=ATTENTIONAL_V2_POLICY_VERSION,
        ),
    }
    return builders[name]


def _load_or_default(path: Path, builder: Callable[[], dict[str, object]]) -> dict[str, object]:
    """Load one JSON artifact or return its default shape."""

    if path.exists():
        return load_json(path)
    return builder()


def _load_runtime_bundle(output_dir: Path) -> dict[str, dict[str, object]]:
    """Load the attentional runtime bundle from persisted artifacts."""

    return {
        "local_buffer": _load_or_default(local_buffer_file(output_dir), _default_builder("local_buffer")),
        "trigger_state": _load_or_default(trigger_state_file(output_dir), _default_builder("trigger_state")),
        "working_pressure": _load_or_default(working_pressure_file(output_dir), _default_builder("working_pressure")),
        "anchor_memory": _load_or_default(anchor_memory_file(output_dir), _default_builder("anchor_memory")),
        "reflective_summaries": _load_or_default(reflective_summaries_file(output_dir), _default_builder("reflective_summaries")),
        "knowledge_activations": _load_or_default(
            knowledge_activations_file(output_dir),
            _default_builder("knowledge_activations"),
        ),
        "move_history": _load_or_default(move_history_file(output_dir), _default_builder("move_history")),
        "reaction_records": _load_or_default(reaction_records_file(output_dir), _default_builder("reaction_records")),
        "reconsolidation_records": _load_or_default(
            reconsolidation_records_file(output_dir),
            _default_builder("reconsolidation_records"),
        ),
        "reader_policy": _load_or_default(reader_policy_file(output_dir), _default_builder("reader_policy")),
        "resume_metadata": _load_or_default(resume_metadata_file(output_dir), _default_builder("resume_metadata")),
    }


def _save_runtime_bundle(output_dir: Path, bundle: dict[str, dict[str, object]]) -> None:
    """Persist the attentional runtime bundle."""

    save_json(local_buffer_file(output_dir), bundle["local_buffer"])
    save_json(trigger_state_file(output_dir), bundle["trigger_state"])
    save_json(working_pressure_file(output_dir), bundle["working_pressure"])
    save_json(anchor_memory_file(output_dir), bundle["anchor_memory"])
    save_json(reflective_summaries_file(output_dir), bundle["reflective_summaries"])
    save_json(knowledge_activations_file(output_dir), bundle["knowledge_activations"])
    save_json(move_history_file(output_dir), bundle["move_history"])
    save_json(reaction_records_file(output_dir), bundle["reaction_records"])
    save_json(reconsolidation_records_file(output_dir), bundle["reconsolidation_records"])
    save_json(reader_policy_file(output_dir), bundle["reader_policy"])
    save_json(resume_metadata_file(output_dir), bundle["resume_metadata"])


def _compatibility_section_ref(chapter_id: int, sentence: dict[str, object]) -> str:
    """Return the current section-ref sidecar for one sentence anchor."""

    locator = sentence.get("locator")
    paragraph_index = 0
    if isinstance(locator, dict):
        paragraph_index = int(locator.get("paragraph_index", 0) or locator.get("paragraph_start", 0) or 0)
    if paragraph_index <= 0:
        paragraph_index = int(sentence.get("paragraph_index", 0) or 0)
    return f"{chapter_id}.{max(1, paragraph_index)}"


def _span_sentences(local_buffer: LocalBufferState) -> list[dict[str, object]]:
    """Return the current meaning-unit span from the rolling local buffer."""

    recent_sentences = [dict(item) for item in local_buffer.get("recent_sentences", []) if isinstance(item, dict)]
    open_ids = [str(item or "") for item in local_buffer.get("open_meaning_unit_sentence_ids", []) if str(item or "")]
    if not open_ids:
        return recent_sentences[-1:] if recent_sentences else []
    open_set = set(open_ids)
    span = [sentence for sentence in recent_sentences if _clean_text(sentence.get("sentence_id")) in open_set]
    return span or recent_sentences[-1:]


def _reading_locus(chapter_id: int, chapter_ref: str, sentence: dict[str, object], local_buffer: LocalBufferState) -> dict[str, object]:
    """Build the additive public reading-locus payload for live activity."""

    locus: dict[str, object] = {
        "kind": "span" if local_buffer.get("open_meaning_unit_sentence_ids") else "sentence",
        "chapter_id": chapter_id,
        "chapter_ref": chapter_ref,
        "sentence_start_id": _clean_text(local_buffer.get("open_meaning_unit_sentence_ids", [sentence.get("sentence_id")])[0] if local_buffer.get("open_meaning_unit_sentence_ids") else sentence.get("sentence_id")),
        "sentence_end_id": _clean_text(sentence.get("sentence_id")),
        "excerpt": _clean_text(sentence.get("text"))[:220],
    }
    locator = sentence.get("locator")
    if isinstance(locator, dict):
        locus["locator"] = dict(locator)
    return locus


def _current_activity(
    *,
    chapter_id: int,
    chapter_ref: str,
    sentence: dict[str, object],
    local_buffer: LocalBufferState,
    move_type: str | None = None,
    active_reaction_id: str | None = None,
) -> dict[str, object]:
    """Build the shared current-reading-activity snapshot."""

    activity: dict[str, object] = {
        "phase": "reading",
        "updated_at": _timestamp(),
        "segment_ref": _compatibility_section_ref(chapter_id, sentence),
        "current_excerpt": _clean_text(sentence.get("text"))[:220],
        "reading_locus": _reading_locus(chapter_id, chapter_ref, sentence, local_buffer),
        "reconstructed_hot_state": bool(local_buffer.get("is_reconstructed")),
        "last_resume_kind": local_buffer.get("last_resume_kind"),
    }
    if move_type:
        activity["move_type"] = move_type
    if active_reaction_id:
        activity["active_reaction_id"] = active_reaction_id
    return activity


def _update_shell_phase(output_dir: Path, *, status: str, phase: str) -> None:
    """Update the thin shared runtime shell status/phase."""

    shell_path = runtime_artifacts.runtime_shell_file(output_dir)
    shell = load_runtime_shell(shell_path)
    shell["status"] = status
    shell["phase"] = phase
    shell["updated_at"] = _timestamp()
    save_runtime_shell(shell_path, shell)


def _reset_live_runtime(output_dir: Path) -> None:
    """Clear live attentional runtime artifacts for one fresh full rerun."""

    for path in (
        working_pressure_file(output_dir),
        local_buffer_file(output_dir),
        trigger_state_file(output_dir),
        anchor_memory_file(output_dir),
        reflective_summaries_file(output_dir),
        knowledge_activations_file(output_dir),
        move_history_file(output_dir),
        reaction_records_file(output_dir),
        reconsolidation_records_file(output_dir),
        resume_metadata_file(output_dir),
        runtime_artifacts.runtime_shell_file(output_dir),
        runtime_artifacts.run_state_file(output_dir),
        runtime_artifacts.parse_state_file(output_dir),
    ):
        path.unlink(missing_ok=True)
    shutil.rmtree(checkpoints_dir(output_dir), ignore_errors=True)
    shutil.rmtree(runtime_artifacts.checkpoint_summaries_dir(output_dir), ignore_errors=True)
    shutil.rmtree(chapter_result_compatibility_file(output_dir, 1).parent, ignore_errors=True)
    shutil.rmtree(normalized_eval_bundle_file(output_dir).parent, ignore_errors=True)
    reset_activity(output_dir)


def _chapter_selection(
    document: BookDocument,
    output_dir: Path,
    *,
    chapter_number: int | None,
    continue_mode: bool,
    resume_chapter_id: int | None,
) -> list[dict[str, object]]:
    """Select chapters for the current live runner invocation."""

    chapters = [dict(chapter) for chapter in document.get("chapters", []) if isinstance(chapter, dict)]
    if chapter_number is not None:
        selected = [chapter for chapter in chapters if _chapter_matches_request(chapter, chapter_number)]
        if not selected:
            raise ValueError(f"Chapter {chapter_number} was not found in the parsed book.")
        return selected

    if not continue_mode:
        return chapters

    remaining = [
        chapter
        for chapter in chapters
        if not chapter_result_compatibility_file(output_dir, int(chapter.get("id", 0) or 0)).exists()
    ]
    if resume_chapter_id:
        remaining.sort(key=lambda chapter: (int(chapter.get("id", 0) or 0) < int(resume_chapter_id), int(chapter.get("id", 0) or 0)))
    return remaining


def _chapter_start_index(chapter: dict[str, object], current_sentence_id: str) -> int:
    """Return the first unread sentence index for one continued chapter."""

    if not current_sentence_id:
        return 0
    sentences = chapter.get("sentences", [])
    for index, sentence in enumerate(sentences):
        if isinstance(sentence, dict) and _clean_text(sentence.get("sentence_id")) == current_sentence_id:
            return index + 1
    return 0


def parse_attentional_v2(request: ParseRequest, mechanism: MechanismInfo) -> ParseResult:
    """Implement the parse-stage entrypoint for attentional_v2."""

    provisioned = ensure_canonical_parse(request.book_path, language_mode=request.language_mode)
    if provisioned.book_document is None:
        raise RuntimeError("Shared canonical parse did not produce book_document.json.")

    save_book_document(book_document_file(provisioned.output_dir), provisioned.book_document)
    created = not runtime_artifacts.book_manifest_file(provisioned.output_dir).exists()
    with llm_invocation_scope(
        profile_id=DEFAULT_RUNTIME_PROFILE_ID,
        trace_context=runtime_trace_context(
            provisioned.output_dir,
            mechanism_key=mechanism.key,
            stage="parse",
        ),
    ):
        artifact_tree = initialize_artifact_tree(provisioned.output_dir)
        survey_summary = write_book_survey_artifacts(
            provisioned.output_dir,
            provisioned.book_document,
            policy_snapshot=build_default_reader_policy(),
        )
        chapter_ids = [
            int(chapter.get("id", 0) or 0)
            for chapter in provisioned.book_document.get("chapters", [])
            if isinstance(chapter, dict) and int(chapter.get("id", 0) or 0) > 0
        ]
        _write_manifest(
            provisioned.output_dir,
            provisioned.book_document,
            chapter_statuses={chapter_id: "pending" for chapter_id in chapter_ids},
        )
        write_parse_progress(
            provisioned.output_dir,
            book_title=provisioned.title,
            status="ready",
            total_chapters=len(chapter_ids),
            completed_chapters=len(chapter_ids),
            parsed_chapter_ids=chapter_ids,
            sync_run_state=False,
        )
        write_run_state(
            provisioned.output_dir,
            build_run_state(
                book_title=provisioned.title,
                stage="ready",
                total_chapters=len(chapter_ids),
                completed_chapters=0,
                resume_available=False,
            ),
        )
        append_activity_event(
            provisioned.output_dir,
            {
                "type": "structure_ready",
                "message": "Attentional V2 parse is ready; the shared sentence substrate and survey artifacts are available.",
            },
        )
        return ParseResult(
            mechanism=mechanism,
            book_document=provisioned.book_document,
            output_dir=provisioned.output_dir,
            created=created,
            mechanism_artifact=_artifact_summary(
                provisioned,
                provisioned.book_document,
                artifact_tree=artifact_tree,
                survey_summary=survey_summary,
            ),
        )


def read_attentional_v2(request: ReadRequest, mechanism: MechanismInfo) -> ReadResult:
    """Run the live attentional_v2 sequential reading loop."""

    if request.task_mode == "book_analysis":
        raise ValueError("attentional_v2 does not support book_analysis mode yet.")

    provisioned = ensure_canonical_parse(request.book_path, language_mode=request.language_mode)
    if provisioned.book_document is None:
        raise RuntimeError("Shared canonical parse did not produce book_document.json.")

    output_dir = provisioned.output_dir
    save_book_document(book_document_file(output_dir), provisioned.book_document)
    created = not runtime_artifacts.book_manifest_file(output_dir).exists()
    with llm_invocation_scope(
        profile_id=DEFAULT_RUNTIME_PROFILE_ID,
        trace_context=runtime_trace_context(
            output_dir,
            mechanism_key=mechanism.key,
            stage="read",
        ),
    ):
        if not request.continue_mode:
            _reset_live_runtime(output_dir)
        artifact_tree = initialize_artifact_tree(output_dir)
        survey_summary = write_book_survey_artifacts(
            output_dir,
            provisioned.book_document,
            policy_snapshot=build_default_reader_policy(),
        )
        if not request.continue_mode:
            _write_manifest(output_dir, provisioned.book_document)
        _update_shell_phase(output_dir, status="running", phase="preparing")

        bundle = _load_runtime_bundle(output_dir)
        resume_payload: dict[str, object] | None = None
        if request.continue_mode:
            resume_payload = resume_from_checkpoint(output_dir, book_document=provisioned.book_document)
            bundle = _load_runtime_bundle(output_dir)

        reader_policy: ReaderPolicy = bundle["reader_policy"]  # type: ignore[assignment]
        local_buffer: LocalBufferState = bundle["local_buffer"]  # type: ignore[assignment]
        trigger_state: TriggerState = bundle["trigger_state"]  # type: ignore[assignment]
        working_pressure: WorkingPressureState = bundle["working_pressure"]  # type: ignore[assignment]
        anchor_memory: AnchorMemoryState = bundle["anchor_memory"]  # type: ignore[assignment]
        reflective_summaries: ReflectiveSummariesState = bundle["reflective_summaries"]  # type: ignore[assignment]
        knowledge_activations: KnowledgeActivationsState = bundle["knowledge_activations"]  # type: ignore[assignment]
        move_history: MoveHistoryState = bundle["move_history"]  # type: ignore[assignment]
        reaction_records: ReactionRecordsState = bundle["reaction_records"]  # type: ignore[assignment]
        reconsolidation_records = bundle["reconsolidation_records"]
        resume_metadata = bundle["resume_metadata"]

        chapter_statuses = _chapter_statuses(provisioned.book_document, output_dir)
        resume_chapter_id = int(resume_payload.get("local_continuity", {}).get("chapter_id", 0) or 0) if isinstance(resume_payload, dict) else None
        chapters = _chapter_selection(
            provisioned.book_document,
            output_dir,
            chapter_number=request.chapter_number,
            continue_mode=request.continue_mode,
            resume_chapter_id=resume_chapter_id,
        )

        completed_chapters = len([status for status in chapter_statuses.values() if status == "done"])
        total_chapters = len([chapter for chapter in provisioned.book_document.get("chapters", []) if isinstance(chapter, dict)])
        run_started_at = _timestamp()

        for chapter in chapters:
            chapter_id = int(chapter.get("id", 0) or 0)
            chapter_ref = _chapter_ref(chapter)
            chapter_statuses[chapter_id] = "in_progress"
            _write_manifest(output_dir, provisioned.book_document, chapter_statuses=chapter_statuses)
            write_run_state(
                output_dir,
                build_run_state(
                    book_title=provisioned.title,
                    stage="deep_reading",
                    total_chapters=total_chapters,
                    completed_chapters=completed_chapters,
                    current_chapter_id=chapter_id,
                    current_chapter_ref=chapter_ref,
                    current_phase_step="reading",
                    resume_available=bool(load_runtime_shell(runtime_artifacts.runtime_shell_file(output_dir)).get("resume_available")),
                    last_checkpoint_at=load_runtime_shell(runtime_artifacts.runtime_shell_file(output_dir)).get("last_checkpoint_at"),
                ),
            )
            append_activity_event(
                output_dir,
                {
                    "type": "chapter_started",
                    "message": f"Started {chapter_ref}.",
                    "chapter_id": chapter_id,
                    "chapter_ref": chapter_ref,
                },
            )

            meaning_units_in_chapter: list[dict[str, object]] = []
            sentences = [dict(sentence) for sentence in chapter.get("sentences", []) if isinstance(sentence, dict)]
            start_index = 0
            if request.continue_mode and resume_chapter_id == chapter_id:
                start_index = _chapter_start_index(chapter, _clean_text(local_buffer.get("current_sentence_id")))
            if start_index >= len(sentences):
                chapter_statuses[chapter_id] = "done"
                continue

            for sentence in sentences[start_index:]:
                sentence_id = _clean_text(sentence.get("sentence_id"))
                local_buffer, trigger_state = process_sentence_intake(
                    sentence,
                    local_buffer=local_buffer,
                    working_pressure=working_pressure,
                    anchor_memory=anchor_memory,
                )
                save_json(trigger_state_file(output_dir), trigger_state)

                current_activity = _current_activity(
                    chapter_id=chapter_id,
                    chapter_ref=chapter_ref,
                    sentence=sentence,
                    local_buffer=local_buffer,
                )
                persist_reading_position(
                    output_dir,
                    chapter_id=chapter_id,
                    chapter_ref=chapter_ref,
                    local_buffer=local_buffer,
                    status="running",
                    phase="reading",
                )
                write_run_state(
                    output_dir,
                    build_run_state(
                        book_title=provisioned.title,
                        stage="deep_reading",
                        total_chapters=total_chapters,
                        completed_chapters=completed_chapters,
                        current_chapter_id=chapter_id,
                        current_chapter_ref=chapter_ref,
                        current_segment_ref=_compatibility_section_ref(chapter_id, sentence),
                        current_reading_activity=current_activity,
                        current_phase_step="reading",
                        resume_available=True,
                        last_checkpoint_at=load_runtime_shell(runtime_artifacts.runtime_shell_file(output_dir)).get("last_checkpoint_at"),
                    ),
                )

                if _clean_text(trigger_state.get("output")) == "no_zoom":
                    continue

                current_span_sentences = _span_sentences(local_buffer)
                candidate_set = generate_candidate_set(
                    provisioned.book_document,
                    current_sentence_id=sentence_id,
                    current_text=_clean_text(sentence.get("text")),
                    anchor_memory=anchor_memory,
                )
                bridge_candidates = candidate_pool_for_bridge_resolution(
                    candidate_set,
                    max_supporting_candidates=int(reader_policy.get("bridge", {}).get("max_supporting_candidates", 2) or 2),
                )
                phase4 = run_phase4_local_cycle(
                    focal_sentence=sentence,
                    current_span_sentences=current_span_sentences,
                    trigger_state=trigger_state,
                    working_pressure=working_pressure,
                    anchor_memory=anchor_memory,
                    knowledge_activations=knowledge_activations,
                    reader_policy=reader_policy,
                    bridge_candidates=bridge_candidates,
                    output_language=provisioned.output_language,
                    output_dir=output_dir,
                    book_title=provisioned.title,
                    author=provisioned.author,
                    chapter_title=_clean_text(chapter.get("title")),
                    boundary_context={
                        "trigger_output": _clean_text(trigger_state.get("output")),
                        "gate_state": _clean_text(trigger_state.get("gate_state")),
                        "cadence_counter": int(trigger_state.get("cadence_counter", 0) or 0),
                        "trigger_signals": [
                            {
                                "signal_kind": _clean_text(signal.get("signal_kind")),
                                "family": _clean_text(signal.get("family")),
                                "strength": _clean_text(signal.get("strength")),
                                "evidence": _clean_text(signal.get("evidence")),
                            }
                            for signal in trigger_state.get("signals", [])
                            if isinstance(signal, dict)
                        ],
                        "callback_anchor_ids": [
                            _clean_text(anchor_id)
                            for anchor_id in trigger_state.get("callback_anchor_ids", [])
                            if _clean_text(anchor_id)
                        ],
                    },
                )
                zoom_result = dict(phase4.get("zoom_result") or {})
                closure_result = dict(phase4.get("closure_result") or {})
                controller_result = dict(phase4.get("controller_result") or {})
                reaction_result = dict(phase4.get("reaction_result") or {})
                working_pressure = apply_working_pressure_operations(working_pressure, zoom_result.get("pressure_updates", []))
                working_pressure = apply_working_pressure_operations(
                    working_pressure,
                    closure_result.get("proposed_state_operations", []),
                )

                chosen_move = _clean_text(controller_result.get("chosen_move"))
                if chosen_move in {"advance", "dwell", "bridge", "reframe"}:
                    move_history = append_move(
                        move_history,
                        {
                            "move_id": f"move:{sentence_id}:{chosen_move}",
                            "move_type": chosen_move,
                            "reason": _clean_text(controller_result.get("reason")) or "controller decision",
                            "source_sentence_id": sentence_id,
                            "target_anchor_id": _clean_text(controller_result.get("target_anchor_id")),
                            "target_sentence_id": _clean_text(controller_result.get("target_sentence_id")),
                            "created_at": _timestamp(),
                        },
                    )

                emitted_reaction: AnchoredReactionRecord | None = None
                current_anchor = build_anchor_record(
                    sentence_start_id=_clean_text(current_span_sentences[0].get("sentence_id")) if current_span_sentences else sentence_id,
                    sentence_end_id=sentence_id,
                    quote=_clean_text(reaction_result.get("reaction", {}).get("anchor_quote")) or _clean_text(sentence.get("text")),
                    locator=dict(sentence.get("locator", {})) if isinstance(sentence.get("locator"), dict) else {},
                    anchor_kind="visible_reaction",
                    why_it_mattered=_clean_text(reaction_result.get("reason")) or _clean_text(zoom_result.get("local_interpretation")) or _clean_text(closure_result.get("meaning_unit_summary")),
                )

                if reaction_result.get("decision") == "emit" and isinstance(reaction_result.get("reaction"), dict):
                    anchor_memory = upsert_anchor_record(anchor_memory, current_anchor)
                    chapter_reaction_count = len(reaction_records_for_chapter(reaction_records, chapter_ref=chapter_ref))
                    emitted_reaction = build_reaction_record(
                        reaction=reaction_result["reaction"],
                        primary_anchor=current_anchor,
                        chapter_id=chapter_id,
                        chapter_ref=chapter_ref,
                        emitted_at_sentence_id=sentence_id,
                        compatibility_section_ref=_compatibility_section_ref(chapter_id, sentence),
                        ordinal=chapter_reaction_count + 1,
                    )
                    reaction_records = append_reaction_record(reaction_records, emitted_reaction)
                    append_activity_event(
                        output_dir,
                        {
                            "type": "reaction_emitted",
                            "stream": "mindstream",
                            "kind": "thought",
                            "visibility": "default",
                            "message": _clean_text(emitted_reaction.get("thought")),
                            "chapter_id": chapter_id,
                            "chapter_ref": chapter_ref,
                            "segment_ref": _compatibility_section_ref(chapter_id, sentence),
                            "anchor_quote": _clean_text(emitted_reaction.get("primary_anchor", {}).get("quote")),
                            "reading_locus": _reading_locus(chapter_id, chapter_ref, sentence, local_buffer),
                            "move_type": chosen_move or None,
                            "active_reaction_id": _clean_text(emitted_reaction.get("reaction_id")),
                            "reaction_types": [_clean_text(emitted_reaction.get("type"))],
                            "current_excerpt": _clean_text(sentence.get("text"))[:220],
                        },
                    )

                if chosen_move == "bridge":
                    phase5 = run_phase5_bridge_cycle(
                        current_span_sentences=current_span_sentences,
                        candidate_set=candidate_set,
                        working_pressure=working_pressure,
                        anchor_memory=anchor_memory,
                        knowledge_activations=knowledge_activations,
                        move_history=move_history,
                        reader_policy=reader_policy,
                        output_language=provisioned.output_language,
                        current_anchor=current_anchor,
                        output_dir=output_dir,
                        book_title=provisioned.title,
                        author=provisioned.author,
                        chapter_title=_clean_text(chapter.get("title")),
                    )
                    working_pressure = phase5["working_pressure"]  # type: ignore[assignment]
                    anchor_memory = phase5["anchor_memory"]  # type: ignore[assignment]
                    knowledge_activations = phase5["knowledge_activations"]  # type: ignore[assignment]
                    move_history = phase5["move_history"]  # type: ignore[assignment]

                if _clean_text(closure_result.get("closure_decision")) == "close":
                    meaning_units_in_chapter.append(
                        {
                            "sentence_ids": [sentence_id for sentence_id in local_buffer.get("open_meaning_unit_sentence_ids", []) if _clean_text(sentence_id)],
                            "summary": _clean_text(closure_result.get("meaning_unit_summary")),
                            "dominant_move": _clean_text(closure_result.get("dominant_move")),
                        }
                    )
                    local_buffer = close_local_meaning_unit(local_buffer)

                bundle.update(
                    {
                        "local_buffer": local_buffer,
                        "trigger_state": trigger_state,
                        "working_pressure": working_pressure,
                        "anchor_memory": anchor_memory,
                        "reflective_summaries": reflective_summaries,
                        "knowledge_activations": knowledge_activations,
                        "move_history": move_history,
                        "reaction_records": reaction_records,
                        "reconsolidation_records": reconsolidation_records,
                        "reader_policy": reader_policy,
                        "resume_metadata": resume_metadata,
                    }
                )
                _save_runtime_bundle(output_dir, bundle)
                active_refs = {
                    "reaction_id": _clean_text(emitted_reaction.get("reaction_id")) if emitted_reaction else "",
                    "anchor_id": _clean_text(current_anchor.get("anchor_id")),
                    "move_id": _clean_text(move_history.get("moves", [])[-1].get("move_id")) if move_history.get("moves") else "",
                }
                persist_reading_position(
                    output_dir,
                    chapter_id=chapter_id,
                    chapter_ref=chapter_ref,
                    local_buffer=local_buffer,
                    active_artifact_refs={key: value for key, value in active_refs.items() if value},
                    status="running",
                    phase="reading",
                )

            chapter_end_anchor = build_anchor_record(
                sentence_start_id=_clean_text(sentences[-1].get("sentence_id")) if sentences else f"c{chapter_id}-end",
                sentence_end_id=_clean_text(sentences[-1].get("sentence_id")) if sentences else f"c{chapter_id}-end",
                quote=_clean_text(sentences[-1].get("text")) if sentences else chapter_ref,
                locator=dict(sentences[-1].get("locator", {})) if sentences and isinstance(sentences[-1].get("locator"), dict) else {},
                anchor_kind="chapter_end",
                why_it_mattered="chapter-end consolidation anchor",
            )
            phase6 = run_phase6_chapter_cycle(
                book_id=runtime_artifacts.book_id_from_output_dir(output_dir),
                chapter=chapter,
                meaning_units_in_chapter=meaning_units_in_chapter,
                chapter_end_anchor=chapter_end_anchor,
                working_pressure=working_pressure,
                anchor_memory=anchor_memory,
                reflective_summaries=reflective_summaries,
                knowledge_activations=knowledge_activations,
                reaction_records=reaction_records,
                reader_policy=reader_policy,
                output_language=provisioned.output_language,
                output_dir=output_dir,
                persist_compatibility_projection=True,
                book_title=provisioned.title,
                author=provisioned.author,
            )
            working_pressure = phase6["working_pressure"]  # type: ignore[assignment]
            anchor_memory = phase6["anchor_memory"]  # type: ignore[assignment]
            reflective_summaries = phase6["reflective_summaries"]  # type: ignore[assignment]
            knowledge_activations = phase6["knowledge_activations"]  # type: ignore[assignment]
            reaction_records = phase6["reaction_records"]  # type: ignore[assignment]
            chapter_statuses[chapter_id] = "done"
            completed_chapters += 1
            _write_manifest(output_dir, provisioned.book_document, chapter_statuses=chapter_statuses)
            checkpoint = write_full_checkpoint(
                output_dir,
                checkpoint_id=f"chapter-{chapter_id:03d}",
                checkpoint_reason="chapter_boundary",
            )
            append_activity_event(
                output_dir,
                {
                    "type": "chapter_completed",
                    "message": f"Finished {chapter_ref} with {len(reaction_records_for_chapter(reaction_records, chapter_ref=chapter_ref))} visible reactions.",
                    "chapter_id": chapter_id,
                    "chapter_ref": chapter_ref,
                },
            )
            write_run_state(
                output_dir,
                build_run_state(
                    book_title=provisioned.title,
                    stage="deep_reading",
                    total_chapters=total_chapters,
                    completed_chapters=completed_chapters,
                    current_chapter_id=chapter_id,
                    current_chapter_ref=chapter_ref,
                    current_phase_step="chapter_completed",
                    resume_available=True,
                    last_checkpoint_at=checkpoint.get("created_at"),
                ),
            )
            bundle.update(
                {
                    "local_buffer": local_buffer,
                    "trigger_state": trigger_state,
                    "working_pressure": working_pressure,
                    "anchor_memory": anchor_memory,
                    "reflective_summaries": reflective_summaries,
                    "knowledge_activations": knowledge_activations,
                    "move_history": move_history,
                    "reaction_records": reaction_records,
                    "reconsolidation_records": reconsolidation_records,
                    "reader_policy": reader_policy,
                    "resume_metadata": resume_metadata,
                }
            )
            _save_runtime_bundle(output_dir, bundle)

        _write_manifest(output_dir, provisioned.book_document, chapter_statuses=chapter_statuses)
        _update_shell_phase(output_dir, status="completed", phase="idle")
        write_run_state(
            output_dir,
            build_run_state(
                book_title=provisioned.title,
                stage="completed",
                total_chapters=total_chapters,
                completed_chapters=completed_chapters,
                resume_available=bool(load_runtime_shell(runtime_artifacts.runtime_shell_file(output_dir)).get("resume_available")),
                last_checkpoint_at=load_runtime_shell(runtime_artifacts.runtime_shell_file(output_dir)).get("last_checkpoint_at"),
            ),
        )
        append_activity_event(
            output_dir,
            {
                "type": "run_completed",
                "message": "Attentional V2 sequential reading completed.",
                "details": {
                    "started_at": run_started_at,
                    "finished_at": _timestamp(),
                },
            },
        )

        normalized_eval_bundle = build_normalized_eval_bundle(
            output_dir,
            config_payload={
                "task_mode": request.task_mode,
                "mechanism_config": dict(request.mechanism_config),
            },
        )
        if bool(dict(request.mechanism_config).get("persist_normalized_eval_bundle")):
            persist_normalized_eval_bundle(
                output_dir,
                config_payload={
                    "task_mode": request.task_mode,
                    "mechanism_config": dict(request.mechanism_config),
                },
            )
        return ReadResult(
            mechanism=mechanism,
            book_document=provisioned.book_document,
            output_dir=output_dir,
            created=created,
            mechanism_artifact=_artifact_summary(
                provisioned,
                provisioned.book_document,
                artifact_tree=artifact_tree,
                survey_summary=survey_summary,
            ),
            normalized_eval_bundle=normalized_eval_bundle,
        )

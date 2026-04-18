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
    chapter_reference,
    reset_activity,
    write_book_manifest,
    write_parse_progress,
    write_run_state,
)
from src.reading_runtime.shell_state import load_runtime_shell, save_runtime_shell
from src.iterator_reader.llm_utils import ReaderLLMError, llm_invocation_scope, runtime_trace_context

from .bridge import build_anchor_record, run_phase5_bridge_cycle
from .evaluation import build_normalized_eval_bundle, persist_normalized_eval_bundle
from .intake import process_sentence_intake
from .knowledge import apply_activation_operations
from .nodes import (
    build_unitize_preview,
    express_unit,
    navigate_route,
    navigate_unitize,
    persist_unitization_audit,
    read_unit,
)
from .read_context import (
    build_carry_forward_context,
    merge_supplemental_contexts,
    persist_read_audit,
    resolve_context_request,
)
from .resume import persist_reading_position, resume_from_checkpoint, write_full_checkpoint
from .schemas import (
    ATTENTIONAL_V2_MECHANISM_VERSION,
    ATTENTIONAL_V2_POLICY_VERSION,
    AnchorBankState,
    AnchoredReactionRecord,
    ConceptRegistryState,
    ExpressResult,
    KnowledgeActivationsState,
    LocalBufferState,
    MoveHistoryState,
    NavigateRouteDecision,
    ReactionRecordsState,
    ReaderPolicy,
    ReflectiveFramesState,
    ThreadTraceState,
    TriggerState,
    UnitizeDecision,
    ReadUnitResult,
    WorkingState,
    build_empty_anchor_bank,
    build_empty_continuation_capsule,
    build_empty_concept_registry,
    build_default_reader_policy,
    build_empty_knowledge_activations,
    build_empty_local_buffer,
    build_empty_move_history,
    build_empty_reaction_records,
    build_empty_reconsolidation_records,
    build_empty_reflective_frames,
    build_empty_resume_metadata,
    build_empty_thread_trace,
    build_empty_trigger_state,
    build_empty_working_state,
)
from .slow_cycle import (
    build_reaction_record,
    build_reaction_record_from_express_result,
    compat_reaction_family,
    project_chapter_result_compatibility,
    reaction_records_for_chapter,
    run_phase6_chapter_cycle,
)
from .state_ops import (
    append_move,
    append_reaction_record,
    apply_anchor_bank_operations,
    apply_concept_registry_operations,
    apply_thread_trace_operations,
    close_local_meaning_unit,
    apply_working_state_operations,
    upsert_anchor_record,
)
from .state_projection import build_navigation_context, context_ref_ids
from .storage import (
    ATTENTIONAL_V2_MECHANISM_KEY,
    anchor_bank_file,
    chapter_result_compatibility_file,
    checkpoints_dir,
    concept_registry_file,
    continuation_capsule_file,
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
    reflective_frames_file,
    resume_metadata_file,
    revisit_index_file,
    runtime_dir,
    save_json,
    survey_map_file,
    thread_trace_file,
    trigger_state_file,
    read_audit_file,
    unitization_audit_file,
    working_state_file,
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

    return chapter_reference(chapter)


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
        "continuation_capsule": lambda: build_empty_continuation_capsule(
            mechanism_version=ATTENTIONAL_V2_MECHANISM_VERSION,
        ),
        "working_state": lambda: build_empty_working_state(mechanism_version=ATTENTIONAL_V2_MECHANISM_VERSION),
        "concept_registry": lambda: build_empty_concept_registry(mechanism_version=ATTENTIONAL_V2_MECHANISM_VERSION),
        "thread_trace": lambda: build_empty_thread_trace(mechanism_version=ATTENTIONAL_V2_MECHANISM_VERSION),
        "reflective_frames": lambda: build_empty_reflective_frames(mechanism_version=ATTENTIONAL_V2_MECHANISM_VERSION),
        "anchor_bank": lambda: build_empty_anchor_bank(mechanism_version=ATTENTIONAL_V2_MECHANISM_VERSION),
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

    bundle = {
        "local_buffer": _load_or_default(local_buffer_file(output_dir), _default_builder("local_buffer")),
        "trigger_state": _load_or_default(trigger_state_file(output_dir), _default_builder("trigger_state")),
        "continuation_capsule": _load_or_default(continuation_capsule_file(output_dir), _default_builder("continuation_capsule")),
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
    legacy_paths = {
        "working_pressure": runtime_dir(output_dir) / "working_pressure.json",
        "anchor_memory": runtime_dir(output_dir) / "anchor_memory.json",
        "reflective_summaries": runtime_dir(output_dir) / "reflective_summaries.json",
    }
    new_state_paths = {
        "working_state": working_state_file(output_dir),
        "concept_registry": concept_registry_file(output_dir),
        "thread_trace": thread_trace_file(output_dir),
        "reflective_frames": reflective_frames_file(output_dir),
        "anchor_bank": anchor_bank_file(output_dir),
    }
    loaded_new = {name: load_json(path) for name, path in new_state_paths.items() if path.exists()}
    if not loaded_new and any(path.exists() for path in legacy_paths.values()):
        raise RuntimeError(
            "Pre-Phase C.3 attentional_v2 runtime state is no longer supported; rerun from a new-format state directory."
        )
    for name in ("working_state", "concept_registry", "thread_trace", "reflective_frames", "anchor_bank"):
        bundle[name] = loaded_new.get(name) or _default_builder(name)()
    return bundle


def _save_runtime_bundle(output_dir: Path, bundle: dict[str, dict[str, object]]) -> None:
    """Persist the attentional runtime bundle."""

    save_json(local_buffer_file(output_dir), bundle["local_buffer"])
    save_json(trigger_state_file(output_dir), bundle["trigger_state"])
    save_json(continuation_capsule_file(output_dir), bundle["continuation_capsule"])
    save_json(working_state_file(output_dir), bundle["working_state"])
    save_json(concept_registry_file(output_dir), bundle["concept_registry"])
    save_json(thread_trace_file(output_dir), bundle["thread_trace"])
    save_json(reflective_frames_file(output_dir), bundle["reflective_frames"])
    save_json(anchor_bank_file(output_dir), bundle["anchor_bank"])
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
        working_state_file(output_dir),
        concept_registry_file(output_dir),
        thread_trace_file(output_dir),
        local_buffer_file(output_dir),
        trigger_state_file(output_dir),
        continuation_capsule_file(output_dir),
        anchor_bank_file(output_dir),
        reflective_frames_file(output_dir),
        knowledge_activations_file(output_dir),
        move_history_file(output_dir),
        reaction_records_file(output_dir),
        reconsolidation_records_file(output_dir),
        resume_metadata_file(output_dir),
        read_audit_file(output_dir),
        unitization_audit_file(output_dir),
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


def _sentence_id(sentence: dict[str, object]) -> str:
    """Return the normalized sentence id for one sentence-like mapping."""

    return _clean_text(sentence.get("sentence_id"))


def _resolve_unit_sentences(
    sentences: list[dict[str, object]],
    *,
    unitize_decision: UnitizeDecision,
) -> list[dict[str, object]]:
    """Return the exact chosen coverage unit from the chapter sentence list."""

    start_id = _clean_text(unitize_decision.get("start_sentence_id"))
    end_id = _clean_text(unitize_decision.get("end_sentence_id"))
    if not start_id or not end_id:
        return []

    start_index = next((index for index, sentence in enumerate(sentences) if _sentence_id(sentence) == start_id), -1)
    end_index = next((index for index, sentence in enumerate(sentences) if _sentence_id(sentence) == end_id), -1)
    if start_index < 0 or end_index < start_index:
        return []
    return [dict(sentence) for sentence in sentences[start_index : end_index + 1]]


def _build_current_anchor_from_read_result(
    *,
    read_result: ReadUnitResult,
    express_result: ExpressResult | None,
    chosen_unit_sentences: list[dict[str, object]],
    focal_sentence: dict[str, object],
) -> dict[str, object]:
    """Build one deterministic current anchor from the authoritative read result."""

    evidence_list = [dict(item) for item in read_result.get("anchor_evidence", []) if isinstance(item, dict)]
    sentence_lookup = {
        _clean_text(sentence.get("sentence_id")): sentence
        for sentence in chosen_unit_sentences
        if isinstance(sentence, dict) and _clean_text(sentence.get("sentence_id"))
    }
    anchor_quote = ""
    anchor_sentence = None
    why_it_mattered = ""

    if evidence_list:
        first_evidence = evidence_list[0]
        anchor_quote = _clean_text(first_evidence.get("quote"))
        anchor_sentence = sentence_lookup.get(_clean_text(first_evidence.get("sentence_id")))
        why_it_mattered = _clean_text(first_evidence.get("why_it_matters"))

    if anchor_sentence is None and isinstance(express_result, dict):
        express_anchor_quote = _clean_text(express_result.get("anchor_quote"))
        if express_anchor_quote:
            for sentence in chosen_unit_sentences:
                sentence_text = _clean_text(sentence.get("text"))
                if express_anchor_quote in sentence_text:
                    anchor_sentence = sentence
                    anchor_quote = express_anchor_quote
                    break

    if anchor_sentence is None:
        raw_reaction = dict(read_result.get("raw_reaction", {})) if isinstance(read_result.get("raw_reaction"), dict) else {}
        raw_anchor_quote = _clean_text(raw_reaction.get("anchor_quote"))
        if raw_anchor_quote:
            for sentence in chosen_unit_sentences:
                sentence_text = _clean_text(sentence.get("text"))
                if raw_anchor_quote in sentence_text:
                    anchor_sentence = sentence
                    anchor_quote = raw_anchor_quote
                    break

    if anchor_sentence is None:
        anchor_sentence = focal_sentence
        if not anchor_quote:
            anchor_quote = _clean_text(focal_sentence.get("text"))

    return build_anchor_record(
        sentence_start_id=_clean_text(anchor_sentence.get("sentence_id")),
        sentence_end_id=_clean_text(anchor_sentence.get("sentence_id")),
        quote=anchor_quote or _clean_text(anchor_sentence.get("text")),
        locator=dict(anchor_sentence.get("locator", {})) if isinstance(anchor_sentence.get("locator"), dict) else {},
        anchor_kind="unit_evidence",
        why_it_mattered=why_it_mattered or _clean_text(read_result.get("unit_delta")) or _clean_text(read_result.get("local_understanding")),
    )


def _supporting_refs_for_express(
    *,
    ref_ids: list[str],
    carry_forward_context: dict[str, object],
    supplemental_context: dict[str, object] | None,
) -> list[dict[str, object]]:
    """Collect a narrow express-supporting ref packet from carry-forward and supplemental context."""

    requested_ref_ids = [_clean_text(ref_id) for ref_id in ref_ids if _clean_text(ref_id)]
    if not requested_ref_ids:
        return []

    refs_by_id: dict[str, dict[str, object]] = {}
    excerpt_by_id: dict[str, dict[str, object]] = {}
    for source in (carry_forward_context, supplemental_context or {}):
        if not isinstance(source, dict):
            continue
        for ref in source.get("refs", []):
            if not isinstance(ref, dict):
                continue
            ref_id = _clean_text(ref.get("ref_id"))
            if ref_id and ref_id not in refs_by_id:
                refs_by_id[ref_id] = dict(ref)
        for key in ("excerpts", "anchors", "concepts", "threads", "reactions", "moves", "reflective_items"):
            items = source.get(key, [])
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                ref_id = _clean_text(item.get("ref_id"))
                if ref_id and ref_id not in excerpt_by_id:
                    excerpt_by_id[ref_id] = dict(item)

    supporting_refs: list[dict[str, object]] = []
    for ref_id in requested_ref_ids:
        ref_payload = dict(refs_by_id.get(ref_id) or {})
        if ref_payload:
            detail = excerpt_by_id.get(ref_id)
            if isinstance(detail, dict):
                for field in ("excerpt_text", "sentence_ids", "chapter_ref", "anchor_id", "label", "kind", "summary"):
                    if field in detail and field not in ref_payload:
                        ref_payload[field] = detail.get(field)
            supporting_refs.append(ref_payload)
            continue
        detail = excerpt_by_id.get(ref_id)
        if isinstance(detail, dict):
            supporting_refs.append(dict(detail))
    return supporting_refs[:4]


def _move_type_from_route_decision(
    route_decision: NavigateRouteDecision,
    *,
    fallback_move_hint: str,
) -> str:
    """Project a route action back into the current move-history vocabulary."""

    action = _clean_text(route_decision.get("action"))
    if action == "bridge_back":
        return "bridge"
    if action == "reframe":
        return "reframe"
    if action == "continue":
        return "dwell"
    fallback = _clean_text(fallback_move_hint)
    return fallback or "advance"


def _build_runtime_continuation_capsule(
    *,
    chapter_ref: str,
    local_buffer: LocalBufferState,
    working_state: WorkingState,
    concept_registry: ConceptRegistryState,
    thread_trace: ThreadTraceState,
    reflective_frames: ReflectiveFramesState,
    anchor_bank: AnchorBankState,
    move_history: MoveHistoryState,
    reaction_records: ReactionRecordsState,
) -> dict[str, object]:
    """Build the persisted continuation capsule from the current live primary state."""

    carry_forward_context = build_carry_forward_context(
        chapter_ref=chapter_ref,
        current_unit_sentence_ids=[],
        local_buffer=local_buffer,
        working_state=working_state,
        concept_registry=concept_registry,
        thread_trace=thread_trace,
        reflective_frames=reflective_frames,
        anchor_bank=anchor_bank,
        move_history=move_history,
        reaction_records=reaction_records,
    )
    capsule = carry_forward_context.get("continuation_capsule", {})
    return dict(capsule) if isinstance(capsule, dict) else {}


def _run_read_with_context_loop(
    *,
    chapter: dict[str, object],
    book_document: BookDocument,
    chosen_unit_sentences: list[dict[str, object]],
    unitize_decision: UnitizeDecision,
    local_buffer: LocalBufferState,
    continuation_capsule: dict[str, object],
    working_state: WorkingState,
    concept_registry: ConceptRegistryState,
    thread_trace: ThreadTraceState,
    reflective_frames: ReflectiveFramesState,
    anchor_bank: AnchorBankState,
    knowledge_activations: KnowledgeActivationsState,
    move_history: MoveHistoryState,
    reaction_records: ReactionRecordsState,
    reader_policy: ReaderPolicy,
    output_language: str,
    output_dir: Path | None,
    book_title: str,
    author: str,
    chapter_id: int,
    chapter_ref: str,
) -> tuple[ReadUnitResult, dict[str, object] | None, list[dict[str, str]]]:
    """Run the authoritative read with budget-bounded supplemental-context looping."""

    carry_forward_context = build_carry_forward_context(
        chapter_ref=chapter_ref,
        current_unit_sentence_ids=[
            _clean_text(sentence.get("sentence_id"))
            for sentence in chosen_unit_sentences
            if _clean_text(sentence.get("sentence_id"))
        ],
        local_buffer=local_buffer,
        working_state=working_state,
        concept_registry=concept_registry,
        thread_trace=thread_trace,
        reflective_frames=reflective_frames,
        anchor_bank=anchor_bank,
        move_history=move_history,
        reaction_records=reaction_records,
        continuation_capsule=continuation_capsule,
    )
    llm_fallbacks: list[dict[str, str]] = []
    read_policy = dict(reader_policy.get("read", {})) if isinstance(reader_policy, dict) else {}
    recall_budget = max(0, int(read_policy.get("supplemental_context_budget", 4) or 4))
    emergency_cap = max(1, int(read_policy.get("supplemental_context_emergency_cap", 4) or 4))
    current_unit_sentence_ids = [
        _clean_text(sentence.get("sentence_id"))
        for sentence in chosen_unit_sentences
        if _clean_text(sentence.get("sentence_id"))
    ]
    try:
        first_read = read_unit(
            current_unit_sentences=chosen_unit_sentences,
            carry_forward_context=carry_forward_context,
            reader_policy=reader_policy,
            output_language=output_language,
            supplemental_context=None,
            output_dir=output_dir,
            book_title=book_title,
            author=author,
            chapter_title=_clean_text(chapter.get("title")),
        )
    except ReaderLLMError as exc:
        llm_fallbacks.append({"node": "read_unit", "problem_code": exc.problem_code})
        first_read = {
            "unit_delta": "",
            "pressure_signals": {
                "continuation_pressure": bool(unitize_decision.get("continuation_pressure")),
                "backward_pull": False,
                "frame_shift_pressure": False,
            },
            "express_signal": {
                "should_express": False,
                "focal_quote": "",
                "why_now": "",
                "supporting_ref_ids": [],
            },
            "local_understanding": "",
            "move_hint": "advance",
            "continuation_pressure": bool(unitize_decision.get("continuation_pressure")),
            "implicit_uptake": [],
            "anchor_evidence": [],
            "prior_material_use": {
                "materially_used": False,
                "explanation": "",
                "supporting_ref_ids": [],
            },
            "raw_reaction": None,
            "context_request": None,
        }

    final_read = first_read
    context_request = dict(first_read.get("context_request", {})) if isinstance(first_read.get("context_request"), dict) else None
    accumulated_supplemental_context: dict[str, object] | None = None
    supplemental_steps: list[dict[str, object]] = []
    supplemental_satisfied = False
    stop_reason = "no_supplemental_requested" if context_request is None else "supplemental_requested"
    budget_exhausted = False
    supplemental_rounds = 0

    while context_request is not None and supplemental_rounds < recall_budget and supplemental_rounds < emergency_cap:
        supplemental_rounds += 1
        resolved_context = resolve_context_request(
            context_request=context_request,
            carry_forward_context=carry_forward_context,
            book_document=book_document,
            chapter_ref=chapter_ref,
            anchor_bank=anchor_bank,
            concept_registry=concept_registry,
            thread_trace=thread_trace,
            reflective_frames=reflective_frames,
            move_history=move_history,
            reaction_records=reaction_records,
            reader_policy=reader_policy,
            current_unit_sentence_ids=current_unit_sentence_ids,
        )
        step: dict[str, object] = {
            "step_index": supplemental_rounds,
            "kind": _clean_text(context_request.get("kind")),
            "reason": _clean_text(context_request.get("reason")),
            "requested_anchor_ids": [
                _clean_text(item)
                for item in context_request.get("anchor_ids", [])
                if _clean_text(item)
            ],
            "requested_sentence_ids": [
                _clean_text(item)
                for item in context_request.get("sentence_ids", [])
                if _clean_text(item)
            ],
            "resolved_ref_ids": sorted(context_ref_ids(resolved_context)),
            "satisfied": resolved_context is not None,
        }
        supplemental_steps.append(step)
        if resolved_context is None:
            stop_reason = "supplemental_unsatisfied"
            break

        accumulated_supplemental_context = merge_supplemental_contexts(
            accumulated_supplemental_context,
            resolved_context,
        )
        supplemental_satisfied = True
        try:
            final_read = read_unit(
                current_unit_sentences=chosen_unit_sentences,
                carry_forward_context=carry_forward_context,
                reader_policy=reader_policy,
                output_language=output_language,
                supplemental_context=accumulated_supplemental_context,
                output_dir=output_dir,
                book_title=book_title,
                author=author,
                chapter_title=_clean_text(chapter.get("title")),
            )
        except ReaderLLMError as exc:
            llm_fallbacks.append({"node": "read_unit_supplemental", "problem_code": exc.problem_code})
            stop_reason = "supplemental_read_fallback"
            break

        context_request = (
            dict(final_read.get("context_request", {}))
            if isinstance(final_read.get("context_request"), dict)
            else None
        )
        if context_request is None:
            stop_reason = "read_complete"

    if context_request is not None and supplemental_rounds >= min(recall_budget, emergency_cap):
        budget_exhausted = True
        stop_reason = "budget_exhausted"

    persist_read_audit(
        output_dir,
        chapter_id=chapter_id,
        chapter_ref=chapter_ref,
        unitize_decision=unitize_decision,
        carry_forward_context=carry_forward_context,
        context_request=context_request,
        supplemental_context=accumulated_supplemental_context,
        supplemental_satisfied=supplemental_satisfied,
        supplemental_steps=supplemental_steps,
        stop_reason=stop_reason,
        budget_exhausted=budget_exhausted,
        read_result=final_read,
        llm_fallbacks=llm_fallbacks,
    )
    return final_read, accumulated_supplemental_context, llm_fallbacks


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
        raise ValueError("attentional_v2 does not support the retired legacy book_analysis mode.")

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
        working_state: WorkingState = bundle["working_state"]  # type: ignore[assignment]
        concept_registry: ConceptRegistryState = bundle["concept_registry"]  # type: ignore[assignment]
        thread_trace: ThreadTraceState = bundle["thread_trace"]  # type: ignore[assignment]
        reflective_frames: ReflectiveFramesState = bundle["reflective_frames"]  # type: ignore[assignment]
        anchor_bank: AnchorBankState = bundle["anchor_bank"]  # type: ignore[assignment]
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

            cursor = start_index
            while cursor < len(sentences):
                sentence = sentences[cursor]
                sentence_id = _clean_text(sentence.get("sentence_id"))
                local_buffer, trigger_state = process_sentence_intake(
                    sentence,
                    local_buffer=local_buffer,
                    working_state=working_state,
                    concept_registry=concept_registry,
                    thread_trace=thread_trace,
                    anchor_bank=anchor_bank,
                )
                save_json(trigger_state_file(output_dir), trigger_state)
                preview_sentences, preview_range = build_unitize_preview(
                    chapter_sentences=sentences,
                    current_sentence_id=sentence_id,
                )
                navigation_context = build_navigation_context(
                    chapter_ref=chapter_ref,
                    current_sentence_id=sentence_id,
                    local_buffer=local_buffer,
                    trigger_state=trigger_state,
                    working_state=working_state,
                    concept_registry=concept_registry,
                    thread_trace=thread_trace,
                    reflective_frames=reflective_frames,
                    anchor_bank=anchor_bank,
                    move_history=move_history,
                    reaction_records=reaction_records,
                )
                unitize_decision = navigate_unitize(
                    current_sentence=sentence,
                    preview_sentences=preview_sentences,
                    navigation_context=navigation_context,
                    reader_policy=reader_policy,
                    output_language=provisioned.output_language,
                    output_dir=output_dir,
                    book_title=provisioned.title,
                    author=provisioned.author,
                    chapter_title=_clean_text(chapter.get("title")),
                )
                chosen_unit_sentences = _resolve_unit_sentences(sentences, unitize_decision=unitize_decision)
                if not chosen_unit_sentences:
                    chosen_unit_sentences = [dict(sentence)]
                    unitize_decision = {
                        "start_sentence_id": sentence_id,
                        "end_sentence_id": sentence_id,
                        "preview_range": preview_range,
                        "boundary_type": "paragraph_end",
                        "evidence_sentence_ids": [sentence_id],
                        "reason": "unitize_resolve_fallback",
                        "continuation_pressure": False,
                    }

                for later_sentence in chosen_unit_sentences[1:]:
                    local_buffer, trigger_state = process_sentence_intake(
                        later_sentence,
                        local_buffer=local_buffer,
                        working_state=working_state,
                        concept_registry=concept_registry,
                        thread_trace=thread_trace,
                        anchor_bank=anchor_bank,
                    )
                    save_json(trigger_state_file(output_dir), trigger_state)

                persist_unitization_audit(
                    output_dir,
                    chapter_id=chapter_id,
                    chapter_ref=chapter_ref,
                    unitize_decision=unitize_decision,
                )

                focal_sentence = chosen_unit_sentences[-1]
                focal_sentence_id = _clean_text(focal_sentence.get("sentence_id"))
                current_activity = _current_activity(
                    chapter_id=chapter_id,
                    chapter_ref=chapter_ref,
                    sentence=focal_sentence,
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
                        current_segment_ref=_compatibility_section_ref(chapter_id, focal_sentence),
                        current_reading_activity=current_activity,
                        current_phase_step="reading",
                        resume_available=True,
                        last_checkpoint_at=load_runtime_shell(runtime_artifacts.runtime_shell_file(output_dir)).get("last_checkpoint_at"),
                    ),
                )

                read_result, supplemental_context, read_fallbacks = _run_read_with_context_loop(
                    chapter=chapter,
                    book_document=provisioned.book_document,
                    chosen_unit_sentences=chosen_unit_sentences,
                    unitize_decision=unitize_decision,
                    local_buffer=local_buffer,
                    continuation_capsule=dict(bundle.get("continuation_capsule", {})),
                    working_state=working_state,
                    concept_registry=concept_registry,
                    thread_trace=thread_trace,
                    reflective_frames=reflective_frames,
                    anchor_bank=anchor_bank,
                    knowledge_activations=knowledge_activations,
                    move_history=move_history,
                    reaction_records=reaction_records,
                    reader_policy=reader_policy,
                    output_language=provisioned.output_language,
                    output_dir=output_dir,
                    book_title=provisioned.title,
                    author=provisioned.author,
                    chapter_id=chapter_id,
                    chapter_ref=chapter_ref,
                )
                carry_forward_context = build_carry_forward_context(
                    chapter_ref=chapter_ref,
                    current_unit_sentence_ids=[
                        _clean_text(sentence.get("sentence_id"))
                        for sentence in chosen_unit_sentences
                        if _clean_text(sentence.get("sentence_id"))
                    ],
                    local_buffer=local_buffer,
                    working_state=working_state,
                    concept_registry=concept_registry,
                    thread_trace=thread_trace,
                    reflective_frames=reflective_frames,
                    anchor_bank=anchor_bank,
                    move_history=move_history,
                    reaction_records=reaction_records,
                    continuation_capsule=dict(bundle.get("continuation_capsule", {})),
                )
                express_signal = dict(read_result.get("express_signal") or {})
                supporting_refs = _supporting_refs_for_express(
                    ref_ids=[
                        _clean_text(ref_id)
                        for ref_id in express_signal.get("supporting_ref_ids", [])
                        if isinstance(express_signal.get("supporting_ref_ids"), list) and _clean_text(ref_id)
                    ],
                    carry_forward_context=carry_forward_context,
                    supplemental_context=supplemental_context,
                )
                express_result: ExpressResult | None = None
                if bool(express_signal.get("should_express")):
                    try:
                        express_result = express_unit(
                            current_unit_sentences=chosen_unit_sentences,
                            express_signal=express_signal,
                            supporting_refs=supporting_refs,
                            reader_policy=reader_policy,
                            output_language=provisioned.output_language,
                            output_dir=output_dir,
                            book_title=provisioned.title,
                            author=provisioned.author,
                            chapter_title=_clean_text(chapter.get("title")),
                        )
                    except ReaderLLMError as exc:
                        express_result = {
                            "decision": "withhold",
                            "anchor_quote": "",
                            "content": "",
                            "prior_link": None,
                            "outside_link": None,
                            "search_intent": None,
                        }
                        append_activity_event(
                            output_dir,
                            {
                                "type": "llm_fallback",
                                "stream": "mindstream",
                                "kind": "transition",
                                "visibility": "hidden",
                                "message": "Express fallback for express_unit.",
                                "chapter_id": chapter_id,
                                "chapter_ref": chapter_ref,
                                "segment_ref": _compatibility_section_ref(chapter_id, focal_sentence),
                                "reading_locus": _reading_locus(chapter_id, chapter_ref, focal_sentence, local_buffer),
                                "current_excerpt": _clean_text(focal_sentence.get("text"))[:220],
                                "problem_code": exc.problem_code,
                            },
                        )
                route_decision: NavigateRouteDecision = navigate_route(read_result=read_result)
                for fallback in read_fallbacks:
                    if not isinstance(fallback, dict):
                        continue
                    append_activity_event(
                        output_dir,
                        {
                            "type": "llm_fallback",
                            "stream": "mindstream",
                            "kind": "transition",
                            "visibility": "hidden",
                            "message": f"Read fallback for {_clean_text(fallback.get('node')) or 'unknown_node'}.",
                            "chapter_id": chapter_id,
                            "chapter_ref": chapter_ref,
                            "segment_ref": _compatibility_section_ref(chapter_id, focal_sentence),
                            "reading_locus": _reading_locus(chapter_id, chapter_ref, focal_sentence, local_buffer),
                            "current_excerpt": _clean_text(focal_sentence.get("text"))[:220],
                            "problem_code": _clean_text(fallback.get("problem_code")),
                        },
                    )
                working_state = apply_working_state_operations(
                    working_state,
                    read_result.get("implicit_uptake", []),
                )
                concept_registry = apply_concept_registry_operations(
                    concept_registry,
                    read_result.get("implicit_uptake", []),
                )
                thread_trace = apply_thread_trace_operations(
                    thread_trace,
                    read_result.get("implicit_uptake", []),
                )
                anchor_bank = apply_anchor_bank_operations(anchor_bank, read_result.get("implicit_uptake", []))
                knowledge_activations = apply_activation_operations(
                    knowledge_activations,
                    read_result.get("implicit_uptake", []),
                    current_sentence_id=focal_sentence_id,
                    reader_policy=reader_policy,
                )

                chosen_move = _move_type_from_route_decision(
                    route_decision,
                    fallback_move_hint=_clean_text(read_result.get("move_hint")),
                )
                if chosen_move in {"advance", "dwell", "bridge", "reframe"}:
                    move_history = append_move(
                        move_history,
                        {
                            "move_id": f"move:{sentence_id}:{chosen_move}",
                            "move_type": chosen_move,
                            "reason": _clean_text(route_decision.get("reason")) or "read route",
                            "source_sentence_id": focal_sentence_id,
                            "target_anchor_id": _clean_text(route_decision.get("target_anchor_id")),
                            "target_sentence_id": _clean_text(route_decision.get("target_sentence_id")),
                            "created_at": _timestamp(),
                        },
                    )

                emitted_reaction: AnchoredReactionRecord | None = None
                current_anchor = _build_current_anchor_from_read_result(
                    read_result=read_result,
                    express_result=express_result,
                    chosen_unit_sentences=chosen_unit_sentences,
                    focal_sentence=focal_sentence,
                )

                if route_decision.get("persist_raw_reaction"):
                    chapter_reaction_count = len(reaction_records_for_chapter(reaction_records, chapter_ref=chapter_ref))
                    emitted_reaction = build_reaction_record_from_express_result(
                        express_result=express_result or {},
                        primary_anchor=current_anchor,
                        chapter_id=chapter_id,
                        chapter_ref=chapter_ref,
                        emitted_at_sentence_id=focal_sentence_id,
                        compatibility_section_ref=_compatibility_section_ref(chapter_id, focal_sentence),
                        ordinal=chapter_reaction_count + 1,
                    )
                    if emitted_reaction is None and isinstance(read_result.get("raw_reaction"), dict):
                        emitted_reaction = build_reaction_record(
                            reaction=dict(read_result.get("raw_reaction", {})),
                            primary_anchor=current_anchor,
                            chapter_id=chapter_id,
                            chapter_ref=chapter_ref,
                            emitted_at_sentence_id=focal_sentence_id,
                            compatibility_section_ref=_compatibility_section_ref(chapter_id, focal_sentence),
                            ordinal=chapter_reaction_count + 1,
                            record_source="legacy_fallback",
                        )
                    if emitted_reaction is not None:
                        anchor_bank = upsert_anchor_record(anchor_bank, current_anchor)  # type: ignore[assignment]
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
                                "segment_ref": _compatibility_section_ref(chapter_id, focal_sentence),
                                "anchor_quote": _clean_text(emitted_reaction.get("primary_anchor", {}).get("quote")),
                                "reading_locus": _reading_locus(chapter_id, chapter_ref, focal_sentence, local_buffer),
                                "move_type": chosen_move or None,
                                "active_reaction_id": _clean_text(emitted_reaction.get("reaction_id")),
                                "reaction_types": [compat_reaction_family(emitted_reaction)],
                                "current_excerpt": _clean_text(focal_sentence.get("text"))[:220],
                            },
                        )

                if route_decision.get("action") == "bridge_back":
                    candidate_set = generate_candidate_set(
                        provisioned.book_document,
                        current_sentence_id=focal_sentence_id,
                        current_text=_clean_text(focal_sentence.get("text")),
                        anchor_bank=anchor_bank,
                        concept_registry=concept_registry,
                        thread_trace=thread_trace,
                    )
                    phase5 = run_phase5_bridge_cycle(
                        current_span_sentences=chosen_unit_sentences,
                        candidate_set=candidate_set,
                        working_state=working_state,
                        concept_registry=concept_registry,
                        thread_trace=thread_trace,
                        anchor_bank=anchor_bank,
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
                    working_state = phase5["working_state"]  # type: ignore[assignment]
                    concept_registry = phase5["concept_registry"]  # type: ignore[assignment]
                    thread_trace = phase5["thread_trace"]  # type: ignore[assignment]
                    anchor_bank = phase5["anchor_bank"]  # type: ignore[assignment]
                    knowledge_activations = phase5["knowledge_activations"]  # type: ignore[assignment]
                    move_history = phase5["move_history"]  # type: ignore[assignment]
                    bridge_result = dict(phase5.get("bridge_result") or {})
                    primary_attribution = dict(bridge_result.get("primary_attribution") or {})
                    if (
                        _clean_text(bridge_result.get("decision")) == "bridge"
                        and (
                            _clean_text(primary_attribution.get("relation_explanation"))
                            or _clean_text(bridge_result.get("reason"))
                        )
                    ):
                        append_activity_event(
                            output_dir,
                            {
                                "type": "bridge_resolved",
                                "stream": "mindstream",
                                "kind": "thought",
                                "visibility": "default",
                                "message": _clean_text(primary_attribution.get("relation_explanation"))
                                or _clean_text(bridge_result.get("reason")),
                                "chapter_id": chapter_id,
                                "chapter_ref": chapter_ref,
                                "segment_ref": _compatibility_section_ref(chapter_id, focal_sentence),
                                "anchor_quote": _clean_text(primary_attribution.get("target_quote")),
                                "reading_locus": _reading_locus(chapter_id, chapter_ref, focal_sentence, local_buffer),
                                "move_type": "bridge",
                                "current_excerpt": _clean_text(primary_attribution.get("current_quote"))
                                or _clean_text(focal_sentence.get("text"))[:220],
                            },
                        )

                if route_decision.get("close_current_unit", True):
                    meaning_units_in_chapter.append(
                        {
                            "sentence_ids": [_clean_text(item.get("sentence_id")) for item in chosen_unit_sentences if _clean_text(item.get("sentence_id"))],
                            "summary": _clean_text(read_result.get("local_understanding")),
                            "dominant_move": _clean_text(read_result.get("move_hint")),
                        }
                    )
                    local_buffer = close_local_meaning_unit(local_buffer)

                bundle.update(
                    {
                        "local_buffer": local_buffer,
                        "trigger_state": trigger_state,
                        "continuation_capsule": _build_runtime_continuation_capsule(
                            chapter_ref=chapter_ref,
                            local_buffer=local_buffer,
                            working_state=working_state,
                            concept_registry=concept_registry,
                            thread_trace=thread_trace,
                            reflective_frames=reflective_frames,
                            anchor_bank=anchor_bank,
                            move_history=move_history,
                            reaction_records=reaction_records,
                        ),
                        "working_state": working_state,
                        "concept_registry": concept_registry,
                        "thread_trace": thread_trace,
                        "reflective_frames": reflective_frames,
                        "anchor_bank": anchor_bank,
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
                cursor += len(chosen_unit_sentences)

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
                working_state=working_state,
                concept_registry=concept_registry,
                thread_trace=thread_trace,
                reflective_frames=reflective_frames,
                anchor_bank=anchor_bank,
                knowledge_activations=knowledge_activations,
                reaction_records=reaction_records,
                reader_policy=reader_policy,
                output_language=provisioned.output_language,
                output_dir=output_dir,
                persist_compatibility_projection=True,
                book_title=provisioned.title,
                author=provisioned.author,
            )
            working_state = phase6["working_state"]  # type: ignore[assignment]
            concept_registry = phase6["concept_registry"]  # type: ignore[assignment]
            thread_trace = phase6["thread_trace"]  # type: ignore[assignment]
            reflective_frames = phase6["reflective_frames"]  # type: ignore[assignment]
            anchor_bank = phase6["anchor_bank"]  # type: ignore[assignment]
            knowledge_activations = phase6["knowledge_activations"]  # type: ignore[assignment]
            reaction_records = phase6["reaction_records"]  # type: ignore[assignment]
            bundle.update(
                {
                    "local_buffer": local_buffer,
                    "trigger_state": trigger_state,
                    "continuation_capsule": _build_runtime_continuation_capsule(
                        chapter_ref=chapter_ref,
                        local_buffer=local_buffer,
                        working_state=working_state,
                        concept_registry=concept_registry,
                        thread_trace=thread_trace,
                        reflective_frames=reflective_frames,
                        anchor_bank=anchor_bank,
                        move_history=move_history,
                        reaction_records=reaction_records,
                    ),
                    "working_state": working_state,
                    "concept_registry": concept_registry,
                    "thread_trace": thread_trace,
                    "reflective_frames": reflective_frames,
                    "anchor_bank": anchor_bank,
                    "knowledge_activations": knowledge_activations,
                    "move_history": move_history,
                    "reaction_records": reaction_records,
                    "reconsolidation_records": reconsolidation_records,
                    "reader_policy": reader_policy,
                    "resume_metadata": resume_metadata,
                }
            )
            _save_runtime_bundle(output_dir, bundle)
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

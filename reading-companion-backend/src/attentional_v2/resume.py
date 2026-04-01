"""Phase 7 checkpointing, continuity persistence, and resume helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from src.reading_core import BookDocument
from src.reading_core.runtime_contracts import ResumeKind, RuntimeArtifactRefs, SharedRunCursor
from src.reading_runtime.artifacts import runtime_shell_file
from src.reading_runtime.shell_state import (
    build_checkpoint_summary,
    empty_cursor,
    ensure_runtime_shell,
    load_runtime_shell,
    save_runtime_shell,
    write_checkpoint_summary,
)

from .observability import emit_checkpoint_observability, emit_resume_observability, observability_mode
from .schemas import (
    ATTENTIONAL_V2_MECHANISM_VERSION,
    ATTENTIONAL_V2_POLICY_VERSION,
    ATTENTIONAL_V2_SCHEMA_VERSION,
    FullCheckpointState,
    LocalBufferSentence,
    LocalBufferState,
    LocalContinuityState,
    ReaderPolicy,
    ResumeMetadataState,
    TriggerState,
    build_empty_anchor_memory,
    build_empty_knowledge_activations,
    build_empty_local_buffer,
    build_empty_local_continuity,
    build_empty_move_history,
    build_empty_reaction_records,
    build_empty_reconsolidation_records,
    build_empty_reflective_summaries,
    build_empty_resume_metadata,
    build_empty_trigger_state,
    build_empty_working_pressure,
    build_default_reader_policy,
)
from .storage import (
    ATTENTIONAL_V2_MECHANISM_KEY,
    anchor_memory_file,
    full_checkpoint_file,
    knowledge_activations_file,
    load_json,
    local_buffer_file,
    local_continuity_file,
    move_history_file,
    reaction_records_file,
    reader_policy_file,
    reconsolidation_records_file,
    reflective_summaries_file,
    resume_metadata_file,
    save_json,
    trigger_state_file,
    working_pressure_file,
)


def _timestamp() -> str:
    """Return a stable UTC timestamp."""

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _clean_text(value: object) -> str:
    """Return one normalized string."""

    return str(value or "").strip()


def _load_or_default(path: Path, builder: Callable[[], dict[str, object]]) -> dict[str, object]:
    """Load one JSON artifact or return a builder-backed default."""

    if path.exists():
        return load_json(path)
    return builder()


def _state_builders() -> dict[str, Callable[[], dict[str, object]]]:
    """Return builder functions for all Phase 7-restored runtime states."""

    return {
        "local_buffer": lambda: build_empty_local_buffer(mechanism_version=ATTENTIONAL_V2_MECHANISM_VERSION),
        "local_continuity": lambda: build_empty_local_continuity(mechanism_version=ATTENTIONAL_V2_MECHANISM_VERSION),
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


def _state_paths(output_dir: Path) -> dict[str, Path]:
    """Return all Phase 7 runtime-state paths."""

    return {
        "local_buffer": local_buffer_file(output_dir),
        "local_continuity": local_continuity_file(output_dir),
        "trigger_state": trigger_state_file(output_dir),
        "working_pressure": working_pressure_file(output_dir),
        "anchor_memory": anchor_memory_file(output_dir),
        "reflective_summaries": reflective_summaries_file(output_dir),
        "knowledge_activations": knowledge_activations_file(output_dir),
        "move_history": move_history_file(output_dir),
        "reaction_records": reaction_records_file(output_dir),
        "reconsolidation_records": reconsolidation_records_file(output_dir),
        "reader_policy": reader_policy_file(output_dir),
        "resume_metadata": resume_metadata_file(output_dir),
    }


def build_shared_cursor(
    *,
    chapter_id: int | None,
    chapter_ref: str,
    current_sentence_id: str = "",
    open_meaning_unit_sentence_ids: list[str] | None = None,
) -> SharedRunCursor:
    """Build one mechanism-neutral shared cursor from the local continuity state."""

    cursor: SharedRunCursor = {
        "position_kind": "chapter",
        "chapter_id": chapter_id,
        "chapter_ref": _clean_text(chapter_ref),
    }
    current_sentence_id = _clean_text(current_sentence_id)
    if not current_sentence_id:
        return cursor
    cursor["position_kind"] = "sentence"
    cursor["sentence_id"] = current_sentence_id
    open_ids = [str(sentence_id or "") for sentence_id in open_meaning_unit_sentence_ids or [] if str(sentence_id or "")]
    if open_ids:
        cursor["position_kind"] = "span"
        cursor["span_start_sentence_id"] = open_ids[0]
        cursor["span_end_sentence_id"] = open_ids[-1]
    return cursor


def capture_local_continuity(
    *,
    chapter_id: int | None,
    chapter_ref: str,
    local_buffer: LocalBufferState,
    mechanism_version: str = ATTENTIONAL_V2_MECHANISM_VERSION,
) -> LocalContinuityState:
    """Project the heavier local buffer into the compact Phase 7 continuity envelope."""

    recent_sentence_ids = [
        _clean_text(sentence.get("sentence_id"))
        for sentence in local_buffer.get("recent_sentences", [])
        if isinstance(sentence, dict) and _clean_text(sentence.get("sentence_id"))
    ]
    recent_meaning_units = [
        [_clean_text(sentence_id) for sentence_id in unit if _clean_text(sentence_id)]
        for unit in local_buffer.get("recent_meaning_units", [])
        if isinstance(unit, list)
    ]
    return {
        "schema_version": ATTENTIONAL_V2_SCHEMA_VERSION,
        "mechanism_version": mechanism_version,
        "updated_at": _timestamp(),
        "chapter_id": chapter_id,
        "chapter_ref": _clean_text(chapter_ref),
        "current_sentence_id": _clean_text(local_buffer.get("current_sentence_id")),
        "current_sentence_index": int(local_buffer.get("current_sentence_index", 0) or 0),
        "recent_sentence_ids": recent_sentence_ids,
        "open_meaning_unit_sentence_ids": [
            _clean_text(sentence_id)
            for sentence_id in local_buffer.get("open_meaning_unit_sentence_ids", [])
            if _clean_text(sentence_id)
        ],
        "recent_meaning_units": recent_meaning_units,
        "last_meaning_unit_closed_at_sentence_id": _clean_text(local_buffer.get("last_meaning_unit_closed_at_sentence_id")),
        "is_reconstructed": bool(local_buffer.get("is_reconstructed", False)),
        "reconstructed_from_checkpoint_id": local_buffer.get("reconstructed_from_checkpoint_id"),
        "last_resume_kind": local_buffer.get("last_resume_kind"),
    }


def persist_reading_position(
    output_dir: Path,
    *,
    chapter_id: int | None,
    chapter_ref: str,
    local_buffer: LocalBufferState,
    active_artifact_refs: RuntimeArtifactRefs | None = None,
    status: str | None = None,
    phase: str | None = None,
) -> dict[str, object]:
    """Persist the current local buffer, compact continuity state, and shared cursor."""

    save_json(local_buffer_file(output_dir), local_buffer)
    continuity = capture_local_continuity(
        chapter_id=chapter_id,
        chapter_ref=chapter_ref,
        local_buffer=local_buffer,
        mechanism_version=str(local_buffer.get("mechanism_version", "") or ATTENTIONAL_V2_MECHANISM_VERSION),
    )
    save_json(local_continuity_file(output_dir), continuity)

    shell = ensure_runtime_shell(
        output_dir,
        mechanism_key=ATTENTIONAL_V2_MECHANISM_KEY,
        mechanism_version=str(local_buffer.get("mechanism_version", "") or ATTENTIONAL_V2_MECHANISM_VERSION),
        policy_version=ATTENTIONAL_V2_POLICY_VERSION,
    )
    shell["cursor"] = build_shared_cursor(
        chapter_id=chapter_id,
        chapter_ref=chapter_ref,
        current_sentence_id=str(continuity.get("current_sentence_id", "") or ""),
        open_meaning_unit_sentence_ids=list(continuity.get("open_meaning_unit_sentence_ids", [])),
    )
    if active_artifact_refs is not None:
        shell["active_artifact_refs"] = dict(active_artifact_refs)
    if status is not None:
        shell["status"] = status
    if phase is not None:
        shell["phase"] = phase
    shell["updated_at"] = _timestamp()
    save_runtime_shell(runtime_shell_file(output_dir), shell)
    return {"cursor": shell["cursor"], "local_continuity": continuity, "runtime_shell": shell}


def _load_runtime_bundle(output_dir: Path) -> dict[str, dict[str, object]]:
    """Load all Phase 7 runtime files with defaults for absent artifacts."""

    builders = _state_builders()
    bundle: dict[str, dict[str, object]] = {}
    for name, path in _state_paths(output_dir).items():
        builder = builders[name]
        bundle[name] = _load_or_default(path, builder)
    return bundle


def _save_runtime_bundle(output_dir: Path, bundle: dict[str, dict[str, object]]) -> None:
    """Persist all Phase 7 runtime files from one bundle."""

    for name, path in _state_paths(output_dir).items():
        payload = bundle.get(name)
        if payload is not None:
            save_json(path, payload)


def load_full_checkpoint(output_dir: Path, checkpoint_id: str | None = None) -> FullCheckpointState | None:
    """Load one full checkpoint by id or the shell's latest pointer."""

    selected = _clean_text(checkpoint_id)
    if not selected:
        shell = load_runtime_shell(runtime_shell_file(output_dir))
        selected = _clean_text(shell.get("last_checkpoint_id"))
    if not selected:
        return None
    path = full_checkpoint_file(output_dir, selected)
    if not path.exists():
        return None
    return load_json(path)  # type: ignore[return-value]


def write_full_checkpoint(
    output_dir: Path,
    *,
    checkpoint_id: str,
    resume_kind: ResumeKind = "warm_resume",
    checkpoint_reason: str = "manual",
) -> FullCheckpointState:
    """Persist a full mechanism checkpoint plus the shared thin checkpoint summary."""

    bundle = _load_runtime_bundle(output_dir)
    shell = load_runtime_shell(runtime_shell_file(output_dir))
    continuity = bundle["local_continuity"]
    cursor = dict(shell.get("cursor", {})) or build_shared_cursor(
        chapter_id=continuity.get("chapter_id"),  # type: ignore[arg-type]
        chapter_ref=str(continuity.get("chapter_ref", "") or ""),
        current_sentence_id=str(continuity.get("current_sentence_id", "") or ""),
        open_meaning_unit_sentence_ids=list(continuity.get("open_meaning_unit_sentence_ids", [])),
    )
    active_artifact_refs = dict(shell.get("active_artifact_refs", {}))
    reaction_records = bundle["reaction_records"]
    visible_reaction_ids = [
        _clean_text(record.get("reaction_id"))
        for record in reaction_records.get("records", [])
        if isinstance(record, dict) and _clean_text(record.get("reaction_id"))
    ]
    summary = build_checkpoint_summary(
        checkpoint_id=checkpoint_id,
        mechanism_key=str(shell.get("mechanism_key", "") or "attentional_v2"),
        mechanism_version=str(shell.get("mechanism_version", "") or ATTENTIONAL_V2_MECHANISM_VERSION),
        policy_version=str(shell.get("policy_version", "") or ATTENTIONAL_V2_POLICY_VERSION),
        observability_mode=observability_mode(bundle["reader_policy"]),
        resume_kind=resume_kind,
    )
    summary["cursor"] = cursor
    summary["active_artifact_refs"] = active_artifact_refs
    summary["visible_reaction_ids"] = visible_reaction_ids
    write_checkpoint_summary(output_dir, summary)

    checkpoint: FullCheckpointState = {
        "schema_version": ATTENTIONAL_V2_SCHEMA_VERSION,
        "mechanism_version": str(shell.get("mechanism_version", "") or ATTENTIONAL_V2_MECHANISM_VERSION),
        "policy_version": str(shell.get("policy_version", "") or ATTENTIONAL_V2_POLICY_VERSION),
        "checkpoint_id": checkpoint_id,
        "created_at": str(summary.get("created_at", "") or _timestamp()),
        "checkpoint_reason": checkpoint_reason,
        "resume_kind": resume_kind,
        "cursor": cursor,
        "active_artifact_refs": active_artifact_refs,
        "visible_reaction_ids": visible_reaction_ids,
        "local_buffer": bundle["local_buffer"],  # type: ignore[typeddict-item]
        "local_continuity": continuity,  # type: ignore[typeddict-item]
        "trigger_state": bundle["trigger_state"],  # type: ignore[typeddict-item]
        "working_pressure": bundle["working_pressure"],  # type: ignore[typeddict-item]
        "anchor_memory": bundle["anchor_memory"],  # type: ignore[typeddict-item]
        "reflective_summaries": bundle["reflective_summaries"],  # type: ignore[typeddict-item]
        "knowledge_activations": bundle["knowledge_activations"],  # type: ignore[typeddict-item]
        "move_history": bundle["move_history"],  # type: ignore[typeddict-item]
        "reaction_records": reaction_records,  # type: ignore[typeddict-item]
        "reconsolidation_records": bundle["reconsolidation_records"],  # type: ignore[typeddict-item]
        "reader_policy": bundle["reader_policy"],  # type: ignore[typeddict-item]
        "resume_metadata": bundle["resume_metadata"],  # type: ignore[typeddict-item]
    }
    save_json(full_checkpoint_file(output_dir, checkpoint_id), checkpoint)

    shell["cursor"] = cursor
    shell["observability_mode"] = observability_mode(bundle["reader_policy"])
    shell["resume_available"] = True
    shell["last_checkpoint_id"] = checkpoint_id
    shell["last_checkpoint_at"] = checkpoint["created_at"]
    shell["updated_at"] = _timestamp()
    save_runtime_shell(runtime_shell_file(output_dir), shell)

    resume_metadata = dict(bundle["resume_metadata"])
    resume_metadata["updated_at"] = _timestamp()
    resume_metadata["resume_available"] = True
    resume_metadata["default_resume_kind"] = str(bundle["reader_policy"].get("resume", {}).get("default_mode", "warm_resume"))  # type: ignore[assignment]
    resume_metadata["last_checkpoint_id"] = checkpoint_id
    resume_metadata["last_checkpoint_at"] = checkpoint["created_at"]
    save_json(resume_metadata_file(output_dir), resume_metadata)
    emit_checkpoint_observability(
        output_dir,
        checkpoint,
        reader_policy=bundle["reader_policy"],  # type: ignore[arg-type]
    )
    return checkpoint


def validate_resume_compatibility(
    checkpoint: FullCheckpointState,
    *,
    book_document: BookDocument,
    current_mechanism_version: str = ATTENTIONAL_V2_MECHANISM_VERSION,
    current_policy_version: str = ATTENTIONAL_V2_POLICY_VERSION,
) -> dict[str, object]:
    """Check whether one checkpoint can be used against the current mechanism and book substrate."""

    issues: list[str] = []
    if _clean_text(checkpoint.get("mechanism_version")) != _clean_text(current_mechanism_version):
        issues.append("mechanism_version_mismatch")
    if _clean_text(checkpoint.get("policy_version")) != _clean_text(current_policy_version):
        issues.append("policy_version_mismatch")

    cursor = checkpoint.get("cursor", {})
    chapter_id = int(cursor.get("chapter_id", 0) or 0)
    chapter = next(
        (item for item in book_document.get("chapters", []) if isinstance(item, dict) and int(item.get("id", 0) or 0) == chapter_id),
        None,
    )
    if chapter is None:
        issues.append("chapter_missing")
    sentence_id = _clean_text(cursor.get("sentence_id"))
    if sentence_id and chapter is not None:
        sentence_ids = {
            _clean_text(sentence.get("sentence_id"))
            for sentence in chapter.get("sentences", [])
            if isinstance(sentence, dict)
        }
        if sentence_id not in sentence_ids:
            issues.append("sentence_missing")

    return {"compatible": not issues, "issues": issues}


def _chapter_sentences(book_document: BookDocument, *, chapter_id: int | None, chapter_ref: str) -> list[dict[str, object]]:
    """Return the current chapter's sentence inventory."""

    selected_id = int(chapter_id or 0)
    for chapter in book_document.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        if selected_id > 0 and int(chapter.get("id", 0) or 0) == selected_id:
            return [dict(sentence) for sentence in chapter.get("sentences", []) if isinstance(sentence, dict)]
        if not selected_id and _clean_text(chapter.get("title")) == _clean_text(chapter_ref):
            return [dict(sentence) for sentence in chapter.get("sentences", []) if isinstance(sentence, dict)]
    return []


def _window_sentence_records(
    *,
    book_document: BookDocument,
    continuity: LocalContinuityState,
    resume_kind: ResumeKind,
    resume_policy: dict[str, object],
) -> list[dict[str, object]]:
    """Select the sentence window to reread for the requested non-warm resume mode."""

    if resume_kind == "warm_resume":
        return []

    sentences = _chapter_sentences(
        book_document,
        chapter_id=continuity.get("chapter_id"),
        chapter_ref=str(continuity.get("chapter_ref", "") or ""),
    )
    if not sentences:
        return []

    current_sentence_id = _clean_text(continuity.get("current_sentence_id"))
    if not current_sentence_id:
        recent_ids = [sentence_id for sentence_id in continuity.get("recent_sentence_ids", []) if _clean_text(sentence_id)]
        current_sentence_id = _clean_text(recent_ids[-1] if recent_ids else "")
    if not current_sentence_id:
        return []

    index_by_id = {
        _clean_text(sentence.get("sentence_id")): index
        for index, sentence in enumerate(sentences)
        if _clean_text(sentence.get("sentence_id"))
    }
    current_index = index_by_id.get(current_sentence_id)
    if current_index is None:
        return []

    if resume_kind == "cold_resume":
        target = max(1, int(resume_policy.get("cold_resume_target_sentences", 8) or 8))
        cap = max(target, int(resume_policy.get("cold_resume_max_sentences", 12) or 12))
        start = max(0, current_index - target + 1)
        open_indices = [
            index_by_id[sentence_id]
            for sentence_id in continuity.get("open_meaning_unit_sentence_ids", [])
            if _clean_text(sentence_id) in index_by_id
        ]
        if open_indices and min(open_indices) < start:
            start = min(open_indices)
        if current_index - start + 1 > cap:
            start = max(0, current_index - cap + 1)
        return sentences[start : current_index + 1]

    target = max(1, int(resume_policy.get("reconstitution_resume_target_sentences", 24) or 24))
    cap = max(target, int(resume_policy.get("reconstitution_resume_max_sentences", 30) or 30))
    target_units = max(1, int(resume_policy.get("reconstitution_resume_target_meaning_units", 3) or 3))
    start = max(0, current_index - target + 1)
    groups = [
        [sentence_id for sentence_id in unit if _clean_text(sentence_id) in index_by_id]
        for unit in continuity.get("recent_meaning_units", [])
        if isinstance(unit, list)
    ]
    open_group = [
        sentence_id
        for sentence_id in continuity.get("open_meaning_unit_sentence_ids", [])
        if _clean_text(sentence_id) in index_by_id
    ]
    if open_group:
        groups.append(open_group)
    groups = [group for group in groups if group]
    if groups:
        selected_groups = groups[-target_units:]
        group_start = min(index_by_id[sentence_id] for group in selected_groups for sentence_id in group)
        if group_start < start:
            start = group_start
    if current_index - start + 1 > cap:
        start = max(0, current_index - cap + 1)
    return sentences[start : current_index + 1]


def _to_local_buffer_sentences(sentences: list[dict[str, object]]) -> list[LocalBufferSentence]:
    """Project canonical sentence records into the local-buffer sentence shape."""

    return [
        {
            "sentence_id": _clean_text(sentence.get("sentence_id")),
            "sentence_index": int(sentence.get("sentence_index", 0) or 0),
            "paragraph_index": int(sentence.get("paragraph_index", 0) or 0),
            "text": _clean_text(sentence.get("text")),
            "text_role": sentence.get("text_role", "body"),
        }
        for sentence in sentences
    ]


def _filter_meaning_units(units: list[list[str]], allowed_ids: set[str]) -> list[list[str]]:
    """Keep only ids that still fall inside the reconstructed sentence window."""

    filtered_units: list[list[str]] = []
    for unit in units:
        kept = [sentence_id for sentence_id in unit if sentence_id in allowed_ids]
        if kept:
            filtered_units.append(kept)
    return filtered_units


def _mark_local_buffer(
    local_buffer: LocalBufferState,
    *,
    resume_kind: ResumeKind,
    checkpoint_id: str | None,
    reconstructed: bool,
    window_sentences: list[dict[str, object]] | None = None,
    continuity: LocalContinuityState | None = None,
) -> LocalBufferState:
    """Return the post-resume local buffer, optionally reconstructed from a sentence window."""

    next_buffer = dict(local_buffer)
    if window_sentences is not None and continuity is not None:
        window_ids = [_clean_text(sentence.get("sentence_id")) for sentence in window_sentences if _clean_text(sentence.get("sentence_id"))]
        allowed_ids = set(window_ids)
        next_buffer["recent_sentences"] = _to_local_buffer_sentences(window_sentences)
        next_buffer["current_sentence_id"] = _clean_text(continuity.get("current_sentence_id")) or (window_ids[-1] if window_ids else "")
        next_buffer["current_sentence_index"] = int(continuity.get("current_sentence_index", 0) or 0)
        next_buffer["open_meaning_unit_sentence_ids"] = [
            sentence_id
            for sentence_id in continuity.get("open_meaning_unit_sentence_ids", [])
            if sentence_id in allowed_ids
        ]
        next_buffer["recent_meaning_units"] = _filter_meaning_units(
            [
                [str(sentence_id or "") for sentence_id in unit if _clean_text(sentence_id)]
                for unit in continuity.get("recent_meaning_units", [])
                if isinstance(unit, list)
            ],
            allowed_ids,
        )
        next_buffer["last_meaning_unit_closed_at_sentence_id"] = _clean_text(
            continuity.get("last_meaning_unit_closed_at_sentence_id")
        )
    next_buffer["updated_at"] = _timestamp()
    next_buffer["is_reconstructed"] = reconstructed
    next_buffer["reconstructed_from_checkpoint_id"] = checkpoint_id
    next_buffer["last_resume_kind"] = resume_kind
    return next_buffer  # type: ignore[return-value]


def _mark_local_continuity(
    continuity: LocalContinuityState,
    *,
    resume_kind: ResumeKind,
    checkpoint_id: str | None,
    reconstructed: bool,
    window_sentence_ids: list[str] | None = None,
) -> LocalContinuityState:
    """Return the post-resume compact continuity state."""

    next_continuity = dict(continuity)
    if window_sentence_ids is not None:
        allowed_ids = set(window_sentence_ids)
        next_continuity["recent_sentence_ids"] = list(window_sentence_ids)
        next_continuity["open_meaning_unit_sentence_ids"] = [
            sentence_id
            for sentence_id in continuity.get("open_meaning_unit_sentence_ids", [])
            if sentence_id in allowed_ids
        ]
        next_continuity["recent_meaning_units"] = _filter_meaning_units(
            [
                [str(sentence_id or "") for sentence_id in unit if _clean_text(sentence_id)]
                for unit in continuity.get("recent_meaning_units", [])
                if isinstance(unit, list)
            ],
            allowed_ids,
        )
    next_continuity["updated_at"] = _timestamp()
    next_continuity["is_reconstructed"] = reconstructed
    next_continuity["reconstructed_from_checkpoint_id"] = checkpoint_id
    next_continuity["last_resume_kind"] = resume_kind
    return next_continuity  # type: ignore[return-value]


def _rebuild_trigger_state(trigger_state: TriggerState, *, current_sentence_id: str) -> TriggerState:
    """Reset the cheap trigger state after a non-warm reconstruction."""

    return {
        **dict(trigger_state),
        "updated_at": _timestamp(),
        "current_sentence_id": current_sentence_id,
        "output": "no_zoom",
        "signals": [],
        "cadence_counter": 0,
        "callback_anchor_ids": [],
    }


def resume_from_checkpoint(
    output_dir: Path,
    *,
    book_document: BookDocument,
    requested_resume_kind: ResumeKind | None = None,
    checkpoint_id: str | None = None,
) -> dict[str, object]:
    """Restore live runtime state from the latest compatible checkpoint or fall back to live files."""

    live_bundle = _load_runtime_bundle(output_dir)
    policy = live_bundle["reader_policy"]
    resume_policy = dict(policy.get("resume", {}))
    effective_resume_kind: ResumeKind = requested_resume_kind or str(resume_policy.get("default_mode", "warm_resume"))  # type: ignore[assignment]
    checkpoint = load_full_checkpoint(output_dir, checkpoint_id=checkpoint_id)
    shell = load_runtime_shell(runtime_shell_file(output_dir))

    compatibility_status = "compatible"
    compatibility_issues: list[str] = []
    if checkpoint is None:
        compatibility_status = "fallback_to_live_state"
        compatibility_issues = ["checkpoint_missing"]
        effective_resume_kind = "warm_resume"
    else:
        compatibility = validate_resume_compatibility(
            checkpoint,
            book_document=book_document,
            current_mechanism_version=str(policy.get("mechanism_version", "") or ATTENTIONAL_V2_MECHANISM_VERSION),
            current_policy_version=str(policy.get("policy_version", "") or ATTENTIONAL_V2_POLICY_VERSION),
        )
        if not bool(compatibility.get("compatible", False)):
            compatibility_status = "fallback_to_live_state"
            compatibility_issues = [str(issue) for issue in compatibility.get("issues", [])]
            effective_resume_kind = "warm_resume"

    checkpoint_source = checkpoint or {
        "checkpoint_id": None,
        "cursor": shell.get("cursor", empty_cursor()),
        "local_buffer": live_bundle["local_buffer"],
        "local_continuity": live_bundle["local_continuity"],
        "trigger_state": live_bundle["trigger_state"],
        "working_pressure": live_bundle["working_pressure"],
        "anchor_memory": live_bundle["anchor_memory"],
        "reflective_summaries": live_bundle["reflective_summaries"],
        "knowledge_activations": live_bundle["knowledge_activations"],
        "move_history": live_bundle["move_history"],
        "reaction_records": live_bundle["reaction_records"],
        "reconsolidation_records": live_bundle["reconsolidation_records"],
        "reader_policy": live_bundle["reader_policy"],
        "resume_metadata": live_bundle["resume_metadata"],
        "active_artifact_refs": shell.get("active_artifact_refs", {}),
    }

    continuity = dict(checkpoint_source.get("local_continuity", {})) or build_empty_local_continuity(
        mechanism_version=str(policy.get("mechanism_version", "") or ATTENTIONAL_V2_MECHANISM_VERSION)
    )
    local_buffer = dict(checkpoint_source.get("local_buffer", {})) or build_empty_local_buffer(
        mechanism_version=str(policy.get("mechanism_version", "") or ATTENTIONAL_V2_MECHANISM_VERSION)
    )
    trigger_state = dict(checkpoint_source.get("trigger_state", {})) or build_empty_trigger_state(
        mechanism_version=str(policy.get("mechanism_version", "") or ATTENTIONAL_V2_MECHANISM_VERSION)
    )

    resume_window_sentence_ids: list[str] = []
    reconstructed = False
    if effective_resume_kind == "warm_resume":
        local_buffer = _mark_local_buffer(
            local_buffer,
            resume_kind="warm_resume",
            checkpoint_id=_clean_text(checkpoint_source.get("checkpoint_id")),
            reconstructed=False,
        )
        continuity = _mark_local_continuity(
            continuity,
            resume_kind="warm_resume",
            checkpoint_id=_clean_text(checkpoint_source.get("checkpoint_id")),
            reconstructed=False,
        )
    else:
        window_sentences = _window_sentence_records(
            book_document=book_document,
            continuity=continuity,  # type: ignore[arg-type]
            resume_kind=effective_resume_kind,
            resume_policy=resume_policy,
        )
        resume_window_sentence_ids = [
            _clean_text(sentence.get("sentence_id"))
            for sentence in window_sentences
            if _clean_text(sentence.get("sentence_id"))
        ]
        reconstructed = True
        local_buffer = _mark_local_buffer(
            local_buffer,
            resume_kind=effective_resume_kind,
            checkpoint_id=_clean_text(checkpoint_source.get("checkpoint_id")),
            reconstructed=True,
            window_sentences=window_sentences,
            continuity=continuity,  # type: ignore[arg-type]
        )
        continuity = _mark_local_continuity(
            continuity,  # type: ignore[arg-type]
            resume_kind=effective_resume_kind,
            checkpoint_id=_clean_text(checkpoint_source.get("checkpoint_id")),
            reconstructed=True,
            window_sentence_ids=resume_window_sentence_ids,
        )
        trigger_state = _rebuild_trigger_state(
            trigger_state,  # type: ignore[arg-type]
            current_sentence_id=_clean_text(local_buffer.get("current_sentence_id")),
        )

    bundle = {
        "local_buffer": local_buffer,
        "local_continuity": continuity,
        "trigger_state": trigger_state,
        "working_pressure": dict(checkpoint_source.get("working_pressure", live_bundle["working_pressure"])),
        "anchor_memory": dict(checkpoint_source.get("anchor_memory", live_bundle["anchor_memory"])),
        "reflective_summaries": dict(checkpoint_source.get("reflective_summaries", live_bundle["reflective_summaries"])),
        "knowledge_activations": dict(checkpoint_source.get("knowledge_activations", live_bundle["knowledge_activations"])),
        "move_history": dict(checkpoint_source.get("move_history", live_bundle["move_history"])),
        "reaction_records": dict(checkpoint_source.get("reaction_records", live_bundle["reaction_records"])),
        "reconsolidation_records": dict(checkpoint_source.get("reconsolidation_records", live_bundle["reconsolidation_records"])),
        "reader_policy": policy,
        "resume_metadata": dict(live_bundle["resume_metadata"]),
    }
    _save_runtime_bundle(output_dir, bundle)

    cursor = build_shared_cursor(
        chapter_id=continuity.get("chapter_id"),  # type: ignore[arg-type]
        chapter_ref=str(continuity.get("chapter_ref", "") or ""),
        current_sentence_id=str(continuity.get("current_sentence_id", "") or ""),
        open_meaning_unit_sentence_ids=list(continuity.get("open_meaning_unit_sentence_ids", [])),
    )
    shell["cursor"] = cursor
    shell["observability_mode"] = observability_mode(policy)
    shell["active_artifact_refs"] = dict(checkpoint_source.get("active_artifact_refs", shell.get("active_artifact_refs", {})))
    shell["resume_available"] = bool(shell.get("last_checkpoint_id"))
    shell["updated_at"] = _timestamp()
    save_runtime_shell(runtime_shell_file(output_dir), shell)

    resume_metadata: ResumeMetadataState = {
        **dict(live_bundle["resume_metadata"]),
        "updated_at": _timestamp(),
        "resume_available": bool(shell.get("last_checkpoint_id")),
        "default_resume_kind": effective_resume_kind if compatibility_status == "fallback_to_live_state" else str(
            resume_policy.get("default_mode", "warm_resume")
        ),
        "last_resume_kind": effective_resume_kind,
        "last_resume_at": _timestamp(),
        "last_resume_checkpoint_id": checkpoint_source.get("checkpoint_id"),
        "last_resume_status": "hot_reconstructed" if reconstructed else "warm_restored",
        "last_resume_reason": ",".join(compatibility_issues) if compatibility_issues else "checkpoint_restored",
        "last_resume_window_sentence_ids": resume_window_sentence_ids,
        "reconstructed_hot_state": reconstructed,
    }
    save_json(resume_metadata_file(output_dir), resume_metadata)

    resume_result = {
        "requested_resume_kind": requested_resume_kind or resume_policy.get("default_mode", "warm_resume"),
        "effective_resume_kind": effective_resume_kind,
        "compatibility_status": compatibility_status,
        "compatibility_issues": compatibility_issues,
        "checkpoint_id": checkpoint_source.get("checkpoint_id"),
        "resume_window_sentence_ids": resume_window_sentence_ids,
        "cursor": cursor,
        "local_buffer": local_buffer,
        "local_continuity": continuity,
        "trigger_state": trigger_state,
        "resume_metadata": resume_metadata,
    }
    emit_resume_observability(
        output_dir,
        resume_result,
        reader_policy=policy,  # type: ignore[arg-type]
        active_artifact_refs=shell.get("active_artifact_refs"),  # type: ignore[arg-type]
    )

    return resume_result

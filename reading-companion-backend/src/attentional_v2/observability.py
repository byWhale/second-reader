"""Phase 8 observability helpers for standard vs debug persistence."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

from src.reading_core.runtime_contracts import ObservabilityMode, RuntimeArtifactRefs
from src.reading_runtime import artifacts as runtime_artifacts

from .schemas import FullCheckpointState, ReaderPolicy
from .storage import append_jsonl, event_stream_file


def _timestamp() -> str:
    """Return a stable UTC timestamp."""

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _clean_text(value: object) -> str:
    """Return one normalized string."""

    return str(value or "").strip()


def _logging_policy(reader_policy: Mapping[str, object] | None) -> Mapping[str, object]:
    """Return the logging policy subsection when available."""

    if not isinstance(reader_policy, Mapping):
        return {}
    logging = reader_policy.get("logging")
    return logging if isinstance(logging, Mapping) else {}


def observability_mode(reader_policy: Mapping[str, object] | None) -> ObservabilityMode:
    """Return the effective observability mode for one run."""

    mode = _clean_text(_logging_policy(reader_policy).get("observability_mode"))
    return "debug" if mode == "debug" else "standard"


def debug_event_stream_enabled(reader_policy: Mapping[str, object] | None) -> bool:
    """Whether debug-only event diagnostics should be emitted."""

    logging = _logging_policy(reader_policy)
    return observability_mode(reader_policy) == "debug" or bool(logging.get("debug_event_stream", False))


def debug_checkpoint_diagnostics_enabled(reader_policy: Mapping[str, object] | None) -> bool:
    """Whether richer checkpoint diagnostics should be emitted in debug mode."""

    logging = _logging_policy(reader_policy)
    return observability_mode(reader_policy) == "debug" or bool(logging.get("debug_checkpoint_diagnostics", False))


def standard_event_stream_enabled(reader_policy: Mapping[str, object] | None) -> bool:
    """Whether the shared standard activity stream should be emitted."""

    return bool(_logging_policy(reader_policy).get("event_stream", True))


def _append_shared_jsonl(path: Path, payload: object) -> None:
    """Append one JSONL line to a shared runtime file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False))
        file.write("\n")


def reading_locus_from_cursor(cursor: Mapping[str, object] | None) -> dict[str, object] | None:
    """Project a shared cursor into the additive public reading-locus shape."""

    if not isinstance(cursor, Mapping):
        return None
    kind = _clean_text(cursor.get("position_kind"))
    if kind not in {"chapter", "sentence", "span"}:
        kind = "chapter"
    locus: dict[str, object] = {"kind": kind}
    chapter_id = cursor.get("chapter_id")
    if isinstance(chapter_id, int):
        locus["chapter_id"] = chapter_id
    chapter_ref = _clean_text(cursor.get("chapter_ref"))
    if chapter_ref:
        locus["chapter_ref"] = chapter_ref
    sentence_id = _clean_text(cursor.get("sentence_id"))
    start_id = _clean_text(cursor.get("span_start_sentence_id")) or sentence_id
    end_id = _clean_text(cursor.get("span_end_sentence_id")) or sentence_id or start_id
    if start_id:
        locus["sentence_start_id"] = start_id
    if end_id:
        locus["sentence_end_id"] = end_id
    if len(locus) == 1 and kind == "chapter":
        return None
    return locus


def _checkpoint_state_counts(checkpoint: FullCheckpointState) -> dict[str, int]:
    """Return compact checkpoint counts that are useful for debug forensics."""

    local_buffer = checkpoint.get("local_buffer", {})
    anchor_memory = checkpoint.get("anchor_memory", {})
    reflective_summaries = checkpoint.get("reflective_summaries", {})
    knowledge_activations = checkpoint.get("knowledge_activations", {})
    move_history = checkpoint.get("move_history", {})
    reaction_records = checkpoint.get("reaction_records", {})
    reconsolidation_records = checkpoint.get("reconsolidation_records", {})
    return {
        "recent_sentence_count": len(local_buffer.get("recent_sentences", [])),
        "open_meaning_unit_sentence_count": len(local_buffer.get("open_meaning_unit_sentence_ids", [])),
        "anchor_count": len(anchor_memory.get("anchor_records", [])),
        "reflective_item_count": len(reflective_summaries.get("chapter_understandings", [])),
        "activation_count": len(knowledge_activations.get("activations", [])),
        "move_count": len(move_history.get("moves", [])),
        "reaction_count": len(reaction_records.get("records", [])),
        "reconsolidation_count": len(reconsolidation_records.get("records", [])),
    }


def build_checkpoint_activity_event(checkpoint: FullCheckpointState) -> dict[str, object]:
    """Build the standard shared activity event for a checkpoint write."""

    checkpoint_id = _clean_text(checkpoint.get("checkpoint_id")) or "latest"
    created_at = _clean_text(checkpoint.get("created_at")) or _timestamp()
    cursor = checkpoint.get("cursor", {})
    chapter_ref = _clean_text(cursor.get("chapter_ref"))
    message = f"Checkpoint saved in {chapter_ref}." if chapter_ref else "Checkpoint saved."
    active_refs = checkpoint.get("active_artifact_refs", {})
    event: dict[str, object] = {
        "event_id": f"checkpoint:{checkpoint_id}",
        "timestamp": created_at,
        "type": "checkpoint.saved",
        "stream": "system",
        "kind": "checkpoint",
        "visibility": "collapsed",
        "message": message,
        "chapter_id": cursor.get("chapter_id"),
        "chapter_ref": chapter_ref or None,
        "reaction_types": [],
        "visible_reactions": [],
        "featured_reactions": [],
        "visible_reaction_count": len(checkpoint.get("visible_reaction_ids", [])),
        "active_reaction_id": _clean_text(active_refs.get("reaction_id")) or None,
    }
    reading_locus = reading_locus_from_cursor(cursor)
    if reading_locus is not None:
        event["reading_locus"] = reading_locus
    return event


def build_resume_activity_event(
    resume_payload: Mapping[str, object],
    *,
    active_artifact_refs: RuntimeArtifactRefs | None = None,
) -> dict[str, object]:
    """Build the standard shared activity event for resume restoration."""

    effective_resume_kind = _clean_text(resume_payload.get("effective_resume_kind")) or "warm_resume"
    compatibility_status = _clean_text(resume_payload.get("compatibility_status"))
    if compatibility_status == "fallback_to_live_state":
        message = "Resumed from live state after checkpoint compatibility fallback."
    elif effective_resume_kind == "cold_resume":
        message = "Rebuilt recent reading context from the latest checkpoint."
    elif effective_resume_kind == "reconstitution_resume":
        message = "Reconstituted recent reading context from the latest checkpoint."
    else:
        message = "Resumed from the latest checkpoint."
    checkpoint_id = _clean_text(resume_payload.get("checkpoint_id")) or "latest"
    cursor = resume_payload.get("cursor", {})
    chapter_ref = _clean_text(cursor.get("chapter_ref")) if isinstance(cursor, Mapping) else ""
    event: dict[str, object] = {
        "event_id": f"resume:{checkpoint_id}:{effective_resume_kind}",
        "timestamp": _timestamp(),
        "type": "resume.restored",
        "stream": "system",
        "kind": "transition",
        "visibility": "collapsed",
        "message": message,
        "chapter_id": cursor.get("chapter_id") if isinstance(cursor, Mapping) else None,
        "chapter_ref": chapter_ref or None,
        "reaction_types": [],
        "visible_reactions": [],
        "featured_reactions": [],
        "active_reaction_id": _clean_text((active_artifact_refs or {}).get("reaction_id")) or None,
        "reconstructed_hot_state": bool(resume_payload.get("resume_window_sentence_ids")),
        "last_resume_kind": effective_resume_kind,
    }
    reading_locus = reading_locus_from_cursor(cursor if isinstance(cursor, Mapping) else None)
    if reading_locus is not None:
        event["reading_locus"] = reading_locus
    return event


def append_standard_activity_event(
    output_dir: Path,
    event: Mapping[str, object],
    *,
    reader_policy: ReaderPolicy | Mapping[str, object] | None,
) -> None:
    """Append one standard-mode shared activity event when enabled."""

    if not standard_event_stream_enabled(reader_policy):
        return
    _append_shared_jsonl(runtime_artifacts.activity_file(output_dir), dict(event))


def append_debug_event(
    output_dir: Path,
    *,
    event_type: str,
    payload: Mapping[str, object],
    reader_policy: ReaderPolicy | Mapping[str, object] | None,
) -> None:
    """Append one debug-only diagnostics event when enabled."""

    if not debug_event_stream_enabled(reader_policy):
        return
    append_jsonl(
        event_stream_file(output_dir),
        {
            "event_id": f"debug:{_clean_text(event_type)}:{_timestamp()}",
            "timestamp": _timestamp(),
            "event_type": _clean_text(event_type),
            "observability_mode": "debug",
            "payload": dict(payload),
        },
    )


def emit_checkpoint_observability(
    output_dir: Path,
    checkpoint: FullCheckpointState,
    *,
    reader_policy: ReaderPolicy | Mapping[str, object] | None,
) -> None:
    """Emit the standard checkpoint event and optional debug diagnostics."""

    append_standard_activity_event(
        output_dir,
        build_checkpoint_activity_event(checkpoint),
        reader_policy=reader_policy,
    )
    debug_payload: dict[str, object] = {
        "checkpoint_id": _clean_text(checkpoint.get("checkpoint_id")),
        "checkpoint_reason": _clean_text(checkpoint.get("checkpoint_reason")),
        "resume_kind": _clean_text(checkpoint.get("resume_kind")),
        "cursor": dict(checkpoint.get("cursor", {})),
        "active_artifact_refs": dict(checkpoint.get("active_artifact_refs", {})),
        "visible_reaction_ids": list(checkpoint.get("visible_reaction_ids", [])),
    }
    if debug_checkpoint_diagnostics_enabled(reader_policy):
        debug_payload["state_counts"] = _checkpoint_state_counts(checkpoint)
    append_debug_event(
        output_dir,
        event_type="checkpoint.saved",
        payload=debug_payload,
        reader_policy=reader_policy,
    )


def emit_resume_observability(
    output_dir: Path,
    resume_payload: Mapping[str, object],
    *,
    reader_policy: ReaderPolicy | Mapping[str, object] | None,
    active_artifact_refs: RuntimeArtifactRefs | None = None,
) -> None:
    """Emit the standard resume event and optional debug diagnostics."""

    append_standard_activity_event(
        output_dir,
        build_resume_activity_event(resume_payload, active_artifact_refs=active_artifact_refs),
        reader_policy=reader_policy,
    )
    debug_payload: dict[str, object] = {
        "requested_resume_kind": _clean_text(resume_payload.get("requested_resume_kind")),
        "effective_resume_kind": _clean_text(resume_payload.get("effective_resume_kind")),
        "compatibility_status": _clean_text(resume_payload.get("compatibility_status")),
        "compatibility_issues": list(resume_payload.get("compatibility_issues", [])),
        "checkpoint_id": _clean_text(resume_payload.get("checkpoint_id")),
        "resume_window_sentence_ids": list(resume_payload.get("resume_window_sentence_ids", [])),
        "cursor": dict(resume_payload.get("cursor", {})) if isinstance(resume_payload.get("cursor"), Mapping) else {},
        "active_artifact_refs": dict(active_artifact_refs or {}),
    }
    append_debug_event(
        output_dir,
        event_type="resume.restored",
        payload=debug_payload,
        reader_policy=reader_policy,
    )

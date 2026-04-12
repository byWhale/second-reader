"""Phase 8 evaluation exports and integrity checks for attentional_v2."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, TypedDict

from src.reading_core import BookDocument
from src.reading_core.normalized_outputs import (
    NormalizedAttentionEvent,
    NormalizedChapterOutput,
    NormalizedEvalBundle,
    NormalizedReaction,
    NormalizedRunSnapshot,
)
from src.reading_core.runtime_contracts import stable_config_fingerprint
from src.reading_core.storage import existing_book_document_file, load_book_document
from src.reading_runtime import artifacts as runtime_artifacts
from src.reading_runtime.shell_state import load_runtime_shell

from .observability import reading_locus_from_cursor
from .schemas import ATTENTIONAL_V2_MECHANISM_VERSION, ATTENTIONAL_V2_POLICY_VERSION, ReaderPolicy
from .storage import (
    ATTENTIONAL_V2_MECHANISM_KEY,
    chapter_result_compatibility_file,
    load_json,
    reaction_records_file,
    reader_policy_file,
    reflective_frames_file,
    reflective_summaries_file,
    reconsolidation_records_file,
    save_json,
)


IntegrityCheckStatus = Literal["pass", "warn", "fail"]


class IntegrityCheckResult(TypedDict, total=False):
    """One structural integrity check over persisted attentional_v2 artifacts."""

    code: str
    status: IntegrityCheckStatus
    message: str
    details: dict[str, object]


class MechanismIntegrityReport(TypedDict, total=False):
    """Integrity-report envelope for attentional_v2 artifact validation."""

    mechanism_key: str
    mechanism_version: str
    generated_at: str
    output_dir: str
    passed: bool
    check_count: int
    failure_count: int
    warning_count: int
    checks: list[IntegrityCheckResult]


def _timestamp() -> str:
    """Return a stable UTC timestamp."""

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _clean_text(value: object) -> str:
    """Return one normalized string."""

    return str(value or "").strip()


def _load_json_if_exists(path: Path) -> dict[str, object]:
    """Load one JSON object when present, otherwise return an empty payload."""

    if not path.exists():
        return {}
    return load_json(path)


def _load_jsonl(path: Path) -> list[dict[str, object]]:
    """Load one JSONL file into dictionaries, skipping malformed lines."""

    if not path.exists():
        return []
    items: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            items.append(payload)
    return items


def _reaction_section_ref(record: Mapping[str, object], *, chapter_id: int) -> str:
    """Return the compatibility section ref for one persisted reaction."""

    explicit = _clean_text(record.get("compatibility_section_ref"))
    if explicit:
        return explicit
    primary_anchor = record.get("primary_anchor")
    if isinstance(primary_anchor, Mapping):
        locator = primary_anchor.get("locator")
        if isinstance(locator, Mapping):
            paragraph_index = int(locator.get("paragraph_index", 0) or locator.get("paragraph_start", 0) or 0)
            if paragraph_index > 0:
                return f"{int(chapter_id)}.{paragraph_index}"
    return f"{int(chapter_id)}.1"


def normalized_eval_bundle_file(output_dir: Path) -> Path:
    """Return the explicit attentional_v2 normalized eval export path."""

    return runtime_artifacts.mechanism_export_file(output_dir, ATTENTIONAL_V2_MECHANISM_KEY, "normalized_eval_bundle.json")


def _load_book_document(output_dir: Path) -> BookDocument:
    """Load the shared parsed-book substrate for one output directory."""

    return load_book_document(existing_book_document_file(output_dir))


def _reaction_section_index(output_dir: Path, document: BookDocument) -> dict[str, str]:
    """Return a `reaction_id -> segment_ref` mapping from persisted compatibility payloads."""

    index: dict[str, str] = {}
    for chapter in document.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        chapter_id = int(chapter.get("id", 0) or 0)
        payload = _load_json_if_exists(chapter_result_compatibility_file(output_dir, chapter_id))
        for section in payload.get("sections", []):
            if not isinstance(section, dict):
                continue
            segment_ref = _clean_text(section.get("segment_ref"))
            if not segment_ref:
                continue
            for reaction in section.get("reactions", []):
                if not isinstance(reaction, dict):
                    continue
                reaction_id = _clean_text(reaction.get("reaction_id"))
                if reaction_id:
                    index[reaction_id] = segment_ref
    return index


def _last_activity_event(output_dir: Path) -> dict[str, object]:
    """Return the latest shared activity event when present."""

    events = _load_jsonl(runtime_artifacts.existing_activity_file(output_dir))
    return dict(events[-1]) if events else {}


def _normalized_run_snapshot(
    output_dir: Path,
    document: BookDocument,
    reaction_sections: Mapping[str, str],
) -> NormalizedRunSnapshot | None:
    """Build the normalized run snapshot from the shared shell and activity trace."""

    shell_path = runtime_artifacts.existing_runtime_shell_file(output_dir)
    if not shell_path.exists():
        return None
    shell = load_runtime_shell(shell_path)
    cursor = shell.get("cursor", {})
    current_activity = _last_activity_event(output_dir)
    active_reaction_id = _clean_text(shell.get("active_artifact_refs", {}).get("reaction_id"))
    current_section_ref = (
        _clean_text(current_activity.get("segment_ref"))
        or _clean_text(current_activity.get("section_ref"))
        or reaction_sections.get(active_reaction_id, "")
    )
    snapshot: NormalizedRunSnapshot = {
        "status": _clean_text(shell.get("status")),
        "current_chapter_ref": _clean_text(cursor.get("chapter_ref")),
        "current_section_ref": current_section_ref,
        "resume_available": bool(shell.get("resume_available")) if shell.get("resume_available") is not None else None,
        "last_checkpoint_at": shell.get("last_checkpoint_at"),
        "completed_chapters": sum(
            1
            for chapter in document.get("chapters", [])
            if isinstance(chapter, dict)
            and chapter_result_compatibility_file(output_dir, int(chapter.get("id", 0) or 0)).exists()
        ),
        "total_chapters": len(document.get("chapters", [])),
        "active_reaction_id": active_reaction_id or None,
    }
    reading_locus = reading_locus_from_cursor(cursor if isinstance(cursor, Mapping) else None)
    if reading_locus is not None:
        snapshot["current_reading_locus"] = reading_locus
    if current_activity:
        activity_payload = {
            "reading_locus": current_activity.get("reading_locus"),
            "move_type": current_activity.get("move_type"),
            "current_excerpt": current_activity.get("anchor_quote") or current_activity.get("highlight_quote") or "",
            "reconstructed_hot_state": bool(current_activity.get("reconstructed_hot_state")),
            "last_resume_kind": current_activity.get("last_resume_kind"),
            "active_reaction_id": current_activity.get("active_reaction_id") or active_reaction_id or None,
        }
        snapshot["current_reading_activity"] = activity_payload
        snapshot["current_move_type"] = _clean_text(current_activity.get("move_type"))
        snapshot["reconstructed_hot_state"] = (
            bool(current_activity.get("reconstructed_hot_state"))
            if current_activity.get("reconstructed_hot_state") is not None
            else None
        )
        snapshot["last_resume_kind"] = _clean_text(current_activity.get("last_resume_kind")) or None
        if current_activity.get("active_reaction_id") or active_reaction_id:
            snapshot["active_reaction_id"] = _clean_text(current_activity.get("active_reaction_id")) or active_reaction_id
    return snapshot


def _normalized_attention_events(output_dir: Path) -> list[NormalizedAttentionEvent]:
    """Normalize shared activity events into a cross-mechanism comparison surface."""

    events: list[NormalizedAttentionEvent] = []
    for raw in _load_jsonl(runtime_artifacts.existing_activity_file(output_dir)):
        payload: NormalizedAttentionEvent = {
            "event_id": _clean_text(raw.get("event_id")),
            "timestamp": _clean_text(raw.get("timestamp")),
            "stream": _clean_text(raw.get("stream")),
            "kind": _clean_text(raw.get("kind")),
            "message": _clean_text(raw.get("message")),
            "chapter_ref": _clean_text(raw.get("chapter_ref")),
            "section_ref": _clean_text(raw.get("segment_ref") or raw.get("section_ref")),
            "current_excerpt": _clean_text(raw.get("anchor_quote") or raw.get("highlight_quote")),
            "search_query": _clean_text(raw.get("search_query")),
            "thought_family": _clean_text(raw.get("thought_family")),
            "problem_code": _clean_text(raw.get("problem_code")),
            "move_type": _clean_text(raw.get("move_type")),
            "active_reaction_id": _clean_text(raw.get("active_reaction_id")),
        }
        phase = _clean_text(raw.get("phase"))
        if phase:
            payload["phase"] = phase  # type: ignore[typeddict-item]
        if isinstance(raw.get("reading_locus"), Mapping):
            payload["reading_locus"] = dict(raw.get("reading_locus"))
        events.append(payload)
    return events


def _normalized_reactions(output_dir: Path) -> list[NormalizedReaction]:
    """Normalize persisted attentional_v2 reactions into a comparison list."""

    payload = _load_json_if_exists(reaction_records_file(output_dir))
    reactions: list[NormalizedReaction] = []
    for raw in payload.get("records", []):
        if not isinstance(raw, dict):
            continue
        chapter_id = int(raw.get("chapter_id", 0) or 0)
        primary_anchor = raw.get("primary_anchor")
        reactions.append(
            {
                "reaction_id": _clean_text(raw.get("reaction_id")),
                "type": _clean_text(raw.get("type")) or "association",
                "chapter_ref": _clean_text(raw.get("chapter_ref")),
                "section_ref": _reaction_section_ref(raw, chapter_id=chapter_id),
                "anchor_quote": _clean_text(primary_anchor.get("quote")) if isinstance(primary_anchor, Mapping) else "",
                "content": _clean_text(raw.get("thought")),
                "search_query": _clean_text(raw.get("search_query")),
                "search_results": [
                    dict(item)
                    for item in raw.get("search_results", [])
                    if isinstance(item, dict)
                ]
                if isinstance(raw.get("search_results"), list)
                else [],
                "primary_anchor": dict(primary_anchor) if isinstance(primary_anchor, Mapping) else None,
                "related_anchors": [
                    dict(anchor)
                    for anchor in raw.get("related_anchors", [])
                    if isinstance(anchor, dict)
                ]
                if isinstance(raw.get("related_anchors"), list)
                else [],
                "supersedes_reaction_id": _clean_text(raw.get("supersedes_reaction_id")),
            }
        )
    return reactions


def _normalized_chapter_outputs(output_dir: Path, document: BookDocument) -> list[NormalizedChapterOutput]:
    """Build compact chapter summaries from compatibility payloads and chapter truth."""

    outputs: list[NormalizedChapterOutput] = []
    for chapter in document.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        chapter_id = int(chapter.get("id", 0) or 0)
        chapter_ref = _clean_text(chapter.get("reference")) or f"Chapter {chapter_id}"
        payload = _load_json_if_exists(chapter_result_compatibility_file(output_dir, chapter_id))
        featured = payload.get("featured_reactions", []) if isinstance(payload.get("featured_reactions"), list) else []
        outputs.append(
            {
                "chapter_id": chapter_id,
                "chapter_ref": _clean_text(payload.get("chapter", {}).get("reference") if isinstance(payload.get("chapter"), dict) else chapter_ref) or chapter_ref,
                "title": _clean_text(chapter.get("title")),
                "status": _clean_text(payload.get("chapter", {}).get("status") if isinstance(payload.get("chapter"), dict) else "") or "pending",
                "section_count": len(payload.get("sections", [])) if isinstance(payload.get("sections"), list) else 0,
                "visible_reaction_count": int(payload.get("visible_reaction_count", 0) or 0),
                "featured_reaction_count": len(featured),
                "reflection_summary": _clean_text(
                    payload.get("chapter_reflection", {}).get("summary") if isinstance(payload.get("chapter_reflection"), dict) else ""
                ),
            }
        )
    return outputs


def _memory_summaries(output_dir: Path) -> list[str]:
    """Extract compact reflective summaries for comparison and audits."""

    payload = _load_json_if_exists(reflective_frames_file(output_dir))
    if not payload or not any(isinstance(payload.get(bucket), list) and payload.get(bucket) for bucket in (
        "chapter_understandings",
        "book_level_frames",
        "durable_definitions",
        "stabilized_motifs",
        "resolved_questions_of_record",
        "chapter_end_notes",
    )):
        payload = _load_json_if_exists(reflective_summaries_file(output_dir))
    summaries: list[str] = []
    for bucket in (
        "chapter_understandings",
        "book_level_frames",
        "durable_definitions",
        "stabilized_motifs",
        "resolved_questions_of_record",
        "chapter_end_notes",
    ):
        for item in payload.get(bucket, []):
            if not isinstance(item, dict):
                continue
            statement = _clean_text(item.get("statement"))
            if statement:
                summaries.append(statement)
    return summaries[:12]


def build_normalized_eval_bundle(
    output_dir: Path,
    *,
    config_payload: Mapping[str, object] | None = None,
) -> NormalizedEvalBundle:
    """Build the current normalized evaluation bundle from persisted attentional_v2 artifacts."""

    document = _load_book_document(output_dir)
    reaction_sections = _reaction_section_index(output_dir, document)
    return {
        "mechanism_key": ATTENTIONAL_V2_MECHANISM_KEY,
        "mechanism_label": "Attentional V2 scaffold (Phase 1-8)",
        "generated_at": _timestamp(),
        "output_dir": str(output_dir),
        "config_fingerprint": stable_config_fingerprint(
            dict(config_payload) if isinstance(config_payload, Mapping) else {"policy_version": ATTENTIONAL_V2_POLICY_VERSION}
        ),
        "run_snapshot": _normalized_run_snapshot(output_dir, document, reaction_sections),
        "attention_events": _normalized_attention_events(output_dir),
        "reactions": _normalized_reactions(output_dir),
        "chapters": _normalized_chapter_outputs(output_dir, document),
        "memory_summaries": _memory_summaries(output_dir),
        "token_metadata": {},
        "latency_metadata": {},
        "cost_metadata": {},
    }


def persist_normalized_eval_bundle(
    output_dir: Path,
    *,
    config_payload: Mapping[str, object] | None = None,
) -> Path:
    """Persist one explicit attentional_v2 normalized eval export for eval runs."""

    path = normalized_eval_bundle_file(output_dir)
    save_json(path, build_normalized_eval_bundle(output_dir, config_payload=config_payload))
    return path


def _book_sentence_ids(document: BookDocument) -> set[str]:
    """Return the set of shared sentence ids available in the parsed-book substrate."""

    ids: set[str] = set()
    for chapter in document.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        for sentence in chapter.get("sentences", []):
            if not isinstance(sentence, dict):
                continue
            sentence_id = _clean_text(sentence.get("sentence_id"))
            if sentence_id:
                ids.add(sentence_id)
    return ids


def _check_result(
    code: str,
    status: IntegrityCheckStatus,
    message: str,
    *,
    details: Mapping[str, object] | None = None,
) -> IntegrityCheckResult:
    """Build one integrity-check result entry."""

    return {
        "code": code,
        "status": status,
        "message": message,
        "details": dict(details or {}),
    }


def run_mechanism_integrity_checks(output_dir: Path) -> MechanismIntegrityReport:
    """Run structural attentional_v2 integrity checks over the current persisted artifacts."""

    document = _load_book_document(output_dir)
    sentence_ids = _book_sentence_ids(document)
    shell = load_runtime_shell(runtime_artifacts.existing_runtime_shell_file(output_dir))
    reactions_payload = _load_json_if_exists(reaction_records_file(output_dir))
    recon_payload = _load_json_if_exists(reconsolidation_records_file(output_dir))
    policy = _load_json_if_exists(reader_policy_file(output_dir))
    checks: list[IntegrityCheckResult] = []

    cursor = shell.get("cursor", {})
    referenced_sentence_ids = [
        _clean_text(cursor.get("sentence_id")),
        _clean_text(cursor.get("span_start_sentence_id")),
        _clean_text(cursor.get("span_end_sentence_id")),
    ]
    missing_cursor_ids = [sentence_id for sentence_id in referenced_sentence_ids if sentence_id and sentence_id not in sentence_ids]
    checks.append(
        _check_result(
            "runtime_cursor_sentence_ids_resolve",
            "fail" if missing_cursor_ids else "pass",
            "Shared runtime cursor sentence ids resolve against the canonical parsed-book substrate."
            if not missing_cursor_ids
            else "Shared runtime cursor references sentence ids that are missing from public/book_document.json.",
            details={"missing_sentence_ids": missing_cursor_ids},
        )
    )

    reaction_ids = [
        _clean_text(record.get("reaction_id"))
        for record in reactions_payload.get("records", [])
        if isinstance(record, dict) and _clean_text(record.get("reaction_id"))
    ]
    duplicate_reaction_ids = sorted([reaction_id for reaction_id, count in Counter(reaction_ids).items() if count > 1])
    checks.append(
        _check_result(
            "reaction_ids_unique",
            "fail" if duplicate_reaction_ids else "pass",
            "Persisted reactions keep immutable unique ids."
            if not duplicate_reaction_ids
            else "Persisted reactions contain duplicate reaction ids.",
            details={"duplicate_reaction_ids": duplicate_reaction_ids},
        )
    )

    missing_anchor_sentence_ids: list[str] = []
    bad_locator_reactions: list[str] = []
    for record in reactions_payload.get("records", []):
        if not isinstance(record, dict):
            continue
        anchors = []
        primary_anchor = record.get("primary_anchor")
        if isinstance(primary_anchor, dict):
            anchors.append(primary_anchor)
        if isinstance(record.get("related_anchors"), list):
            anchors.extend(anchor for anchor in record.get("related_anchors", []) if isinstance(anchor, dict))
        for anchor in anchors:
            start_id = _clean_text(anchor.get("sentence_start_id"))
            end_id = _clean_text(anchor.get("sentence_end_id")) or start_id
            if start_id and start_id not in sentence_ids:
                missing_anchor_sentence_ids.append(start_id)
            if end_id and end_id not in sentence_ids:
                missing_anchor_sentence_ids.append(end_id)
            locator = anchor.get("locator")
            if not isinstance(locator, Mapping):
                bad_locator_reactions.append(_clean_text(record.get("reaction_id")))
                continue
            href = _clean_text(locator.get("href"))
            paragraph_index = int(locator.get("paragraph_index", 0) or locator.get("paragraph_start", 0) or 0)
            char_start = int(locator.get("char_start", 0) or 0)
            char_end = int(locator.get("char_end", 0) or 0)
            if not href or paragraph_index <= 0 or char_end < char_start:
                bad_locator_reactions.append(_clean_text(record.get("reaction_id")))
    checks.append(
        _check_result(
            "anchors_reference_shared_sentences",
            "fail" if missing_anchor_sentence_ids else "pass",
            "Anchors resolve against shared sentence ids."
            if not missing_anchor_sentence_ids
            else "One or more anchors point at sentence ids outside the shared parsed-book substrate.",
            details={"missing_sentence_ids": sorted(set(missing_anchor_sentence_ids))},
        )
    )
    checks.append(
        _check_result(
            "anchors_have_usable_locators",
            "fail" if bad_locator_reactions else "pass",
            "Anchors carry usable locator data for recall, marks, and audits."
            if not bad_locator_reactions
            else "One or more reactions have anchors with missing or invalid locator data.",
            details={"reaction_ids": sorted(set(filter(None, bad_locator_reactions)))},
        )
    )

    known_reaction_ids = set(reaction_ids)
    broken_reconsolidations: list[str] = []
    for record in recon_payload.get("records", []):
        if not isinstance(record, dict):
            continue
        record_id = _clean_text(record.get("record_id")) or "unknown"
        prior_reaction_id = _clean_text(record.get("prior_reaction_id"))
        new_reaction_id = _clean_text(record.get("new_reaction_id"))
        if not prior_reaction_id or not new_reaction_id or prior_reaction_id == new_reaction_id:
            broken_reconsolidations.append(record_id)
            continue
        if prior_reaction_id not in known_reaction_ids or new_reaction_id not in known_reaction_ids:
            broken_reconsolidations.append(record_id)
    checks.append(
        _check_result(
            "reconsolidation_links_are_append_only",
            "fail" if broken_reconsolidations else "pass",
            "Reconsolidation records link prior and later reactions without mutating identity."
            if not broken_reconsolidations
            else "One or more reconsolidation records are missing valid prior/new reaction links.",
            details={"record_ids": broken_reconsolidations},
        )
    )

    resume = policy.get("resume") if isinstance(policy.get("resume"), Mapping) else {}
    q7_mismatches: dict[str, object] = {}
    expected_resume = {
        "cold_resume_target_sentences": 8,
        "cold_resume_max_sentences": 12,
        "reconstitution_resume_target_sentences": 24,
        "reconstitution_resume_max_sentences": 30,
        "reconstitution_resume_target_meaning_units": 3,
        "chapter_local_only": True,
    }
    for key, expected in expected_resume.items():
        actual = resume.get(key)
        if actual != expected:
            q7_mismatches[key] = {"expected": expected, "actual": actual}
    checks.append(
        _check_result(
            "resume_policy_matches_q7_bounds",
            "fail" if q7_mismatches else "pass",
            "Persisted reader policy still matches the agreed Q7 resume bounds."
            if not q7_mismatches
            else "Persisted reader policy has drifted from the agreed Q7 resume bounds.",
            details=q7_mismatches,
        )
    )

    compatibility_errors: list[str] = []
    for chapter in document.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        chapter_id = int(chapter.get("id", 0) or 0)
        payload = _load_json_if_exists(chapter_result_compatibility_file(output_dir, chapter_id))
        if not payload:
            continue
        for section in payload.get("sections", []):
            if not isinstance(section, dict):
                continue
            for reaction in section.get("reactions", []):
                if not isinstance(reaction, dict):
                    continue
                reaction_id = _clean_text(reaction.get("reaction_id"))
                source_record = next(
                    (
                        record
                        for record in reactions_payload.get("records", [])
                        if isinstance(record, dict) and _clean_text(record.get("reaction_id")) == reaction_id
                    ),
                    None,
                )
                if source_record is None:
                    compatibility_errors.append(reaction_id or "unknown")
                    continue
                source_anchor = source_record.get("primary_anchor")
                if isinstance(source_anchor, Mapping) and _clean_text(reaction.get("anchor_quote")) != _clean_text(source_anchor.get("quote")):
                    compatibility_errors.append(reaction_id or "unknown")
    checks.append(
        _check_result(
            "compatibility_projection_preserves_reaction_identity",
            "fail" if compatibility_errors else "pass",
            "Compatibility chapter payloads preserve persisted reaction identity and anchor quote."
            if not compatibility_errors
            else "Compatibility chapter payloads have drifted from persisted reaction truth.",
            details={"reaction_ids": sorted(set(filter(None, compatibility_errors)))},
        )
    )

    failure_count = sum(1 for check in checks if check.get("status") == "fail")
    warning_count = sum(1 for check in checks if check.get("status") == "warn")
    return {
        "mechanism_key": ATTENTIONAL_V2_MECHANISM_KEY,
        "mechanism_version": _clean_text(shell.get("mechanism_version")) or ATTENTIONAL_V2_MECHANISM_VERSION,
        "generated_at": _timestamp(),
        "output_dir": str(output_dir),
        "passed": failure_count == 0,
        "check_count": len(checks),
        "failure_count": failure_count,
        "warning_count": warning_count,
        "checks": checks,
    }

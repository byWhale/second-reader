"""Pure state-operation helpers for attentional_v2 runtime state."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from .schemas import (
    AnchoredReactionRecord,
    AnchorBankState,
    AnchorMemoryState,
    AnchorRecord,
    AnchorRelation,
    ConceptRegistryEntry,
    ConceptRegistryState,
    GateState,
    KnowledgeActivation,
    KnowledgeActivationsState,
    LocalBufferSentence,
    LocalBufferState,
    MoveHistoryState,
    MoveRecord,
    PressureSnapshot,
    ReactionRecordsState,
    ReaderPolicy,
    ReconsolidationRecord,
    ReconsolidationRecordsState,
    ReflectiveItem,
    ReflectiveFramesState,
    ReflectiveSummariesState,
    ThreadTraceEntry,
    ThreadTraceState,
    TriggerDecision,
    TriggerSignal,
    TriggerState,
    WorkingPressureItem,
    WorkingPressureState,
    WorkingState,
    StateOperation,
)


PressureBucket = Literal["local_hypotheses", "local_questions", "local_tensions", "local_motifs"]
ReflectiveBucket = Literal[
    "chapter_understandings",
    "book_level_frames",
    "durable_definitions",
    "stabilized_motifs",
    "resolved_questions_of_record",
    "chapter_end_notes",
]


def _timestamp() -> str:
    """Return a stable UTC timestamp."""

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _touch_state(state: dict[str, object]) -> dict[str, object]:
    """Return one shallow-copied state with an updated timestamp."""

    next_state = dict(state)
    next_state["updated_at"] = _timestamp()
    return next_state


def _upsert_by_id(items: list[dict[str, object]], item: dict[str, object], *, id_key: str) -> list[dict[str, object]]:
    """Replace an existing item by id or append it when absent."""

    item_id = str(item.get(id_key, "") or "")
    if not item_id:
        return [*items, item]

    replaced = False
    next_items: list[dict[str, object]] = []
    for existing in items:
        if str(existing.get(id_key, "") or "") == item_id:
            next_items.append(item)
            replaced = True
        else:
            next_items.append(existing)
    if not replaced:
        next_items.append(item)
    return next_items


def _remove_by_id(items: list[dict[str, object]], item_id: str, *, id_key: str) -> list[dict[str, object]]:
    """Return one list with the selected id removed."""

    selected = str(item_id or "")
    if not selected:
        return list(items)
    return [item for item in items if str(item.get(id_key, "") or "") != selected]


def _working_state_active_items(state: WorkingPressureState | WorkingState) -> list[WorkingPressureItem]:
    """Return the normalized active-items view over the current working state."""

    active_items = [dict(item) for item in state.get("active_items", []) if isinstance(item, dict)]
    if active_items:
        return active_items  # type: ignore[return-value]

    flattened: list[WorkingPressureItem] = []
    for bucket in ("local_hypotheses", "local_questions", "local_tensions", "local_motifs"):
        for item in state.get(bucket, []):
            if not isinstance(item, dict):
                continue
            item_id = str(item.get("item_id", "") or "").strip()
            if not item_id:
                continue
            flattened.append(
                {
                    "item_id": item_id,
                    "bucket": bucket,
                    "kind": str(item.get("kind", "") or "").strip(),
                    "statement": str(item.get("statement", "") or "").strip(),
                    "support_anchor_ids": list(item.get("support_anchor_ids", []))
                    if isinstance(item.get("support_anchor_ids"), list)
                    else [],
                    "linked_concept_keys": list(item.get("linked_concept_keys", []))
                    if isinstance(item.get("linked_concept_keys"), list)
                    else [],
                    "linked_thread_keys": list(item.get("linked_thread_keys", []))
                    if isinstance(item.get("linked_thread_keys"), list)
                    else [],
                    "last_touched_sentence_id": str(item.get("last_touched_sentence_id", "") or "").strip(),
                    "status": str(item.get("status", "") or "").strip(),
                }
            )
    return flattened


def _classify_pressure_bucket(item: dict[str, object]) -> PressureBucket:
    """Infer the closest legacy pressure bucket for one active item."""

    explicit_bucket = str(item.get("bucket", "") or "").strip()
    if explicit_bucket in {"local_hypotheses", "local_questions", "local_tensions", "local_motifs"}:
        return explicit_bucket  # type: ignore[return-value]

    kind = str(item.get("kind", "") or "").strip().lower()
    if "question" in kind:
        return "local_questions"
    if any(token in kind for token in ("tension", "conflict", "contrast", "pressure")):
        return "local_tensions"
    if any(token in kind for token in ("motif", "image", "pattern", "callback", "echo")):
        return "local_motifs"
    return "local_hypotheses"


def _sync_legacy_pressure_buckets(
    state: WorkingPressureState | WorkingState,
    *,
    active_items: list[WorkingPressureItem],
) -> WorkingPressureState | WorkingState:
    """Project active-items back into the legacy pressure buckets."""

    bucketed: dict[PressureBucket, list[WorkingPressureItem]] = {
        "local_hypotheses": [],
        "local_questions": [],
        "local_tensions": [],
        "local_motifs": [],
    }
    for item in active_items:
        bucket = _classify_pressure_bucket(item)
        bucketed[bucket].append(
            {
                **dict(item),
                "bucket": bucket,
            }
        )
    next_state = dict(state)
    next_state["active_items"] = [dict(item) for item in active_items]
    for bucket, items in bucketed.items():
        next_state[bucket] = [dict(item) for item in items]
    return next_state  # type: ignore[return-value]


def _rebuild_active_items_from_buckets(
    state: WorkingPressureState | WorkingState,
) -> WorkingPressureState | WorkingState:
    """Project the legacy bucketed state back into active-items."""

    return _sync_legacy_pressure_buckets(state, active_items=_working_state_active_items(state))


def _merge_unique_ids(*values: object) -> list[str]:
    """Return one stable de-duplicated list of linked ids."""

    ordered: list[str] = []
    seen: set[str] = set()
    for raw in values:
        if not isinstance(raw, list):
            continue
        for item in raw:
            clean = str(item or "").strip()
            if not clean or clean in seen:
                continue
            seen.add(clean)
            ordered.append(clean)
    return ordered


def _merge_active_item(
    existing: dict[str, object],
    payload: dict[str, object],
    *,
    item_id: str,
) -> WorkingPressureItem:
    """Merge one active-item payload on top of an existing entry."""

    merged: WorkingPressureItem = {
        "item_id": item_id,
        "bucket": str(payload.get("bucket", "") or existing.get("bucket", "") or "").strip(),
        "kind": str(payload.get("kind", "") or existing.get("kind", "") or "").strip(),
        "statement": str(payload.get("statement", "") or existing.get("statement", "") or "").strip(),
        "support_anchor_ids": _merge_unique_ids(existing.get("support_anchor_ids"), payload.get("support_anchor_ids")),
        "linked_concept_keys": _merge_unique_ids(existing.get("linked_concept_keys"), payload.get("linked_concept_keys")),
        "linked_thread_keys": _merge_unique_ids(existing.get("linked_thread_keys"), payload.get("linked_thread_keys")),
        "last_touched_sentence_id": str(
            payload.get("last_touched_sentence_id", "") or existing.get("last_touched_sentence_id", "") or ""
        ).strip(),
        "status": str(payload.get("status", "") or existing.get("status", "") or "").strip(),
    }
    return merged


def set_gate_state(
    state: WorkingPressureState | WorkingState,
    gate_state: GateState,
) -> WorkingPressureState | WorkingState:
    """Set the controller gate state."""

    next_state = _touch_state(state)
    next_state["gate_state"] = gate_state
    return next_state  # type: ignore[return-value]


def replace_pressure_bucket(
    state: WorkingPressureState | WorkingState,
    *,
    bucket: PressureBucket,
    items: list[WorkingPressureItem],
) -> WorkingPressureState | WorkingState:
    """Replace one local-pressure bucket."""

    next_state = _touch_state(state)
    next_state[bucket] = [dict(item) for item in items]
    return _rebuild_active_items_from_buckets(next_state)  # type: ignore[return-value]


def set_pressure_snapshot(
    state: WorkingPressureState | WorkingState,
    snapshot: PressureSnapshot,
) -> WorkingPressureState | WorkingState:
    """Replace the derived pressure snapshot."""

    next_state = _touch_state(state)
    next_state["pressure_snapshot"] = dict(snapshot)
    return next_state  # type: ignore[return-value]


def _apply_working_state_operations(
    state: WorkingPressureState | WorkingState,
    operations: list[StateOperation],
    *,
    allowed_target_stores: set[str],
) -> WorkingPressureState | WorkingState:
    """Apply explicit working-pressure mutations from node outputs."""

    next_state = dict(state)
    active_items = [dict(item) for item in _working_state_active_items(state)]
    touched = False
    for operation in operations:
        if str(operation.get("target_store", "") or "") not in allowed_target_stores:
            continue
        payload = operation.get("payload")
        if not isinstance(payload, dict):
            continue
        item_id = str(operation.get("target_key", "") or operation.get("item_id", "") or payload.get("item_id", "") or "").strip()
        if not item_id:
            continue
        operation_type = str(operation.get("op", "") or operation.get("operation_type", "") or "").strip().lower().replace("-", "_")
        existing = next((dict(item) for item in active_items if str(item.get("item_id", "") or "").strip() == item_id), {})

        if operation_type in {"append", "create", "update", "reactivate", "cool"}:
            merged_item = _merge_active_item(existing, payload, item_id=item_id)
            if operation_type in {"append", "create"} and not merged_item.get("status"):
                merged_item["status"] = "active"
            if operation_type == "reactivate" and not payload.get("status"):
                merged_item["status"] = "active"
            if operation_type == "cool" and not payload.get("status"):
                merged_item["status"] = "cooling"
            active_items = _upsert_by_id(active_items, merged_item, id_key="item_id")
            touched = True
            continue

        if operation_type in {"close", "resolve"}:
            if not existing:
                continue
            merged_item = _merge_active_item(existing, payload, item_id=item_id)
            if not payload.get("status"):
                merged_item["status"] = "resolved" if operation_type == "resolve" else "closed"
            active_items = _upsert_by_id(active_items, merged_item, id_key="item_id")
            touched = True
            continue

        if operation_type in {"link", "link_anchors"}:
            if not existing and not payload:
                continue
            merged_item = _merge_active_item(existing, payload, item_id=item_id)
            active_items = _upsert_by_id(active_items, merged_item, id_key="item_id")
            touched = True
            continue

        if operation_type == "drop":
            active_items = _remove_by_id(active_items, item_id, id_key="item_id")
            touched = True

    if not touched:
        return state

    next_state["updated_at"] = _timestamp()
    return _sync_legacy_pressure_buckets(next_state, active_items=active_items)  # type: ignore[return-value]


def apply_working_pressure_operations(
    state: WorkingPressureState,
    operations: list[StateOperation],
) -> WorkingPressureState:
    """Apply explicit working-pressure mutations from node outputs."""

    return _apply_working_state_operations(
        state,
        operations,
        allowed_target_stores={"working_pressure"},
    )  # type: ignore[return-value]


def apply_working_state_operations(
    state: WorkingState,
    operations: list[StateOperation],
) -> WorkingState:
    """Apply explicit working-state mutations from read outputs."""

    return _apply_working_state_operations(
        state,
        operations,
        allowed_target_stores={"working_state"},
    )  # type: ignore[return-value]


def push_local_buffer_sentence(
    state: LocalBufferState,
    sentence: LocalBufferSentence,
    *,
    window_size: int = 6,
) -> LocalBufferState:
    """Append one seen sentence to the rolling local buffer."""

    next_state = _touch_state(state)
    sentence_id = str(sentence.get("sentence_id", "") or "")
    recent = [dict(item) for item in state.get("recent_sentences", [])]
    recent.append(dict(sentence))
    if window_size > 0:
        recent = recent[-window_size:]
    seen_sentence_ids = [*state.get("seen_sentence_ids", [])]
    if sentence_id and sentence_id not in seen_sentence_ids:
        seen_sentence_ids.append(sentence_id)
    open_ids = [*state.get("open_meaning_unit_sentence_ids", [])]
    if sentence_id and sentence_id not in open_ids:
        open_ids.append(sentence_id)
    next_state["current_sentence_id"] = sentence_id
    next_state["current_sentence_index"] = int(sentence.get("sentence_index", 0) or 0)
    next_state["recent_sentences"] = recent
    next_state["seen_sentence_ids"] = seen_sentence_ids
    next_state["open_meaning_unit_sentence_ids"] = open_ids
    return next_state  # type: ignore[return-value]


def close_local_meaning_unit(state: LocalBufferState) -> LocalBufferState:
    """Close the current open meaning-unit span without dropping seen history."""

    next_state = _touch_state(state)
    recent_meaning_units = [
        [str(sentence_id or "") for sentence_id in unit if str(sentence_id or "")]
        for unit in state.get("recent_meaning_units", [])
        if isinstance(unit, list)
    ]
    current_unit = [sentence_id for sentence_id in state.get("open_meaning_unit_sentence_ids", []) if str(sentence_id or "")]
    if current_unit:
        recent_meaning_units.append(current_unit)
        recent_meaning_units = recent_meaning_units[-6:]
    next_state["last_meaning_unit_closed_at_sentence_id"] = str(state.get("current_sentence_id", "") or "")
    next_state["recent_meaning_units"] = recent_meaning_units
    next_state["open_meaning_unit_sentence_ids"] = []
    return next_state  # type: ignore[return-value]


def set_trigger_result(
    state: TriggerState,
    *,
    sentence_id: str,
    output: TriggerDecision,
    gate_state: GateState,
    signals: list[TriggerSignal],
    cadence_counter: int,
    callback_anchor_ids: list[str] | None = None,
) -> TriggerState:
    """Replace the current trigger result."""

    next_state = _touch_state(state)
    next_state["current_sentence_id"] = sentence_id
    next_state["output"] = output
    next_state["gate_state"] = gate_state
    next_state["signals"] = [dict(signal) for signal in signals]
    next_state["cadence_counter"] = cadence_counter
    next_state["callback_anchor_ids"] = list(callback_anchor_ids or [])
    return next_state  # type: ignore[return-value]


def upsert_anchor_record(
    state: AnchorMemoryState | AnchorBankState,
    anchor: AnchorRecord,
) -> AnchorMemoryState | AnchorBankState:
    """Upsert one anchor record by anchor id."""

    next_state = _touch_state(state)
    anchors = [dict(item) for item in state.get("anchor_records", [])]
    next_state["anchor_records"] = _upsert_by_id(anchors, dict(anchor), id_key="anchor_id")
    return next_state  # type: ignore[return-value]


def append_anchor_relation(
    state: AnchorMemoryState | AnchorBankState,
    relation: AnchorRelation,
) -> AnchorMemoryState | AnchorBankState:
    """Append or replace one anchor relation by relation id."""

    next_state = _touch_state(state)
    relations = [dict(item) for item in state.get("anchor_relations", [])]
    next_state["anchor_relations"] = _upsert_by_id(relations, dict(relation), id_key="relation_id")
    return next_state  # type: ignore[return-value]


def _apply_anchor_bank_operations(
    state: AnchorMemoryState | AnchorBankState,
    operations: list[StateOperation],
    *,
    allowed_target_stores: set[str],
) -> AnchorMemoryState | AnchorBankState:
    """Apply explicit anchor-memory mutations from read/bridge outputs."""

    next_state = state
    for operation in operations:
        if str(operation.get("target_store", "") or "") not in allowed_target_stores:
            continue
        payload = operation.get("payload")
        if not isinstance(payload, dict):
            continue
        operation_type = str(operation.get("operation_type", "") or "")

        if operation_type in {"append", "create", "update", "retain_anchor"}:
            anchor_id = str(operation.get("item_id", "") or payload.get("anchor_id", "") or "")
            sentence_start_id = str(payload.get("sentence_start_id", "") or "")
            sentence_end_id = str(payload.get("sentence_end_id", "") or sentence_start_id or "")
            quote = str(payload.get("quote", "") or "")
            if not any((anchor_id, sentence_start_id, quote)):
                continue
            anchor: AnchorRecord = {
                "anchor_id": anchor_id or f"anchor:{sentence_start_id}:{sentence_end_id}",
                "sentence_start_id": sentence_start_id,
                "sentence_end_id": sentence_end_id,
                "quote": quote,
                "locator": dict(payload.get("locator", {})) if isinstance(payload.get("locator"), dict) else {},
                "anchor_kind": str(payload.get("anchor_kind", "") or "unit_evidence"),
                "why_it_mattered": str(payload.get("why_it_mattered", "") or str(operation.get("reason", "") or "")),
                "status": str(payload.get("status", "") or "active"),
                "linked_reaction_ids": list(payload.get("linked_reaction_ids", []))
                if isinstance(payload.get("linked_reaction_ids"), list)
                else [],
                "linked_activation_ids": list(payload.get("linked_activation_ids", []))
                if isinstance(payload.get("linked_activation_ids"), list)
                else [],
            }
            next_state = upsert_anchor_record(next_state, anchor)
            continue

        if operation_type in {"link", "link_anchors"}:
            relation_id = str(operation.get("item_id", "") or payload.get("relation_id", "") or "")
            source_anchor_id = str(payload.get("source_anchor_id", "") or "")
            target_anchor_id = str(payload.get("target_anchor_id", "") or "")
            if not source_anchor_id or not target_anchor_id:
                continue
            relation: AnchorRelation = {
                "relation_id": relation_id or f"relation:{source_anchor_id}:{target_anchor_id}",
                "relation_type": str(payload.get("relation_type", "") or "echo"),
                "source_anchor_id": source_anchor_id,
                "target_anchor_id": target_anchor_id,
                "rationale": str(payload.get("rationale", "") or str(operation.get("reason", "") or "")),
            }
            next_state = append_anchor_relation(next_state, relation)
            continue

        if operation_type in {"close", "resolve"}:
            anchor_id = str(operation.get("item_id", "") or payload.get("anchor_id", "") or "")
            if not anchor_id:
                continue
            existing_anchor = next(
                (
                    dict(anchor)
                    for anchor in next_state.get("anchor_records", [])
                    if isinstance(anchor, dict) and str(anchor.get("anchor_id", "") or "") == anchor_id
                ),
                None,
            )
            if existing_anchor is None:
                continue
            existing_anchor["status"] = str(payload.get("status", "") or ("resolved" if operation_type == "resolve" else "closed"))
            next_state = upsert_anchor_record(next_state, existing_anchor)

    return next_state


def apply_anchor_memory_operations(
    state: AnchorMemoryState,
    operations: list[StateOperation],
) -> AnchorMemoryState:
    """Apply explicit anchor-memory mutations from read/bridge outputs."""

    return _apply_anchor_bank_operations(
        state,
        operations,
        allowed_target_stores={"anchor_memory"},
    )  # type: ignore[return-value]


def apply_anchor_bank_operations(
    state: AnchorBankState,
    operations: list[StateOperation],
) -> AnchorBankState:
    """Apply explicit anchor-bank mutations from read outputs."""

    return _apply_anchor_bank_operations(
        state,
        operations,
        allowed_target_stores={"anchor_bank"},
    )  # type: ignore[return-value]


def upsert_reflective_item(
    state: ReflectiveSummariesState | ReflectiveFramesState,
    *,
    bucket: ReflectiveBucket,
    item: ReflectiveItem,
) -> ReflectiveSummariesState | ReflectiveFramesState:
    """Upsert one reflective summary item inside the selected bucket."""

    next_state = _touch_state(state)
    bucket_items = [dict(existing) for existing in state.get(bucket, [])]
    next_state[bucket] = _upsert_by_id(bucket_items, dict(item), id_key="item_id")
    return next_state  # type: ignore[return-value]


def _merge_linked_ids(existing: dict[str, object], payload: dict[str, object], key: str) -> list[str]:
    """Merge one linked-id field while preserving a stable order."""

    values = [str(item or "") for item in [*existing.get(key, []), *payload.get(key, [])] if str(item or "")]
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _upsert_concept_entry(
    entries: list[dict[str, object]],
    *,
    concept_key: str,
    operation_type: str,
    payload: dict[str, object],
) -> list[dict[str, object]]:
    """Apply one concept-registry mutation to the current entries."""

    existing = next((dict(entry) for entry in entries if str(entry.get("concept_key", "") or "") == concept_key), {})
    normalized_operation = operation_type
    if normalized_operation in {"append", "create", "link"}:
        normalized_operation = "update"
    elif normalized_operation == "close":
        normalized_operation = "resolve"

    if normalized_operation == "drop":
        return [entry for entry in entries if str(entry.get("concept_key", "") or "") != concept_key]

    merged: ConceptRegistryEntry = {
        "concept_key": concept_key,
        "concept_type": str(payload.get("concept_type", "") or existing.get("concept_type", "") or "concept"),
        "status": str(
            payload.get("status", "") or existing.get("status", "") or ("resolved" if normalized_operation == "resolve" else "active")
        ),
        "summary": str(payload.get("summary", "") or existing.get("summary", "")),
        "support_anchor_ids": _merge_linked_ids(existing, payload, "support_anchor_ids"),
        "linked_thread_ids": _merge_linked_ids(existing, payload, "linked_thread_ids"),
        "last_touched_sentence_id": str(
            payload.get("last_touched_sentence_id", "") or existing.get("last_touched_sentence_id", "")
        ),
    }
    if normalized_operation == "reactivate" and not payload.get("status"):
        merged["status"] = "active"
    return _upsert_by_id([dict(entry) for entry in entries], merged, id_key="concept_key")


def apply_concept_registry_operations(
    state: ConceptRegistryState,
    operations: list[StateOperation],
) -> ConceptRegistryState:
    """Apply explicit concept-registry mutations from read outputs."""

    next_state = dict(state)
    entries = [dict(entry) for entry in state.get("entries", []) if isinstance(entry, dict)]
    touched = False
    for operation in operations:
        if str(operation.get("target_store", "") or "") != "concept_registry":
            continue
        payload = operation.get("payload")
        if not isinstance(payload, dict):
            continue
        concept_key = str(operation.get("item_id", "") or payload.get("concept_key", "") or "").strip()
        if not concept_key:
            continue
        entries = _upsert_concept_entry(
            entries,
            concept_key=concept_key,
            operation_type=str(operation.get("operation_type", "") or ""),
            payload=payload,
        )
        touched = True
    if not touched:
        return state
    next_state["entries"] = entries
    next_state["updated_at"] = _timestamp()
    return next_state  # type: ignore[return-value]


def _upsert_thread_entry(
    entries: list[dict[str, object]],
    *,
    thread_key: str,
    operation_type: str,
    payload: dict[str, object],
) -> list[dict[str, object]]:
    """Apply one thread-trace mutation to the current entries."""

    existing = next((dict(entry) for entry in entries if str(entry.get("thread_key", "") or "") == thread_key), {})
    normalized_operation = operation_type
    if normalized_operation in {"append", "create", "link"}:
        normalized_operation = "update"
    elif normalized_operation == "close":
        normalized_operation = "resolve"

    if normalized_operation == "drop":
        return [entry for entry in entries if str(entry.get("thread_key", "") or "") != thread_key]

    merged: ThreadTraceEntry = {
        "thread_key": thread_key,
        "thread_type": str(payload.get("thread_type", "") or existing.get("thread_type", "") or "thread"),
        "status": str(
            payload.get("status", "") or existing.get("status", "") or ("resolved" if normalized_operation == "resolve" else "active")
        ),
        "summary": str(payload.get("summary", "") or existing.get("summary", "")),
        "support_anchor_ids": _merge_linked_ids(existing, payload, "support_anchor_ids"),
        "linked_concept_keys": _merge_linked_ids(existing, payload, "linked_concept_keys"),
        "last_touched_sentence_id": str(
            payload.get("last_touched_sentence_id", "") or existing.get("last_touched_sentence_id", "")
        ),
        "source_anchor_id": str(payload.get("source_anchor_id", "") or existing.get("source_anchor_id", "")),
        "target_anchor_ids": _merge_linked_ids(existing, payload, "target_anchor_ids"),
    }
    if normalized_operation == "reactivate" and not payload.get("status"):
        merged["status"] = "active"
    return _upsert_by_id([dict(entry) for entry in entries], merged, id_key="thread_key")


def apply_thread_trace_operations(
    state: ThreadTraceState,
    operations: list[StateOperation],
) -> ThreadTraceState:
    """Apply explicit thread-trace mutations from read outputs."""

    next_state = dict(state)
    entries = [dict(entry) for entry in state.get("entries", []) if isinstance(entry, dict)]
    touched = False
    for operation in operations:
        if str(operation.get("target_store", "") or "") != "thread_trace":
            continue
        payload = operation.get("payload")
        if not isinstance(payload, dict):
            continue
        thread_key = str(operation.get("item_id", "") or payload.get("thread_key", "") or "").strip()
        if not thread_key:
            continue
        entries = _upsert_thread_entry(
            entries,
            thread_key=thread_key,
            operation_type=str(operation.get("operation_type", "") or ""),
            payload=payload,
        )
        touched = True
    if not touched:
        return state
    next_state["entries"] = entries
    next_state["updated_at"] = _timestamp()
    return next_state  # type: ignore[return-value]


def upsert_knowledge_activation(
    state: KnowledgeActivationsState,
    activation: KnowledgeActivation,
) -> KnowledgeActivationsState:
    """Upsert one activation by activation id."""

    next_state = _touch_state(state)
    activations = [dict(item) for item in state.get("activations", [])]
    next_state["activations"] = _upsert_by_id(activations, dict(activation), id_key="activation_id")
    return next_state  # type: ignore[return-value]


def append_move(state: MoveHistoryState, move: MoveRecord) -> MoveHistoryState:
    """Append one controller move in source order."""

    next_state = _touch_state(state)
    next_state["moves"] = [*state.get("moves", []), dict(move)]
    return next_state  # type: ignore[return-value]


def append_reaction_record(
    state: ReactionRecordsState,
    record: AnchoredReactionRecord,
) -> ReactionRecordsState:
    """Append one durable anchored reaction in occurrence order."""

    next_state = _touch_state(state)
    next_state["records"] = [*state.get("records", []), dict(record)]
    return next_state  # type: ignore[return-value]


def append_reconsolidation_record(
    state: ReconsolidationRecordsState,
    record: ReconsolidationRecord,
) -> ReconsolidationRecordsState:
    """Append one reconsolidation record in occurrence order."""

    next_state = _touch_state(state)
    next_state["records"] = [*state.get("records", []), dict(record)]
    return next_state  # type: ignore[return-value]


def supersede_reflective_item(
    state: ReflectiveSummariesState,
    *,
    bucket: ReflectiveBucket,
    item_id: str,
    superseded_by_item_id: str,
) -> ReflectiveSummariesState:
    """Mark one reflective item as superseded without mutating its statement."""

    selected_item_id = str(item_id or "")
    if not selected_item_id:
        return state

    bucket_items = [dict(existing) for existing in state.get(bucket, [])]
    touched = False
    next_bucket: list[dict[str, object]] = []
    for item in bucket_items:
        if str(item.get("item_id", "") or "") == selected_item_id:
            next_bucket.append(
                {
                    **item,
                    "status": "superseded",
                    "superseded_by_item_id": str(superseded_by_item_id or ""),
                }
            )
            touched = True
        else:
            next_bucket.append(item)

    if not touched:
        return state

    next_state = _touch_state(state)
    next_state[bucket] = next_bucket
    return next_state  # type: ignore[return-value]


def replace_policy_section(
    policy: ReaderPolicy,
    *,
    section: Literal["gate", "controller", "knowledge", "search", "bridge", "resume", "logging"],
    payload: dict[str, object],
) -> ReaderPolicy:
    """Replace one reader-policy section while preserving other policy data."""

    next_policy = _touch_state(policy)
    next_policy[section] = dict(payload)
    return next_policy  # type: ignore[return-value]

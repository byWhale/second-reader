"""Deterministic migration and legacy-adapter helpers for Phase C.3 state cutover."""

from __future__ import annotations

from .schemas import (
    ATTENTIONAL_V2_MECHANISM_VERSION,
    ATTENTIONAL_V2_SCHEMA_VERSION,
    AnchorBankState,
    AnchorMemoryState,
    ConceptRegistryEntry,
    ConceptRegistryState,
    ReflectiveFramesState,
    ReflectiveSummariesState,
    ThreadTraceEntry,
    ThreadTraceState,
    WorkingPressureState,
    WorkingState,
    build_empty_anchor_bank,
    build_empty_concept_registry,
    build_empty_reflective_frames,
    build_empty_thread_trace,
    build_empty_working_state,
)


def _clean_text(value: object) -> str:
    """Return one normalized string value."""

    return str(value or "").strip()


def _dedupe_ordered(values: list[str]) -> list[str]:
    """Return one order-preserving de-duplicated list."""

    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        clean_value = _clean_text(value)
        if not clean_value or clean_value in seen:
            continue
        seen.add(clean_value)
        ordered.append(clean_value)
    return ordered


def _anchor_inventory(anchor_records: list[dict[str, object]]) -> tuple[dict[str, dict[str, object]], dict[str, int]]:
    """Return an anchor lookup plus deterministic recency order."""

    lookup: dict[str, dict[str, object]] = {}
    order: dict[str, int] = {}
    for index, anchor in enumerate(anchor_records):
        anchor_id = _clean_text(anchor.get("anchor_id"))
        if not anchor_id:
            continue
        lookup[anchor_id] = dict(anchor)
        order[anchor_id] = index
    return lookup, order


def _sort_anchor_ids(anchor_ids: list[str], anchor_order: dict[str, int]) -> list[str]:
    """Return anchor ids sorted by recency with deterministic tie-breaks."""

    return sorted(
        _dedupe_ordered(anchor_ids),
        key=lambda anchor_id: (-int(anchor_order.get(anchor_id, -1)), anchor_id),
    )


def _last_touched_sentence_id(anchor_ids: list[str], anchor_lookup: dict[str, dict[str, object]]) -> str:
    """Return the latest sentence id visible from one support-anchor set."""

    for anchor_id in anchor_ids:
        anchor = anchor_lookup.get(anchor_id, {})
        sentence_id = _clean_text(anchor.get("sentence_end_id") or anchor.get("sentence_start_id"))
        if sentence_id:
            return sentence_id
    return ""


def migrate_working_pressure_to_working_state(
    working_pressure: WorkingPressureState | None,
    *,
    mechanism_version: str = ATTENTIONAL_V2_MECHANISM_VERSION,
) -> WorkingState:
    """Convert legacy working-pressure state into the new primary working-state shape."""

    if isinstance(working_pressure, dict) and working_pressure:
        return dict(working_pressure)  # type: ignore[return-value]
    return build_empty_working_state(mechanism_version=mechanism_version)


def migrate_reflective_summaries_to_frames(
    reflective_summaries: ReflectiveSummariesState | None,
    *,
    mechanism_version: str = ATTENTIONAL_V2_MECHANISM_VERSION,
) -> ReflectiveFramesState:
    """Convert legacy reflective summaries into the new reflective-frames shape."""

    if isinstance(reflective_summaries, dict) and reflective_summaries:
        return dict(reflective_summaries)  # type: ignore[return-value]
    return build_empty_reflective_frames(mechanism_version=mechanism_version)


def _merge_concept_entry(existing: dict[str, object], derived: ConceptRegistryEntry) -> ConceptRegistryEntry:
    """Merge one derived concept entry onto an existing richer entry."""

    status = _clean_text(derived.get("status")) or _clean_text(existing.get("status"))
    if _clean_text(existing.get("status")) == "open" or _clean_text(derived.get("status")) == "open":
        status = "open"
    return {
        "concept_key": _clean_text(derived.get("concept_key")) or _clean_text(existing.get("concept_key")),
        "concept_type": _clean_text(derived.get("concept_type")) or _clean_text(existing.get("concept_type")),
        "status": status or "active",
        "summary": _clean_text(existing.get("summary")) or _clean_text(derived.get("summary")),
        "support_anchor_ids": _dedupe_ordered(
            list(existing.get("support_anchor_ids", [])) + list(derived.get("support_anchor_ids", []))
        ),
        "linked_thread_ids": _dedupe_ordered(
            list(existing.get("linked_thread_ids", [])) + list(derived.get("linked_thread_ids", []))
        ),
        "last_touched_sentence_id": _clean_text(derived.get("last_touched_sentence_id"))
        or _clean_text(existing.get("last_touched_sentence_id")),
    }


def _merge_thread_entry(existing: dict[str, object], derived: ThreadTraceEntry) -> ThreadTraceEntry:
    """Merge one derived thread entry onto an existing richer entry."""

    status = _clean_text(derived.get("status")) or _clean_text(existing.get("status"))
    if _clean_text(existing.get("status")) == "open" or _clean_text(derived.get("status")) == "open":
        status = "open"
    return {
        "thread_key": _clean_text(derived.get("thread_key")) or _clean_text(existing.get("thread_key")),
        "thread_type": _clean_text(derived.get("thread_type")) or _clean_text(existing.get("thread_type")),
        "status": status or "active",
        "summary": _clean_text(existing.get("summary")) or _clean_text(derived.get("summary")),
        "support_anchor_ids": _dedupe_ordered(
            list(existing.get("support_anchor_ids", [])) + list(derived.get("support_anchor_ids", []))
        ),
        "linked_concept_keys": _dedupe_ordered(
            list(existing.get("linked_concept_keys", [])) + list(derived.get("linked_concept_keys", []))
        ),
        "last_touched_sentence_id": _clean_text(derived.get("last_touched_sentence_id"))
        or _clean_text(existing.get("last_touched_sentence_id")),
        "source_anchor_id": _clean_text(derived.get("source_anchor_id")) or _clean_text(existing.get("source_anchor_id")),
        "target_anchor_ids": _dedupe_ordered(
            list(existing.get("target_anchor_ids", [])) + list(derived.get("target_anchor_ids", []))
        ),
    }


def _derive_concepts_and_threads(
    *,
    anchor_records: list[dict[str, object]],
    motif_index: dict[str, list[str]],
    unresolved_reference_index: dict[str, list[str]],
    trace_links: dict[str, list[str]],
) -> tuple[list[ConceptRegistryEntry], list[ThreadTraceEntry]]:
    """Derive new semantic layers from the legacy anchor-memory indexes."""

    anchor_lookup, anchor_order = _anchor_inventory(anchor_records)
    concepts_by_key: dict[str, ConceptRegistryEntry] = {}

    concept_keys = sorted({_clean_text(key).lower() for key in [*motif_index.keys(), *unresolved_reference_index.keys()] if _clean_text(key)})
    for concept_key in concept_keys:
        support_anchor_ids = _sort_anchor_ids(
            list(motif_index.get(concept_key, [])) + list(unresolved_reference_index.get(concept_key, [])),
            anchor_order,
        )
        if not support_anchor_ids:
            continue
        in_motif = concept_key in motif_index
        in_unresolved = concept_key in unresolved_reference_index
        if in_motif and in_unresolved:
            concept_type = "motif_and_unresolved_reference"
            summary = "Recurring concept that still carries unresolved pressure."
        elif in_unresolved:
            concept_type = "unresolved_reference"
            summary = "Concept that remains unresolved across retained anchors."
        else:
            concept_type = "motif"
            summary = "Recurring concept retained across earlier anchors."
        concepts_by_key[concept_key] = {
            "concept_key": concept_key,
            "concept_type": concept_type,
            "status": "open" if in_unresolved else "active",
            "summary": summary,
            "support_anchor_ids": support_anchor_ids,
            "linked_thread_ids": [],
            "last_touched_sentence_id": _last_touched_sentence_id(support_anchor_ids, anchor_lookup),
        }

    threads_by_key: dict[str, ThreadTraceEntry] = {}
    for source_anchor_id, target_anchor_ids in trace_links.items():
        clean_source = _clean_text(source_anchor_id)
        clean_targets = _sort_anchor_ids(list(target_anchor_ids), anchor_order)
        if not clean_source or not clean_targets:
            continue
        support_anchor_ids = _sort_anchor_ids([clean_source, *clean_targets], anchor_order)
        thread_key = f"trace:{clean_source}"
        threads_by_key[thread_key] = {
            "thread_key": thread_key,
            "thread_type": "trace_link",
            "status": "active",
            "summary": "Linked trace carried across earlier and later anchors.",
            "support_anchor_ids": support_anchor_ids,
            "linked_concept_keys": [],
            "last_touched_sentence_id": _last_touched_sentence_id(support_anchor_ids, anchor_lookup),
            "source_anchor_id": clean_source,
            "target_anchor_ids": clean_targets,
        }

    for unresolved_key, anchor_ids in unresolved_reference_index.items():
        clean_key = _clean_text(unresolved_key).lower()
        support_anchor_ids = _sort_anchor_ids(list(anchor_ids), anchor_order)
        if not clean_key or not support_anchor_ids:
            continue
        thread_key = f"open:{clean_key}"
        threads_by_key[thread_key] = {
            "thread_key": thread_key,
            "thread_type": "open_reference",
            "status": "open",
            "summary": "Open unresolved line that may require later continuation or answer.",
            "support_anchor_ids": support_anchor_ids,
            "linked_concept_keys": [],
            "last_touched_sentence_id": _last_touched_sentence_id(support_anchor_ids, anchor_lookup),
            "source_anchor_id": support_anchor_ids[0],
            "target_anchor_ids": [],
        }

    for thread_key, thread in threads_by_key.items():
        linked_concept_keys: list[str] = []
        open_key = thread_key.removeprefix("open:")
        if thread_key.startswith("open:") and open_key in concepts_by_key:
            linked_concept_keys.append(open_key)
        thread_support = set(thread.get("support_anchor_ids", []))
        for concept_key, concept in concepts_by_key.items():
            if thread_support.intersection(concept.get("support_anchor_ids", [])):
                linked_concept_keys.append(concept_key)
        thread["linked_concept_keys"] = _dedupe_ordered(linked_concept_keys)

    for concept_key, concept in concepts_by_key.items():
        linked_thread_ids = [
            thread_key
            for thread_key, thread in threads_by_key.items()
            if concept_key in thread.get("linked_concept_keys", [])
        ]
        concept["linked_thread_ids"] = _dedupe_ordered(linked_thread_ids)

    concepts = sorted(concepts_by_key.values(), key=lambda item: item.get("concept_key", ""))
    threads = sorted(threads_by_key.values(), key=lambda item: item.get("thread_key", ""))
    return concepts, threads


def migrate_anchor_memory_to_new_layers(
    anchor_memory: AnchorMemoryState | None,
    *,
    existing_concept_registry: ConceptRegistryState | None = None,
    existing_thread_trace: ThreadTraceState | None = None,
    mechanism_version: str = ATTENTIONAL_V2_MECHANISM_VERSION,
) -> tuple[AnchorBankState, ConceptRegistryState, ThreadTraceState]:
    """Convert legacy anchor-memory state into the new primary semantic layers."""

    if not isinstance(anchor_memory, dict):
        return (
            build_empty_anchor_bank(mechanism_version=mechanism_version),
            build_empty_concept_registry(mechanism_version=mechanism_version),
            build_empty_thread_trace(mechanism_version=mechanism_version),
        )

    anchor_records = [dict(anchor) for anchor in anchor_memory.get("anchor_records", []) if isinstance(anchor, dict)]
    anchor_relations = [dict(relation) for relation in anchor_memory.get("anchor_relations", []) if isinstance(relation, dict)]
    anchor_bank: AnchorBankState = {
        "schema_version": int(anchor_memory.get("schema_version", ATTENTIONAL_V2_SCHEMA_VERSION) or ATTENTIONAL_V2_SCHEMA_VERSION),
        "mechanism_version": _clean_text(anchor_memory.get("mechanism_version")) or mechanism_version,
        "updated_at": _clean_text(anchor_memory.get("updated_at")),
        "anchor_records": anchor_records,
        "anchor_relations": anchor_relations,
    }

    derived_concepts, derived_threads = _derive_concepts_and_threads(
        anchor_records=anchor_records,
        motif_index={
            _clean_text(key).lower(): list(value)
            for key, value in anchor_memory.get("motif_index", {}).items()
            if _clean_text(key)
        },
        unresolved_reference_index={
            _clean_text(key).lower(): list(value)
            for key, value in anchor_memory.get("unresolved_reference_index", {}).items()
            if _clean_text(key)
        },
        trace_links={
            _clean_text(key): list(value)
            for key, value in anchor_memory.get("trace_links", {}).items()
            if _clean_text(key)
        },
    )

    concept_registry = build_empty_concept_registry(
        mechanism_version=_clean_text(anchor_bank.get("mechanism_version")) or mechanism_version
    )
    concept_registry["updated_at"] = _clean_text(anchor_bank.get("updated_at"))
    existing_concepts = {
        _clean_text(entry.get("concept_key")): dict(entry)
        for entry in (existing_concept_registry or {}).get("entries", [])
        if isinstance(entry, dict) and _clean_text(entry.get("concept_key"))
    }
    concept_registry["entries"] = [
        _merge_concept_entry(existing_concepts.get(_clean_text(entry.get("concept_key")), {}), entry)
        for entry in derived_concepts
    ]

    thread_trace = build_empty_thread_trace(
        mechanism_version=_clean_text(anchor_bank.get("mechanism_version")) or mechanism_version
    )
    thread_trace["updated_at"] = _clean_text(anchor_bank.get("updated_at"))
    existing_threads = {
        _clean_text(entry.get("thread_key")): dict(entry)
        for entry in (existing_thread_trace or {}).get("entries", [])
        if isinstance(entry, dict) and _clean_text(entry.get("thread_key"))
    }
    thread_trace["entries"] = [
        _merge_thread_entry(existing_threads.get(_clean_text(entry.get("thread_key")), {}), entry)
        for entry in derived_threads
    ]
    return anchor_bank, concept_registry, thread_trace


def migrate_legacy_runtime_state(
    *,
    working_pressure: WorkingPressureState | None,
    anchor_memory: AnchorMemoryState | None,
    reflective_summaries: ReflectiveSummariesState | None,
    existing_concept_registry: ConceptRegistryState | None = None,
    existing_thread_trace: ThreadTraceState | None = None,
    mechanism_version: str = ATTENTIONAL_V2_MECHANISM_VERSION,
) -> dict[str, object]:
    """Convert the old V2 primary runtime state territory into the new main layers."""

    working_state = migrate_working_pressure_to_working_state(
        working_pressure,
        mechanism_version=mechanism_version,
    )
    anchor_bank, concept_registry, thread_trace = migrate_anchor_memory_to_new_layers(
        anchor_memory,
        existing_concept_registry=existing_concept_registry,
        existing_thread_trace=existing_thread_trace,
        mechanism_version=mechanism_version,
    )
    reflective_frames = migrate_reflective_summaries_to_frames(
        reflective_summaries,
        mechanism_version=mechanism_version,
    )
    return {
        "working_state": working_state,
        "concept_registry": concept_registry,
        "thread_trace": thread_trace,
        "reflective_frames": reflective_frames,
        "anchor_bank": anchor_bank,
    }


def project_legacy_working_pressure(working_state: WorkingState | None) -> WorkingPressureState:
    """Project the new primary working state back into the legacy helper shape."""

    if isinstance(working_state, dict) and working_state:
        return dict(working_state)  # type: ignore[return-value]
    return build_empty_working_state()


def project_legacy_reflective_summaries(
    reflective_frames: ReflectiveFramesState | None,
) -> ReflectiveSummariesState:
    """Project the new reflective frames back into the legacy helper shape."""

    if isinstance(reflective_frames, dict) and reflective_frames:
        return dict(reflective_frames)  # type: ignore[return-value]
    return build_empty_reflective_frames()


def project_legacy_anchor_memory(
    anchor_bank: AnchorBankState | None,
    concept_registry: ConceptRegistryState | None,
    thread_trace: ThreadTraceState | None,
) -> AnchorMemoryState:
    """Project the new primary semantic layers back into the legacy anchor-memory helper shape."""

    anchor_memory: AnchorMemoryState = {
        "schema_version": int((anchor_bank or {}).get("schema_version", ATTENTIONAL_V2_SCHEMA_VERSION) or ATTENTIONAL_V2_SCHEMA_VERSION),
        "mechanism_version": _clean_text((anchor_bank or {}).get("mechanism_version")) or ATTENTIONAL_V2_MECHANISM_VERSION,
        "updated_at": _clean_text((anchor_bank or {}).get("updated_at")),
        "anchor_records": [dict(anchor) for anchor in (anchor_bank or {}).get("anchor_records", []) if isinstance(anchor, dict)],
        "anchor_relations": [dict(relation) for relation in (anchor_bank or {}).get("anchor_relations", []) if isinstance(relation, dict)],
        "motif_index": {},
        "unresolved_reference_index": {},
        "trace_links": {},
    }

    motif_index: dict[str, list[str]] = {}
    unresolved_index: dict[str, list[str]] = {}
    for entry in (concept_registry or {}).get("entries", []):
        if not isinstance(entry, dict):
            continue
        concept_key = _clean_text(entry.get("concept_key")).lower()
        support_anchor_ids = _dedupe_ordered(list(entry.get("support_anchor_ids", [])))
        concept_type = _clean_text(entry.get("concept_type"))
        status = _clean_text(entry.get("status"))
        if not concept_key or not support_anchor_ids:
            continue
        if "motif" in concept_type:
            motif_index[concept_key] = _dedupe_ordered(motif_index.get(concept_key, []) + support_anchor_ids)
        if "unresolved" in concept_type or status == "open":
            unresolved_index[concept_key] = _dedupe_ordered(unresolved_index.get(concept_key, []) + support_anchor_ids)

    trace_links: dict[str, list[str]] = {}
    for entry in (thread_trace or {}).get("entries", []):
        if not isinstance(entry, dict):
            continue
        thread_type = _clean_text(entry.get("thread_type"))
        if thread_type == "open_reference":
            open_key = _clean_text(entry.get("thread_key")).removeprefix("open:")
            support_anchor_ids = _dedupe_ordered(list(entry.get("support_anchor_ids", [])))
            if open_key and support_anchor_ids:
                unresolved_index[open_key] = _dedupe_ordered(unresolved_index.get(open_key, []) + support_anchor_ids)
            continue
        if thread_type != "trace_link":
            continue
        source_anchor_id = _clean_text(entry.get("source_anchor_id"))
        target_anchor_ids = _dedupe_ordered(list(entry.get("target_anchor_ids", [])))
        if not source_anchor_id:
            support_anchor_ids = _dedupe_ordered(list(entry.get("support_anchor_ids", [])))
            if support_anchor_ids:
                source_anchor_id = support_anchor_ids[0]
                target_anchor_ids = [anchor_id for anchor_id in support_anchor_ids[1:] if anchor_id != source_anchor_id]
        if source_anchor_id and target_anchor_ids:
            trace_links[source_anchor_id] = _dedupe_ordered(trace_links.get(source_anchor_id, []) + target_anchor_ids)

    anchor_memory["motif_index"] = motif_index
    anchor_memory["unresolved_reference_index"] = unresolved_index
    anchor_memory["trace_links"] = trace_links
    return anchor_memory

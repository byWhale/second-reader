"""Deterministic carry-forward, supplemental-context, and read-audit helpers."""

from __future__ import annotations

from pathlib import Path

from src.reading_core import BookDocument

from .schemas import (
    AnchorBankState,
    CarryForwardContext,
    CarryForwardRef,
    ConceptRegistryState,
    ContinuationCapsule,
    ContextRequest,
    MoveHistoryState,
    ReactionRecordsState,
    ReaderPolicy,
    ReflectiveFramesState,
    ThreadTraceState,
    UnitizeDecision,
)
from .state_projection import build_carry_forward_context, clean_text, context_ref_ids, matching_chapter_items
from .storage import append_jsonl, read_audit_file


def _sentence_inventory(book_document: BookDocument) -> dict[str, dict[str, object]]:
    """Return a sentence-id keyed inventory over the whole book document."""

    inventory: dict[str, dict[str, object]] = {}
    for chapter in book_document.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        chapter_ref = clean_text(chapter.get("reference")) or clean_text(chapter.get("title"))
        for sentence in chapter.get("sentences", []):
            if not isinstance(sentence, dict):
                continue
            sentence_id = clean_text(sentence.get("sentence_id"))
            if not sentence_id:
                continue
            inventory[sentence_id] = {
                **dict(sentence),
                "_chapter_ref": chapter_ref,
            }
    return inventory


def _sentence_span_text(
    sentence_inventory: dict[str, dict[str, object]],
    *,
    start_sentence_id: str,
    end_sentence_id: str,
    max_sentences: int | None = None,
) -> tuple[list[str], str, str]:
    """Return one bounded sentence span from the global sentence inventory."""

    ordered = list(sentence_inventory.keys())
    clean_start = clean_text(start_sentence_id)
    clean_end = clean_text(end_sentence_id) or clean_start
    if clean_start not in sentence_inventory or clean_end not in sentence_inventory:
        return [], "", ""
    try:
        start_index = ordered.index(clean_start)
        end_index = ordered.index(clean_end)
    except ValueError:
        return [], "", ""
    if end_index < start_index:
        start_index, end_index = end_index, start_index
    if max_sentences is not None and max_sentences > 0:
        end_index = min(end_index, start_index + max_sentences - 1)
    selected_ids = ordered[start_index : end_index + 1]
    texts = [clean_text(sentence_inventory[sentence_id].get("text")) for sentence_id in selected_ids]
    chapter_ref = clean_text(sentence_inventory[selected_ids[0]].get("_chapter_ref"))
    return selected_ids, " ".join(text for text in texts if text), chapter_ref


def _anchor_records(anchor_bank: AnchorBankState) -> list[dict[str, object]]:
    """Return normalized anchor records from the primary anchor bank."""

    return [dict(anchor) for anchor in anchor_bank.get("anchor_records", []) if isinstance(anchor, dict)]


def _linked_keys_from_digest(
    carry_forward_context: CarryForwardContext,
    *,
    digest_key: str,
    id_key: str,
) -> set[str]:
    """Return ids already present in the carried-forward digest."""

    return {
        clean_text(item.get(id_key))
        for item in carry_forward_context.get(digest_key, [])
        if isinstance(item, dict) and clean_text(item.get(id_key))
    }


def _dedupe_ref_items(items: list[dict[str, object]], *, id_key: str) -> list[dict[str, object]]:
    """Return one order-preserving deduplicated list of dict items."""

    seen: set[str] = set()
    deduped: list[dict[str, object]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = clean_text(item.get(id_key))
        if not item_id or item_id in seen:
            continue
        seen.add(item_id)
        deduped.append(dict(item))
    return deduped


def merge_supplemental_contexts(
    existing: dict[str, object] | None,
    addition: dict[str, object] | None,
) -> dict[str, object] | None:
    """Merge one newly resolved supplemental context into the accumulated bundle."""

    if not isinstance(existing, dict) or not existing:
        return dict(addition or {}) if isinstance(addition, dict) else None
    if not isinstance(addition, dict) or not addition:
        return dict(existing)

    merged: dict[str, object] = {
        "kind": "supplemental_bundle",
        "reason": " | ".join(
            reason
            for reason in (clean_text(existing.get("reason")), clean_text(addition.get("reason")))
            if reason
        ),
        "refs": _dedupe_ref_items(
            [dict(item) for item in existing.get("refs", []) if isinstance(item, dict)]
            + [dict(item) for item in addition.get("refs", []) if isinstance(item, dict)],
            id_key="ref_id",
        ),
    }
    for key, id_key in (
        ("anchors", "anchor_id"),
        ("concepts", "concept_key"),
        ("threads", "thread_key"),
        ("reactions", "reaction_id"),
        ("moves", "move_id"),
        ("reflective_items", "item_id"),
        ("excerpts", "ref_id"),
    ):
        merged_items = _dedupe_ref_items(
            [dict(item) for item in existing.get(key, []) if isinstance(item, dict)]
            + [dict(item) for item in addition.get(key, []) if isinstance(item, dict)],
            id_key=id_key,
        )
        if merged_items:
            merged[key] = merged_items
    return merged


def _current_unit_anchor_ids(
    anchor_bank: AnchorBankState,
    *,
    current_unit_sentence_ids: list[str] | None,
) -> set[str]:
    """Return anchor ids whose evidence overlaps the current chosen unit."""

    unit_ids = {clean_text(sentence_id) for sentence_id in current_unit_sentence_ids or [] if clean_text(sentence_id)}
    if not unit_ids:
        return set()
    matched: set[str] = set()
    for anchor in _anchor_records(anchor_bank):
        anchor_id = clean_text(anchor.get("anchor_id"))
        start_id = clean_text(anchor.get("sentence_start_id"))
        end_id = clean_text(anchor.get("sentence_end_id"))
        if anchor_id and (start_id in unit_ids or end_id in unit_ids):
            matched.add(anchor_id)
    return matched


def _continuation_capsule(
    carry_forward_context: CarryForwardContext,
) -> ContinuationCapsule:
    """Return the carried continuation capsule when present."""

    capsule = carry_forward_context.get("continuation_capsule", {})
    return dict(capsule) if isinstance(capsule, dict) else {}


def resolve_context_request(
    *,
    context_request: ContextRequest,
    carry_forward_context: CarryForwardContext,
    book_document: BookDocument,
    chapter_ref: str,
    anchor_bank: AnchorBankState,
    concept_registry: ConceptRegistryState,
    thread_trace: ThreadTraceState,
    reflective_frames: ReflectiveFramesState,
    move_history: MoveHistoryState,
    reaction_records: ReactionRecordsState,
    reader_policy: ReaderPolicy | None = None,
    current_unit_sentence_ids: list[str] | None = None,
) -> dict[str, object] | None:
    """Resolve one bounded supplemental-context request against persisted state."""

    kind = clean_text(context_request.get("kind"))
    reason = clean_text(context_request.get("reason"))
    requested_anchor_ids = [
        clean_text(item)
        for item in context_request.get("anchor_ids", [])
        if clean_text(item)
    ][:4]
    requested_sentence_ids = [
        clean_text(item)
        for item in context_request.get("sentence_ids", [])
        if clean_text(item)
    ][:4]
    anchor_records = carry_forward_context.get("anchor_bank_digest", {}).get("active_anchors", [])
    if not isinstance(anchor_records, list):
        anchor_records = carry_forward_context.get("anchor_digest", [])
    carry_anchor_ids = {
        clean_text(item.get("anchor_id"))
        for item in anchor_records
        if isinstance(item, dict) and clean_text(item.get("anchor_id"))
    }
    continuity_capsule = carry_forward_context.get("session_continuity_capsule", {})
    if not isinstance(continuity_capsule, dict):
        continuity_capsule = carry_forward_context.get("continuity_digest", {})
    carry_reaction_ids = {
        clean_text(item.get("reaction_id"))
        for item in continuity_capsule.get("recent_reactions", [])
        if isinstance(item, dict) and clean_text(item.get("reaction_id"))
    }
    carry_move_ids = {
        clean_text(item.get("move_id"))
        for item in continuity_capsule.get("recent_moves", [])
        if isinstance(item, dict) and clean_text(item.get("move_id"))
    }
    carry_concept_keys = _linked_keys_from_digest(
        carry_forward_context,
        digest_key="concept_digest",
        id_key="concept_key",
    )
    carry_thread_keys = _linked_keys_from_digest(
        carry_forward_context,
        digest_key="thread_digest",
        id_key="thread_key",
    )
    continuation_capsule = _continuation_capsule(carry_forward_context)
    capsule_anchor_ids = {
        clean_text(item.get("anchor_id"))
        for item in continuation_capsule.get("rehydration_entrypoints", [])
        if isinstance(item, dict) and clean_text(item.get("anchor_id"))
    }
    capsule_concept_keys = {
        clean_text(item.get("concept_key"))
        for item in continuation_capsule.get("concept_digest", [])
        if isinstance(item, dict) and clean_text(item.get("concept_key"))
    }
    capsule_thread_keys = {
        clean_text(item.get("thread_key"))
        for item in continuation_capsule.get("thread_digest", [])
        if isinstance(item, dict) and clean_text(item.get("thread_key"))
    }
    unit_anchor_ids = _current_unit_anchor_ids(
        anchor_bank,
        current_unit_sentence_ids=current_unit_sentence_ids,
    )

    if kind == "active_recall":
        refs: list[CarryForwardRef] = []
        anchors: list[dict[str, object]] = []
        anchor_records = _anchor_records(anchor_bank)
        selected_anchors = [
            dict(anchor)
            for anchor in anchor_records
            if isinstance(anchor, dict)
            and (
                (clean_text(anchor.get("anchor_id")) in requested_anchor_ids)
                or (
                    not requested_anchor_ids
                    and (
                        clean_text(anchor.get("anchor_id")) not in carry_anchor_ids
                        or clean_text(anchor.get("anchor_id")) in unit_anchor_ids
                    )
                )
            )
        ]
        if not requested_anchor_ids:
            selected_anchors.sort(
                key=lambda anchor: (
                    clean_text(anchor.get("anchor_id")) not in unit_anchor_ids,
                    clean_text(anchor.get("anchor_id")) not in capsule_anchor_ids,
                    clean_text(anchor.get("anchor_id")) in carry_anchor_ids,
                    clean_text(anchor.get("anchor_id")),
                )
            )
            selected_anchors = selected_anchors[:4]
        for anchor in selected_anchors[:4]:
            anchor_id = clean_text(anchor.get("anchor_id"))
            if not anchor_id:
                continue
            ref_id = f"anchor:{anchor_id}"
            anchors.append(
                {
                    "ref_id": ref_id,
                    "anchor_id": anchor_id,
                    "quote": clean_text(anchor.get("quote")),
                    "anchor_kind": clean_text(anchor.get("anchor_kind")),
                    "status": clean_text(anchor.get("status")),
                    "sentence_start_id": clean_text(anchor.get("sentence_start_id")),
                    "sentence_end_id": clean_text(anchor.get("sentence_end_id")),
                    "why_it_mattered": clean_text(anchor.get("why_it_mattered")),
                }
            )
            refs.append(
                {
                    "ref_id": ref_id,
                    "kind": "anchor",
                    "item_id": anchor_id,
                    "summary": clean_text(anchor.get("quote")) or clean_text(anchor.get("why_it_mattered")),
                    "anchor_id": anchor_id,
                    "sentence_id": clean_text(anchor.get("sentence_end_id") or anchor.get("sentence_start_id")),
                }
            )

        concepts: list[dict[str, object]] = []
        concept_candidates = [dict(entry) for entry in concept_registry.get("entries", []) if isinstance(entry, dict)]
        if not requested_anchor_ids and not requested_sentence_ids:
            concept_candidates.sort(
                key=lambda entry: (
                    clean_text(entry.get("concept_key")) not in carry_concept_keys,
                    clean_text(entry.get("concept_key")) not in capsule_concept_keys,
                    not unit_anchor_ids.intersection(
                        {clean_text(anchor_id) for anchor_id in entry.get("support_anchor_ids", []) if clean_text(anchor_id)}
                    ),
                    clean_text(entry.get("status")) != "open",
                    clean_text(entry.get("concept_key")),
                )
            )
        for entry in concept_candidates:
            concept_key = clean_text(entry.get("concept_key"))
            support_anchor_ids = [
                clean_text(anchor_id)
                for anchor_id in entry.get("support_anchor_ids", [])
                if clean_text(anchor_id)
            ]
            if not concept_key or (requested_anchor_ids and not set(support_anchor_ids).intersection(requested_anchor_ids)):
                continue
            ref_id = f"concept:{concept_key}"
            concepts.append(
                {
                    "ref_id": ref_id,
                    "concept_key": concept_key,
                    "concept_type": clean_text(entry.get("concept_type")),
                    "status": clean_text(entry.get("status")),
                    "summary": clean_text(entry.get("summary")),
                    "support_anchor_ids": support_anchor_ids[:4],
                    "linked_thread_ids": [
                        clean_text(thread_id)
                        for thread_id in entry.get("linked_thread_ids", [])
                        if clean_text(thread_id)
                    ][:4],
                    "last_touched_sentence_id": clean_text(entry.get("last_touched_sentence_id")),
                }
            )
            refs.append(
                {
                    "ref_id": ref_id,
                    "kind": "concept",
                    "item_id": concept_key,
                    "summary": clean_text(entry.get("summary")) or clean_text(entry.get("concept_type")),
                    "anchor_id": support_anchor_ids[0] if support_anchor_ids else "",
                    "sentence_id": clean_text(entry.get("last_touched_sentence_id")),
                }
            )
            if len(concepts) >= 3:
                break

        threads: list[dict[str, object]] = []
        thread_candidates = [dict(entry) for entry in thread_trace.get("entries", []) if isinstance(entry, dict)]
        if not requested_anchor_ids and not requested_sentence_ids:
            thread_candidates.sort(
                key=lambda entry: (
                    clean_text(entry.get("thread_key")) not in carry_thread_keys,
                    clean_text(entry.get("thread_key")) not in capsule_thread_keys,
                    not unit_anchor_ids.intersection(
                        {clean_text(anchor_id) for anchor_id in entry.get("support_anchor_ids", []) if clean_text(anchor_id)}
                    ),
                    clean_text(entry.get("status")) != "open",
                    clean_text(entry.get("thread_key")),
                )
            )
        for entry in thread_candidates:
            thread_key = clean_text(entry.get("thread_key"))
            support_anchor_ids = [
                clean_text(anchor_id)
                for anchor_id in entry.get("support_anchor_ids", [])
                if clean_text(anchor_id)
            ]
            if not thread_key or (requested_anchor_ids and not set(support_anchor_ids).intersection(requested_anchor_ids)):
                continue
            ref_id = f"thread:{thread_key}"
            threads.append(
                {
                    "ref_id": ref_id,
                    "thread_key": thread_key,
                    "thread_type": clean_text(entry.get("thread_type")),
                    "status": clean_text(entry.get("status")),
                    "summary": clean_text(entry.get("summary")),
                    "support_anchor_ids": support_anchor_ids[:4],
                    "linked_concept_keys": [
                        clean_text(concept_key)
                        for concept_key in entry.get("linked_concept_keys", [])
                        if clean_text(concept_key)
                    ][:4],
                    "last_touched_sentence_id": clean_text(entry.get("last_touched_sentence_id")),
                }
            )
            refs.append(
                {
                    "ref_id": ref_id,
                    "kind": "thread",
                    "item_id": thread_key,
                    "summary": clean_text(entry.get("summary")) or clean_text(entry.get("thread_type")),
                    "anchor_id": support_anchor_ids[0] if support_anchor_ids else "",
                    "sentence_id": clean_text(entry.get("last_touched_sentence_id")),
                }
            )
            if len(threads) >= 3:
                break

        reactions: list[dict[str, object]] = []
        for record in list(reaction_records.get("records", []))[-6:]:
            if not isinstance(record, dict):
                continue
            reaction_id = clean_text(record.get("reaction_id"))
            if not reaction_id or reaction_id in carry_reaction_ids:
                continue
            primary_anchor = dict(record.get("primary_anchor", {})) if isinstance(record.get("primary_anchor"), dict) else {}
            primary_anchor_id = clean_text(primary_anchor.get("anchor_id"))
            emitted_at_sentence_id = clean_text(record.get("emitted_at_sentence_id"))
            if requested_anchor_ids or requested_sentence_ids:
                if primary_anchor_id not in requested_anchor_ids and emitted_at_sentence_id not in requested_sentence_ids:
                    continue
            ref_id = f"reaction:{reaction_id}"
            reactions.append(
                {
                    "ref_id": ref_id,
                    "reaction_id": reaction_id,
                    "type": clean_text(record.get("type")),
                    "thought": clean_text(record.get("thought")),
                    "emitted_at_sentence_id": emitted_at_sentence_id,
                    "primary_anchor_id": primary_anchor_id,
                    "primary_anchor_quote": clean_text(primary_anchor.get("quote")),
                }
            )
            refs.append(
                {
                    "ref_id": ref_id,
                    "kind": "reaction",
                    "item_id": reaction_id,
                    "summary": clean_text(record.get("thought")) or clean_text(record.get("type")),
                    "reaction_id": reaction_id,
                    "sentence_id": emitted_at_sentence_id,
                    "anchor_id": primary_anchor_id,
                }
            )
            if len(reactions) >= 3:
                break

        moves: list[dict[str, object]] = []
        for move in list(move_history.get("moves", []))[-6:]:
            if not isinstance(move, dict):
                continue
            move_id = clean_text(move.get("move_id"))
            if not move_id or move_id in carry_move_ids:
                continue
            source_sentence_id = clean_text(move.get("source_sentence_id"))
            target_anchor_id = clean_text(move.get("target_anchor_id"))
            target_sentence_id = clean_text(move.get("target_sentence_id"))
            if requested_anchor_ids or requested_sentence_ids:
                if (
                    target_anchor_id not in requested_anchor_ids
                    and source_sentence_id not in requested_sentence_ids
                    and target_sentence_id not in requested_sentence_ids
                ):
                    continue
            ref_id = f"move:{move_id}"
            moves.append(
                {
                    "ref_id": ref_id,
                    "move_id": move_id,
                    "move_type": clean_text(move.get("move_type")),
                    "reason": clean_text(move.get("reason")),
                    "source_sentence_id": source_sentence_id,
                    "target_anchor_id": target_anchor_id,
                    "target_sentence_id": target_sentence_id,
                }
            )
            refs.append(
                {
                    "ref_id": ref_id,
                    "kind": "move",
                    "item_id": move_id,
                    "summary": clean_text(move.get("reason")) or clean_text(move.get("move_type")),
                    "move_id": move_id,
                    "sentence_id": source_sentence_id,
                    "anchor_id": target_anchor_id,
                }
            )
            if len(moves) >= 3:
                break

        reflective_items: list[dict[str, object]] = []
        for bucket, limit in (("chapter_understandings", 2), ("book_level_frames", 1)):
            for item in matching_chapter_items(
                [entry for entry in reflective_frames.get(bucket, []) if isinstance(entry, dict)],
                chapter_ref=chapter_ref,
                limit=limit,
            ):
                item_id = clean_text(item.get("item_id"))
                if not item_id:
                    continue
                ref_id = f"reflective:{item_id}"
                reflective_items.append(
                    {
                        "ref_id": ref_id,
                        "item_id": item_id,
                        "bucket": bucket,
                        "statement": clean_text(item.get("statement")),
                        "chapter_ref": clean_text(item.get("chapter_ref")),
                        "confidence_band": clean_text(item.get("confidence_band")),
                        "support_anchor_ids": list(item.get("support_anchor_ids", []))
                        if isinstance(item.get("support_anchor_ids"), list)
                        else [],
                    }
                )
                refs.append(
                    {
                        "ref_id": ref_id,
                        "kind": "reflective",
                        "item_id": item_id,
                        "summary": clean_text(item.get("statement")),
                    }
                )

        if not any((anchors, concepts, threads, reactions, moves, reflective_items)):
            return None
        return {
            "kind": "active_recall",
            "reason": reason,
            "refs": refs,
            "anchors": anchors,
            "concepts": concepts,
            "threads": threads,
            "reactions": reactions,
            "moves": moves,
            "reflective_items": reflective_items,
        }

    if kind != "look_back":
        return None

    sentence_inventory = _sentence_inventory(book_document)
    read_policy = dict(reader_policy.get("read", {})) if isinstance(reader_policy, dict) else {}
    look_back_max_sentences = max(1, int(read_policy.get("look_back_max_sentences", 8) or 8))
    excerpts: list[dict[str, object]] = []
    refs: list[CarryForwardRef] = []

    for anchor in _anchor_records(anchor_bank):
        if not isinstance(anchor, dict):
            continue
        anchor_id = clean_text(anchor.get("anchor_id"))
        if anchor_id not in requested_anchor_ids:
            continue
        sentence_ids, excerpt_text, source_chapter_ref = _sentence_span_text(
            sentence_inventory,
            start_sentence_id=clean_text(anchor.get("sentence_start_id")),
            end_sentence_id=clean_text(anchor.get("sentence_end_id")),
            max_sentences=look_back_max_sentences,
        )
        if not sentence_ids or not excerpt_text:
            continue
        ref_id = f"lookback:anchor:{anchor_id}"
        excerpts.append(
            {
                "ref_id": ref_id,
                "source_kind": "anchor",
                "anchor_id": anchor_id,
                "sentence_ids": sentence_ids,
                "chapter_ref": source_chapter_ref,
                "excerpt_text": excerpt_text,
            }
        )
        refs.append(
            {
                "ref_id": ref_id,
                "kind": "look_back_excerpt",
                "item_id": anchor_id,
                "summary": excerpt_text[:180],
                "anchor_id": anchor_id,
                "sentence_id": sentence_ids[-1],
            }
        )
        break

    for sentence_id in requested_sentence_ids:
        if excerpts:
            break
        sentence = sentence_inventory.get(sentence_id)
        if not isinstance(sentence, dict):
            continue
        ref_id = f"lookback:sentence:{sentence_id}"
        excerpts.append(
            {
                "ref_id": ref_id,
                "source_kind": "sentence",
                "anchor_id": "",
                "sentence_ids": [sentence_id],
                "chapter_ref": clean_text(sentence.get("_chapter_ref")),
                "excerpt_text": clean_text(sentence.get("text")),
            }
        )
        refs.append(
            {
                "ref_id": ref_id,
                "kind": "look_back_excerpt",
                "item_id": sentence_id,
                "summary": clean_text(sentence.get("text"))[:180],
                "sentence_id": sentence_id,
            }
        )

    if not excerpts:
        return None
    return {
        "kind": "look_back",
        "reason": reason,
        "refs": refs,
        "excerpts": excerpts,
    }


def persist_read_audit(
    output_dir: Path | None,
    *,
    chapter_id: int,
    chapter_ref: str,
    unitize_decision: UnitizeDecision,
    carry_forward_context: CarryForwardContext,
    context_request: ContextRequest | None = None,
    supplemental_context: dict[str, object] | None = None,
    supplemental_satisfied: bool = False,
    supplemental_steps: list[dict[str, object]] | None = None,
    stop_reason: str = "",
    budget_exhausted: bool = False,
    read_result: dict[str, object],
    llm_fallbacks: list[dict[str, str]] | None = None,
) -> None:
    """Append one mechanism-private read audit record."""

    if output_dir is None:
        return
    append_jsonl(
        read_audit_file(output_dir),
        {
            "chapter_id": chapter_id,
            "chapter_ref": chapter_ref,
            "unitize_decision": dict(unitize_decision),
            "carry_forward_ref_ids": sorted(context_ref_ids(carry_forward_context)),
            "context_request": dict(context_request or {}),
            "supplemental_ref_ids": sorted(context_ref_ids(supplemental_context)),
            "supplemental_satisfied": supplemental_satisfied,
            "supplemental_steps": [dict(step) for step in (supplemental_steps or []) if isinstance(step, dict)],
            "stop_reason": clean_text(stop_reason),
            "budget_exhausted": bool(budget_exhausted),
            "unit_delta": clean_text(read_result.get("unit_delta")),
            "pressure_signals": dict(read_result.get("pressure_signals") or {}),
            "surfaced_reaction_count": len(
                [item for item in read_result.get("surfaced_reactions", []) if isinstance(item, dict)]
            )
            if isinstance(read_result.get("surfaced_reactions"), list)
            else 0,
            "detour_need": dict(read_result.get("detour_need") or {})
            if isinstance(read_result.get("detour_need"), dict)
            else {},
            "llm_fallbacks": [dict(item) for item in (llm_fallbacks or []) if isinstance(item, dict)],
        },
    )

"""Deterministic carry-forward, supplemental-context, and read-audit helpers."""

from __future__ import annotations

from pathlib import Path

from src.reading_core import BookDocument

from .schemas import (
    AnchorMemoryState,
    CarryForwardContext,
    CarryForwardRef,
    ContextRequest,
    LocalBufferState,
    MoveHistoryState,
    ReactionRecordsState,
    ReaderPolicy,
    ReflectiveItem,
    ReflectiveSummariesState,
    UnitizeDecision,
    WorkingPressureState,
)
from .storage import append_jsonl, read_audit_file


def _clean_text(value: object) -> str:
    """Normalize one free-text value."""

    return str(value or "").strip()


def _matching_chapter_items(items: list[ReflectiveItem], *, chapter_ref: str, limit: int) -> list[dict[str, object]]:
    """Return chapter-matching reflective items with a bounded fallback."""

    matching = [
        dict(item)
        for item in items
        if isinstance(item, dict) and _clean_text(item.get("chapter_ref")) == _clean_text(chapter_ref)
    ]
    if matching:
        return matching[:limit]
    return [dict(item) for item in items[:limit] if isinstance(item, dict)]


def build_carry_forward_context(
    *,
    chapter_ref: str,
    current_unit_sentence_ids: list[str],
    local_buffer: LocalBufferState,
    working_pressure: WorkingPressureState,
    anchor_memory: AnchorMemoryState,
    reflective_summaries: ReflectiveSummariesState,
    move_history: MoveHistoryState,
    reaction_records: ReactionRecordsState,
) -> CarryForwardContext:
    """Build a small stable continuity packet for one formal read."""

    excluded_sentence_ids = {_clean_text(item) for item in current_unit_sentence_ids if _clean_text(item)}
    refs: list[CarryForwardRef] = []

    working_items: list[dict[str, object]] = []
    for bucket in ("local_questions", "local_tensions", "local_hypotheses", "local_motifs"):
        for item in working_pressure.get(bucket, []):
            if not isinstance(item, dict):
                continue
            item_id = _clean_text(item.get("item_id"))
            if not item_id:
                continue
            ref_id = f"pressure:{item_id}"
            summary = _clean_text(item.get("statement")) or _clean_text(item.get("kind"))
            working_items.append(
                {
                    "ref_id": ref_id,
                    "item_id": item_id,
                    "bucket": bucket,
                    "kind": _clean_text(item.get("kind")),
                    "statement": _clean_text(item.get("statement")),
                    "status": _clean_text(item.get("status")),
                    "support_anchor_ids": list(item.get("support_anchor_ids", []))
                    if isinstance(item.get("support_anchor_ids"), list)
                    else [],
                }
            )
            refs.append(
                {
                    "ref_id": ref_id,
                    "kind": "working_pressure",
                    "item_id": item_id,
                    "summary": summary,
                }
            )
            if len(working_items) >= 4:
                break
        if len(working_items) >= 4:
            break

    reflective_items: list[dict[str, object]] = []
    for bucket, limit in (
        ("chapter_understandings", 2),
        ("book_level_frames", 1),
        ("durable_definitions", 1),
    ):
        selected = _matching_chapter_items(
            [item for item in reflective_summaries.get(bucket, []) if isinstance(item, dict)],
            chapter_ref=chapter_ref,
            limit=limit,
        )
        for item in selected:
            item_id = _clean_text(item.get("item_id"))
            if not item_id:
                continue
            ref_id = f"reflective:{item_id}"
            reflective_items.append(
                {
                    "ref_id": ref_id,
                    "item_id": item_id,
                    "bucket": bucket,
                    "statement": _clean_text(item.get("statement")),
                    "chapter_ref": _clean_text(item.get("chapter_ref")),
                    "confidence_band": _clean_text(item.get("confidence_band")),
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
                    "summary": _clean_text(item.get("statement")),
                }
            )

    anchor_digest: list[dict[str, object]] = []
    for anchor in list(anchor_memory.get("anchor_records", []))[-4:]:
        if not isinstance(anchor, dict):
            continue
        anchor_id = _clean_text(anchor.get("anchor_id"))
        if not anchor_id:
            continue
        ref_id = f"anchor:{anchor_id}"
        anchor_digest.append(
            {
                "ref_id": ref_id,
                "anchor_id": anchor_id,
                "quote": _clean_text(anchor.get("quote")),
                "anchor_kind": _clean_text(anchor.get("anchor_kind")),
                "status": _clean_text(anchor.get("status")),
                "sentence_start_id": _clean_text(anchor.get("sentence_start_id")),
                "sentence_end_id": _clean_text(anchor.get("sentence_end_id")),
                "why_it_mattered": _clean_text(anchor.get("why_it_mattered")),
            }
        )
        refs.append(
            {
                "ref_id": ref_id,
                "kind": "anchor",
                "item_id": anchor_id,
                "summary": _clean_text(anchor.get("quote")) or _clean_text(anchor.get("why_it_mattered")),
                "anchor_id": anchor_id,
                "sentence_id": _clean_text(anchor.get("sentence_end_id") or anchor.get("sentence_start_id")),
            }
        )

    recent_moves: list[dict[str, object]] = []
    for move in list(move_history.get("moves", []))[-2:]:
        if not isinstance(move, dict):
            continue
        move_id = _clean_text(move.get("move_id"))
        if not move_id:
            continue
        ref_id = f"move:{move_id}"
        recent_moves.append(
            {
                "ref_id": ref_id,
                "move_id": move_id,
                "move_type": _clean_text(move.get("move_type")),
                "reason": _clean_text(move.get("reason")),
                "source_sentence_id": _clean_text(move.get("source_sentence_id")),
                "target_anchor_id": _clean_text(move.get("target_anchor_id")),
                "target_sentence_id": _clean_text(move.get("target_sentence_id")),
            }
        )
        refs.append(
            {
                "ref_id": ref_id,
                "kind": "move",
                "item_id": move_id,
                "summary": _clean_text(move.get("reason")) or _clean_text(move.get("move_type")),
                "move_id": move_id,
                "sentence_id": _clean_text(move.get("source_sentence_id")),
                "anchor_id": _clean_text(move.get("target_anchor_id")),
            }
        )

    recent_reactions: list[dict[str, object]] = []
    for record in list(reaction_records.get("records", []))[-2:]:
        if not isinstance(record, dict):
            continue
        reaction_id = _clean_text(record.get("reaction_id"))
        if not reaction_id:
            continue
        primary_anchor = dict(record.get("primary_anchor", {})) if isinstance(record.get("primary_anchor"), dict) else {}
        ref_id = f"reaction:{reaction_id}"
        recent_reactions.append(
            {
                "ref_id": ref_id,
                "reaction_id": reaction_id,
                "type": _clean_text(record.get("type")),
                "thought": _clean_text(record.get("thought")),
                "emitted_at_sentence_id": _clean_text(record.get("emitted_at_sentence_id")),
                "primary_anchor_id": _clean_text(primary_anchor.get("anchor_id")),
                "primary_anchor_quote": _clean_text(primary_anchor.get("quote")),
            }
        )
        refs.append(
            {
                "ref_id": ref_id,
                "kind": "reaction",
                "item_id": reaction_id,
                "summary": _clean_text(record.get("thought")) or _clean_text(record.get("type")),
                "reaction_id": reaction_id,
                "sentence_id": _clean_text(record.get("emitted_at_sentence_id")),
                "anchor_id": _clean_text(primary_anchor.get("anchor_id")),
            }
        )

    recent_sentence_ids = [
        _clean_text(sentence.get("sentence_id"))
        for sentence in local_buffer.get("recent_sentences", [])
        if isinstance(sentence, dict)
        and _clean_text(sentence.get("sentence_id"))
        and _clean_text(sentence.get("sentence_id")) not in excluded_sentence_ids
    ][-6:]
    recent_meaning_units = [
        [sentence_id for sentence_id in unit if _clean_text(sentence_id) and _clean_text(sentence_id) not in excluded_sentence_ids]
        for unit in local_buffer.get("recent_meaning_units", [])
        if isinstance(unit, list)
    ][-2:]

    return {
        "working_pressure_digest": {
            "gate_state": _clean_text(working_pressure.get("gate_state")),
            "pressure_snapshot": dict(working_pressure.get("pressure_snapshot", {}))
            if isinstance(working_pressure.get("pressure_snapshot"), dict)
            else {},
            "items": working_items,
        },
        "reflective_digest": reflective_items,
        "anchor_digest": anchor_digest,
        "continuity_digest": {
            "recent_sentence_ids": recent_sentence_ids,
            "recent_meaning_units": recent_meaning_units,
            "recent_moves": recent_moves,
            "recent_reactions": recent_reactions,
        },
        "refs": refs,
    }


def context_ref_ids(*contexts: dict[str, object] | None) -> set[str]:
    """Return all declared reference ids from one or more context packets."""

    ref_ids: set[str] = set()
    for context in contexts:
        if not isinstance(context, dict):
            continue
        for ref in context.get("refs", []):
            if isinstance(ref, dict) and _clean_text(ref.get("ref_id")):
                ref_ids.add(_clean_text(ref.get("ref_id")))
        if isinstance(context.get("excerpts"), list):
            for excerpt in context.get("excerpts", []):
                if isinstance(excerpt, dict) and _clean_text(excerpt.get("ref_id")):
                    ref_ids.add(_clean_text(excerpt.get("ref_id")))
    return ref_ids


def _sentence_inventory(book_document: BookDocument) -> dict[str, dict[str, object]]:
    """Return a sentence-id keyed inventory over the whole book document."""

    inventory: dict[str, dict[str, object]] = {}
    for chapter in book_document.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        chapter_ref = _clean_text(chapter.get("reference")) or _clean_text(chapter.get("title"))
        for sentence in chapter.get("sentences", []):
            if not isinstance(sentence, dict):
                continue
            sentence_id = _clean_text(sentence.get("sentence_id"))
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
) -> tuple[list[str], str, str]:
    """Return one bounded sentence span from the global sentence inventory."""

    ordered = list(sentence_inventory.keys())
    clean_start = _clean_text(start_sentence_id)
    clean_end = _clean_text(end_sentence_id) or clean_start
    if clean_start not in sentence_inventory or clean_end not in sentence_inventory:
        return [], "", ""
    try:
        start_index = ordered.index(clean_start)
        end_index = ordered.index(clean_end)
    except ValueError:
        return [], "", ""
    if end_index < start_index:
        start_index, end_index = end_index, start_index
    selected_ids = ordered[start_index : end_index + 1]
    texts = [_clean_text(sentence_inventory[sentence_id].get("text")) for sentence_id in selected_ids]
    chapter_ref = _clean_text(sentence_inventory[selected_ids[0]].get("_chapter_ref"))
    return selected_ids, " ".join(text for text in texts if text), chapter_ref


def resolve_context_request(
    *,
    context_request: ContextRequest,
    carry_forward_context: CarryForwardContext,
    book_document: BookDocument,
    chapter_ref: str,
    anchor_memory: AnchorMemoryState,
    reflective_summaries: ReflectiveSummariesState,
    move_history: MoveHistoryState,
    reaction_records: ReactionRecordsState,
    reader_policy: ReaderPolicy | None = None,
) -> dict[str, object] | None:
    """Resolve one bounded supplemental-context request against persisted state."""

    kind = _clean_text(context_request.get("kind"))
    reason = _clean_text(context_request.get("reason"))
    requested_anchor_ids = [
        _clean_text(item)
        for item in context_request.get("anchor_ids", [])
        if _clean_text(item)
    ][:4]
    requested_sentence_ids = [
        _clean_text(item)
        for item in context_request.get("sentence_ids", [])
        if _clean_text(item)
    ][:4]
    carry_anchor_ids = {
        _clean_text(item.get("anchor_id"))
        for item in carry_forward_context.get("anchor_digest", [])
        if isinstance(item, dict) and _clean_text(item.get("anchor_id"))
    }
    carry_reaction_ids = {
        _clean_text(item.get("reaction_id"))
        for item in carry_forward_context.get("continuity_digest", {}).get("recent_reactions", [])
        if isinstance(item, dict) and _clean_text(item.get("reaction_id"))
    }
    carry_move_ids = {
        _clean_text(item.get("move_id"))
        for item in carry_forward_context.get("continuity_digest", {}).get("recent_moves", [])
        if isinstance(item, dict) and _clean_text(item.get("move_id"))
    }

    if kind == "active_recall":
        refs: list[CarryForwardRef] = []
        anchors: list[dict[str, object]] = []
        selected_anchors = [
            dict(anchor)
            for anchor in anchor_memory.get("anchor_records", [])
            if isinstance(anchor, dict)
            and (
                (_clean_text(anchor.get("anchor_id")) in requested_anchor_ids)
                or (not requested_anchor_ids and _clean_text(anchor.get("anchor_id")) not in carry_anchor_ids)
            )
        ]
        if not requested_anchor_ids:
            selected_anchors = selected_anchors[-4:]
        for anchor in selected_anchors[:4]:
            anchor_id = _clean_text(anchor.get("anchor_id"))
            if not anchor_id:
                continue
            ref_id = f"anchor:{anchor_id}"
            anchors.append(
                {
                    "ref_id": ref_id,
                    "anchor_id": anchor_id,
                    "quote": _clean_text(anchor.get("quote")),
                    "anchor_kind": _clean_text(anchor.get("anchor_kind")),
                    "status": _clean_text(anchor.get("status")),
                    "sentence_start_id": _clean_text(anchor.get("sentence_start_id")),
                    "sentence_end_id": _clean_text(anchor.get("sentence_end_id")),
                    "why_it_mattered": _clean_text(anchor.get("why_it_mattered")),
                }
            )
            refs.append(
                {
                    "ref_id": ref_id,
                    "kind": "anchor",
                    "item_id": anchor_id,
                    "summary": _clean_text(anchor.get("quote")) or _clean_text(anchor.get("why_it_mattered")),
                    "anchor_id": anchor_id,
                    "sentence_id": _clean_text(anchor.get("sentence_end_id") or anchor.get("sentence_start_id")),
                }
            )

        reactions: list[dict[str, object]] = []
        for record in list(reaction_records.get("records", []))[-6:]:
            if not isinstance(record, dict):
                continue
            reaction_id = _clean_text(record.get("reaction_id"))
            if not reaction_id or reaction_id in carry_reaction_ids:
                continue
            primary_anchor = dict(record.get("primary_anchor", {})) if isinstance(record.get("primary_anchor"), dict) else {}
            primary_anchor_id = _clean_text(primary_anchor.get("anchor_id"))
            emitted_at_sentence_id = _clean_text(record.get("emitted_at_sentence_id"))
            if requested_anchor_ids or requested_sentence_ids:
                if primary_anchor_id not in requested_anchor_ids and emitted_at_sentence_id not in requested_sentence_ids:
                    continue
            ref_id = f"reaction:{reaction_id}"
            reactions.append(
                {
                    "ref_id": ref_id,
                    "reaction_id": reaction_id,
                    "type": _clean_text(record.get("type")),
                    "thought": _clean_text(record.get("thought")),
                    "emitted_at_sentence_id": emitted_at_sentence_id,
                    "primary_anchor_id": primary_anchor_id,
                    "primary_anchor_quote": _clean_text(primary_anchor.get("quote")),
                }
            )
            refs.append(
                {
                    "ref_id": ref_id,
                    "kind": "reaction",
                    "item_id": reaction_id,
                    "summary": _clean_text(record.get("thought")) or _clean_text(record.get("type")),
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
            move_id = _clean_text(move.get("move_id"))
            if not move_id or move_id in carry_move_ids:
                continue
            source_sentence_id = _clean_text(move.get("source_sentence_id"))
            target_anchor_id = _clean_text(move.get("target_anchor_id"))
            target_sentence_id = _clean_text(move.get("target_sentence_id"))
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
                    "move_type": _clean_text(move.get("move_type")),
                    "reason": _clean_text(move.get("reason")),
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
                    "summary": _clean_text(move.get("reason")) or _clean_text(move.get("move_type")),
                    "move_id": move_id,
                    "sentence_id": source_sentence_id,
                    "anchor_id": target_anchor_id,
                }
            )
            if len(moves) >= 3:
                break

        reflective_items: list[dict[str, object]] = []
        for bucket, limit in (("chapter_understandings", 2), ("book_level_frames", 1)):
            for item in _matching_chapter_items(
                [entry for entry in reflective_summaries.get(bucket, []) if isinstance(entry, dict)],
                chapter_ref=chapter_ref,
                limit=limit,
            ):
                item_id = _clean_text(item.get("item_id"))
                if not item_id:
                    continue
                ref_id = f"reflective:{item_id}"
                reflective_items.append(
                    {
                        "ref_id": ref_id,
                        "item_id": item_id,
                        "bucket": bucket,
                        "statement": _clean_text(item.get("statement")),
                        "chapter_ref": _clean_text(item.get("chapter_ref")),
                        "confidence_band": _clean_text(item.get("confidence_band")),
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
                        "summary": _clean_text(item.get("statement")),
                    }
                )

        if not any((anchors, reactions, moves, reflective_items)):
            return None
        return {
            "kind": "active_recall",
            "reason": reason,
            "refs": refs,
            "anchors": anchors,
            "reactions": reactions,
            "moves": moves,
            "reflective_items": reflective_items,
        }

    if kind != "look_back":
        return None

    sentence_inventory = _sentence_inventory(book_document)
    excerpts: list[dict[str, object]] = []
    refs: list[CarryForwardRef] = []

    for anchor in anchor_memory.get("anchor_records", []):
        if not isinstance(anchor, dict):
            continue
        anchor_id = _clean_text(anchor.get("anchor_id"))
        if anchor_id not in requested_anchor_ids:
            continue
        sentence_ids, excerpt_text, source_chapter_ref = _sentence_span_text(
            sentence_inventory,
            start_sentence_id=_clean_text(anchor.get("sentence_start_id")),
            end_sentence_id=_clean_text(anchor.get("sentence_end_id")),
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

    for sentence_id in requested_sentence_ids:
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
                "chapter_ref": _clean_text(sentence.get("_chapter_ref")),
                "excerpt_text": _clean_text(sentence.get("text")),
            }
        )
        refs.append(
            {
                "ref_id": ref_id,
                "kind": "look_back_excerpt",
                "item_id": sentence_id,
                "summary": _clean_text(sentence.get("text"))[:180],
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
    context_request: ContextRequest | None,
    supplemental_context: dict[str, object] | None,
    supplemental_satisfied: bool,
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
            "prior_material_use": dict(read_result.get("prior_material_use") or {}),
            "raw_reaction_present": bool(read_result.get("raw_reaction")),
            "move_hint": _clean_text(read_result.get("move_hint")),
            "llm_fallbacks": [dict(item) for item in (llm_fallbacks or []) if isinstance(item, dict)],
        },
    )

"""Cluster planning helpers for the human-notes-guided dataset line."""

from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from typing import Any

HUMAN_NOTES_TARGET_SOURCE_COUNT = 5
HUMAN_NOTES_MIN_CLUSTERS_TOTAL = 6
HUMAN_NOTES_MAX_CLUSTERS_TOTAL = 8
HUMAN_NOTES_MIN_CLUSTERS_PER_BOOK = 1
HUMAN_NOTES_MAX_CLUSTERS_PER_BOOK = 2


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [cleaned for item in value if (cleaned := _clean_text(item))]


def _normalize_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, Any] = {}
    for key, item in value.items():
        cleaned = _clean_text(key)
        if cleaned:
            normalized[cleaned] = item
    return normalized


def _priority(value: Any, *, fallback: int = 9999) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback
    return parsed


def _row_index(chapter_rows_by_language: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for rows in chapter_rows_by_language.values():
        for row in rows:
            chapter_case_id = _clean_text(row.get("chapter_case_id"))
            if chapter_case_id:
                index[chapter_case_id] = row
    return index


def _chapter_case_id_for_proposal(source_id: str, proposal: dict[str, Any]) -> str:
    explicit = _clean_text(proposal.get("chapter_case_id"))
    if explicit:
        return explicit
    chapter_id = _clean_text(proposal.get("chapter_id"))
    if chapter_id:
        return f"{source_id}__{chapter_id}"
    return ""


def _normalized_cross_chapter_window(
    source_id: str,
    proposal: dict[str, Any],
) -> dict[str, Any]:
    payload = proposal.get("cross_chapter_window")
    if not isinstance(payload, dict):
        return {}

    start_chapter_case_id = _clean_text(payload.get("start_chapter_case_id"))
    if not start_chapter_case_id:
        start_chapter_id = _clean_text(payload.get("start_chapter_id"))
        if start_chapter_id:
            start_chapter_case_id = f"{source_id}__{start_chapter_id}"

    end_chapter_case_id = _clean_text(payload.get("end_chapter_case_id"))
    if not end_chapter_case_id:
        end_chapter_id = _clean_text(payload.get("end_chapter_id"))
        if end_chapter_id:
            end_chapter_case_id = f"{source_id}__{end_chapter_id}"

    normalized = {
        "start_chapter_case_id": start_chapter_case_id,
        "end_chapter_case_id": end_chapter_case_id,
        "summary": _clean_text(payload.get("summary")),
        "note_refs": _normalize_string_list(payload.get("note_refs"))
        or _normalize_string_list(payload.get("artifact_refs")),
    }
    return {key: value for key, value in normalized.items() if value}


def _selection_group_id(
    source_id: str,
    chapter_case_id: str,
    cluster_id: str,
    proposal: dict[str, Any],
    guidance: dict[str, Any],
) -> str:
    if explicit := _clean_text(proposal.get("selection_group_id") or proposal.get("selection_group")):
        return explicit
    selection_group_map = (
        _normalize_mapping(guidance.get("selection_group_map"))
        or _normalize_mapping(guidance.get("selection_groups"))
    )
    chapter_id = _clean_text(proposal.get("chapter_id"))
    for key in (cluster_id, chapter_case_id, chapter_id):
        mapped = _clean_text(selection_group_map.get(key))
        if mapped:
            return mapped
    if default_group := _clean_text(guidance.get("default_selection_group")):
        return default_group
    return f"{source_id}__default"


def _normalized_proposals_for_source(
    *,
    source: dict[str, Any],
    chapter_case_index: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    source_id = _clean_text(source.get("source_id"))
    guidance = source.get("human_notes_guidance")
    guidance = guidance if isinstance(guidance, dict) else {}
    raw_proposals = guidance.get("cluster_proposals")
    if not isinstance(raw_proposals, list):
        raw_proposals = guidance.get("clusters")
    if not isinstance(raw_proposals, list):
        raw_proposals = []

    valid: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    shared_note_refs = _normalize_string_list(guidance.get("artifact_refs")) or _normalize_string_list(
        guidance.get("note_refs")
    )
    shared_summary = _clean_text(guidance.get("summary")) or " | ".join(
        _normalize_string_list(source.get("notes"))
    )

    for proposal_index, raw in enumerate(raw_proposals, start=1):
        if not isinstance(raw, dict):
            continue
        chapter_case_id = _chapter_case_id_for_proposal(source_id, raw)
        cluster_id = (
            _clean_text(raw.get("cluster_id"))
            or _clean_text(raw.get("proposal_id"))
            or f"{source_id}__cluster_{proposal_index}"
        )
        selection_group_id = _selection_group_id(
            source_id,
            chapter_case_id,
            cluster_id,
            raw,
            guidance,
        )
        proposal_payload = {
            "cluster_id": cluster_id,
            "source_id": source_id,
            "book_title": _clean_text(source.get("title")),
            "language_track": _clean_text(source.get("language")),
            "chapter_case_id": chapter_case_id,
            "selection_group_id": selection_group_id,
            "priority": _priority(raw.get("priority"), fallback=proposal_index),
            "summary": _clean_text(raw.get("summary")) or shared_summary,
            "note_artifact_refs": list(
                dict.fromkeys(
                    _normalize_string_list(raw.get("note_refs"))
                    or _normalize_string_list(raw.get("artifact_refs"))
                    or shared_note_refs
                )
            ),
            "cross_chapter_window": _normalized_cross_chapter_window(source_id, raw),
            "proposal_origin": _clean_text(raw.get("origin")) or "human_notes_guided",
        }
        row = chapter_case_index.get(chapter_case_id)
        if row is None:
            invalid.append(
                {
                    **proposal_payload,
                    "proposal_status": "invalid_missing_chapter_case",
                }
            )
            continue
        valid.append(
            {
                **proposal_payload,
                "chapter_id": _clean_text(row.get("chapter_id")),
                "chapter_title": _clean_text(row.get("chapter_title")),
                "proposal_status": "eligible",
            }
        )

    valid.sort(
        key=lambda row: (
            int(row.get("priority", 9999)),
            str(row.get("selection_group_id", "")),
            str(row.get("chapter_case_id", "")),
        )
    )
    invalid.sort(
        key=lambda row: (
            int(row.get("priority", 9999)),
            str(row.get("chapter_case_id", "")),
            str(row.get("cluster_id", "")),
        )
    )
    return valid, invalid


def _book_sort_key(source: dict[str, Any]) -> tuple[int, str]:
    return (
        _priority(source.get("selection_priority"), fallback=9999),
        _clean_text(source.get("source_id")),
    )


def _selected_cluster_payload(
    cluster: dict[str, Any],
    chapter_case_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    row = chapter_case_index[str(cluster["chapter_case_id"])]
    return {
        **deepcopy(cluster),
        "chapter_number": int(row.get("chapter_number", 0) or 0),
        "selection_status": "human_notes_guided_cluster_v1",
    }


def resolve_human_notes_guided_cluster_plan(
    chapter_rows_by_language: dict[str, list[dict[str, Any]]],
    source_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Resolve the chapter-cluster plan for the human-notes-guided dataset line."""

    chapter_case_index = _row_index(chapter_rows_by_language)
    eligible_sources: list[dict[str, Any]] = []
    skipped_sources: list[dict[str, Any]] = []
    all_proposals: list[dict[str, Any]] = []

    for source in sorted(source_index.values(), key=_book_sort_key):
        guidance = source.get("human_notes_guidance")
        guidance = guidance if isinstance(guidance, dict) else {}
        valid, invalid = _normalized_proposals_for_source(
            source=source,
            chapter_case_index=chapter_case_index,
        )
        all_proposals.extend(valid)
        all_proposals.extend(invalid)
        if valid:
            eligible_sources.append(
                {
                    "source_id": _clean_text(source.get("source_id")),
                    "book_title": _clean_text(source.get("title")),
                    "language_track": _clean_text(source.get("language")),
                    "selection_priority": _priority(source.get("selection_priority"), fallback=9999),
                    "summary": _clean_text(guidance.get("summary")) or " | ".join(
                        _normalize_string_list(source.get("notes"))
                    ),
                    "note_artifact_refs": _normalize_string_list(guidance.get("artifact_refs"))
                    or _normalize_string_list(guidance.get("note_refs")),
                    "proposals": valid,
                }
            )
        else:
            skipped_sources.append(
                {
                    "source_id": _clean_text(source.get("source_id")),
                    "book_title": _clean_text(source.get("title")),
                    "language_track": _clean_text(source.get("language")),
                    "skip_reason": "no_eligible_human_notes_clusters",
                }
            )

    if len(eligible_sources) < HUMAN_NOTES_TARGET_SOURCE_COUNT:
        raise ValueError(
            "Human-notes-guided dataset v1 requires at least 5 note-guided books with eligible cluster proposals."
        )

    selected_sources = eligible_sources[:HUMAN_NOTES_TARGET_SOURCE_COUNT]
    selected_clusters = [source["proposals"][0] for source in selected_sources]
    secondary_candidates = [
        proposal
        for source in selected_sources
        for proposal in source["proposals"][1:HUMAN_NOTES_MAX_CLUSTERS_PER_BOOK]
    ]

    target_total = min(
        HUMAN_NOTES_MAX_CLUSTERS_TOTAL,
        len(selected_clusters) + min(3, len(secondary_candidates)),
    )
    target_total = max(HUMAN_NOTES_MIN_CLUSTERS_TOTAL, target_total)
    if len(selected_clusters) + len(secondary_candidates) < target_total:
        raise ValueError(
            "Human-notes-guided dataset v1 could not reach the required 6-8 selected clusters from the available proposals."
        )

    used_selection_groups = {str(cluster["selection_group_id"]) for cluster in selected_clusters}
    secondary_candidates.sort(
        key=lambda cluster: (
            1 if str(cluster["selection_group_id"]) in used_selection_groups else 0,
            int(cluster.get("priority", 9999)),
            str(cluster.get("chapter_case_id", "")),
        )
    )
    while len(selected_clusters) < target_total and secondary_candidates:
        next_cluster = secondary_candidates.pop(0)
        selected_clusters.append(next_cluster)
        used_selection_groups.add(str(next_cluster["selection_group_id"]))

    selected_clusters = [
        _selected_cluster_payload(cluster, chapter_case_index)
        for cluster in sorted(
            selected_clusters,
            key=lambda row: (
                _clean_text(row.get("language_track")),
                _priority(
                    source_index[str(row["source_id"])].get("selection_priority"),
                    fallback=9999,
                ),
                _clean_text(row.get("source_id")),
                int(row.get("priority", 9999)),
                _clean_text(row.get("chapter_case_id")),
            ),
        )
    ]
    selected_counts = Counter(str(cluster["source_id"]) for cluster in selected_clusters)
    if any(
        count < HUMAN_NOTES_MIN_CLUSTERS_PER_BOOK or count > HUMAN_NOTES_MAX_CLUSTERS_PER_BOOK
        for count in selected_counts.values()
    ):
        raise ValueError("Human-notes-guided cluster resolution violated the 1-2 clusters per book rule.")
    if not (HUMAN_NOTES_MIN_CLUSTERS_TOTAL <= len(selected_clusters) <= HUMAN_NOTES_MAX_CLUSTERS_TOTAL):
        raise ValueError("Human-notes-guided cluster resolution violated the 6-8 total cluster rule.")

    selected_rows_by_language: dict[str, list[dict[str, Any]]] = defaultdict(list)
    selected_cluster_rows: list[dict[str, Any]] = []
    for selection_order, cluster in enumerate(selected_clusters, start=1):
        chapter_row = deepcopy(chapter_case_index[str(cluster["chapter_case_id"])])
        chapter_row["selection_group_id"] = str(cluster["selection_group_id"])
        chapter_row["cluster_id"] = str(cluster["cluster_id"])
        chapter_row["note_guided_cluster_summary"] = str(cluster.get("summary", ""))
        chapter_row["note_guided_artifact_refs"] = list(cluster.get("note_artifact_refs") or [])
        if cluster.get("cross_chapter_window"):
            chapter_row["cross_chapter_window"] = deepcopy(cluster["cross_chapter_window"])
        chapter_row["selection_status"] = "human_notes_guided_cluster_v1"
        chapter_row["selection_role"] = "human_notes_guided_cluster"
        chapter_row["cluster_selection_order"] = selection_order
        selected_rows_by_language[str(chapter_row["language_track"])].append(chapter_row)
        selected_cluster_rows.append(
            {
                **cluster,
                "selection_order": selection_order,
            }
        )

    selection_groups: dict[str, dict[str, Any]] = {}
    for cluster in selected_cluster_rows:
        selection_group_id = str(cluster["selection_group_id"])
        payload = selection_groups.setdefault(
            selection_group_id,
            {
                "selection_group_id": selection_group_id,
                "cluster_ids": [],
                "chapter_case_ids": [],
                "source_ids": [],
            },
        )
        payload["cluster_ids"].append(str(cluster["cluster_id"]))
        payload["chapter_case_ids"].append(str(cluster["chapter_case_id"]))
        payload["source_ids"].append(str(cluster["source_id"]))
    for payload in selection_groups.values():
        payload["cluster_ids"] = list(dict.fromkeys(payload["cluster_ids"]))
        payload["chapter_case_ids"] = list(dict.fromkeys(payload["chapter_case_ids"]))
        payload["source_ids"] = list(dict.fromkeys(payload["source_ids"]))

    return {
        "selected_chapter_case_ids": [str(cluster["chapter_case_id"]) for cluster in selected_cluster_rows],
        "selected_chapter_rows_by_language": {
            language: rows for language, rows in sorted(selected_rows_by_language.items())
        },
        "selected_clusters": selected_cluster_rows,
        "cluster_proposals": sorted(
            all_proposals,
            key=lambda row: (
                _clean_text(row.get("source_id")),
                int(row.get("priority", 9999)),
                _clean_text(row.get("chapter_case_id")),
                _clean_text(row.get("cluster_id")),
            ),
        ),
        "source_note_summaries": [
            {
                "source_id": str(source["source_id"]),
                "book_title": str(source["book_title"]),
                "language_track": str(source["language_track"]),
                "summary": str(source.get("summary", "")),
                "note_artifact_refs": list(source.get("note_artifact_refs") or []),
                "selected_cluster_ids": [
                    str(cluster["cluster_id"])
                    for cluster in selected_cluster_rows
                    if str(cluster["source_id"]) == str(source["source_id"])
                ],
            }
            for source in selected_sources
        ],
        "selection_groups": {
            group_id: payload for group_id, payload in sorted(selection_groups.items())
        },
        "resolution_summary": {
            "target_source_books": HUMAN_NOTES_TARGET_SOURCE_COUNT,
            "selected_source_books": len(selected_sources),
            "selected_cluster_count": len(selected_cluster_rows),
            "min_clusters_total": HUMAN_NOTES_MIN_CLUSTERS_TOTAL,
            "max_clusters_total": HUMAN_NOTES_MAX_CLUSTERS_TOTAL,
            "min_clusters_per_book": HUMAN_NOTES_MIN_CLUSTERS_PER_BOOK,
            "max_clusters_per_book": HUMAN_NOTES_MAX_CLUSTERS_PER_BOOK,
            "selected_cluster_counts_by_language": dict(
                sorted(
                    Counter(str(cluster["language_track"]) for cluster in selected_cluster_rows).items()
                )
            ),
            "selected_cluster_counts_by_source": dict(sorted(selected_counts.items())),
            "selection_group_counts": {
                group_id: len(payload["cluster_ids"])
                for group_id, payload in sorted(selection_groups.items())
            },
            "skipped_source_count": len(skipped_sources),
        },
        "skipped_sources": skipped_sources,
    }

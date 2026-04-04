"""Human-notes-guided cluster planning for Dataset V1."""

from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
import re
from typing import Any

from .library_notes import LibraryNotesPaths, load_notes_catalog


HUMAN_NOTES_GUIDED_SOURCE_IDS = (
    "value_of_others_private_en",
    "xidaduo_private_zh",
    "huochu_shengming_de_yiyi_private_zh",
    "nawaer_baodian_private_zh",
    "mangge_zhi_dao_private_zh",
)
HUMAN_NOTES_GUIDED_CASES_PER_CLUSTER = 8
HUMAN_NOTES_GUIDED_RESERVES_PER_CLUSTER = 2
HUMAN_NOTES_GUIDED_MIN_CLUSTER_SENTENCES = 80
HUMAN_NOTES_GUIDED_MAX_CLUSTER_SENTENCES = 220
HUMAN_NOTES_GUIDED_MIN_CLUSTERS_TOTAL = 6
HUMAN_NOTES_GUIDED_MAX_CLUSTERS_TOTAL = 8
HUMAN_NOTES_GUIDED_MAX_CLUSTERS_PER_BOOK = 2

HUMAN_NOTES_GUIDED_CLUSTER_BLUEPRINTS = {
    "value_of_others_private_en": [
        {
            "cluster_slug": "dense_band_41_100",
            "label": "Dense note band 41-100",
            "strategy": "page_band",
            "page_min": 41,
            "page_max": 100,
            "optional": False,
            "max_adjacent_chapters": 3,
        },
        {
            "cluster_slug": "dense_band_161_200",
            "label": "Dense note band 161-200",
            "strategy": "page_band",
            "page_min": 161,
            "page_max": 200,
            "optional": False,
            "max_adjacent_chapters": 3,
        },
    ],
    "xidaduo_private_zh": [
        {
            "cluster_slug": "late_book",
            "label": "Late-book enlightenment cluster",
            "strategy": "section_keywords",
            "keywords": ["儿子", "唵", "乔文达"],
            "optional": False,
            "max_adjacent_chapters": 3,
        },
        {
            "cluster_slug": "worldly_earlier",
            "label": "Earlier worldly-life cluster",
            "strategy": "section_keywords",
            "keywords": ["尘世间"],
            "optional": True,
            "max_adjacent_chapters": 2,
        },
    ],
    "huochu_shengming_de_yiyi_private_zh": [
        {
            "cluster_slug": "camp_experience",
            "label": "Camp experience cluster",
            "strategy": "section_keywords",
            "keywords": ["第一部分 在集中营的经历"],
            "optional": False,
            "max_adjacent_chapters": 2,
        },
        {
            "cluster_slug": "meaning_logotherapy",
            "label": "Meaning and logotherapy cluster",
            "strategy": "section_keywords",
            "keywords": [
                "追求意义",
                "作为一项技术的意义疗法",
                "为悲剧性的乐观主义辩护",
                "生命之意义",
            ],
            "optional": False,
            "max_adjacent_chapters": 3,
        },
    ],
    "nawaer_baodian_private_zh": [
        {
            "cluster_slug": "wealth",
            "label": "Wealth cluster",
            "strategy": "section_keywords",
            "keywords": ["第一章 积累财富"],
            "optional": False,
            "max_adjacent_chapters": 3,
        },
        {
            "cluster_slug": "judgment",
            "label": "Judgment cluster",
            "strategy": "section_keywords",
            "keywords": ["第二章 增强判断力"],
            "optional": False,
            "max_adjacent_chapters": 3,
        },
    ],
    "mangge_zhi_dao_private_zh": [
        {
            "cluster_slug": "speeches_2007_2010",
            "label": "2007-2010 speeches cluster",
            "strategy": "section_keywords",
            "keywords": ["2007年", "2010年"],
            "optional": False,
            "max_adjacent_chapters": 4,
        },
        {
            "cluster_slug": "speeches_2019_2020",
            "label": "2019-2020 speeches cluster",
            "strategy": "section_keywords",
            "keywords": ["2019年", "2020年"],
            "optional": False,
            "max_adjacent_chapters": 4,
        },
    ],
}


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _normalized_text(value: Any) -> str:
    return _clean_text(value).casefold()


def _page_number(value: Any) -> int | None:
    cleaned = _clean_text(value)
    if not cleaned:
        return None
    match = re.search(r"(\d+)", cleaned)
    if match is None:
        return None
    return int(match.group(1))


def _cluster_note_signal(entry: dict[str, Any]) -> str:
    parts = [
        _clean_text(entry.get("section_label")),
        _clean_text(entry.get("quote")),
        _clean_text(entry.get("note")),
        _clean_text(entry.get("chapter_hint_title")),
    ]
    return " ".join(part for part in parts if part)


def _aligned_entries_for_source(catalog: dict[str, Any], *, source_id: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for entry in catalog.get("entries", []):
        if _clean_text(entry.get("linked_source_id")) != source_id:
            continue
        if not _clean_text(entry.get("matched_chapter_id")):
            continue
        entries.append(dict(entry))
    return entries


def _notes_assets_for_source(catalog: dict[str, Any], *, source_id: str) -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    for asset in catalog.get("assets", []):
        if _clean_text(asset.get("linked_source_id")) == source_id:
            assets.append(dict(asset))
    assets.sort(key=lambda item: _clean_text(item.get("notes_id")))
    return assets


def _proposal_matches_entry(entry: dict[str, Any], proposal: dict[str, Any]) -> bool:
    strategy = proposal["strategy"]
    if strategy == "page_band":
        page_number = _page_number(entry.get("raw_locator") or entry.get("page_hint"))
        if page_number is None:
            return False
        return int(proposal["page_min"]) <= page_number <= int(proposal["page_max"])
    keywords = [_normalized_text(keyword) for keyword in proposal.get("keywords") or []]
    signal = _normalized_text(_cluster_note_signal(entry))
    return any(keyword and keyword in signal for keyword in keywords)


def _chapter_sort_index(row: dict[str, Any]) -> int:
    chapter_number = int(row.get("chapter_number", 0) or 0)
    if chapter_number > 0:
        return chapter_number
    chapter_id = _clean_text(row.get("chapter_id"))
    if chapter_id.isdigit():
        return int(chapter_id)
    return 0


def _chapter_windows(
    rows: list[dict[str, Any]],
    *,
    max_adjacent_chapters: int,
) -> list[list[dict[str, Any]]]:
    sorted_rows = sorted(rows, key=lambda row: (_chapter_sort_index(row), _clean_text(row.get("chapter_id"))))
    windows: list[list[dict[str, Any]]] = []
    for start_index in range(len(sorted_rows)):
        window = [sorted_rows[start_index]]
        windows.append(list(window))
        for next_index in range(start_index + 1, len(sorted_rows)):
            current = sorted_rows[next_index - 1]
            nxt = sorted_rows[next_index]
            if len(window) >= max_adjacent_chapters:
                break
            if _chapter_sort_index(nxt) != _chapter_sort_index(current) + 1:
                break
            window.append(nxt)
            windows.append(list(window))
    return windows


def _best_window_for_proposal(
    *,
    proposal: dict[str, Any],
    chapter_rows: list[dict[str, Any]],
    entries_by_chapter: dict[str, list[dict[str, Any]]],
    anchor_chapter_ids: set[str],
) -> list[dict[str, Any]]:
    if not chapter_rows:
        return []
    candidate_windows = _chapter_windows(
        chapter_rows,
        max_adjacent_chapters=int(proposal.get("max_adjacent_chapters", 1) or 1),
    )
    best_window: list[dict[str, Any]] = []
    best_score: tuple[int, int, int, int] | None = None
    for window in candidate_windows:
        chapter_ids = {_clean_text(row.get("chapter_id")) for row in window}
        if anchor_chapter_ids and not chapter_ids.intersection(anchor_chapter_ids):
            continue
        note_count = sum(len(entries_by_chapter.get(chapter_id, [])) for chapter_id in chapter_ids)
        sentence_count = sum(int(row.get("sentence_count", 0) or 0) for row in window)
        if sentence_count > HUMAN_NOTES_GUIDED_MAX_CLUSTER_SENTENCES and len(window) > 1:
            continue
        in_budget = int(
            len(window) == 1
            or HUMAN_NOTES_GUIDED_MIN_CLUSTER_SENTENCES <= sentence_count <= HUMAN_NOTES_GUIDED_MAX_CLUSTER_SENTENCES
        )
        score = (
            in_budget,
            note_count,
            -abs(sentence_count - 140),
            -int(window[0].get("chapter_number", 0) or 0),
        )
        if best_score is None or score > best_score:
            best_score = score
            best_window = list(window)
    return best_window


def _note_refs_for_assets(assets: list[dict[str, Any]]) -> list[str]:
    refs: list[str] = []
    for asset in assets:
        for key in ("relative_notes_path", "entries_rel_path"):
            value = _clean_text(asset.get(key))
            if value and value not in refs:
                refs.append(value)
    return refs


def _cross_chapter_window_payload(
    *,
    chapter_case_ids: list[str],
    chapter_ids: list[str],
    summary: str,
    note_refs: list[str],
) -> dict[str, Any]:
    if len(chapter_case_ids) <= 1:
        return {}
    payload = {
        "start_chapter_case_id": chapter_case_ids[0],
        "end_chapter_case_id": chapter_case_ids[-1],
        "start_chapter_id": chapter_ids[0],
        "end_chapter_id": chapter_ids[-1],
        "summary": summary,
        "note_refs": note_refs,
    }
    return {key: value for key, value in payload.items() if value}


def _proposal_priority_key(proposal: dict[str, Any], *, source_order: int) -> tuple[int, int, int, int, int]:
    return (
        0 if not bool(proposal.get("optional")) else 1,
        -int(proposal.get("note_count", 0) or 0),
        0 if bool(proposal.get("in_sentence_budget")) else 1,
        abs(int(proposal.get("sentence_count", 0) or 0) - 140),
        source_order,
    )


def _selection_order(source_id: str) -> int:
    try:
        return HUMAN_NOTES_GUIDED_SOURCE_IDS.index(source_id)
    except ValueError:
        return len(HUMAN_NOTES_GUIDED_SOURCE_IDS)


def _annotated_row(
    row: dict[str, Any],
    *,
    cluster_id: str,
    cluster_label: str,
    cluster_summary: str,
    notes: list[dict[str, Any]],
    note_artifact_refs: list[str],
    cross_chapter_window: dict[str, Any],
    selection_order: int,
) -> dict[str, Any]:
    annotated = dict(row)
    annotated["selection_group_id"] = cluster_id
    annotated["selection_group_kind"] = "notes_guided_cluster"
    annotated["selection_group_label"] = cluster_label
    annotated["selection_note_ids"] = [str(note["entry_id"]) for note in notes if _clean_text(note.get("entry_id"))]
    annotated["selection_notes"] = [
        _clean_text(note.get("quote") or note.get("note"))
        for note in notes
        if _clean_text(note.get("quote") or note.get("note"))
    ]
    annotated["selection_note_provenance"] = [
        {
            "note_id": _clean_text(note.get("entry_id")),
            "quote": _clean_text(note.get("quote")),
            "note": _clean_text(note.get("note")),
            "raw_locator": _clean_text(note.get("raw_locator")),
            "section_label": _clean_text(note.get("section_label")),
            "matched_sentence_ids": list(note.get("matched_sentence_ids") or []),
            "matched_sentence_span": deepcopy(note.get("matched_sentence_span")),
        }
        for note in notes
    ]
    annotated["selection_status"] = "human_notes_guided_cluster_v1"
    annotated["selection_role"] = "human_notes_guided_cluster"
    annotated["cluster_id"] = cluster_id
    annotated["cluster_selection_order"] = selection_order
    annotated["note_guided_cluster_summary"] = cluster_summary
    annotated["note_guided_artifact_refs"] = list(note_artifact_refs)
    if cross_chapter_window:
        annotated["cross_chapter_window"] = deepcopy(cross_chapter_window)
    return annotated


def build_human_notes_guided_cluster_plan(
    *,
    root: Path,
    source_records: list[dict[str, Any]],
    chapter_rows_by_language: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    notes_paths = LibraryNotesPaths.from_root(root)
    catalog = load_notes_catalog(notes_paths.notes_catalog_json_path)
    source_record_index = {str(record["source_id"]): record for record in source_records}
    chapter_rows_by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rows in chapter_rows_by_language.values():
        for row in rows:
            chapter_rows_by_source[str(row["source_id"])].append(dict(row))

    cluster_proposals: list[dict[str, Any]] = []
    source_summaries: list[dict[str, Any]] = []
    selected_rows_by_language: dict[str, list[dict[str, Any]]] = defaultdict(list)
    selected_clusters: list[dict[str, Any]] = []
    skipped_sources: list[dict[str, Any]] = []
    eligible_by_source: dict[str, list[dict[str, Any]]] = {}

    for source_id in HUMAN_NOTES_GUIDED_SOURCE_IDS:
        source_record = source_record_index.get(source_id)
        if source_record is None:
            skipped_sources.append(
                {
                    "source_id": source_id,
                    "skip_reason": "source_record_missing",
                }
            )
            continue
        note_assets = _notes_assets_for_source(catalog, source_id=source_id)
        aligned_entries = _aligned_entries_for_source(catalog, source_id=source_id)
        chapter_rows = [dict(row) for row in chapter_rows_by_source.get(source_id, [])]
        row_index = {_clean_text(row.get("chapter_id")): row for row in chapter_rows}
        entries_by_chapter: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for entry in aligned_entries:
            entries_by_chapter[_clean_text(entry.get("matched_chapter_id"))].append(entry)

        source_summary = {
            "source_id": source_id,
            "book_title": _clean_text(source_record.get("title")),
            "language_track": _clean_text(source_record.get("language")),
            "notes_asset_ids": [_clean_text(asset.get("notes_id")) for asset in note_assets],
            "note_artifact_refs": _note_refs_for_assets(note_assets),
            "notes_asset_count": len(note_assets),
            "aligned_entry_count": len(aligned_entries),
            "cluster_blueprint_count": len(HUMAN_NOTES_GUIDED_CLUSTER_BLUEPRINTS.get(source_id, [])),
            "eligible_cluster_count": 0,
            "selected_cluster_ids": [],
        }

        source_candidates: list[dict[str, Any]] = []
        for blueprint_index, blueprint in enumerate(HUMAN_NOTES_GUIDED_CLUSTER_BLUEPRINTS.get(source_id, []), start=1):
            proposal_entries = [entry for entry in aligned_entries if _proposal_matches_entry(entry, blueprint)]
            proposal_record = {
                "cluster_id": f"{source_id}__{blueprint['cluster_slug']}",
                "cluster_label": blueprint["label"],
                "source_id": source_id,
                "book_title": _clean_text(source_record.get("title")),
                "language_track": _clean_text(source_record.get("language")),
                "selection_group_id": f"{source_id}__{blueprint['cluster_slug']}",
                "selection_group_kind": "notes_guided_cluster",
                "selection_group_label": blueprint["label"],
                "proposal_order": blueprint_index,
                "optional": bool(blueprint.get("optional")),
                "strategy": blueprint["strategy"],
                "summary": blueprint["label"],
                "note_artifact_refs": _note_refs_for_assets(note_assets),
                "note_entry_ids": [str(entry["entry_id"]) for entry in proposal_entries],
                "note_count": len(proposal_entries),
            }
            if not proposal_entries:
                cluster_proposals.append(
                    {
                        **proposal_record,
                        "proposal_status": "no_matching_notes",
                    }
                )
                continue

            anchor_chapter_ids = {
                _clean_text(entry.get("matched_chapter_id"))
                for entry in proposal_entries
                if _clean_text(entry.get("matched_chapter_id"))
            }
            best_window = _best_window_for_proposal(
                proposal=blueprint,
                chapter_rows=chapter_rows,
                entries_by_chapter=entries_by_chapter,
                anchor_chapter_ids=anchor_chapter_ids,
            )
            if not best_window:
                cluster_proposals.append(
                    {
                        **proposal_record,
                        "proposal_status": "no_viable_chapter_window",
                    }
                )
                continue

            chapter_case_ids = [str(row["chapter_case_id"]) for row in best_window]
            chapter_ids = [_clean_text(row.get("chapter_id")) for row in best_window]
            chapter_numbers = [int(row.get("chapter_number", 0) or 0) for row in best_window]
            sentence_count = sum(int(row.get("sentence_count", 0) or 0) for row in best_window)
            in_sentence_budget = (
                len(best_window) == 1
                or HUMAN_NOTES_GUIDED_MIN_CLUSTER_SENTENCES <= sentence_count <= HUMAN_NOTES_GUIDED_MAX_CLUSTER_SENTENCES
            )
            summary = blueprint["label"]
            if blueprint["strategy"] == "page_band":
                summary = f"{blueprint['label']} (pp. {blueprint['page_min']}-{blueprint['page_max']})"
            cluster_candidate = {
                **proposal_record,
                "proposal_status": "eligible",
                "chapter_case_ids": chapter_case_ids,
                "chapter_ids": chapter_ids,
                "chapter_numbers": chapter_numbers,
                "sentence_count": sentence_count,
                "in_sentence_budget": in_sentence_budget,
                "primary_chapter_case_id": chapter_case_ids[0],
                "chapter_titles": [_clean_text(row.get("chapter_title")) for row in best_window],
                "cross_chapter_window": _cross_chapter_window_payload(
                    chapter_case_ids=chapter_case_ids,
                    chapter_ids=chapter_ids,
                    summary=summary,
                    note_refs=proposal_record["note_artifact_refs"],
                ),
            }
            source_candidates.append(cluster_candidate)
            cluster_proposals.append(cluster_candidate)

        source_summary["eligible_cluster_count"] = len(source_candidates)
        source_summaries.append(source_summary)
        if not note_assets:
            skipped_sources.append(
                {
                    "source_id": source_id,
                    "book_title": _clean_text(source_record.get("title")),
                    "language_track": _clean_text(source_record.get("language")),
                    "skip_reason": "notes_asset_missing",
                }
            )
            continue
        if not aligned_entries:
            skipped_sources.append(
                {
                    "source_id": source_id,
                    "book_title": _clean_text(source_record.get("title")),
                    "language_track": _clean_text(source_record.get("language")),
                    "skip_reason": "no_aligned_notes_entries",
                }
            )
            continue
        if not source_candidates:
            skipped_sources.append(
                {
                    "source_id": source_id,
                    "book_title": _clean_text(source_record.get("title")),
                    "language_track": _clean_text(source_record.get("language")),
                    "skip_reason": "no_eligible_clusters_from_notes",
                }
            )
            continue
        eligible_by_source[source_id] = sorted(
            source_candidates,
            key=lambda proposal: _proposal_priority_key(
                proposal,
                source_order=_selection_order(source_id),
            ),
        )

    if len(eligible_by_source) < len(HUMAN_NOTES_GUIDED_SOURCE_IDS):
        raise ValueError(
            "Human-notes-guided dataset v1 requires all 5 configured books to have linked notes assets and at least one eligible cluster."
        )

    for source_id in HUMAN_NOTES_GUIDED_SOURCE_IDS:
        selected_clusters.append(dict(eligible_by_source[source_id][0]))

    secondary_candidates = [
        dict(candidate)
        for source_id in HUMAN_NOTES_GUIDED_SOURCE_IDS
        for candidate in eligible_by_source[source_id][1:HUMAN_NOTES_GUIDED_MAX_CLUSTERS_PER_BOOK]
    ]
    secondary_candidates.sort(
        key=lambda proposal: _proposal_priority_key(
            proposal,
            source_order=_selection_order(str(proposal.get("source_id"))),
        ),
    )
    target_total = min(
        HUMAN_NOTES_GUIDED_MAX_CLUSTERS_TOTAL,
        len(selected_clusters) + min(3, len(secondary_candidates)),
    )
    target_total = max(HUMAN_NOTES_GUIDED_MIN_CLUSTERS_TOTAL, target_total)
    while len(selected_clusters) < target_total and secondary_candidates:
        selected_clusters.append(secondary_candidates.pop(0))

    selected_counts = Counter(str(cluster["source_id"]) for cluster in selected_clusters)
    if any(count > HUMAN_NOTES_GUIDED_MAX_CLUSTERS_PER_BOOK for count in selected_counts.values()):
        raise ValueError("Human-notes-guided cluster selection exceeded the 2-cluster-per-book cap.")
    if not (HUMAN_NOTES_GUIDED_MIN_CLUSTERS_TOTAL <= len(selected_clusters) <= HUMAN_NOTES_GUIDED_MAX_CLUSTERS_TOTAL):
        raise ValueError("Human-notes-guided cluster selection violated the required 6-8 total cluster range.")

    selected_clusters.sort(
        key=lambda cluster: (
            _selection_order(str(cluster.get("source_id"))),
            int(cluster.get("proposal_order", 0) or 0),
            str(cluster.get("cluster_id", "")),
        )
    )

    selection_groups: dict[str, dict[str, Any]] = {}
    for selection_order, cluster in enumerate(selected_clusters, start=1):
        cluster["selection_order"] = selection_order
        cluster["selection_status"] = "human_notes_guided_cluster_v1"
        cluster_id = str(cluster["cluster_id"])
        source_id = str(cluster["source_id"])
        aligned_entries = _aligned_entries_for_source(catalog, source_id=source_id)
        entries_by_chapter: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for entry in aligned_entries:
            entries_by_chapter[_clean_text(entry.get("matched_chapter_id"))].append(entry)
        row_lookup = {
            str(row["chapter_case_id"]): row
            for row in chapter_rows_by_source.get(source_id, [])
        }
        for chapter_case_id in cluster["chapter_case_ids"]:
            row = row_lookup[chapter_case_id]
            chapter_notes = entries_by_chapter.get(_clean_text(row.get("chapter_id")), [])
            selected_rows_by_language[_clean_text(row.get("language_track"))].append(
                _annotated_row(
                    row,
                    cluster_id=cluster_id,
                    cluster_label=str(cluster["cluster_label"]),
                    cluster_summary=str(cluster.get("summary") or cluster["cluster_label"]),
                    notes=chapter_notes,
                    note_artifact_refs=list(cluster.get("note_artifact_refs") or []),
                    cross_chapter_window=dict(cluster.get("cross_chapter_window") or {}),
                    selection_order=selection_order,
                )
            )
        selection_groups[cluster_id] = {
            "selection_group_id": cluster_id,
            "selection_group_kind": "notes_guided_cluster",
            "selection_group_label": str(cluster["cluster_label"]),
            "cluster_ids": [cluster_id],
            "chapter_case_ids": list(cluster["chapter_case_ids"]),
            "source_ids": [source_id],
            "note_entry_ids": list(cluster.get("note_entry_ids") or []),
        }
        for source_summary in source_summaries:
            if source_summary["source_id"] == source_id:
                source_summary["selected_cluster_ids"].append(cluster_id)

    for language, rows in list(selected_rows_by_language.items()):
        deduped: dict[tuple[str, str], dict[str, Any]] = {}
        for row in rows:
            dedupe_key = (
                str(row["chapter_case_id"]),
                str(row.get("selection_group_id") or row["chapter_case_id"]),
            )
            deduped[dedupe_key] = row
        selected_rows_by_language[language] = sorted(
            deduped.values(),
            key=lambda row: (
                _selection_order(str(row.get("source_id"))),
                int(row.get("cluster_selection_order", 0) or 0),
                int(row.get("chapter_number", 0) or 0),
            ),
        )

    selected_chapter_case_ids = [
        str(row["chapter_case_id"])
        for language in sorted(selected_rows_by_language)
        for row in selected_rows_by_language[language]
    ]
    source_summaries.sort(key=lambda item: _selection_order(str(item.get("source_id"))))
    cluster_proposals.sort(
        key=lambda proposal: (
            _selection_order(str(proposal.get("source_id"))),
            int(proposal.get("proposal_order", 0) or 0),
            str(proposal.get("cluster_id", "")),
        )
    )

    return {
        "selected_source_ids": list(HUMAN_NOTES_GUIDED_SOURCE_IDS),
        "selected_chapter_case_ids": selected_chapter_case_ids,
        "selected_chapter_rows_by_language": dict(selected_rows_by_language),
        "selected_rows_by_language": dict(selected_rows_by_language),
        "selected_clusters": selected_clusters,
        "clusters": selected_clusters,
        "cluster_proposals": cluster_proposals,
        "selection_groups": selection_groups,
        "source_note_summaries": source_summaries,
        "resolution_summary": {
            "target_source_books": len(HUMAN_NOTES_GUIDED_SOURCE_IDS),
            "selected_source_books": len(HUMAN_NOTES_GUIDED_SOURCE_IDS),
            "selected_cluster_count": len(selected_clusters),
            "min_clusters_total": HUMAN_NOTES_GUIDED_MIN_CLUSTERS_TOTAL,
            "max_clusters_total": HUMAN_NOTES_GUIDED_MAX_CLUSTERS_TOTAL,
            "max_clusters_per_book": HUMAN_NOTES_GUIDED_MAX_CLUSTERS_PER_BOOK,
            "selected_cluster_counts_by_language": dict(
                sorted(Counter(str(cluster["language_track"]) for cluster in selected_clusters).items())
            ),
            "selected_cluster_counts_by_source": dict(sorted(selected_counts.items())),
            "selection_group_counts": {
                group_id: len(payload["chapter_case_ids"])
                for group_id, payload in sorted(selection_groups.items())
            },
        },
        "skipped_sources": skipped_sources,
    }

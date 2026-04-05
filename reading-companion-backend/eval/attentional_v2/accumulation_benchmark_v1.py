"""Deterministic long-span benchmark artifacts for split-surface evaluation.

This module intentionally optimizes for a runnable, bounded v1:
- exactly 6 windows
- deterministic probe generation from existing reviewed excerpt rows + notes anchors
- draft/freeze-capable local datasets plus a tracked draft manifest

It does not claim to solve the full long-span review stack. Probe review automation
remains an explicit follow-up lane.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

from src.reading_runtime.provisioning import ensure_canonical_parse


ROOT = Path(__file__).resolve().parents[2]

WINDOW_CASES_FAMILY = "window_cases"
ACCUMULATION_PROBES_FAMILY = "accumulation_probes"

WINDOW_DATASET_ID = "attentional_v2_accumulation_benchmark_v1_window_cases"
PROBE_DRAFT_DATASET_ID = "attentional_v2_accumulation_benchmark_v1_probes_draft"
PROBE_FROZEN_DATASET_ID = "attentional_v2_accumulation_benchmark_v1_probes_frozen_draft"

WINDOW_DATASET_DIR = ROOT / "state" / "eval_local_datasets" / WINDOW_CASES_FAMILY / WINDOW_DATASET_ID
PROBE_DRAFT_DATASET_DIR = ROOT / "state" / "eval_local_datasets" / ACCUMULATION_PROBES_FAMILY / PROBE_DRAFT_DATASET_ID
PROBE_FROZEN_DATASET_DIR = ROOT / "state" / "eval_local_datasets" / ACCUMULATION_PROBES_FAMILY / PROBE_FROZEN_DATASET_ID

DRAFT_MANIFEST_PATH = ROOT / "eval" / "manifests" / "splits" / "attentional_v2_accumulation_benchmark_v1_draft.json"

CLUSTERED_SOURCE_MANIFESTS = (
    ROOT / "eval" / "manifests" / "source_books" / "attentional_v2_clustered_benchmark_v1_source_books.json",
    ROOT / "eval" / "manifests" / "local_refs" / "attentional_v2_clustered_benchmark_v1_local_refs.json",
)
NOTES_GUIDED_SOURCE_MANIFESTS = (
    ROOT
    / "state"
    / "dataset_build"
    / "build_runs"
    / "human_notes_guided_dataset_v1_20260404"
    / "manifests"
    / "source_books"
    / "attentional_v2_human_notes_guided_dataset_v1_source_books__scratch__human_notes_guided_dataset_v1_20260404.json",
    ROOT
    / "state"
    / "dataset_build"
    / "build_runs"
    / "human_notes_guided_dataset_v1_20260404"
    / "manifests"
    / "local_refs"
    / "attentional_v2_human_notes_guided_dataset_v1_local_refs__scratch__human_notes_guided_dataset_v1_20260404.json",
)
SOURCE_MANIFEST_PATHS = (*CLUSTERED_SOURCE_MANIFESTS, *NOTES_GUIDED_SOURCE_MANIFESTS)

REVIEWED_EXCERPT_DATASET_DIRS = (
    ROOT / "state" / "eval_local_datasets" / "excerpt_cases" / "attentional_v2_clustered_benchmark_v1_excerpt_en",
    ROOT / "state" / "eval_local_datasets" / "excerpt_cases" / "attentional_v2_clustered_benchmark_v1_excerpt_zh",
    ROOT
    / "state"
    / "eval_local_datasets"
    / "excerpt_cases"
    / "attentional_v2_human_notes_guided_dataset_v1_excerpt_en_reviewed_cluster_freeze_20260404",
    ROOT
    / "state"
    / "eval_local_datasets"
    / "excerpt_cases"
    / "attentional_v2_human_notes_guided_dataset_v1_excerpt_zh_reviewed_cluster_freeze_complete_20260404",
)

NOTES_CATALOG_PATH = ROOT / "state" / "dataset_build" / "library_notes_catalog.json"

CLUSTERED_CHAPTER_DATASET_DIRS = (
    ROOT / "state" / "eval_local_datasets" / "chapter_corpora" / "attentional_v2_clustered_benchmark_v1_chapters_en",
    ROOT / "state" / "eval_local_datasets" / "chapter_corpora" / "attentional_v2_clustered_benchmark_v1_chapters_zh",
)

WINDOW_SPECS: tuple[dict[str, Any], ...] = (
    {
        "window_case_id": "supremacy_private_en__13",
        "source_id": "supremacy_private_en",
        "language_track": "en",
        "chapter_ids": ["13"],
        "chapter_case_ids": ["supremacy_private_en__13"],
        "origin_line": "clustered_benchmark_v1",
        "window_label": "Chapter 7. Playing Games",
        "selection_reason": (
            "Keep this concise narrative AI-race chapter as a bounded within-chapter accumulation "
            "surface because it already has dense reviewed excerpt support and can be repaired by "
            "narrowing the thematic thread instead of widening to a new English source."
        ),
    },
    {
        "window_case_id": "steve_jobs_private_en__17",
        "source_id": "steve_jobs_private_en",
        "language_track": "en",
        "chapter_ids": ["17"],
        "chapter_case_ids": ["steve_jobs_private_en__17"],
        "origin_line": "clustered_benchmark_v1",
        "window_label": "Chapter Eight: Xerox and Lisa",
        "selection_reason": (
            "Keep this chapter as a bounded within-chapter accumulation surface because the book is "
            "strongly sequential and this window already carries many reviewed excerpt anchors; the "
            "first-review failure pointed at probe focus drift rather than source misfit."
        ),
    },
    {
        "window_case_id": "value_of_others_private_en__8_10",
        "source_id": "value_of_others_private_en",
        "language_track": "en",
        "chapter_ids": ["8", "9", "10"],
        "chapter_case_ids": [
            "value_of_others_private_en__8",
            "value_of_others_private_en__9",
            "value_of_others_private_en__10",
        ],
        "origin_line": "human_notes_guided_dataset_v1",
        "window_label": "Chapters 2-4 argumentative carryover arc",
        "selection_reason": (
            "Add this cross-chapter argument window because aligned human notes stay dense across all "
            "three chapters and chapter 8 already has reviewed excerpt support, giving a true "
            "carryover surface without reopening a broad builder wave."
        ),
    },
    {
        "window_case_id": "xidaduo_private_zh__13_15",
        "source_id": "xidaduo_private_zh",
        "language_track": "zh",
        "chapter_ids": ["13", "14", "15"],
        "chapter_case_ids": [
            "xidaduo_private_zh__13",
            "xidaduo_private_zh__14",
            "xidaduo_private_zh__15",
        ],
        "origin_line": "human_notes_guided_dataset_v1",
        "window_label": "儿子 / 唵 / 乔文达 late arc",
        "selection_reason": (
            "Upgrade Siddhartha from a single late chapter to a true late-book arc because the "
            "opening, middle, and final chapters all have aligned notes and the source's spiritual "
            "continuity makes it the strongest current long-span fit."
        ),
    },
    {
        "window_case_id": "huochu_shengming_de_yiyi_private_zh__8",
        "source_id": "huochu_shengming_de_yiyi_private_zh",
        "language_track": "zh",
        "chapter_ids": ["8"],
        "chapter_case_ids": ["huochu_shengming_de_yiyi_private_zh__8"],
        "origin_line": "human_notes_guided_dataset_v1",
        "window_label": "第一部分 在集中营的经历",
        "selection_reason": (
            "Keep the camp-experience chapter as a heavy single-window memory surface because one read "
            "covers many reviewed excerpt anchors and note-backed reactions, making it costly but very "
            "efficient evidence once executed."
        ),
    },
    {
        "window_case_id": "huochu_shengming_de_yiyi_private_zh__13_16",
        "source_id": "huochu_shengming_de_yiyi_private_zh",
        "language_track": "zh",
        "chapter_ids": ["13", "14", "15", "16"],
        "chapter_case_ids": [
            "huochu_shengming_de_yiyi_private_zh__13",
            "huochu_shengming_de_yiyi_private_zh__14",
            "huochu_shengming_de_yiyi_private_zh__15",
            "huochu_shengming_de_yiyi_private_zh__16",
        ],
        "origin_line": "human_notes_guided_dataset_v1",
        "window_label": "心理-动力 / 存在之虚无 / 生命之意义 / 存在之本质",
        "selection_reason": (
            "Add this compact logotherapy-definition arc because it delivers genuine cross-chapter "
            "carryover in under one hundred sentences, which is valuable for fast iteration on the "
            "accumulation surface."
        ),
    },
)

VALUE_TARGET_PROFILE_IDS = {"distinction_definition", "tension_reversal", "callback_bridge"}
LONG_SPAN_PROFILE_PRIORITY = {
    "callback_bridge": 4,
    "tension_reversal": 3,
    "distinction_definition": 3,
    "anchored_reaction_selectivity": 1,
}
STAGE_ORDER = {"early": 0, "mid": 1, "late": 2}
TARGET_PRIMARY_PROBES_PER_WINDOW = 2

BUILDER_LIMITATIONS = (
    "Probe review automation is intentionally deferred in this minimal implementation.",
    "Draft probes are deterministic, window-specific, and traceable, but they are not yet passed through a dedicated long-span review packet lane.",
    "The tracked draft manifest is immediately runnable for harness work; later freeze promotion should prefer reviewed probes when they exist.",
)


@dataclass(frozen=True)
class ExcerptSupport:
    case_id: str
    source_id: str
    chapter_id: str
    anchor_sentence_index: int
    start_sentence_id: str
    end_sentence_id: str
    excerpt_text: str
    target_profile_id: str
    selection_reason: str
    judge_focus: str
    benchmark_status: str
    book_title: str
    author: str
    output_language: str


@dataclass(frozen=True)
class NoteSupport:
    entry_id: str
    source_id: str
    chapter_id: str
    chapter_title: str
    anchor_sentence_index: int
    start_sentence_id: str
    end_sentence_id: str
    excerpt_text: str
    note_text: str
    alignment_confidence: float


WINDOW_PROBE_PLANS: dict[str, tuple[dict[str, Any], ...]] = {
    "supremacy_private_en__13": (
        {
            "selection_reason": (
                "Use the governance-autonomy thread inside chapter 13 instead of the later AlphaGo/ethical-AI topic jump. "
                "The probe should test whether the reader carries DeepMind's promised autonomy into Google's repeated reversals "
                "and the final licensing compromise."
            ),
            "judge_focus": (
                "Within chapter 13, does the reader carry forward the governance conflict around DeepMind's autonomy: "
                "from the initial promise of becoming an Alphabet company with real independence, through Google's reversal, "
                "to the later compromise where DeepMind is recast as mission-driven but still economically tied to Google?"
            ),
            "anchors": (
                {"kind": "excerpt_case", "ref": "supremacy_private_en__13__distinction_definition__reserve_1", "stage": "early"},
                {"kind": "excerpt_case", "ref": "supremacy_private_en__13__tension_reversal__seed_2", "stage": "mid"},
                {"kind": "excerpt_case", "ref": "supremacy_private_en__13__tension_reversal__seed_1", "stage": "late"},
            ),
        },
    ),
    "steve_jobs_private_en__17": (
        {
            "selection_reason": (
                "Keep one strong within-chapter probe focused on how Jobs's breakthrough vision for mass-market computing "
                "turns into implementation conflict on Lisa. This is the clearest text-grounded carryforward thread in chapter 17."
            ),
            "judge_focus": (
                "Within chapter 17, does the reader carry forward Jobs's GUI breakthrough and democratizing product vision into "
                "the later clash on the Lisa team, recognizing that the interpersonal conflict matters because it obstructs the "
                "same vision that the earlier passages make explicit?"
            ),
            "anchors": (
                {"kind": "excerpt_case", "ref": "steve_jobs_private_en__17__callback_bridge__seed_1", "stage": "early"},
                {"kind": "excerpt_case", "ref": "steve_jobs_private_en__17__tension_reversal__seed_9", "stage": "mid"},
                {"kind": "excerpt_case", "ref": "steve_jobs_private_en__17__tension_reversal__seed_3", "stage": "late"},
            ),
        },
    ),
    "value_of_others_private_en__8_10": (
        {
            "selection_reason": (
                "Use the marketplace-governs-exchange thread rather than the beauty/presentation detour. "
                "This probe is meant to show that chapters 8-10 continue one negotiation model instead of offering separate aphorisms."
            ),
            "judge_focus": (
                "Across chapters 8-10, does the reader carry forward the seller's-market captain/passenger framing into the later claim "
                "that sexual exchange still obeys general marketplace principles, using chapter 9's negotiation logic as the bridge "
                "rather than treating chapter 10 as an isolated maxim?"
            ),
            "anchors": (
                {"kind": "excerpt_case", "ref": "value_of_others_private_en__8__distinction_definition__seed_2", "stage": "early"},
                {"kind": "note_entry", "ref": "value_of_others_private_en_personal_notes__e0024", "stage": "mid"},
                {"kind": "note_entry", "ref": "value_of_others_private_en_personal_notes__e0039", "stage": "late"},
            ),
        },
    ),
    "xidaduo_private_zh__13_15": (
        {
            "selection_reason": (
                "Shift the Siddhartha window away from abstract completeness claims and toward the son's departure arc, "
                "where worldly attachment, raw suffering, and later acceptance form a visible carryforward line."
            ),
            "judge_focus": (
                "Across chapters 13-15, does the reader carry forward Siddhartha's descent into worldly attachment and pain into "
                "his later acceptance of the world, showing that the final serenity matters because the earlier chapters make the wound concrete?"
            ),
            "anchors": (
                {"kind": "note_entry", "ref": "xidaduo_private_zh_personal_notes__e0014", "stage": "early"},
                {"kind": "note_entry", "ref": "xidaduo_private_zh_personal_notes__e0019", "stage": "mid"},
                {"kind": "excerpt_case", "ref": "xidaduo_private_zh__15__tension_reversal__seed_2", "stage": "late"},
            ),
        },
        {
            "selection_reason": (
                "Keep one second Siddhartha probe on the moral-learning arc: hardship and sin, then compassion toward worldly life, "
                "then explicit acceptance of the world. This gives the window a second, still text-grounded carryforward path."
            ),
            "judge_focus": (
                "Across chapters 13-15, does the reader connect suffering and error in the earlier chapters to Siddhartha's later claim "
                "that he learned to love and accept the world, rather than reading the late acceptance passage as a free-floating aphorism?"
            ),
            "anchors": (
                {"kind": "note_entry", "ref": "xidaduo_private_zh_personal_notes__e0012", "stage": "early"},
                {"kind": "note_entry", "ref": "xidaduo_private_zh_personal_notes__e0016", "stage": "mid"},
                {"kind": "note_entry", "ref": "xidaduo_private_zh_personal_notes__e0025", "stage": "late"},
            ),
        },
    ),
    "huochu_shengming_de_yiyi_private_zh__8": (
        {
            "selection_reason": (
                "Use the strongest single-chapter carryover inside chapter 8: concrete bodily adaptation first, then the later claim "
                "that suffering itself must be faced as meaningful work."
            ),
            "judge_focus": (
                "Within chapter 8, does the reader carry forward the concrete evidence of human adaptation under camp suffering into the later "
                "claim that enduring suffering itself becomes a meaningful task, instead of reading the later passage as generic stoicism?"
            ),
            "anchors": (
                {"kind": "excerpt_case", "ref": "huochu_shengming_de_yiyi_private_zh__8__distinction_definition__seed_2", "stage": "early"},
                {"kind": "excerpt_case", "ref": "huochu_shengming_de_yiyi_private_zh__8__tension_reversal__seed_1", "stage": "late"},
            ),
        },
        {
            "selection_reason": (
                "Keep one second chapter-8 probe centered on the dying young woman's response and Frankl's later suffering frame. "
                "This is narrower and more explicit than the older beauty-to-suffering pairing."
            ),
            "judge_focus": (
                "Within chapter 8, does the reader connect the dying young woman's grateful acceptance of suffering to the later claim that "
                "suffering must be faced as a task, rather than treating the later statement as a separate philosophical aside?"
            ),
            "anchors": (
                {"kind": "excerpt_case", "ref": "huochu_shengming_de_yiyi_private_zh__8__tension_reversal__seed_4", "stage": "early"},
                {"kind": "excerpt_case", "ref": "huochu_shengming_de_yiyi_private_zh__8__tension_reversal__seed_1", "stage": "late"},
            ),
        },
    ),
    "huochu_shengming_de_yiyi_private_zh__13_16": (
        {
            "selection_reason": (
                "Use the cleanest meaning/responsibility arc in the later Frankl window rather than forcing three separate abstract claims together. "
                "This probe keeps the carryforward on one line: why meaning sustains life, why responsibility matters, and how meaning is concretely found."
            ),
            "judge_focus": (
                "Across chapters 13-16, does the reader carry forward Frankl's claim that people survive through meaning into his later account of "
                "responsibility and the three concrete routes to meaning, treating the late chapter as an answer to the earlier need rather than as an isolated list?"
            ),
            "anchors": (
                {"kind": "note_entry", "ref": "huochu_shengming_de_yiyi_private_zh_personal_notes__e0045", "stage": "early"},
                {"kind": "note_entry", "ref": "huochu_shengming_de_yiyi_private_zh_personal_notes__e0053", "stage": "mid"},
                {"kind": "note_entry", "ref": "huochu_shengming_de_yiyi_private_zh_personal_notes__e0056", "stage": "late"},
            ),
        },
        {
            "selection_reason": (
                "Keep a second Frankl probe on tension and vacuum: healthy tension first, then existential boredom, then the later move that meaning "
                "must be found in the world. This stays explicit enough to judge and avoids the old generic prompting."
            ),
            "judge_focus": (
                "Across chapters 13-16, does the reader carry forward Frankl's argument that healthy human life requires tension into the later diagnosis "
                "of existential vacuum and finally into the claim that meaning must be found in the world rather than inside the self?"
            ),
            "anchors": (
                {"kind": "note_entry", "ref": "huochu_shengming_de_yiyi_private_zh_personal_notes__e0046", "stage": "early"},
                {"kind": "note_entry", "ref": "huochu_shengming_de_yiyi_private_zh_personal_notes__e0049", "stage": "mid"},
                {"kind": "note_entry", "ref": "huochu_shengming_de_yiyi_private_zh_personal_notes__e0054", "stage": "late"},
            ),
        },
    ),
}


def _json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _jsonl_dump(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object JSON at {path}")
    return payload


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _sentence_index(sentence_id: object) -> int:
    match = re.search(r"-s(\d+)$", str(sentence_id or ""))
    return int(match.group(1)) if match else 0


def _chapter_ids_are_contiguous(chapter_ids: list[str]) -> bool:
    values = [int(item) for item in chapter_ids if str(item).isdigit()]
    if len(values) <= 1:
        return True
    return all(current == previous + 1 for previous, current in zip(values, values[1:]))


def _source_index() -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for manifest_path in SOURCE_MANIFEST_PATHS:
        payload = _load_json(manifest_path)
        if isinstance(payload.get("books"), list):
            entries = payload["books"]
        elif isinstance(payload.get("source_refs"), list):
            entries = payload["source_refs"]
        else:
            entries = []
        for item in entries:
            if not isinstance(item, dict):
                continue
            source_id = _clean_text(item.get("source_id"))
            if not source_id:
                continue
            existing = index.get(source_id, {})
            merged = {**existing, **item}
            index[source_id] = merged
    return index


def _clustered_chapter_rows() -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for dataset_dir in CLUSTERED_CHAPTER_DATASET_DIRS:
        manifest = _load_json(dataset_dir / "manifest.json")
        for row in _load_jsonl(dataset_dir / str(manifest["primary_file"])):
            chapter_case_id = _clean_text(row.get("chapter_case_id"))
            if chapter_case_id:
                rows[chapter_case_id] = dict(row)
    return rows


def _notes_catalog() -> dict[str, Any]:
    return _load_json(NOTES_CATALOG_PATH)


def _notes_entries_for(source_id: str, *, chapter_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in _notes_catalog().get("entries", []):
        if not isinstance(entry, dict):
            continue
        if _clean_text(entry.get("linked_source_id")) != source_id:
            continue
        if _clean_text(entry.get("matched_chapter_id")) != chapter_id:
            continue
        span = dict(entry.get("matched_sentence_span") or {})
        if not _clean_text(span.get("start_sentence_id")) or not _clean_text(span.get("end_sentence_id")):
            continue
        rows.append(dict(entry))
    rows.sort(
        key=lambda item: (
            -float(item.get("alignment_confidence", 0.0) or 0.0),
            _clean_text(item.get("entry_id")),
        )
    )
    return rows


def _reviewed_excerpt_supports() -> dict[tuple[str, str], list[ExcerptSupport]]:
    grouped: dict[tuple[str, str], list[ExcerptSupport]] = defaultdict(list)
    for dataset_dir in REVIEWED_EXCERPT_DATASET_DIRS:
        manifest = _load_json(dataset_dir / "manifest.json")
        for raw in _load_jsonl(dataset_dir / str(manifest["primary_file"])):
            if _clean_text(raw.get("benchmark_status")) != "reviewed_active":
                continue
            support = ExcerptSupport(
                case_id=_clean_text(raw.get("case_id")),
                source_id=_clean_text(raw.get("source_id")),
                chapter_id=_clean_text(raw.get("chapter_id")),
                anchor_sentence_index=int(raw.get("anchor_sentence_index", 0) or 0),
                start_sentence_id=_clean_text(raw.get("start_sentence_id")),
                end_sentence_id=_clean_text(raw.get("end_sentence_id")),
                excerpt_text=_clean_text(raw.get("excerpt_text")),
                target_profile_id=_clean_text(raw.get("target_profile_id")),
                selection_reason=_clean_text(raw.get("selection_reason")),
                judge_focus=_clean_text(raw.get("judge_focus")),
                benchmark_status=_clean_text(raw.get("benchmark_status")),
                book_title=_clean_text(raw.get("book_title")),
                author=_clean_text(raw.get("author")),
                output_language=_clean_text(raw.get("output_language")),
            )
            grouped[(support.source_id, support.chapter_id)].append(support)
    for rows in grouped.values():
        rows.sort(key=lambda item: (item.anchor_sentence_index, item.case_id))
    return grouped


def _reviewed_excerpt_case_index() -> dict[str, ExcerptSupport]:
    index: dict[str, ExcerptSupport] = {}
    for rows in _reviewed_excerpt_supports().values():
        for row in rows:
            index.setdefault(row.case_id, row)
    return index


def _note_support_index() -> dict[str, NoteSupport]:
    index: dict[str, NoteSupport] = {}
    for entry in _notes_catalog().get("entries", []):
        if not isinstance(entry, dict):
            continue
        source_id = _clean_text(entry.get("linked_source_id"))
        chapter_id = _clean_text(entry.get("matched_chapter_id"))
        span = dict(entry.get("matched_sentence_span") or {})
        start_sentence_id = _clean_text(span.get("start_sentence_id"))
        end_sentence_id = _clean_text(span.get("end_sentence_id"))
        entry_id = _clean_text(entry.get("entry_id"))
        if not source_id or not chapter_id or not entry_id or not start_sentence_id or not end_sentence_id:
            continue
        index[entry_id] = NoteSupport(
            entry_id=entry_id,
            source_id=source_id,
            chapter_id=chapter_id,
            chapter_title=_clean_text(entry.get("section_label") or entry.get("chapter_hint_title")),
            anchor_sentence_index=_sentence_index(start_sentence_id),
            start_sentence_id=start_sentence_id,
            end_sentence_id=end_sentence_id,
            excerpt_text=_clean_text(entry.get("quote")),
            note_text=_clean_text(entry.get("note")),
            alignment_confidence=float(entry.get("alignment_confidence", 0.0) or 0.0),
        )
    return index


def _window_spec(window_case_id: str) -> dict[str, Any]:
    for spec in WINDOW_SPECS:
        if spec["window_case_id"] == window_case_id:
            return dict(spec)
    raise KeyError(window_case_id)


def _book_document_for(source_id: str, *, language_track: str, source_index: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], Any]:
    source = dict(source_index[source_id])
    book_path = ROOT / str(source["relative_local_path"])
    provisioned = ensure_canonical_parse(book_path, language_mode=language_track)
    if provisioned.book_document is None:
        raise RuntimeError(f"Missing canonical parse for {source_id}")
    return source, provisioned


def build_window_rows(root: Path | None = None) -> list[dict[str, Any]]:
    _ = root  # Reserved for future non-default roots.
    source_index = _source_index()
    clustered_rows = _clustered_chapter_rows()
    window_rows: list[dict[str, Any]] = []
    for spec in WINDOW_SPECS:
        source, provisioned = _book_document_for(
            spec["source_id"],
            language_track=str(spec["language_track"]),
            source_index=source_index,
        )
        chapter_map = {
            _clean_text(chapter.get("id")): dict(chapter)
            for chapter in provisioned.book_document.get("chapters", [])
            if isinstance(chapter, dict)
        }
        chapter_titles: list[str] = []
        sentence_count_total = 0
        for chapter_id in spec["chapter_ids"]:
            chapter = chapter_map.get(chapter_id)
            if chapter is None:
                raise ValueError(f"Missing chapter {chapter_id} for {spec['window_case_id']}")
            chapter_titles.append(_clean_text(chapter.get("title")))
            sentence_count_total += len([item for item in chapter.get("sentences", []) if isinstance(item, dict)])
        clustered_row = clustered_rows.get(spec["chapter_case_ids"][0], {})
        row = {
            "window_case_id": spec["window_case_id"],
            "source_id": spec["source_id"],
            "book_title": provisioned.title,
            "author": provisioned.author,
            "language_track": spec["language_track"],
            "output_language": spec["language_track"],
            "window_kind": "cross_chapter" if len(spec["chapter_ids"]) > 1 else "single_chapter",
            "chapter_ids": list(spec["chapter_ids"]),
            "chapter_numbers": [int(item) for item in spec["chapter_ids"] if str(item).isdigit()],
            "chapter_case_ids": list(spec["chapter_case_ids"]),
            "chapter_titles": chapter_titles,
            "window_title": _clean_text(spec.get("window_label")) or " / ".join(chapter_titles),
            "selection_group_id": spec["window_case_id"],
            "selection_group_label": _clean_text(spec.get("window_label")) or " / ".join(chapter_titles),
            "sentence_count_total": sentence_count_total,
            "sentence_count": sentence_count_total,
            "origin_line": spec["origin_line"],
            "benchmark_line": spec["origin_line"],
            "selection_role": _clean_text(clustered_row.get("selection_role")) or "long_span_window",
            "selection_status": _clean_text(clustered_row.get("selection_status")) or "bounded_long_span_window_v1",
            "selection_reason": _clean_text(spec.get("selection_reason")),
            "contiguous_chapters": _chapter_ids_are_contiguous(list(spec["chapter_ids"])),
            "cross_chapter_window": (
                {
                    "start_chapter_id": spec["chapter_ids"][0],
                    "end_chapter_id": spec["chapter_ids"][-1],
                    "start_chapter_case_id": spec["chapter_case_ids"][0],
                    "end_chapter_case_id": spec["chapter_case_ids"][-1],
                    "summary": _clean_text(spec.get("window_label")),
                }
                if len(spec["chapter_ids"]) > 1
                else None
            ),
            "relative_local_path": _clean_text(source.get("relative_local_path")),
        }
        window_rows.append(row)
    return window_rows


def _excerpt_anchor(case: ExcerptSupport, *, stage: str, chapter_order: int) -> dict[str, Any]:
    return {
        "anchor_id": f"excerpt::{case.case_id}",
        "stage": stage,
        "anchor_kind": "excerpt_case",
        "source_ref_id": case.case_id,
        "source_case_id": case.case_id,
        "chapter_id": case.chapter_id,
        "chapter_order": chapter_order,
        "start_sentence_id": case.start_sentence_id,
        "end_sentence_id": case.end_sentence_id,
        "anchor_sentence_index": case.anchor_sentence_index,
        "excerpt_text": case.excerpt_text,
        "target_profile_id": case.target_profile_id,
        "selection_reason": case.selection_reason,
        "judge_focus": case.judge_focus,
        "chapter_title": "",
    }


def _note_anchor(entry: NoteSupport, *, stage: str, chapter_order: int) -> dict[str, Any]:
    return {
        "anchor_id": f"note::{entry.entry_id}",
        "stage": stage,
        "anchor_kind": "note_entry",
        "source_ref_id": entry.entry_id,
        "source_case_id": "",
        "chapter_id": entry.chapter_id,
        "chapter_order": chapter_order,
        "start_sentence_id": entry.start_sentence_id,
        "end_sentence_id": entry.end_sentence_id,
        "anchor_sentence_index": entry.anchor_sentence_index,
        "excerpt_text": entry.excerpt_text,
        "target_profile_id": "",
        "selection_reason": entry.note_text,
        "judge_focus": "",
        "alignment_confidence": entry.alignment_confidence,
        "chapter_title": entry.chapter_title,
    }


def _chapter_title_map(window_row: dict[str, Any]) -> dict[str, str]:
    return {
        _clean_text(chapter_id): _clean_text(chapter_title)
        for chapter_id, chapter_title in zip(window_row.get("chapter_ids", []), window_row.get("chapter_titles", []))
    }


def _anchor_priority(anchor: dict[str, Any]) -> float:
    if _clean_text(anchor.get("anchor_kind")) == "note_entry":
        return 2.0 + min(0.9, float(anchor.get("alignment_confidence", 0.0) or 0.0) / 100.0)
    return float(LONG_SPAN_PROFILE_PRIORITY.get(_clean_text(anchor.get("target_profile_id")), 0))


def _anchor_distance_score(anchors: list[dict[str, Any]]) -> float:
    if len(anchors) < 2:
        return 0.0
    total = 0.0
    for previous, current in zip(anchors, anchors[1:]):
        chapter_gap = max(0, int(current.get("chapter_order", 0) or 0) - int(previous.get("chapter_order", 0) or 0))
        sentence_gap = abs(int(current.get("anchor_sentence_index", 0) or 0) - int(previous.get("anchor_sentence_index", 0) or 0))
        total += chapter_gap * 1000 + sentence_gap
    return total


def _ordered_probe_anchors(anchors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        anchors,
        key=lambda anchor: (
            int(anchor.get("chapter_order", 0) or 0),
            STAGE_ORDER.get(_clean_text(anchor.get("stage")), 99),
            int(anchor.get("anchor_sentence_index", 0) or 0),
            _clean_text(anchor.get("source_ref_id")),
        ),
    )


def _resolve_planned_anchor(
    anchor_spec: dict[str, Any],
    *,
    window_row: dict[str, Any],
    excerpt_index: dict[str, ExcerptSupport],
    note_index: dict[str, NoteSupport],
) -> dict[str, Any]:
    kind = _clean_text(anchor_spec.get("kind"))
    ref = _clean_text(anchor_spec.get("ref"))
    stage = _clean_text(anchor_spec.get("stage")) or "mid"
    chapter_order_map = {
        _clean_text(chapter_id): index
        for index, chapter_id in enumerate(window_row.get("chapter_ids", []))
    }
    chapter_titles = _chapter_title_map(window_row)
    if kind == "excerpt_case":
        case = excerpt_index.get(ref)
        if case is None:
            raise ValueError(f"Missing excerpt support {ref} for {window_row['window_case_id']}")
        chapter_order = chapter_order_map.get(case.chapter_id)
        if chapter_order is None:
            raise ValueError(f"Excerpt support chapter {case.chapter_id} is outside {window_row['window_case_id']}")
        anchor = _excerpt_anchor(case, stage=stage, chapter_order=chapter_order)
        anchor["chapter_title"] = chapter_titles.get(case.chapter_id, "")
        return anchor
    if kind == "note_entry":
        entry = note_index.get(ref)
        if entry is None:
            raise ValueError(f"Missing note support {ref} for {window_row['window_case_id']}")
        chapter_order = chapter_order_map.get(entry.chapter_id)
        if chapter_order is None:
            raise ValueError(f"Note support chapter {entry.chapter_id} is outside {window_row['window_case_id']}")
        anchor = _note_anchor(entry, stage=stage, chapter_order=chapter_order)
        if not anchor.get("chapter_title"):
            anchor["chapter_title"] = chapter_titles.get(entry.chapter_id, "")
        return anchor
    raise ValueError(f"Unsupported planned anchor kind {kind!r}")


def _planned_probe_payloads(
    window_row: dict[str, Any],
    *,
    excerpt_index: dict[str, ExcerptSupport],
    note_index: dict[str, NoteSupport],
) -> list[dict[str, Any]]:
    plans = WINDOW_PROBE_PLANS.get(_clean_text(window_row.get("window_case_id")))
    if not plans:
        raise ValueError(f"Missing window probe plan for {window_row['window_case_id']}")
    payloads: list[dict[str, Any]] = []
    seen: set[tuple[str, ...]] = set()
    for plan in plans:
        anchors = _ordered_probe_anchors([
            _resolve_planned_anchor(
                dict(anchor_spec),
                window_row=window_row,
                excerpt_index=excerpt_index,
                note_index=note_index,
            )
            for anchor_spec in plan.get("anchors", [])
        ])
        if len(anchors) < 2:
            continue
        if not all(
            _clean_text(anchor.get("chapter_id"))
            and _clean_text(anchor.get("start_sentence_id"))
            and _clean_text(anchor.get("end_sentence_id"))
            for anchor in anchors
        ):
            continue
        chapter_orders = [int(anchor.get("chapter_order", 0) or 0) for anchor in anchors]
        if chapter_orders != sorted(chapter_orders):
            continue
        if len(window_row.get("chapter_ids", [])) > 1:
            if min(chapter_orders) == max(chapter_orders):
                continue
        elif _anchor_distance_score(anchors) < 3:
            continue
        key = tuple(f"{_clean_text(anchor.get('anchor_kind'))}:{_clean_text(anchor.get('source_ref_id'))}" for anchor in anchors)
        if key in seen:
            continue
        seen.add(key)
        payloads.append(
            {
                "anchors": anchors,
                "selection_reason": _clean_text(plan.get("selection_reason")),
                "judge_focus": _clean_text(plan.get("judge_focus")),
            }
        )
    return payloads


def _probe_type(anchors: list[dict[str, Any]]) -> str:
    chapter_ids = {_clean_text(anchor.get("chapter_id")) for anchor in anchors}
    if len(chapter_ids) > 1:
        return "cross_chapter_carryover"
    if len(anchors) >= 3:
        return "single_chapter_full_span"
    return "single_chapter_carryover"


def _probe_selection_reason(window_row: dict[str, Any], anchors: list[dict[str, Any]], *, custom_reason: str = "") -> str:
    if custom_reason:
        return custom_reason
    anchor_labels = [f"{anchor['stage']}@chapter{anchor['chapter_id']}" for anchor in anchors]
    span_kind = "cross-chapter" if len(window_row["chapter_ids"]) > 1 else "within-chapter"
    return (
        f"Bounded {span_kind} accumulation probe selected from {window_row['window_case_id']} using "
        f"{', '.join(anchor_labels)}. It is intended to test whether earlier material is carried "
        f"forward coherently rather than the later anchor being read as if it stands alone."
    )


def _probe_judge_focus(window_row: dict[str, Any], anchors: list[dict[str, Any]], *, custom_focus: str = "") -> str:
    if custom_focus:
        return custom_focus
    if len(window_row["chapter_ids"]) > 1:
        chapter_span = f"chapters {'-'.join(window_row['chapter_ids'])}"
    else:
        chapter_span = f"chapter {window_row['chapter_ids'][0]}"
    return (
        f"Within {chapter_span}, does the reader show coherent accumulation at the later anchor(s) by "
        f"explicitly carrying forward a concrete earlier idea, tension, or narrative state in a "
        f"text-grounded way, rather than reacting as if the later passage were independent?"
    )


def _probe_excerpt_text(anchors: list[dict[str, Any]]) -> str:
    return "\n".join(
        f"{str(anchor['stage']).upper()} ({anchor['chapter_id']}): {_clean_text(anchor['excerpt_text'])}"
        for anchor in anchors
    )


def _support_case_ids(anchors: list[dict[str, Any]]) -> list[str]:
    return [_clean_text(anchor.get("source_case_id")) for anchor in anchors if _clean_text(anchor.get("source_case_id"))]


def _note_entry_ids(anchors: list[dict[str, Any]]) -> list[str]:
    return [_clean_text(anchor.get("source_ref_id")) for anchor in anchors if _clean_text(anchor.get("anchor_kind")) == "note_entry"]


def _probe_display_chapter_id(anchors: list[dict[str, Any]], *, fallback_chapter_ids: list[str]) -> str:
    chapter_ids: list[str] = []
    for anchor in anchors:
        chapter_id = _clean_text(anchor.get("chapter_id"))
        if chapter_id and chapter_id not in chapter_ids:
            chapter_ids.append(chapter_id)
    return "→".join(chapter_ids or fallback_chapter_ids)


def _probe_display_chapter_title(anchors: list[dict[str, Any]], *, window_row: dict[str, Any]) -> str:
    titles: list[str] = []
    chapter_title_map = _chapter_title_map(window_row)
    for anchor in anchors:
        chapter_id = _clean_text(anchor.get("chapter_id"))
        chapter_title = _clean_text(anchor.get("chapter_title")) or chapter_title_map.get(chapter_id, "")
        if chapter_title and chapter_title not in titles:
            titles.append(chapter_title)
    return " / ".join(titles or [item for item in window_row.get("chapter_titles", []) if _clean_text(item)])


def _prior_context_text(anchors: list[dict[str, Any]]) -> str:
    if len(anchors) <= 1:
        return _clean_text(anchors[0]["excerpt_text"]) if anchors else ""
    return "\n".join(
        _clean_text(anchor["excerpt_text"])
        for anchor in anchors[:-1]
        if _clean_text(anchor.get("excerpt_text"))
    )


def build_probe_rows(root: Path | None = None) -> list[dict[str, Any]]:
    _ = root
    window_rows = build_window_rows()
    excerpt_index = _reviewed_excerpt_case_index()
    note_index = _note_support_index()
    probe_rows: list[dict[str, Any]] = []
    for window_row in window_rows:
        source_id = _clean_text(window_row["source_id"])
        chapter_ids = [str(item) for item in window_row["chapter_ids"]]
        planned_payloads = _planned_probe_payloads(
            window_row,
            excerpt_index=excerpt_index,
            note_index=note_index,
        )
        for index, planned_payload in enumerate(planned_payloads, start=1):
            anchors = [dict(anchor) for anchor in planned_payload["anchors"]]
            late_anchor = anchors[-1]
            probe_type = _probe_type(anchors)
            probe_id = f"{window_row['window_case_id']}__probe_{index}"
            serves_reader_value = any(
                _clean_text(anchor.get("target_profile_id")) in VALUE_TARGET_PROFILE_IDS
                or _clean_text(anchor.get("anchor_kind")) == "note_entry"
                for anchor in anchors
            )
            probe_rows.append(
                {
                    "probe_id": probe_id,
                    "case_id": probe_id,
                    "case_title": f"{window_row['window_title']} carryover probe {index}",
                    "window_case_id": window_row["window_case_id"],
                    "source_id": source_id,
                    "book_title": window_row["book_title"],
                    "author": window_row["author"],
                    "language_track": window_row["language_track"],
                    "output_language": window_row["output_language"],
                    "window_kind": window_row["window_kind"],
                    "chapter_id": _clean_text(late_anchor.get("chapter_id")),
                    "chapter_title": _clean_text(late_anchor.get("chapter_title")) or _probe_display_chapter_title(anchors, window_row=window_row),
                    "chapter_span_label": _probe_display_chapter_id(anchors, fallback_chapter_ids=chapter_ids),
                    "chapter_ids": chapter_ids,
                    "chapter_case_ids": list(window_row["chapter_case_ids"]),
                    "start_sentence_id": _clean_text(late_anchor.get("start_sentence_id")),
                    "end_sentence_id": _clean_text(late_anchor.get("end_sentence_id")),
                    "target_profile_id": _clean_text(late_anchor.get("target_profile_id")) or "coherent_accumulation_probe",
                    "selection_role": "long_span_accumulation_probe",
                    "probe_type": probe_type,
                    "question_ids": ["EQ-CM-003", "EQ-CM-004", "EQ-AV2-004"],
                    "phenomena": (
                        ["coherent_accumulation", "insight_and_clarification"]
                        if serves_reader_value
                        else ["coherent_accumulation"]
                    ),
                    "selection_reason": _probe_selection_reason(
                        window_row,
                        anchors,
                        custom_reason=_clean_text(planned_payload.get("selection_reason")),
                    ),
                    "judge_focus": _probe_judge_focus(
                        window_row,
                        anchors,
                        custom_focus=_clean_text(planned_payload.get("judge_focus")),
                    ),
                    "excerpt_text": _probe_excerpt_text(anchors),
                    "prior_context_text": _prior_context_text(anchors),
                    "anchor_refs": anchors,
                    "support_excerpt_case_ids": _support_case_ids(anchors),
                    "support_excerpt_case_count": len(_support_case_ids(anchors)),
                    "note_provenance": _note_entry_ids(anchors),
                    "target_axes": [
                        "reader_character.coherent_accumulation",
                        "reader_value.insight_and_clarification",
                    ]
                    if serves_reader_value
                    else ["reader_character.coherent_accumulation"],
                    "serves_reader_value": serves_reader_value,
                    "construction_priority": float(
                        sum(_anchor_priority(anchor) for anchor in anchors)
                        + len(_support_case_ids(anchors))
                        + (1.0 if serves_reader_value else 0.0)
                    ),
                    "judgeability_score": float(
                        len(anchors) * 2
                        + sum(1 for anchor in anchors if _clean_text(anchor.get("anchor_kind")) == "excerpt_case")
                        + (_anchor_distance_score(anchors) / 1000.0)
                    ),
                    "benchmark_status": "builder_curated",
                    "review_status": "builder_curated",
                    "curation_status": "builder_curated_v1_repair",
                    "window_probe_rank": index,
                    "notes": "Deterministic repaired long-span draft probe built from curated reviewed-excerpt and notes anchors.",
                }
            )
    probe_rows.sort(key=lambda row: (_clean_text(row.get("window_case_id")), int(row.get("window_probe_rank", 0) or 0), _clean_text(row.get("probe_id"))))
    return probe_rows


def _window_manifest() -> dict[str, Any]:
    return {
        "dataset_id": WINDOW_DATASET_ID,
        "family": WINDOW_CASES_FAMILY,
        "language_track": "bilingual",
        "version": "1",
        "description": "Bounded long-span window cases for attentional_v2 accumulation benchmark v1.",
        "primary_file": "windows.jsonl",
        "question_ids": ["EQ-CM-003", "EQ-CM-004", "EQ-AV2-004"],
        "source_manifest_refs": [str(path.relative_to(ROOT)) for path in SOURCE_MANIFEST_PATHS],
        "storage_mode": "local-only",
        "window_count": len(WINDOW_SPECS),
    }


def _probe_manifest(dataset_id: str, *, row_count: int, description: str) -> dict[str, Any]:
    return {
        "dataset_id": dataset_id,
        "family": ACCUMULATION_PROBES_FAMILY,
        "language_track": "bilingual",
        "version": "1",
        "description": description,
        "primary_file": "probes.jsonl",
        "question_ids": ["EQ-CM-003", "EQ-CM-004", "EQ-AV2-004"],
        "source_manifest_refs": [str(path.relative_to(ROOT)) for path in SOURCE_MANIFEST_PATHS],
        "storage_mode": "local-only",
        "row_count": row_count,
    }


def build_draft_manifest_payload() -> dict[str, Any]:
    window_rows = build_window_rows()
    probe_rows = build_probe_rows()
    insight_ids = [row["probe_id"] for row in probe_rows if bool(row.get("serves_reader_value"))]
    return {
        "manifest_id": "attentional_v2_accumulation_benchmark_v1_draft",
        "description": "Bounded long-span/window draft manifest for split-surface coherent accumulation evaluation.",
        "targets": [
            "reader_character.coherent_accumulation",
            "reader_value.insight_and_clarification",
        ],
        "benchmark_shape": {
            "kind": "long_span_window",
            "window_case_target_total": len(window_rows),
            "accumulation_probe_target_total": len(probe_rows),
        },
        "builder_limitations": list(BUILDER_LIMITATIONS),
        "source_refs": {
            "source_manifests": [str(path.relative_to(ROOT)) for path in SOURCE_MANIFEST_PATHS],
            "window_case_datasets": [str(WINDOW_DATASET_DIR.relative_to(ROOT))],
            "accumulation_probe_datasets": [str(PROBE_DRAFT_DATASET_DIR.relative_to(ROOT))],
        },
        "quota_status": {
            "window_cases": {
                "target_total": len(window_rows),
                "ready_now": len(window_rows),
                "gap": 0,
            },
            "accumulation_probes": {
                "target_total": len(probe_rows),
                "ready_now": len(probe_rows),
                "gap": 0,
            },
            "insight_and_clarification_subset": {
                "target_total": len(insight_ids),
                "ready_now": len(insight_ids),
                "gap": 0,
            },
        },
        "splits": {
            "accumulation_window_core_draft": {
                "all": [row["window_case_id"] for row in window_rows],
            },
            "accumulation_probes_frozen_draft": {
                "all": [row["probe_id"] for row in probe_rows],
            },
            "accumulation_probe_core_draft": {
                "by_window": {
                    row["window_case_id"]: [probe["probe_id"] for probe in probe_rows if probe["window_case_id"] == row["window_case_id"]]
                    for row in window_rows
                },
                "all": [row["probe_id"] for row in probe_rows],
            },
            "insight_and_clarification_subset_frozen_draft": {
                "all": insight_ids,
            },
            "insight_and_clarification_subset_draft": {
                "all": insight_ids,
            },
        },
    }


def write_draft_artifacts(root: Path | None = None) -> dict[str, Any]:
    _ = root
    window_rows = build_window_rows()
    probe_rows = build_probe_rows()
    WINDOW_DATASET_DIR.mkdir(parents=True, exist_ok=True)
    PROBE_DRAFT_DATASET_DIR.mkdir(parents=True, exist_ok=True)
    _json_dump(WINDOW_DATASET_DIR / "manifest.json", _window_manifest())
    _jsonl_dump(WINDOW_DATASET_DIR / "windows.jsonl", window_rows)
    _json_dump(
        PROBE_DRAFT_DATASET_DIR / "manifest.json",
        _probe_manifest(
            PROBE_DRAFT_DATASET_ID,
            row_count=len(probe_rows),
            description="Deterministic draft probes for attentional_v2 accumulation benchmark v1.",
        ),
    )
    _jsonl_dump(PROBE_DRAFT_DATASET_DIR / "probes.jsonl", probe_rows)
    draft_manifest = build_draft_manifest_payload()
    _json_dump(DRAFT_MANIFEST_PATH, draft_manifest)
    return {
        "window_dataset_dir": str(WINDOW_DATASET_DIR),
        "probe_dataset_dir": str(PROBE_DRAFT_DATASET_DIR),
        "draft_manifest_path": str(DRAFT_MANIFEST_PATH),
        "window_count": len(window_rows),
        "probe_count": len(probe_rows),
    }


def freeze_probe_rows(probe_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in probe_rows:
        grouped[_clean_text(row.get("window_case_id"))].append(dict(row))

    frozen_rows: list[dict[str, Any]] = []
    saturation: dict[str, Any] = {}
    for window_case_id, rows in grouped.items():
        reviewed = [row for row in rows if _clean_text(row.get("benchmark_status")) == "reviewed_active"]
        eligible = reviewed or rows
        eligible.sort(key=lambda row: (int(row.get("window_probe_rank", 999) or 999), _clean_text(row.get("probe_id"))))
        selected = eligible[:TARGET_PRIMARY_PROBES_PER_WINDOW]
        for row in selected:
            row["freeze_metadata"] = {
                "frozen_from_dataset_id": PROBE_DRAFT_DATASET_ID,
                "freeze_role": "primary",
                "freeze_reason": "reviewed_active" if reviewed else "builder_curated_fallback",
            }
            frozen_rows.append(row)
        saturation_reason = ""
        if not selected:
            saturation_reason = "insufficient_probe_rows"
        elif len(selected) < TARGET_PRIMARY_PROBES_PER_WINDOW:
            saturation_reason = "honest_short_repaired_probe_budget"
        saturation[window_case_id] = {
            "eligible_count": len(eligible),
            "selected_count": len(selected),
            "used_reviewed_rows": bool(reviewed),
            "saturation_reason": saturation_reason,
        }
    frozen_rows.sort(key=lambda row: (_clean_text(row.get("window_case_id")), int(row.get("window_probe_rank", 0) or 0)))
    return frozen_rows, saturation


def write_frozen_probe_dataset(root: Path | None = None) -> dict[str, Any]:
    _ = root
    draft_manifest = _load_json(PROBE_DRAFT_DATASET_DIR / "manifest.json")
    probe_rows = _load_jsonl(PROBE_DRAFT_DATASET_DIR / str(draft_manifest["primary_file"]))
    frozen_rows, saturation = freeze_probe_rows(probe_rows)
    PROBE_FROZEN_DATASET_DIR.mkdir(parents=True, exist_ok=True)
    _json_dump(
        PROBE_FROZEN_DATASET_DIR / "manifest.json",
        _probe_manifest(
            PROBE_FROZEN_DATASET_ID,
            row_count=len(frozen_rows),
            description="Frozen-draft long-span probes for attentional_v2 accumulation benchmark v1.",
        ),
    )
    _jsonl_dump(PROBE_FROZEN_DATASET_DIR / "probes.jsonl", frozen_rows)
    draft_manifest = build_draft_manifest_payload()
    draft_manifest["source_refs"]["accumulation_probe_datasets"] = [str(PROBE_FROZEN_DATASET_DIR.relative_to(ROOT))]
    draft_manifest["quota_status"]["accumulation_probes"]["ready_now"] = len(frozen_rows)
    draft_manifest["quota_status"]["accumulation_probes"]["target_total"] = len(frozen_rows)
    draft_manifest["quota_status"]["accumulation_probes"]["gap"] = 0
    frozen_probe_ids = [row["probe_id"] for row in frozen_rows]
    frozen_insight_ids = [row["probe_id"] for row in frozen_rows if bool(row.get("serves_reader_value"))]
    draft_manifest["splits"]["accumulation_probes_frozen_draft"] = {"all": frozen_probe_ids}
    draft_manifest["splits"]["insight_and_clarification_subset_frozen_draft"] = {"all": frozen_insight_ids}
    _json_dump(DRAFT_MANIFEST_PATH, draft_manifest)
    return {
        "probe_dataset_dir": str(PROBE_FROZEN_DATASET_DIR),
        "probe_count": len(frozen_rows),
        "saturation": saturation,
        "draft_manifest_path": str(DRAFT_MANIFEST_PATH),
    }

"""Build the active note-aligned user-level selective benchmark package.

This benchmark replaces the old active excerpt-surface pointer. Each source
contributes one continuous reading segment that starts at the opening of body
text and ends once the segment covers at least the target number of aligned
human notes, preserving a complete structural boundary where possible.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
from typing import Any
import unicodedata

from eval.attentional_v2.corpus_builder import ROOT, chapter_title, is_front_matter, write_json, write_jsonl
from src.reading_runtime.provisioning import ensure_canonical_parse


MANIFEST_ID = "attentional_v2_user_level_selective_v1_draft"
MANIFEST_PATH = ROOT / "eval" / "manifests" / "splits" / f"{MANIFEST_ID}.json"
DATASET_ID = "attentional_v2_user_level_selective_v1_repaired_20260416"
DATASET_DIR = ROOT / "state" / "eval_local_datasets" / "user_level_benchmarks" / DATASET_ID
SEGMENTS_FILE = "segments.jsonl"
NOTE_CASES_FILE = "note_cases.jsonl"
SEGMENT_SOURCE_DIRNAME = "segment_sources"
DEFAULT_VERSION = "2026-04-16"
DEFAULT_TARGET_NOTE_COUNT = 20
DEFAULT_HARD_SENTENCE_CAP = 350

DEFAULT_NOTES_LOCAL_REF_MANIFEST = (
    ROOT
    / "state"
    / "dataset_build"
    / "build_runs"
    / "human_notes_guided_dataset_v1_20260404"
    / "manifests"
    / "local_refs"
    / "attentional_v2_human_notes_guided_dataset_v1_local_refs__scratch__human_notes_guided_dataset_v1_20260404.json"
)
DEFAULT_NOTES_CATALOG_PATH = ROOT / "state" / "dataset_build" / "library_notes_catalog.json"
REGISTERED_NOTES_SOURCE_IDS = (
    "huochu_shengming_de_yiyi_private_zh",
    "mangge_zhi_dao_private_zh",
    "nawaer_baodian_private_zh",
    "value_of_others_private_en",
    "xidaduo_private_zh",
)
BODY_START_CHAPTER_OVERRIDES = {
    "nawaer_baodian_private_zh": 13,
}
FRONT_MATTER_EXTRA_TITLE_PATTERNS_ZH = tuple(
    re.compile(pattern)
    for pattern in (
        r"^书名页$",
        r"^版权页$",
        r"^版权$",
        r"^关于本书的重要说明(?:disclaimer)?$",
        r"^出版说明$",
        r"^出版前言$",
        r"^推荐序.*$",
        r"^前言$",
        r"^导言$",
        r"^导读$",
        r"^编者按$",
        r"^编者说明$",
        r"^编辑说明$",
        r"^作者说明$",
        r"^译者说明$",
        r"^序言$",
        r"^序(?:prologue)?$",
        r"^自序$",
        r"^.*关于这本书.*$",
        r"^.*(?:年表|经历表)$",
        r"^目录$",
    )
)
FRONT_MATTER_EXTRA_TITLE_PATTERNS_EN = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"^title page$",
        r"^copyright$",
        r"^contents$",
        r"^table of contents$",
        r"^disclaimer$",
        r"^foreword$",
        r"^preface$",
        r"^prologue$",
        r"^introduction$",
        r"^editor'?s note$",
        r"^author'?s note$",
        r"^about this book$",
        r"^timeline$",
    )
)


@dataclass(frozen=True)
class AlignedNote:
    note_id: str
    notes_id: str
    source_id: str
    note_text: str
    note_comment: str
    raw_locator: str
    section_label: str
    source_chapter_id: int
    chapter_title: str
    start_sentence_id: str
    end_sentence_id: str
    sentence_ids: tuple[str, ...]
    aligned_text: str
    alignment_match_type: str
    alignment_score: float


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_title(value: str) -> str:
    return re.sub(r"\s+", "", _clean_text(value)).casefold()


def _sentence_number(sentence_id: str) -> int:
    suffix = str(sentence_id or "").rsplit("-s", 1)[-1]
    return int(suffix) if suffix.isdigit() else 0


def _relative_to_root(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _join_sentence_texts(sentences: list[dict[str, Any]], *, language_track: str) -> str:
    if not sentences:
        return ""
    separator = " " if language_track == "en" else ""
    return separator.join(_clean_text(sentence.get("text")) for sentence in sentences if _clean_text(sentence.get("text")))


def _normalized_join_separator(left: str, right: str) -> str:
    if not left or not right:
        return ""
    if re.match(r"[\w\u4e00-\u9fff]", left[-1], flags=re.UNICODE) and re.match(
        r"[\w\u4e00-\u9fff]",
        right[0],
        flags=re.UNICODE,
    ):
        return " "
    return ""


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return payload


def _load_notes_catalog() -> dict[str, Any]:
    return _load_json(DEFAULT_NOTES_CATALOG_PATH)


def _load_source_index() -> dict[str, dict[str, Any]]:
    payload = _load_json(DEFAULT_NOTES_LOCAL_REF_MANIFEST)
    index: dict[str, dict[str, Any]] = {}
    for item in payload.get("source_refs") or []:
        if not isinstance(item, dict):
            continue
        source_id = _clean_text(item.get("source_id"))
        relative_local_path = _clean_text(item.get("relative_local_path"))
        if source_id and relative_local_path:
            index[source_id] = dict(item)
    return index


def _entry_file_path(notes_id: str) -> Path:
    return ROOT / "state" / "library_notes" / "entries" / f"{notes_id}.jsonl"


def _load_aligned_notes(*, notes_id: str, source_id: str) -> list[AlignedNote]:
    path = _entry_file_path(notes_id)
    notes: list[AlignedNote] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if _clean_text(row.get("alignment_status")) != "aligned":
                continue
            if _clean_text(row.get("linked_source_id")) != source_id:
                continue
            matched_span = dict(row.get("matched_sentence_span") or {})
            source_chapter_id = int(_clean_text(row.get("matched_chapter_id")) or matched_span.get("chapter_id") or 0)
            if source_chapter_id <= 0:
                continue
            start_sentence_id = _clean_text(matched_span.get("start_sentence_id"))
            end_sentence_id = _clean_text(matched_span.get("end_sentence_id")) or start_sentence_id
            if not start_sentence_id:
                continue
            notes.append(
                AlignedNote(
                    note_id=_clean_text(row.get("entry_id")),
                    notes_id=notes_id,
                    source_id=source_id,
                    note_text=_clean_text(row.get("quote")),
                    note_comment=_clean_text(row.get("note")),
                    raw_locator=_clean_text(row.get("raw_locator")),
                    section_label=_clean_text(row.get("section_label")),
                    source_chapter_id=source_chapter_id,
                    chapter_title=_clean_text((row.get("alignment") or {}).get("chapter_title")) or _clean_text(row.get("section_label")),
                    start_sentence_id=start_sentence_id,
                    end_sentence_id=end_sentence_id,
                    sentence_ids=tuple(str(item) for item in (row.get("matched_sentence_ids") or []) if _clean_text(item)),
                    aligned_text=_clean_text((row.get("alignment") or {}).get("aligned_text")),
                    alignment_match_type=_clean_text((row.get("alignment") or {}).get("match_type")),
                    alignment_score=float((row.get("alignment") or {}).get("score") or 0.0),
                )
            )
    notes.sort(key=lambda item: (item.source_chapter_id, _sentence_number(item.start_sentence_id), item.note_id))
    return notes


def _title_matches_extra_front_matter(title: str, *, language_track: str) -> bool:
    patterns = FRONT_MATTER_EXTRA_TITLE_PATTERNS_EN if language_track == "en" else FRONT_MATTER_EXTRA_TITLE_PATTERNS_ZH
    normalized = _normalize_title(title)
    return any(pattern.search(normalized) for pattern in patterns)


def _body_start_override_index(*, chapters: list[dict[str, Any]], source_id: str) -> int | None:
    override_chapter_id = BODY_START_CHAPTER_OVERRIDES.get(source_id)
    if override_chapter_id is None:
        return None
    for chapter_index, chapter in enumerate(chapters):
        chapter_id = int(chapter.get("id", 0) or 0)
        if chapter_id == override_chapter_id:
            return chapter_index
    raise ValueError(f"body-start override chapter {override_chapter_id} not found for source {source_id}")


def _find_body_start_index(
    *,
    chapters: list[dict[str, Any]],
    language_track: str,
    book_title_value: str,
    source_id: str | None = None,
) -> int:
    if source_id:
        override_index = _body_start_override_index(chapters=chapters, source_id=source_id)
        if override_index is not None:
            return override_index
    for chapter_index, chapter in enumerate(chapters):
        front_matter, _reason = is_front_matter(
            chapter,
            language=language_track,
            book_title=book_title_value,
            chapter_index=chapter_index,
        )
        title = chapter_title(chapter)
        if front_matter or _title_matches_extra_front_matter(title, language_track=language_track):
            continue
        if len(chapter.get("sentences") or []) < 20:
            continue
        return chapter_index
    return 0


def _flatten_document(
    *,
    chapters: list[dict[str, Any]],
    start_index: int,
    language_track: str,
) -> tuple[list[dict[str, Any]], dict[str, int], dict[tuple[int, int], int], dict[int, int]]:
    flat_sentences: list[dict[str, Any]] = []
    sentence_index: dict[str, int] = {}
    paragraph_end_positions: dict[tuple[int, int], int] = {}
    chapter_end_positions: dict[int, int] = {}
    for chapter in chapters[start_index:]:
        chapter_id = int(chapter.get("id", 0) or 0)
        chapter_name = chapter_title(chapter)
        chapter_sentences = [sentence for sentence in chapter.get("sentences") or [] if isinstance(sentence, dict)]
        current_paragraph_key: tuple[int, int] | None = None
        for sentence in chapter_sentences:
            position = len(flat_sentences)
            sentence_id = _clean_text(sentence.get("sentence_id"))
            paragraph_index = int(sentence.get("paragraph_index", 0) or 0)
            flat_sentences.append(
                {
                    "global_index": position,
                    "chapter_id": chapter_id,
                    "chapter_title": chapter_name,
                    "sentence_id": sentence_id,
                    "paragraph_index": paragraph_index,
                    "text": _clean_text(sentence.get("text")),
                    "text_role": _clean_text(sentence.get("text_role")),
                    "language_track": language_track,
                    "locator": dict(sentence.get("locator") or {}) if isinstance(sentence.get("locator"), dict) else {},
                }
            )
            sentence_index[sentence_id] = position
            paragraph_key = (chapter_id, paragraph_index)
            if current_paragraph_key is not None and paragraph_key != current_paragraph_key:
                paragraph_end_positions[current_paragraph_key] = position - 1
            current_paragraph_key = paragraph_key
        if current_paragraph_key is not None:
            paragraph_end_positions[current_paragraph_key] = len(flat_sentences) - 1
        if chapter_sentences:
            chapter_end_positions[chapter_id] = len(flat_sentences) - 1
    return flat_sentences, sentence_index, paragraph_end_positions, chapter_end_positions


def _normalize_with_offsets(value: str, offsets: list[Any] | None = None) -> tuple[str, list[Any]]:
    raw_offsets = offsets if offsets is not None else [None] * len(value)
    chars: list[tuple[str, Any]] = []
    for character, offset in zip(value, raw_offsets, strict=False):
        normalized = unicodedata.normalize("NFKC", character)
        normalized = normalized.replace("“", '"').replace("”", '"')
        normalized = normalized.replace("’", "'").replace("–", "-").replace("—", "-")
        normalized = normalized.replace("…", "...")
        normalized = normalized.lower()
        for item in normalized:
            chars.append((" " if item.isspace() else item, offset))

    collapsed: list[tuple[str, Any]] = []
    for character, offset in chars:
        if character == " " and (not collapsed or collapsed[-1][0] == " "):
            continue
        collapsed.append((character, offset))
    while collapsed and collapsed[0][0] == " ":
        collapsed.pop(0)
    while collapsed and collapsed[-1][0] == " ":
        collapsed.pop()

    punctuation = set(",.;:!?()\"'")
    filtered: list[tuple[str, Any]] = []
    for index, (character, offset) in enumerate(collapsed):
        if character == " ":
            previous_character = collapsed[index - 1][0] if index > 0 else ""
            next_character = collapsed[index + 1][0] if index + 1 < len(collapsed) else ""
            if previous_character in punctuation or next_character in punctuation:
                continue
        filtered.append((character, offset))
    return "".join(character for character, _offset in filtered), [offset for _character, offset in filtered]


def _render_segment_source(
    *,
    flat_sentences: list[dict[str, Any]],
    start_position: int,
    end_position: int,
    language_track: str,
) -> tuple[str, dict[str, dict[str, Any]], dict[int, str]]:
    lines: list[str] = []
    current_chapter_id: int | None = None
    current_paragraph_key: tuple[int, int] | None = None
    current_paragraph_sentences: list[dict[str, Any]] = []
    segment_paragraph_index = 0
    sentence_spans: dict[str, dict[str, Any]] = {}
    paragraph_texts: dict[int, str] = {}

    def append_blank_line() -> None:
        if lines and lines[-1] != "":
            lines.append("")

    def emit_source_paragraph(sentences: list[dict[str, Any]]) -> None:
        nonlocal segment_paragraph_index
        if not sentences:
            return
        paragraph_text = _join_sentence_texts(sentences, language_track=language_track)
        if not paragraph_text:
            return
        segment_paragraph_index += 1
        paragraph_texts[segment_paragraph_index] = paragraph_text
        search_from = 0
        for sentence in sentences:
            sentence_text = _clean_text(sentence.get("text"))
            if not sentence_text:
                continue
            char_start = paragraph_text.find(sentence_text, search_from)
            if char_start < 0:
                char_start = search_from
            char_end = char_start + len(sentence_text)
            search_from = char_end
            sentence_spans[str(sentence["sentence_id"])] = {
                "paragraph_index": segment_paragraph_index,
                "char_start": char_start,
                "char_end": char_end,
                "source_chapter_id": int(sentence["chapter_id"]),
                "source_paragraph_index": int(sentence["paragraph_index"]),
                "source_locator": dict(sentence.get("locator") or {}),
            }
        lines.append(paragraph_text)

    for sentence in flat_sentences[start_position : end_position + 1]:
        chapter_id = int(sentence["chapter_id"])
        paragraph_key = (chapter_id, int(sentence["paragraph_index"]))
        if current_chapter_id != chapter_id:
            if current_paragraph_sentences:
                emit_source_paragraph(current_paragraph_sentences)
                append_blank_line()
                current_paragraph_sentences = []
            append_blank_line()
            segment_paragraph_index += 1
            chapter_title_text = str(sentence["chapter_title"])
            paragraph_texts[segment_paragraph_index] = chapter_title_text
            lines.append(chapter_title_text)
            append_blank_line()
            current_chapter_id = chapter_id
            current_paragraph_key = None
        if current_paragraph_key is not None and paragraph_key != current_paragraph_key:
            emit_source_paragraph(current_paragraph_sentences)
            append_blank_line()
            current_paragraph_sentences = []
        current_paragraph_key = paragraph_key
        current_paragraph_sentences.append(sentence)
    if current_paragraph_sentences:
        emit_source_paragraph(current_paragraph_sentences)
    return "\n".join(line.rstrip() for line in lines).strip() + "\n", sentence_spans, paragraph_texts


def _note_source_span(
    *,
    note: AlignedNote,
    flat_sentences: list[dict[str, Any]],
    sentence_index: dict[str, int],
    language_track: str,
    segment_sentence_spans: dict[str, dict[str, Any]],
    segment_paragraph_texts: dict[int, str],
    segment_id: str,
) -> tuple[str, list[str], list[dict[str, Any]]]:
    start_index = sentence_index[note.start_sentence_id]
    end_index = sentence_index[note.end_sentence_id]
    span_sentences = flat_sentences[start_index : end_index + 1]
    normalized_parts: list[str] = []
    normalized_offsets: list[tuple[int, int] | None] = []
    previous_normalized = ""
    for sentence in span_sentences:
        sentence_id = str(sentence["sentence_id"])
        segment_span = segment_sentence_spans.get(sentence_id)
        if not segment_span:
            raise ValueError(f"Missing segment-source locator for note {note.note_id} sentence {sentence_id}")
        sentence_text = _clean_text(sentence.get("text"))
        char_start = int(segment_span["char_start"])
        source_offsets = [
            (int(segment_span["paragraph_index"]), char_start + offset)
            for offset in range(len(sentence_text))
        ]
        normalized_sentence, sentence_offsets = _normalize_with_offsets(sentence_text, source_offsets)
        joiner = _normalized_join_separator(previous_normalized, normalized_sentence)
        if joiner:
            normalized_parts.append(joiner)
            normalized_offsets.extend([None] * len(joiner))
        normalized_parts.append(normalized_sentence)
        normalized_offsets.extend(sentence_offsets)
        previous_normalized = normalized_sentence

    normalized_source = "".join(normalized_parts)
    match_text_candidates = [note.note_text]
    if note.aligned_text and note.aligned_text not in match_text_candidates:
        match_text_candidates.append(note.aligned_text)
    match_start = -1
    normalized_note = ""
    matched_source_text_kind = ""
    for match_text in match_text_candidates:
        normalized_candidate, _note_offsets = _normalize_with_offsets(match_text)
        candidate_start = normalized_source.find(normalized_candidate)
        if candidate_start >= 0:
            match_start = candidate_start
            normalized_note = normalized_candidate
            matched_source_text_kind = "note_text" if match_text == note.note_text else "aligned_text"
            break
    if match_start < 0:
        raise ValueError(
            f"Aligned note {note.note_id} cannot be mapped to a segment-source char span; "
            f"neither note_text nor aligned_text is an exact normalized substring of the aligned source sentences."
        )
    match_end = match_start + len(normalized_note)
    matched_offsets = [offset for offset in normalized_offsets[match_start:match_end] if offset is not None]
    if not matched_offsets:
        raise ValueError(f"Aligned note {note.note_id} mapped only to separator characters")

    slices: list[dict[str, Any]] = []
    by_paragraph: dict[int, list[int]] = defaultdict(list)
    for paragraph_index, char_offset in matched_offsets:
        by_paragraph[int(paragraph_index)].append(int(char_offset))
    source_sentence_ids = [str(sentence["sentence_id"]) for sentence in span_sentences]
    for paragraph_index in sorted(by_paragraph):
        offsets = by_paragraph[paragraph_index]
        char_start = min(offsets)
        char_end = max(offsets) + 1
        paragraph_text = segment_paragraph_texts.get(paragraph_index, "")
        slices.append(
            {
                "coordinate_system": "segment_source_v1",
                "segment_id": segment_id,
                "source_id": note.source_id,
                "paragraph_index": paragraph_index,
                "char_start": char_start,
                "char_end": char_end,
                "text": paragraph_text[char_start:char_end],
                "source_sentence_ids": source_sentence_ids,
                "matched_source_text_kind": matched_source_text_kind,
            }
        )
    source_span_text = "\n\n".join(slice_payload["text"] for slice_payload in slices if slice_payload["text"])
    return source_span_text, source_sentence_ids, slices


def _render_segment_text(
    *,
    flat_sentences: list[dict[str, Any]],
    start_position: int,
    end_position: int,
    language_track: str,
) -> str:
    rendered, _sentence_spans, _paragraph_texts = _render_segment_source(
        flat_sentences=flat_sentences,
        start_position=start_position,
        end_position=end_position,
        language_track=language_track,
    )
    return rendered


def _section_end_position(
    *,
    flat_sentences: list[dict[str, Any]],
    threshold_position: int,
    limit_position: int,
    paragraph_end_positions: dict[tuple[int, int], int],
) -> int | None:
    for position in range(threshold_position + 1, min(limit_position, len(flat_sentences) - 1) + 1):
        sentence = flat_sentences[position]
        if _clean_text(sentence.get("text_role")) != "heading":
            continue
        previous = position - 1
        if previous < threshold_position:
            continue
        paragraph_key = (int(flat_sentences[previous]["chapter_id"]), int(flat_sentences[previous]["paragraph_index"]))
        section_end = paragraph_end_positions.get(paragraph_key)
        if section_end is not None and threshold_position <= section_end <= limit_position:
            return section_end
    return None


def _choose_segment_end(
    *,
    target_note: AlignedNote,
    target_note_end_position: int,
    flat_sentences: list[dict[str, Any]],
    chapter_end_positions: dict[int, int],
    paragraph_end_positions: dict[tuple[int, int], int],
    hard_sentence_cap: int,
) -> tuple[int, str]:
    chapter_end = chapter_end_positions[target_note.source_chapter_id]
    additional_sentences = chapter_end - target_note_end_position
    if additional_sentences <= hard_sentence_cap:
        return chapter_end, "chapter_end_after_target_notes"
    limit_position = min(len(flat_sentences) - 1, target_note_end_position + hard_sentence_cap)
    section_end = _section_end_position(
        flat_sentences=flat_sentences,
        threshold_position=target_note_end_position,
        limit_position=limit_position,
        paragraph_end_positions=paragraph_end_positions,
    )
    if section_end is not None:
        return section_end, "section_end_after_hard_cap"
    paragraph_key = (
        int(flat_sentences[limit_position]["chapter_id"]),
        int(flat_sentences[limit_position]["paragraph_index"]),
    )
    paragraph_end = paragraph_end_positions.get(paragraph_key, limit_position)
    if paragraph_end < target_note_end_position:
        paragraph_end = limit_position
    return min(paragraph_end, limit_position), "paragraph_end_after_hard_cap"


def _catalog_asset_by_source_id(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for asset in catalog.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        source_id = _clean_text(asset.get("linked_source_id"))
        if source_id:
            index[source_id] = dict(asset)
    return index


def build_user_level_selective_v1(
    *,
    dataset_dir: Path | None = None,
    dataset_id: str | None = None,
    dataset_version: str | None = None,
    split_manifest_path: Path | None = None,
    target_note_count: int = DEFAULT_TARGET_NOTE_COUNT,
    hard_sentence_cap: int = DEFAULT_HARD_SENTENCE_CAP,
) -> dict[str, Any]:
    catalog = _load_notes_catalog()
    asset_index = _catalog_asset_by_source_id(catalog)
    source_index = _load_source_index()
    dataset_root = Path(dataset_dir if dataset_dir is not None else DATASET_DIR).resolve()
    resolved_dataset_id = str(dataset_id if dataset_id is not None else DATASET_ID)
    resolved_dataset_version = str(dataset_version if dataset_version is not None else DEFAULT_VERSION)
    resolved_split_manifest_path = (
        Path(split_manifest_path).resolve() if split_manifest_path is not None else MANIFEST_PATH.resolve()
    )

    shutil.rmtree(dataset_root, ignore_errors=True)
    dataset_root.mkdir(parents=True, exist_ok=True)
    segment_sources_dir = dataset_root / SEGMENT_SOURCE_DIRNAME
    segment_sources_dir.mkdir(parents=True, exist_ok=True)

    segments_rows: list[dict[str, Any]] = []
    note_case_rows: list[dict[str, Any]] = []
    selected_source_ids: list[str] = []
    skipped_sources: list[dict[str, str]] = []

    for source_id in REGISTERED_NOTES_SOURCE_IDS:
        asset = asset_index.get(source_id)
        source_record = source_index.get(source_id)
        if asset is None:
            skipped_sources.append({"source_id": source_id, "reason": "missing_notes_asset"})
            continue
        if source_record is None:
            skipped_sources.append({"source_id": source_id, "reason": "missing_source_ref"})
            continue
        aligned_entry_count = int(asset.get("aligned_entry_count", 0) or 0)
        if aligned_entry_count <= 0:
            skipped_sources.append({"source_id": source_id, "reason": "no_aligned_notes"})
            continue

        notes_id = _clean_text(asset.get("notes_id"))
        aligned_notes = _load_aligned_notes(notes_id=notes_id, source_id=source_id)
        if len(aligned_notes) < target_note_count:
            skipped_sources.append({"source_id": source_id, "reason": "insufficient_aligned_notes"})
            continue

        book_path = ROOT / _clean_text(source_record["relative_local_path"])
        provisioned = ensure_canonical_parse(book_path)
        document = provisioned.book_document or {}
        chapters = [chapter for chapter in document.get("chapters") or [] if isinstance(chapter, dict)]
        body_start_index = _find_body_start_index(
            chapters=chapters,
            language_track=provisioned.output_language,
            book_title_value=provisioned.title,
            source_id=source_id,
        )
        flat_sentences, sentence_index, paragraph_end_positions, chapter_end_positions = _flatten_document(
            chapters=chapters,
            start_index=body_start_index,
            language_track=provisioned.output_language,
        )
        if not flat_sentences:
            skipped_sources.append({"source_id": source_id, "reason": "empty_body_segment"})
            continue

        eligible_notes = [note for note in aligned_notes if note.start_sentence_id in sentence_index and note.end_sentence_id in sentence_index]
        if len(eligible_notes) < target_note_count:
            skipped_sources.append({"source_id": source_id, "reason": "insufficient_notes_after_body_start"})
            continue

        threshold_note = eligible_notes[target_note_count - 1]
        threshold_position = sentence_index[threshold_note.end_sentence_id]
        segment_end_position, termination_reason = _choose_segment_end(
            target_note=threshold_note,
            target_note_end_position=threshold_position,
            flat_sentences=flat_sentences,
            chapter_end_positions=chapter_end_positions,
            paragraph_end_positions=paragraph_end_positions,
            hard_sentence_cap=hard_sentence_cap,
        )
        segment_notes = [
            note
            for note in eligible_notes
            if sentence_index[note.end_sentence_id] <= segment_end_position
        ]
        segment_start_sentence_id = str(flat_sentences[0]["sentence_id"])
        segment_end_sentence_id = str(flat_sentences[segment_end_position]["sentence_id"])
        covered_source_chapter_ids: list[int] = []
        covered_chapter_titles: list[str] = []
        for sentence in flat_sentences[: segment_end_position + 1]:
            chapter_id = int(sentence["chapter_id"])
            if chapter_id in covered_source_chapter_ids:
                continue
            covered_source_chapter_ids.append(chapter_id)
            covered_chapter_titles.append(str(sentence["chapter_title"]))

        segment_id = f"{source_id}__segment_1"
        segment_source_path = segment_sources_dir / f"{segment_id}.txt"
        segment_source_text, segment_sentence_spans, segment_paragraph_texts = _render_segment_source(
            flat_sentences=flat_sentences,
            start_position=0,
            end_position=segment_end_position,
            language_track=provisioned.output_language,
        )
        segment_source_path.write_text(segment_source_text, encoding="utf-8")

        segments_rows.append(
            {
                "segment_id": segment_id,
                "source_id": source_id,
                "book_title": provisioned.title,
                "author": provisioned.author,
                "language_track": provisioned.output_language,
                "start_sentence_id": segment_start_sentence_id,
                "end_sentence_id": segment_end_sentence_id,
                "source_chapter_ids": covered_source_chapter_ids,
                "chapter_titles": covered_chapter_titles,
                "target_note_count": target_note_count,
                "covered_note_count": len(segment_notes),
                "termination_reason": termination_reason,
                "segment_source_path": f"{SEGMENT_SOURCE_DIRNAME}/{segment_id}.txt",
                "source_span_coordinate_system": "segment_source_v1",
            }
        )

        for note in segment_notes:
            source_span_text, source_sentence_ids, source_span_slices = _note_source_span(
                note=note,
                flat_sentences=flat_sentences,
                sentence_index=sentence_index,
                language_track=provisioned.output_language,
                segment_sentence_spans=segment_sentence_spans,
                segment_paragraph_texts=segment_paragraph_texts,
                segment_id=segment_id,
            )
            note_case_rows.append(
                {
                    "note_case_id": f"{source_id}__{note.note_id}",
                    "segment_id": segment_id,
                    "source_id": source_id,
                    "book_title": provisioned.title,
                    "author": provisioned.author,
                    "language_track": provisioned.output_language,
                    "note_id": note.note_id,
                    "note_text": note.note_text,
                    "note_comment": note.note_comment,
                    "source_span_text": source_span_text,
                    "source_sentence_ids": source_sentence_ids,
                    "source_span_coordinate_system": "segment_source_v1",
                    "source_span_slices": source_span_slices,
                    "source_chapter_id": note.source_chapter_id,
                    "chapter_title": note.chapter_title,
                    "section_label": note.section_label,
                    "raw_locator": note.raw_locator,
                    "provenance": {
                        "notes_id": note.notes_id,
                        "entry_file": _relative_to_root(_entry_file_path(note.notes_id)),
                        "alignment_match_type": note.alignment_match_type,
                        "alignment_score": note.alignment_score,
                        "start_sentence_id": note.start_sentence_id,
                        "end_sentence_id": note.end_sentence_id,
                        "source_coordinate_note": "source_span_slices are in the rendered reading segment coordinate system; source_sentence_ids preserve original parsed-book provenance.",
                    },
                }
            )
        selected_source_ids.append(source_id)

    manifest_payload = {
        "dataset_id": resolved_dataset_id,
        "family": "user_level_note_aligned_benchmark",
        "status": "active",
        "version": resolved_dataset_version,
        "generated_at": utc_now(),
        "description": "Active user-level selective benchmark built directly from aligned human note spans and continuous reading segments.",
        "segments_file": SEGMENTS_FILE,
        "note_cases_file": NOTE_CASES_FILE,
        "registered_source_ids": list(REGISTERED_NOTES_SOURCE_IDS),
        "eligible_source_ids": selected_source_ids,
        "skipped_sources": skipped_sources,
        "target_note_count": target_note_count,
        "hard_sentence_cap": hard_sentence_cap,
        "segment_count": len(segments_rows),
        "note_case_count": len(note_case_rows),
        "source_manifest_refs": [
            _relative_to_root(DEFAULT_NOTES_LOCAL_REF_MANIFEST),
        ],
        "notes_catalog_path": _relative_to_root(DEFAULT_NOTES_CATALOG_PATH),
        "supersedes": [
            "eval/manifests/splits/attentional_v2_excerpt_surface_v1_1_draft.json",
            "state/eval_local_datasets/excerpt_cases/attentional_v2_excerpt_surface_v1_1_excerpt_en",
            "state/eval_local_datasets/excerpt_cases/attentional_v2_excerpt_surface_v1_1_excerpt_zh",
        ],
    }
    write_json(dataset_root / "manifest.json", manifest_payload)
    write_jsonl(dataset_root / SEGMENTS_FILE, segments_rows)
    write_jsonl(dataset_root / NOTE_CASES_FILE, note_case_rows)

    split_payload = {
        "manifest_id": MANIFEST_ID,
        "description": "Active user-level selective benchmark built from note-aligned continuous reading segments.",
        "status": "active",
        "supersedes": [
            "attentional_v2_excerpt_surface_v1_1_draft",
        ],
        "targets": [
            "reader_character.selective_legibility",
        ],
        "benchmark_shape": {
            "kind": "user_level_selective_v1",
            "surface_role": "user_level_note_aligned",
            "reading_segments": len(segments_rows),
            "target_note_count": target_note_count,
            "hard_sentence_cap": hard_sentence_cap,
            "note_case_count": len(note_case_rows),
        },
        "source_refs": {
            "source_manifests": [
                _relative_to_root(DEFAULT_NOTES_LOCAL_REF_MANIFEST),
            ],
            "notes_catalog": _relative_to_root(DEFAULT_NOTES_CATALOG_PATH),
            "user_level_dataset_roots": [
                _relative_to_root(dataset_root),
            ],
        },
        "selected_segments": [
            {
                "segment_id": row["segment_id"],
                "source_id": row["source_id"],
                "book_title": row["book_title"],
                "language_track": row["language_track"],
                "covered_note_count": row["covered_note_count"],
                "termination_reason": row["termination_reason"],
            }
            for row in segments_rows
        ],
        "skipped_sources": skipped_sources,
        "quota_status": {
            "reading_segments": {
                "registered_sources": len(REGISTERED_NOTES_SOURCE_IDS),
                "ready_now": len(segments_rows),
                "skipped": len(skipped_sources),
            },
            "note_cases": {
                "ready_now": len(note_case_rows),
            },
        },
        "splits": {
            "selective_legibility_note_cases_v1": {
                "by_segment": {
                    row["segment_id"]: [
                        case["note_case_id"]
                        for case in note_case_rows
                        if case["segment_id"] == row["segment_id"]
                    ]
                    for row in segments_rows
                },
                "all": [case["note_case_id"] for case in note_case_rows],
            }
        },
    }
    if split_manifest_path is not None:
        write_json(resolved_split_manifest_path, split_payload)
    return split_payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=DATASET_DIR)
    parser.add_argument("--dataset-id", default=DATASET_ID)
    parser.add_argument("--dataset-version", default=DEFAULT_VERSION)
    parser.add_argument("--split-manifest-path", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--skip-split-manifest", action="store_true")
    parser.add_argument("--target-note-count", type=int, default=DEFAULT_TARGET_NOTE_COUNT)
    parser.add_argument("--hard-sentence-cap", type=int, default=DEFAULT_HARD_SENTENCE_CAP)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    build_user_level_selective_v1(
        dataset_dir=Path(args.dataset_dir),
        dataset_id=str(args.dataset_id),
        dataset_version=str(args.dataset_version),
        split_manifest_path=None if args.skip_split_manifest else Path(args.split_manifest_path),
        target_note_count=int(args.target_note_count),
        hard_sentence_cap=int(args.hard_sentence_cap),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

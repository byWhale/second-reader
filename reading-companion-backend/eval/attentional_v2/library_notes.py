"""Managed notes helpers for the local source library."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from src.reading_runtime.provisioning import ensure_canonical_parse

ROOT = Path(__file__).resolve().parents[2]
STATE_ROOT = ROOT / "state"
DATASET_BUILD_ROOT = STATE_ROOT / "dataset_build"
LIBRARY_NOTES_ROOT = STATE_ROOT / "library_notes"
RAW_EXPORTS_ROOT = LIBRARY_NOTES_ROOT / "raw_exports"
NOTES_ENTRIES_ROOT = LIBRARY_NOTES_ROOT / "entries"
NOTES_CATALOG_JSON_PATH = DATASET_BUILD_ROOT / "library_notes_catalog.json"
NOTES_CATALOG_MD_PATH = DATASET_BUILD_ROOT / "library_notes_catalog.md"
NOTES_CATALOG_VERSION = 1


@dataclass(frozen=True)
class LibraryNotesPaths:
    root: Path
    state_root: Path
    dataset_build_root: Path
    library_notes_root: Path
    raw_exports_root: Path
    notes_entries_root: Path
    notes_catalog_json_path: Path
    notes_catalog_md_path: Path

    @classmethod
    def from_root(cls, root: Path) -> "LibraryNotesPaths":
        resolved = root.expanduser().resolve()
        state_root = resolved / "state"
        library_notes_root = state_root / "library_notes"
        return cls(
            root=resolved,
            state_root=state_root,
            dataset_build_root=state_root / "dataset_build",
            library_notes_root=library_notes_root,
            raw_exports_root=library_notes_root / "raw_exports",
            notes_entries_root=library_notes_root / "entries",
            notes_catalog_json_path=(state_root / "dataset_build" / "library_notes_catalog.json"),
            notes_catalog_md_path=(state_root / "dataset_build" / "library_notes_catalog.md"),
        )


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object JSON at {path}")
    return payload


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _sanitize_slug(value: str) -> str:
    cleaned = unicodedata.normalize("NFKC", value or "")
    cleaned = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", cleaned, flags=re.UNICODE)
    cleaned = re.sub(r"_+", "_", cleaned).strip("._-")
    return cleaned.casefold() or "notes"


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text or "")
    normalized = normalized.replace("“", '"').replace("”", '"')
    normalized = normalized.replace("’", "'").replace("–", "-").replace("—", "-")
    normalized = normalized.replace("…", "...")
    normalized = normalized.lower()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"\s*([,.;:!?()\"'])\s*", r"\1", normalized)
    return normalized.strip()


def _normalized_tokens(text: str) -> tuple[str, ...]:
    normalized = normalize_text(text)
    if not normalized:
        return ()
    return tuple(re.findall(r"[\w\u4e00-\u9fff]+", normalized, flags=re.UNICODE))


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


def fuzzy_ratio(left: str, right: str) -> float:
    normalized_left = normalize_text(left)
    normalized_right = normalize_text(right)
    return fuzzy_ratio_normalized(normalized_left, normalized_right)


def fuzzy_ratio_normalized(normalized_left: str, normalized_right: str) -> float:
    if not normalized_left or not normalized_right:
        return 0.0
    if normalized_left in normalized_right or normalized_right in normalized_left:
        return 100.0
    return SequenceMatcher(None, normalized_left, normalized_right).ratio() * 100


def _clean_quote_text(text: str) -> str:
    cleaned = unicodedata.normalize("NFC", text or "")
    cleaned = re.sub(r"!\[\]\[image\d+\]", "", cleaned)
    cleaned = cleaned.replace("|", " ")
    cleaned = cleaned.replace("\\", "")
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned.strip(" -*_>\t\r\n")
    for left, right in (('"', '"'), ("“", "”"), ("'", "'")):
        if cleaned.startswith(left) and cleaned.endswith(right) and len(cleaned) >= 2:
            cleaned = cleaned[1:-1].strip()
    return cleaned


def load_notes_catalog(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "version": NOTES_CATALOG_VERSION,
            "updated_at": "",
            "asset_count": 0,
            "entry_count": 0,
            "assets": [],
            "entries": [],
        }
    payload = load_json(path)
    payload.setdefault("version", NOTES_CATALOG_VERSION)
    payload.setdefault("updated_at", "")
    payload.setdefault("assets", [])
    payload.setdefault("entries", [])
    payload["asset_count"] = len(payload["assets"])
    payload["entry_count"] = len(payload["entries"])
    return payload


def render_notes_catalog_markdown(catalog: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Library Notes Catalog")
    lines.append("")
    lines.append(f"- Updated at: `{_clean_text(catalog.get('updated_at'))}`")
    lines.append(f"- Assets: `{len(catalog.get('assets', []))}`")
    lines.append(f"- Entries: `{len(catalog.get('entries', []))}`")
    lines.append("")
    lines.append("## Assets")
    lines.append("")
    assets = list(catalog.get("assets", []))
    if not assets:
        lines.append("- No managed notes assets registered.")
    for asset in assets:
        lines.append(
            f"- `{_clean_text(asset.get('notes_id'))}` format `{_clean_text(asset.get('notes_format'))}` "
            f"linked `{_clean_text(asset.get('linked_source_id') or '-')}` "
            f"entries `{int(asset.get('entry_count', 0) or 0)}` "
            f"unresolved `{int(asset.get('unresolved_entry_count', 0) or 0)}`"
        )
    lines.append("")
    lines.append("## Unresolved Entries")
    lines.append("")
    unresolved = [entry for entry in catalog.get("entries", []) if _clean_text(entry.get("alignment_status")) != "aligned"]
    if not unresolved:
        lines.append("- No unresolved entries.")
    for entry in unresolved[:50]:
        lines.append(
            f"- `{_clean_text(entry.get('entry_id'))}` title `{_clean_text(entry.get('title'))}` "
            f"reason `{_clean_text(entry.get('unresolved_reason') or entry.get('source_match_reason'))}`"
        )
    return "\n".join(lines)


def save_notes_catalog(paths: LibraryNotesPaths, catalog: dict[str, Any]) -> dict[str, Any]:
    payload = dict(catalog)
    payload["version"] = NOTES_CATALOG_VERSION
    payload["updated_at"] = utc_now()
    payload["asset_count"] = len(payload.get("assets", []))
    payload["entry_count"] = len(payload.get("entries", []))
    write_json(paths.notes_catalog_json_path, payload)
    write_markdown(paths.notes_catalog_md_path, render_notes_catalog_markdown(payload))
    return payload


def load_source_catalog(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"records": []}
    payload = load_json(path)
    payload.setdefault("records", [])
    return payload


def _extract_asset_title(markdown: str, fallback_name: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return _clean_heading_text(stripped)
    return _clean_text(Path(fallback_name).stem.replace("_", " ").replace("-", " "))


def _extract_chapter_heading_info(raw_heading: str) -> tuple[int | None, str]:
    cleaned = _clean_heading_text(raw_heading)
    chapter_number: int | None = None
    numeric_match = re.search(r"\bchapter\s+(\d+)\b", cleaned, flags=re.IGNORECASE)
    if numeric_match is None:
        numeric_match = re.search(r"第\s*(\d+)\s*[章节回]", cleaned)
    if numeric_match is not None:
        chapter_number = int(numeric_match.group(1))
    chapter_title = cleaned
    chapter_title = re.sub(r"^#+\s*", "", chapter_title)
    chapter_title = re.sub(r"^\*+", "", chapter_title).strip()
    return chapter_number, chapter_title


def _detect_notes_format(markdown: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and ("[http" in stripped or "](" in stripped):
            return "google_books_markdown"
    return "wechat_markdown"


def default_structure_mode(source_format: str) -> str:
    if source_format == "google_books_markdown":
        return "page_stream"
    return "section_markdown"


def _clean_heading_text(text: str) -> str:
    cleaned = unicodedata.normalize("NFKC", text or "")
    cleaned = cleaned.replace("\u00a0", " ")
    cleaned = re.sub(r"^#+\s*", "", cleaned)
    cleaned = cleaned.replace("*", " ")
    cleaned = cleaned.replace("《", "《").replace("》", "》")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" -")


def _parse_google_books_entry(line: str) -> dict[str, Any] | None:
    stripped = line.strip()
    if not stripped.startswith("|") or ("[http" not in stripped and "](" not in stripped):
        return None
    content = stripped.strip("|").strip()
    if set(content) == {"-"}:
        return None
    content = re.sub(r"!\[\]\[image\d+\]\s*", "", content)
    page_match = re.search(r"\[(?P<page>\d+)\]\(", content)
    if page_match is None:
        return None
    prefix = content[: page_match.start()].strip()
    suffix = content[page_match.end() :]
    closing_paren_index = suffix.find(")")
    if closing_paren_index >= 0:
        suffix = suffix[closing_paren_index + 1 :]
    prefix = re.sub(r"\b[A-Z][a-z]+ \d{1,2}, \d{4}\s*$", "", prefix).strip()
    if not prefix:
        return None
    quote = ""
    note = ""
    starred = list(re.finditer(r"\*(.+?)\*", prefix))
    if starred:
        quote = starred[-1].group(1).strip()
        note = prefix[starred[-1].end() :].strip()
    else:
        quote = prefix
    quote = _clean_quote_text(quote)
    note = _clean_quote_text(" ".join(part for part in (note, suffix) if _clean_text(part)))
    if not quote:
        return None
    return {
        "page_hint": page_match.group("page"),
        "raw_locator": f"p.{page_match.group('page')}",
        "section_label": "",
        "quote_text": quote,
        "note_text": note,
        "raw_block": stripped,
    }


def parse_google_books_markdown(markdown: str, *, fallback_title: str) -> dict[str, Any]:
    asset_title = _extract_asset_title(markdown, fallback_title)
    current_heading = ""
    entry_rows: list[dict[str, Any]] = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("##") or stripped.startswith("###"):
            current_heading = stripped
            continue
        parsed = _parse_google_books_entry(line)
        if parsed is None:
            continue
        chapter_number, chapter_title = _extract_chapter_heading_info(current_heading)
        parsed["chapter_hint_raw"] = current_heading
        parsed["chapter_hint_number"] = chapter_number
        parsed["chapter_hint_title"] = chapter_title
        if chapter_title and not parsed.get("section_label"):
            parsed["section_label"] = chapter_title
        entry_rows.append(parsed)
    return {
        "source_format": "google_books_markdown",
        "title": asset_title,
        "author": "",
        "entries": entry_rows,
    }


def parse_wechat_markdown(markdown: str, *, fallback_title: str) -> dict[str, Any]:
    asset_title = _extract_asset_title(markdown, fallback_title)
    lines = markdown.splitlines()
    current_heading = ""
    entries: list[dict[str, Any]] = []
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if stripped.startswith("###") or stripped.startswith("##"):
            current_heading = stripped
            index += 1
            continue
        if stripped.startswith(">"):
            quote_lines: list[str] = []
            note_lines: list[str] = []
            while index < len(lines):
                current = lines[index].strip()
                if current.startswith("###") or current.startswith("##"):
                    break
                if current.startswith(">"):
                    quote_lines.append(current.lstrip(">").strip())
                elif current.startswith("我的批注：") or current.startswith("My note:"):
                    note_lines.append(current.split("：", 1)[-1].split(":", 1)[-1].strip())
                elif quote_lines and current:
                    note_lines.append(current)
                elif quote_lines and not current:
                    break
                index += 1
            quote_text = _clean_quote_text(" ".join(quote_lines))
            note_text = _clean_quote_text(" ".join(note_lines))
            if quote_text:
                chapter_number, chapter_title = _extract_chapter_heading_info(current_heading)
                entries.append(
                    {
                        "page_hint": "",
                        "raw_locator": _clean_heading_text(current_heading),
                        "section_label": chapter_title,
                        "quote_text": quote_text,
                        "note_text": note_text,
                        "chapter_hint_raw": current_heading,
                        "chapter_hint_number": chapter_number,
                        "chapter_hint_title": chapter_title,
                        "raw_block": "\n".join(quote_lines + note_lines),
                    }
                )
            continue
        if stripped.startswith("- "):
            block_lines = [lines[index]]
            index += 1
            while index < len(lines):
                current = lines[index].strip()
                if current.startswith("###") or current.startswith("##") or current.startswith("- "):
                    break
                block_lines.append(lines[index])
                index += 1
            parsed = _parse_wechat_bullet_block(block_lines, current_heading=current_heading)
            if parsed is not None:
                entries.append(parsed)
            continue
        index += 1
    return {
        "source_format": "wechat_markdown",
        "title": asset_title,
        "author": "",
        "entries": entries,
    }


def parse_notes_export(path: Path, *, source_format: str = "auto") -> dict[str, Any]:
    markdown = path.read_text(encoding="utf-8")
    effective_format = source_format if source_format != "auto" else _detect_notes_format(markdown)
    if effective_format == "google_books_markdown":
        return parse_google_books_markdown(markdown, fallback_title=path.name)
    if effective_format == "wechat_markdown":
        return parse_wechat_markdown(markdown, fallback_title=path.name)
    raise ValueError(f"Unsupported notes format: {effective_format}")


def _source_record_indexes(source_catalog: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    by_source_id: dict[str, dict[str, Any]] = {}
    by_title: dict[str, list[dict[str, Any]]] = {}
    for record in source_catalog.get("records", []):
        if not isinstance(record, dict):
            continue
        source_id = _clean_text(record.get("source_id"))
        if source_id:
            by_source_id[source_id] = record
        title_key = normalize_text(_clean_text(record.get("title")))
        if title_key:
            by_title.setdefault(title_key, []).append(record)
    return by_source_id, by_title


def _parse_wechat_bullet_block(block_lines: list[str], *, current_heading: str) -> dict[str, Any] | None:
    first_line = block_lines[0].strip()
    bullet_text = _clean_quote_text(first_line[2:].strip())
    quote_lines: list[str] = []
    note_lines: list[str] = []
    metadata_only = "发表想法" in bullet_text or bullet_text == "点评"

    if bullet_text and not metadata_only:
        quote_lines.append(bullet_text)

    for raw_line in block_lines[1:]:
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith(">"):
            quoted = stripped.lstrip(">").strip()
            quoted = re.sub(r"^(原文|Original)[:：]\s*", "", quoted, flags=re.IGNORECASE)
            if quoted:
                quote_lines.append(quoted)
            continue
        cleaned = _clean_quote_text(stripped)
        if cleaned and cleaned != bullet_text:
            note_lines.append(cleaned)

    quote_text = _clean_quote_text(" ".join(quote_lines))
    if not quote_text:
        return None
    chapter_number, chapter_title = _extract_chapter_heading_info(current_heading)
    return {
        "page_hint": "",
        "raw_locator": _clean_heading_text(current_heading),
        "section_label": chapter_title,
        "quote_text": quote_text,
        "note_text": _clean_quote_text(" ".join(note_lines)),
        "chapter_hint_raw": current_heading,
        "chapter_hint_number": chapter_number,
        "chapter_hint_title": chapter_title,
        "raw_block": "\n".join(block_lines),
    }


def resolve_source_record(
    source_catalog: dict[str, Any],
    *,
    explicit_source_id: str = "",
    title_hint: str = "",
) -> tuple[dict[str, Any] | None, str, str]:
    by_source_id, by_title = _source_record_indexes(source_catalog)
    source_id = _clean_text(explicit_source_id)
    if source_id:
        record = by_source_id.get(source_id)
        if record is not None:
            return record, "linked", "matched_source_id"
        return None, "unresolved", f"source_id_not_found:{source_id}"
    title_key = normalize_text(_clean_text(title_hint))
    if title_key and len(by_title.get(title_key, [])) == 1:
        return by_title[title_key][0], "linked", "matched_title"
    if title_key and len(by_title.get(title_key, [])) > 1:
        return None, "unresolved", f"ambiguous_title:{title_hint}"
    return None, "unresolved", "no_source_match"


def _sentence_rows(book_document: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for chapter in book_document.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        chapter_id = int(chapter.get("id", 0) or 0)
        chapter_title = _clean_text(chapter.get("title"))
        chapter_number = chapter.get("chapter_number")
        for sentence in chapter.get("sentences", []):
            if not isinstance(sentence, dict):
                continue
            rows.append(
                {
                    "chapter_id": chapter_id,
                    "chapter_title": chapter_title,
                    "chapter_number": chapter_number,
                    "sentence_id": _clean_text(sentence.get("sentence_id")),
                    "text": _clean_text(sentence.get("text")),
                    "paragraph_index": int(sentence.get("paragraph_index", 0) or 0),
                    "locator": dict(sentence.get("locator") or {}),
                }
            )
    return rows


def _chapter_candidates_for_entry(entry: dict[str, Any], book_document: dict[str, Any]) -> list[dict[str, Any]]:
    chapter_number = entry.get("chapter_hint_number")
    chapter_title = normalize_text(_clean_text(entry.get("chapter_hint_title")))
    chapters = [chapter for chapter in book_document.get("chapters", []) if isinstance(chapter, dict)]
    filtered = []
    for chapter in chapters:
        if chapter_number is not None and chapter.get("chapter_number") == chapter_number:
            filtered.append(chapter)
            continue
        if chapter_number is not None and int(chapter.get("id", 0) or 0) == chapter_number:
            filtered.append(chapter)
            continue
        if chapter_title and chapter_title in normalize_text(_clean_text(chapter.get("title"))):
            filtered.append(chapter)
    return filtered or chapters


def _alignment_index(book_document: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, dict[str, Any]] = {}
    for chapter in book_document.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        chapter_id = str(chapter.get("id", "") or "")
        if not chapter_id:
            continue
        prepared_rows: list[dict[str, Any]] = []
        chapter_token_set: set[str] = set()
        joined_normalized_parts: list[str] = []
        sentence_ranges: list[dict[str, int]] = []
        current_offset = 0
        sentences = [sentence for sentence in chapter.get("sentences", []) if isinstance(sentence, dict)]
        for position, sentence in enumerate(sentences):
            sentence_text = _clean_text(sentence.get("text"))
            if not sentence_text:
                continue
            normalized_text = normalize_text(sentence_text)
            sentence_token_set = set(_normalized_tokens(normalized_text))
            chapter_token_set.update(sentence_token_set)
            prepared = {
                "sentence_id": _clean_text(sentence.get("sentence_id")),
                "paragraph_index": int(sentence.get("paragraph_index", 0) or 0),
                "text": sentence_text,
                "normalized_text": normalized_text,
                "token_set": sentence_token_set,
                "next_sentence_id": "",
                "paragraph_end": int(sentence.get("paragraph_index", 0) or 0),
                "span_text": "",
                "span_normalized_text": "",
                "span_token_set": set(),
            }
            if position + 1 < len(sentences):
                next_sentence = sentences[position + 1]
                next_text = _clean_text(next_sentence.get("text"))
                if next_text:
                    span_text = _clean_text(f"{sentence_text} {next_text}")
                    prepared["next_sentence_id"] = _clean_text(next_sentence.get("sentence_id"))
                    prepared["paragraph_end"] = int(next_sentence.get("paragraph_index", 0) or 0)
                    prepared["span_text"] = span_text
                    prepared["span_normalized_text"] = normalize_text(span_text)
                    prepared["span_token_set"] = set(_normalized_tokens(prepared["span_normalized_text"]))
            prepared_rows.append(prepared)
            joiner = _normalized_join_separator(
                joined_normalized_parts[-1] if joined_normalized_parts else "",
                normalized_text,
            )
            if joiner:
                current_offset += len(joiner)
            joined_normalized_parts.append(f"{joiner}{normalized_text}")
            sentence_ranges.append(
                {
                    "start": current_offset,
                    "end": current_offset + len(normalized_text),
                }
            )
            current_offset += len(normalized_text)
        index[chapter_id] = {
            "chapter_id": chapter_id,
            "chapter_title": _clean_text(chapter.get("title")),
            "token_set": chapter_token_set,
            "sentences": prepared_rows,
            "joined_normalized_text": "".join(joined_normalized_parts),
            "sentence_ranges": sentence_ranges,
        }
    return index


def _rank_candidate_chapters(
    candidate_chapters: list[dict[str, Any]],
    prepared_index: dict[str, dict[str, Any]],
    *,
    normalized_quote: str,
) -> list[dict[str, Any]]:
    if len(candidate_chapters) <= 3:
        return candidate_chapters
    quote_tokens = set(_normalized_tokens(normalized_quote))
    if not quote_tokens:
        return candidate_chapters[:3]

    def sort_key(chapter: dict[str, Any]) -> tuple[int, int]:
        chapter_id = str(chapter.get("id", "") or "")
        prepared = prepared_index.get(chapter_id) or {}
        chapter_tokens = prepared.get("token_set") or set()
        overlap = len(quote_tokens.intersection(chapter_tokens))
        chapter_number = int(chapter.get("chapter_number", 0) or 0)
        return (overlap, -chapter_number)

    ranked = sorted(candidate_chapters, key=sort_key, reverse=True)
    best_overlap = sort_key(ranked[0])[0]
    if best_overlap <= 0:
        return candidate_chapters
    return ranked[:3]


def _should_compare_sentence(
    *,
    quote_tokens: set[str],
    sentence_tokens: set[str],
    quote_length: int,
) -> bool:
    if not quote_tokens or not sentence_tokens:
        return True
    overlap = len(quote_tokens.intersection(sentence_tokens))
    if quote_length >= 160:
        return overlap >= 3
    if quote_length >= 80:
        return overlap >= 2
    if quote_length >= 30:
        return overlap >= 1
    return True


def _exact_quote_alignment(
    *,
    normalized_quote: str,
    chapter_payload: dict[str, Any],
) -> dict[str, Any] | None:
    joined_normalized_text = str(chapter_payload.get("joined_normalized_text") or "")
    if not joined_normalized_text or not normalized_quote:
        return None
    match_start = joined_normalized_text.find(normalized_quote)
    if match_start < 0:
        return None
    match_end = match_start + len(normalized_quote)
    sentences = list(chapter_payload.get("sentences") or [])
    sentence_ranges = list(chapter_payload.get("sentence_ranges") or [])
    if not sentences or not sentence_ranges:
        return None
    start_index: int | None = None
    end_index: int | None = None
    for index, sentence_range in enumerate(sentence_ranges):
        if int(sentence_range.get("end", 0) or 0) <= match_start:
            continue
        if int(sentence_range.get("start", 0) or 0) >= match_end and start_index is not None:
            break
        if start_index is None:
            start_index = index
        end_index = index
    if start_index is None or end_index is None:
        return None
    start_sentence = sentences[start_index]
    end_sentence = sentences[end_index]
    aligned_text = _clean_text(" ".join(str(sentence["text"]) for sentence in sentences[start_index : end_index + 1]))
    return {
        "status": "aligned",
        "match_type": "exact_chapter_span" if end_index > start_index else "exact_sentence",
        "score": 100.0,
        "chapter_id": str(chapter_payload.get("chapter_id") or ""),
        "chapter_title": str(chapter_payload.get("chapter_title") or ""),
        "sentence_start_id": str(start_sentence.get("sentence_id") or ""),
        "sentence_end_id": str(end_sentence.get("sentence_id") or ""),
        "paragraph_start": int(start_sentence.get("paragraph_index", 0) or 0),
        "paragraph_end": int(end_sentence.get("paragraph_end", end_sentence.get("paragraph_index", 0)) or 0),
        "aligned_text": aligned_text,
    }


def align_entry_to_book_document(
    entry: dict[str, Any],
    book_document: dict[str, Any],
    *,
    prepared_sentences_by_chapter: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    quote_text = _clean_text(entry.get("quote") or entry.get("quote_text"))
    if not quote_text:
        return {
            "status": "unresolved",
            "match_type": "missing_quote",
            "score": 0.0,
        }
    normalized_quote = normalize_text(quote_text)
    best_alignment: dict[str, Any] | None = None
    quote_tokens = set(_normalized_tokens(normalized_quote))
    candidate_chapters = _chapter_candidates_for_entry(entry, book_document)
    prepared_index = prepared_sentences_by_chapter or _alignment_index(book_document)
    ranked_chapters = _rank_candidate_chapters(
        candidate_chapters,
        prepared_index,
        normalized_quote=normalized_quote,
    )
    for chapter in ranked_chapters:
        chapter_id = str(chapter.get("id", "") or "")
        chapter_title = _clean_text(chapter.get("title"))
        chapter_payload = prepared_index.get(chapter_id) or {}
        exact_alignment = _exact_quote_alignment(
            normalized_quote=normalized_quote,
            chapter_payload=chapter_payload,
        )
        if exact_alignment is not None:
            return exact_alignment
        sentences = chapter_payload.get("sentences", [])
        for sentence in sentences:
            sentence_text = str(sentence["text"])
            if not sentence_text:
                continue
            if not _should_compare_sentence(
                quote_tokens=quote_tokens,
                sentence_tokens=set(sentence.get("token_set") or ()),
                quote_length=len(normalized_quote),
            ) and not _should_compare_sentence(
                quote_tokens=quote_tokens,
                sentence_tokens=set(sentence.get("span_token_set") or ()),
                quote_length=len(normalized_quote),
            ):
                continue
            exact_match = normalized_quote in str(sentence["normalized_text"])
            score = (
                100.0
                if exact_match
                else fuzzy_ratio_normalized(normalized_quote, str(sentence["normalized_text"]))
            )
            if not exact_match and sentence["span_text"]:
                span_text = str(sentence["span_text"])
                span_score = fuzzy_ratio_normalized(normalized_quote, str(sentence["span_normalized_text"]))
                if span_score > score:
                    score = span_score
                    alignment = {
                        "status": "aligned" if span_score >= 55.0 else "unresolved",
                        "match_type": "fuzzy_span",
                        "score": round(span_score, 3),
                        "chapter_id": chapter_id,
                        "chapter_title": chapter_title,
                        "sentence_start_id": str(sentence["sentence_id"]),
                        "sentence_end_id": str(sentence["next_sentence_id"]),
                        "paragraph_start": int(sentence["paragraph_index"]),
                        "paragraph_end": int(sentence["paragraph_end"]),
                        "aligned_text": span_text,
                    }
                else:
                    alignment = {
                        "status": "aligned" if score >= 55.0 else "unresolved",
                        "match_type": "exact_sentence" if exact_match else "fuzzy_sentence",
                        "score": round(score, 3),
                        "chapter_id": chapter_id,
                        "chapter_title": chapter_title,
                        "sentence_start_id": str(sentence["sentence_id"]),
                        "sentence_end_id": str(sentence["sentence_id"]),
                        "paragraph_start": int(sentence["paragraph_index"]),
                        "paragraph_end": int(sentence["paragraph_index"]),
                        "aligned_text": sentence_text,
                    }
            else:
                alignment = {
                    "status": "aligned" if score >= 55.0 else "unresolved",
                    "match_type": "exact_sentence" if exact_match else "fuzzy_sentence",
                    "score": round(score, 3),
                    "chapter_id": chapter_id,
                    "chapter_title": chapter_title,
                    "sentence_start_id": str(sentence["sentence_id"]),
                    "sentence_end_id": str(sentence["sentence_id"]),
                    "paragraph_start": int(sentence["paragraph_index"]),
                    "paragraph_end": int(sentence["paragraph_index"]),
                    "aligned_text": sentence_text,
                }
            if best_alignment is None or float(alignment["score"]) > float(best_alignment["score"]):
                best_alignment = alignment
            if exact_match:
                return alignment
    return best_alignment or {
        "status": "unresolved",
        "match_type": "no_candidate",
        "score": 0.0,
    }


def load_book_document_for_source_record(root: Path, source_record: dict[str, Any]) -> dict[str, Any] | None:
    output_dir = _clean_text(source_record.get("output_dir"))
    if not output_dir:
        relative_local_path = _clean_text(source_record.get("relative_local_path"))
        if not relative_local_path:
            return None
        source_path = root.resolve() / relative_local_path
        if not source_path.exists():
            return None
        provisioned = ensure_canonical_parse(source_path)
        path = Path(provisioned.output_dir) / "public" / "book_document.json"
    else:
        path = root.resolve() / output_dir / "public" / "book_document.json"
    if not path.exists():
        return None
    return load_json(path)


def align_entries_to_source_record(root: Path, source_record: dict[str, Any], entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    book_document = load_book_document_for_source_record(root, source_record)
    if book_document is None:
        aligned_entries = []
        for entry in entries:
            aligned = dict(entry)
            aligned["alignment"] = {
                "status": "unresolved",
                "match_type": "missing_book_document",
                "score": 0.0,
            }
            aligned["alignment_status"] = "unresolved"
            aligned["alignment_confidence"] = 0.0
            aligned_entries.append(aligned)
        return aligned_entries
    prepared_sentences_by_chapter = _alignment_index(book_document)
    aligned_entries = []
    for entry in entries:
        aligned = dict(entry)
        aligned["alignment"] = align_entry_to_book_document(
            aligned,
            book_document,
            prepared_sentences_by_chapter=prepared_sentences_by_chapter,
        )
        alignment = aligned["alignment"]
        aligned["alignment_status"] = _clean_text(alignment.get("status"))
        aligned["alignment_confidence"] = float(alignment.get("score", 0.0) or 0.0)
        aligned["matched_chapter_id"] = _clean_text(alignment.get("chapter_id"))
        if aligned["matched_chapter_id"]:
            aligned["section_label"] = _clean_text(alignment.get("chapter_title")) or aligned.get("section_label", "")
        if _clean_text(alignment.get("sentence_start_id")):
            aligned["matched_sentence_span"] = {
                "start_sentence_id": _clean_text(alignment.get("sentence_start_id")),
                "end_sentence_id": _clean_text(alignment.get("sentence_end_id")),
                "paragraph_start": int(alignment.get("paragraph_start", 0) or 0),
                "paragraph_end": int(alignment.get("paragraph_end", 0) or 0),
            }
            sentence_ids = [_clean_text(alignment.get("sentence_start_id"))]
            end_sentence_id = _clean_text(alignment.get("sentence_end_id"))
            if end_sentence_id and end_sentence_id != sentence_ids[0]:
                sentence_ids.append(end_sentence_id)
            aligned["matched_sentence_ids"] = sentence_ids
        aligned_entries.append(aligned)
    return aligned_entries


def _managed_raw_export_path(paths: LibraryNotesPaths, *, asset_id: str, raw_export_path: Path) -> Path:
    suffix = raw_export_path.suffix or ".md"
    return paths.raw_exports_root / asset_id / f"raw_export{suffix}"


def _entries_path(paths: LibraryNotesPaths, *, notes_id: str) -> Path:
    return paths.notes_entries_root / f"{notes_id}.jsonl"


def _write_entries_jsonl(path: Path, entries: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _normalize_entries(
    notes_id: str,
    parsed_export: dict[str, Any],
    *,
    linked_source_id: str,
    language: str,
    structure_mode: str,
    status: str,
    notes_format: str,
    source_link_status: str,
    source_match_reason: str,
    unresolved_reason: str,
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    title = _clean_text(parsed_export.get("title"))
    author = _clean_text(parsed_export.get("author"))
    for index, item in enumerate(parsed_export.get("entries", []), start=1):
        if not isinstance(item, dict):
            continue
        entry_id = f"{notes_id}__e{index:04d}"
        normalized.append(
            {
                "notes_id": notes_id,
                "entry_id": entry_id,
                "registered_at": utc_now(),
                "language": language,
                "notes_format": notes_format,
                "structure_mode": structure_mode,
                "status": status,
                "source_link_status": source_link_status,
                "linked_source_id": linked_source_id,
                "source_match_reason": source_match_reason,
                "unresolved_reason": unresolved_reason if source_link_status != "linked" else "",
                "title": title,
                "author": author,
                "raw_locator": _clean_text(item.get("raw_locator") or item.get("page_hint")),
                "section_label": _clean_text(item.get("section_label") or item.get("chapter_hint_title")),
                "chapter_hint_raw": _clean_text(item.get("chapter_hint_raw")),
                "chapter_hint_number": item.get("chapter_hint_number"),
                "chapter_hint_title": _clean_text(item.get("chapter_hint_title")),
                "page_hint": _clean_text(item.get("page_hint")),
                "quote": _clean_text(item.get("quote_text")),
                "note": _clean_text(item.get("note_text")),
                "raw_block": _clean_text(item.get("raw_block")),
                "alignment_status": "unresolved",
                "alignment_confidence": 0.0,
                "matched_chapter_id": "",
                "matched_sentence_span": None,
                "matched_sentence_ids": [],
                "alignment": None,
            }
        )
    return normalized


def register_notes_asset(
    paths: LibraryNotesPaths,
    *,
    notes_id: str,
    linked_source_id: str,
    title: str,
    language: str,
    notes_format: str,
    origin_path: Path,
    structure_mode: str = "",
    status: str = "active",
    source_catalog_path: Path,
    title_hint: str = "",
) -> dict[str, Any]:
    parsed_export = parse_notes_export(origin_path, source_format=notes_format)
    effective_format = _clean_text(parsed_export.get("source_format")) or notes_format
    effective_structure_mode = _clean_text(structure_mode) or default_structure_mode(effective_format)
    source_catalog = load_source_catalog(source_catalog_path)
    source_record, source_link_status, source_match_reason = resolve_source_record(
        source_catalog,
        explicit_source_id=linked_source_id,
        title_hint=title_hint or title or _clean_text(parsed_export.get("title")),
    )
    linked_source_id = _clean_text(source_record.get("source_id")) if isinstance(source_record, dict) else ""
    unresolved_reason = "" if source_link_status == "linked" else source_match_reason
    raw_sha256 = sha256_file(origin_path)
    normalized_notes_id = _sanitize_slug(notes_id)
    managed_raw_path = _managed_raw_export_path(paths, asset_id=normalized_notes_id, raw_export_path=origin_path)
    managed_raw_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(origin_path, managed_raw_path)

    entries = _normalize_entries(
        normalized_notes_id,
        parsed_export,
        linked_source_id=linked_source_id,
        language=language,
        structure_mode=effective_structure_mode,
        status=status,
        notes_format=effective_format,
        source_link_status=source_link_status,
        source_match_reason=source_match_reason,
        unresolved_reason=unresolved_reason,
    )
    if source_record is not None:
        entries = align_entries_to_source_record(paths.root, source_record, entries)
    else:
        entries = [
            {
                **entry,
                "alignment": {
                    "status": "unresolved",
                    "match_type": "unlinked_source",
                    "score": 0.0,
                },
            }
            for entry in entries
        ]

    catalog = load_notes_catalog(paths.notes_catalog_json_path)
    assets = [asset for asset in catalog.get("assets", []) if _clean_text(asset.get("notes_id")) != normalized_notes_id]
    existing_entries = [entry for entry in catalog.get("entries", []) if _clean_text(entry.get("notes_id")) != normalized_notes_id]
    asset_record = {
        "notes_id": normalized_notes_id,
        "registered_at": utc_now(),
        "linked_source_id": linked_source_id,
        "title": title or _clean_text(parsed_export.get("title")),
        "language": language,
        "notes_format": effective_format,
        "origin_path": str(origin_path),
        "relative_notes_path": str(managed_raw_path.relative_to(paths.root)),
        "structure_mode": effective_structure_mode,
        "status": status,
        "linked_source_id": linked_source_id,
        "source_link_status": source_link_status,
        "source_match_reason": source_match_reason,
        "author": _clean_text(parsed_export.get("author")),
        "raw_sha256": raw_sha256,
        "raw_export_file_name": origin_path.name,
        "entry_count": len(entries),
        "unresolved_entry_count": sum(1 for entry in entries if _clean_text(entry.get("alignment_status")) != "aligned"),
        "aligned_entry_count": sum(
            1
            for entry in entries
            if _clean_text(entry.get("alignment_status")) == "aligned"
        ),
        "entries_rel_path": str(_entries_path(paths, notes_id=normalized_notes_id).relative_to(paths.root)),
    }
    assets.append(asset_record)
    assets.sort(key=lambda asset: _clean_text(asset.get("notes_id")))
    existing_entries.extend(entries)
    existing_entries.sort(key=lambda entry: _clean_text(entry.get("entry_id")))
    _write_entries_jsonl(_entries_path(paths, notes_id=normalized_notes_id), entries)
    save_notes_catalog(
        paths,
        {
            "version": NOTES_CATALOG_VERSION,
            "assets": assets,
            "entries": existing_entries,
        },
    )
    return {
        "asset": asset_record,
        "entries": entries,
        "source_link_status": source_link_status,
        "source_match_reason": source_match_reason,
    }


def register_notes_export(
    paths: LibraryNotesPaths,
    *,
    raw_export_path: Path,
    source_catalog_path: Path,
    source_format: str = "auto",
    explicit_source_id: str = "",
    title_hint: str = "",
) -> dict[str, Any]:
    parsed = parse_notes_export(raw_export_path, source_format=source_format)
    notes_id = _sanitize_slug(explicit_source_id or _clean_text(parsed.get("title")) or raw_export_path.stem)
    return register_notes_asset(
        paths,
        notes_id=notes_id,
        linked_source_id=explicit_source_id,
        title=_clean_text(parsed.get("title")),
        language="unknown",
        notes_format=_clean_text(parsed.get("source_format")) or source_format,
        origin_path=raw_export_path,
        structure_mode=default_structure_mode(_clean_text(parsed.get("source_format")) or source_format),
        status="active",
        source_catalog_path=source_catalog_path,
        title_hint=title_hint,
    )

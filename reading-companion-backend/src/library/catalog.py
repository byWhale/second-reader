"""Catalog helpers that aggregate output artifacts into product-facing views."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

from .pagination import paginate_items
from .storage import jobs_dir, load_json as load_state_json
from .user_marks import list_book_marks, list_marks
from src.api.contract import (
    REACTION_FILTERS,
    canonical_book_path,
    canonical_chapter_path,
    to_api_book_id,
    to_api_reaction_id,
    to_api_reaction_type,
)
from src.iterator_reader.storage import (
    activity_file,
    book_manifest_file,
    chapter_result_file,
    existing_chapter_result_file,
    existing_cover_asset_file,
    existing_activity_file,
    existing_book_manifest_file,
    existing_parse_state_file,
    existing_run_state_file,
    resolve_output_relative_file,
    run_state_file,
)
from src.iterator_reader.frontend_artifacts import normalize_activity_event


def output_root(root: Path | None = None) -> Path:
    """Return the root output directory."""
    return (root or Path.cwd()) / "output"


def _load_json(path: Path) -> dict:
    """Load one JSON object if it exists."""
    return json.loads(path.read_text(encoding="utf-8"))


def _excerpt_text(value: str, *, max_length: int = 132) -> str:
    """Collapse whitespace and trim long preview strings."""
    normalized = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(normalized) <= max_length:
        return normalized
    return f"{normalized[: max_length - 3].rstrip()}..."


def _chapter_heading_payload(payload: object) -> dict | None:
    """Return one public-safe chapter heading block when available."""
    if not isinstance(payload, dict):
        return None
    text = str(payload.get("text", "") or "").strip()
    title = str(payload.get("title", "") or "").strip()
    if not text and not title:
        return None
    normalized = {
        "label": str(payload.get("label", "") or "").strip() or None,
        "title": title or text,
        "subtitle": str(payload.get("subtitle", "") or "").strip() or None,
        "text": text or title,
        "locator": payload.get("locator"),
    }
    return normalized


def _natural_sort_key(value: str) -> tuple[object, ...]:
    """Return a stable natural-sort key for chapter and section references."""
    parts = re.split(r"(\d+)", str(value or "").strip().lower())
    key: list[object] = []
    for part in parts:
        if not part:
            continue
        key.append(int(part) if part.isdigit() else part)
    return tuple(key)


def _load_jsonl(path: Path) -> list[dict]:
    """Load one JSONL file into a list of dictionaries."""
    if not path.exists():
        return []
    items: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            items.append(payload)
    return items


def _file_sha1(path: Path) -> str | None:
    """Return a stable digest for one file, or None if the file is missing."""
    try:
        digest = hashlib.sha1()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except FileNotFoundError:
        return None
    return digest.hexdigest()


def _book_dir(book_id: str, root: Path | None = None) -> Path:
    """Resolve one output directory by book id."""
    return output_root(root) / book_id


def _manifest_paths(root: Path | None = None) -> list[Path]:
    """Return canonical and legacy manifest paths without duplicates."""
    manifest_paths = sorted(output_root(root).glob("*/public/book_manifest.json"))
    manifest_paths.extend(sorted(output_root(root).glob("*/book_manifest.json")))
    seen: set[Path] = set()
    unique_paths: list[Path] = []
    for path in manifest_paths:
        output_dir = path.parent.parent if path.parent.name == "public" else path.parent
        if output_dir in seen:
            continue
        seen.add(output_dir)
        unique_paths.append(path)
    return unique_paths


def _manifest(book_id: str, root: Path | None = None) -> dict:
    """Load one persisted manifest."""
    path = existing_book_manifest_file(_book_dir(book_id, root))
    if not path.exists():
        raise FileNotFoundError(book_id)
    return _load_json(path)


def _run_state(book_id: str, root: Path | None = None) -> dict | None:
    """Load one persisted run state if present."""
    path = existing_run_state_file(_book_dir(book_id, root))
    return _load_json(path) if path.exists() else None


def _parse_state(book_id: str, root: Path | None = None) -> dict | None:
    """Load one persisted parse checkpoint state if present."""
    path = existing_parse_state_file(_book_dir(book_id, root))
    return _load_json(path) if path.exists() else None


def _chapter_result_path(book_id: str, chapter: dict, root: Path | None = None) -> Path:
    """Resolve one chapter result path with manifest-relative and canonical fallbacks."""
    output_dir = _book_dir(book_id, root)
    relative_path = str(chapter.get("result_file", "") or "").strip() or None
    return resolve_output_relative_file(
        output_dir,
        relative_path,
        fallback=existing_chapter_result_file(output_dir, chapter),
    )


def _sort_by_updated_and_id(items: list[dict], *, updated_key: str, id_key: str) -> list[dict]:
    """Sort by updated_at desc with id asc as the stable tie-breaker."""
    ordered = sorted(items, key=lambda item: str(item.get(id_key, "")))
    ordered.sort(key=lambda item: str(item.get(updated_key, "")), reverse=True)
    return ordered


def _display_status(manifest: dict, run_state: dict | None) -> str:
    """Map persisted state into the bookshelf/result-view status vocabulary."""
    if run_state:
        stage = str(run_state.get("stage", "")).strip()
        if stage == "error":
            return "error"
        if stage == "paused":
            return "paused"
        if stage == "completed":
            return "completed"
        if stage in {"parsing_structure", "deep_reading"}:
            return "analyzing"
    if any(str(chapter.get("status", "")).strip() == "done" for chapter in manifest.get("chapters", [])):
        return "completed"
    return "not_started"


def _has_active_analysis_job(book_id: str, root: Path | None = None) -> bool:
    """Return whether there is an in-flight deep-reading job for this book."""
    for path in sorted(jobs_dir(root).glob("*.json")):
        try:
            record = load_state_json(path)
        except (FileNotFoundError, json.JSONDecodeError):
            continue
        if str(record.get("book_id", "")).strip() != book_id:
            continue
        status = str(record.get("status", "")).strip()
        if status in {"queued", "parsing_structure", "deep_reading", "chapter_note_generation"}:
            return True
    return False


def _api_cover_url(book_id: str, manifest: dict, root: Path | None = None) -> str | None:
    """Return the API URL for the cover image when a cover asset exists."""
    api_book_id = to_api_book_id(book_id)
    if manifest.get("cover_image_url"):
        return f"/api/books/{api_book_id}/cover"
    if existing_cover_asset_file(_book_dir(book_id, root)):
        return f"/api/books/{api_book_id}/cover"
    return None


def _completed_chapter_count(manifest: dict) -> int:
    """Count completed chapters in a manifest."""
    return sum(1 for chapter in manifest.get("chapters", []) if str(chapter.get("status", "")) == "done")


def _normalize_target_locator(payload: object) -> dict | None:
    """Drop partial legacy locator payloads that no longer satisfy the public schema."""
    if not isinstance(payload, dict):
        return None
    href = str(payload.get("href", "") or "").strip()
    match_text = str(payload.get("match_text", "") or "").strip()
    match_mode = str(payload.get("match_mode", "") or "").strip()
    if not href or not match_text or not match_mode:
        return None
    return {
        "href": href,
        "start_cfi": payload.get("start_cfi"),
        "end_cfi": payload.get("end_cfi"),
        "match_text": match_text,
        "match_mode": match_mode,
    }


def _book_card(book_id: str, manifest: dict, run_state: dict | None, root: Path | None = None) -> dict:
    """Build one bookshelf card payload."""
    status = _display_status(manifest, run_state)
    if status == "not_started" and _has_active_analysis_job(book_id, root=root):
        status = "analyzing"
    mark_count = len(list_book_marks(book_id, root=root))
    api_book_id = to_api_book_id(book_id)
    return {
        "book_id": api_book_id,
        "title": str(manifest.get("book", "")),
        "author": str(manifest.get("author", "")),
        "cover_image_url": _api_cover_url(book_id, manifest, root=root),
        "book_language": str(manifest.get("book_language", "")),
        "output_language": str(manifest.get("output_language", "")),
        "reading_status": status,
        "completed_chapters": _completed_chapter_count(manifest),
        "total_chapters": len(manifest.get("chapters", [])),
        "updated_at": str(manifest.get("updated_at", "")),
        "mark_count": mark_count,
        "open_target": canonical_book_path(api_book_id),
    }


def _chapter_status_for_analysis(chapter: dict, current_chapter_id: int | None, run_state: dict | None) -> str:
    """Return the chapter status used by progress/result pages."""
    chapter_id = int(chapter.get("id", 0))
    raw_status = str(chapter.get("status", "")).strip()
    stage = str(run_state.get("stage", "")) if run_state else ""
    if stage == "error" and current_chapter_id == chapter_id:
        return "error"
    if stage in {"parsing_structure", "paused"}:
        if current_chapter_id == chapter_id:
            return "in_progress"
        if int(chapter.get("segment_count", 0) or 0) > 0:
            return "completed"
        return "pending"
    if raw_status == "done":
        return "completed"
    if current_chapter_id == chapter_id:
        return "in_progress"
    return "pending"


def _source_asset(book_id: str, manifest: dict) -> dict:
    """Build the standard source asset payload."""
    api_book_id = to_api_book_id(book_id)
    return {
        "format": str(manifest.get("source_asset", {}).get("format", "epub")),
        "url": f"/api/books/{api_book_id}/source",
        "media_type": "application/epub+zip",
    }


def list_books_page(
    root: Path | None = None,
    *,
    limit: int = 20,
    cursor: str | None = None,
    status: str | None = None,
    search: str | None = None,
) -> dict:
    """Return paginated bookshelf cards."""
    books: list[dict] = []
    for manifest_path in _manifest_paths(root):
        manifest = _load_json(manifest_path)
        manifest_parent = manifest_path.parent.parent if manifest_path.parent.name == "public" else manifest_path.parent
        book_id = str(manifest.get("book_id", manifest_parent.name))
        run_state = _run_state(book_id, root)
        books.append(_book_card(book_id, manifest, run_state, root=root))

    if search:
        needle = search.strip().lower()
        books = [
            item
            for item in books
            if needle in str(item.get("title", "")).lower() or needle in str(item.get("author", "")).lower()
        ]
    if status:
        books = [item for item in books if str(item.get("reading_status", "")) == status]

    books = _sort_by_updated_and_id(books, updated_key="updated_at", id_key="book_id")
    page_items, page_info = paginate_items(books, limit=limit, cursor=cursor)
    return {
        "items": page_items,
        "page_info": page_info,
        "global_mark_count": len(list_marks(root=root)),
    }


def list_books(root: Path | None = None) -> list[dict]:
    """Backward-compatible raw bookshelf list."""
    return list_books_page(root=root, limit=1000)["items"]


def get_book(book_id: str, root: Path | None = None) -> dict:
    """Load one book manifest plus its current run state."""
    manifest = _manifest(book_id, root)
    run_state = _run_state(book_id, root)
    return {"book_id": book_id, "manifest": manifest, "run_state": run_state}


def get_book_detail(book_id: str, root: Path | None = None) -> dict:
    """Build the result-view book overview payload."""
    manifest = _manifest(book_id, root)
    run_state = _run_state(book_id, root)
    api_book_id = to_api_book_id(book_id)
    chapters = []
    current_chapter_id = int(run_state.get("current_chapter_id", 0) or 0) or None if run_state else None
    for chapter in manifest.get("chapters", []):
        status = _chapter_status_for_analysis(chapter, current_chapter_id, run_state)
        chapters.append(
            {
                "chapter_id": int(chapter.get("id", 0)),
                "chapter_ref": str(chapter.get("reference", "")),
                "title": str(chapter.get("title", "")),
                "segment_count": int(chapter.get("segment_count", 0)),
                "status": "error" if status == "error" else ("completed" if status == "completed" else "pending"),
                "visible_reaction_count": int(chapter.get("visible_reaction_count", 0)),
                "reaction_type_diversity": int(chapter.get("reaction_type_diversity", 0)),
                "result_ready": str(chapter.get("status", "")) == "done",
            }
        )

    reaction_counts = {reaction_type: 0 for reaction_type in REACTION_FILTERS if reaction_type != "all"}
    for chapter in manifest.get("chapters", []):
        result_path = _chapter_result_path(book_id, chapter, root=root)
        if not result_path.exists():
            continue
        payload = _load_json(result_path)
        for reaction_type, count in payload.get("ui_summary", {}).get("reaction_counts", {}).items():
            api_reaction_type = to_api_reaction_type(str(reaction_type))
            reaction_counts[api_reaction_type] = reaction_counts.get(api_reaction_type, 0) + int(count)

    display_status = _display_status(manifest, run_state)
    if display_status == "not_started" and _has_active_analysis_job(book_id, root=root):
        display_status = "analyzing"

    return {
        "book_id": api_book_id,
        "title": str(manifest.get("book", "")),
        "author": str(manifest.get("author", "")),
        "cover_image_url": _api_cover_url(book_id, manifest, root=root),
        "book_language": str(manifest.get("book_language", "")),
        "output_language": str(manifest.get("output_language", "")),
        "status": display_status,
        "source_asset": _source_asset(book_id, manifest),
        "chapters": chapters,
        "my_mark_count": len(list_book_marks(book_id, root=root)),
        "reaction_counts": reaction_counts,
        "chapter_count": len(manifest.get("chapters", [])),
        "completed_chapter_count": _completed_chapter_count(manifest),
        "segment_count": sum(int(chapter.get("segment_count", 0)) for chapter in manifest.get("chapters", [])),
    }


def _event_id(event: dict) -> str:
    """Build a fallback stable event id when older artifacts do not have one."""
    raw = json.dumps(event, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _featured_reaction_preview(book_id: str, chapter_id: int, chapter_ref: str, item: dict) -> dict:
    """Normalize one compact featured reaction payload."""
    internal_reaction_id = str(item.get("reaction_id", ""))
    return {
        "reaction_id": to_api_reaction_id(book_id=book_id, reaction_id=internal_reaction_id),
        "type": to_api_reaction_type(str(item.get("type", ""))),
        "anchor_quote": str(item.get("anchor_quote", "")),
        "content": str(item.get("content", "")),
        "book_id": to_api_book_id(book_id),
        "chapter_id": chapter_id,
        "chapter_ref": chapter_ref,
        "section_ref": str(item.get("segment_ref", item.get("section_ref", ""))),
        "target_locator": _normalize_target_locator(item.get("target_locator")),
    }


def _decorate_activity_event(book_id: str, event: dict) -> dict:
    """Decorate one persisted activity event into the public API shape."""
    event = normalize_activity_event(event)
    chapter_id = int(event.get("chapter_id", 0) or 0) or None
    chapter_ref = str(event.get("chapter_ref", "") or "") or None
    section_ref = str(event.get("segment_ref", event.get("section_ref", "")) or "") or None
    featured = []
    for item in event.get("featured_reactions", []):
        if not isinstance(item, dict):
            continue
        featured.append(
            _featured_reaction_preview(
                book_id,
                chapter_id or 0,
                chapter_ref or "",
                item,
            )
        )

    return {
        "event_id": str(event.get("event_id", "") or _event_id(event)),
        "timestamp": str(event.get("timestamp", "")),
        "type": str(event.get("type", "")),
        "stream": str(event.get("stream", "")),
        "kind": str(event.get("kind", "")),
        "visibility": str(event.get("visibility", "")),
        "message": str(event.get("message", "")),
        "chapter_id": chapter_id,
        "chapter_ref": chapter_ref,
        "section_ref": section_ref,
        "highlight_quote": str(event.get("highlight_quote", "") or "") or None,
        "reaction_types": [to_api_reaction_type(str(item)) for item in event.get("reaction_types", []) if str(item).strip()],
        "search_query": str(event.get("search_query", "") or "") or None,
        "featured_reactions": featured,
        "visible_reaction_count": (
            int(event.get("visible_reaction_count", 0) or 0) if event.get("visible_reaction_count") is not None else None
        ),
        "result_url": canonical_chapter_path(to_api_book_id(book_id), chapter_id) if chapter_id is not None else None,
    }


def get_activity(book_id: str, root: Path | None = None) -> list[dict]:
    """Load the user-facing activity stream for one book."""
    return [_decorate_activity_event(book_id, item) for item in _load_jsonl(existing_activity_file(_book_dir(book_id, root)))]


def get_activity_page(
    book_id: str,
    root: Path | None = None,
    *,
    limit: int = 20,
    cursor: str | None = None,
    event_type: str | None = None,
    stream: str | None = None,
    chapter_id: int | None = None,
) -> dict:
    """Load paginated activity events for one book."""
    items = get_activity(book_id, root)
    if event_type:
        items = [item for item in items if str(item.get("type", "")) == event_type]
    if stream:
        items = [item for item in items if str(item.get("stream", "")) == stream]
    if chapter_id is not None:
        items = [item for item in items if int(item.get("chapter_id", 0) or 0) == chapter_id]
    items = _sort_by_updated_and_id(items, updated_key="timestamp", id_key="event_id")
    page_items, page_info = paginate_items(items, limit=limit, cursor=cursor)
    return {"items": page_items, "page_info": page_info}


def get_chapter_result(book_id: str, chapter_id: int, root: Path | None = None) -> dict:
    """Load one chapter companion JSON by chapter id."""
    book = get_book(book_id, root=root)
    manifest = book["manifest"]
    for chapter in manifest.get("chapters", []):
        if int(chapter.get("id", 0)) != chapter_id:
            continue
        result_path = _chapter_result_path(book_id, chapter, root=root)
        if not result_path.exists():
            raise FileNotFoundError(f"{book_id}:{chapter_id}")
        return _load_json(result_path)
    raise FileNotFoundError(f"{book_id}:{chapter_id}")


def _mark_index(book_id: str, root: Path | None = None) -> dict[str, str]:
    """Return a reaction_id -> mark_type index for one book."""
    index: dict[str, str] = {}
    for mark in list_book_marks(book_id, root=root):
        reaction_id = str(mark.get("reaction_id", "")).strip()
        mark_type = str(mark.get("mark_type", "")).strip()
        if reaction_id and mark_type:
            index[reaction_id] = mark_type
    return index


def _reaction_card(section: dict, reaction: dict, mark_index: dict[str, str]) -> dict:
    """Build one frontend reaction card."""
    reaction_id = str(reaction.get("reaction_id", ""))
    book_id = str(section.get("_book_id", ""))
    return {
        "reaction_id": to_api_reaction_id(book_id=book_id, reaction_id=reaction_id),
        "type": to_api_reaction_type(str(reaction.get("type", ""))),
        "anchor_quote": str(reaction.get("anchor_quote", "")),
        "content": str(reaction.get("content", "")),
        "search_query": str(reaction.get("search_query", "") or "") or None,
        "search_results": list(reaction.get("search_results", [])),
        "target_locator": _normalize_target_locator(reaction.get("target_locator")),
        "section_ref": str(section.get("segment_ref", "")),
        "section_summary": str(section.get("summary", "")),
        "mark_type": mark_index.get(reaction_id),
    }


def _outline_preview_text(section: dict) -> str:
    """Choose one short section preview line for the outline pane."""
    reactions = [reaction for reaction in section.get("reactions", []) if isinstance(reaction, dict)]
    for reaction in reactions:
        anchor_quote = _excerpt_text(str(reaction.get("anchor_quote", "")))
        if anchor_quote:
            return anchor_quote
    for reaction in reactions:
        content_preview = _excerpt_text(str(reaction.get("content", "")))
        if content_preview:
            return content_preview
    return _excerpt_text(str(section.get("original_text", "")))


def _chapter_outline_section(section: dict) -> dict:
    """Build one compact section-outline payload."""
    reactions = [reaction for reaction in section.get("reactions", []) if isinstance(reaction, dict)]
    return {
        "section_ref": str(section.get("segment_ref", "")),
        "summary": str(section.get("summary", "")),
        "preview_text": _outline_preview_text(section),
        "visible_reaction_count": len(reactions),
        "locator": section.get("locator"),
    }


def _filter_reactions(
    reactions: Iterable[dict],
    *,
    reaction_type: str | None = None,
    mark_type: str | None = None,
) -> list[dict]:
    """Apply filter options to a reaction card list."""
    filtered = list(reactions)
    if reaction_type and reaction_type != "all":
        normalized_type = to_api_reaction_type(reaction_type)
        filtered = [reaction for reaction in filtered if str(reaction.get("type", "")) == normalized_type]
    if mark_type:
        filtered = [reaction for reaction in filtered if str(reaction.get("mark_type", "") or "") == mark_type]
    return filtered


def get_chapter_detail(
    book_id: str,
    chapter_id: int,
    root: Path | None = None,
    *,
    limit: int = 20,
    cursor: str | None = None,
    reaction_filter: str | None = None,
) -> dict:
    """Build the chapter split-view payload."""
    manifest = _manifest(book_id, root)
    chapter_payload = get_chapter_result(book_id, chapter_id, root=root)
    mark_index = _mark_index(book_id, root)
    sections = []
    for section in chapter_payload.get("sections", []):
        if not isinstance(section, dict):
            continue
        section = {**section, "_book_id": book_id}
        reactions = [
            _reaction_card(section, reaction, mark_index)
            for reaction in section.get("reactions", [])
            if isinstance(reaction, dict)
        ]
        reactions = _filter_reactions(reactions, reaction_type=reaction_filter)
        sections.append(
            {
                "section_ref": str(section.get("segment_ref", "")),
                "summary": str(section.get("summary", "")),
                "verdict": str(section.get("verdict", "")),
                "quality_status": str(section.get("quality_status", "")),
                "skip_reason": str(section.get("skip_reason", "") or "") or None,
                "locator": section.get("locator"),
                "reactions": reactions,
            }
        )

    sections = sorted(sections, key=lambda item: _natural_sort_key(str(item.get("section_ref", ""))))
    page_sections, page_info = paginate_items(sections, limit=limit, cursor=cursor)
    chapter_info = chapter_payload.get("chapter", {})
    chapter_ref = str(chapter_info.get("reference", ""))
    chapter_id_value = int(chapter_info.get("id", chapter_id))
    return {
        "book_id": to_api_book_id(book_id),
        "chapter_id": chapter_id_value,
        "chapter_ref": chapter_ref,
        "title": str(chapter_info.get("title", "")),
        "status": "completed",
        "output_language": str(chapter_payload.get("output_language", manifest.get("output_language", ""))),
        "visible_reaction_count": int(chapter_payload.get("visible_reaction_count", 0)),
        "reaction_type_diversity": int(chapter_payload.get("reaction_type_diversity", 0)),
        "featured_reactions": [
            _featured_reaction_preview(book_id, chapter_id_value, chapter_ref, item)
            for item in chapter_payload.get("featured_reactions", [])
            if isinstance(item, dict)
        ],
        "chapter_heading": _chapter_heading_payload(chapter_payload.get("chapter_heading")),
        "chapter_reflection": [],
        "sections": page_sections,
        "sections_page_info": page_info,
        "available_filters": REACTION_FILTERS,
        "source_asset": _source_asset(book_id, manifest),
    }


def get_chapter_outline(book_id: str, chapter_id: int, root: Path | None = None) -> dict:
    """Build the lightweight outline payload for one chapter."""
    manifest = _manifest(book_id, root)
    run_state = _run_state(book_id, root)
    current_chapter_id = int(run_state.get("current_chapter_id", 0) or 0) or None if run_state else None

    chapter_entry = None
    for chapter in manifest.get("chapters", []):
        if int(chapter.get("id", 0)) == chapter_id:
            chapter_entry = chapter
            break

    if chapter_entry is None:
        raise FileNotFoundError(f"{book_id}:{chapter_id}")

    status = _chapter_status_for_analysis(chapter_entry, current_chapter_id, run_state)
    public_status = "error" if status == "error" else ("completed" if str(chapter_entry.get("status", "")) == "done" else "pending")
    result_ready = str(chapter_entry.get("status", "")) == "done"

    sections: list[dict] = []
    chapter_ref = str(chapter_entry.get("reference", ""))
    chapter_title = str(chapter_entry.get("title", ""))
    chapter_heading = _chapter_heading_payload(chapter_entry.get("chapter_heading"))
    if result_ready:
        try:
            chapter_payload = get_chapter_result(book_id, chapter_id, root=root)
        except FileNotFoundError:
            result_ready = False
        else:
            chapter_info = chapter_payload.get("chapter", {})
            chapter_ref = str(chapter_info.get("reference", chapter_ref))
            chapter_title = str(chapter_info.get("title", chapter_title))
            chapter_heading = _chapter_heading_payload(chapter_payload.get("chapter_heading")) or chapter_heading
            sections = sorted(
                [
                    _chapter_outline_section(section)
                    for section in chapter_payload.get("sections", [])
                    if isinstance(section, dict)
                ],
                key=lambda item: _natural_sort_key(str(item.get("section_ref", ""))),
            )

    return {
        "book_id": to_api_book_id(book_id),
        "chapter_id": int(chapter_entry.get("id", chapter_id)),
        "chapter_ref": chapter_ref,
        "title": chapter_title,
        "result_ready": result_ready,
        "status": public_status,
        "chapter_heading": chapter_heading,
        "section_count": len(sections) if sections else int(chapter_entry.get("segment_count", 0) or 0),
        "sections": sections,
    }


def get_chapter_reactions_page(
    book_id: str,
    chapter_id: int,
    root: Path | None = None,
    *,
    limit: int = 20,
    cursor: str | None = None,
    reaction_type: str | None = None,
    section_ref: str | None = None,
    mark_type: str | None = None,
) -> dict:
    """Build a flattened, paginated reaction list for one chapter."""
    chapter_payload = get_chapter_result(book_id, chapter_id, root=root)
    mark_index = _mark_index(book_id, root)
    reactions: list[dict] = []
    for section in chapter_payload.get("sections", []):
        if not isinstance(section, dict):
            continue
        section = {**section, "_book_id": book_id}
        current_section_ref = str(section.get("segment_ref", ""))
        if section_ref and current_section_ref != section_ref:
            continue
        for reaction in section.get("reactions", []):
            if not isinstance(reaction, dict):
                continue
            card = _reaction_card(section, reaction, mark_index)
            card["sort_key"] = (current_section_ref, str(reaction.get("reaction_id", "")))
            reactions.append(card)

    reactions = _filter_reactions(
        reactions,
        reaction_type=reaction_type,
        mark_type=mark_type,
    )
    reactions.sort(key=lambda item: tuple(item.pop("sort_key", (item.get("section_ref"), item.get("reaction_id")))))
    page_items, page_info = paginate_items(reactions, limit=limit, cursor=cursor)
    return {
        "items": page_items,
        "page_info": page_info,
        "applied_filters": {
            "type": to_api_reaction_type(reaction_type) if reaction_type else None,
            "section_ref": section_ref,
            "mark_type": mark_type,
        },
    }


def source_asset_path(book_id: str, root: Path | None = None) -> Path:
    """Return the frontend-accessible source EPUB path for one book."""
    manifest = _manifest(book_id, root)
    source_asset = manifest.get("source_asset", {})
    relative_path = str(source_asset.get("file", "_assets/source.epub"))
    return _book_dir(book_id, root) / relative_path


def cover_asset_path(book_id: str, root: Path | None = None) -> Path | None:
    """Return the cover asset path for one book when available."""
    manifest = _manifest(book_id, root)
    relative_path = str(manifest.get("cover_image_url", "") or "").strip()
    if relative_path:
        return _book_dir(book_id, root) / relative_path
    return existing_cover_asset_file(_book_dir(book_id, root))


def _message_ref(key: str | None, params: dict[str, Any] | None = None) -> tuple[str | None, dict[str, Any] | None]:
    """Normalize structured UI copy references for analysis status payloads."""
    return key, params or None


def _analysis_status(
    run_state: dict,
    *,
    current_chapter_id: int | None,
) -> tuple[str, str, str | None, dict[str, Any] | None]:
    """Map run_state into the public analysis page status vocabulary."""
    stage = str(run_state.get("stage", "ready"))
    if stage == "completed":
        key, params = _message_ref("system.stage.completed")
        return "completed", "全部完成", key, params
    if stage == "paused":
        key, params = _message_ref("system.stage.paused")
        return "paused", "已暂停，可继续", key, params
    if stage == "error":
        key, params = _message_ref("system.stage.error")
        return "error", "分析中断", key, params
    if stage == "parsing_structure":
        if current_chapter_id is not None:
            chapter_ref = str(run_state.get("current_chapter_ref", "") or "").strip()
            key, params = _message_ref("system.stage.parsingChapter", {"chapter": chapter_ref})
            return "parsing_structure", f"正在解析 {chapter_ref}", key, params
        key, params = _message_ref("system.stage.parsingStructure")
        return "parsing_structure", "正在解析书籍结构", key, params
    if current_chapter_id is not None:
        chapter_ref = str(run_state.get("current_chapter_ref", "") or "").strip()
        key, params = _message_ref("system.stage.deepReadingChapter", {"chapter": chapter_ref})
        return "deep_reading", f"正在分析 {chapter_ref}", key, params
    key, params = _message_ref("system.stage.parsingStructure")
    return "parsing_structure", "正在解析书籍结构", key, params


_PHASE_STEP_KEYS: dict[str, tuple[str, dict[str, Any] | None]] = {
    "等待继续执行": ("system.step.waitingToResume", None),
    "准备章节结构": ("system.step.prepareChapterStructure", None),
    "语义切分中": ("system.step.segmenting", None),
    "已保存结构 checkpoint": ("system.step.structureCheckpointSaved", None),
    "结构解析失败": ("system.step.structureParseFailed", None),
    "等待当前章节切分完成": ("system.step.waitingCurrentChapterSegmentation", None),
    "后台准备后续章节": ("system.step.prefetchFutureChapters", None),
    "为首章准备语义结构": ("system.step.prepareFirstChapter", None),
    "等待首章切分": ("system.step.waitingFirstChapterSegmentation", None),
    "等待后续章节切分": ("system.step.waitingNextChapterSegmentation", None),
}


def _analysis_phase_step_message(step: str | None) -> tuple[str | None, dict[str, Any] | None]:
    """Map the current raw phase-step string into a stable UI copy key when known."""
    normalized = str(step or "").strip()
    if not normalized:
        return None, None
    key, params = _PHASE_STEP_KEYS.get(normalized, (None, None))
    return _message_ref(key, params)


def get_analysis_state(book_id: str, root: Path | None = None) -> dict:
    """Build the progress-page snapshot from persisted artifacts."""
    manifest = _manifest(book_id, root)
    run_state = _run_state(book_id, root)
    if not run_state:
        raise FileNotFoundError(book_id)
    parse_state = _parse_state(book_id, root)

    current_chapter_id = int(run_state.get("current_chapter_id", 0) or 0) or None
    chapters = []
    for chapter in manifest.get("chapters", []):
        status = _chapter_status_for_analysis(chapter, current_chapter_id, run_state)
        chapters.append(
            {
                "chapter_id": int(chapter.get("id", 0)),
                "chapter_ref": str(chapter.get("reference", "")),
                "title": str(chapter.get("title", "")),
                "segment_count": int(chapter.get("segment_count", 0)),
                "status": status,
                "is_current": current_chapter_id == int(chapter.get("id", 0)),
                "result_ready": str(chapter.get("status", "")) == "done",
            }
        )

    recent_activity = get_activity(book_id, root)
    recent_activity = _sort_by_updated_and_id(recent_activity, updated_key="timestamp", id_key="event_id")

    reaction_counts: dict[str, int] = {reaction_type: 0 for reaction_type in REACTION_FILTERS if reaction_type != "all"}
    for chapter in manifest.get("chapters", []):
        result_path = _chapter_result_path(book_id, chapter, root=root)
        if not result_path.exists():
            continue
        payload = _load_json(result_path)
        for reaction_type, count in payload.get("ui_summary", {}).get("reaction_counts", {}).items():
            api_reaction_type = to_api_reaction_type(str(reaction_type))
            reaction_counts[api_reaction_type] = reaction_counts.get(api_reaction_type, 0) + int(count)

    completed_cards = []
    for item in recent_activity:
        if str(item.get("type", "")) != "chapter_completed":
            continue
        chapter_id = int(item.get("chapter_id", 0) or 0)
        chapter_ref = str(item.get("chapter_ref", ""))
        title = chapter_ref
        for chapter in manifest.get("chapters", []):
            if int(chapter.get("id", 0)) == chapter_id:
                title = str(chapter.get("title", chapter_ref))
                break
        completed_cards.append(
            {
                "chapter_id": chapter_id,
                "chapter_ref": chapter_ref,
                "title": title,
                "visible_reaction_count": int(item.get("visible_reaction_count", 0) or 0),
                "featured_reactions": list(item.get("featured_reactions", [])),
                "result_url": canonical_chapter_path(to_api_book_id(book_id), chapter_id),
            }
        )
        if len(completed_cards) >= 3:
            break

    recent_reactions = []
    for card in completed_cards:
        recent_reactions.extend(card.get("featured_reactions", []))
        if len(recent_reactions) >= 5:
            break
    recent_visible_activity = [
        item
        for item in recent_activity
        if str(item.get("visibility", "default") or "default") != "hidden"
    ]

    status, stage_label, stage_label_key, stage_label_params = _analysis_status(
        run_state, current_chapter_id=current_chapter_id
    )
    completed_chapters = int(run_state.get("completed_chapters", 0) or 0)
    total_chapters = int(run_state.get("total_chapters", len(chapters)) or len(chapters))
    current_phase_step = str(run_state.get("current_phase_step", "") or "") or None
    resume_available = bool(run_state.get("resume_available", False))
    last_checkpoint_at = str(run_state.get("last_checkpoint_at", "") or "") or None
    if status == "parsing_structure" and parse_state:
        completed_chapters = int(parse_state.get("completed_chapters", completed_chapters) or completed_chapters)
        total_chapters = int(parse_state.get("total_chapters", total_chapters) or total_chapters)
        current_phase_step = str(parse_state.get("current_step", "") or "") or current_phase_step
        resume_available = bool(parse_state.get("resume_available", resume_available))
        last_checkpoint_at = str(parse_state.get("last_checkpoint_at", "") or "") or last_checkpoint_at
        if current_chapter_id is None:
            current_chapter_id = int(parse_state.get("current_chapter_id", 0) or 0) or None
        if not run_state.get("current_chapter_ref") and parse_state.get("current_chapter_ref"):
            run_state["current_chapter_ref"] = parse_state.get("current_chapter_ref")
    status, stage_label, stage_label_key, stage_label_params = _analysis_status(
        run_state, current_chapter_id=current_chapter_id
    )
    current_phase_step_key, current_phase_step_params = _analysis_phase_step_message(current_phase_step)
    progress_percent = round((completed_chapters / total_chapters) * 100, 2) if total_chapters > 0 else None

    return {
        "book_id": to_api_book_id(book_id),
        "title": str(manifest.get("book", "")),
        "author": str(manifest.get("author", "")),
        "status": status,
        "stage_label": stage_label,
        "stage_label_key": stage_label_key,
        "stage_label_params": stage_label_params,
        "progress_percent": progress_percent,
        "completed_chapters": completed_chapters,
        "total_chapters": total_chapters,
        "current_chapter_id": current_chapter_id,
        "current_chapter_ref": run_state.get("current_chapter_ref"),
        "eta_seconds": run_state.get("eta_seconds"),
        "current_phase_step": current_phase_step,
        "current_phase_step_key": current_phase_step_key,
        "current_phase_step_params": current_phase_step_params,
        "resume_available": resume_available,
        "last_checkpoint_at": last_checkpoint_at,
        "structure_ready": bool(chapters),
        "chapters": chapters,
        "current_state_panel": {
            "current_chapter_id": current_chapter_id,
            "current_chapter_ref": run_state.get("current_chapter_ref"),
            "current_section_ref": run_state.get("current_segment_ref") if status == "deep_reading" else None,
            "current_phase_step": current_phase_step,
            "current_phase_step_key": current_phase_step_key,
            "current_phase_step_params": current_phase_step_params,
            "recent_reactions": recent_reactions[:5],
            "reaction_counts": reaction_counts,
            "search_active": any(str(item.get("search_query", "") or "").strip() for item in recent_activity[:5]),
            "last_activity_message": recent_visible_activity[0].get("message") if recent_visible_activity else None,
        },
        "recent_completed_chapters": completed_cards,
        "last_error": (
            {
                "error_id": "run-state-error",
                "code": "ANALYSIS_FAILED",
                "message": str(run_state.get("error", "")),
                "status": 409,
                "retryable": bool(resume_available),
                "details": None,
            }
            if status in {"error", "paused"}
            else None
        ),
    }


def get_book_featured_reactions(book_id: str, root: Path | None = None, *, limit: int = 3) -> list[dict]:
    """Collect a small set of featured reactions across the analyzed book."""
    manifest = _manifest(book_id, root)
    previews: list[dict] = []
    for chapter in sorted(manifest.get("chapters", []), key=lambda item: int(item.get("id", 0))):
        chapter_id = int(chapter.get("id", 0))
        try:
            payload = get_chapter_result(book_id, chapter_id, root=root)
        except FileNotFoundError:
            continue
        for item in payload.get("featured_reactions", []):
            if not isinstance(item, dict):
                continue
            previews.append(
                _featured_reaction_preview(
                    book_id,
                    chapter_id,
                    str(chapter.get("reference", "")),
                    item,
                )
            )
            if len(previews) >= limit:
                return previews
    return previews


def find_book_id_by_source(upload_path: Path, root: Path | None = None) -> str | None:
    """Find the output book id associated with one uploaded source file."""
    target = str(upload_path.resolve())
    target_digest: str | None = None
    for manifest_path in _manifest_paths(root):
        manifest = _load_json(manifest_path)
        source_file = str(manifest.get("source_file", "")).strip()
        if not source_file:
            source_file = ""
        if source_file:
            try:
                if str(Path(source_file).resolve()) == target:
                    manifest_parent = manifest_path.parent.parent if manifest_path.parent.name == "public" else manifest_path.parent
                    return str(manifest.get("book_id", manifest_parent.name))
            except FileNotFoundError:
                pass
        if target_digest is None:
            target_digest = _file_sha1(upload_path)
        if target_digest is None:
            return None
        manifest_parent = manifest_path.parent.parent if manifest_path.parent.name == "public" else manifest_path.parent
        book_id = str(manifest.get("book_id", manifest_parent.name))
        asset_path = source_asset_path(book_id, root)
        if _file_sha1(asset_path) == target_digest:
            return book_id
    return None

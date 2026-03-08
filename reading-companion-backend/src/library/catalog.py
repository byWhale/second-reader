"""Catalog helpers that aggregate output artifacts into product-facing views."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

from .pagination import paginate_items
from .user_marks import list_book_marks, list_marks
from src.api.contract import (
    REACTION_FILTERS,
    canonical_analysis_path,
    canonical_book_path,
    canonical_chapter_path,
    to_api_book_id,
    to_api_reaction_id,
    to_api_reaction_type,
)
from src.iterator_reader.storage import (
    activity_file,
    book_manifest_file,
    existing_cover_asset_file,
    run_state_file,
)


HIGH_SIGNAL_TYPES = {"highlight", "curious", "discern", "retrospect"}


def output_root(root: Path | None = None) -> Path:
    """Return the root output directory."""
    return (root or Path.cwd()) / "output"


def _load_json(path: Path) -> dict:
    """Load one JSON object if it exists."""
    return json.loads(path.read_text(encoding="utf-8"))


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


def _book_dir(book_id: str, root: Path | None = None) -> Path:
    """Resolve one output directory by book id."""
    return output_root(root) / book_id


def _manifest(book_id: str, root: Path | None = None) -> dict:
    """Load one persisted manifest."""
    path = book_manifest_file(_book_dir(book_id, root))
    if not path.exists():
        raise FileNotFoundError(book_id)
    return _load_json(path)


def _run_state(book_id: str, root: Path | None = None) -> dict | None:
    """Load one persisted run state if present."""
    path = run_state_file(_book_dir(book_id, root))
    return _load_json(path) if path.exists() else None


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
        if stage == "completed":
            return "completed"
        if stage in {"ready", "deep_reading"}:
            return "analyzing"
    if any(str(chapter.get("status", "")).strip() == "done" for chapter in manifest.get("chapters", [])):
        return "completed"
    return "not_started"


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


def _book_card(book_id: str, manifest: dict, run_state: dict | None, root: Path | None = None) -> dict:
    """Build one bookshelf card payload."""
    status = _display_status(manifest, run_state)
    mark_count = len(list_book_marks(book_id, root=root))
    api_book_id = to_api_book_id(book_id)
    open_target = canonical_book_path(api_book_id) if status in {"completed", "error"} else canonical_analysis_path(api_book_id)
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
        "open_target": open_target,
    }


def _chapter_status_for_analysis(chapter: dict, current_chapter_id: int | None, run_state: dict | None) -> str:
    """Return the chapter status used by progress/result pages."""
    chapter_id = int(chapter.get("id", 0))
    raw_status = str(chapter.get("status", "")).strip()
    if run_state and str(run_state.get("stage", "")) == "error" and current_chapter_id == chapter_id:
        return "error"
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
    for manifest_path in output_root(root).glob("*/book_manifest.json"):
        manifest = _load_json(manifest_path)
        book_id = str(manifest.get("book_id", manifest_path.parent.name))
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
                "high_signal_reaction_count": int(chapter.get("high_signal_reaction_count", 0)),
                "result_ready": str(chapter.get("status", "")) == "done",
            }
        )

    reaction_counts = {reaction_type: 0 for reaction_type in REACTION_FILTERS if reaction_type != "all"}
    for chapter in manifest.get("chapters", []):
        result_path = _book_dir(book_id, root) / str(chapter.get("result_file", ""))
        if not result_path.exists():
            continue
        payload = _load_json(result_path)
        for reaction_type, count in payload.get("ui_summary", {}).get("reaction_counts", {}).items():
            api_reaction_type = to_api_reaction_type(str(reaction_type))
            reaction_counts[api_reaction_type] = reaction_counts.get(api_reaction_type, 0) + int(count)

    return {
        "book_id": api_book_id,
        "title": str(manifest.get("book", "")),
        "author": str(manifest.get("author", "")),
        "cover_image_url": _api_cover_url(book_id, manifest, root=root),
        "book_language": str(manifest.get("book_language", "")),
        "output_language": str(manifest.get("output_language", "")),
        "status": _display_status(manifest, run_state),
        "source_asset": _source_asset(book_id, manifest),
        "chapters": chapters,
        "my_mark_count": len(list_book_marks(book_id, root=root)),
        "reaction_counts": reaction_counts,
        "chapter_count": len(manifest.get("chapters", [])),
        "completed_chapter_count": _completed_chapter_count(manifest),
        "segment_count": sum(int(chapter.get("segment_count", 0)) for chapter in manifest.get("chapters", [])),
        "sample": False,
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
        "target_locator": item.get("target_locator"),
    }


def _decorate_activity_event(book_id: str, event: dict) -> dict:
    """Decorate one persisted activity event into the public API shape."""
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
        "high_signal_reaction_count": (
            int(event.get("high_signal_reaction_count", 0) or 0)
            if event.get("high_signal_reaction_count") is not None
            else None
        ),
        "result_url": canonical_chapter_path(to_api_book_id(book_id), chapter_id) if chapter_id is not None else None,
    }


def get_activity(book_id: str, root: Path | None = None) -> list[dict]:
    """Load the user-facing activity stream for one book."""
    return [_decorate_activity_event(book_id, item) for item in _load_jsonl(activity_file(_book_dir(book_id, root)))]


def get_activity_page(
    book_id: str,
    root: Path | None = None,
    *,
    limit: int = 20,
    cursor: str | None = None,
    event_type: str | None = None,
    chapter_id: int | None = None,
) -> dict:
    """Load paginated activity events for one book."""
    items = get_activity(book_id, root)
    if event_type:
        items = [item for item in items if str(item.get("type", "")) == event_type]
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
        result_path = _book_dir(book_id, root) / str(chapter.get("result_file", ""))
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
        "target_locator": reaction.get("target_locator"),
        "section_ref": str(section.get("segment_ref", "")),
        "section_summary": str(section.get("summary", "")),
        "mark_type": mark_index.get(reaction_id),
    }


def _filter_reactions(
    reactions: Iterable[dict],
    *,
    reaction_type: str | None = None,
    mark_type: str | None = None,
    high_signal_only: bool = False,
) -> list[dict]:
    """Apply filter options to a reaction card list."""
    filtered = list(reactions)
    if reaction_type and reaction_type != "all":
        normalized_type = to_api_reaction_type(reaction_type)
        filtered = [reaction for reaction in filtered if str(reaction.get("type", "")) == normalized_type]
    if mark_type:
        filtered = [reaction for reaction in filtered if str(reaction.get("mark_type", "") or "") == mark_type]
    if high_signal_only:
        filtered = [reaction for reaction in filtered if str(reaction.get("type", "")) in HIGH_SIGNAL_TYPES]
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

    sections = sorted(sections, key=lambda item: str(item.get("section_ref", "")))
    page_sections, page_info = paginate_items(sections, limit=limit, cursor=cursor)
    chapter_info = chapter_payload.get("chapter", {})
    chapter_reflection = []
    raw_reflection = chapter_payload.get("chapter_reflection", {}).get("chapter_insights", [])
    for item in raw_reflection if isinstance(raw_reflection, list) else []:
        text = str(item or "").strip()
        if text:
            chapter_reflection.append(text)

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
        "high_signal_reaction_count": int(chapter_payload.get("high_signal_reaction_count", 0)),
        "featured_reactions": [
            _featured_reaction_preview(book_id, chapter_id_value, chapter_ref, item)
            for item in chapter_payload.get("featured_reactions", [])
            if isinstance(item, dict)
        ],
        "chapter_reflection": chapter_reflection,
        "sections": page_sections,
        "sections_page_info": page_info,
        "available_filters": REACTION_FILTERS,
        "source_asset": _source_asset(book_id, manifest),
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
    high_signal_only: bool = False,
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
        high_signal_only=high_signal_only,
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
            "high_signal_only": high_signal_only,
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


def _analysis_status(run_state: dict, *, current_chapter_id: int | None) -> tuple[str, str]:
    """Map run_state into the public analysis page status vocabulary."""
    stage = str(run_state.get("stage", "ready"))
    if stage == "completed":
        return "completed", "全部完成"
    if stage == "error":
        return "error", "分析中断"
    if current_chapter_id is not None:
        return "deep_reading", f"正在分析 {run_state.get('current_chapter_ref', '')}"
    return "parsing_structure", "正在解析书籍结构"


def get_analysis_state(book_id: str, root: Path | None = None) -> dict:
    """Build the progress-page snapshot from persisted artifacts."""
    manifest = _manifest(book_id, root)
    run_state = _run_state(book_id, root)
    if not run_state:
        raise FileNotFoundError(book_id)

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

    reaction_counts: dict[str, int] = {}
    for chapter in manifest.get("chapters", []):
        result_path = _book_dir(book_id, root) / str(chapter.get("result_file", ""))
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
                "high_signal_reaction_count": int(item.get("high_signal_reaction_count", 0) or 0),
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

    status, stage_label = _analysis_status(run_state, current_chapter_id=current_chapter_id)
    completed_chapters = int(run_state.get("completed_chapters", 0) or 0)
    total_chapters = int(run_state.get("total_chapters", len(chapters)) or len(chapters))
    progress_percent = round((completed_chapters / total_chapters) * 100, 2) if total_chapters > 0 else None

    return {
        "book_id": to_api_book_id(book_id),
        "title": str(manifest.get("book", "")),
        "author": str(manifest.get("author", "")),
        "status": status,
        "stage_label": stage_label,
        "progress_percent": progress_percent,
        "completed_chapters": completed_chapters,
        "total_chapters": total_chapters,
        "current_chapter_id": current_chapter_id,
        "current_chapter_ref": run_state.get("current_chapter_ref"),
        "eta_seconds": run_state.get("eta_seconds"),
        "structure_ready": True,
        "chapters": chapters,
        "current_state_panel": {
            "current_chapter_id": current_chapter_id,
            "current_chapter_ref": run_state.get("current_chapter_ref"),
            "current_section_ref": run_state.get("current_segment_ref"),
            "recent_reactions": recent_reactions[:5],
            "reaction_counts": reaction_counts,
            "search_active": any(str(item.get("search_query", "") or "").strip() for item in recent_activity[:5]),
            "last_activity_message": recent_activity[0].get("message") if recent_activity else None,
        },
        "recent_completed_chapters": completed_cards,
        "last_error": (
            {
                "error_id": "run-state-error",
                "code": "ANALYSIS_FAILED",
                "message": str(run_state.get("error", "")),
                "status": 409,
                "retryable": False,
                "details": None,
            }
            if status == "error"
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
    for manifest_path in output_root(root).glob("*/book_manifest.json"):
        manifest = _load_json(manifest_path)
        source_file = str(manifest.get("source_file", "")).strip()
        if not source_file:
            continue
        try:
            if str(Path(source_file).resolve()) == target:
                return str(manifest.get("book_id", manifest_path.parent.name))
        except FileNotFoundError:
            continue
    return None

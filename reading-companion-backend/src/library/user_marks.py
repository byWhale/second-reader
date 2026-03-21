"""Single-user mark persistence on top of chapter_result artifacts."""

from __future__ import annotations

from pathlib import Path

from .pagination import paginate_items
from .storage import load_json, save_json, timestamp, user_marks_file
from src.api.contract import MARK_TYPES, to_internal_mark_type
from src.reading_core.runtime_contracts import UserMark, UserMarksState
from src.iterator_reader.storage import existing_book_manifest_file, existing_chapter_result_file, resolve_output_relative_file


def normalize_mark_type(mark_type: str) -> str:
    """Normalize mark values to the current public taxonomy."""
    return to_internal_mark_type(mark_type)


def load_marks_state(root: Path | None = None) -> UserMarksState:
    """Load the marks store or create an empty view."""
    path = user_marks_file(root)
    if not path.exists():
        return {"updated_at": timestamp(), "marks": {}}
    payload = load_json(path)
    raw_marks = dict(payload.get("marks", {}))
    normalized_marks: dict[str, UserMark] = {}
    for reaction_id, raw_mark in raw_marks.items():
        if not isinstance(raw_mark, dict):
            continue
        normalized = dict(raw_mark)
        normalized["mark_type"] = normalize_mark_type(str(raw_mark.get("mark_type", "")))
        normalized_marks[str(reaction_id)] = normalized  # type: ignore[assignment]
    return {
        "updated_at": str(payload.get("updated_at", timestamp())),
        "marks": normalized_marks,
    }


def save_marks_state(state: UserMarksState, root: Path | None = None) -> UserMarksState:
    """Persist the marks store."""
    state["updated_at"] = timestamp()
    save_json(user_marks_file(root), state)
    return state


def _sorted_marks(items: list[UserMark]) -> list[UserMark]:
    """Return marks in API order: updated_at desc, reaction_id asc."""
    ordered = sorted(items, key=lambda mark: str(mark.get("reaction_id", "")))
    ordered.sort(key=lambda mark: str(mark.get("updated_at", "")), reverse=True)
    return ordered


def list_marks(root: Path | None = None) -> list[UserMark]:
    """Return all persisted marks."""
    state = load_marks_state(root)
    marks = [mark for mark in state.get("marks", {}).values() if isinstance(mark, dict)]
    return _sorted_marks(marks)


def list_marks_page(
    *,
    root: Path | None = None,
    limit: int = 20,
    cursor: str | None = None,
    book_id: str | None = None,
    mark_type: str | None = None,
) -> dict:
    """Return paginated marks with optional filters."""
    items = list_marks(root)
    if book_id:
        items = [item for item in items if str(item.get("book_id", "")) == book_id]
    if mark_type:
        normalized_mark_type = normalize_mark_type(mark_type)
        items = [item for item in items if str(item.get("mark_type", "")) == normalized_mark_type]
    page_items, page_info = paginate_items(items, limit=limit, cursor=cursor)
    return {"items": page_items, "page_info": page_info}


def list_book_marks(book_id: str, root: Path | None = None) -> list[UserMark]:
    """Return persisted marks for one book."""
    return [mark for mark in list_marks(root) if str(mark.get("book_id", "")) == book_id]


def list_book_marks_grouped(book_id: str, root: Path | None = None) -> list[dict]:
    """Return one book's marks grouped by chapter."""
    grouped: dict[tuple[int, str], list[UserMark]] = {}
    for mark in list_book_marks(book_id, root):
        chapter_id = int(mark.get("chapter_id", 0) or 0)
        chapter_ref = str(mark.get("chapter_ref", ""))
        grouped.setdefault((chapter_id, chapter_ref), []).append(mark)

    groups = []
    for (chapter_id, chapter_ref), items in sorted(grouped.items(), key=lambda item: item[0][0]):
        groups.append({
            "chapter_id": chapter_id,
            "chapter_ref": chapter_ref,
            "items": items,
        })
    return groups


def find_reaction(book_id: str, reaction_id: str, root: Path | None = None) -> dict | None:
    """Find one reaction payload by id across all chapter results in a book."""
    book_dir = (root or Path.cwd()) / "output" / book_id
    if not book_dir.exists():
        return None
    manifest_path = existing_book_manifest_file(book_dir)
    if not manifest_path.exists():
        return None
    manifest = load_json(manifest_path)
    for chapter in manifest.get("chapters", []):
        path = resolve_output_relative_file(
            book_dir,
            str(chapter.get("result_file", "") or "").strip() or None,
            fallback=existing_chapter_result_file(book_dir, chapter),
        )
        if not path.exists():
            continue
        payload = load_json(path)
        chapter = payload.get("chapter", {})
        for section in payload.get("sections", []):
            if not isinstance(section, dict):
                continue
            for reaction in section.get("reactions", []):
                if not isinstance(reaction, dict):
                    continue
                if str(reaction.get("reaction_id", "")) != reaction_id:
                    continue
                return {
                    "book_id": book_id,
                    "book_title": str(payload.get("book_title", "")) or "",
                    "chapter_id": int(chapter.get("id", 0)),
                    "chapter_ref": str(chapter.get("reference", "")),
                    "segment_ref": str(section.get("segment_ref", "")),
                    "reaction": reaction,
                }
    return None


def put_mark(*, book_id: str, reaction_id: str, mark_type: str, root: Path | None = None) -> UserMark:
    """Create or update one persisted mark with idempotent semantics."""
    normalized_mark_type = normalize_mark_type(mark_type)
    if normalized_mark_type not in MARK_TYPES:
        raise ValueError(f"Unsupported mark_type: {mark_type}")

    reaction_record = find_reaction(book_id, reaction_id, root)
    if reaction_record is None:
        raise FileNotFoundError(reaction_id)

    state = load_marks_state(root)
    existing = state["marks"].get(reaction_id)
    now = timestamp()
    reaction = reaction_record["reaction"]
    created_at = str(existing.get("created_at", now)) if isinstance(existing, dict) else now

    book_title = str(reaction_record.get("book_title", "")) or ""
    if not book_title:
        from .catalog import get_book

        book_title = str(get_book(book_id, root)["manifest"].get("book", ""))

    payload: UserMark = {
        "reaction_id": reaction_id,
        "book_id": book_id,
        "book_title": book_title,
        "chapter_id": int(reaction_record["chapter_id"]),
        "chapter_ref": str(reaction_record["chapter_ref"]),
        "segment_ref": str(reaction_record["segment_ref"]),
        "reaction_type": reaction.get("type", "association"),
        "mark_type": normalized_mark_type,  # type: ignore[assignment]
        "reaction_excerpt": str(reaction.get("content", ""))[:180],
        "anchor_quote": str(reaction.get("anchor_quote", "")),
        "created_at": created_at,
        "updated_at": now,
    }
    state["marks"][reaction_id] = payload
    save_marks_state(state, root)
    return payload


def delete_mark(reaction_id: str, root: Path | None = None) -> bool:
    """Delete one persisted mark."""
    state = load_marks_state(root)
    removed = state["marks"].pop(reaction_id, None) is not None
    save_marks_state(state, root)
    return removed

"""Cursor pagination helpers for product-layer API responses."""

from __future__ import annotations

import base64
import json
from typing import TypeVar


T = TypeVar("T")


def encode_cursor(payload: dict[str, object]) -> str:
    """Encode an opaque cursor as URL-safe base64 JSON."""
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def decode_cursor(cursor: str | None) -> dict[str, object]:
    """Decode an opaque base64 JSON cursor."""
    if not cursor:
        return {}
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii"))
        payload = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ValueError("Invalid cursor") from exc
    if not isinstance(payload, dict):
        raise ValueError("Invalid cursor")
    return payload


def paginate_items(items: list[T], *, limit: int, cursor: str | None) -> tuple[list[T], dict[str, object]]:
    """Apply simple offset-based cursor pagination to a pre-sorted list."""
    payload = decode_cursor(cursor)
    offset = int(payload.get("offset", 0) or 0)
    offset = max(0, min(offset, len(items)))
    bounded_limit = max(1, min(100, int(limit)))
    page_items = items[offset : offset + bounded_limit]
    next_offset = offset + len(page_items)
    has_more = next_offset < len(items)
    next_cursor = encode_cursor({"offset": next_offset}) if has_more else None
    return page_items, {
        "limit": bounded_limit,
        "next_cursor": next_cursor,
        "has_more": has_more,
    }

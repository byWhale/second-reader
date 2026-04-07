"""Deterministic candidate-generation helpers for attentional_v2."""

from __future__ import annotations

import re

from src.reading_core import BookDocument, SentenceRecord

from .schemas import AnchorMemoryState


_CALLBACK_MARKERS = (
    "as noted earlier",
    "as mentioned earlier",
    "earlier example",
    "since that day",
    "from that day",
    "when they were young",
    "when he was young",
    "when she was young",
    "earlier",
    "previously",
    "once",
    "remember",
    "recall",
    "above",
    "當年",
    "当年",
    "自從",
    "自从",
    "那日",
    "前面",
    "前文",
    "上文",
    "之前",
    "此前",
    "前述",
    "先前",
    "從前",
    "从前",
    "記得",
    "记得",
    "昔日",
)


def _token_set(text: str) -> set[str]:
    """Return a coarse lexical set for cheap overlap ranking."""

    normalized = (text or "").lower()
    tokens = {
        token
        for token in re.findall(r"[a-z][a-z'-]{2,}", normalized)
        if token not in {"the", "and", "for", "with", "this", "that", "from", "into"}
    }
    for chunk in re.findall(r"[\u4e00-\u9fff]+", normalized):
        if len(chunk) < 2:
            continue
        if len(chunk) <= 4:
            tokens.add(chunk)
        for ngram_size in (2, 3):
            if len(chunk) < ngram_size:
                continue
            for start in range(len(chunk) - ngram_size + 1):
                tokens.add(chunk[start : start + ngram_size])
    return tokens


def _has_callback_marker(text: str) -> bool:
    """Return whether the current text explicitly points backward."""

    normalized = (text or "").lower()
    return any(marker in normalized for marker in _CALLBACK_MARKERS)


def _score_sentence(
    *,
    current_tokens: set[str],
    current_text: str,
    candidate_text: str,
    distance: int,
    local_window_size: int,
) -> tuple[int, float]:
    """Score one prior sentence for deterministic callback/bridge retrieval."""

    candidate_tokens = _token_set(candidate_text)
    overlap_tokens = current_tokens & candidate_tokens
    overlap = len(overlap_tokens)
    if overlap <= 0:
        return 0, 0.0

    score = float(overlap)
    score += min(
        2.0,
        sum(
            0.5
            for token in overlap_tokens
            if any("\u4e00" <= char <= "\u9fff" for char in token) or len(token) >= 6
        ),
    )
    if _has_callback_marker(current_text) and distance > local_window_size:
        score += 2.0
    return overlap, score


def flatten_sentence_inventory(document: BookDocument) -> list[dict[str, object]]:
    """Flatten the shared sentence inventory into source order."""

    flattened: list[dict[str, object]] = []
    for chapter in document.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        chapter_id = int(chapter.get("id", 0) or 0)
        chapter_title = str(chapter.get("title", "") or "")
        for sentence in chapter.get("sentences", []):
            if not isinstance(sentence, dict):
                continue
            flattened.append(
                {
                    **sentence,
                    "chapter_id": chapter_id,
                    "chapter_title": chapter_title,
                }
            )
    return flattened


def bounded_lookback_source_space(
    document: BookDocument,
    *,
    current_sentence_id: str,
    max_candidates: int = 12,
) -> list[dict[str, object]]:
    """Return a bounded source-space window ending immediately before the current sentence."""

    sentences = flatten_sentence_inventory(document)
    current_index = next(
        (index for index, sentence in enumerate(sentences) if str(sentence.get("sentence_id", "") or "") == current_sentence_id),
        None,
    )
    if current_index is None or current_index <= 0:
        return []
    lower_bound = max(0, current_index - max(1, int(max_candidates)))
    return sentences[lower_bound:current_index]


def generate_candidate_set(
    document: BookDocument,
    *,
    current_sentence_id: str,
    current_text: str,
    anchor_memory: AnchorMemoryState,
    max_memory_candidates: int = 3,
    max_lookback_candidates: int = 12,
) -> dict[str, object]:
    """Generate deterministic bridge candidates without performing bridge judgment."""

    current_tokens = _token_set(current_text)
    memory_candidates: list[dict[str, object]] = []
    for anchor in anchor_memory.get("anchor_records", []):
        if not isinstance(anchor, dict):
            continue
        overlap = len(current_tokens & _token_set(str(anchor.get("quote", "") or "")))
        if overlap <= 0:
            continue
        memory_candidates.append(
            {
                "candidate_kind": "anchor_memory",
                "anchor_id": str(anchor.get("anchor_id", "") or ""),
                "sentence_start_id": str(anchor.get("sentence_start_id", "") or ""),
                "sentence_end_id": str(anchor.get("sentence_end_id", "") or ""),
                "quote": str(anchor.get("quote", "") or ""),
                "overlap_score": overlap,
            }
        )
    memory_candidates.sort(key=lambda candidate: (-int(candidate.get("overlap_score", 0) or 0), str(candidate.get("anchor_id", "") or "")))
    memory_candidates = memory_candidates[: max(1, int(max_memory_candidates))]

    sentences = flatten_sentence_inventory(document)
    current_index = next(
        (index for index, sentence in enumerate(sentences) if str(sentence.get("sentence_id", "") or "") == current_sentence_id),
        None,
    )
    if current_index is None:
        return {
            "current_sentence_id": current_sentence_id,
            "memory_candidates": memory_candidates,
            "lookback_candidates": [],
        }

    lookback_window = bounded_lookback_source_space(
        document,
        current_sentence_id=current_sentence_id,
        max_candidates=max_lookback_candidates,
    )
    local_window_ids = {
        str(sentence.get("sentence_id", "") or "")
        for sentence in lookback_window
        if isinstance(sentence, dict)
    }
    lookback_candidates: list[dict[str, object]] = []
    callback_search_active = _has_callback_marker(current_text)
    for index, sentence in enumerate(sentences[:current_index]):
        sentence_id = str(sentence.get("sentence_id", "") or "")
        candidate_text = str(sentence.get("text", "") or "")
        overlap, score = _score_sentence(
            current_tokens=current_tokens,
            current_text=current_text,
            candidate_text=candidate_text,
            distance=current_index - index,
            local_window_size=max(1, int(max_lookback_candidates)),
        )
        if overlap <= 0:
            continue
        if sentence_id not in local_window_ids and not callback_search_active:
            continue
        is_callback_candidate = sentence_id not in local_window_ids
        lookback_candidates.append(
            {
                "candidate_kind": "source_callback" if is_callback_candidate else "source_lookback",
                "sentence_id": sentence_id,
                "chapter_id": int(sentence.get("chapter_id", 0) or 0),
                "chapter_title": str(sentence.get("chapter_title", "") or ""),
                "text": candidate_text,
                "text_role": str(sentence.get("text_role", "") or ""),
                "locator": dict(sentence.get("locator", {})) if isinstance(sentence.get("locator"), dict) else {},
                "overlap_score": score,
                "retrieval_channel": "source_callback" if is_callback_candidate else "source_lookback",
                "relation_type": "callback" if is_callback_candidate else "echo",
            }
        )

    lookback_candidates.sort(
        key=lambda candidate: (
            -float(candidate.get("overlap_score", 0) or 0.0),
            str(candidate.get("candidate_kind", "") or ""),
            str(candidate.get("sentence_id", "") or ""),
        )
    )

    return {
        "current_sentence_id": current_sentence_id,
        "memory_candidates": memory_candidates,
        "lookback_candidates": lookback_candidates[: max(1, int(max_lookback_candidates))],
    }

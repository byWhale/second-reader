"""Inner Reader agent for the Iterator-Reader architecture."""

from __future__ import annotations

import json
import random
import re
import time
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Callable, Literal, Optional, Union

from langgraph.graph import END, StateGraph

from src.prompts.templates import (
    READER_CHAPTER_REFLECT_PROMPT,
    READER_CHAPTER_REFLECT_SYSTEM,
    READER_CURIOSITY_FUSE_PROMPT,
    READER_CURIOSITY_FUSE_SYSTEM,
    READER_EXPRESS_PROMPT,
    READER_EXPRESS_SYSTEM,
    READER_REFLECT_PROMPT,
    READER_REFLECT_SYSTEM,
    READER_THINK_PROMPT,
    READER_THINK_SYSTEM,
)
from src.tools.search import classify_search_problem, search_web

from .language import language_name
from .llm_utils import ReaderLLMError, invoke_json
from .models import (
    ChapterMemorySummary,
    FindingStatus,
    MemoryFinding,
    MemoryThread,
    PromptBudget,
    PromptBudgetTier,
    ReactionPayload,
    ReaderBudget,
    ReasonCode,
    ReaderMemory,
    ReaderPromptNode,
    ReaderProgressEvent,
    ReaderState,
    QualityStatus,
    ReflectionPayload,
    RenderedSegment,
    SalienceLedgerItem,
    SalienceStatus,
    SearchHit,
    CurrentReadingProblemCode,
    SearchResultPayload,
    SkillPolicy,
    ThoughtPayload,
)


ProgressReporter = Optional[Callable[[Union[ReaderProgressEvent, str]], None]]

_REFLECT_MESSAGE_POOLS = {
    "pass": ["这段想法还行，继续", "嗯，保留 ✅", "可以，下一段"],
    "revise": ["等等，这个联想有点勉强...", "🔄 重新想想", "不太对，再来"],
    "skip": ["算了，这段没什么好说的", "刚才在凑数，删掉", "安静更好"],
}
_LAST_REFLECT_MESSAGE: dict[str, str] = {}
_REASON_CODES: set[str] = {
    "LOW_SELECTIVITY",
    "WEAK_ASSOCIATION",
    "LOW_ATTRIBUTION_CONFIDENCE",
    "WEAK_TEXT_CONNECTION",
    "LOW_DEPTH",
    "NO_CONCRETE_DISCERN",
    "NO_EXPLICIT_CALLBACK",
    "OVER_EXTENDED",
    "INSUFFICIENT_EVIDENCE",
    "OTHER",
}
_QUALITY_STATUSES: set[str] = {"strong", "acceptable", "weak", "skipped"}
_PROMPT_MEMORY_CAPS: dict[ReaderPromptNode, int] = {
    "think": 900,
    "express": 1400,
    "reflect": 700,
}
_RECENT_SEGMENT_FLOW_LIMIT = 8
_RECENT_HIGHLIGHT_LIMIT = 8
_MODEL_CONTEXT_WINDOW_ESTIMATE = 16_000
_PROMPT_RESERVED_OUTPUT_TOKENS = 4_096
_PROMPT_RESERVED_SYSTEM_TOKENS = 1_400
_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'_-]*")
_CURRENT_READING_PROBLEM_CODES: set[str] = {
    "llm_timeout",
    "llm_quota",
    "llm_auth",
    "search_timeout",
    "search_quota",
    "search_auth",
    "network_blocked",
}

def _timestamp() -> str:
    """Return a stable UTC timestamp for memory updates."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _estimate_tokens(text: str) -> int:
    """Cheap local token estimate without provider round-trips."""
    return max(1, len(str(text or "")) // 4)


def _lexical_terms(text: str) -> set[str]:
    """Return lightweight lexical terms for cheap relevance scoring."""
    return {
        token.lower()
        for token in _TOKEN_RE.findall(str(text or ""))
        if len(token) >= 3
    }


def _memory_flow_line(item: dict[str, object]) -> str:
    """Render one recent segment-flow item."""
    segment_ref = _clean_text(item.get("segment_ref", ""))
    summary = _clean_text(item.get("summary", ""))
    if segment_ref and summary:
        return f"{segment_ref}: {summary}"
    return summary or segment_ref


def _legacy_memory_view(memory: ReaderMemory) -> ReaderMemory:
    """Backfill the old list-based memory view from the richer schema."""
    flow_lines = [_memory_flow_line(item) for item in memory.get("recent_segment_flow", [])]
    findings = [
        _clean_text(item.get("text", ""))
        for item in memory.get("findings", [])
        if _clean_text(item.get("status", "")) != "superseded" and _clean_text(item.get("text", ""))
    ]
    open_threads = [
        _clean_text(item.get("text", ""))
        for item in memory.get("threads", [])
        if _clean_text(item.get("status", "")) == "open" and _clean_text(item.get("text", ""))
    ]
    memory["prior_segment_summaries"] = flow_lines[-_RECENT_SEGMENT_FLOW_LIMIT:]
    memory["notable_findings"] = findings[-8:]
    memory["open_threads"] = open_threads[-8:]
    memory["highlighted_quotes"] = list(memory.get("recent_highlighted_quotes", []))[-_RECENT_HIGHLIGHT_LIMIT:]
    return memory


def coerce_reader_memory(memory: ReaderMemory | dict[str, object] | None) -> ReaderMemory:
    """Normalize legacy and new reader memory payloads into one stable schema."""
    payload = dict(memory or {})
    normalized: ReaderMemory = {
        "recent_segment_flow": [],
        "recent_highlighted_quotes": [],
        "findings": [],
        "threads": [],
        "chapter_memory_summaries": [],
        "book_arc_summary": _clean_text(payload.get("book_arc_summary", "")),
        "salience_ledger": [],
    }

    for item in payload.get("recent_segment_flow", []):
        if not isinstance(item, dict):
            continue
        segment_ref = _clean_text(item.get("segment_ref", ""))
        summary = _clean_text(item.get("summary", ""))
        if not segment_ref and not summary:
            continue
        normalized["recent_segment_flow"].append(
            {
                "segment_ref": segment_ref,
                "chapter_ref": _clean_text(item.get("chapter_ref", "")),
                "summary": summary,
                "touched_at": _clean_text(item.get("touched_at", "")) or _timestamp(),
            }
        )
    if not normalized["recent_segment_flow"]:
        for legacy in payload.get("prior_segment_summaries", []):
            text = _clean_text(legacy)
            if not text:
                continue
            if ":" in text:
                segment_ref, summary = text.split(":", 1)
                normalized["recent_segment_flow"].append(
                    {
                        "segment_ref": _clean_text(segment_ref),
                        "summary": _clean_text(summary),
                        "chapter_ref": "",
                        "touched_at": _timestamp(),
                    }
                )
            else:
                normalized["recent_segment_flow"].append(
                    {
                        "segment_ref": "",
                        "summary": text,
                        "chapter_ref": "",
                        "touched_at": _timestamp(),
                    }
                )
    normalized["recent_segment_flow"] = normalized["recent_segment_flow"][-_RECENT_SEGMENT_FLOW_LIMIT:]

    for item in payload.get("findings", []):
        if not isinstance(item, dict):
            continue
        text = _clean_text(item.get("text", ""))
        if not text:
            continue
        status = _clean_text(item.get("status", ""))
        normalized["findings"].append(
            {
                "text": text,
                "status": status if status in {"provisional", "durable", "superseded"} else "durable",
                "anchor_quote": _clean_text(item.get("anchor_quote", "")),
                "chapter_ref": _clean_text(item.get("chapter_ref", "")),
                "segment_ref": _clean_text(item.get("segment_ref", "")),
                "touched_at": _clean_text(item.get("touched_at", "")) or _timestamp(),
            }
        )
    if not normalized["findings"]:
        for legacy in payload.get("notable_findings", []):
            text = _clean_text(legacy)
            if not text:
                continue
            normalized["findings"].append(
                {
                    "text": text,
                    "status": "durable",
                    "anchor_quote": "",
                    "chapter_ref": "",
                    "segment_ref": "",
                    "touched_at": _timestamp(),
                }
            )

    for item in payload.get("threads", []):
        if not isinstance(item, dict):
            continue
        text = _clean_text(item.get("text", ""))
        if not text:
            continue
        status = _clean_text(item.get("status", ""))
        normalized["threads"].append(
            {
                "text": text,
                "status": status if status in {"open", "resolved", "parked"} else "open",
                "chapter_ref": _clean_text(item.get("chapter_ref", "")),
                "segment_ref": _clean_text(item.get("segment_ref", "")),
                "resolution": _clean_text(item.get("resolution", "")),
                "touched_at": _clean_text(item.get("touched_at", "")) or _timestamp(),
            }
        )
    if not normalized["threads"]:
        for legacy in payload.get("open_threads", []):
            text = _clean_text(legacy)
            if not text:
                continue
            normalized["threads"].append(
                {
                    "text": text,
                    "status": "open",
                    "chapter_ref": "",
                    "segment_ref": "",
                    "resolution": "",
                    "touched_at": _timestamp(),
                }
            )

    quotes = payload.get("recent_highlighted_quotes", payload.get("highlighted_quotes", []))
    normalized["recent_highlighted_quotes"] = [
        _clean_text(item)
        for item in quotes
        if _clean_text(item)
    ][-_RECENT_HIGHLIGHT_LIMIT:]

    for item in payload.get("chapter_memory_summaries", []):
        if not isinstance(item, dict):
            continue
        summary = _clean_text(item.get("summary", ""))
        if not summary:
            continue
        role = _clean_text(item.get("primary_role", "")) or "body"
        normalized["chapter_memory_summaries"].append(
            {
                "chapter_ref": _clean_text(item.get("chapter_ref", "")),
                "chapter_title": _clean_text(item.get("chapter_title", "")),
                "primary_role": role if role in {"front_matter", "body", "back_matter"} else "body",
                "summary": summary,
                "touched_at": _clean_text(item.get("touched_at", "")) or _timestamp(),
            }
        )

    for item in payload.get("salience_ledger", []):
        if not isinstance(item, dict):
            continue
        name = _clean_text(item.get("name", ""))
        if not name:
            continue
        kind = _clean_text(item.get("kind", "")) or "concept"
        status = _clean_text(item.get("status", "")) or "active"
        normalized["salience_ledger"].append(
            {
                "kind": kind if kind in {"concept", "character", "institution", "place", "motif"} else "concept",
                "name": name,
                "working_note": _clean_text(item.get("working_note", "")),
                "introduced_at": _clean_text(item.get("introduced_at", "")) or _timestamp(),
                "last_touched_at": _clean_text(item.get("last_touched_at", "")) or _timestamp(),
                "status": status if status in {"emerging", "active", "stable", "contested", "resolved"} else "active",
            }
        )

    return _legacy_memory_view(normalized)


def _memory_text(memory: ReaderMemory) -> str:
    """Render running reading memory into compact text."""
    return _memory_text_for_language(memory, "zh")


def _role_context_note(primary_role: str, role_tags: list[str], output_language: str) -> str:
    """Render one factual note about the likely function of this chapter."""
    tags = set(role_tags)
    if "overview" in tags or "roadmap" in tags:
        return (
            "这部分更像在预告后文结构与主题，其中一些判断可能只是框架性线索。"
            if output_language != "en"
            else "This part appears to preview later structure and themes; some claims may still be provisional framing cues."
        )
    if "preface" in tags or "prologue" in tags or primary_role == "front_matter":
        return (
            "这部分更像在定调或搭建阅读入口，不一定承载完整论证。"
            if output_language != "en"
            else "This part seems to set the tone or entry frame, rather than carrying the full argument by itself."
        )
    if primary_role == "back_matter":
        return (
            "这部分更像补充、收束或旁证材料。"
            if output_language != "en"
            else "This part seems more supplementary, closing, or evidentiary than a core argument section."
        )
    return (
        "这部分看起来属于书的主体展开。"
        if output_language != "en"
        else "This part appears to belong to the main body of the book."
    )


def _format_book_context(state: ReaderState) -> str:
    """Render book-level position context for prompts."""
    title = _clean_text(state.get("book_title", ""))
    author = _clean_text(state.get("author", ""))
    chapter_index = int(state.get("chapter_index", 0) or 0)
    total = int(state.get("total_chapters", 0) or 0)
    nearby = [item for item in state.get("nearby_outline", []) if _clean_text(item)]
    lines = [
        f"书名：{title or '（未知）'}",
        f"作者：{author or '（未知）'}",
        f"当前位置：第 {chapter_index}/{max(total, 1)} 章",
    ]
    if nearby:
        lines.append("附近目录：")
        lines.extend(f"- {item}" for item in nearby)
    return "\n".join(lines)


def _format_current_part_context(state: ReaderState) -> str:
    """Render current chapter/section role context for prompts."""
    output_language = state.get("output_language", "en")
    tags = [tag for tag in state.get("role_tags", []) if _clean_text(tag)]
    section_heading = _clean_text(state.get("section_heading", ""))
    lines = [
        f"当前章节：{_clean_text(state.get('chapter_ref', '')) or _clean_text(state.get('chapter_title', ''))}",
        f"章节标题：{_clean_text(state.get('chapter_title', ''))}",
        f"章节角色：{_clean_text(state.get('primary_role', 'body'))}",
        f"角色标签：{', '.join(tags) if tags else '无'}",
        f"角色置信度：{_clean_text(state.get('role_confidence', 'low'))}",
    ]
    if section_heading:
        lines.append(f"当前小节标题：{section_heading}")
    lines.append(_role_context_note(_clean_text(state.get("primary_role", "body")), tags, output_language))
    return "\n".join(lines)


def _relevance_score(text: str, query_terms: set[str], *, recency_rank: int, status_boost: int = 0) -> int:
    """Compute a cheap lexical + recency relevance score."""
    if not text:
        return status_boost - recency_rank
    overlap = len(_lexical_terms(text) & query_terms)
    return overlap * 10 + status_boost + max(0, 6 - recency_rank)


def _compute_prompt_budget(state: ReaderState, node: ReaderPromptNode) -> PromptBudget:
    """Estimate a lightweight node-local prompt memory budget."""
    estimated_segment_tokens = _estimate_tokens(state.get("segment_text", "")[:6000])
    cap = _PROMPT_MEMORY_CAPS[node]
    multiplier = 1.0
    tier: PromptBudgetTier = "ample"
    if estimated_segment_tokens > 900:
        multiplier = 0.6
        tier = "tight"
    elif estimated_segment_tokens > 500:
        multiplier = 0.8
        tier = "normal"
    available_context = max(
        0,
        _MODEL_CONTEXT_WINDOW_ESTIMATE
        - _PROMPT_RESERVED_OUTPUT_TOKENS
        - _PROMPT_RESERVED_SYSTEM_TOKENS
        - estimated_segment_tokens,
    )
    return {
        "node": node,
        "model_context_window_estimate": _MODEL_CONTEXT_WINDOW_ESTIMATE,
        "reserved_output_tokens": _PROMPT_RESERVED_OUTPUT_TOKENS,
        "reserved_system_tokens": _PROMPT_RESERVED_SYSTEM_TOKENS,
        "estimated_segment_tokens": estimated_segment_tokens,
        "node_memory_budget_tokens": min(int(cap * multiplier), available_context),
        "available_context_tokens": available_context,
        "budget_tier": tier,
    }


def _assemble_memory_packet(state: ReaderState, node: ReaderPromptNode) -> tuple[str, PromptBudget]:
    """Assemble a budget-aware memory packet for one prompt node."""
    memory = coerce_reader_memory(state.get("memory", {}))
    budget = _compute_prompt_budget(state, node)
    token_limit = max(240, int(budget.get("node_memory_budget_tokens", 0) or 0))
    output_language = state.get("output_language", "en")
    query_terms = _lexical_terms(
        " ".join(
            [
                state.get("segment_text", ""),
                state.get("segment_summary", ""),
                state.get("section_heading", ""),
                state.get("chapter_title", ""),
            ]
        )
    )

    recent_flow = list(reversed(memory.get("recent_segment_flow", [])))
    active_threads = [
        item
        for item in memory.get("threads", [])
        if _clean_text(item.get("status", "")) == "open"
    ]
    findings = [
        item
        for item in memory.get("findings", [])
        if _clean_text(item.get("status", "")) in {"provisional", "durable"}
    ]
    ledger = [
        item
        for item in memory.get("salience_ledger", [])
        if _clean_text(item.get("status", "")) != "resolved"
    ]
    chapter_summaries = list(reversed(memory.get("chapter_memory_summaries", [])))

    active_threads = sorted(
        active_threads,
        key=lambda item: _relevance_score(
            _clean_text(item.get("text", "")),
            query_terms,
            recency_rank=0,
            status_boost=12,
        ),
        reverse=True,
    )
    findings = sorted(
        findings,
        key=lambda item: _relevance_score(
            _clean_text(item.get("text", "")),
            query_terms,
            recency_rank=0,
            status_boost=18 if _clean_text(item.get("status", "")) == "durable" else 10,
        ),
        reverse=True,
    )
    ledger = sorted(
        ledger,
        key=lambda item: _relevance_score(
            f"{_clean_text(item.get('name', ''))} {_clean_text(item.get('working_note', ''))}",
            query_terms,
            recency_rank=0,
            status_boost=10 if _clean_text(item.get("status", "")) in {"active", "stable"} else 6,
        ),
        reverse=True,
    )
    chapter_limit = 2 if budget.get("budget_tier") == "tight" else 4
    if budget.get("budget_tier") == "ample":
        chapter_limit = 8

    sections: list[tuple[str, list[str]]] = []
    book_arc_summary = _clean_text(memory.get("book_arc_summary", ""))
    if book_arc_summary:
        sections.append(("全书脉络", [book_arc_summary]))
    if active_threads:
        sections.append(("活跃问题", [f"- {item.get('text', '')}" for item in active_threads[:5]]))
    if findings:
        sections.append(
            (
                "相关发现",
                [
                    f"- [{_clean_text(item.get('status', 'durable'))}] {_clean_text(item.get('text', ''))}"
                    for item in findings[:6]
                ],
            )
        )
    if ledger:
        sections.append(
            (
                "关键概念/角色账本",
                [
                    f"- {_clean_text(item.get('name', ''))} ({_clean_text(item.get('kind', 'concept'))}): {_clean_text(item.get('working_note', ''))}"
                    for item in ledger[:6]
                ],
            )
        )
    if recent_flow:
        sections.append(("最近阅读流", [f"- {_memory_flow_line(item)}" for item in recent_flow[:6]]))
    if chapter_summaries:
        sections.append(
            (
                "最近章节记忆",
                [
                    f"- {_clean_text(item.get('chapter_ref', '')) or _clean_text(item.get('chapter_title', ''))}: {_clean_text(item.get('summary', ''))}"
                    for item in chapter_summaries[:chapter_limit]
                ],
            )
        )

    assembled: list[str] = []
    used_tokens = 0
    for title, lines in sections:
        section_text = f"{title}：\n" + "\n".join(line for line in lines if _clean_text(line))
        section_tokens = _estimate_tokens(section_text)
        if used_tokens and used_tokens + section_tokens > token_limit:
            trimmed_lines: list[str] = []
            for line in lines:
                line_tokens = _estimate_tokens(f"{title}：\n" + "\n".join(trimmed_lines + [line]))
                if used_tokens + line_tokens > token_limit:
                    break
                trimmed_lines.append(line)
            if not trimmed_lines:
                continue
            section_text = f"{title}：\n" + "\n".join(trimmed_lines)
            section_tokens = _estimate_tokens(section_text)
        if used_tokens + section_tokens > token_limit and assembled:
            break
        assembled.append(section_text)
        used_tokens += section_tokens

    if not assembled:
        fallback = "No reading memory yet." if output_language == "en" else "暂无阅读记忆。"
        return fallback, budget
    return "\n\n".join(assembled), budget


def _memory_text_for_language(memory: ReaderMemory, output_language: str) -> str:
    """Render memory in the language used by older prompt call sites."""
    normalized = coerce_reader_memory(memory)
    if output_language == "en":
        lines: list[str] = []
        if normalized.get("prior_segment_summaries"):
            lines.append("Prior segment summaries:")
            lines.extend(f"- {item}" for item in normalized.get("prior_segment_summaries", [])[-5:])
        if normalized.get("highlighted_quotes"):
            lines.append("Earlier highlighted quotes:")
            lines.extend(f"- {item}" for item in normalized.get("highlighted_quotes", [])[-5:])
        if normalized.get("notable_findings"):
            lines.append("Earlier findings:")
            lines.extend(f"- {item}" for item in normalized.get("notable_findings", [])[-5:])
        if normalized.get("open_threads"):
            lines.append("Open threads:")
            lines.extend(f"- {item}" for item in normalized.get("open_threads", [])[-3:])
        return "\n".join(lines) if lines else "No reading memory yet."
    lines = []
    if normalized.get("prior_segment_summaries"):
        lines.append("此前段落要点：")
        lines.extend(f"- {item}" for item in normalized.get("prior_segment_summaries", [])[-5:])
    if normalized.get("highlighted_quotes"):
        lines.append("此前划过的原句：")
        lines.extend(f"- {item}" for item in normalized.get("highlighted_quotes", [])[-5:])
    if normalized.get("notable_findings"):
        lines.append("此前已出现的发现：")
        lines.extend(f"- {item}" for item in normalized.get("notable_findings", [])[-5:])
    if normalized.get("open_threads"):
        lines.append("仍在悬而未决的问题：")
        lines.extend(f"- {item}" for item in normalized.get("open_threads", [])[-3:])
    return "\n".join(lines) if lines else "暂无阅读记忆。"


def _default_user_intent(output_language: str) -> str:
    """Fallback user intent label for prompts."""
    return "Not specified" if output_language == "en" else "未指定"


def _default_revision_instruction(output_language: str) -> str:
    """Fallback revision note for prompts."""
    return "None" if output_language == "en" else "无"


def _default_anchor(segment_text: str) -> str:
    """Fallback excerpt when the model does not provide one."""
    lines = [line.strip() for line in segment_text.splitlines() if line.strip()]
    text = lines[0] if lines else segment_text.strip()
    text = re.sub(r"\s+", " ", text)
    return text[:180]


def _default_thought_reason(output_language: str) -> str:
    """Fallback explanation when Think returns nothing useful."""
    if output_language == "en":
        return "Nothing in this segment feels worth expanding."
    return "这段暂时没有形成值得展开的反应。"


def _default_skip_summary(output_language: str) -> str:
    """Fallback reflection summary for a skipped segment."""
    if output_language == "en":
        return "No reaction here feels worth keeping."
    return "这段没有形成值得保留的反应，跳过更合适。"


def _default_revision_overflow_summary(output_language: str) -> str:
    """Fallback summary when revision attempts are exhausted."""
    if output_language == "en":
        return "Even after multiple revisions, this segment still feels forced."
    return "多轮修改后仍显得勉强，这段宁可跳过。"


def _default_reflection_summary(output_language: str) -> str:
    """Fallback summary when Reflect returns malformed output."""
    if output_language == "en":
        return "The self-review did not return a usable verdict."
    return "未给出有效审稿结论。"


def _default_timeout_summary(output_language: str) -> str:
    """Fallback summary when a segment is truncated by budget safeguards."""
    if output_language == "en":
        return "This section keeps a concise best-effort draft to preserve the main insight."
    return "该语义段已保留精简但可用的草稿，核心洞见不丢失。"


def _default_skill_policy() -> SkillPolicy:
    """Fallback skill policy when state is partially missing."""
    return {
        "profile": "balanced",
        "enabled_reactions": ["highlight", "association", "curious", "discern", "retrospect", "silent"],
        "max_reactions_per_segment": 8,
        "max_curious_reactions": 2,
    }


def _default_budget() -> ReaderBudget:
    """Fallback budget state when not explicitly provided."""
    return {
        "search_queries_remaining_in_chapter": 12,
        "search_queries_remaining_in_segment": 2,
        "segment_timeout_seconds": 120,
        "segment_timed_out": False,
        "early_stop": False,
        "token_budget_ratio": 1.5,
        "slice_target_tokens": 420,
        "slice_max_tokens": 700,
        "slice_max_subsegments": 4,
        "work_units_remaining": 0,
    }


def _clean_text(value: object) -> str:
    """Normalize model text content for markdown output."""
    text = str(value or "").strip()
    text = text.replace("\\n", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _normalize_matching_text(text: str) -> str:
    """Normalize text for cheap source-quote matching."""
    normalized = _clean_text(text)
    normalized = normalized.replace("“", '"').replace("”", '"')
    normalized = normalized.replace("’", "'").replace("‘", "'")
    normalized = normalized.replace("—", "-").replace("–", "-")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.lower().strip()


def _partial_match_score(needle: str, haystack: str) -> float:
    """Return a cheap fuzzy containment score for quote recovery."""
    if not needle or not haystack:
        return 0.0
    if needle in haystack or haystack in needle:
        return 100.0

    shorter, longer = (needle, haystack) if len(needle) <= len(haystack) else (haystack, needle)
    window = min(len(longer), max(len(shorter) + 24, int(len(shorter) * 1.4)))
    step = max(1, len(shorter) // 6)
    last_start = max(0, len(longer) - window)
    best = 0.0

    for start in range(0, last_start + 1, step):
        chunk = longer[start : start + window]
        best = max(best, SequenceMatcher(None, shorter, chunk).ratio() * 100.0)
        if best >= 98.0:
            return best

    if last_start and last_start % step:
        chunk = longer[last_start : last_start + window]
        best = max(best, SequenceMatcher(None, shorter, chunk).ratio() * 100.0)

    return best


def _match_source_sentence(segment_text: str, excerpt: str) -> str:
    """Find the most likely source sentence for a model-selected excerpt."""
    normalized_excerpt = _normalize_matching_text(excerpt)
    if not normalized_excerpt:
        return ""

    direct_matches: list[str] = []
    best_sentence = ""
    best_score = 0.0
    for sentence in _split_sentences(segment_text):
        normalized_sentence = _normalize_matching_text(sentence)
        if not normalized_sentence:
            continue
        if normalized_excerpt in normalized_sentence:
            direct_matches.append(sentence.strip())
            continue
        score = _partial_match_score(normalized_excerpt, normalized_sentence)
        if score > best_score:
            best_score = score
            best_sentence = sentence.strip()

    if direct_matches:
        return min(direct_matches, key=lambda item: len(_normalize_matching_text(item)))
    if best_score >= 88.0:
        return best_sentence
    return ""


def _split_strong_clauses(sentence: str) -> list[dict[str, object]]:
    """Split one sentence on strong punctuation boundaries only."""
    if not sentence.strip():
        return []

    clauses: list[dict[str, object]] = []
    separator_pattern = re.compile(r"\s*(?::|;|--|—|–)\s*")
    start = 0
    boundary_before = ""

    for match in separator_pattern.finditer(sentence):
        raw_clause = sentence[start : match.start()]
        trimmed = raw_clause.strip()
        if trimmed:
            leading_ws = len(raw_clause) - len(raw_clause.lstrip())
            trailing_ws = len(raw_clause) - len(raw_clause.rstrip())
            clause_start = start + leading_ws
            clause_end = match.start() - trailing_ws
            clauses.append(
                {
                    "text": sentence[clause_start:clause_end],
                    "start": clause_start,
                    "end": clause_end,
                    "boundary_before": boundary_before,
                }
            )
        boundary_before = match.group(0)
        start = match.end()

    raw_clause = sentence[start:]
    trimmed = raw_clause.strip()
    if trimmed:
        leading_ws = len(raw_clause) - len(raw_clause.lstrip())
        trailing_ws = len(raw_clause) - len(raw_clause.rstrip())
        clause_start = start + leading_ws
        clause_end = len(sentence) - trailing_ws
        clauses.append(
            {
                "text": sentence[clause_start:clause_end],
                "start": clause_start,
                "end": clause_end,
                "boundary_before": boundary_before,
            }
        )

    if clauses:
        return clauses
    stripped = sentence.strip()
    start_index = sentence.find(stripped) if stripped else 0
    return [{"text": stripped, "start": start_index, "end": start_index + len(stripped), "boundary_before": ""}]


def _looks_self_contained_clause(text: str, boundary_before: str = "") -> bool:
    """Heuristic guardrail for avoiding obviously dangling quote fragments."""
    cleaned = _clean_text(text).strip(" \"'“”‘’")
    if not cleaned:
        return False
    if boundary_before and any(marker in boundary_before for marker in [":", ";", "--", "—", "–"]):
        return False

    lowered = _normalize_matching_text(cleaned)
    subordinate_prefixes = (
        "because ",
        "if ",
        "when ",
        "while ",
        "although ",
        "though ",
        "unless ",
        "since ",
        "that ",
        "which ",
        "who ",
        "whom ",
        "whose ",
        "whereas ",
        "if only ",
        "because of ",
        "因为",
        "如果",
        "虽然",
        "当",
        "除非",
        "由于",
    )
    if lowered.startswith(subordinate_prefixes):
        return False
    return True


def _best_matching_clause_index(clauses: list[dict[str, object]], excerpt: str) -> int:
    """Pick the clause that most likely contains the model-selected quote."""
    normalized_excerpt = _normalize_matching_text(excerpt)
    if not normalized_excerpt:
        return -1

    direct_hits = [
        index
        for index, clause in enumerate(clauses)
        if normalized_excerpt in _normalize_matching_text(str(clause.get("text", "")))
    ]
    if direct_hits:
        return min(
            direct_hits,
            key=lambda idx: len(_normalize_matching_text(str(clauses[idx].get("text", "")))),
        )

    best_index = -1
    best_score = 0.0
    for index, clause in enumerate(clauses):
        score = _partial_match_score(normalized_excerpt, _normalize_matching_text(str(clause.get("text", ""))))
        if score > best_score:
            best_score = score
            best_index = index
    return best_index if best_score >= 88.0 else -1


def _normalize_source_clause(segment_text: str, excerpt: object) -> str:
    """Map a raw quote fragment to the smallest source-grounded readable clause."""
    raw_excerpt = _clean_text(excerpt)
    if not raw_excerpt or not _clean_text(segment_text):
        return raw_excerpt

    sentence = _match_source_sentence(segment_text, raw_excerpt)
    if not sentence:
        return raw_excerpt
    if _normalize_matching_text(sentence) == _normalize_matching_text(raw_excerpt):
        return _clean_text(sentence)

    clauses = _split_strong_clauses(sentence)
    if len(clauses) <= 1:
        return _clean_text(sentence)

    clause_index = _best_matching_clause_index(clauses, raw_excerpt)
    if clause_index < 0:
        return raw_excerpt

    start_index = int(clauses[clause_index]["start"])
    end_index = int(clauses[clause_index]["end"])
    candidate = sentence[start_index:end_index].strip()

    if _looks_self_contained_clause(candidate, str(clauses[clause_index].get("boundary_before", ""))):
        return candidate

    if clause_index > 0:
        start_index = int(clauses[clause_index - 1]["start"])
        candidate = sentence[start_index:end_index].strip()
        if _looks_self_contained_clause(candidate):
            return candidate

    if clause_index + 1 < len(clauses):
        end_index = int(clauses[clause_index + 1]["end"])
        candidate = sentence[start_index:end_index].strip()
        if _looks_self_contained_clause(candidate):
            return candidate

    return _clean_text(sentence)


def _segment_ref(state: ReaderState | dict[str, object]) -> str:
    """Return user-facing segment ref with internal id fallback."""
    visible = _clean_text(state.get("segment_ref", ""))
    if visible:
        return visible
    return _clean_text(state.get("segment_id", ""))


def _normalize_list(value: object, limit: int | None) -> list[str]:
    """Normalize arbitrary values into a bounded string list."""
    if not isinstance(value, list):
        return []
    items = []
    for item in value:
        if not isinstance(item, str):
            continue
        text = item.strip()
        if text:
            items.append(text)
    if limit is None:
        return items
    return items[:limit]


def _infer_reason_codes(issues: list[str], reflection: dict) -> list[ReasonCode]:
    """Infer structured reason codes when the model does not provide them."""
    codes: list[ReasonCode] = []
    if reflection.get("selectivity", 3) <= 2:
        codes.append("LOW_SELECTIVITY")
    if reflection.get("association_quality", 3) <= 2:
        codes.append("WEAK_ASSOCIATION")
    if reflection.get("attribution_reasonableness", 3) <= 2:
        codes.append("LOW_ATTRIBUTION_CONFIDENCE")
    if reflection.get("text_connection", 3) <= 2:
        codes.append("WEAK_TEXT_CONNECTION")
    if reflection.get("depth", 3) <= 2:
        codes.append("LOW_DEPTH")

    keyword_mapping = [
        ("推敲", "NO_CONCRETE_DISCERN"),
        ("discern", "NO_CONCRETE_DISCERN"),
        ("回溯", "NO_EXPLICIT_CALLBACK"),
        ("retrospect", "NO_EXPLICIT_CALLBACK"),
        ("证据", "INSUFFICIENT_EVIDENCE"),
        ("来源", "INSUFFICIENT_EVIDENCE"),
        ("拖沓", "OVER_EXTENDED"),
        ("冗长", "OVER_EXTENDED"),
    ]
    for issue in issues:
        lowered = issue.lower()
        for keyword, code in keyword_mapping:
            if keyword in issue or keyword in lowered:
                typed = code  # type: ignore[assignment]
                if typed not in codes:
                    codes.append(typed)

    if not codes:
        return ["OTHER"]
    return codes[:3]


def _normalize_reason_codes(value: object, issues: list[str], reflection: dict) -> list[ReasonCode]:
    """Normalize reason codes into the supported controlled vocabulary."""
    normalized: list[ReasonCode] = []
    if isinstance(value, list):
        for item in value:
            code = str(item or "").strip().upper()
            if code in _REASON_CODES and code not in normalized:
                normalized.append(code)  # type: ignore[list-item]
    if normalized:
        return normalized[:3]
    return _infer_reason_codes(issues, reflection)


def _normalize_target_indexes(value: object, reactions: list[ReactionPayload]) -> list[int]:
    """Normalize revision target indexes to valid active reaction indexes."""
    max_index = max(-1, len(reactions) - 1)
    if max_index < 0:
        return []
    normalized: list[int] = []
    if isinstance(value, list):
        for item in value:
            try:
                index = int(item)
            except (TypeError, ValueError):
                continue
            if 0 <= index <= max_index and index not in normalized:
                normalized.append(index)
    if normalized:
        return normalized
    return [0]


def _safe_score(value: object, default: int = 3) -> int:
    """Normalize reflective scores into a stable 1-5 range."""
    try:
        score = int(value)
    except (TypeError, ValueError):
        score = default
    return max(1, min(5, score))


def _normalize_thought(
    payload: object,
    segment_text: str,
    output_language: str,
) -> ThoughtPayload:
    """Normalize Think node payload."""
    if not isinstance(payload, dict):
        payload = {}
    return {
        "should_express": bool(payload.get("should_express", False)),
        "selected_excerpt": _normalize_source_clause(
            segment_text,
            payload.get("selected_excerpt", "") or _default_anchor(segment_text),
        ),
        "reason": _clean_text(payload.get("reason", "") or _default_thought_reason(output_language)),
        "connections": _normalize_list(payload.get("connections"), 2),
        "curiosities": _normalize_list(payload.get("curiosities"), 2),
        "curiosity_potential": _safe_score(payload.get("curiosity_potential", 3)),
    }


def _normalize_reaction_type(value: object) -> str:
    """Map arbitrary model output to the supported reaction types."""
    normalized = _clean_text(value).lower().replace("-", "_")
    aliases = {
        "highlight": "highlight",
        "underline": "highlight",
        "association": "association",
        "annotation": "association",
        "deep_dive": "association",
        "curious": "curious",
        "question": "curious",
        "search": "curious",
        "discern": "discern",
        "critique": "discern",
        "challenge": "discern",
        "retrospect": "retrospect",
        "connect_back": "retrospect",
        "callback": "retrospect",
        "recall": "retrospect",
        "backlink": "retrospect",
        "silent": "silent",
        "skip": "silent",
    }
    return aliases.get(normalized, "association")


def _normalize_search_query(value: object) -> str:
    """Keep curiosity queries compact enough for cheap web search."""
    query = _clean_text(value)
    query = re.sub(r"\s+", " ", query)
    return query[:200].strip()


def _apply_skill_policy(
    reactions: list[ReactionPayload],
    skill_policy: SkillPolicy,
    budget: ReaderBudget,
) -> list[ReactionPayload]:
    """Filter and cap reactions under skill and budget constraints."""
    enabled = set(skill_policy.get("enabled_reactions", []))
    max_reactions = max(1, int(skill_policy.get("max_reactions_per_segment", 8)))
    max_curious = max(0, int(skill_policy.get("max_curious_reactions", 2)))
    max_curious = min(max_curious, int(budget.get("search_queries_remaining_in_segment", 0)))

    filtered: list[ReactionPayload] = []
    curious_count = 0
    for reaction in reactions:
        reaction_type = reaction.get("type", "association")
        if reaction_type not in enabled:
            continue
        if reaction_type == "curious":
            if curious_count >= max_curious:
                continue
            curious_count += 1
        filtered.append(reaction)
        if len(filtered) >= max_reactions:
            break

    if filtered:
        return filtered

    if "silent" in enabled:
        return [{"type": "silent", "content": "技能策略选择安静读过。", "search_results": []}]
    return [{"type": "association", "content": "简要保留一个观察。", "search_results": []}]


def _legacy_reactions(payload: dict) -> list[dict]:
    """Best-effort fallback for old Express payloads."""
    if str(payload.get("decision", "")).strip().lower() == "skip":
        return [{"type": "silent", "content": _clean_text(payload.get("reflection", ""))}]

    reactions: list[dict] = []
    reflection = _clean_text(payload.get("reflection", ""))
    if reflection:
        reactions.append(
            {
                "type": "association",
                "anchor_quote": _clean_text(payload.get("anchor_quote", "")),
                "content": reflection,
            }
        )
    open_question = _clean_text(payload.get("open_question", ""))
    if open_question:
        reactions.append(
            {
                "type": "curious",
                "content": open_question,
                "search_query": open_question,
            }
        )
    return reactions


def _normalize_reactions(payload: object, state: ReaderState) -> list[ReactionPayload]:
    """Normalize Express node payload into mixed reactions."""
    thought = state.get("thought") or _normalize_thought(
        {},
        state.get("segment_text", ""),
        state.get("output_language", "en"),
    )
    if not isinstance(payload, dict):
        payload = {}

    raw_reactions = payload.get("reactions")
    if not isinstance(raw_reactions, list):
        raw_reactions = _legacy_reactions(payload)

    reactions: list[ReactionPayload] = []
    segment_text = state.get("segment_text", "")
    for item in raw_reactions:
        if not isinstance(item, dict):
            continue
        reaction_type = _normalize_reaction_type(item.get("type"))
        content = _clean_text(
            item.get("content", "")
            or item.get("text", "")
            or item.get("reaction", "")
            or item.get("note", "")
        )
        anchor_quote = _normalize_source_clause(
            segment_text,
            item.get("anchor_quote", "") or item.get("excerpt", ""),
        )
        search_query = _normalize_search_query(item.get("search_query", ""))

        if reaction_type == "curious" and not search_query:
            search_query = _normalize_search_query(content)

        if reaction_type == "silent":
            silent_content = content or thought.get("reason", "")
            if silent_content:
                reactions.append(
                    {
                        "type": "silent",
                        "content": silent_content,
                        "search_results": [],
                    }
                )
            continue

        if not content and not anchor_quote and not search_query:
            continue

        reaction: ReactionPayload = {
            "type": reaction_type,  # type: ignore[typeddict-item]
            "search_results": [],
        }
        if content:
            reaction["content"] = content
        if anchor_quote:
            reaction["anchor_quote"] = anchor_quote
        if search_query:
            reaction["search_query"] = search_query
        reactions.append(reaction)

    if not reactions:
        if thought.get("should_express"):
            fallback_reaction: ReactionPayload = {
                "type": "highlight",
                "content": thought.get("reason", ""),
                "search_results": [],
            }
            if thought.get("selected_excerpt"):
                fallback_reaction["anchor_quote"] = thought.get("selected_excerpt", "")
            reactions.append(fallback_reaction)
        else:
            reactions.append(
                {
                    "type": "silent",
                    "content": thought.get("reason", ""),
                    "search_results": [],
                }
            )

    if any(reaction.get("type") != "silent" for reaction in reactions):
        for reaction in reactions:
            if reaction.get("type") == "silent":
                continue
            if not reaction.get("anchor_quote") and thought.get("selected_excerpt"):
                reaction["anchor_quote"] = thought.get("selected_excerpt", "")
                break

    filtered_reactions: list[ReactionPayload] = []
    for reaction in reactions:
        if reaction.get("type") == "silent":
            filtered_reactions.append(reaction)
            continue
        if str(reaction.get("anchor_quote", "") or "").strip():
            filtered_reactions.append(reaction)

    if not filtered_reactions:
        filtered_reactions.append(
            {
                "type": "silent",
                "content": thought.get("reason", ""),
                "search_results": [],
            }
        )

    skill_policy = state.get("skill_policy") or _default_skill_policy()
    budget = state.get("budget") or _default_budget()
    return _apply_skill_policy(filtered_reactions, skill_policy, budget)


def _active_reactions(reactions: list[ReactionPayload]) -> list[ReactionPayload]:
    """Return only reactions that should be reviewed and rendered."""
    return [reaction for reaction in reactions if reaction.get("type") != "silent"]


def _estimate_tokens(text: str) -> int:
    """Estimate token count without requiring tokenizer dependencies."""
    normalized = re.sub(r"\s+", " ", text or "").strip()
    if not normalized:
        return 0
    cjk_chars = len(re.findall(r"[\u4e00-\u9fff]", normalized))
    latin_words = len(re.findall(r"[A-Za-z0-9_]+", normalized))
    punctuation = len(re.findall(r"[.,;:!?。！？；：]", normalized))
    return max(1, int(cjk_chars * 1.15 + latin_words * 1.3 + punctuation * 0.2))


def _split_sentences(text: str) -> list[str]:
    """Split text into sentence-like chunks while preserving readability."""
    raw = re.split(r"(?<=[。！？!?\.])\s+", (text or "").strip())
    sentences = [item.strip() for item in raw if item and item.strip()]
    if len(sentences) <= 1:
        sentences = [line.strip() for line in (text or "").splitlines() if line.strip()]
    return sentences or [(text or "").strip()]


def _segment_density_signal(text: str) -> float:
    """Compute a rough density score used to trigger dynamic slicing."""
    sentences = _split_sentences(text)
    if not sentences:
        return 0.0

    long_sentence_count = sum(1 for sentence in sentences if _estimate_tokens(sentence) >= 80)
    lower = text.lower()
    transition_hits = sum(
        lower.count(marker)
        for marker in [
            "however",
            "therefore",
            "on the other hand",
            "in contrast",
            "but",
            "because",
            "if ",
            "then",
        ]
    )
    definition_hits = sum(
        lower.count(marker)
        for marker in ["defined as", "means", "refers to", "in other words"]
    )
    numeric_hits = len(re.findall(r"\d", text))
    return long_sentence_count * 1.2 + transition_hits * 0.3 + definition_hits * 0.6 + min(2.0, numeric_hits / 16.0)


def _chunk_sentences(
    sentences: list[str],
    target_tokens: int,
    max_subsegments: int,
) -> list[str]:
    """Pack sentences into bounded sub-segments near the target size."""
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0
    target = max(120, int(target_tokens))
    max_parts = max(1, int(max_subsegments))

    for sentence in sentences:
        sentence_tokens = _estimate_tokens(sentence)
        if current and current_tokens + sentence_tokens > target:
            chunks.append(" ".join(current).strip())
            current = [sentence]
            current_tokens = sentence_tokens
        else:
            current.append(sentence)
            current_tokens += sentence_tokens

    if current:
        chunks.append(" ".join(current).strip())

    if len(chunks) <= max_parts:
        return chunks

    merged = chunks[: max_parts - 1]
    tail = " ".join(chunks[max_parts - 1 :]).strip()
    merged.append(tail)
    return merged


def _build_subsegments(state: ReaderState) -> list[dict[str, str]]:
    """Build optional dynamic sub-segments for one semantic unit."""
    text = state.get("segment_text", "")
    summary = state.get("segment_summary", "")
    budget = state.get("budget") or _default_budget()
    max_tokens = max(180, int(budget.get("slice_max_tokens", 700)))
    target_tokens = max(120, int(budget.get("slice_target_tokens", 420)))
    max_subsegments = max(1, int(budget.get("slice_max_subsegments", 4)))

    estimated_tokens = _estimate_tokens(text)
    density = _segment_density_signal(text)
    should_slice = estimated_tokens > max_tokens or density >= 3.2
    if not should_slice:
        return [{"summary": summary, "text": text}]

    chunks = _chunk_sentences(_split_sentences(text), target_tokens=target_tokens, max_subsegments=max_subsegments)
    if len(chunks) <= 1:
        return [{"summary": summary, "text": text}]

    subsegments: list[dict[str, str]] = []
    for index, chunk in enumerate(chunks, start=1):
        chunk_summary = _default_anchor(chunk)
        if len(chunk_summary) > 64:
            chunk_summary = chunk_summary[:61].rstrip() + "..."
        subsegments.append(
            {
                "summary": f"{summary} [{index}/{len(chunks)}]" if summary else f"Part {index}/{len(chunks)}",
                "text": chunk,
            }
        )
    return subsegments


def _initial_work_units(state: ReaderState) -> int:
    """Compute segment work units from text size and token budget ratio."""
    ratio = max(0.5, float((state.get("budget") or {}).get("token_budget_ratio", 1.5)))
    input_tokens = max(1, _estimate_tokens(state.get("segment_text", "")))
    units = int((input_tokens / 180.0) * ratio) + 2
    return max(3, min(30, units))


def _consume_work_units(budget: ReaderBudget, amount: int = 1) -> None:
    """Consume work units in-place."""
    remaining = max(0, int(budget.get("work_units_remaining", 0)) - max(1, int(amount)))
    budget["work_units_remaining"] = remaining


def _should_expand_curiosity(
    thought: ThoughtPayload | dict,
    budget: ReaderBudget,
) -> bool:
    """Decide whether a sub-segment deserves expensive curiosity expansion."""
    potential = _safe_score((thought or {}).get("curiosity_potential", 3))
    if potential < 3:
        return False
    if int(budget.get("work_units_remaining", 0)) <= 1:
        return False
    if int(budget.get("search_queries_remaining_in_chapter", 0)) <= 0:
        return False
    return True


def _minimal_budget_reflection(state: ReaderState) -> ReflectionPayload:
    """Create a lightweight reflection when budget is too tight for full review."""
    reactions = _active_reactions(state.get("reactions", []))
    if reactions:
        return {
            "verdict": "pass",
            "summary": _default_timeout_summary(state.get("output_language", "en")),
            "selectivity": 3,
            "association_quality": 3,
            "attribution_reasonableness": 3,
            "text_connection": 3,
            "depth": 3,
            "issues": ["kept concise due to budget guard"],
            "reason_codes": ["OVER_EXTENDED"],
            "target_reaction_indexes": [],
            "revision_instruction": "",
        }
    return {
        "verdict": "skip",
        "summary": _default_skip_summary(state.get("output_language", "en")),
        "selectivity": 4,
        "association_quality": 3,
        "attribution_reasonableness": 3,
        "text_connection": 3,
        "depth": 3,
        "issues": ["no retained reaction"],
        "reason_codes": ["LOW_SELECTIVITY"],
        "target_reaction_indexes": [],
        "revision_instruction": "",
    }


def _merge_reactions(
    reactions: list[ReactionPayload],
    max_items: int,
) -> list[ReactionPayload]:
    """Deduplicate merged reactions while preserving first-seen order."""
    merged: list[ReactionPayload] = []
    seen: set[tuple[str, str, str, str]] = set()
    limit = max(1, int(max_items))
    for reaction in reactions:
        reaction_type = str(reaction.get("type", "association"))
        anchor = _clean_text(reaction.get("anchor_quote", ""))
        content = _clean_text(reaction.get("content", ""))
        query = _clean_text(reaction.get("search_query", ""))
        key = (reaction_type, anchor, content, query)
        if key in seen:
            continue
        seen.add(key)
        merged.append(reaction)
        if len(merged) >= limit:
            break
    return merged


def _normalize_quality_status(value: object, fallback: QualityStatus = "acceptable") -> QualityStatus:
    """Normalize one quality status label."""
    normalized = _clean_text(value).lower()
    if normalized in _QUALITY_STATUSES:
        return normalized  # type: ignore[return-value]
    return fallback


def _skip_reason_from_codes(reason_codes: list[ReasonCode] | list[str]) -> str:
    """Project structured reason codes into compact skip reasons."""
    for item in reason_codes:
        code = _clean_text(item).upper()
        if code in _REASON_CODES and code != "OVER_EXTENDED":
            return code.lower()
    return "other"


def _segment_quality_from_rendered(segment: RenderedSegment) -> QualityStatus:
    """Infer quality tier from segment verdict and reflection diagnostics."""
    verdict = str(segment.get("verdict", "skip")).strip().lower()
    reactions = _active_reactions(segment.get("reactions", []))
    if verdict == "skip" or not reactions:
        return "skipped"

    explicit = _normalize_quality_status(segment.get("quality_status", ""))
    if explicit in {"strong", "acceptable", "weak"}:
        return explicit

    low_signal_codes = {
        "LOW_SELECTIVITY",
        "WEAK_ASSOCIATION",
        "LOW_ATTRIBUTION_CONFIDENCE",
        "WEAK_TEXT_CONNECTION",
        "LOW_DEPTH",
        "INSUFFICIENT_EVIDENCE",
    }
    codes = {
        _clean_text(code).upper()
        for code in segment.get("reflection_reason_codes", [])
    }
    if codes & low_signal_codes:
        return "weak"
    if len(reactions) >= 4:
        return "strong"
    return "acceptable"


def _quality_reason_label(status: QualityStatus, output_language: str) -> str:
    """Render one short reason for chapter-level quality tags."""
    if output_language == "en":
        mapping = {
            "strong": "clear insight with grounded evidence",
            "acceptable": "useful reading signal with room to deepen",
            "weak": "interesting but still shallow or under-supported",
            "skipped": "no stable incremental value after review",
        }
        return mapping[status]
    mapping = {
        "strong": "有清晰洞见且锚点扎实",
        "acceptable": "有阅读增量，但还可深化",
        "weak": "有想法但支撑偏弱或偏浅",
        "skipped": "回看后仍无稳定增量",
    }
    return mapping[status]


def _compact_segments_for_chapter_reflection(
    segments: list[RenderedSegment],
) -> list[dict[str, object]]:
    """Build compact per-segment payload for chapter-level reflection."""
    compact: list[dict[str, object]] = []
    for segment in segments:
        reactions: list[dict[str, str]] = []
        for reaction in segment.get("reactions", [])[:6]:
            reactions.append(
                {
                    "type": _clean_text(reaction.get("type", "association"))[:32],
                    "anchor_quote": _clean_text(reaction.get("anchor_quote", "")),
                    "content": _clean_text(reaction.get("content", ""))[:320],
                }
            )
        compact.append(
            {
                "segment_id": _clean_text(segment.get("segment_id", "")),
                "segment_ref": _clean_text(segment.get("segment_ref", "") or segment.get("segment_id", "")),
                "summary": _clean_text(segment.get("summary", ""))[:220],
                "verdict": _clean_text(segment.get("verdict", "skip")),
                "quality_status": _segment_quality_from_rendered(segment),
                "reflection_summary": _clean_text(segment.get("reflection_summary", ""))[:220],
                "reason_codes": list(segment.get("reflection_reason_codes", []))[:3],
                "reactions": reactions,
            }
        )
    return compact


def _normalize_chapter_reflection_payload(
    payload: object,
    segments: list[RenderedSegment],
    output_language: str,
) -> dict[str, object]:
    """Normalize chapter-level reflection payload into a stable structure."""
    segment_refs_by_id = {
        _clean_text(segment.get("segment_id", "")): _clean_text(
            segment.get("segment_ref", "") or segment.get("segment_id", "")
        )
        for segment in segments
        if _clean_text(segment.get("segment_id", ""))
    }
    segment_ids = set(segment_refs_by_id.keys())
    segment_id_by_ref = {
        segment_ref: segment_id
        for segment_id, segment_ref in segment_refs_by_id.items()
        if segment_ref
    }
    if not isinstance(payload, dict):
        payload = {}

    def _resolve_segment_id(item: dict[str, object]) -> str:
        raw_segment_id = _clean_text(item.get("segment_id", ""))
        raw_segment_ref = _clean_text(item.get("segment_ref", ""))
        if raw_segment_id in segment_ids:
            return raw_segment_id
        if raw_segment_ref in segment_id_by_ref:
            return segment_id_by_ref[raw_segment_ref]
        if raw_segment_id in segment_id_by_ref:
            return segment_id_by_ref[raw_segment_id]
        return ""

    segment_repairs: list[dict[str, str]] = []
    seen_segment_repair: set[tuple[str, str]] = set()
    for item in payload.get("segment_repairs", []):
        if not isinstance(item, dict):
            continue
        segment_id = _resolve_segment_id(item)
        note = _clean_text(item.get("note", ""))
        if not segment_id or segment_id not in segment_ids or not note:
            continue
        key = (segment_id, note)
        if key in seen_segment_repair:
            continue
        seen_segment_repair.add(key)
        segment_repairs.append({"segment_id": segment_id, "note": note[:320]})

    reaction_repairs: list[dict[str, object]] = []
    seen_reaction_repair: set[tuple[str, int, str]] = set()
    for item in payload.get("reaction_repairs", []):
        if not isinstance(item, dict):
            continue
        segment_id = _resolve_segment_id(item)
        note = _clean_text(item.get("note", ""))
        if not segment_id or segment_id not in segment_ids or not note:
            continue
        try:
            reaction_index = int(item.get("reaction_index", -1))
        except (TypeError, ValueError):
            reaction_index = -1
        if reaction_index < 0:
            continue
        key = (segment_id, reaction_index, note)
        if key in seen_reaction_repair:
            continue
        seen_reaction_repair.add(key)
        reaction_repairs.append(
            {
                "segment_id": segment_id,
                "reaction_index": reaction_index,
                "note": note[:240],
            }
        )

    chapter_insights = _normalize_list(payload.get("chapter_insights"), 6)
    if len(chapter_insights) < 2:
        chapter_insights = []

    provided_flags: dict[str, dict[str, str]] = {}
    for item in payload.get("segment_quality_flags", []):
        if not isinstance(item, dict):
            continue
        segment_id = _resolve_segment_id(item)
        if not segment_id or segment_id not in segment_ids:
            continue
        quality_status = _normalize_quality_status(
            item.get("quality_status", ""),
            fallback=_segment_quality_from_rendered(
                next(
                    (
                        segment
                        for segment in segments
                        if _clean_text(segment.get("segment_id", "")) == segment_id
                    ),
                    {
                        "segment_id": segment_id,
                        "summary": "",
                        "verdict": "skip",
                        "reactions": [],
                        "reflection_summary": "",
                        "reflection_reason_codes": [],
                    },
                ),
            ),
        )
        reason = _clean_text(item.get("reason", ""))[:180] or _quality_reason_label(
            quality_status,
            output_language,
        )
        provided_flags[segment_id] = {
            "segment_id": segment_id,
            "quality_status": quality_status,
            "reason": reason,
        }

    segment_quality_flags: list[dict[str, str]] = []
    for segment in segments:
        segment_id = _clean_text(segment.get("segment_id", ""))
        if not segment_id:
            continue
        if segment_id in provided_flags:
            segment_quality_flags.append(provided_flags[segment_id])
            continue
        inferred = _segment_quality_from_rendered(segment)
        segment_quality_flags.append(
            {
                "segment_id": segment_id,
                "quality_status": inferred,
                "reason": _quality_reason_label(inferred, output_language),
            }
        )

    return {
        "segment_repairs": segment_repairs,
        "reaction_repairs": reaction_repairs,
        "chapter_insights": chapter_insights,
        "segment_quality_flags": segment_quality_flags,
        "memory_actions": _normalize_memory_actions(payload if isinstance(payload, dict) else {}),
    }


def run_chapter_reflection(
    chapter_title: str,
    user_intent: str | None,
    segments: list[RenderedSegment],
    output_language: str,
    chapter_primary_role: str = "body",
    chapter_role_tags: list[str] | None = None,
) -> dict[str, object]:
    """Run one chapter-end reflection pass with scoped repair hints."""
    if not segments:
        return {
            "segment_repairs": [],
            "reaction_repairs": [],
            "chapter_insights": [],
            "segment_quality_flags": [],
            "memory_actions": {
                "finding_updates": [],
                "thread_updates": [],
                "salience_updates": [],
                "chapter_memory_summary": "",
                "book_arc_summary": "",
            },
        }

    # Keep tiny chapters local and deterministic; run LLM reflection on richer chapters.
    if len(segments) < 3:
        return _normalize_chapter_reflection_payload({}, segments, output_language)

    compact_segments = _compact_segments_for_chapter_reflection(segments)
    payload: object = {}
    try:
        payload = invoke_json(
            READER_CHAPTER_REFLECT_SYSTEM,
            READER_CHAPTER_REFLECT_PROMPT.format(
                chapter_title=chapter_title,
                chapter_primary_role=chapter_primary_role,
                chapter_role_tags=", ".join(chapter_role_tags or []) or "none",
                user_intent=user_intent or _default_user_intent(output_language),
                segments_json=json.dumps(compact_segments, ensure_ascii=False, indent=2),
                output_language_name=language_name(output_language),
            ),
            default={},
        )
    except Exception:
        payload = {}
    return _normalize_chapter_reflection_payload(payload, segments, output_language)


def apply_chapter_reflection_repairs(
    segments: list[RenderedSegment],
    chapter_reflection: dict[str, object] | None,
    output_language: str,
) -> list[RenderedSegment]:
    """Apply chapter reflection repairs back into segment/reaction outputs."""
    if not segments:
        return []

    repaired_segments: list[RenderedSegment] = []
    for segment in segments:
        copied = dict(segment)
        copied["reactions"] = [dict(reaction) for reaction in segment.get("reactions", [])]
        repaired_segments.append(copied)  # type: ignore[arg-type]

    if not chapter_reflection:
        chapter_reflection = {}
    reflection = _normalize_chapter_reflection_payload(chapter_reflection, repaired_segments, output_language)
    by_segment_id = {
        _clean_text(segment.get("segment_id", "")): segment
        for segment in repaired_segments
    }
    quality_flags = {
        _clean_text(item.get("segment_id", "")): item
        for item in reflection.get("segment_quality_flags", [])
        if isinstance(item, dict)
    }
    for segment in repaired_segments:
        segment_id = _clean_text(segment.get("segment_id", ""))
        quality_item = quality_flags.get(segment_id, {})
        inferred_status = _segment_quality_from_rendered(segment)
        quality_status = _normalize_quality_status(
            quality_item.get("quality_status", ""),
            fallback=inferred_status,
        )
        segment["quality_status"] = quality_status

        if quality_status == "skipped":
            reason = _clean_text(quality_item.get("reason", ""))
            if not reason:
                reason = _skip_reason_from_codes(segment.get("reflection_reason_codes", []))
            segment["skip_reason"] = reason
            if not _active_reactions(segment.get("reactions", [])):
                segment["verdict"] = "skip"
                segment["reactions"] = []
        else:
            segment.pop("skip_reason", None)
            if segment.get("verdict") == "skip" and _active_reactions(segment.get("reactions", [])):
                segment["verdict"] = "pass"

    return repaired_segments


def _normalize_search_hit(item: object) -> SearchHit | None:
    """Normalize one Tavily hit into a compact prompt-safe structure."""
    if not isinstance(item, dict):
        return None
    title = _clean_text(item.get("title", ""))
    url = _clean_text(item.get("url", ""))
    snippet = _clean_text(item.get("snippet", "") or item.get("content", ""))
    if len(snippet) > 240:
        snippet = snippet[:237].rstrip() + "..."

    score_value = item.get("score")
    try:
        score = float(score_value) if score_value is not None else None
    except (TypeError, ValueError):
        score = None

    if not title and not url:
        return None
    return {
        "title": title or url,
        "url": url,
        "snippet": snippet,
        "score": score,
    }


def _normalize_search_hits(results: object, max_results: int = 3) -> list[SearchHit]:
    """Normalize, deduplicate, and trim Tavily hits."""
    if not isinstance(results, list):
        return []

    normalized: list[SearchHit] = []
    seen_urls: set[str] = set()
    for item in results:
        hit = _normalize_search_hit(item)
        if not hit:
            continue
        url = hit.get("url", "")
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        normalized.append(hit)
        if len(normalized) >= max_results:
            break
    return normalized


def _invoke_curiosity_search(query: str, max_results: int = 3) -> object:
    """Run the Tavily tool behind a small local seam for testing."""
    return search_web.invoke({"query": query, "max_results": max_results})


def _normalize_reflection(payload: object, state: ReaderState) -> ReflectionPayload:
    """Normalize Reflect node payload."""
    output_language = state.get("output_language", "en")
    reactions = _active_reactions(state.get("reactions", []))
    if not reactions:
        return {
            "verdict": "skip",
            "summary": _default_skip_summary(output_language),
            "selectivity": 5,
            "association_quality": 3,
            "attribution_reasonableness": 4,
            "text_connection": 4,
            "depth": 3,
            "issues": [],
            "reason_codes": ["OTHER"],
            "target_reaction_indexes": [],
            "revision_instruction": "",
        }

    if not isinstance(payload, dict):
        payload = {}

    verdict = str(payload.get("verdict", "skip")).strip().lower()
    if verdict not in {"pass", "revise", "skip"}:
        verdict = "skip"

    reflection_scores = {
        "selectivity": _safe_score(payload.get("selectivity", 3)),
        "association_quality": _safe_score(payload.get("association_quality", 3)),
        "attribution_reasonableness": _safe_score(payload.get("attribution_reasonableness", 3)),
        "text_connection": _safe_score(payload.get("text_connection", 3)),
        "depth": _safe_score(payload.get("depth", 3)),
    }
    issues = _normalize_list(payload.get("issues"), 3)
    reason_codes = _normalize_reason_codes(payload.get("reason_codes"), issues, reflection_scores)
    target_reaction_indexes = _normalize_target_indexes(payload.get("target_reaction_indexes"), reactions)
    revision_instruction = _clean_text(payload.get("revision_instruction", ""))
    if verdict == "revise" and not revision_instruction:
        revision_instruction = issues[0] if issues else _default_reflection_summary(output_language)

    return {
        "verdict": verdict,  # type: ignore[return-value]
        "summary": _clean_text(payload.get("summary", "")) or _default_reflection_summary(output_language),
        "selectivity": reflection_scores["selectivity"],
        "association_quality": reflection_scores["association_quality"],
        "attribution_reasonableness": reflection_scores["attribution_reasonableness"],
        "text_connection": reflection_scores["text_connection"],
        "depth": reflection_scores["depth"],
        "issues": issues,
        "reason_codes": reason_codes,
        "target_reaction_indexes": target_reaction_indexes,
        "revision_instruction": revision_instruction,
    }


def create_reader_state(
    chapter_title: str,
    segment_id: str,
    segment_summary: str,
    segment_text: str,
    memory: ReaderMemory,
    output_language: str,
    user_intent: str | None = None,
    skill_policy: SkillPolicy | None = None,
    budget: ReaderBudget | None = None,
    max_revisions: int = 2,
    segment_ref: str | None = None,
    book_title: str = "",
    author: str = "",
    chapter_ref: str = "",
    chapter_index: int = 0,
    total_chapters: int = 0,
    primary_role: str = "body",
    role_tags: list[str] | None = None,
    role_confidence: str = "low",
    section_heading: str = "",
    nearby_outline: list[str] | None = None,
) -> ReaderState:
    """Create initial reader state for a semantic unit."""
    return {
        "book_title": book_title,
        "author": author,
        "chapter_title": chapter_title,
        "chapter_ref": chapter_ref,
        "chapter_index": chapter_index,
        "total_chapters": total_chapters,
        "primary_role": primary_role if primary_role in {"front_matter", "body", "back_matter"} else "body",
        "role_tags": list(role_tags or []),
        "role_confidence": role_confidence if role_confidence in {"low", "medium", "high"} else "low",
        "section_heading": _clean_text(section_heading),
        "nearby_outline": list(nearby_outline or []),
        "segment_id": segment_id,
        "segment_ref": _clean_text(segment_ref or segment_id),
        "segment_summary": segment_summary,
        "segment_text": segment_text,
        "user_intent": user_intent,
        "output_language": output_language,
        "memory": coerce_reader_memory(memory),
        "read_packet": "",
        "thought": None,
        "reactions": [],
        "search_results": [],
        "reflection": None,
        "revision_count": 0,
        "max_revisions": max_revisions,
        "revision_instruction": "",
        "skill_policy": skill_policy or _default_skill_policy(),
        "budget": budget or _default_budget(),
        "chapter_reflection": None,
        "segment_quality_flags": [],
    }


def read_node(state: ReaderState) -> ReaderState:
    """Prepare the segment and memory packet for the thinking stage."""
    memory_text, _budget = _assemble_memory_packet(state, "think")
    packet = "\n\n".join(
        [
            f"Book context:\n{_format_book_context(state)}",
            f"Current part of the book:\n{_format_current_part_context(state)}",
            f'语义单元：{_segment_ref(state)} / {state.get("segment_summary", "")}',
            f'原文：\n{state.get("segment_text", "")}',
            f"Reading memory:\n{memory_text}",
        ]
    )
    return {"read_packet": packet}


def think_node(state: ReaderState) -> ReaderState:
    """Decide whether this semantic unit deserves expression."""
    memory_text, _budget = _assemble_memory_packet(state, "think")
    payload = invoke_json(
        READER_THINK_SYSTEM,
        READER_THINK_PROMPT.format(
            book_context=_format_book_context(state),
            current_part_context=_format_current_part_context(state),
            chapter_title=state.get("chapter_title", ""),
            segment_ref=_segment_ref(state),
            segment_summary=state.get("segment_summary", ""),
            segment_text=state.get("segment_text", "")[:6000],
            memory_text=memory_text,
            user_intent=state.get("user_intent") or _default_user_intent(state.get("output_language", "en")),
            output_language_name=language_name(state.get("output_language", "en")),
        ),
        default={},
    )
    return {
        "thought": _normalize_thought(
            payload,
            state.get("segment_text", ""),
            state.get("output_language", "en"),
        )
    }


def express_node(state: ReaderState) -> ReaderState:
    """Produce mixed reactions for this semantic unit."""
    memory_text, _budget = _assemble_memory_packet(state, "express")
    payload = invoke_json(
        READER_EXPRESS_SYSTEM,
        READER_EXPRESS_PROMPT.format(
            book_context=_format_book_context(state),
            current_part_context=_format_current_part_context(state),
            chapter_title=state.get("chapter_title", ""),
            segment_ref=_segment_ref(state),
            segment_summary=state.get("segment_summary", ""),
            segment_text=state.get("segment_text", "")[:6000],
            thought_json=json.dumps(state.get("thought") or {}, ensure_ascii=False, indent=2),
            memory_text=memory_text,
            user_intent=state.get("user_intent") or _default_user_intent(state.get("output_language", "en")),
            revision_instruction=state.get("revision_instruction") or _default_revision_instruction(state.get("output_language", "en")),
            output_language_name=language_name(state.get("output_language", "en")),
        ),
        default={},
    )
    return {
        "reactions": _normalize_reactions(payload, state),
        "search_results": [],
        "reflection": None,
    }


def search_if_curious_node(state: ReaderState) -> ReaderState:
    """Call Tavily only for curiosity-driven reactions, up to two queries."""
    reactions = [dict(reaction) for reaction in state.get("reactions", [])]
    budget = dict(state.get("budget") or _default_budget())
    segment_quota = max(0, int(budget.get("search_queries_remaining_in_segment", 0)))
    chapter_quota = max(0, int(budget.get("search_queries_remaining_in_chapter", 0)))
    query_quota = min(segment_quota, chapter_quota)

    query_to_indexes: dict[str, list[int]] = {}
    for index, reaction in enumerate(reactions):
        if reaction.get("type") != "curious":
            continue
        query = _normalize_search_query(reaction.get("search_query", ""))
        if not query:
            continue
        query_to_indexes.setdefault(query, []).append(index)

    if not query_to_indexes or query_quota <= 0:
        return {"reactions": reactions, "search_results": [], "budget": budget}

    search_results: list[SearchResultPayload] = []
    for query in list(query_to_indexes)[:query_quota]:
        error = ""
        problem_code = None
        try:
            raw_results = _invoke_curiosity_search(query, max_results=3)
        except Exception as exc:
            raw_results = []
            error = str(exc)
            problem_code = _normalize_problem_code(classify_search_problem(error))

        if isinstance(raw_results, list):
            for item in raw_results:
                if isinstance(item, dict) and item.get("error"):
                    error = _clean_text(item.get("error", ""))
                    problem_code = _normalize_problem_code(item.get("problem_code", ""))
                    break

        normalized_results = _normalize_search_hits(raw_results, max_results=3)
        result_payload: SearchResultPayload = {
            "reaction_indexes": query_to_indexes[query],
            "search_query": query,
            "results": normalized_results,
        }
        if error:
            result_payload["error"] = error
        if problem_code:
            result_payload["problem_code"] = problem_code
        search_results.append(result_payload)

    query_results = {
        item.get("search_query", ""): item.get("results", [])
        for item in search_results
    }
    for reaction in reactions:
        query = _normalize_search_query(reaction.get("search_query", ""))
        reaction["search_results"] = list(query_results.get(query, []))

    used_queries = len(search_results)
    budget["search_queries_remaining_in_segment"] = max(0, segment_quota - used_queries)
    budget["search_queries_remaining_in_chapter"] = max(0, chapter_quota - used_queries)
    return {"reactions": reactions, "search_results": search_results, "budget": budget}


def _fuse_curiosity_reaction(reaction: ReactionPayload, state: ReaderState) -> ReactionPayload:
    """Digest search results into the curious reaction's own voice."""
    if reaction.get("type") != "curious" or not reaction.get("search_results"):
        return reaction

    try:
        payload = invoke_json(
            READER_CURIOSITY_FUSE_SYSTEM,
            READER_CURIOSITY_FUSE_PROMPT.format(
                chapter_title=state.get("chapter_title", ""),
                segment_ref=_segment_ref(state),
                segment_summary=state.get("segment_summary", ""),
                anchor_quote=reaction.get("anchor_quote", "") or "（无）",
                reaction_content=reaction.get("content", "") or reaction.get("search_query", ""),
                search_query=reaction.get("search_query", ""),
                search_results=json.dumps(reaction.get("search_results", []), ensure_ascii=False, indent=2),
                output_language_name=language_name(state.get("output_language", "en")),
            ),
            default={},
        )
    except ReaderLLMError:
        raise
    except Exception:
        return reaction

    if not isinstance(payload, dict):
        return reaction

    fused_content = _clean_text(payload.get("content", ""))
    if not fused_content:
        return reaction

    updated = dict(reaction)
    updated["content"] = fused_content
    return updated


def fuse_curious_results_node(state: ReaderState) -> ReaderState:
    """Rewrite curious reactions after search so results are absorbed into the note."""
    reactions = [
        _fuse_curiosity_reaction(dict(reaction), state)
        for reaction in state.get("reactions", [])
    ]
    return {"reactions": reactions}


def reflect_node(state: ReaderState) -> ReaderState:
    """Self-review the reactions and decide pass/revise/skip."""
    payload = None
    active_reactions = _active_reactions(state.get("reactions", []))
    if active_reactions:
        memory_text, _budget = _assemble_memory_packet(state, "reflect")
        payload = invoke_json(
            READER_REFLECT_SYSTEM,
            READER_REFLECT_PROMPT.format(
                book_context=_format_book_context(state),
                current_part_context=_format_current_part_context(state),
                chapter_title=state.get("chapter_title", ""),
                segment_ref=_segment_ref(state),
                segment_summary=state.get("segment_summary", ""),
                segment_text=state.get("segment_text", "")[:6000],
                memory_text=memory_text,
                reactions_json=json.dumps(
                    state.get("reactions", []),
                    ensure_ascii=False,
                    indent=2,
                ),
                output_language_name=language_name(state.get("output_language", "en")),
            ),
            default={},
        )

    reflection = _normalize_reflection(payload, state)
    revision_count = state.get("revision_count", 0)
    output_language = state.get("output_language", "en")

    if reflection["verdict"] == "revise":
        next_count = revision_count + 1
        if next_count > state.get("max_revisions", 2):
            reflection = {
                **reflection,
                "verdict": "skip",
                "summary": _default_revision_overflow_summary(output_language),
                "revision_instruction": "",
            }
            return {
                "reflection": reflection,
                "revision_count": next_count,
                "revision_instruction": "",
            }
        return {
            "reflection": reflection,
            "revision_count": next_count,
            "revision_instruction": reflection.get("revision_instruction", ""),
        }

    return {
        "reflection": reflection,
        "revision_instruction": "",
    }


def should_continue_reader(state: ReaderState) -> Literal["express", "end"]:
    """Loop back to Express only when Reflect explicitly asks for revision."""
    reflection = state.get("reflection") or {}
    if reflection.get("verdict") == "revise":
        return "express"
    return "end"


def build_reader_graph() -> StateGraph:
    """Build the inner Reader graph."""
    graph = StateGraph(ReaderState)
    graph.add_node("read", read_node)
    graph.add_node("think", think_node)
    graph.add_node("express", express_node)
    graph.add_node("search_if_curious", search_if_curious_node)
    graph.add_node("fuse_curious_results", fuse_curious_results_node)
    graph.add_node("reflect", reflect_node)
    graph.set_entry_point("read")
    graph.add_edge("read", "think")
    graph.add_edge("think", "express")
    graph.add_edge("express", "search_if_curious")
    graph.add_edge("search_if_curious", "fuse_curious_results")
    graph.add_edge("fuse_curious_results", "reflect")
    graph.add_conditional_edges(
        "reflect",
        should_continue_reader,
        {
            "express": "express",
            "end": END,
        },
    )
    return graph


def _final_segment(state: ReaderState) -> RenderedSegment:
    """Extract the final renderable payload from reader state."""
    reflection = state.get("reflection") or {
        "verdict": "skip",
        "summary": "",
        "reason_codes": ["OTHER"],
    }
    reactions = _active_reactions(state.get("reactions", []))
    verdict = str(reflection.get("verdict", "skip")).strip().lower()
    if verdict not in {"pass", "skip"}:
        verdict = "pass" if reactions else "skip"

    reason_codes = [
        _clean_text(code).upper()
        for code in reflection.get("reason_codes", [])
        if _clean_text(code).upper() in _REASON_CODES
    ]
    typed_reason_codes: list[ReasonCode] = (
        [code for code in reason_codes]  # type: ignore[list-item]
        if reason_codes
        else ["OTHER"]
    )

    base: RenderedSegment = {
        "segment_id": state.get("segment_id", ""),
        "segment_ref": _segment_ref(state),
        "summary": state.get("segment_summary", ""),
        "verdict": verdict,
        "reactions": reactions if verdict == "pass" else [],
        "reflection_summary": reflection.get("summary", ""),
        "reflection_reason_codes": typed_reason_codes,
    }
    if verdict == "skip" or not reactions:
        base["verdict"] = "skip"
        base["reactions"] = []
        base["quality_status"] = "skipped"
        base["skip_reason"] = _skip_reason_from_codes(typed_reason_codes)
        return base

    low_signal_codes = {
        "LOW_SELECTIVITY",
        "WEAK_ASSOCIATION",
        "LOW_ATTRIBUTION_CONFIDENCE",
        "WEAK_TEXT_CONNECTION",
        "LOW_DEPTH",
        "INSUFFICIENT_EVIDENCE",
    }
    scores = [
        _safe_score(reflection.get("selectivity", 3)),
        _safe_score(reflection.get("association_quality", 3)),
        _safe_score(reflection.get("attribution_reasonableness", 3)),
        _safe_score(reflection.get("text_connection", 3)),
        _safe_score(reflection.get("depth", 3)),
    ]
    average_score = sum(scores) / len(scores)
    if any(code in low_signal_codes for code in typed_reason_codes):
        quality_status: QualityStatus = "weak"
    elif average_score >= 4.2 and len(reactions) >= 2:
        quality_status = "strong"
    elif average_score >= 3.0:
        quality_status = "acceptable"
    else:
        quality_status = "weak"
    base["quality_status"] = quality_status
    return base


def _short_progress_text(text: str, limit: int = 36) -> str:
    """Turn reaction content into a short status snippet."""
    cleaned = _clean_text(text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .。!！?？")
    if not cleaned:
        return ""
    sentence = re.split(r"[。!！?？]", cleaned, maxsplit=1)[0].strip()
    if len(sentence) <= limit:
        return sentence
    return sentence[: limit - 1].rstrip() + "…"


def _progress_excerpt(text: str, limit: int = 88) -> str:
    """Return a short excerpt for the live reading-activity snapshot."""
    cleaned = _clean_text(text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return ""
    sentence = re.split(r"(?<=[。!！?？.])\s+", cleaned, maxsplit=1)[0].strip()
    if len(sentence) <= limit:
        return sentence
    return sentence[: limit - 1].rstrip() + "…"


def _first_active_family(reactions: list[ReactionPayload]) -> str | None:
    """Return the most prominent visible reaction family in stable UI priority order."""
    family_priority = ("discern", "association", "curious", "retrospect", "highlight")
    active = _active_reactions(reactions)
    for family in family_priority:
        if any(str(reaction.get("type", "")) == family for reaction in active):
            return family
    return None


def _normalize_problem_code(value: object) -> CurrentReadingProblemCode | None:
    """Return one stable runtime problem code when recognized."""
    normalized = _clean_text(value).lower()
    if normalized in _CURRENT_READING_PROBLEM_CODES:
        return normalized  # type: ignore[return-value]
    return None


def _reader_progress_event(
    message: str,
    *,
    kind: ReaderProgressEvent["kind"],
    visibility: ReaderProgressEvent["visibility"] = "default",
    search_query: str | None = None,
    phase: str | None = None,
    current_excerpt: str | None = None,
    thought_family: str | None = None,
    problem_code: str | None = None,
) -> ReaderProgressEvent:
    """Create one structured progress event for the outer iterator."""
    payload: ReaderProgressEvent = {
        "message": message,
        "kind": kind,
        "visibility": visibility,
    }
    if search_query:
        payload["search_query"] = search_query
    if phase in {"reading", "thinking", "searching", "fusing", "reflecting", "waiting", "preparing"}:
        payload["phase"] = phase  # type: ignore[typeddict-item]
    excerpt = _progress_excerpt(current_excerpt or "")
    if excerpt:
        payload["current_excerpt"] = excerpt
    if thought_family in {"highlight", "association", "curious", "discern", "retrospect"}:
        payload["thought_family"] = thought_family  # type: ignore[typeddict-item]
    normalized_problem_code = _normalize_problem_code(problem_code)
    if normalized_problem_code:
        payload["problem_code"] = normalized_problem_code
    return payload


def express_progress_event(state: ReaderState) -> ReaderProgressEvent:
    """Render a co-reader style progress event from current reactions."""
    reactions = state.get("reactions", [])
    active_reactions = _active_reactions(reactions)
    if not active_reactions:
        return _reader_progress_event(
            "🤫 这段是过渡，安静读过",
            kind="transition",
            visibility="collapsed",
            phase="thinking",
            current_excerpt=state.get("segment_text", ""),
        )

    retrospect = next(
        (reaction for reaction in active_reactions if reaction.get("type") == "retrospect"),
        None,
    )
    if retrospect:
        snippet = _short_progress_text(retrospect.get("content", ""))
        return _reader_progress_event(
            f"🔗 {snippet}..." if snippet else "🔗 这和前文某处呼应了...",
            kind="thought",
            phase="thinking",
            current_excerpt=retrospect.get("anchor_quote", "") or state.get("segment_text", ""),
            thought_family="retrospect",
        )

    discern = next(
        (reaction for reaction in active_reactions if reaction.get("type") == "discern"),
        None,
    )
    if discern:
        snippet = _short_progress_text(discern.get("content", ""))
        return _reader_progress_event(
            f"⚡ {snippet}..." if snippet else "⚡ 这里的前提值得再推敲...",
            kind="thought",
            phase="thinking",
            current_excerpt=discern.get("anchor_quote", "") or state.get("segment_text", ""),
            thought_family="discern",
        )

    curious = next(
        (reaction for reaction in active_reactions if reaction.get("type") == "curious"),
        None,
    )
    if curious:
        query = _short_progress_text(
            curious.get("search_query", "") or curious.get("content", ""),
            limit=48,
        )
        search_query = _normalize_search_query(curious.get("search_query", "")) or None
        return _reader_progress_event(
            f"🔍 好奇 {query}，查一下..." if query else "🔍 这里有点好奇，查一下...",
            kind="search",
            search_query=search_query,
            phase="thinking",
            current_excerpt=curious.get("anchor_quote", "") or state.get("segment_text", ""),
            thought_family="curious",
        )

    highlights = [reaction for reaction in active_reactions if reaction.get("type") == "highlight"]
    if len(highlights) >= 2:
        return _reader_progress_event(
            "💡 好几句都有感触...",
            kind="thought",
            phase="thinking",
            current_excerpt=highlights[0].get("anchor_quote", "") or state.get("segment_text", ""),
            thought_family="highlight",
        )
    if highlights:
        snippet = _short_progress_text(
            highlights[0].get("content", "") or highlights[0].get("anchor_quote", "")
        )
        return _reader_progress_event(
            f"💡 {snippet}..." if snippet else "💡 先把这句划下来...",
            kind="thought",
            phase="thinking",
            current_excerpt=highlights[0].get("anchor_quote", "") or state.get("segment_text", ""),
            thought_family="highlight",
        )

    association = next(
        (reaction for reaction in active_reactions if reaction.get("type") == "association"),
        None,
    )
    if association:
        snippet = _short_progress_text(association.get("content", ""))
        return _reader_progress_event(
            f"✍️ {snippet}..." if snippet else "✍️ 这几句开始串起来了...",
            kind="thought",
            phase="thinking",
            current_excerpt=association.get("anchor_quote", "") or state.get("segment_text", ""),
            thought_family="association",
        )

    return _reader_progress_event(
        "🤫 这段先安静读过",
        kind="transition",
        visibility="collapsed",
        phase="thinking",
        current_excerpt=state.get("segment_text", ""),
        thought_family=_first_active_family(reactions),
    )


def express_progress_message(state: ReaderState) -> str:
    """Backward-compatible plain-text wrapper for tests and helper callers."""
    return str(express_progress_event(state).get("message", ""))


def search_progress_event(state: ReaderState) -> ReaderProgressEvent | None:
    """Render actual search queries for the search stage."""
    queries: list[str] = []
    for reaction in state.get("reactions", []):
        if reaction.get("type") != "curious":
            continue
        query = _normalize_search_query(reaction.get("search_query", ""))
        if not query or query in queries:
            continue
        queries.append(query)
        if len(queries) >= 2:
            break
    if not queries:
        return None
    return _reader_progress_event(
        f"🔎 搜索: {' / '.join(queries)}",
        kind="search",
        search_query=queries[0],
        phase="searching",
        current_excerpt=state.get("segment_text", ""),
        thought_family="curious",
    )


def search_progress_message(state: ReaderState) -> str:
    """Backward-compatible plain-text wrapper for tests and helper callers."""
    event = search_progress_event(state)
    return str(event.get("message", "")) if event else ""


def reflect_progress_event(reflection: ReflectionPayload | dict | None) -> ReaderProgressEvent:
    """Render one reflective status event from the verdict."""
    verdict = str((reflection or {}).get("verdict", "skip")).strip().lower()
    pool = _REFLECT_MESSAGE_POOLS.get(verdict, _REFLECT_MESSAGE_POOLS["skip"])
    previous = _LAST_REFLECT_MESSAGE.get(verdict)
    choices = [message for message in pool if message != previous] or list(pool)
    message = random.choice(choices)
    _LAST_REFLECT_MESSAGE[verdict] = message
    return _reader_progress_event(message, kind="transition", visibility="hidden", phase="reflecting")


def reflect_progress_message(reflection: ReflectionPayload | dict | None) -> str:
    """Backward-compatible plain-text wrapper for tests and helper callers."""
    return str(reflect_progress_event(reflection).get("message", ""))


def _reaction_memory_text(reaction: ReactionPayload) -> str:
    """Render one reaction into compact memory text."""
    parts = []
    if reaction.get("anchor_quote"):
        parts.append(reaction.get("anchor_quote", ""))
    if reaction.get("content"):
        parts.append(reaction.get("content", ""))
    elif reaction.get("search_query"):
        parts.append(reaction.get("search_query", ""))
    return " ".join(part for part in parts if part).strip()


def _finding_status_for_role(primary_role: str, role_tags: list[str] | None) -> FindingStatus:
    """Pick the default segment-time finding status from soft chapter role cues."""
    tags = set(role_tags or [])
    if primary_role == "body":
        return "durable"
    if "overview" in tags or "roadmap" in tags or "preface" in tags or "prologue" in tags:
        return "provisional"
    return "provisional"


def _touch_existing_ledger_items(memory: ReaderMemory, text: str, touched_at: str) -> None:
    """Refresh any ledger entries that clearly recur in the current segment."""
    lowered = _clean_text(text).lower()
    if not lowered:
        return
    for item in memory.get("salience_ledger", []):
        name = _clean_text(item.get("name", "")).lower()
        if name and name in lowered:
            item["last_touched_at"] = touched_at
            if _clean_text(item.get("status", "")) == "emerging":
                item["status"] = "active"


def _upsert_memory_finding(memory: ReaderMemory, finding: MemoryFinding) -> None:
    """Merge one finding into memory with lightweight deduplication."""
    normalized_text = _clean_text(finding.get("text", ""))
    if not normalized_text:
        return
    for item in memory.get("findings", []):
        if _clean_text(item.get("text", "")).lower() != normalized_text.lower():
            continue
        item["status"] = finding.get("status", item.get("status", "durable"))  # type: ignore[typeddict-item]
        item["anchor_quote"] = _clean_text(finding.get("anchor_quote", "")) or _clean_text(item.get("anchor_quote", ""))
        item["chapter_ref"] = _clean_text(finding.get("chapter_ref", "")) or _clean_text(item.get("chapter_ref", ""))
        item["segment_ref"] = _clean_text(finding.get("segment_ref", "")) or _clean_text(item.get("segment_ref", ""))
        item["touched_at"] = _clean_text(finding.get("touched_at", "")) or _timestamp()
        return
    memory.setdefault("findings", []).append(finding)


def _upsert_memory_thread(memory: ReaderMemory, thread: MemoryThread) -> None:
    """Merge one thread into memory with lightweight deduplication."""
    normalized_text = _clean_text(thread.get("text", ""))
    if not normalized_text:
        return
    for item in memory.get("threads", []):
        if _clean_text(item.get("text", "")).lower() != normalized_text.lower():
            continue
        item["status"] = _clean_text(thread.get("status", "")) or _clean_text(item.get("status", "open"))
        item["resolution"] = _clean_text(thread.get("resolution", "")) or _clean_text(item.get("resolution", ""))
        item["chapter_ref"] = _clean_text(thread.get("chapter_ref", "")) or _clean_text(item.get("chapter_ref", ""))
        item["segment_ref"] = _clean_text(thread.get("segment_ref", "")) or _clean_text(item.get("segment_ref", ""))
        item["touched_at"] = _clean_text(thread.get("touched_at", "")) or _timestamp()
        return
    memory.setdefault("threads", []).append(thread)


def _upsert_salience_item(memory: ReaderMemory, item: SalienceLedgerItem) -> None:
    """Merge one salience-ledger item into memory."""
    normalized_name = _clean_text(item.get("name", ""))
    if not normalized_name:
        return
    for existing in memory.get("salience_ledger", []):
        if _clean_text(existing.get("name", "")).lower() != normalized_name.lower():
            continue
        if _clean_text(item.get("working_note", "")):
            existing["working_note"] = _clean_text(item.get("working_note", ""))
        if _clean_text(item.get("status", "")):
            existing["status"] = _clean_text(item.get("status", "active"))  # type: ignore[typeddict-item]
        if _clean_text(item.get("kind", "")):
            existing["kind"] = _clean_text(item.get("kind", "concept"))  # type: ignore[typeddict-item]
        existing["last_touched_at"] = _clean_text(item.get("last_touched_at", "")) or _timestamp()
        return
    memory.setdefault("salience_ledger", []).append(item)


def update_memory(
    memory: ReaderMemory,
    segment: RenderedSegment,
    *,
    chapter_ref: str = "",
    primary_role: str = "body",
    role_tags: list[str] | None = None,
) -> ReaderMemory:
    """Update reading memory after one semantic unit is processed."""
    next_memory = coerce_reader_memory(memory)
    touched_at = _timestamp()
    segment_ref = _clean_text(segment.get("segment_ref", "")) or _clean_text(segment.get("segment_id", ""))
    next_memory.setdefault("recent_segment_flow", []).append(
        {
            "segment_ref": segment_ref,
            "chapter_ref": _clean_text(chapter_ref),
            "summary": _clean_text(segment.get("summary", "")),
            "touched_at": touched_at,
        }
    )
    next_memory["recent_segment_flow"] = next_memory.get("recent_segment_flow", [])[-_RECENT_SEGMENT_FLOW_LIMIT:]

    reactions = segment.get("reactions", [])
    if segment.get("verdict") == "pass":
        finding_status = _finding_status_for_role(primary_role, role_tags)
        for reaction in reactions:
            if reaction.get("type") not in {"highlight", "association", "discern", "retrospect"}:
                continue
            text = _reaction_memory_text(reaction)
            if not text:
                continue
            _upsert_memory_finding(
                next_memory,
                {
                    "text": text,
                    "status": finding_status,
                    "anchor_quote": _clean_text(reaction.get("anchor_quote", "")),
                    "chapter_ref": _clean_text(chapter_ref),
                    "segment_ref": segment_ref,
                    "touched_at": touched_at,
                },
            )

    highlighted_quotes = [
        reaction.get("anchor_quote", "").strip()
        for reaction in reactions
        if reaction.get("type") == "highlight" and reaction.get("anchor_quote", "").strip()
    ]
    next_memory.setdefault("recent_highlighted_quotes", []).extend(highlighted_quotes)
    next_memory["recent_highlighted_quotes"] = next_memory.get("recent_highlighted_quotes", [])[-_RECENT_HIGHLIGHT_LIMIT:]

    curiosities = [
        _reaction_memory_text(reaction) or reaction.get("search_query", "")
        for reaction in reactions
        if reaction.get("type") == "curious"
    ]
    for item in curiosities:
        text = _clean_text(item)
        if not text:
            continue
        _upsert_memory_thread(
            next_memory,
            {
                "text": text,
                "status": "open",
                "chapter_ref": _clean_text(chapter_ref),
                "segment_ref": segment_ref,
                "resolution": "",
                "touched_at": touched_at,
            },
        )

    _touch_existing_ledger_items(next_memory, segment.get("summary", ""), touched_at)
    _touch_existing_ledger_items(next_memory, " ".join(_reaction_memory_text(reaction) for reaction in reactions), touched_at)
    return _legacy_memory_view(next_memory)


def initial_memory() -> ReaderMemory:
    """Create empty reading memory for a new read session."""
    return coerce_reader_memory({})


def _default_chapter_memory_summary(chapter_title: str, segments: list[RenderedSegment]) -> str:
    """Create a deterministic fallback chapter summary when chapter reflection omits one."""
    summaries = [
        _clean_text(segment.get("summary", ""))
        for segment in segments
        if _clean_text(segment.get("summary", ""))
    ][:2]
    if summaries:
        return f"{chapter_title}: " + " / ".join(summaries)
    return chapter_title


def _normalize_memory_actions(chapter_reflection: dict[str, object] | None) -> dict[str, object]:
    """Extract normalized memory actions from chapter reflection payload."""
    if not isinstance(chapter_reflection, dict):
        return {
            "finding_updates": [],
            "thread_updates": [],
            "salience_updates": [],
            "chapter_memory_summary": "",
            "book_arc_summary": "",
        }
    payload = chapter_reflection.get("memory_actions", {})
    if not isinstance(payload, dict):
        payload = {}

    def normalize_status(value: object, allowed: set[str], fallback: str) -> str:
        text = _clean_text(value).lower()
        return text if text in allowed else fallback

    finding_updates: list[dict[str, object]] = []
    for item in payload.get("finding_updates", []):
        if not isinstance(item, dict):
            continue
        text = _clean_text(item.get("text", ""))
        if not text:
            continue
        finding_updates.append(
            {
                "text": text,
                "status": normalize_status(item.get("status", ""), {"provisional", "durable", "superseded"}, "durable"),
                "anchor_quote": _clean_text(item.get("anchor_quote", "")),
                "segment_ref": _clean_text(item.get("segment_ref", "")),
            }
        )

    thread_updates: list[dict[str, object]] = []
    for item in payload.get("thread_updates", []):
        if not isinstance(item, dict):
            continue
        text = _clean_text(item.get("text", ""))
        if not text:
            continue
        thread_updates.append(
            {
                "text": text,
                "status": normalize_status(item.get("status", ""), {"open", "resolved", "parked"}, "open"),
                "resolution": _clean_text(item.get("resolution", "")),
                "segment_ref": _clean_text(item.get("segment_ref", "")),
            }
        )

    salience_updates: list[dict[str, object]] = []
    for item in payload.get("salience_updates", []):
        if not isinstance(item, dict):
            continue
        name = _clean_text(item.get("name", ""))
        if not name:
            continue
        salience_updates.append(
            {
                "kind": normalize_status(item.get("kind", ""), {"concept", "character", "institution", "place", "motif"}, "concept"),
                "name": name,
                "working_note": _clean_text(item.get("working_note", "")),
                "status": normalize_status(item.get("status", ""), {"emerging", "active", "stable", "contested", "resolved"}, "active"),
            }
        )

    return {
        "finding_updates": finding_updates,
        "thread_updates": thread_updates,
        "salience_updates": salience_updates,
        "chapter_memory_summary": _clean_text(payload.get("chapter_memory_summary", "")),
        "book_arc_summary": _clean_text(payload.get("book_arc_summary", "")),
    }


def consolidate_memory_after_chapter(
    memory: ReaderMemory,
    *,
    chapter_ref: str,
    chapter_title: str,
    primary_role: str,
    rendered_segments: list[RenderedSegment],
    chapter_reflection: dict[str, object] | None,
) -> ReaderMemory:
    """Apply chapter-end memory actions and persist a book-level snapshot view."""
    next_memory = coerce_reader_memory(memory)
    touched_at = _timestamp()
    actions = _normalize_memory_actions(chapter_reflection)

    for update in actions.get("finding_updates", []):
        if not isinstance(update, dict):
            continue
        anchor_quote = _clean_text(update.get("anchor_quote", ""))
        _upsert_memory_finding(
            next_memory,
            {
                "text": _clean_text(update.get("text", "")),
                "status": _clean_text(update.get("status", "durable")) or "durable",
                "anchor_quote": anchor_quote,
                "chapter_ref": chapter_ref,
                "segment_ref": _clean_text(update.get("segment_ref", "")),
                "touched_at": touched_at,
            },
        )
        if anchor_quote:
            next_memory.setdefault("recent_highlighted_quotes", []).append(anchor_quote)
    if not actions.get("finding_updates"):
        fallback_finding_count = 0
        for segment in rendered_segments:
            for reaction in segment.get("reactions", []):
                if not isinstance(reaction, dict):
                    continue
                if reaction.get("type") == "silent":
                    continue
                text = _reaction_memory_text(reaction)
                if not text:
                    continue
                _upsert_memory_finding(
                    next_memory,
                    {
                        "text": text,
                        "status": "durable",
                        "anchor_quote": _clean_text(reaction.get("anchor_quote", "")),
                        "chapter_ref": chapter_ref,
                        "segment_ref": _clean_text(segment.get("segment_ref", "")) or _clean_text(segment.get("segment_id", "")),
                        "touched_at": touched_at,
                    },
                )
                if _clean_text(reaction.get("anchor_quote", "")):
                    next_memory.setdefault("recent_highlighted_quotes", []).append(_clean_text(reaction.get("anchor_quote", "")))
                fallback_finding_count += 1
                if fallback_finding_count >= 2:
                    break
            if fallback_finding_count >= 2:
                break

    for update in actions.get("thread_updates", []):
        if not isinstance(update, dict):
            continue
        _upsert_memory_thread(
            next_memory,
            {
                "text": _clean_text(update.get("text", "")),
                "status": _clean_text(update.get("status", "open")) or "open",
                "chapter_ref": chapter_ref,
                "segment_ref": _clean_text(update.get("segment_ref", "")),
                "resolution": _clean_text(update.get("resolution", "")),
                "touched_at": touched_at,
            },
        )

    for update in actions.get("salience_updates", []):
        if not isinstance(update, dict):
            continue
        _upsert_salience_item(
            next_memory,
            {
                "kind": _clean_text(update.get("kind", "concept")) or "concept",
                "name": _clean_text(update.get("name", "")),
                "working_note": _clean_text(update.get("working_note", "")),
                "introduced_at": touched_at,
                "last_touched_at": touched_at,
                "status": _clean_text(update.get("status", "active")) or "active",
            },
        )

    chapter_summary = _clean_text(actions.get("chapter_memory_summary", "")) or _default_chapter_memory_summary(
        chapter_title,
        rendered_segments,
    )
    summaries = [
        item
        for item in next_memory.get("chapter_memory_summaries", [])
        if _clean_text(item.get("chapter_ref", "")) != chapter_ref
    ]
    summaries.append(
        {
            "chapter_ref": chapter_ref,
            "chapter_title": chapter_title,
            "primary_role": primary_role if primary_role in {"front_matter", "body", "back_matter"} else "body",
            "summary": chapter_summary,
            "touched_at": touched_at,
        }
    )
    next_memory["chapter_memory_summaries"] = summaries

    book_arc_summary = _clean_text(actions.get("book_arc_summary", ""))
    if book_arc_summary:
        next_memory["book_arc_summary"] = book_arc_summary
    elif not _clean_text(next_memory.get("book_arc_summary", "")):
        recent = [
            _clean_text(item.get("summary", ""))
            for item in next_memory.get("chapter_memory_summaries", [])[-3:]
            if _clean_text(item.get("summary", ""))
        ]
        next_memory["book_arc_summary"] = " / ".join(recent)

    next_memory["recent_highlighted_quotes"] = next_memory.get("recent_highlighted_quotes", [])[-_RECENT_HIGHLIGHT_LIMIT:]
    return _legacy_memory_view(next_memory)


def run_reader_segment(
    state: ReaderState,
    progress: ProgressReporter = None,
) -> tuple[RenderedSegment, ReaderState]:
    """Run one semantic unit with dynamic slicing and token-driven budget guards."""
    current = dict(state)
    budget = dict(_default_budget())
    budget.update(current.get("budget") or {})
    timeout_seconds = max(1, int(budget.get("segment_timeout_seconds", 120)))
    started_at = time.monotonic()
    budget["work_units_remaining"] = _initial_work_units(current)
    current["budget"] = budget

    merged_reactions: list[ReactionPayload] = []
    merged_reason_codes: list[ReasonCode] = []
    merged_summaries: list[str] = []
    subsegments = _build_subsegments(current)

    def elapsed_seconds() -> float:
        return time.monotonic() - started_at

    def budget_exhausted() -> bool:
        return int(budget.get("work_units_remaining", 0)) <= 0 or elapsed_seconds() > timeout_seconds

    for index, subsegment in enumerate(subsegments, start=1):
        if budget_exhausted() and (merged_reactions or index > 1):
            break

        progress_prefix = f"[{index}/{len(subsegments)}] " if len(subsegments) > 1 else ""
        substate = dict(current)
        substate["segment_id"] = state.get("segment_id", "")
        substate["segment_ref"] = _segment_ref(state)
        substate["segment_summary"] = subsegment.get("summary", current.get("segment_summary", ""))
        substate["segment_text"] = subsegment.get("text", current.get("segment_text", ""))
        substate["revision_count"] = 0
        substate["max_revisions"] = 0
        substate["revision_instruction"] = ""
        substate["budget"] = dict(budget)

        if progress:
            progress(
                _reader_progress_event(
                    "",
                    kind="position",
                    visibility="hidden",
                    phase="reading",
                    current_excerpt=subsegment.get("text", current.get("segment_text", "")),
                )
            )

        substate.update(read_node(substate))
        if progress:
            progress(
                _reader_progress_event(
                    "",
                    kind="transition",
                    visibility="hidden",
                    phase="thinking",
                    current_excerpt=subsegment.get("text", current.get("segment_text", "")),
                )
            )
        try:
            substate.update(think_node(substate))
        except ReaderLLMError as exc:
            if progress:
                progress(
                    _reader_progress_event(
                        "",
                        kind="transition",
                        visibility="hidden",
                        phase="thinking",
                        current_excerpt=subsegment.get("text", current.get("segment_text", "")),
                        problem_code=exc.problem_code,
                    )
                )
            raise
        _consume_work_units(budget, 1)
        thought = substate.get("thought") or {}
        if not thought.get("should_express"):
            budget["early_stop"] = True
            if progress:
                progress(
                    _reader_progress_event(
                        f"{progress_prefix}🤫 这段是过渡，安静读过",
                        kind="transition",
                        visibility="collapsed",
                    )
                )
            continue

        substate["budget"] = dict(budget)
        try:
            substate.update(express_node(substate))
        except ReaderLLMError as exc:
            if progress:
                progress(
                    _reader_progress_event(
                        "",
                        kind="transition",
                        visibility="hidden",
                        phase="thinking",
                        current_excerpt=subsegment.get("text", current.get("segment_text", "")),
                        problem_code=exc.problem_code,
                    )
                )
            raise
        _consume_work_units(budget, 1)

        if progress:
            express_event = express_progress_event(substate)
            progress(
                _reader_progress_event(
                    f"{progress_prefix}{express_event['message']}",
                    kind=express_event["kind"],
                    visibility=express_event.get("visibility", "default"),
                    search_query=express_event.get("search_query"),
                )
            )

        sub_budget = dict(budget)
        if _should_expand_curiosity(thought, sub_budget):
            curiosity_potential = _safe_score(thought.get("curiosity_potential", 3))
            max_queries = 2 if curiosity_potential >= 4 else 1
            sub_budget["search_queries_remaining_in_segment"] = min(
                max(0, int(sub_budget.get("search_queries_remaining_in_segment", 0))),
                max_queries,
            )
            substate["budget"] = sub_budget
            search_event = search_progress_event(substate)
            if progress and search_event:
                progress(
                    _reader_progress_event(
                        f"{progress_prefix}{search_event['message']}",
                        kind=search_event["kind"],
                        visibility=search_event.get("visibility", "default"),
                        search_query=search_event.get("search_query"),
                    )
                )
            substate.update(search_if_curious_node(substate))
            sub_budget = dict(substate.get("budget") or sub_budget)
            search_problem = next(
                (
                    _normalize_problem_code(result.get("problem_code", ""))
                    for result in substate.get("search_results", [])
                    if isinstance(result, dict) and _normalize_problem_code(result.get("problem_code", ""))
                ),
                None,
            )
            if progress and search_problem:
                progress(
                    _reader_progress_event(
                        "",
                        kind="search",
                        visibility="hidden",
                        phase="searching",
                        current_excerpt=substate.get("segment_text", ""),
                        search_query=_normalize_search_query(
                            next(
                                (
                                    result.get("search_query", "")
                                    for result in substate.get("search_results", [])
                                    if isinstance(result, dict) and _clean_text(result.get("search_query", ""))
                                ),
                                "",
                            )
                        ),
                        problem_code=search_problem,
                    )
                )
            _consume_work_units(budget, 1)
        else:
            sub_budget["search_queries_remaining_in_segment"] = 0
            substate["budget"] = sub_budget
            substate["search_results"] = []

        budget["search_queries_remaining_in_chapter"] = max(
            0,
            int(sub_budget.get("search_queries_remaining_in_chapter", budget.get("search_queries_remaining_in_chapter", 0))),
        )
        budget["search_queries_remaining_in_segment"] = max(
            0,
            int(sub_budget.get("search_queries_remaining_in_segment", budget.get("search_queries_remaining_in_segment", 0))),
        )

        if substate.get("search_results") and int(budget.get("work_units_remaining", 0)) > 0:
            if progress:
                progress(
                    _reader_progress_event(
                        "",
                        kind="transition",
                        visibility="hidden",
                        phase="fusing",
                        current_excerpt=substate.get("segment_text", ""),
                        search_query=_normalize_search_query(
                            next(
                                (
                                    reaction.get("search_query", "")
                                    for reaction in substate.get("reactions", [])
                                    if reaction.get("type") == "curious"
                                ),
                                "",
                            )
                        ),
                        thought_family=_first_active_family(substate.get("reactions", [])),
                    )
                )
            substate["budget"] = dict(budget)
            try:
                substate.update(fuse_curious_results_node(substate))
            except ReaderLLMError as exc:
                if progress:
                    progress(
                        _reader_progress_event(
                            "",
                            kind="transition",
                            visibility="hidden",
                            phase="fusing",
                            current_excerpt=substate.get("segment_text", ""),
                            search_query=_normalize_search_query(
                                next(
                                    (
                                        reaction.get("search_query", "")
                                        for reaction in substate.get("reactions", [])
                                        if reaction.get("type") == "curious"
                                    ),
                                    "",
                                )
                            ),
                            thought_family=_first_active_family(substate.get("reactions", [])),
                            problem_code=exc.problem_code,
                        )
                    )
                raise
            _consume_work_units(budget, 1)

        if int(budget.get("work_units_remaining", 0)) > 0 and elapsed_seconds() <= timeout_seconds:
            if progress:
                progress(
                    _reader_progress_event(
                        "",
                        kind="transition",
                        visibility="hidden",
                        phase="reflecting",
                        current_excerpt=substate.get("segment_text", ""),
                        thought_family=_first_active_family(substate.get("reactions", [])),
                    )
                )
            substate["budget"] = dict(budget)
            try:
                substate.update(reflect_node(substate))
            except ReaderLLMError as exc:
                if progress:
                    progress(
                        _reader_progress_event(
                            "",
                            kind="transition",
                            visibility="hidden",
                            phase="reflecting",
                            current_excerpt=substate.get("segment_text", ""),
                            thought_family=_first_active_family(substate.get("reactions", [])),
                            problem_code=exc.problem_code,
                        )
                    )
                raise
            reflection = dict(substate.get("reflection") or {})
            if reflection.get("verdict") == "revise":
                reflection["verdict"] = "pass" if _active_reactions(substate.get("reactions", [])) else "skip"
                reflection["revision_instruction"] = ""
                substate["reflection"] = reflection
            _consume_work_units(budget, 1)
        else:
            substate["reflection"] = _minimal_budget_reflection(substate)

        reflection_payload = substate.get("reflection") or {}
        if progress:
            reflect_event = reflect_progress_event(reflection_payload)
            progress(
                _reader_progress_event(
                    f"{progress_prefix}{reflect_event['message']}",
                    kind=reflect_event["kind"],
                    visibility=reflect_event.get("visibility", "default"),
                    search_query=reflect_event.get("search_query"),
                )
            )

        rendered = _final_segment(substate)
        if rendered.get("verdict") != "skip" and rendered.get("reactions"):
            merged_reactions.extend(rendered.get("reactions", []))
            for reason_code in rendered.get("reflection_reason_codes", []):
                if reason_code in _REASON_CODES and reason_code not in merged_reason_codes:
                    merged_reason_codes.append(reason_code)  # type: ignore[list-item]
            summary = _clean_text(rendered.get("reflection_summary", ""))
            if summary:
                merged_summaries.append(summary)

    budget["segment_timed_out"] = elapsed_seconds() > timeout_seconds
    current["budget"] = budget

    if not merged_reactions:
        current["reactions"] = []
        current["reflection"] = _minimal_budget_reflection(current)
        return _final_segment(current), current

    skill_policy = current.get("skill_policy") or _default_skill_policy()
    merged_limit = min(
        24,
        max(
            6,
            int(skill_policy.get("max_reactions_per_segment", 8)) * (2 if len(subsegments) > 1 else 1),
        ),
    )
    final_reactions = _merge_reactions(merged_reactions, max_items=merged_limit)

    merged_summary = merged_summaries[0] if merged_summaries else _default_reflection_summary(current.get("output_language", "en"))
    reason_codes: list[ReasonCode] = merged_reason_codes[:3] if merged_reason_codes else ["OTHER"]
    if budget.get("segment_timed_out") and "OVER_EXTENDED" not in reason_codes:
        reason_codes = (reason_codes + ["OVER_EXTENDED"])[:3]  # type: ignore[assignment]

    current["reactions"] = final_reactions
    current["reflection"] = {
        "verdict": "pass",
        "summary": merged_summary,
        "selectivity": 4,
        "association_quality": 4,
        "attribution_reasonableness": 4,
        "text_connection": 4,
        "depth": 4,
        "issues": [],
        "reason_codes": reason_codes,
        "target_reaction_indexes": [],
        "revision_instruction": "",
    }
    return _final_segment(current), current


def run_reader_segment_for_analysis(
    state: ReaderState,
    progress: ProgressReporter = None,
) -> tuple[RenderedSegment, ReaderState]:
    """Lightweight wrapper used by book-level analysis mode."""
    rendered, final_state = run_reader_segment(state, progress=progress)
    compact: RenderedSegment = {
        "segment_id": rendered.get("segment_id", ""),
        "segment_ref": rendered.get("segment_ref", rendered.get("segment_id", "")),
        "summary": rendered.get("summary", ""),
        "verdict": rendered.get("verdict", "skip"),
        "reactions": rendered.get("reactions", []),
        "reflection_summary": rendered.get("reflection_summary", ""),
        "reflection_reason_codes": rendered.get("reflection_reason_codes", []),
    }
    if "quality_status" in rendered:
        compact["quality_status"] = rendered.get("quality_status", "acceptable")
    if "skip_reason" in rendered:
        compact["skip_reason"] = rendered.get("skip_reason", "")
    return compact, final_state

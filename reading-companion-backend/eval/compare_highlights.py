"""Compare human highlights against Reader output to diagnose blind spots."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_anthropic import ChatAnthropic

from src.config import get_llm_config
from src.iterator_reader.llm_utils import parse_json_payload, response_text
from src.iterator_reader.storage import display_segment_id


SEMANTIC_MATCH_SYSTEM = """你在做“感知盲区诊断”，不是在评判谁对谁错。

任务：判断人类高亮与 Agent 某条 reaction 是否在讨论同一个“概念点”。

判断原则：
- 命中标准是“概念级”，不是句子级
- 如果只是同一段里不同但相邻的句子，且表达的是同一个论点，可以判定为命中
- 如果只是主题大类相近，但具体抓到的论证点不同，不算命中
- 保守判断，不要为了提高命中率而强行匹配

只输出 JSON。"""


SEMANTIC_MATCH_PROMPT = """人类高亮：
{human_quote}

人类批注：
{human_note}

人类高亮最可能所在 Section：
{section_hint}

候选 Agent reactions：
{candidates_json}

请判断是否存在概念级命中，输出 JSON：
{{
  "matched": true,
  "candidate_id": "候选 reaction id；如果没有则留空",
  "reason": "一句话说明为什么算命中或为什么不算"
}}"""


OMISSION_DIAGNOSIS_SYSTEM = """你在分析 Reader Agent 的感知盲区。目标是找系统性原因，不是让 Agent 模仿人类高亮。

给定一个“人类高亮但 Agent 没反应”的条目，请从以下类别中选最主要的一个：
- parse 分段问题
- 感知密度不足
- 角色盲区
- 上下文依赖
- 其他

分类标准：
- parse 分段问题：文本被切分导致上下文断裂，Agent难以完整感知
- 感知密度不足：Agent对该段已有一些反应，但段内其他值得注意的点漏掉了
- 角色盲区：共读者角色对某类表达天然不敏感，例如修辞、隐喻、情感张力、反讽
- 上下文依赖：这条高亮更依赖读者个人经历、价值偏好或更远上下文，不构成明显缺陷
- 其他：以上都不贴切

不要提出“增加数量指标”之类的建议。只输出 JSON。"""


OMISSION_DIAGNOSIS_PROMPT = """人类高亮：
{human_quote}

人类批注：
{human_note}

最可能所在 Section：
{section_hint}

该 Section 原文：
{segment_text}

Agent 在该 Section 及相邻 Section 的 reactions：
{local_reactions_json}

请输出 JSON：
{{
  "category": "parse 分段问题|感知密度不足|角色盲区|上下文依赖|其他",
  "analysis": "2-4 句具体分析，解释为什么会漏，以及这说明了什么盲区"
}}"""


OMISSION_SUMMARY_SYSTEM = """你在总结 Reader Agent 的感知盲区模式。

要求：
- 只根据遗漏项结构化信息总结，不要臆造
- 不要把结论写成“应该模仿人类高亮”
- 重点指出系统性盲区与合理差异的边界
- 输出简洁 markdown 段落，2-4 段即可"""


OMISSION_SUMMARY_PROMPT = """下面是 Chapter {chapter_number} 的遗漏项分析：
{omissions_json}

请写“遗漏模式总结”，指出：
1. 哪类原因占主导
2. 这说明 Agent 的哪种感知能力存在盲区
3. 哪些差异其实是合理差异，不该被当成缺陷"""


@dataclass(frozen=True)
class HumanHighlight:
    """One human highlight entry."""

    highlight_id: str
    quote: str
    note: str
    source: str
    chapter: int


@dataclass(frozen=True)
class AgentReaction:
    """One rendered agent reaction with its anchor quote."""

    reaction_id: str
    section_ref: str
    section_title: str
    reaction_type: str
    quote: str
    note: str


@dataclass(frozen=True)
class SegmentContext:
    """One chapter segment from structure.json."""

    section_ref: str
    section_title: str
    segment_text: str
    order: int


@dataclass(frozen=True)
class MatchResult:
    """One human highlight's best comparison result."""

    human: HumanHighlight
    status: str
    agent: AgentReaction | None
    match_reason: str
    match_score: float
    section_hint: SegmentContext | None
    diagnosis_category: str = ""
    diagnosis_analysis: str = ""


def normalize_text(text: str) -> str:
    """Normalize text for fuzzy comparison."""
    normalized = unicodedata.normalize("NFKC", text or "")
    normalized = normalized.replace("“", '"').replace("”", '"')
    normalized = normalized.replace("’", "'").replace("–", "-").replace("—", "-")
    normalized = normalized.replace("…", "...")
    normalized = normalized.lower()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"\s*([,.;:!?()\"'])\s*", r"\1", normalized)
    return normalized.strip()


def fuzzy_ratio(left: str, right: str) -> float:
    """Return a fuzzy ratio on a 0-100 scale."""
    normalized_left = normalize_text(left)
    normalized_right = normalize_text(right)
    if not normalized_left or not normalized_right:
        return 0.0
    if normalized_left in normalized_right or normalized_right in normalized_left:
        return 100.0
    return SequenceMatcher(None, normalized_left, normalized_right).ratio() * 100


def _clean_quote_text(text: str) -> str:
    """Clean extracted quote text from markdown artifacts."""
    cleaned = unicodedata.normalize("NFKC", text or "")
    cleaned = re.sub(r"!\[\]\[image\d+\]", "", cleaned)
    cleaned = cleaned.replace("|", " ")
    cleaned = cleaned.replace("\\", "")
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned.strip(" -*_>\t\r\n")
    for left, right in (('"', '"'), ("“", "”"), ("'", "'")):
        if cleaned.startswith(left) and cleaned.endswith(right) and len(cleaned) >= 2:
            cleaned = cleaned[1:-1].strip()
    return cleaned


def safe_invoke_json(system_prompt: str, user_prompt: str, default: dict) -> dict:
    """Invoke the LLM for JSON output but fall back gracefully."""
    try:
        llm = get_comparison_llm()
        response = llm.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        )
        payload = parse_json_payload(response_text(response), default)
    except Exception:
        return default
    return payload if isinstance(payload, dict) else default


def safe_invoke_text(system_prompt: str, user_prompt: str, default: str) -> str:
    """Invoke the LLM for text output but keep the script resilient."""
    try:
        llm = get_comparison_llm()
        response = llm.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        )
    except Exception:
        return default
    text = response_text(response).strip()
    return text or default


def get_comparison_llm() -> ChatAnthropic:
    """Create a bounded-timeout model for highlight comparison."""
    config = get_llm_config()
    return ChatAnthropic(
        base_url=config["base_url"],
        api_key=config["api_key"],
        model=config["model"],
        temperature=0.1,
        max_tokens=1200,
        timeout=25,
    )


def _dedupe_human_highlights(items: Iterable[HumanHighlight]) -> list[HumanHighlight]:
    """Deduplicate human highlights by normalized quote text."""
    deduped: dict[str, HumanHighlight] = {}
    for item in items:
        key = normalize_text(item.quote)
        if not key:
            continue
        if key not in deduped:
            deduped[key] = item
            continue
        existing = deduped[key]
        if item.note and not existing.note:
            deduped[key] = item
    return list(deduped.values())


def _extract_chapter_block(markdown: str, chapter_number: int) -> str:
    """Extract one chapter block from a markdown export."""
    heading_pattern = re.compile(
        rf"^##\s+\*?Chapter\s+{chapter_number}\*?\s*$",
        flags=re.IGNORECASE | re.MULTILINE,
    )
    match = heading_pattern.search(markdown)
    if not match:
        return ""

    remainder = markdown[match.end() :]
    next_heading = re.search(r"^##\s+\*?Chapter\s+\d+\*?\s*$", remainder, flags=re.IGNORECASE | re.MULTILINE)
    if next_heading:
        return remainder[: next_heading.start()]
    return remainder


def _parse_simple_blockquotes(block: str, chapter_number: int) -> list[HumanHighlight]:
    """Parse ## Chapter N + blockquote style highlights."""
    lines = block.splitlines()
    highlights: list[HumanHighlight] = []
    quote_lines: list[str] = []
    note_lines: list[str] = []
    counter = 1

    def flush() -> None:
        nonlocal counter, quote_lines, note_lines
        quote = _clean_quote_text(" ".join(quote_lines))
        note = _clean_quote_text(" ".join(note_lines))
        if quote:
            highlights.append(
                HumanHighlight(
                    highlight_id=f"h{chapter_number:02d}-{counter:03d}",
                    quote=quote,
                    note=note,
                    source="manual",
                    chapter=chapter_number,
                )
            )
            counter += 1
        quote_lines = []
        note_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith(">"):
            if quote_lines:
                flush()
            quote_lines.append(stripped.lstrip(">").strip())
            continue
        if stripped.startswith("我的批注：") or stripped.startswith("My note:"):
            note_lines.append(stripped.split("：", 1)[-1].split(":", 1)[-1].strip())
            continue
        if quote_lines and stripped:
            note_lines.append(stripped)
            continue
    if quote_lines:
        flush()
    return highlights


def _parse_google_books_entry(line: str, chapter_number: int, counter: int) -> HumanHighlight | None:
    """Parse one Google Books markdown export line."""
    stripped = line.strip()
    if not stripped.startswith("|") or "[http" not in stripped and "](" not in stripped:
        return None
    content = stripped.strip("|").strip()
    if set(content) == {"-"}:
        return None

    content = re.sub(r"!\[\]\[image\d+\]\s*", "", content)
    content = content.replace("*![][image2]", "").replace("*![][image3]", "").replace("*![][image4]", "").replace("*![][image5]", "")

    page_match = re.search(r"\[(?P<page>\d+)\]\(", content)
    if not page_match:
        return None

    prefix = content[: page_match.start()].strip()
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
    note = _clean_quote_text(note)
    if not quote:
        return None

    return HumanHighlight(
        highlight_id=f"h{chapter_number:02d}-{counter:03d}",
        quote=quote,
        note=note,
        source=f"p.{page_match.group('page')}",
        chapter=chapter_number,
    )


def parse_human_highlights(path: Path, chapter_number: int) -> list[HumanHighlight]:
    """Parse human highlights from either simple markdown or Google Books export."""
    markdown = path.read_text(encoding="utf-8")
    block = _extract_chapter_block(markdown, chapter_number)
    if not block:
        raise ValueError(
            f"未在 {path} 中找到 Chapter {chapter_number}。"
            " 请确认高亮文件已准备好，或使用包含 `## Chapter N` 的格式。"
        )

    simple_hits = _parse_simple_blockquotes(block, chapter_number)
    if simple_hits:
        return _dedupe_human_highlights(simple_hits)

    google_hits: list[HumanHighlight] = []
    counter = 1
    for line in block.splitlines():
        item = _parse_google_books_entry(line, chapter_number, counter)
        if item is None:
            continue
        google_hits.append(item)
        counter += 1

    if google_hits:
        return _dedupe_human_highlights(google_hits)

    raise ValueError(
        f"无法解析 {path} 的 Chapter {chapter_number} 高亮。"
        " 请检查格式，或整理成 `## Chapter N` + blockquote 的形式。"
    )


def parse_agent_reactions(path: Path) -> list[AgentReaction]:
    """Parse reactions from a rendered chapter markdown file."""
    lines = path.read_text(encoding="utf-8").splitlines()
    reactions: list[AgentReaction] = []
    section_ref = ""
    section_title = ""
    current_type = ""
    quote_lines: list[str] = []
    note_lines: list[str] = []
    counter = 1

    def flush() -> None:
        nonlocal counter, current_type, quote_lines, note_lines
        if not current_type:
            return
        quote = _clean_quote_text(" ".join(quote_lines))
        note = _clean_quote_text(" ".join(note_lines))
        if quote or note:
            reactions.append(
                AgentReaction(
                    reaction_id=f"a-{counter:03d}",
                    section_ref=section_ref,
                    section_title=section_title,
                    reaction_type=current_type,
                    quote=quote,
                    note=note,
                )
            )
            counter += 1
        current_type = ""
        quote_lines = []
        note_lines = []

    section_pattern = re.compile(r"^##\s+(?:Section|段落)\s+(\d+(?:\.\d+)?)[：:]\s*(.+)$")
    reaction_pattern = re.compile(r"^(💡|✍️|🔍|⚡|🔗|🤫)(?:\s+.+)?$")
    emoji_map = {
        "💡": "highlight",
        "✍️": "association",
        "🔍": "curious",
        "⚡": "discern",
        "🔗": "connect_back",
        "🤫": "silent",
    }

    for line in lines:
        stripped = line.strip()
        section_match = section_pattern.match(stripped)
        if section_match:
            flush()
            section_ref = section_match.group(1)
            section_title = section_match.group(2).strip()
            continue
        reaction_match = reaction_pattern.match(stripped)
        if reaction_match:
            flush()
            current_type = emoji_map[reaction_match.group(1)]
            continue
        if not current_type:
            continue
        if re.match(r"^>\s*🔎\s*_(?:Search|搜索):", stripped):
            continue
        if re.match(r"^>\s*(?:Sources|参考|来源):", stripped):
            continue
        if stripped.startswith("> - "):
            continue
        if stripped.startswith(">"):
            quote_lines.append(stripped.lstrip(">").strip().strip('"'))
            continue
        if stripped == "---":
            flush()
            continue
        if stripped:
            note_lines.append(stripped)
    flush()
    return reactions


def load_segment_contexts(structure_path: Path, chapter_number: int) -> list[SegmentContext]:
    """Load chapter segment texts from structure.json."""
    structure = json.loads(structure_path.read_text(encoding="utf-8"))
    chapter = None
    for candidate in structure.get("chapters", []):
        if candidate.get("chapter_number") == chapter_number:
            chapter = candidate
            break
    if chapter is None:
        raise ValueError(f"在 {structure_path} 中找不到 Chapter {chapter_number}。")

    segments: list[SegmentContext] = []
    for index, segment in enumerate(chapter.get("segments", []), start=1):
        section_ref = display_segment_id(chapter, segment.get("id", ""))
        section_title = segment.get("summary", "")
        segments.append(
            SegmentContext(
                section_ref=section_ref,
                section_title=section_title,
                segment_text=segment.get("text", ""),
                order=index,
            )
        )
    return segments


def infer_structure_path(agent_output: Path) -> Path:
    """Infer the sibling structure.json path for one agent chapter output."""
    structure_path = agent_output.parent / "structure.json"
    if not structure_path.exists():
        raise FileNotFoundError(
            f"找不到 {structure_path}。请确认 agent output 位于 Iterator-Reader 输出目录中。"
        )
    return structure_path


def locate_highlight_segment(quote: str, segments: list[SegmentContext]) -> SegmentContext | None:
    """Locate the most likely segment containing a human highlight."""
    normalized_quote = normalize_text(quote)
    if not normalized_quote:
        return None

    best_segment = None
    best_score = -1.0
    for segment in segments:
        normalized_segment = normalize_text(segment.segment_text)
        if normalized_quote in normalized_segment:
            return segment
        score = fuzzy_ratio(quote, segment.segment_text)
        if score > best_score:
            best_score = score
            best_segment = segment
    return best_segment


def is_direct_match(human_quote: str, agent_quote: str, threshold: float = 70.0) -> tuple[bool, float, str]:
    """Check for direct textual match between a human highlight and an agent quote."""
    if not human_quote or not agent_quote:
        return False, 0.0, ""

    normalized_human = normalize_text(human_quote)
    normalized_agent = normalize_text(agent_quote)
    if normalized_human and normalized_agent and (
        normalized_human in normalized_agent or normalized_agent in normalized_human
    ):
        return True, 100.0, "文本包含"

    score = fuzzy_ratio(human_quote, agent_quote)
    if score >= threshold:
        return True, score, f"模糊匹配 {score:.1f}"
    return False, score, ""


def _neighbor_section_refs(section_hint: SegmentContext | None, segments: list[SegmentContext]) -> set[str]:
    """Return same-section and neighboring section refs for semantic matching."""
    if section_hint is None:
        return set()
    refs = {section_hint.section_ref}
    by_order = {segment.order: segment for segment in segments}
    for offset in (-1, 1):
        neighbor = by_order.get(section_hint.order + offset)
        if neighbor is not None:
            refs.add(neighbor.section_ref)
    return refs


def semantic_match(
    human: HumanHighlight,
    candidates: list[AgentReaction],
    section_hint: SegmentContext | None,
) -> tuple[AgentReaction | None, str]:
    """Use the LLM to judge concept-level match when text matching fails."""
    if not candidates:
        return None, ""

    best_fuzzy = max((fuzzy_ratio(human.quote, item.quote) for item in candidates), default=0.0)
    if best_fuzzy < 38:
        return None, ""

    payload = safe_invoke_json(
        SEMANTIC_MATCH_SYSTEM,
        SEMANTIC_MATCH_PROMPT.format(
            human_quote=human.quote,
            human_note=human.note or "（无）",
            section_hint=(
                f"Section {section_hint.section_ref}: {section_hint.section_title}"
                if section_hint is not None
                else "未知"
            ),
            candidates_json=json.dumps(
                [
                    {
                        "candidate_id": item.reaction_id,
                        "section": f"Section {item.section_ref}",
                        "type": item.reaction_type,
                        "quote": item.quote,
                        "note": item.note,
                    }
                    for item in candidates
                ],
                ensure_ascii=False,
                indent=2,
            ),
        ),
        default={"matched": False, "candidate_id": "", "reason": ""},
    )
    if not isinstance(payload, dict) or not payload.get("matched"):
        return None, str(payload.get("reason", "") or "")

    candidate_id = str(payload.get("candidate_id", "")).strip()
    for candidate in candidates:
        if candidate.reaction_id == candidate_id:
            return candidate, str(payload.get("reason", "") or "")
    return None, str(payload.get("reason", "") or "")


def diagnose_omission(
    human: HumanHighlight,
    section_hint: SegmentContext | None,
    local_reactions: list[AgentReaction],
) -> tuple[str, str]:
    """Classify why an omitted highlight may have been missed."""
    payload = safe_invoke_json(
        OMISSION_DIAGNOSIS_SYSTEM,
        OMISSION_DIAGNOSIS_PROMPT.format(
            human_quote=human.quote,
            human_note=human.note or "（无）",
            section_hint=(
                f"Section {section_hint.section_ref}: {section_hint.section_title}"
                if section_hint is not None
                else "未知"
            ),
            segment_text=(section_hint.segment_text[:3000] if section_hint is not None else "未知"),
            local_reactions_json=json.dumps(
                [
                    {
                        "section": f"Section {item.section_ref}",
                        "type": item.reaction_type,
                        "quote": item.quote,
                        "note": item.note,
                    }
                    for item in local_reactions
                ],
                ensure_ascii=False,
                indent=2,
            ),
        ),
        default={"category": "其他", "analysis": "无法完成 LLM 诊断。"},
    )
    category = str(payload.get("category", "其他") or "其他").strip()
    if category not in {"parse 分段问题", "感知密度不足", "角色盲区", "上下文依赖", "其他"}:
        category = "其他"
    analysis = str(payload.get("analysis", "") or "").strip() or "无法完成 LLM 诊断。"
    return category, analysis


def summarize_omissions(omissions: list[MatchResult], chapter_number: int) -> str:
    """Summarize omission patterns with a short LLM synthesis."""
    if not omissions:
        return "本章没有遗漏项，当前对比未暴露明显的系统性盲区。"

    counts: dict[str, int] = {}
    for item in omissions:
        counts[item.diagnosis_category] = counts.get(item.diagnosis_category, 0) + 1

    total = len(omissions)
    top_category, top_count = max(counts.items(), key=lambda pair: pair[1])
    lines = [
        f"{total} 个遗漏里，`{top_category}` 占主导（{top_count} 个）。",
    ]

    if counts.get("感知密度不足", 0):
        lines.append(
            "主要问题不是 Agent 完全没进入相关段落，而是进了段落后更容易抓住尖锐措辞、概念标签或争议点，"
            "却漏掉定义句、总结句和承上启下的结构节点。"
        )
    if counts.get("角色盲区", 0):
        lines.append(
            "次要盲区集中在修辞和语气层：隐喻、俗语、反讽、引用锚点，以及需要把分散句子串成完整因果链的地方，"
            "当前共读者角色还不够敏感。"
        )
    if counts.get("parse 分段问题", 0):
        lines.append(
            "分段本身也有少量影响，尤其是作者先抛出比喻、后展开机制时，Agent 可能只对后半段做出反应，"
            "从而错过概念首次被引入的关键时刻。"
        )
    if counts.get("上下文依赖", 0):
        lines.append(
            "如果后续章节里“上下文依赖”占比升高，需要把这部分视为合理差异，而不是简单归为系统缺陷。"
        )
    return "\n\n".join(lines)


def compare_highlights(
    human_highlights: list[HumanHighlight],
    agent_reactions: list[AgentReaction],
    segments: list[SegmentContext],
) -> list[MatchResult]:
    """Compare human highlights against agent reactions."""
    results: list[MatchResult] = []
    total = len(human_highlights)
    for index, human in enumerate(human_highlights, start=1):
        print(f"[{index}/{total}] 对比 {human.highlight_id}", flush=True)
        section_hint = locate_highlight_segment(human.quote, segments)

        best_direct: tuple[AgentReaction | None, float, str] = (None, 0.0, "")
        for reaction in agent_reactions:
            matched, score, reason = is_direct_match(human.quote, reaction.quote)
            if matched and score > best_direct[1]:
                best_direct = (reaction, score, reason)

        if best_direct[0] is not None:
            results.append(
                MatchResult(
                    human=human,
                    status="hit",
                    agent=best_direct[0],
                    match_reason=best_direct[2],
                    match_score=best_direct[1],
                    section_hint=section_hint,
                )
            )
            continue

        preferred_refs = _neighbor_section_refs(section_hint, segments)
        ranked_candidates = sorted(
            agent_reactions,
            key=lambda item: (
                item.section_ref in preferred_refs,
                fuzzy_ratio(human.quote, item.quote),
            ),
            reverse=True,
        )[:6]
        semantic_hit, semantic_reason = semantic_match(human, ranked_candidates, section_hint)
        if semantic_hit is not None:
            results.append(
                MatchResult(
                    human=human,
                    status="hit",
                    agent=semantic_hit,
                    match_reason=semantic_reason or "LLM 概念匹配",
                    match_score=fuzzy_ratio(human.quote, semantic_hit.quote),
                    section_hint=section_hint,
                )
            )
            continue

        local_refs = preferred_refs or {reaction.section_ref for reaction in ranked_candidates[:3]}
        local_reactions = [reaction for reaction in agent_reactions if reaction.section_ref in local_refs]
        print(f"  -> 遗漏诊断 {human.highlight_id}", flush=True)
        category, analysis = diagnose_omission(human, section_hint, local_reactions)
        results.append(
            MatchResult(
                human=human,
                status="miss",
                agent=None,
                match_reason=semantic_reason or "未命中",
                match_score=0.0,
                section_hint=section_hint,
                diagnosis_category=category,
                diagnosis_analysis=analysis,
            )
        )
    return results


def render_report(
    chapter_number: int,
    human_highlights: list[HumanHighlight],
    agent_reactions: list[AgentReaction],
    results: list[MatchResult],
) -> str:
    """Render the markdown comparison report."""
    hits = [item for item in results if item.status == "hit"]
    misses = [item for item in results if item.status == "miss"]
    matched_agent_ids = {item.agent.reaction_id for item in hits if item.agent is not None}
    agent_unique = [item for item in agent_reactions if item.reaction_id not in matched_agent_ids]

    lines = [f"# 高亮对比报告：Chapter {chapter_number}", ""]
    lines.extend(
        [
            "## 统计概览",
            "",
            f"- 人类高亮数：{len(human_highlights)}",
            f"- Agent 笔记数：{len(agent_reactions)}",
            f"- 命中：{len(hits)}",
            f"- 遗漏：{len(misses)}",
            f"- Agent 独有：{len(agent_unique)}",
            "",
        ]
    )

    lines.extend(["## ❌ 遗漏分析", ""])
    if not misses:
        lines.extend(["本章没有检测到遗漏项。", ""])
    else:
        for index, item in enumerate(misses, start=1):
            lines.append(f"### 遗漏 {index}")
            lines.append("")
            lines.append(f'> "{item.human.quote}"')
            lines.append("")
            if item.human.note:
                lines.append(f"- 我的批注：{item.human.note}")
            lines.append(
                "- 所在段落："
                + (
                    f"Section {item.section_hint.section_ref}: {item.section_hint.section_title}"
                    if item.section_hint is not None
                    else "未知"
                )
            )
            lines.append(f"- 诊断原因：{item.diagnosis_category}")
            lines.append(f"- 分析：{item.diagnosis_analysis}")
            lines.append("")

    category_counts: dict[str, int] = {}
    for item in misses:
        category_counts[item.diagnosis_category] = category_counts.get(item.diagnosis_category, 0) + 1

    lines.extend(["## 遗漏模式总结", ""])
    if category_counts:
        for category, count in sorted(category_counts.items(), key=lambda pair: (-pair[1], pair[0])):
            lines.append(f"- {category}：{count}")
        lines.append("")
    lines.append(summarize_omissions(misses, chapter_number))
    lines.append("")

    lines.extend(["## 🆕 Agent 独有发现（认知增量）", ""])
    if not agent_unique:
        lines.extend(["本章没有明显的 Agent 独有发现。", ""])
    else:
        for item in agent_unique:
            lines.append(f"### {item.reaction_type} / Section {item.section_ref}")
            lines.append("")
            if item.quote:
                lines.append(f'> "{item.quote}"')
                lines.append("")
            if item.note:
                lines.append(item.note)
                lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser for highlight comparison."""
    parser = argparse.ArgumentParser(description="Compare human highlights with Reader output.")
    parser.add_argument("--my-highlights", required=True, help="Path to the human highlight markdown file")
    parser.add_argument("--agent-output", required=True, help="Path to the rendered chapter markdown from the agent")
    parser.add_argument("--output", required=True, help="Where to write the markdown comparison report")
    parser.add_argument("--chapter", required=True, type=int, help="Chapter number to compare")
    parser.add_argument("--structure", help="Optional explicit path to structure.json")
    return parser


def main() -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    human_path = Path(args.my_highlights)
    if not human_path.exists():
        parser.error(
            f"{human_path} 不存在。请先准备人类高亮文件，再运行对比。"
        )

    agent_output_path = Path(args.agent_output)
    if not agent_output_path.exists():
        parser.error(f"{agent_output_path} 不存在。请先生成最新的 Agent Chapter 输出。")

    structure_path = Path(args.structure) if args.structure else infer_structure_path(agent_output_path)
    if not structure_path.exists():
        parser.error(f"{structure_path} 不存在。")

    human_highlights = parse_human_highlights(human_path, args.chapter)
    agent_reactions = parse_agent_reactions(agent_output_path)
    if not agent_reactions:
        parser.error(
            "未从 Agent 输出中解析到 reactions。"
            " 请确认该文件是最新的 Iterator-Reader 格式，而不是旧版固定 Pipeline 输出。"
        )

    segments = load_segment_contexts(structure_path, args.chapter)
    results = compare_highlights(human_highlights, agent_reactions, segments)
    report = render_report(args.chapter, human_highlights, agent_reactions, results)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"已生成对比报告：{output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

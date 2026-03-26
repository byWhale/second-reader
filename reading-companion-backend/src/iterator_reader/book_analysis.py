"""Book-level analysis mode with plan-and-execute orchestration."""

from __future__ import annotations

import json
import math
import re
from datetime import datetime
from pathlib import Path

from src.prompts.capabilities.book_analysis import BOOK_ANALYSIS_PROMPTS, BookAnalysisPromptSet
from src.tools.search import search_web

from .language import language_name
from .llm_utils import LLMTraceContext, invoke_json, invoke_text, llm_invocation_scope
from .models import (
    BookAnalysisPolicy,
    BookAnalysisState,
    BookStructure,
    BudgetPolicy,
    ClaimCard,
    ReaderMemory,
    RenderedSegment,
    SearchHit,
    SegmentSkimCard,
    SkillProfileName,
    StructureChapter,
)
from .policy import chapter_budget, resolve_skill_policy, segment_budget
from .reader import (
    create_reader_state,
    initial_memory,
    run_reader_segment_for_analysis,
    update_memory,
)
from .prompts import ITERATOR_V1_PROMPTS, IteratorV1PromptSet
from .storage import (
    analysis_plan_file,
    analysis_trace_file,
    append_jsonl,
    book_analysis_file,
    chapter_markdown_file,
    deep_dossiers_file,
    deep_targets_file,
    display_segment_id,
    evidence_checks_file,
    existing_chapter_markdown_file,
    save_json,
    segment_reference,
    segment_skim_cards_file,
)


LOW_VALUE_TITLES = {
    "preface",
    "prologue",
    "epilogue",
    "acknowledgments",
    "acknowledgements",
}
LOW_QUALITY_SOURCE_DOMAINS = {
    "reddit.com",
    "medium.com",
    "quora.com",
    "linkedin.com",
    "youtube.com",
    "news.ycombinator.com",
}
LOW_QUALITY_SOURCE_SUFFIXES = (
    ".reddit.com",
    ".medium.com",
    ".quora.com",
    ".linkedin.com",
)
HIGH_TRUST_SOURCE_DOMAINS = {
    "wikipedia.org",
    "nih.gov",
    "cdc.gov",
    "data.gov",
    "who.int",
    "oecd.org",
    "worldbank.org",
    "imf.org",
    "ourworldindata.org",
    "nature.com",
    "science.org",
    "sciencedirect.com",
    "springer.com",
    "link.springer.com",
    "jstor.org",
    "tandfonline.com",
    "cambridge.org",
    "oxfordacademic.com",
    "ssrn.com",
    "ncbi.nlm.nih.gov",
    "arxiv.org",
}


def _clean_text(value: object) -> str:
    text = str(value or "").strip()
    text = text.replace("\\n", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _normalize_score(value: object, default: int = 3) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        score = default
    return max(1, min(5, score))


def _normalize_list(value: object, limit: int | None = None) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        text = _clean_text(item)
        if text:
            items.append(text)
    if limit is None:
        return items
    return items[:limit]


def _is_low_value_chapter(chapter: StructureChapter) -> bool:
    return chapter.get("title", "").strip().lower() in LOW_VALUE_TITLES


def _fallback_skim_summary(text: str) -> str:
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if not lines:
        return ""
    merged = " ".join(lines)
    sentence = re.split(r"(?<=[.!?。！？])\s+", merged)[0].strip()
    return sentence[:280] if sentence else merged[:280]


def _claim_density(card: SegmentSkimCard) -> float:
    return min(1.0, len(card.get("candidate_claims", [])) / 3.0)


def _chapter_centrality(index: int, total: int) -> float:
    if total <= 1:
        return 1.0
    midpoint = (total + 1) / 2.0
    return max(0.0, 1.0 - abs((index + 1) - midpoint) / midpoint)


def _combine_segment_score(
    card: SegmentSkimCard,
    chapter_index: int,
    chapter_total: int,
) -> float:
    controversy = float(card.get("controversy_score", 3.0)) / 5.0
    intent_relevance = float(card.get("intent_relevance_score", 3.0)) / 5.0
    evidence_gap = float(card.get("evidence_gap_score", 3.0)) / 5.0
    return (
        0.30 * _claim_density(card)
        + 0.25 * _chapter_centrality(chapter_index, chapter_total)
        + 0.20 * controversy
        + 0.15 * intent_relevance
        + 0.10 * evidence_gap
    )


def _host_from_url(url: str) -> str:
    cleaned = _clean_text(url)
    if not cleaned:
        return ""
    host = cleaned.split("://", 1)[-1].split("/", 1)[0].strip().lower()
    host = host.split(":", 1)[0]
    if host.startswith("www."):
        host = host[4:]
    return host


def _host_matches(host: str, domain: str) -> bool:
    normalized = domain.strip().lower()
    if normalized.startswith("www."):
        normalized = normalized[4:]
    return host == normalized or host.endswith(f".{normalized}")


def _source_quality_tier(url: str) -> int:
    """Return source trust tier: 0=blocked, 1=neutral, 2=acceptable, 3=high-trust."""
    host = _host_from_url(url)
    if not host:
        return 0
    if any(_host_matches(host, domain) for domain in LOW_QUALITY_SOURCE_DOMAINS):
        return 0
    if any(host.endswith(suffix) for suffix in LOW_QUALITY_SOURCE_SUFFIXES):
        return 0
    if host.endswith(".edu") or host.endswith(".gov"):
        return 3
    if any(_host_matches(host, domain) for domain in HIGH_TRUST_SOURCE_DOMAINS):
        return 3
    if host.endswith(".org") or host.endswith(".ac.uk"):
        return 2
    return 1


def _is_high_quality_source(url: str, minimum_tier: int = 2) -> bool:
    return _source_quality_tier(url) >= minimum_tier


def _canonical_url(url: str) -> str:
    cleaned = _clean_text(url)
    if not cleaned:
        return ""
    return cleaned.rstrip("/").lower()


def _normalize_hit(item: object) -> SearchHit | None:
    if not isinstance(item, dict):
        return None
    title = _clean_text(item.get("title", "")) or _clean_text(item.get("url", ""))
    url = _clean_text(item.get("url", ""))
    snippet = _clean_text(item.get("snippet", "") or item.get("content", ""))
    if len(snippet) > 240:
        snippet = snippet[:237].rstrip() + "..."
    try:
        score = float(item.get("score")) if item.get("score") is not None else None
    except (TypeError, ValueError):
        score = None
    if not title:
        return None
    return {
        "title": title,
        "url": url,
        "snippet": snippet,
        "score": score,
    }


def _search(query: str, max_results: int = 3) -> list[SearchHit]:
    raw_limit = max(max_results, max_results * 5)
    try:
        payload = search_web.invoke({"query": query, "max_results": raw_limit})
    except Exception:
        return []
    if not isinstance(payload, list):
        return []
    candidates: list[tuple[int, float, SearchHit]] = []
    for item in payload:
        hit = _normalize_hit(item)
        if not hit:
            continue
        url = _clean_text(hit.get("url", ""))
        tier = _source_quality_tier(url)
        if tier <= 0:
            continue
        ranking = float(hit.get("score")) if hit.get("score") is not None else 0.0
        candidates.append((tier, ranking, hit))

    if not candidates:
        return []

    filtered = [item for item in candidates if item[0] >= 2]
    if not filtered:
        filtered = [item for item in candidates if item[0] >= 1]

    filtered.sort(key=lambda item: (item[0], item[1]), reverse=True)
    results: list[SearchHit] = []
    seen_urls: set[str] = set()
    for _tier, _score, hit in filtered:
        url = _clean_text(hit.get("url", ""))
        canonical = _canonical_url(url) if url else ""
        if canonical and canonical in seen_urls:
            continue
        if canonical:
            seen_urls.add(canonical)
        results.append(hit)
        if len(results) >= max_results:
            break
    return results


def _extract_links(text: str) -> list[SearchHit]:
    hits: list[SearchHit] = []
    for title, url in re.findall(r"\[([^\]]+)\]\((https?://[^)]+)\)", text):
        hits.append(
            {
                "title": _clean_text(title),
                "url": _clean_text(url),
                "snippet": "",
                "score": None,
            }
        )
    return hits


def _load_existing_section_notes(output_dir: Path, chapter: StructureChapter) -> dict[str, str]:
    markdown_path = existing_chapter_markdown_file(output_dir, chapter)
    if not markdown_path.exists():
        return {}
    text = markdown_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    section_regex = re.compile(r"^##\s+(?:Section|段落)\s+(\d+\.\d+)")
    notes: dict[str, str] = {}
    current_id = ""
    buffer: list[str] = []
    for line in lines:
        match = section_regex.match(line.strip())
        if match:
            if current_id and buffer:
                notes[current_id] = "\n".join(buffer).strip()
            current_id = match.group(1)
            buffer = []
            continue
        if line.strip() == "---":
            if current_id and buffer:
                notes[current_id] = "\n".join(buffer).strip()
            current_id = ""
            buffer = []
            continue
        if current_id:
            buffer.append(line)
    if current_id and buffer:
        notes[current_id] = "\n".join(buffer).strip()
    return notes


def _infer_claim_type(statement: str, order: int) -> str:
    lowered = statement.lower()
    if any(token in lowered for token in ["however", "but", "却", "但是", "相反", "矛盾"]):
        return "counter"
    if any(token in lowered for token in ["assume", "assumption", "前提", "默认", "假设"]):
        return "assumption"
    if order < 3:
        return "main"
    return "support"


def _derive_chapter_arc(
    chapters: list[StructureChapter],
    cards: list[SegmentSkimCard],
) -> list[dict[str, object]]:
    by_chapter: dict[int, list[SegmentSkimCard]] = {}
    for card in cards:
        by_chapter.setdefault(int(card.get("chapter_id", 0)), []).append(card)
    arc: list[dict[str, object]] = []
    for chapter in chapters:
        chapter_id = int(chapter.get("id", 0))
        chapter_cards = by_chapter.get(chapter_id, [])
        ranked = sorted(
            chapter_cards,
            key=lambda item: float(item.get("importance_score", 0.0)),
            reverse=True,
        )
        key_points = [
            _clean_text(item.get("skim_summary", ""))
            for item in ranked[:2]
            if _clean_text(item.get("skim_summary", ""))
        ]
        arc.append(
            {
                "chapter_id": chapter_id,
                "chapter_title": chapter.get("title", f"Chapter {chapter_id}"),
                "key_points": key_points,
            }
        )
    return arc


def _render_book_analysis(
    claim_cards: list[ClaimCard],
    chapter_arc: list[dict[str, object]],
    deep_dossiers: list[dict[str, object]],
) -> str:
    lines = ["# Book Analysis", ""]

    lines.extend(["## Core Thesis", ""])
    main_claim = next(
        (
            claim
            for claim in claim_cards
            if claim.get("claim_type") == "main"
        ),
        claim_cards[0] if claim_cards else None,
    )
    if main_claim:
        anchors = ", ".join(f"`{item}`" for item in main_claim.get("anchors", []))
        lines.append(f'- {main_claim.get("statement", "")} ({anchors})')
    else:
        lines.append("- No stable thesis was identified.")
    lines.append("")

    lines.extend(["## Argument Backbone", ""])
    if claim_cards:
        for claim in claim_cards:
            anchors = ", ".join(f"`{item}`" for item in claim.get("anchors", []))
            lines.append(
                f'- [{claim.get("claim_id", "")}] ({claim.get("claim_type", "support")}, {claim.get("evidence_status", "gap")}) '
                f'{claim.get("statement", "")}'
            )
            if anchors:
                lines.append(f"  anchors: {anchors}")
            sources = claim.get("sources", [])
            if sources:
                source_links = []
                for source in sources[:3]:
                    title = _clean_text(source.get("title", "")) or _clean_text(source.get("url", ""))
                    url = _clean_text(source.get("url", ""))
                    source_links.append(f"[{title}]({url})" if url else title)
                if source_links:
                    lines.append(f"  sources: {'; '.join(source_links)}")
    else:
        lines.append("- No claim cards were produced.")
    lines.append("")

    lines.extend(["## Chapter Arc", ""])
    if chapter_arc:
        for item in chapter_arc:
            chapter_title = _clean_text(item.get("chapter_title", ""))
            points = item.get("key_points", [])
            if not points:
                continue
            lines.append(f"- {chapter_title}")
            for point in points:
                lines.append(f"  - {point}")
    else:
        lines.append("- No chapter arc could be derived.")
    lines.append("")

    lines.extend(["## Tensions & Contradictions", ""])
    tensions = [
        claim
        for claim in claim_cards
        if claim.get("claim_type") in {"counter", "assumption"}
        or claim.get("evidence_status") == "disputed"
    ]
    if tensions:
        for claim in tensions[:10]:
            anchors = ", ".join(f"`{item}`" for item in claim.get("anchors", []))
            lines.append(f'- {claim.get("statement", "")} ({anchors})')
    else:
        lines.append("- No explicit cross-chapter contradiction was surfaced from current evidence.")
    lines.append("")

    lines.extend(["## Evidence Checkpoints", ""])
    if claim_cards:
        for claim in claim_cards:
            status = _clean_text(claim.get("evidence_status", "gap"))
            anchors = ", ".join(f"`{item}`" for item in claim.get("anchors", []))
            lines.append(f"- {status.upper()}: {claim.get('statement', '')} ({anchors})")
    else:
        lines.append("- No evidence checkpoints available.")
    lines.append("")

    lines.extend(["## Open Questions", ""])
    open_items: list[str] = []
    for claim in claim_cards:
        if claim.get("evidence_status") in {"gap", "disputed"}:
            open_items.append(_clean_text(claim.get("statement", "")))
    for dossier in deep_dossiers:
        if dossier.get("error"):
            open_items.append(_clean_text(dossier.get("error", "")))
    deduped: list[str] = []
    seen: set[str] = set()
    for item in open_items:
        key = item.casefold()
        if not item or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    if deduped:
        for item in deduped[:12]:
            lines.append(f"- {item}")
    else:
        lines.append("- No unresolved high-impact questions remain after current pass.")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _has_required_sections(markdown: str) -> bool:
    required = [
        "# Book Analysis",
        "## Core Thesis",
        "## Argument Backbone",
        "## Chapter Arc",
        "## Tensions & Contradictions",
        "## Evidence Checkpoints",
        "## Open Questions",
    ]
    return all(item in markdown for item in required)


def _synthesize_book_analysis_with_llm(
    user_intent: str | None,
    output_language: str,
    claim_cards: list[ClaimCard],
    chapter_arc: list[dict[str, object]],
    deep_dossiers: list[dict[str, object]],
    evidence_checks: list[dict[str, object]],
    prompt_set: BookAnalysisPromptSet = BOOK_ANALYSIS_PROMPTS,
) -> str:
    with llm_invocation_scope(
        trace_context=LLMTraceContext(stage="book_analysis", node="synthesis")
    ):
        payload = invoke_text(
            prompt_set.synthesis_system,
            prompt_set.synthesis_prompt.format(
                user_intent=user_intent or "Not specified",
                output_language_name=language_name(output_language),
                claim_cards_json=json.dumps(claim_cards, ensure_ascii=False, indent=2),
                chapter_arc_json=json.dumps(chapter_arc, ensure_ascii=False, indent=2),
                deep_dossiers_json=json.dumps(deep_dossiers, ensure_ascii=False, indent=2),
                evidence_checks_json=json.dumps(evidence_checks, ensure_ascii=False, indent=2),
            ),
            default="",
        ).strip()
    if not payload:
        return ""
    if not payload.startswith("#"):
        payload = "# Book Analysis\n\n" + payload
    if not payload.endswith("\n"):
        payload += "\n"
    if not _has_required_sections(payload):
        return ""
    return payload


def _should_use_llm_synthesis(
    claim_cards: list[ClaimCard],
    deep_dossiers: list[dict[str, object]],
    evidence_checks: list[dict[str, object]],
) -> bool:
    """Guard synthesis prompt size to avoid unstable long-running generations."""
    if len(claim_cards) > 16:
        return False
    if len(evidence_checks) > 10:
        return False
    approx_chars = (
        len(json.dumps(claim_cards, ensure_ascii=False))
        + len(json.dumps(deep_dossiers, ensure_ascii=False))
        + len(json.dumps(evidence_checks, ensure_ascii=False))
    )
    return approx_chars <= 26000


def run_book_analysis(
    structure: BookStructure,
    output_dir: Path,
    selected_chapters: list[StructureChapter],
    user_intent: str | None,
    skill_profile: SkillProfileName,
    budget_policy: BudgetPolicy,
    analysis_policy: BookAnalysisPolicy,
    prompt_set: BookAnalysisPromptSet = BOOK_ANALYSIS_PROMPTS,
    reader_prompt_set: IteratorV1PromptSet = ITERATOR_V1_PROMPTS,
) -> tuple[BookStructure, BookAnalysisState]:
    """Run book-level plan-and-execute analysis and persist intermediate artifacts."""
    def emit_status(message: str) -> None:
        print(message, flush=True)

    def emit_deep_progress(display_segment: str, message: str) -> None:
        emit_status(f"  ├─ [book_analysis][{display_segment}] {message}")

    def short_summary(text: str, limit: int = 18) -> str:
        cleaned = _clean_text(text)
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[:limit].rstrip() + "..."

    output_language = structure.get("output_language", "en")
    skim_cards: list[SegmentSkimCard] = []
    trace_path = analysis_trace_file(output_dir)
    skim_cards_path = segment_skim_cards_file(output_dir)
    deep_targets_path = deep_targets_file(output_dir)
    deep_dossiers_path = deep_dossiers_file(output_dir)
    plan_path = analysis_plan_file(output_dir)
    evidence_path = evidence_checks_file(output_dir)
    report_path = book_analysis_file(output_dir)

    # Reset artifact files for one deterministic run.
    for artifact in [trace_path, skim_cards_path, deep_targets_path, deep_dossiers_path, plan_path, evidence_path]:
        artifact.parent.mkdir(parents=True, exist_ok=True)
        if artifact.suffix == ".jsonl":
            artifact.write_text("", encoding="utf-8")

    ordered_chapters = list(selected_chapters)
    total_segments = sum(len(chapter.get("segments", [])) for chapter in ordered_chapters)
    append_jsonl(
        trace_path,
        {
            "phase": "skim_start",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "chapters": len(ordered_chapters),
            "segments": total_segments,
        },
    )
    emit_status(f"[book_analysis] Phase A skim: {len(ordered_chapters)} chapters / {total_segments} segments")

    chapter_index_by_id = {
        int(chapter.get("id", 0)): index
        for index, chapter in enumerate(ordered_chapters)
    }

    for chapter in ordered_chapters:
        chapter_id = int(chapter.get("id", 0))
        for segment in chapter.get("segments", []):
            segment_id = _clean_text(segment.get("id", ""))
            segment_ref = _clean_text(segment.get("segment_ref", "")) or segment_reference(chapter, segment_id)
            segment_summary = _clean_text(segment.get("summary", ""))
            segment_text = _clean_text(segment.get("text", ""))
            fallback = False
            payload: object = {}
            try:
                with llm_invocation_scope(
                    trace_context=LLMTraceContext(stage="book_analysis", node="skim")
                ):
                    payload = invoke_json(
                        prompt_set.skim_system,
                        prompt_set.skim_prompt.format(
                            chapter_title=chapter.get("title", ""),
                            segment_ref=segment_ref,
                            segment_summary=segment_summary,
                            user_intent=user_intent or "Not specified",
                            segment_text=segment_text[:7000],
                            output_language_name=language_name(output_language),
                        ),
                        default={},
                    )
            except Exception:
                payload = {}
                fallback = True
            if not isinstance(payload, dict):
                payload = {}
                fallback = True

            skim_summary = _clean_text(payload.get("skim_summary", ""))
            if not skim_summary:
                skim_summary = _fallback_skim_summary(segment_text)
                fallback = True

            card: SegmentSkimCard = {
                "chapter_id": chapter_id,
                "segment_id": segment_id,
                "segment_ref": segment_ref,
                "segment_summary": segment_summary,
                "skim_summary": skim_summary,
                "candidate_claims": _normalize_list(payload.get("candidate_claims"), 4),
                "importance_score": float(_normalize_score(payload.get("importance_score", 3))),
                "controversy_score": float(_normalize_score(payload.get("controversy_score", 3))),
                "evidence_gap_score": float(_normalize_score(payload.get("evidence_gap_score", 3))),
                "intent_relevance_score": float(_normalize_score(payload.get("intent_relevance_score", 3))),
                "needs_deep_read": bool(payload.get("needs_deep_read", False)),
                "reason": _clean_text(payload.get("reason", "")) or "skim_default",
            }
            if fallback:
                card["fallback"] = True
            skim_cards.append(card)
            append_jsonl(skim_cards_path, card)

    append_jsonl(
        trace_path,
        {
            "phase": "skim_done",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "skim_cards": len(skim_cards),
        },
    )

    emit_status("[book_analysis] Phase B planning")
    ranked_segments: list[dict[str, object]] = []
    for card in skim_cards:
        chapter_id = int(card.get("chapter_id", 0))
        chapter_index = chapter_index_by_id.get(chapter_id, 0)
        score = _combine_segment_score(card, chapter_index, len(ordered_chapters))
        ranked_segments.append(
            {
                "chapter_id": chapter_id,
                "segment_id": _clean_text(card.get("segment_id", "")),
                "segment_ref": _clean_text(card.get("segment_ref", "")),
                "score": score,
                "needs_deep_read": bool(card.get("needs_deep_read", False)),
                "reason": _clean_text(card.get("reason", "")),
            }
        )

    ranked_segments.sort(
        key=lambda item: (
            1 if bool(item.get("needs_deep_read", False)) else 0,
            float(item.get("score", 0.0)),
        ),
        reverse=True,
    )
    total_target = max(
        1,
        math.ceil(len(skim_cards) * max(0.0, float(analysis_policy.get("deep_target_ratio", 0.30)))),
    )

    selected_target_keys: set[tuple[int, str]] = set()
    deep_targets: list[dict[str, object]] = []
    min_per_chapter = max(0, int(analysis_policy.get("min_deep_per_chapter", 1)))
    for chapter in ordered_chapters:
        if _is_low_value_chapter(chapter):
            continue
        chapter_id = int(chapter.get("id", 0))
        chapter_candidates = [
            item
            for item in ranked_segments
            if int(item.get("chapter_id", 0)) == chapter_id
        ]
        for candidate in chapter_candidates[:min_per_chapter]:
            key = (chapter_id, _clean_text(candidate.get("segment_id", "")))
            if key in selected_target_keys:
                continue
            selected_target_keys.add(key)
            deep_targets.append(candidate)

    for candidate in ranked_segments:
        key = (int(candidate.get("chapter_id", 0)), _clean_text(candidate.get("segment_id", "")))
        if key in selected_target_keys:
            continue
        deep_targets.append(candidate)
        selected_target_keys.add(key)
        if len(deep_targets) >= total_target:
            break

    mandatory_count = len(deep_targets)
    total_target = max(total_target, mandatory_count)
    deep_targets = deep_targets[:total_target]

    deep_target_map = {
        (int(item.get("chapter_id", 0)), _clean_text(item.get("segment_id", ""))): item
        for item in deep_targets
    }
    for card in skim_cards:
        key = (int(card.get("chapter_id", 0)), _clean_text(card.get("segment_id", "")))
        card["needs_deep_read"] = key in deep_target_map

    # Build claim cards from skim candidate claims.
    claim_pool: dict[str, dict[str, object]] = {}
    for card in sorted(
        skim_cards,
        key=lambda item: float(item.get("importance_score", 0.0)),
        reverse=True,
    ):
        chapter_id = int(card.get("chapter_id", 0))
        segment_id = _clean_text(card.get("segment_id", ""))
        segment_ref = _clean_text(card.get("segment_ref", ""))
        chapter = next((item for item in ordered_chapters if int(item.get("id", 0)) == chapter_id), None)
        if not chapter:
            continue
        anchor = segment_ref or display_segment_id(chapter, segment_id)
        source_score = float(card.get("importance_score", 3.0)) / 5.0
        evidence_gap = float(card.get("evidence_gap_score", 3.0))
        controversy = float(card.get("controversy_score", 3.0))
        for claim in card.get("candidate_claims", []):
            normalized_key = re.sub(r"\s+", " ", claim.strip().casefold())
            if not normalized_key:
                continue
            entry = claim_pool.setdefault(
                normalized_key,
                {
                    "statement": claim.strip(),
                    "anchors": set(),
                    "max_score": source_score,
                    "evidence_gap": evidence_gap,
                    "controversy": controversy,
                },
            )
            entry["anchors"].add(anchor)
            entry["max_score"] = max(float(entry.get("max_score", 0.0)), source_score)
            entry["evidence_gap"] = max(float(entry.get("evidence_gap", 0.0)), evidence_gap)
            entry["controversy"] = max(float(entry.get("controversy", 0.0)), controversy)

    sorted_claim_entries = sorted(
        claim_pool.values(),
        key=lambda item: float(item.get("max_score", 0.0)),
        reverse=True,
    )[: max(1, int(analysis_policy.get("max_core_claims", 20)))]

    claim_cards: list[ClaimCard] = []
    for index, entry in enumerate(sorted_claim_entries, start=1):
        evidence_gap = float(entry.get("evidence_gap", 3.0))
        controversy = float(entry.get("controversy", 3.0))
        if evidence_gap >= 4.0:
            evidence_status = "gap"
        elif controversy >= 4.0:
            evidence_status = "disputed"
        else:
            evidence_status = "covered"
        statement = _clean_text(entry.get("statement", ""))
        claim_cards.append(
            {
                "claim_id": f"claim_{index:03d}",
                "statement": statement,
                "claim_type": _infer_claim_type(statement, index - 1),  # type: ignore[typeddict-item]
                "anchors": sorted(_normalize_list(list(entry.get("anchors", [])), None)),
                "confidence": round(float(entry.get("max_score", 0.6)), 3),
                "evidence_status": evidence_status,  # type: ignore[typeddict-item]
                "search_queries": [],
                "sources": [],
            }
        )

    max_web_queries = max(0, int(analysis_policy.get("max_web_queries", 18)))
    max_queries_per_claim = max(1, int(analysis_policy.get("max_queries_per_claim", 2)))
    total_query_slots = max_web_queries
    web_tasks: list[dict[str, object]] = []

    for claim in claim_cards:
        if total_query_slots <= 0:
            break
        if claim.get("evidence_status") not in {"gap", "disputed"}:
            continue
        max_queries = min(max_queries_per_claim, total_query_slots)
        payload: object = {}
        try:
            with llm_invocation_scope(
                trace_context=LLMTraceContext(stage="book_analysis", node="query_generation")
            ):
                payload = invoke_json(
                    prompt_set.query_system,
                    prompt_set.query_prompt.format(
                        claim_statement=claim.get("statement", ""),
                        evidence_status=claim.get("evidence_status", "gap"),
                        max_queries=max_queries,
                    ),
                    default={},
                )
        except Exception:
            payload = {}
        queries = []
        if isinstance(payload, dict):
            queries = _normalize_list(payload.get("queries"), max_queries)
        if not queries:
            queries = [f"{claim.get('statement', '')} evidence"][:max_queries]
        queries = [query for query in queries if query][:max_queries]
        if not queries:
            continue
        web_tasks.append({"claim_id": claim.get("claim_id", ""), "queries": queries})
        total_query_slots -= len(queries)

    save_json(deep_targets_path, {"targets": deep_targets})
    save_json(
        plan_path,
        {
            "policy": analysis_policy,
            "total_segments": len(skim_cards),
            "deep_target_count": len(deep_targets),
            "deep_targets": deep_targets,
            "claim_cards": claim_cards,
            "web_tasks": web_tasks,
        },
    )
    append_jsonl(
        trace_path,
        {
            "phase": "plan_done",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "deep_targets": len(deep_targets),
            "claim_cards": len(claim_cards),
            "web_tasks": len(web_tasks),
        },
    )

    emit_status(f"[book_analysis] Phase C execute: deep_targets={len(deep_targets)} web_tasks={len(web_tasks)}")
    skill = resolve_skill_policy(skill_profile)
    memory: ReaderMemory = initial_memory()
    deep_dossiers: list[dict[str, object]] = []
    existing_notes_by_chapter: dict[int, dict[str, str]] = {}
    reuse_existing = bool(analysis_policy.get("reuse_existing_notes", True))
    for chapter in ordered_chapters:
        existing_notes_by_chapter[int(chapter.get("id", 0))] = _load_existing_section_notes(output_dir, chapter)

    chapter_budget_state = chapter_budget(budget_policy)
    for item in deep_targets:
        chapter_id = int(item.get("chapter_id", 0))
        segment_id = _clean_text(item.get("segment_id", ""))
        chapter = next((entry for entry in ordered_chapters if int(entry.get("id", 0)) == chapter_id), None)
        if not chapter:
            continue
        segment = next(
            (
                entry
                for entry in chapter.get("segments", [])
                if _clean_text(entry.get("id", "")) == segment_id
            ),
            None,
        )
        if not segment:
            continue

        shown_id = (
            _clean_text(item.get("segment_ref", ""))
            or _clean_text(segment.get("segment_ref", ""))
            or segment_reference(chapter, segment_id)
        )
        existing_note = existing_notes_by_chapter.get(chapter_id, {}).get(shown_id, "")
        if reuse_existing and len(_clean_text(existing_note)) >= 80:
            source_links = _extract_links(existing_note)[:4]
            emit_deep_progress(shown_id, "♻️ 复用已有章节笔记")
            dossier = {
                "chapter_id": chapter_id,
                "segment_id": segment_id,
                "segment_ref": shown_id,
                "display_segment_id": shown_id,
                "reused": True,
                "summary": _clean_text(segment.get("summary", "")),
                "evidence_anchor": shown_id,
                "source_links": source_links,
                "source_count": len(source_links),
            }
            deep_dossiers.append(dossier)
            append_jsonl(trace_path, {"phase": "deep_reuse", "chapter_id": chapter_id, "segment_id": segment_id})
            continue

        try:
            emit_deep_progress(
                shown_id,
                f'📖 深读「{short_summary(_clean_text(segment.get("summary", "")))}」...',
            )

            state = create_reader_state(
                chapter_title=chapter.get("title", ""),
                segment_id=segment_id,
                segment_ref=shown_id,
                segment_summary=_clean_text(segment.get("summary", "")),
                segment_text=_clean_text(segment.get("text", "")),
                memory=memory,
                output_language=output_language,
                user_intent=user_intent,
                skill_policy=skill,
                budget=segment_budget(chapter_budget_state, budget_policy),
                max_revisions=int(budget_policy.get("max_revisions", 2)),
                prompt_set=reader_prompt_set,
            )
            rendered, _final_state = run_reader_segment_for_analysis(
                state,
                progress=lambda message, shown_id=shown_id: emit_deep_progress(shown_id, message),
            )
            memory = update_memory(memory, rendered)
            sources: list[SearchHit] = []
            for reaction in rendered.get("reactions", []):
                for source in reaction.get("search_results", []):
                    if source not in sources:
                        sources.append(source)
            dossier = {
                "chapter_id": chapter_id,
                "segment_id": segment_id,
                "segment_ref": shown_id,
                "display_segment_id": shown_id,
                "reused": False,
                "summary": _clean_text(rendered.get("summary", "")),
                "verdict": _clean_text(rendered.get("verdict", "skip")),
                "reflection_summary": _clean_text(rendered.get("reflection_summary", "")),
                "reaction_count": len(rendered.get("reactions", [])),
                "sources": sources[:4],
            }
            deep_dossiers.append(dossier)
            append_jsonl(trace_path, {"phase": "deep_read", "chapter_id": chapter_id, "segment_id": segment_id})
        except Exception as exc:
            deep_dossiers.append(
                {
                    "chapter_id": chapter_id,
                    "segment_id": segment_id,
                    "segment_ref": shown_id,
                    "display_segment_id": shown_id,
                    "reused": False,
                    "error": str(exc),
                }
            )
            append_jsonl(
                trace_path,
                {
                    "phase": "deep_read_error",
                    "chapter_id": chapter_id,
                    "segment_id": segment_id,
                    "error": str(exc),
                },
            )

    save_json(deep_dossiers_path, {"dossiers": deep_dossiers})

    claim_by_id: dict[str, ClaimCard] = {str(claim.get("claim_id", "")): claim for claim in claim_cards}
    evidence_checks: list[dict[str, object]] = []
    for task in web_tasks:
        claim_id = _clean_text(task.get("claim_id", ""))
        claim = claim_by_id.get(claim_id)
        if not claim:
            continue
        queries = _normalize_list(task.get("queries"), max_queries_per_claim)
        for query in queries:
            hits = _search(query, max_results=3)
            best_source_tier = max((_source_quality_tier(hit.get("url", "")) for hit in hits), default=0)
            high_quality_hits = [
                hit
                for hit in hits
                if _is_high_quality_source(hit.get("url", ""), minimum_tier=2)
            ]
            evidence_record = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "claim_id": claim_id,
                "query": query,
                "hits": hits,
                "high_quality_hits": len(high_quality_hits),
                "best_source_tier": best_source_tier,
            }
            evidence_checks.append(evidence_record)
            append_jsonl(
                evidence_path,
                evidence_record,
            )
            claim["search_queries"] = list(claim.get("search_queries", [])) + [query]
            existing_sources = list(claim.get("sources", []))
            seen_urls = {item.get("url", "") for item in existing_sources}
            source_candidates = high_quality_hits or hits[:1]
            for hit in source_candidates:
                url = hit.get("url", "")
                if url and url in seen_urls:
                    continue
                existing_sources.append(hit)
                if url:
                    seen_urls.add(url)
            claim["sources"] = existing_sources[:8]
            if high_quality_hits and claim.get("evidence_status") == "gap":
                claim["evidence_status"] = "covered"  # type: ignore[typeddict-item]
            append_jsonl(
                trace_path,
                {"phase": "evidence_query", "claim_id": claim_id, "query": query, "hits": len(hits)},
            )

    for claim in claim_cards:
        if claim.get("evidence_status") in {"gap", "disputed"} and not claim.get("sources"):
            claim["insufficient_evidence"] = True

    chapter_arc = _derive_chapter_arc(ordered_chapters, skim_cards)
    report_markdown = ""
    if _should_use_llm_synthesis(claim_cards, deep_dossiers, evidence_checks):
        try:
            report_markdown = _synthesize_book_analysis_with_llm(
                user_intent=user_intent,
                output_language=output_language,
                claim_cards=claim_cards,
                chapter_arc=chapter_arc,
                deep_dossiers=deep_dossiers,
                evidence_checks=evidence_checks,
                prompt_set=prompt_set,
            )
        except Exception:
            report_markdown = ""
    if not report_markdown:
        report_markdown = _render_book_analysis(claim_cards, chapter_arc, deep_dossiers)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_markdown, encoding="utf-8")
    append_jsonl(
        trace_path,
        {
            "phase": "synthesis_done",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "report_file": str(report_path.name),
            "output_language": language_name(output_language),
        },
    )
    emit_status(f"[book_analysis] Phase D synthesis: saved {report_path.name}")

    state: BookAnalysisState = {
        "skim_cards": skim_cards,
        "claim_cards": claim_cards,
        "deep_targets": deep_targets,
        "web_tasks": web_tasks,
        "deep_dossiers": deep_dossiers,
        "chapter_arc": chapter_arc,
        "report_payload": {
            "report_file": report_path.name,
            "claim_count": len(claim_cards),
        },
    }
    return structure, state

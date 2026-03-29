"""Question-aligned case construction helpers for attentional_v2 datasets."""

from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
import re
from typing import Any, Callable


TARGET_PROFILE_FLOOR_REVIEWED_ACTIVE = 2
TARGET_PROFILE_FLOOR_RESERVE = 1
TARGET_PROFILE_ORDER = (
    "distinction_definition",
    "tension_reversal",
    "callback_bridge",
    "anchored_reaction_selectivity",
    "reconsolidation_later_reinterpretation",
)

EXCERPT_TARGET_PROFILES = {
    "distinction_definition": {
        "target_profile_id": "distinction_definition",
        "question_ids": ["EQ-CM-002", "EQ-AV2-002", "EQ-AV2-005"],
        "phenomena": ["distinction", "definition_pressure", "anchored_reaction"],
        "selection_reason_template": "Selected because the passage turns on a distinction or definition that a strong reader should close around precisely.",
        "judge_focus_template": "Does the mechanism identify the distinction cleanly and keep the reading move answerable to the passage?",
        "preferred_roles": ("expository", "argumentative"),
        "preferred_positions": ("early", "middle"),
        "en_cues": ("rather than", "instead of", "means", "defined", "definition", "difference between", "not merely"),
        "zh_cues": ("而不是", "不是", "意味着", "定义", "区别", "并非"),
        "radius_en": 1,
        "radius_zh": 1,
    },
    "tension_reversal": {
        "target_profile_id": "tension_reversal",
        "question_ids": ["EQ-CM-002", "EQ-AV2-003", "EQ-AV2-005"],
        "phenomena": ["tension_reversal", "controller_move_quality", "anchored_reaction"],
        "selection_reason_template": "Selected because the passage contains a pressure point or reversal that should reward a proportionate, text-grounded move.",
        "judge_focus_template": "Does the mechanism stay with the reversal or tension instead of flattening it into generic summary?",
        "preferred_roles": ("argumentative", "narrative_reflective"),
        "preferred_positions": ("middle", "late"),
        "en_cues": ("but", "however", "yet", "still", "instead", "despite", "although", "turns out"),
        "zh_cues": ("但", "但是", "然而", "却", "反而", "不过", "其实"),
        "radius_en": 1,
        "radius_zh": 1,
    },
    "callback_bridge": {
        "target_profile_id": "callback_bridge",
        "question_ids": ["EQ-CM-002", "EQ-CM-004", "EQ-AV2-004"],
        "phenomena": ["bridge_potential", "callback", "cross_span_link"],
        "selection_reason_template": "Selected because the passage invites a backward bridge or callback that should remain source-grounded rather than associative.",
        "judge_focus_template": "Does the mechanism connect the current line to earlier material honestly and for the right reason?",
        "preferred_roles": ("argumentative", "reference_heavy", "narrative_reflective"),
        "preferred_positions": ("middle", "late"),
        "en_cues": ("again", "still", "once more", "earlier", "before", "same", "return", "returns"),
        "zh_cues": ("再次", "仍然", "之前", "前面", "同样", "回到", "又"),
        "radius_en": 2,
        "radius_zh": 1,
    },
    "anchored_reaction_selectivity": {
        "target_profile_id": "anchored_reaction_selectivity",
        "question_ids": ["EQ-CM-002", "EQ-AV2-005"],
        "phenomena": ["reaction_anchor", "selective_legibility", "visible_thought"],
        "selection_reason_template": "Selected because the passage contains a line that seems reaction-worthy but still demands selective, anchored reading.",
        "judge_focus_template": "Is the visible reaction anchored to the actual line and genuinely worth preserving?",
        "preferred_roles": ("expository", "argumentative", "narrative_reflective", "reference_heavy"),
        "preferred_positions": ("early", "middle", "late"),
        "en_cues": ("?", "!", "suddenly", "strange", "remarkable", "curious", "why"),
        "zh_cues": ("？", "！", "忽然", "奇怪", "惊人", "为什么"),
        "radius_en": 1,
        "radius_zh": 1,
    },
    "reconsolidation_later_reinterpretation": {
        "target_profile_id": "reconsolidation_later_reinterpretation",
        "question_ids": ["EQ-CM-004", "EQ-AV2-006"],
        "phenomena": ["reconsolidation_candidate", "later_reinterpretation", "durable_trace_candidate"],
        "selection_reason_template": "Selected because the passage looks like something that could matter differently later and should be preserved as a durable trace candidate.",
        "judge_focus_template": "Does the mechanism preserve what would make this line worth returning to later?",
        "preferred_roles": ("narrative_reflective", "reference_heavy"),
        "preferred_positions": ("late",),
        "en_cues": ("later", "only then", "afterward", "at last", "remembered", "would matter"),
        "zh_cues": ("后来", "直到", "这才", "终于", "想起", "原来"),
        "radius_en": 2,
        "radius_zh": 1,
    },
}

LEGACY_PHENOMENA_TO_TARGET = {
    "distinction": "distinction_definition",
    "definition_pressure": "distinction_definition",
    "tension_reversal": "tension_reversal",
    "controller_move_quality": "tension_reversal",
    "bridge_potential": "callback_bridge",
    "callback": "callback_bridge",
    "cross_span_link": "callback_bridge",
    "reaction_anchor": "anchored_reaction_selectivity",
    "selective_legibility": "anchored_reaction_selectivity",
    "visible_thought": "anchored_reaction_selectivity",
    "anchored_reaction": "anchored_reaction_selectivity",
    "reconsolidation_candidate": "reconsolidation_later_reinterpretation",
    "later_reinterpretation": "reconsolidation_later_reinterpretation",
    "durable_trace_candidate": "reconsolidation_later_reinterpretation",
}

DocumentLoader = Callable[[Path], dict[str, Any]]


def excerpt_target_profiles() -> list[dict[str, Any]]:
    """Return the stable ordered target-profile list for excerpt construction."""

    return [deepcopy(EXCERPT_TARGET_PROFILES[target_id]) for target_id in TARGET_PROFILE_ORDER]


def target_profile_id_for_case_row(row: dict[str, Any]) -> str:
    """Resolve one row's target profile, including legacy case rows."""

    explicit = str(row.get("target_profile_id", "")).strip()
    if explicit in EXCERPT_TARGET_PROFILES:
        return explicit

    case_id = str(row.get("case_id", "")).strip()
    for profile_id in TARGET_PROFILE_ORDER:
        if profile_id in case_id:
            return profile_id

    for phenomenon in row.get("phenomena", []) or []:
        resolved = LEGACY_PHENOMENA_TO_TARGET.get(str(phenomenon).strip())
        if resolved:
            return resolved
    return ""


def summarize_existing_case_feedback(
    existing_rows_by_language: dict[str, list[dict[str, Any]]] | None,
) -> dict[str, dict[str, Any]]:
    """Summarize the currently visible dataset-review truth by language/profile."""

    summary: dict[str, dict[str, Any]] = {}
    for language in ("en", "zh"):
        rows = list((existing_rows_by_language or {}).get(language, []))
        profile_counts = {
            profile_id: {
                "reviewed_active": 0,
                "needs_revision": 0,
                "needs_replacement": 0,
                "needs_adjudication": 0,
                "unset": 0,
                "other": 0,
            }
            for profile_id in TARGET_PROFILE_ORDER
        }
        status_counts = Counter()
        for row in rows:
            status = str(row.get("benchmark_status", "")).strip() or "unset"
            status_counts[status] += 1
            profile_id = target_profile_id_for_case_row(row)
            if not profile_id:
                continue
            bucket = status if status in profile_counts[profile_id] else "other"
            profile_counts[profile_id][bucket] += 1
        summary[language] = {
            "row_count": len(rows),
            "reviewed_active_total": int(status_counts.get("reviewed_active", 0)),
            "open_status_counts": {
                "needs_revision": int(status_counts.get("needs_revision", 0)),
                "needs_replacement": int(status_counts.get("needs_replacement", 0)),
                "needs_adjudication": int(status_counts.get("needs_adjudication", 0)),
                "unset": int(status_counts.get("unset", 0)),
            },
            "profiles": profile_counts,
        }
    return summary


def build_question_aligned_excerpt_scope(
    chapter_rows_by_language: dict[str, list[dict[str, Any]]],
    source_index: dict[str, dict[str, Any]],
    *,
    existing_rows_by_language: dict[str, list[dict[str, Any]]] | None = None,
    root: Path,
    document_loader: DocumentLoader,
    scope_id: str,
    cases_per_chapter: int = 1,
    reserves_per_chapter: int = 1,
) -> dict[str, Any]:
    """Build opportunity cards, candidate cases, reserves, and adequacy for one excerpt scope."""

    feedback_summary = summarize_existing_case_feedback(existing_rows_by_language)
    opportunities_by_language: dict[str, list[dict[str, Any]]] = defaultdict(list)
    all_opportunities: list[dict[str, Any]] = []

    for language, chapter_rows in chapter_rows_by_language.items():
        for row in chapter_rows:
            source = source_index[str(row["source_id"])]
            output_dir = root / str(row["output_dir"])
            document = document_loader(output_dir)
            chapter = next(
                (candidate for candidate in document.get("chapters", []) if str(candidate.get("id")) == str(row["chapter_id"])),
                None,
            )
            if not chapter:
                continue
            chapter_opportunities = _build_opportunity_cards_for_chapter(
                row=row,
                source=source,
                chapter=chapter,
                feedback=feedback_summary.get(language, {}),
            )
            opportunities_by_language[language].extend(chapter_opportunities)
            all_opportunities.extend(chapter_opportunities)

    cases_by_language: dict[str, list[dict[str, Any]]] = {}
    reserves_by_language: dict[str, list[dict[str, Any]]] = {}
    for language in ("en", "zh"):
        cases, reserves = _select_cases_and_reserves(
            opportunities_by_language.get(language, []),
            cases_per_chapter=cases_per_chapter,
            reserves_per_chapter=reserves_per_chapter,
        )
        cases_by_language[language] = cases
        reserves_by_language[language] = reserves

    adequacy_report = build_excerpt_adequacy_report(
        scope_id=scope_id,
        existing_rows_by_language=existing_rows_by_language or {},
        candidate_cases_by_language=cases_by_language,
        reserve_cases_by_language=reserves_by_language,
    )
    return {
        "scope_id": scope_id,
        "target_profiles": excerpt_target_profiles(),
        "feedback_summary": feedback_summary,
        "opportunity_cards": sorted(
            all_opportunities,
            key=lambda item: (
                str(item["language_track"]),
                str(item["chapter_case_id"]),
                -float(item["construction_priority"]),
                str(item["target_profile_ids"][0]),
            ),
        ),
        "cases_by_language": cases_by_language,
        "reserve_cases_by_language": reserves_by_language,
        "adequacy_report": adequacy_report,
    }


def build_excerpt_adequacy_report(
    *,
    scope_id: str,
    existing_rows_by_language: dict[str, list[dict[str, Any]]],
    candidate_cases_by_language: dict[str, list[dict[str, Any]]],
    reserve_cases_by_language: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Build an adequacy report that the later unattended loop can consume."""

    existing_summary = summarize_existing_case_feedback(existing_rows_by_language)
    target_profile_coverage: dict[str, dict[str, dict[str, int]]] = {}
    reserve_depth: dict[str, dict[str, int]] = {}
    source_diversity: dict[str, dict[str, int]] = {}
    deficits: list[dict[str, Any]] = []
    open_status_counts: dict[str, dict[str, int]] = {}
    reviewed_active_counts: dict[str, int] = {}

    for language in ("en", "zh"):
        existing_rows = list(existing_rows_by_language.get(language, []))
        candidate_rows = list(candidate_cases_by_language.get(language, []))
        reserve_rows = list(reserve_cases_by_language.get(language, []))
        reviewed_active_counts[language] = int(existing_summary[language]["reviewed_active_total"])
        open_status_counts[language] = dict(existing_summary[language]["open_status_counts"])
        source_diversity[language] = {
            "existing_sources": len({str(row.get("source_id", "")) for row in existing_rows if str(row.get("source_id", "")).strip()}),
            "candidate_sources": len({str(row.get("source_id", "")) for row in candidate_rows if str(row.get("source_id", "")).strip()}),
            "reserve_sources": len({str(row.get("source_id", "")) for row in reserve_rows if str(row.get("source_id", "")).strip()}),
        }
        reserve_depth[language] = {
            profile_id: sum(1 for row in reserve_rows if str(row.get("target_profile_id", "")) == profile_id)
            for profile_id in TARGET_PROFILE_ORDER
        }
        target_profile_coverage[language] = {}
        for profile_id in TARGET_PROFILE_ORDER:
            existing_counts = existing_summary[language]["profiles"][profile_id]
            candidate_count = sum(1 for row in candidate_rows if str(row.get("target_profile_id", "")) == profile_id)
            reserve_count = sum(1 for row in reserve_rows if str(row.get("target_profile_id", "")) == profile_id)
            target_profile_coverage[language][profile_id] = {
                "existing_reviewed_active": int(existing_counts["reviewed_active"]),
                "existing_open_count": int(
                    existing_counts["needs_revision"]
                    + existing_counts["needs_replacement"]
                    + existing_counts["needs_adjudication"]
                ),
                "existing_unset_count": int(existing_counts["unset"]),
                "candidate_case_count": candidate_count,
                "reserve_case_count": reserve_count,
            }
            if int(existing_counts["reviewed_active"]) < TARGET_PROFILE_FLOOR_REVIEWED_ACTIVE:
                deficits.append(
                    {
                        "dataset_id": "",
                        "language_track": language,
                        "target_profile_id": profile_id,
                        "deficit_kind": "reviewed_active_floor",
                        "severity": "high" if existing_counts["reviewed_active"] == 0 else "medium",
                        "recommended_action": "construct_and_review" if candidate_count > 0 else "construct_cases",
                    }
                )
            if reserve_count < TARGET_PROFILE_FLOOR_RESERVE:
                deficits.append(
                    {
                        "dataset_id": "",
                        "language_track": language,
                        "target_profile_id": profile_id,
                        "deficit_kind": "reserve_depth",
                        "severity": "medium",
                        "recommended_action": "construct_cases" if candidate_count > 0 or reserve_count > 0 else "stop_exhausted",
                    }
                )
            if target_profile_coverage[language][profile_id]["existing_open_count"] > 0:
                deficits.append(
                    {
                        "dataset_id": "",
                        "language_track": language,
                        "target_profile_id": profile_id,
                        "deficit_kind": "open_review_backlog",
                        "severity": "high",
                        "recommended_action": "review_existing_cases",
                    }
                )

    recommended_next_action = _recommended_next_action(deficits)
    status = (
        "satisfied"
        if recommended_next_action == "stop_satisfied"
        else "exhausted"
        if recommended_next_action == "stop_exhausted"
        else "needs_action"
    )
    return {
        "scope_id": scope_id,
        "family": "excerpt_cases",
        "iteration_id": "question_aligned_v1",
        "language_scope": "bilingual",
        "status": status,
        "reviewed_active_counts": reviewed_active_counts,
        "open_status_counts": open_status_counts,
        "target_profile_coverage": target_profile_coverage,
        "reserve_depth": reserve_depth,
        "source_diversity": source_diversity,
        "deficits": deficits,
        "recommended_next_action": recommended_next_action,
    }


def _recommended_next_action(deficits: list[dict[str, Any]]) -> str:
    actions = {str(item.get("recommended_action", "")).strip() for item in deficits}
    if "review_existing_cases" in actions:
        return "review_existing_cases"
    if "construct_and_review" in actions:
        return "construct_and_review"
    if "construct_cases" in actions:
        return "construct_cases"
    if "stop_exhausted" in actions and len(actions) == 1:
        return "stop_exhausted"
    return "stop_satisfied"


def _build_opportunity_cards_for_chapter(
    *,
    row: dict[str, Any],
    source: dict[str, Any],
    chapter: dict[str, Any],
    feedback: dict[str, Any],
) -> list[dict[str, Any]]:
    sentences = list(chapter.get("sentences") or [])
    if len(sentences) < 3:
        return []
    language = str(row["language_track"])
    opportunities: list[dict[str, Any]] = []
    total_sentences = len(sentences)
    prior_text = ""
    prior_tokens: set[str] = set()
    sentence_scores_by_profile: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for index, sentence in enumerate(sentences):
        sentence_text = str(sentence.get("text") or "").strip()
        if len(sentence_text) < 20:
            prior_text += " " + sentence_text
            prior_tokens |= _tokenize(sentence_text, language)
            continue
        position_bucket = _position_bucket(index=index, total=total_sentences)
        for profile_id in TARGET_PROFILE_ORDER:
            score_payload = _score_sentence_for_profile(
                profile_id=profile_id,
                sentence_text=sentence_text,
                language=language,
                selection_role=str(row.get("selection_role", "")),
                role_tags=list(row.get("role_tags") or source.get("role_tags") or []),
                position_bucket=position_bucket,
                prior_text=prior_text,
                prior_tokens=prior_tokens,
                feedback=feedback,
            )
            if score_payload["score"] <= 0:
                continue
            sentence_scores_by_profile[profile_id].append(
                {
                    "index": index,
                    "sentence": sentence,
                    "position_bucket": position_bucket,
                    **score_payload,
                }
            )
        prior_text += " " + sentence_text
        prior_tokens |= _tokenize(sentence_text, language)

    for profile_id, candidates in sentence_scores_by_profile.items():
        top_candidates = sorted(
            candidates,
            key=lambda item: (-float(item["construction_priority"]), int(item["index"])),
        )[:2]
        for rank, candidate in enumerate(top_candidates, start=1):
            profile = EXCERPT_TARGET_PROFILES[profile_id]
            radius = int(profile["radius_en"] if language == "en" else profile["radius_zh"])
            start = max(0, candidate["index"] - radius)
            end = min(total_sentences, candidate["index"] + radius + 1)
            window = sentences[start:end]
            if not window:
                continue
            excerpt_text = "\n".join(str(item.get("text") or "").strip() for item in window).strip()
            if len(excerpt_text) < 80:
                continue
            prior_context_ids = [window_item["sentence_id"] for window_item in window[:-1] if window_item["sentence_id"] != candidate["sentence"]["sentence_id"]]
            anchor_sentence_id = candidate["sentence"]["sentence_id"]
            source_priority = int(row.get("selection_priority", 9999) or 9999)
            opportunities.append(
                {
                    "opportunity_id": f"{row['chapter_case_id']}__{profile_id}__opp_{rank}",
                    "chapter_case_id": str(row["chapter_case_id"]),
                    "source_id": str(row["source_id"]),
                    "book_title": str(row["book_title"]),
                    "author": str(row["author"]),
                    "language_track": language,
                    "chapter_id": str(row["chapter_id"]),
                    "chapter_number": int(row["chapter_number"]),
                    "chapter_title": str(row["chapter_title"]),
                    "selection_role": str(row.get("selection_role", "")),
                    "target_profile_ids": [profile_id],
                    "anchor_sentence_ids": [anchor_sentence_id],
                    "support_sentence_ids": [item["sentence_id"] for item in window if item["sentence_id"] != anchor_sentence_id],
                    "prior_context_sentence_ids": prior_context_ids,
                    "anchor_excerpt_text": str(candidate["sentence"].get("text") or "").strip(),
                    "context_excerpt_text": excerpt_text,
                    "phenomenon_evidence": list(candidate["evidence"]),
                    "judgeability_score": round(float(candidate["judgeability_score"]), 3),
                    "discriminative_power_score": round(float(candidate["discriminative_power_score"]), 3),
                    "ambiguity_risk": candidate["ambiguity_risk"],
                    "construction_priority": round(float(candidate["construction_priority"]), 3),
                    "selection_reason_draft": _selection_reason_draft(
                        profile_id=profile_id,
                        sentence_text=str(candidate["sentence"].get("text") or "").strip(),
                    ),
                    "judge_focus_draft": _judge_focus_draft(profile_id=profile_id),
                    "rejection_reasons": [],
                    "reserve_rank": 0,
                    "derived_from_review_feedback": bool(candidate["deficit_boost"]),
                    "candidate_position_bucket": candidate["position_bucket"],
                    "selection_priority": source_priority,
                    "type_tags": list(source.get("type_tags") or []),
                    "role_tags": list(source.get("role_tags") or []),
                }
            )
    return opportunities


def _score_sentence_for_profile(
    *,
    profile_id: str,
    sentence_text: str,
    language: str,
    selection_role: str,
    role_tags: list[str],
    position_bucket: str,
    prior_text: str,
    prior_tokens: set[str],
    feedback: dict[str, Any],
) -> dict[str, Any]:
    profile = EXCERPT_TARGET_PROFILES[profile_id]
    lowered = sentence_text.lower()
    evidence: list[str] = []
    score = 0.0

    cue_hits = sum(lowered.count(cue) for cue in profile["en_cues"]) if language == "en" else sum(sentence_text.count(cue) for cue in profile["zh_cues"])
    if cue_hits:
        evidence.append(f"cue_hits:{cue_hits}")
        score += cue_hits * 1.3

    if selection_role in profile["preferred_roles"] or bool(set(role_tags).intersection(set(profile["preferred_roles"]))):
        evidence.append("preferred_role")
        score += 0.9
    if position_bucket in profile["preferred_positions"]:
        evidence.append(f"preferred_position:{position_bucket}")
        score += 0.7

    if profile_id == "callback_bridge":
        overlap = len(_tokenize(sentence_text, language).intersection(prior_tokens))
        if overlap:
            evidence.append(f"prior_overlap:{overlap}")
            score += min(2.0, overlap * 0.6)
    if profile_id == "anchored_reaction_selectivity" and any(marker in sentence_text for marker in ("?", "!", "？", "！", "“", "\"")):
        evidence.append("reaction_marker")
        score += 0.8
    if profile_id == "reconsolidation_later_reinterpretation" and len(prior_text) > 120:
        evidence.append("later_context_available")
        score += 0.6

    sentence_length = len(sentence_text)
    if 60 <= sentence_length <= 280:
        evidence.append("judgeable_length")
        score += 0.6
    elif sentence_length > 320:
        score -= 0.4

    profile_feedback = (feedback.get("profiles") or {}).get(profile_id, {})
    reviewed_active = int(profile_feedback.get("reviewed_active", 0))
    open_count = int(
        profile_feedback.get("needs_revision", 0)
        + profile_feedback.get("needs_replacement", 0)
        + profile_feedback.get("needs_adjudication", 0)
    )
    deficit_boost = max(0, TARGET_PROFILE_FLOOR_REVIEWED_ACTIVE - reviewed_active) * 0.9 + min(1.5, open_count * 0.5)
    construction_priority = score + deficit_boost
    judgeability_score = max(0.0, min(5.0, score + 1.0))
    discriminative_power_score = max(0.0, min(5.0, score + deficit_boost))
    ambiguity_risk = "low" if score >= 2.8 else "medium" if score >= 1.6 else "high"
    return {
        "score": score,
        "judgeability_score": judgeability_score,
        "discriminative_power_score": discriminative_power_score,
        "ambiguity_risk": ambiguity_risk,
        "evidence": evidence,
        "deficit_boost": deficit_boost,
        "construction_priority": construction_priority,
    }


def _select_cases_and_reserves(
    opportunities: list[dict[str, Any]],
    *,
    cases_per_chapter: int,
    reserves_per_chapter: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    selected_ids: set[str] = set()
    selected_chapters: dict[str, int] = defaultdict(int)
    selected_profiles_per_chapter: dict[str, set[str]] = defaultdict(set)
    cases: list[dict[str, Any]] = []

    for profile_id in TARGET_PROFILE_ORDER:
        profile_candidates = [
            item
            for item in opportunities
            if str(item["target_profile_ids"][0]) == profile_id
        ]
        for item in sorted(
            profile_candidates,
            key=lambda candidate: (-float(candidate["construction_priority"]), int(candidate.get("selection_priority", 9999))),
        ):
            chapter_key = str(item["chapter_case_id"])
            if chapter_key in selected_chapters:
                continue
            case = _assembled_case(item)
            cases.append(case)
            selected_ids.add(str(item["opportunity_id"]))
            selected_chapters[chapter_key] += 1
            selected_profiles_per_chapter[chapter_key].add(profile_id)
            break

    for item in sorted(
        opportunities,
        key=lambda candidate: (
            str(candidate["chapter_case_id"]),
            -float(candidate["construction_priority"]),
            int(candidate.get("selection_priority", 9999)),
        ),
    ):
        chapter_key = str(item["chapter_case_id"])
        profile_id = str(item["target_profile_ids"][0])
        if str(item["opportunity_id"]) in selected_ids:
            continue
        if selected_chapters[chapter_key] >= cases_per_chapter:
            continue
        if profile_id in selected_profiles_per_chapter[chapter_key]:
            continue
        case = _assembled_case(item)
        cases.append(case)
        selected_ids.add(str(item["opportunity_id"]))
        selected_chapters[chapter_key] += 1
        selected_profiles_per_chapter[chapter_key].add(profile_id)

    reserves: list[dict[str, Any]] = []
    reserve_counts: dict[str, int] = defaultdict(int)
    for item in sorted(
        opportunities,
        key=lambda candidate: (
            str(candidate["chapter_case_id"]),
            -float(candidate["construction_priority"]),
            int(candidate.get("selection_priority", 9999)),
        ),
    ):
        chapter_key = str(item["chapter_case_id"])
        if str(item["opportunity_id"]) in selected_ids:
            continue
        if reserve_counts[chapter_key] >= reserves_per_chapter:
            continue
        reserve = _assembled_reserve_case(item, reserve_rank=reserve_counts[chapter_key] + 1)
        reserves.append(reserve)
        reserve_counts[chapter_key] += 1

    cases.sort(key=lambda row: (str(row["output_language"]), str(row["source_id"]), int(row["chapter_number"])))
    reserves.sort(key=lambda row: (str(row["output_language"]), str(row["source_id"]), int(row["chapter_number"]), int(row["reserve_rank"])))
    return cases, reserves


def _assembled_case(opportunity: dict[str, Any]) -> dict[str, Any]:
    profile_id = str(opportunity["target_profile_ids"][0])
    profile = EXCERPT_TARGET_PROFILES[profile_id]
    return {
        "case_id": f"{opportunity['source_id']}__{opportunity['chapter_id']}__{profile_id}__seed_v1",
        "case_title": f"{opportunity['book_title']} / {opportunity['chapter_title']} / {profile_id}",
        "split": "private_library_seed_v2",
        "curation_status": "question_aligned_builder_seed_v1",
        "source_policy": "private-local-source",
        "source_id": opportunity["source_id"],
        "book_title": opportunity["book_title"],
        "author": opportunity["author"],
        "output_language": opportunity["language_track"],
        "chapter_id": str(opportunity["chapter_id"]),
        "chapter_number": int(opportunity["chapter_number"]),
        "chapter_title": opportunity["chapter_title"],
        "start_sentence_id": opportunity["anchor_sentence_ids"][0],
        "end_sentence_id": opportunity["support_sentence_ids"][-1] if opportunity["support_sentence_ids"] else opportunity["anchor_sentence_ids"][0],
        "excerpt_text": opportunity["context_excerpt_text"],
        "question_ids": list(profile["question_ids"]),
        "phenomena": list(profile["phenomena"]),
        "selection_reason": opportunity["selection_reason_draft"],
        "judge_focus": opportunity["judge_focus_draft"],
        "target_profile_id": profile_id,
        "opportunity_id": opportunity["opportunity_id"],
        "replacement_family_id": f"{opportunity['source_id']}::{opportunity['chapter_id']}::{profile_id}",
        "reserve_group_id": f"{opportunity['source_id']}::{opportunity['chapter_id']}",
        "construction_priority": round(float(opportunity["construction_priority"]), 3),
        "judgeability_score": round(float(opportunity["judgeability_score"]), 3),
        "discriminative_power_score": round(float(opportunity["discriminative_power_score"]), 3),
        "selection_role": opportunity["selection_role"],
        "type_tags": list(opportunity.get("type_tags") or []),
        "role_tags": list(opportunity.get("role_tags") or []),
        "candidate_position_bucket": opportunity.get("candidate_position_bucket"),
        "benchmark_status": "unset",
        "review_status": "builder_curated",
        "review_history": [],
        "notes": "Question-aligned seed case built from the managed private-library supplement. Requires later benchmark hardening before promotion.",
    }


def _assembled_reserve_case(opportunity: dict[str, Any], *, reserve_rank: int) -> dict[str, Any]:
    profile_id = str(opportunity["target_profile_ids"][0])
    profile = EXCERPT_TARGET_PROFILES[profile_id]
    return {
        "case_id": f"{opportunity['source_id']}__{opportunity['chapter_id']}__{profile_id}__reserve_v1",
        "case_title": f"{opportunity['book_title']} / {opportunity['chapter_title']} / {profile_id} / reserve",
        "split": "private_library_reserve_v1",
        "curation_status": "question_aligned_reserve_v1",
        "source_policy": "private-local-source",
        "source_id": opportunity["source_id"],
        "book_title": opportunity["book_title"],
        "author": opportunity["author"],
        "output_language": opportunity["language_track"],
        "chapter_id": str(opportunity["chapter_id"]),
        "chapter_number": int(opportunity["chapter_number"]),
        "chapter_title": opportunity["chapter_title"],
        "start_sentence_id": opportunity["anchor_sentence_ids"][0],
        "end_sentence_id": opportunity["support_sentence_ids"][-1] if opportunity["support_sentence_ids"] else opportunity["anchor_sentence_ids"][0],
        "excerpt_text": opportunity["context_excerpt_text"],
        "question_ids": list(profile["question_ids"]),
        "phenomena": list(profile["phenomena"]),
        "selection_reason": opportunity["selection_reason_draft"],
        "judge_focus": opportunity["judge_focus_draft"],
        "target_profile_id": profile_id,
        "opportunity_id": opportunity["opportunity_id"],
        "replacement_family_id": f"{opportunity['source_id']}::{opportunity['chapter_id']}::{profile_id}",
        "reserve_group_id": f"{opportunity['source_id']}::{opportunity['chapter_id']}",
        "reserve_rank": reserve_rank,
        "selection_role": opportunity["selection_role"],
        "type_tags": list(opportunity.get("type_tags") or []),
        "role_tags": list(opportunity.get("role_tags") or []),
        "candidate_position_bucket": opportunity.get("candidate_position_bucket"),
        "notes": "Reserve candidate retained for later replacement or targeted swap-in during benchmark hardening.",
    }


def _selection_reason_draft(*, profile_id: str, sentence_text: str) -> str:
    profile = EXCERPT_TARGET_PROFILES[profile_id]
    clipped = re.sub(r"\s+", " ", sentence_text).strip()
    if len(clipped) > 160:
        clipped = clipped[:157].rstrip() + "..."
    return f"{profile['selection_reason_template']} Anchor line: {clipped}"


def _judge_focus_draft(*, profile_id: str) -> str:
    return str(EXCERPT_TARGET_PROFILES[profile_id]["judge_focus_template"])


def _position_bucket(*, index: int, total: int) -> str:
    if total <= 1:
        return "middle"
    fraction = index / max(total - 1, 1)
    if fraction < 0.34:
        return "early"
    if fraction < 0.67:
        return "middle"
    return "late"


def _tokenize(text: str, language: str) -> set[str]:
    if language == "zh":
        return {match.group(0) for match in re.finditer(r"[\u4e00-\u9fff]{2,}", text)}
    return {token for token in re.findall(r"[A-Za-z]{4,}", text.lower()) if token not in {"that", "this", "with", "from", "have", "were"}}

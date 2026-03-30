"""Question-aligned case construction helpers for attentional_v2 datasets."""

from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
import re
from typing import Any, Callable


TARGET_PROFILE_FLOOR_REVIEWED_ACTIVE = 2
TARGET_PROFILE_FLOOR_RESERVE = 1
MIN_COMPLETE_SENTENCES_PER_EXCERPT = 3
MIN_PROFILE_ORDER_SELECTION_PRIORITY = 4.0
MAX_WINDOW_REFINEMENT_CANDIDATES_PER_PROFILE = 4
ZH_LATE_SCENE_BONUS = 0.65
ZH_SCENE_DIALOGUE_BONUS = 0.45
ZH_EARLY_FILLER_PENALTY = 0.55
WINDOW_EDGE_NOISE_PENALTY = 0.75
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
        "en_cues": ("again", "once more", "earlier", "before", "return", "returns", "went back", "back over"),
        "zh_cues": ("再次", "之前", "前面", "回到", "又一次"),
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

TITLE_FRAGMENT_RE = re.compile(r"^(?:Mr|Mrs|Ms|Dr|Prof|St|Jr|Sr)\.$")
INITIAL_FRAGMENT_RE = re.compile(r"^(?:[A-Z]\.)+$")
LOWERCASE_START_RE = re.compile(r"^[a-z]")
SHORT_COMMA_FRAGMENT_RE = re.compile(r"^[A-Z][^.!?]{0,60},[^.!?]{0,40}[.!?]$")
ABBREVIATION_SUFFIX_RE = re.compile(r"(?:\b(?:Mr|Mrs|Ms|Dr|Prof|St|Jr|Sr)\.|\b(?:[A-Z]\.)+)$")
QUOTE_PAIRS = (
    ("“", "”"),
    ("‘", "’"),
    ("「", "」"),
    ("『", "』"),
)
EXPLICIT_CALLBACK_MARKERS_EN = (
    "again",
    "once more",
    "earlier",
    "return",
    "returns",
    "went back",
    "back over",
)
EXPLICIT_CALLBACK_MARKERS_ZH = ("再次", "回到", "前面", "之前", "又一次")
REPORTED_SPEECH_MARKERS_EN = (
    "said",
    "says",
    "replied",
    "asked",
    "told",
    "cried",
    "reproach",
    "repulsed argument",
    "declaimed",
)
REPORTED_SPEECH_MARKERS_ZH = ("说道", "说", "问", "回答", "斥责")
PARATEXT_MARKERS_EN = (
    "public domain",
    "copyright",
    "published",
    "edition",
    "author:",
    "project gutenberg",
)
PARATEXT_MARKERS_ZH = (
    "作者",
    "文学周报",
    "出版",
    "同名散文集",
    "公有領域",
    "公有领域",
    "版權",
    "版权",
    "Public domain",
)


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
    dataset_ids_by_language: dict[str, str] | None = None,
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
        dataset_ids_by_language=dataset_ids_by_language or {},
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
    dataset_ids_by_language: dict[str, str],
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
        dataset_id = str(dataset_ids_by_language.get(language, "")).strip()
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
                        "dataset_id": dataset_id,
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
                        "dataset_id": dataset_id,
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
                        "dataset_id": dataset_id,
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
        "dataset_ids_by_language": dict(sorted(dataset_ids_by_language.items())),
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
        )[:MAX_WINDOW_REFINEMENT_CANDIDATES_PER_PROFILE]
        for rank, candidate in enumerate(top_candidates, start=1):
            profile = EXCERPT_TARGET_PROFILES[profile_id]
            radius = int(profile["radius_en"] if language == "en" else profile["radius_zh"])
            start = max(0, candidate["index"] - radius)
            end = min(total_sentences, candidate["index"] + radius + 1)
            start, end = _expand_excerpt_window(sentences, start=start, end=end)
            window = sentences[start:end]
            if not window:
                continue
            rendered_excerpt_text = render_excerpt_sentences(
                str(item.get("text") or "").strip() for item in window
            )
            if len(rendered_excerpt_text) < 80:
                continue
            complete_sentence_count = _complete_sentence_count(
                str(item.get("text") or "").strip() for item in window
            )
            if complete_sentence_count < MIN_COMPLETE_SENTENCES_PER_EXCERPT:
                continue
            if not _window_is_valid_for_profile(
                profile_id=profile_id,
                anchor_text=str(candidate["sentence"].get("text") or "").strip(),
                window=[str(item.get("text") or "").strip() for item in window],
                language=language,
            ):
                continue
            window_priority_adjustment, window_evidence = _window_quality_adjustment(
                profile_id=profile_id,
                language=language,
                selection_role=str(row.get("selection_role", "")),
                position_bucket=str(candidate["position_bucket"]),
                window=[str(item.get("text") or "").strip() for item in window],
            )
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
                    "excerpt_sentence_ids": [item["sentence_id"] for item in window],
                    "anchor_sentence_ids": [anchor_sentence_id],
                    "support_sentence_ids": [item["sentence_id"] for item in window if item["sentence_id"] != anchor_sentence_id],
                    "prior_context_sentence_ids": [],
                    "anchor_excerpt_text": str(candidate["sentence"].get("text") or "").strip(),
                    "context_excerpt_text": rendered_excerpt_text,
                    "phenomenon_evidence": list(candidate["evidence"]) + window_evidence,
                    "judgeability_score": round(float(candidate["judgeability_score"]), 3),
                    "discriminative_power_score": round(float(candidate["discriminative_power_score"]), 3),
                    "ambiguity_risk": candidate["ambiguity_risk"],
                    "construction_priority": round(float(candidate["construction_priority"]) + window_priority_adjustment, 3),
                    "complete_sentence_count": complete_sentence_count,
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
        if not _has_explicit_callback_marker(sentence_text, language):
            score -= 2.0
            evidence.append("missing_explicit_callback_marker")
    if profile_id == "anchored_reaction_selectivity" and any(marker in sentence_text for marker in ("?", "!", "？", "！", "“", "\"")):
        evidence.append("reaction_marker")
        score += 0.8
    if profile_id == "anchored_reaction_selectivity" and _looks_like_reported_speech(sentence_text, language):
        score -= 1.6
        evidence.append("reported_speech_penalty")
    if profile_id == "reconsolidation_later_reinterpretation" and len(prior_text) > 120:
        evidence.append("later_context_available")
        score += 0.6
    if _needs_preceding_sentence(sentence_text):
        score -= 1.3
        evidence.append("context_dependency_penalty")
    if _looks_like_paratext_sentence(sentence_text, language):
        score -= 3.2
        evidence.append("paratext_penalty")

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
            if float(item["construction_priority"]) < MIN_PROFILE_ORDER_SELECTION_PRIORITY:
                continue
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
    excerpt_sentence_ids = list(opportunity.get("excerpt_sentence_ids") or [])
    start_sentence_id = excerpt_sentence_ids[0] if excerpt_sentence_ids else opportunity["anchor_sentence_ids"][0]
    end_sentence_id = excerpt_sentence_ids[-1] if excerpt_sentence_ids else (
        opportunity["support_sentence_ids"][-1] if opportunity["support_sentence_ids"] else opportunity["anchor_sentence_ids"][0]
    )
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
        "start_sentence_id": start_sentence_id,
        "end_sentence_id": end_sentence_id,
        "excerpt_text": opportunity["context_excerpt_text"],
        "excerpt_sentence_ids": excerpt_sentence_ids,
        "anchor_sentence_id": opportunity["anchor_sentence_ids"][0],
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
    excerpt_sentence_ids = list(opportunity.get("excerpt_sentence_ids") or [])
    start_sentence_id = excerpt_sentence_ids[0] if excerpt_sentence_ids else opportunity["anchor_sentence_ids"][0]
    end_sentence_id = excerpt_sentence_ids[-1] if excerpt_sentence_ids else (
        opportunity["support_sentence_ids"][-1] if opportunity["support_sentence_ids"] else opportunity["anchor_sentence_ids"][0]
    )
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
        "start_sentence_id": start_sentence_id,
        "end_sentence_id": end_sentence_id,
        "excerpt_text": opportunity["context_excerpt_text"],
        "excerpt_sentence_ids": excerpt_sentence_ids,
        "anchor_sentence_id": opportunity["anchor_sentence_ids"][0],
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


def _is_short_comma_fragment(text: str) -> bool:
    token_count = len(re.findall(r"[A-Za-z]+", text))
    return token_count <= 4 and bool(SHORT_COMMA_FRAGMENT_RE.match(text))


def _needs_preceding_sentence(text: str) -> bool:
    cleaned = str(text or "").strip()
    if not cleaned:
        return False
    return bool(
        LOWERCASE_START_RE.match(cleaned)
        or _is_short_comma_fragment(cleaned)
    )


def _needs_following_sentence(text: str) -> bool:
    cleaned = str(text or "").strip()
    if not cleaned:
        return False
    return bool(
        TITLE_FRAGMENT_RE.match(cleaned)
        or INITIAL_FRAGMENT_RE.match(cleaned)
        or ABBREVIATION_SUFFIX_RE.search(cleaned)
        or _has_unclosed_quote(cleaned)
    )


def _looks_fragmentary(text: str) -> bool:
    cleaned = str(text or "").strip()
    if not cleaned:
        return True
    return _needs_preceding_sentence(cleaned) or _needs_following_sentence(cleaned)


def _complete_sentence_count(texts: list[str] | tuple[str, ...] | Any) -> int:
    return len(_rendered_excerpt_parts(texts))


def render_excerpt_sentences(texts: Any) -> str:
    return "\n".join(_rendered_excerpt_parts(texts)).strip()


def _rendered_excerpt_parts(texts: Any) -> list[str]:
    rendered: list[str] = []
    for raw_text in texts:
        text = str(raw_text or "").strip()
        if not text:
            continue
        if rendered and (_needs_following_sentence(rendered[-1]) or _needs_preceding_sentence(text)):
            rendered[-1] = rendered[-1].rstrip() + " " + text.lstrip()
            continue
        rendered.append(text)
    return rendered


def _expand_excerpt_window(sentences: list[dict[str, Any]], *, start: int, end: int) -> tuple[int, int]:
    while start > 0 and (
        _needs_preceding_sentence(str(sentences[start].get("text") or "").strip())
        or _needs_following_sentence(str(sentences[start - 1].get("text") or "").strip())
    ):
        start -= 1
    while end < len(sentences) and _needs_following_sentence(str(sentences[end - 1].get("text") or "").strip()):
        if end >= len(sentences):
            break
        end += 1
    return start, min(end, len(sentences))


def _has_explicit_callback_marker(text: str, language: str) -> bool:
    lowered = text.lower()
    markers = EXPLICIT_CALLBACK_MARKERS_EN if language == "en" else EXPLICIT_CALLBACK_MARKERS_ZH
    if language == "en":
        return any(marker in lowered for marker in markers)
    return any(marker in text for marker in markers)


def _looks_like_reported_speech(text: str, language: str) -> bool:
    lowered = text.lower()
    markers = REPORTED_SPEECH_MARKERS_EN if language == "en" else REPORTED_SPEECH_MARKERS_ZH
    if language == "en":
        return ("\"" in text or "“" in text) and any(marker in lowered for marker in markers)
    return ("“" in text or "”" in text or "「" in text) and any(marker in text for marker in markers)


def _window_is_valid_for_profile(
    *,
    profile_id: str,
    anchor_text: str,
    window: list[str],
    language: str,
) -> bool:
    rendered_excerpt = render_excerpt_sentences(window)
    if not rendered_excerpt:
        return False
    if profile_id == "callback_bridge" and not _has_explicit_callback_marker(anchor_text, language):
        return False
    if profile_id == "anchored_reaction_selectivity" and _looks_like_reported_speech(anchor_text, language):
        return False
    if _looks_like_paratext_window(window, language):
        return False
    return True


def _looks_like_paratext_sentence(text: str, language: str) -> bool:
    cleaned = str(text or "").strip()
    if not cleaned:
        return False
    digit_count = sum(character.isdigit() for character in cleaned)
    if language == "zh":
        marker_hit = any(marker in cleaned for marker in PARATEXT_MARKERS_ZH)
        issue_marker = "第" in cleaned and "期" in cleaned
        return marker_hit and (digit_count >= 4 or issue_marker)
    lowered = cleaned.lower()
    marker_hit = any(marker in lowered for marker in PARATEXT_MARKERS_EN)
    return marker_hit and digit_count >= 4


def _looks_like_paratext_window(window: list[str], language: str) -> bool:
    cleaned = [str(item or "").strip() for item in window if str(item or "").strip()]
    if not cleaned:
        return False
    sentence_hits = sum(1 for text in cleaned if _looks_like_paratext_sentence(text, language))
    if sentence_hits >= max(2, len(cleaned) - 1):
        return True
    combined = " ".join(cleaned) if language == "en" else "".join(cleaned)
    return sentence_hits >= 1 and _looks_like_paratext_sentence(combined, language)


def _window_quality_adjustment(
    *,
    profile_id: str,
    language: str,
    selection_role: str,
    position_bucket: str,
    window: list[str],
) -> tuple[float, list[str]]:
    cleaned = [str(item or "").strip() for item in window if str(item or "").strip()]
    if not cleaned:
        return 0.0, []

    adjustment = 0.0
    evidence: list[str] = []
    rendered_parts = _rendered_excerpt_parts(cleaned)
    if not rendered_parts:
        return 0.0, []

    if _needs_preceding_sentence(rendered_parts[0]) or _needs_following_sentence(rendered_parts[-1]):
        adjustment -= WINDOW_EDGE_NOISE_PENALTY
        evidence.append("edge_noise_penalty")

    if language == "zh" and profile_id in {"tension_reversal", "reconsolidation_later_reinterpretation"}:
        if position_bucket == "late":
            adjustment += ZH_LATE_SCENE_BONUS
            evidence.append("zh_late_scene_bonus")
        if any(
            any(marker in part for marker in ("「", "」", "“", "”"))
            for part in rendered_parts
        ) and any(
            not any(marker in part for marker in ("「", "」", "“", "”")) for part in rendered_parts
        ):
            adjustment += ZH_SCENE_DIALOGUE_BONUS
            evidence.append("zh_scene_dialogue_bonus")

    if (
        language == "zh"
        and profile_id == "distinction_definition"
        and position_bucket == "early"
        and selection_role == "narrative_reflective"
    ):
        adjustment -= ZH_EARLY_FILLER_PENALTY
        evidence.append("zh_early_filler_penalty")

    return adjustment, evidence


def _has_unclosed_quote(text: str) -> bool:
    cleaned = str(text or "").strip()
    if not cleaned:
        return False
    for opener, closer in QUOTE_PAIRS:
        if cleaned.count(opener) > cleaned.count(closer):
            return True
    if cleaned.count('"') % 2 == 1:
        return True
    return False

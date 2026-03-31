"""Question-aligned case construction helpers for attentional_v2 datasets."""

from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
import re
from typing import Any, Callable
import unicodedata


TARGET_PROFILE_FLOOR_REVIEWED_ACTIVE = 2
TARGET_PROFILE_FLOOR_RESERVE = 1
MIN_COMPLETE_SENTENCES_PER_EXCERPT = 3
MIN_PROFILE_ORDER_SELECTION_PRIORITY = 4.0
MAX_WINDOW_REFINEMENT_CANDIDATES_PER_PROFILE = 4
ZH_LATE_SCENE_BONUS = 0.65
ZH_SCENE_DIALOGUE_BONUS = 0.45
ZH_EARLY_FILLER_PENALTY = 0.55
RECONSOLIDATION_MISSING_CUE_PENALTY = 1.2
WINDOW_EDGE_NOISE_PENALTY = 0.75
ZH_TENSION_MISSING_CUE_PENALTY = 1.2
CALLBACK_LOOKBACK_SENTENCE_LIMIT_EN = 5
CALLBACK_LOOKBACK_SENTENCE_LIMIT_ZH = 7
CALLBACK_INLINE_ANTECEDENT_GAP = 2
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
        "judge_focus_template": "Can the reader trace the backward bridge to specific earlier material from the passage, while keeping the attribution of the bridging claim clear?",
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
LEADING_BACKREFERENCE_RE = re.compile(
    r"^Whether\s+(?:this|that|these|those)\b",
    re.IGNORECASE,
)
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
    "from this",
    "from that",
    "from these",
    "from those",
    "return",
    "returns",
    "went back",
    "back over",
)
EXPLICIT_CALLBACK_MARKERS_ZH = ("再次", "回到", "前面", "之前", "又一次", "依旧", "依舊")
CALLBACK_STOP_TERMS_EN = {
    "again",
    "back",
    "before",
    "earlier",
    "over",
    "return",
    "returns",
    "same",
    "went",
}
CALLBACK_GENERIC_OVERLAP_TERMS_EN = {
    "from",
    "that",
    "their",
    "there",
    "these",
    "this",
    "those",
    "home",
    "into",
    "none",
    "soon",
    "which",
    "while",
    "with",
    "himself",
}
CALLBACK_STOP_TERMS_ZH = {
    "再次",
    "前面",
    "之前",
    "又一次",
    "回到",
    "依旧",
    "依舊",
    "此处",
    "这里",
    "那句",
    "这句",
}
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
SENTENCE_END_MARKERS = frozenset(".!?。！？…;；:：\"”」』）)]'")
NORMALIZED_SPACE_EQUIVALENTS = frozenset({" ", "\t", "\r", "\n", "\f", "\v", "\u00a0", "\u2007", "\u202f"})
INVISIBLE_FORMAT_CHARACTERS = frozenset({"\u200b", "\u200c", "\u200d", "\ufeff", "\u2060"})


def excerpt_target_profiles() -> list[dict[str, Any]]:
    """Return the stable ordered target-profile list for excerpt construction."""

    return [deepcopy(EXCERPT_TARGET_PROFILES[target_id]) for target_id in TARGET_PROFILE_ORDER]


def _normalize_sentence_text(text: Any) -> str:
    cleaned_characters: list[str] = []
    for character in str(text or ""):
        if character in INVISIBLE_FORMAT_CHARACTERS or unicodedata.category(character) == "Cf":
            continue
        if character in NORMALIZED_SPACE_EQUIVALENTS:
            cleaned_characters.append(" ")
            continue
        cleaned_characters.append(character)
    return re.sub(r" +", " ", "".join(cleaned_characters)).strip()


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
        sentence_text = _normalize_sentence_text(sentence.get("text") or "")
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
                    "sentence_text": sentence_text,
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
            prior_context_sentence_ids: list[str] = []
            prior_context_excerpt_text = ""
            callback_evidence: list[str] = []
            callback_antecedent_resolved: bool | None = None
            callback_target_text = ""
            tension_target_text = ""
            if profile_id == "callback_bridge":
                antecedent = _resolve_callback_antecedent(
                    sentences=sentences,
                    anchor_index=int(candidate["index"]),
                    language=language,
                )
                callback_antecedent_resolved = bool(antecedent["resolved"])
                if not callback_antecedent_resolved:
                    continue
                callback_evidence = list(antecedent["evidence"])
                callback_target_text = _callback_target_prompt_text(
                    str(antecedent["excerpt_text"])
                )
                antecedent_index = int(antecedent["antecedent_index"])
                if antecedent_index < start:
                    if (start - antecedent_index) <= CALLBACK_INLINE_ANTECEDENT_GAP:
                        start = antecedent_index
                    else:
                        prior_context_sentence_ids = list(antecedent["sentence_ids"])
                        prior_context_excerpt_text = str(antecedent["excerpt_text"])
            start, end = _refine_excerpt_window_for_profile(
                profile_id=profile_id,
                language=language,
                sentences=sentences,
                anchor_index=int(candidate["index"]),
                start=start,
                end=end,
            )
            start, end = _expand_excerpt_window(sentences, start=start, end=end)
            window = sentences[start:end]
            if not window:
                continue
            rendered_excerpt_text = render_excerpt_sentences(
                item.get("text") or "" for item in window
            )
            if len(rendered_excerpt_text) < 80:
                continue
            if profile_id == "tension_reversal":
                tension_target_text = _tension_target_prompt_text(
                    window_texts=[item.get("text") or "" for item in window],
                    language=language,
                )
            complete_sentence_count = _complete_sentence_count(
                item.get("text") or "" for item in window
            )
            if complete_sentence_count < MIN_COMPLETE_SENTENCES_PER_EXCERPT:
                continue
            if not _window_is_valid_for_profile(
                profile_id=profile_id,
                anchor_text=str(candidate.get("sentence_text") or ""),
                window=[item.get("text") or "" for item in window],
                language=language,
                callback_antecedent_resolved=callback_antecedent_resolved,
            ):
                continue
            window_priority_adjustment, window_evidence = _window_quality_adjustment(
                profile_id=profile_id,
                language=language,
                selection_role=str(row.get("selection_role", "")),
                position_bucket=str(candidate["position_bucket"]),
                window=[item.get("text") or "" for item in window],
            )
            anchor_sentence_id = candidate["sentence"]["sentence_id"]
            anchor_display_text = _selection_reason_anchor_text(
                anchor_text=str(candidate.get("sentence_text") or ""),
                window_texts=[item.get("text") or "" for item in window],
            )
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
                    "prior_context_sentence_ids": prior_context_sentence_ids,
                    "prior_context_excerpt_text": prior_context_excerpt_text,
                    "anchor_excerpt_text": str(candidate.get("sentence_text") or ""),
                    "context_excerpt_text": rendered_excerpt_text,
                    "phenomenon_evidence": list(candidate["evidence"]) + callback_evidence + window_evidence,
                    "judgeability_score": round(float(candidate["judgeability_score"]), 3),
                    "discriminative_power_score": round(float(candidate["discriminative_power_score"]), 3),
                    "ambiguity_risk": candidate["ambiguity_risk"],
                    "construction_priority": round(float(candidate["construction_priority"]) + window_priority_adjustment, 3),
                    "complete_sentence_count": complete_sentence_count,
                    "selection_reason_draft": _selection_reason_draft(
                        profile_id=profile_id,
                        sentence_text=anchor_display_text,
                        callback_target_text=callback_target_text,
                        tension_target_text=tension_target_text,
                    ),
                    "judge_focus_draft": _judge_focus_draft(
                        profile_id=profile_id,
                        callback_target_text=callback_target_text,
                        tension_target_text=tension_target_text,
                    ),
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
    structural_cue_missing = False

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
    if profile_id == "reconsolidation_later_reinterpretation" and cue_hits == 0:
        score -= RECONSOLIDATION_MISSING_CUE_PENALTY
        evidence.append("missing_reinterpretation_cue")
        structural_cue_missing = True
    if (
        language == "zh"
        and profile_id == "tension_reversal"
        and selection_role == "narrative_reflective"
        and cue_hits == 0
    ):
        score -= ZH_TENSION_MISSING_CUE_PENALTY
        evidence.append("zh_missing_tension_cue")
        structural_cue_missing = True
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
    if structural_cue_missing:
        deficit_boost = 0.0
        evidence.append("deficit_boost_suppressed")
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
    selected_signatures: set[tuple[str, str, str, str]] = set()
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
            signature = _case_signature(item)
            if signature in selected_signatures:
                continue
            case = _assembled_case(item)
            cases.append(case)
            selected_ids.add(str(item["opportunity_id"]))
            selected_signatures.add(signature)
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
        if float(item["construction_priority"]) < MIN_PROFILE_ORDER_SELECTION_PRIORITY:
            continue
        signature = _case_signature(item)
        if signature in selected_signatures:
            continue
        case = _assembled_case(item)
        cases.append(case)
        selected_ids.add(str(item["opportunity_id"]))
        selected_signatures.add(signature)
        selected_chapters[chapter_key] += 1
        selected_profiles_per_chapter[chapter_key].add(profile_id)

    reserves: list[dict[str, Any]] = []
    reserve_signatures = set(selected_signatures)
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
        signature = _case_signature(item)
        if signature in reserve_signatures:
            continue
        reserve = _assembled_reserve_case(item, reserve_rank=reserve_counts[chapter_key] + 1)
        reserves.append(reserve)
        reserve_signatures.add(signature)
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
        "excerpt_text": str(opportunity["context_excerpt_text"]).strip(),
        "excerpt_sentence_ids": excerpt_sentence_ids,
        "prior_context_sentence_ids": list(opportunity.get("prior_context_sentence_ids") or []),
        "prior_context_text": str(opportunity.get("prior_context_excerpt_text", "")).strip(),
        "anchor_sentence_id": opportunity["anchor_sentence_ids"][0],
        "question_ids": list(profile["question_ids"]),
        "phenomena": list(profile["phenomena"]),
        "selection_reason": _normalize_sentence_text(opportunity["selection_reason_draft"]),
        "judge_focus": _normalize_sentence_text(opportunity["judge_focus_draft"]),
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
        "excerpt_text": str(opportunity["context_excerpt_text"]).strip(),
        "excerpt_sentence_ids": excerpt_sentence_ids,
        "prior_context_sentence_ids": list(opportunity.get("prior_context_sentence_ids") or []),
        "prior_context_text": str(opportunity.get("prior_context_excerpt_text", "")).strip(),
        "anchor_sentence_id": opportunity["anchor_sentence_ids"][0],
        "question_ids": list(profile["question_ids"]),
        "phenomena": list(profile["phenomena"]),
        "selection_reason": _normalize_sentence_text(opportunity["selection_reason_draft"]),
        "judge_focus": _normalize_sentence_text(opportunity["judge_focus_draft"]),
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


def _clip_prompt_text(text: str, *, max_length: int) -> str:
    cleaned = _normalize_sentence_text(text)
    if len(cleaned) > max_length:
        cleaned = cleaned[: max_length - 3].rstrip() + "..."
    return cleaned


def _callback_target_prompt_text(text: str) -> str:
    return _clip_prompt_text(text, max_length=160)


def _tension_target_prompt_text(*, window_texts: list[str], language: str) -> str:
    if language != "en":
        return ""
    rendered_parts = _rendered_excerpt_parts(window_texts)
    if len(rendered_parts) < 3:
        return ""
    tension_index = next(
        (
            index
            for index, part in enumerate(rendered_parts)
            if "whether " in part.lower()
        ),
        -1,
    )
    if tension_index < 0 or tension_index + 2 >= len(rendered_parts):
        return ""
    first = rendered_parts[tension_index].lower()
    third = rendered_parts[tension_index + 2].lower()
    if "whether " not in first:
        return ""
    if not third.startswith(("it is true", "but ", "yet ", "however", "still ")):
        return ""
    first_part = rendered_parts[tension_index]
    first_marker_index = first_part.lower().find("whether ")
    if first_marker_index > 0:
        first_part = first_part[first_marker_index:]
    focus_parts = [
        _clip_prompt_text(first_part, max_length=96),
        _clip_prompt_text(rendered_parts[tension_index + 1], max_length=96),
        _clip_prompt_text(rendered_parts[tension_index + 2], max_length=96),
    ]
    return _clip_prompt_text(" / ".join(focus_parts), max_length=240)


def _selection_reason_draft(
    *,
    profile_id: str,
    sentence_text: str,
    callback_target_text: str = "",
    tension_target_text: str = "",
) -> str:
    profile = EXCERPT_TARGET_PROFILES[profile_id]
    clipped = _clip_prompt_text(sentence_text, max_length=160)
    if profile_id == "callback_bridge" and callback_target_text:
        return (
            f"{profile['selection_reason_template']} Earlier bridge target: "
            f"{callback_target_text}. Anchor line: {clipped}"
        )
    if profile_id == "tension_reversal" and tension_target_text:
        return (
            f"{profile['selection_reason_template']} Specific tension: "
            f"{tension_target_text}. Anchor line: {clipped}"
        )
    return f"{profile['selection_reason_template']} Anchor line: {clipped}"


def _selection_reason_anchor_text(*, anchor_text: str, window_texts: list[str]) -> str:
    cleaned_anchor = _normalize_sentence_text(anchor_text)
    if not cleaned_anchor:
        return ""
    if not (_needs_preceding_sentence(cleaned_anchor) or _needs_following_sentence(cleaned_anchor)):
        return cleaned_anchor
    for part in _rendered_excerpt_parts(window_texts):
        if cleaned_anchor in part:
            return part
    return cleaned_anchor


def _judge_focus_draft(
    *,
    profile_id: str,
    callback_target_text: str = "",
    tension_target_text: str = "",
) -> str:
    if profile_id == "callback_bridge" and callback_target_text:
        return (
            "Can the reader trace the backward bridge to this specific earlier "
            f"material: {callback_target_text}, while keeping the attribution of "
            "the bridging claim clear and non-associative?"
        )
    if profile_id == "tension_reversal" and tension_target_text:
        return (
            "Does the mechanism keep this exact tension in view: "
            f"{tension_target_text}, instead of flattening it into generic summary?"
        )
    return str(EXCERPT_TARGET_PROFILES[profile_id]["judge_focus_template"])


def _case_signature(opportunity: dict[str, Any]) -> tuple[str, str, str, str]:
    profile_id = str(opportunity["target_profile_ids"][0])
    excerpt_text = re.sub(r"\s+", " ", str(opportunity.get("context_excerpt_text") or "")).strip()
    prior_context_text = re.sub(
        r"\s+",
        " ",
        str(opportunity.get("prior_context_excerpt_text") or ""),
    ).strip()
    return (
        str(opportunity.get("source_id") or ""),
        profile_id,
        excerpt_text,
        prior_context_text,
    )


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
    text = _normalize_sentence_text(text)
    if language == "zh":
        return {match.group(0) for match in re.finditer(r"[\u4e00-\u9fff]{2,}", text)}
    return {token for token in re.findall(r"[A-Za-z]{4,}", text.lower()) if token not in {"that", "this", "with", "from", "have", "were"}}


def _callback_terms(text: str, language: str) -> set[str]:
    text = _normalize_sentence_text(text)
    if language == "zh":
        cleaned = re.sub(r"[^\u4e00-\u9fff]", "", text)
        if len(cleaned) < 2:
            return set()
        terms: set[str] = set()
        for size in (2, 3, 4):
            for index in range(0, max(0, len(cleaned) - size + 1)):
                term = cleaned[index : index + size]
                if term in CALLBACK_STOP_TERMS_ZH:
                    continue
                terms.add(term)
        return terms
    return {
        token
        for token in re.findall(r"[A-Za-z]{4,}", text.lower())
        if token not in CALLBACK_STOP_TERMS_EN
    }


def _callback_terms_after_first_explicit_marker(text: str, language: str) -> set[str]:
    normalized = _normalize_sentence_text(text)
    if language == "zh":
        marker_positions = [
            normalized.find(marker)
            for marker in EXPLICIT_CALLBACK_MARKERS_ZH
            if normalized.find(marker) >= 0
        ]
        if not marker_positions:
            return set()
        marker_index = min(marker_positions)
        return _callback_terms(normalized[marker_index:], language)
    lowered = normalized.lower()
    marker_positions = [
        lowered.find(marker)
        for marker in EXPLICIT_CALLBACK_MARKERS_EN
        if lowered.find(marker) >= 0
    ]
    if not marker_positions:
        return set()
    marker_index = min(marker_positions)
    return _callback_terms(normalized[marker_index:], language)


def _callback_overlap_score(overlap: set[str], language: str) -> float:
    if language == "zh":
        return sum(1.0 if len(term) == 2 else 1.6 if len(term) == 3 else 2.1 for term in overlap)
    return float(len(overlap))


def _english_inferential_callback_score(anchor_text: str, prior_text: str, *, distance: int) -> float:
    lowered_anchor = _normalize_sentence_text(anchor_text).lower()
    lowered_prior = _normalize_sentence_text(prior_text).lower()
    inferential_markers = ("from this", "from that", "from these", "from those")
    if not any(marker in lowered_anchor for marker in inferential_markers):
        return 0.0
    if distance > 2:
        return 0.0
    if len(lowered_prior) < 40:
        return 0.0
    score = 0.9
    if any(marker in lowered_prior for marker in ('"', "“", "”", "chapter", "contribution", "cause")):
        score += 0.35
    return score


def _distinctive_callback_overlap(overlap: set[str], language: str) -> set[str]:
    if language == "zh":
        return {
            term
            for term in overlap
            if len(term) >= 3 and not any(marker in term for marker in EXPLICIT_CALLBACK_MARKERS_ZH)
        }
    return {
        term
        for term in overlap
        if term not in CALLBACK_GENERIC_OVERLAP_TERMS_EN
    }


def _resolve_callback_antecedent(
    *,
    sentences: list[dict[str, Any]],
    anchor_index: int,
    language: str,
) -> dict[str, Any]:
    anchor_text = _normalize_sentence_text(sentences[anchor_index].get("text") or "")
    unresolved = {
        "resolved": False,
        "antecedent_index": -1,
        "sentence_ids": [],
        "excerpt_text": "",
        "evidence": ["callback_antecedent_missing"],
    }
    if not _has_explicit_callback_marker(anchor_text, language):
        return unresolved
    anchor_terms = _callback_terms(anchor_text, language)
    if not anchor_terms:
        return unresolved

    lookback_limit = (
        CALLBACK_LOOKBACK_SENTENCE_LIMIT_ZH if language == "zh" else CALLBACK_LOOKBACK_SENTENCE_LIMIT_EN
    )
    best_candidate: dict[str, Any] | None = None
    best_score = 0.0
    for prior_index in range(max(0, anchor_index - lookback_limit), anchor_index):
        prior_text = _normalize_sentence_text(sentences[prior_index].get("text") or "")
        if len(prior_text) < 20 or _looks_like_paratext_sentence(prior_text, language):
            continue
        overlap = anchor_terms.intersection(_callback_terms(prior_text, language))
        distinctive_overlap = _distinctive_callback_overlap(overlap, language)
        inferential_score = 0.0
        if language == "zh":
            post_marker_terms = _callback_terms_after_first_explicit_marker(anchor_text, language)
            if post_marker_terms:
                distinctive_overlap = distinctive_overlap.intersection(post_marker_terms)
        else:
            inferential_score = _english_inferential_callback_score(
                anchor_text,
                prior_text,
                distance=anchor_index - prior_index,
            )
        overlap_score = _callback_overlap_score(distinctive_overlap, language)
        if overlap_score <= 0 and inferential_score <= 0:
            continue
        distance = anchor_index - prior_index
        candidate_score = max(overlap_score, inferential_score) - (max(0, distance - 1) * 0.18)
        if _looks_fragmentary(prior_text):
            candidate_score -= 0.25
        if candidate_score <= best_score:
            continue
        prior_start, prior_end = _expand_excerpt_window(
            sentences,
            start=prior_index,
            end=min(len(sentences), prior_index + 1),
        )
        prior_rows = sentences[prior_start:prior_end]
        best_candidate = {
            "resolved": True,
            "antecedent_index": prior_index,
            "sentence_ids": [
                str(item.get("sentence_id") or "")
                for item in prior_rows
                if str(item.get("sentence_id") or "").strip()
            ],
            "excerpt_text": render_excerpt_sentences(
                item.get("text") or "" for item in prior_rows
            ),
            "evidence": [
                f"callback_antecedent_distance:{distance}",
                f"callback_overlap_score:{round(candidate_score, 3)}",
                f"callback_overlap_terms:{'|'.join(sorted(distinctive_overlap)[:4])}",
            ],
        }
        if inferential_score > 0:
            best_candidate["evidence"].append(
                f"callback_inferential_backlink:{round(inferential_score, 3)}"
            )
        best_score = candidate_score

    threshold = 1.2 if language == "zh" else 1.0
    if best_candidate is None or best_score < threshold:
        return unresolved
    return best_candidate


def _is_short_comma_fragment(text: str) -> bool:
    token_count = len(re.findall(r"[A-Za-z]+", text))
    return token_count <= 4 and bool(SHORT_COMMA_FRAGMENT_RE.match(text))


def _needs_preceding_sentence(text: str) -> bool:
    cleaned = _normalize_sentence_text(text)
    if not cleaned:
        return False
    return bool(
        LOWERCASE_START_RE.match(cleaned)
        or _is_short_comma_fragment(cleaned)
        or LEADING_BACKREFERENCE_RE.match(cleaned)
    )


def _needs_following_sentence(text: str) -> bool:
    cleaned = _normalize_sentence_text(text)
    if not cleaned:
        return False
    return bool(
        TITLE_FRAGMENT_RE.match(cleaned)
        or INITIAL_FRAGMENT_RE.match(cleaned)
        or ABBREVIATION_SUFFIX_RE.search(cleaned)
        or _has_unclosed_quote(cleaned)
        or _looks_like_cjk_continuation_end(cleaned)
    )


def _looks_fragmentary(text: str) -> bool:
    cleaned = _normalize_sentence_text(text)
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
        text = _normalize_sentence_text(raw_text)
        if not text:
            continue
        if rendered and (_needs_following_sentence(rendered[-1]) or _needs_preceding_sentence(text)):
            rendered[-1] = _join_excerpt_fragments(rendered[-1], text)
            continue
        rendered.append(text)
    return rendered


def _expand_excerpt_window(sentences: list[dict[str, Any]], *, start: int, end: int) -> tuple[int, int]:
    while start > 0 and (
        _needs_preceding_sentence(sentences[start].get("text") or "")
        or _needs_following_sentence(sentences[start - 1].get("text") or "")
    ):
        start -= 1
    while end < len(sentences) and _needs_following_sentence(sentences[end - 1].get("text") or ""):
        if end >= len(sentences):
            break
        end += 1
    return start, min(end, len(sentences))


def _refine_excerpt_window_for_profile(
    *,
    profile_id: str,
    language: str,
    sentences: list[dict[str, Any]],
    anchor_index: int,
    start: int,
    end: int,
) -> tuple[int, int]:
    if profile_id != "tension_reversal" or language != "en":
        return start, end

    window_texts = [
        _normalize_sentence_text(sentences[index].get("text") or "")
        for index in range(start, end)
    ]
    if len(_rendered_excerpt_parts(window_texts)) > 3:
        return start, end

    anchor_text = _normalize_sentence_text(sentences[anchor_index].get("text") or "").lower()
    if not any(marker in anchor_text for marker in ("however", "yet", "but", "still")):
        return start, end

    lowered_window = [text.lower() for text in window_texts]
    has_dual_tension = any(
        "whether" in text and "or whether" in text for text in lowered_window
    )
    has_argument_followthrough = any(
        text.startswith("it is true") or text.startswith("this was")
        for text in lowered_window
    )
    if not has_dual_tension or not has_argument_followthrough:
        return start, end

    return max(0, start - 1), min(len(sentences), end + 1)


def _has_explicit_callback_marker(text: str, language: str) -> bool:
    normalized = _normalize_sentence_text(text)
    lowered = normalized.lower()
    markers = EXPLICIT_CALLBACK_MARKERS_EN if language == "en" else EXPLICIT_CALLBACK_MARKERS_ZH
    if language == "en":
        return any(marker in lowered for marker in markers)
    return any(marker in normalized for marker in markers)


def _looks_like_cjk_continuation_end(text: str) -> bool:
    cleaned = _normalize_sentence_text(text)
    if not cleaned or not re.search(r"[\u4e00-\u9fff]", cleaned):
        return False
    return cleaned[-1] not in SENTENCE_END_MARKERS


def _join_excerpt_fragments(previous: str, current: str) -> str:
    if _looks_like_cjk_continuation_end(previous):
        return previous.rstrip() + current.lstrip()
    return previous.rstrip() + " " + current.lstrip()


def _looks_like_reported_speech(text: str, language: str) -> bool:
    normalized = _normalize_sentence_text(text)
    lowered = normalized.lower()
    markers = REPORTED_SPEECH_MARKERS_EN if language == "en" else REPORTED_SPEECH_MARKERS_ZH
    if language == "en":
        return ("\"" in normalized or "“" in normalized) and any(marker in lowered for marker in markers)
    return ("“" in normalized or "”" in normalized or "「" in normalized) and any(marker in normalized for marker in markers)


def _window_is_valid_for_profile(
    *,
    profile_id: str,
    anchor_text: str,
    window: list[str],
    language: str,
    callback_antecedent_resolved: bool | None = None,
) -> bool:
    rendered_excerpt = render_excerpt_sentences(window)
    if not rendered_excerpt:
        return False
    if profile_id == "callback_bridge" and not _has_explicit_callback_marker(anchor_text, language):
        return False
    if profile_id == "callback_bridge" and callback_antecedent_resolved is False:
        return False
    if profile_id == "anchored_reaction_selectivity" and _looks_like_reported_speech(anchor_text, language):
        return False
    if _looks_like_paratext_window(window, language):
        return False
    return True


def _looks_like_paratext_sentence(text: str, language: str) -> bool:
    cleaned = _normalize_sentence_text(text)
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
    cleaned: list[str] = []
    for item in window:
        normalized = _normalize_sentence_text(item)
        if normalized:
            cleaned.append(normalized)
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
    cleaned: list[str] = []
    for item in window:
        normalized = _normalize_sentence_text(item)
        if normalized:
            cleaned.append(normalized)
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
    cleaned = _normalize_sentence_text(text)
    if not cleaned:
        return False
    for opener, closer in QUOTE_PAIRS:
        if cleaned.count(opener) > cleaned.count(closer):
            return True
    if cleaned.count('"') % 2 == 1:
        return True
    return False

"""Tests for question-aligned case construction helpers."""

from __future__ import annotations

from pathlib import Path

from eval.attentional_v2.question_aligned_case_construction import (
    TARGET_PROFILE_ORDER,
    MIN_PROFILE_ORDER_SELECTION_PRIORITY,
    _assembled_case,
    _score_sentence_for_profile,
    _selection_reason_anchor_text,
    _select_cases_and_reserves,
    _window_quality_adjustment,
    _window_is_valid_for_profile,
    build_question_aligned_excerpt_scope,
    render_excerpt_sentences,
    target_profile_id_for_case_row,
)


def _chapter_row(
    *,
    source_id: str,
    language: str,
    output_dir: str,
    chapter_id: str,
    chapter_title: str,
    role: str,
) -> dict[str, object]:
    return {
        "chapter_case_id": f"{source_id}__{chapter_id}",
        "source_id": source_id,
        "book_title": f"Book {source_id}",
        "author": f"Author {source_id}",
        "language_track": language,
        "type_tags": ["essay"],
        "role_tags": [role],
        "output_dir": output_dir,
        "chapter_id": chapter_id,
        "chapter_number": 1,
        "chapter_title": chapter_title,
        "sentence_count": 6,
        "paragraph_count": 3,
        "candidate_position_bucket": "middle",
        "candidate_score": 4.5,
        "selection_status": "private_library_candidate_v2",
        "selected_for_public_benchmark": False,
        "selection_priority": 1,
        "selection_role": role,
    }


def _sentences_en() -> list[dict[str, str]]:
    return [
        {
            "sentence_id": "c1-s1",
            "text": "Rather than celebrating applause, the author defines freedom as the discipline to refuse easier comfort when the room expects surrender.",
        },
        {
            "sentence_id": "c1-s2",
            "text": "But that confidence turns out fragile, and the paragraph suddenly asks why the speaker wanted public praise at all after claiming independence.",
        },
        {
            "sentence_id": "c1-s3",
            "text": "Again the writer returns to the same promise from earlier, comparing the present hesitation with the first vow to stay intellectually solitary.",
        },
        {
            "sentence_id": "c1-s4",
            "text": "Only then does the chapter admit that the proud decision would matter differently later, after the public failure exposed its hidden need.",
        },
    ]


def _sentences_zh() -> list[dict[str, str]]:
    return [
        {
            "sentence_id": "c2-s1",
            "text": "作者不是在夸耀勇气，而是在定义一种更困难的自持：明知会失去认同，也要守住自己的判断。",
        },
        {
            "sentence_id": "c2-s2",
            "text": "但接下来的转折却很尖锐，他忽然追问自己为什么一直想得到掌声，这个问题把前面的坚定都重新压紧了。",
        },
        {
            "sentence_id": "c2-s3",
            "text": "前面那句关于独立的宣言在这里再次回来，同样的词被放进新的语境里，形成明显的回扣。",
        },
        {
            "sentence_id": "c2-s4",
            "text": "直到后来失败真正发生，这句话才显出另一层意义，原来它一直在为更晚的重新理解埋伏笔。",
        },
    ]


def _sentences_zh_with_paratext_and_prose() -> list[dict[str, str]]:
    return [
        {
            "sentence_id": "c2-s1",
            "text": "背影作者：朱自清1925年10月1925年11月22日 1925年10月在北京。",
        },
        {
            "sentence_id": "c2-s2",
            "text": "1925年11月22日《文学周报》第200期。",
        },
        {
            "sentence_id": "c2-s3",
            "text": "下文不是1928年出版同名散文集。",
        },
        {
            "sentence_id": "c2-s4",
            "text": "他待我漸漸不同往日。",
        },
        {
            "sentence_id": "c2-s5",
            "text": "但最近兩年的不見，他終於忘却我的不好，只是惦記着我，惦記着我的兒子。",
        },
        {
            "sentence_id": "c2-s6",
            "text": "我北來後，他寫了一封信給我，信中說道，「我身體平安，惟膀子疼痛利害，舉箸提筆，諸多不便，大約大去之期不遠矣。」",
        },
        {
            "sentence_id": "c2-s7",
            "text": "那年冬天，祖母死了，父親的差使也交卸了，正是禍不單行的日子，我從北京到徐州，打算跟着父親奔喪囘家。",
        },
        {
            "sentence_id": "c2-s8",
            "text": "到徐州見着父親，看見滿院狼藉的東西，又想起祖母，不禁簌簌地流下眼淚。",
        },
        {
            "sentence_id": "c2-s9",
            "text": "父親說，「事已如此，不必難過，好在天無絕人之路！」",
        },
    ]


def _sentences_zh_with_open_quote_late_scene() -> list[dict[str, str]]:
    return [
        {
            "sentence_id": "c2-s1",
            "text": "他待我漸漸不同往日。",
        },
        {
            "sentence_id": "c2-s2",
            "text": "但最近兩年的不見，他終於忘却我的不好，只是惦記着我，惦記着我的兒子。",
        },
        {
            "sentence_id": "c2-s3",
            "text": "我北來後，他寫了一封信給我，信中說道，「我身體平安，惟膀子疼痛利害，舉箸提筆，諸多不便，大約大去之期不遠矣。",
        },
        {
            "sentence_id": "c2-s4",
            "text": "那年冬天，祖母死了，父親的差使也交卸了，正是禍不單行的日子。」",
        },
    ]


def test_target_profile_id_for_case_row_supports_explicit_case_id_and_legacy_phenomena() -> None:
    assert (
        target_profile_id_for_case_row({"target_profile_id": "callback_bridge"})
        == "callback_bridge"
    )
    assert (
        target_profile_id_for_case_row(
            {"case_id": "demo__reconsolidation_later_reinterpretation__seed_v1"}
        )
        == "reconsolidation_later_reinterpretation"
    )
    assert (
        target_profile_id_for_case_row({"phenomena": ["definition_pressure"]})
        == "distinction_definition"
    )


def test_build_question_aligned_excerpt_scope_generates_cases_reserves_and_review_first_adequacy(
    tmp_path: Path,
) -> None:
    chapter_rows_by_language = {
        "en": [
            _chapter_row(
                source_id="book_en",
                language="en",
                output_dir="outputs/book_en",
                chapter_id="1",
                chapter_title="Chapter One",
                role="argumentative",
            )
        ],
        "zh": [
            _chapter_row(
                source_id="book_zh",
                language="zh",
                output_dir="outputs/book_zh",
                chapter_id="2",
                chapter_title="第二章",
                role="expository",
            )
        ],
    }
    source_index = {
        "book_en": {"source_id": "book_en", "type_tags": ["essay"], "role_tags": ["argumentative"]},
        "book_zh": {"source_id": "book_zh", "type_tags": ["essay"], "role_tags": ["expository"]},
    }
    documents = {
        str(tmp_path / "outputs" / "book_en"): {
            "chapters": [{"id": "1", "sentences": _sentences_en()}]
        },
        str(tmp_path / "outputs" / "book_zh"): {
            "chapters": [{"id": "2", "sentences": _sentences_zh()}]
        },
    }

    def document_loader(path: Path) -> dict[str, object]:
        return documents[str(path)]

    scope = build_question_aligned_excerpt_scope(
        chapter_rows_by_language=chapter_rows_by_language,
        source_index=source_index,
        existing_rows_by_language={
            "en": [
                {
                    "case_id": "legacy_en_case",
                    "target_profile_id": "distinction_definition",
                    "benchmark_status": "needs_revision",
                }
            ],
            "zh": [],
        },
        root=tmp_path,
        document_loader=document_loader,
        scope_id="demo_scope",
    )

    assert [profile["target_profile_id"] for profile in scope["target_profiles"]] == list(
        TARGET_PROFILE_ORDER
    )
    assert scope["adequacy_report"]["recommended_next_action"] == "review_existing_cases"
    assert scope["adequacy_report"]["status"] == "needs_action"

    en_cases = scope["cases_by_language"]["en"]
    zh_cases = scope["cases_by_language"]["zh"]
    en_reserves = scope["reserve_cases_by_language"]["en"]
    zh_reserves = scope["reserve_cases_by_language"]["zh"]

    assert len(en_cases) == 1
    assert len(zh_cases) == 1
    assert len(en_reserves) == 1
    assert len(zh_reserves) == 1
    assert any(card["language_track"] == "en" for card in scope["opportunity_cards"])
    assert any(card["language_track"] == "zh" for card in scope["opportunity_cards"])

    case = en_cases[0]
    reserve = en_reserves[0]
    assert case["target_profile_id"] in TARGET_PROFILE_ORDER
    assert case["opportunity_id"].startswith("book_en__1__")
    assert case["replacement_family_id"] == f"book_en::1::{case['target_profile_id']}"
    assert case["reserve_group_id"] == "book_en::1"
    assert case["benchmark_status"] == "unset"
    assert case["start_sentence_id"] == case["excerpt_sentence_ids"][0]
    assert case["end_sentence_id"] == case["excerpt_sentence_ids"][-1]
    assert reserve["reserve_rank"] == 1
    assert reserve["target_profile_id"] in TARGET_PROFILE_ORDER


def test_render_excerpt_sentences_stitches_fragmentary_sentence_splits() -> None:
    rendered = render_excerpt_sentences(
        [
            "Charles Francis Adams might then have taken his inherited rights in succession to Mr.",
            "Webster and Mr.",
            "Everett, his seniors.",
            "Between him and State Street the relation was more natural.",
        ]
    )

    assert "Mr. Webster and Mr. Everett, his seniors." in rendered
    assert rendered.endswith("Between him and State Street the relation was more natural.")


def test_render_excerpt_sentences_stitches_chinese_continuation_fragments() -> None:
    rendered = render_excerpt_sentences(
        [
            "樓屋的前面，有一塊草地，草地中間，有幾方白石，圍成了一個花園，圈",
            "子裡，臥著一枝老梅，那草地的南盡頭，山頂的平正要向南斜下去的地方，有一",
            "塊石碑立在那裡，系記這梅林的歷史的。",
        ]
    )

    assert "圈\n" not in rendered
    assert "有一\n" not in rendered
    assert rendered == (
        "樓屋的前面，有一塊草地，草地中間，有幾方白石，圍成了一個花園，圈子裡，"
        "臥著一枝老梅，那草地的南盡頭，山頂的平正要向南斜下去的地方，有一塊石碑立在那裡，系記這梅林的歷史的。"
    )


def test_assembled_case_uses_full_excerpt_sentence_bounds() -> None:
    case = _assembled_case(
        {
            "source_id": "book_en",
            "chapter_id": "1",
            "book_title": "Book",
            "author": "Author",
            "language_track": "en",
            "chapter_number": 1,
            "chapter_title": "Chapter One",
            "target_profile_ids": ["callback_bridge"],
            "excerpt_sentence_ids": ["c1-s1", "c1-s2", "c1-s3"],
            "anchor_sentence_ids": ["c1-s2"],
            "support_sentence_ids": ["c1-s1", "c1-s3"],
            "context_excerpt_text": "Sentence 1.\nSentence 2.\nSentence 3.",
            "selection_reason_draft": "Reason",
            "judge_focus_draft": "Focus",
            "construction_priority": 6.4,
            "judgeability_score": 4.8,
            "discriminative_power_score": 4.9,
            "selection_role": "argumentative",
            "type_tags": ["essay"],
            "role_tags": ["argumentative"],
            "candidate_position_bucket": "middle",
            "opportunity_id": "book_en__1__callback_bridge__opp_1",
        }
    )

    assert case["start_sentence_id"] == "c1-s1"
    assert case["end_sentence_id"] == "c1-s3"
    assert case["anchor_sentence_id"] == "c1-s2"


def test_profile_specific_window_filters_reject_generic_callback_and_reported_speech() -> None:
    assert (
        _window_is_valid_for_profile(
            profile_id="callback_bridge",
            anchor_text="No doubt it was the same old furniture, the same old patriot, and the same old President.",
            window=[
                "George Washington remained steady in the mind of Henry Adams.",
                "No doubt it was the same old furniture, the same old patriot, and the same old President.",
                "The boy took to it instinctively.",
            ],
            language="en",
        )
        is False
    )
    assert (
        _window_is_valid_for_profile(
            profile_id="anchored_reaction_selectivity",
            anchor_text="Constantly he repulsed argument: “Adams, you reason too much!”",
            window=[
                "As he said of his friend Okakura, his thought ran as a stream runs through grass.",
                "Constantly he repulsed argument: “Adams, you reason too much!”",
                "was one of his standing reproaches.",
            ],
            language="en",
        )
        is False
    )
    assert (
        _window_is_valid_for_profile(
            profile_id="distinction_definition",
            anchor_text="1925年11月22日《文学周报》第200期。",
            window=[
                "背影作者：朱自清1925年10月1925年11月22日 1925年10月在北京。",
                "1925年11月22日《文学周报》第200期。",
                "下文不是1928年出版同名散文集。",
            ],
            language="zh",
        )
        is False
    )


def test_scope_selection_skips_chinese_paratext_and_keeps_real_prose_window(tmp_path: Path) -> None:
    chapter_rows_by_language = {
        "zh": [
            _chapter_row(
                source_id="book_zh",
                language="zh",
                output_dir="outputs/book_zh",
                chapter_id="2",
                chapter_title="背影",
                role="expository",
            )
        ]
    }
    source_index = {
        "book_zh": {
            "source_id": "book_zh",
            "type_tags": ["essay"],
            "role_tags": ["expository", "narrative_reflective"],
        }
    }
    documents = {
        str(tmp_path / "outputs" / "book_zh"): {
            "chapters": [{"id": "2", "sentences": _sentences_zh_with_paratext_and_prose()}]
        }
    }

    def document_loader(path: Path) -> dict[str, object]:
        return documents[str(path)]

    scope = build_question_aligned_excerpt_scope(
        chapter_rows_by_language=chapter_rows_by_language,
        source_index=source_index,
        root=tmp_path,
        document_loader=document_loader,
        scope_id="demo_scope",
    )

    zh_cases = scope["cases_by_language"]["zh"]
    assert len(zh_cases) == 1
    assert zh_cases[0]["target_profile_id"] == "tension_reversal"
    assert zh_cases[0]["candidate_position_bucket"] in {"middle", "late"}
    assert zh_cases[0]["anchor_sentence_id"] in {"c2-s5", "c2-s6"}
    assert zh_cases[0]["start_sentence_id"] != "c2-s1"
    assert "文学周报" not in zh_cases[0]["excerpt_text"]
    assert "同名散文集" not in zh_cases[0]["excerpt_text"]


def test_window_quality_adjustment_prefers_clean_late_chinese_scene_over_early_filler() -> None:
    adjustment, evidence = _window_quality_adjustment(
        profile_id="tension_reversal",
        language="zh",
        selection_role="narrative_reflective",
        position_bucket="late",
        window=[
            "但最近兩年的不見，他終於忘却我的不好，只是惦記着我，惦記着我的兒子。",
            "我北來後，他寫了一封信給我，信中說道，「我身體平安，惟膀子疼痛利害，舉箸提筆，諸多不便，大約大去之期不遠矣。」",
            "到徐州見着父親，看見滿院狼藉的東西，又想起祖母，不禁簌簌地流下眼淚。",
        ],
    )

    assert adjustment > 1.0
    assert "zh_late_scene_bonus" in evidence
    assert "zh_scene_dialogue_bonus" in evidence

    filler_adjustment, filler_evidence = _window_quality_adjustment(
        profile_id="distinction_definition",
        language="zh",
        selection_role="narrative_reflective",
        position_bucket="early",
        window=[
            "作者不是在夸耀勇气，而是在定义一种更困难的自持：明知会失去认同，也要守住自己的判断。",
            "前面那句关于独立的宣言在这里再次回来，同样的词被放进新的语境里，形成明显的回扣。",
            "直到后来失败真正发生，这句话才显出另一层意义，原来它一直在为更晚的重新理解埋伏笔。",
        ],
    )

    assert filler_adjustment < 0
    assert "zh_early_filler_penalty" in filler_evidence


def test_reconsolidation_requires_explicit_later_cue_for_high_score() -> None:
    cue_free = _score_sentence_for_profile(
        profile_id="reconsolidation_later_reinterpretation",
        sentence_text="樓屋的前面，有一塊草地，草地中間，有幾方白石，圍成了一個花園。",
        language="zh",
        selection_role="narrative_reflective",
        role_tags=["narrative_reflective"],
        position_bucket="late",
        prior_text="前文已經鋪墊了足夠多的背景，因此這裡 technically counts as later context even though the line itself has no reinterpretive cue.",
        prior_tokens=set(),
        feedback={},
    )
    cue_hit = _score_sentence_for_profile(
        profile_id="reconsolidation_later_reinterpretation",
        sentence_text="直到后来他才明白，原来這句話一直在為更晚的重新理解埋伏筆。",
        language="zh",
        selection_role="narrative_reflective",
        role_tags=["narrative_reflective"],
        position_bucket="late",
        prior_text="前文已經鋪墊了足夠多的背景，因此這裡也有 later context。",
        prior_tokens=set(),
        feedback={},
    )

    assert "missing_reinterpretation_cue" in cue_free["evidence"]
    assert cue_free["construction_priority"] < MIN_PROFILE_ORDER_SELECTION_PRIORITY
    assert cue_hit["construction_priority"] > cue_free["construction_priority"]


def test_reconsolidation_missing_cue_suppresses_feedback_boost() -> None:
    cue_free = _score_sentence_for_profile(
        profile_id="reconsolidation_later_reinterpretation",
        sentence_text="樓屋的前面，有一塊草地，草地中間，有幾方白石，圍成了一個花園。",
        language="zh",
        selection_role="narrative_reflective",
        role_tags=["narrative_reflective"],
        position_bucket="late",
        prior_text="前文已經鋪墊了足夠多的背景，因此這裡 technically counts as later context even though the line itself has no reinterpretive cue.",
        prior_tokens=set(),
        feedback={
            "profiles": {
                "reconsolidation_later_reinterpretation": {
                    "reviewed_active": 0,
                    "needs_revision": 3,
                    "needs_replacement": 2,
                    "needs_adjudication": 0,
                }
            }
        },
    )

    assert "missing_reinterpretation_cue" in cue_free["evidence"]
    assert "deficit_boost_suppressed" in cue_free["evidence"]
    assert cue_free["construction_priority"] < MIN_PROFILE_ORDER_SELECTION_PRIORITY


def test_chinese_narrative_tension_requires_explicit_local_cue() -> None:
    cue_free = _score_sentence_for_profile(
        profile_id="tension_reversal",
        sentence_text="附近是一大平原，所以望眼連天，四面並無遮障之處，遠遠裡有一點燈火，明滅無常，森然有些鬼氣。",
        language="zh",
        selection_role="narrative_reflective",
        role_tags=["narrative_reflective"],
        position_bucket="middle",
        prior_text="前文有一些背景鋪陳。",
        prior_tokens=set(),
        feedback={
            "profiles": {
                "tension_reversal": {
                    "reviewed_active": 0,
                    "needs_revision": 2,
                    "needs_replacement": 1,
                    "needs_adjudication": 0,
                }
            }
        },
    )
    cue_hit = _score_sentence_for_profile(
        profile_id="tension_reversal",
        sentence_text="但接下来的转折却很尖锐，他忽然追问自己为什么一直想得到掌声，这个问题把前面的坚定都重新压紧了。",
        language="zh",
        selection_role="narrative_reflective",
        role_tags=["narrative_reflective"],
        position_bucket="middle",
        prior_text="前文有一些背景鋪陳。",
        prior_tokens=set(),
        feedback={},
    )

    assert "zh_missing_tension_cue" in cue_free["evidence"]
    assert "deficit_boost_suppressed" in cue_free["evidence"]
    assert cue_free["construction_priority"] < MIN_PROFILE_ORDER_SELECTION_PRIORITY
    assert cue_hit["construction_priority"] >= MIN_PROFILE_ORDER_SELECTION_PRIORITY


def test_selection_reason_anchor_text_uses_merged_line_for_fragmentary_anchor() -> None:
    anchor_text = "他家裡的人都怪他無恆性，說他的心思太活；然而依他自己講來，他以為他一個"
    merged = _selection_reason_anchor_text(
        anchor_text=anchor_text,
        window_texts=[
            "那時候他已在縣立小學堂卒了業，正在那裡換來換去的換中學堂。",
            anchor_text,
            "人同別的學生不同，不能按部就班的同他們同在一處求學的。",
        ],
    )

    assert merged.endswith("人同別的學生不同，不能按部就班的同他們同在一處求學的。")
    assert "\n" not in merged


def test_second_pass_selection_skips_subthreshold_fillers() -> None:
    cases, reserves = _select_cases_and_reserves(
        [
            {
                "opportunity_id": "demo__1__tension_reversal__opp_1",
                "chapter_case_id": "demo__1",
                "source_id": "demo",
                "book_title": "Demo",
                "author": "Author",
                "language_track": "zh",
                "chapter_id": "1",
                "chapter_number": 1,
                "chapter_title": "Chapter 1",
                "selection_role": "narrative_reflective",
                "target_profile_ids": ["tension_reversal"],
                "excerpt_sentence_ids": ["c1-s1", "c1-s2", "c1-s3"],
                "anchor_sentence_ids": ["c1-s2"],
                "support_sentence_ids": ["c1-s1", "c1-s3"],
                "prior_context_sentence_ids": [],
                "context_excerpt_text": "A.\nB.\nC.",
                "selection_reason_draft": "Reason",
                "judge_focus_draft": "Focus",
                "construction_priority": MIN_PROFILE_ORDER_SELECTION_PRIORITY,
                "judgeability_score": 4.2,
                "discriminative_power_score": 4.2,
                "candidate_position_bucket": "middle",
                "type_tags": ["essay"],
                "role_tags": ["narrative_reflective"],
            },
            {
                "opportunity_id": "demo__2__tension_reversal__opp_1",
                "chapter_case_id": "demo__2",
                "source_id": "demo",
                "book_title": "Demo",
                "author": "Author",
                "language_track": "zh",
                "chapter_id": "2",
                "chapter_number": 2,
                "chapter_title": "Chapter 2",
                "selection_role": "narrative_reflective",
                "target_profile_ids": ["tension_reversal"],
                "excerpt_sentence_ids": ["c2-s1", "c2-s2", "c2-s3"],
                "anchor_sentence_ids": ["c2-s2"],
                "support_sentence_ids": ["c2-s1", "c2-s3"],
                "prior_context_sentence_ids": [],
                "context_excerpt_text": "D.\nE.\nF.",
                "selection_reason_draft": "Reason",
                "judge_focus_draft": "Focus",
                "construction_priority": MIN_PROFILE_ORDER_SELECTION_PRIORITY - 0.1,
                "judgeability_score": 3.8,
                "discriminative_power_score": 3.8,
                "candidate_position_bucket": "middle",
                "type_tags": ["essay"],
                "role_tags": ["narrative_reflective"],
            },
        ],
        cases_per_chapter=1,
        reserves_per_chapter=1,
    )

    assert [case["chapter_id"] for case in cases] == ["1"]
    assert [reserve["chapter_id"] for reserve in reserves] == ["2"]


def test_scope_selection_expands_chinese_late_scene_when_quote_runs_past_boundary(tmp_path: Path) -> None:
    chapter_rows_by_language = {
        "zh": [
            _chapter_row(
                source_id="book_zh",
                language="zh",
                output_dir="outputs/book_zh",
                chapter_id="2",
                chapter_title="背影",
                role="narrative_reflective",
            )
        ]
    }
    source_index = {
        "book_zh": {
            "source_id": "book_zh",
            "type_tags": ["essay"],
            "role_tags": ["narrative_reflective"],
        }
    }
    documents = {
        str(tmp_path / "outputs" / "book_zh"): {
            "chapters": [{"id": "2", "sentences": _sentences_zh_with_open_quote_late_scene()}]
        }
    }

    def document_loader(path: Path) -> dict[str, object]:
        return documents[str(path)]

    scope = build_question_aligned_excerpt_scope(
        chapter_rows_by_language=chapter_rows_by_language,
        source_index=source_index,
        root=tmp_path,
        document_loader=document_loader,
        scope_id="demo_scope",
    )

    zh_case = scope["cases_by_language"]["zh"][0]
    assert zh_case["target_profile_id"] == "tension_reversal"
    assert zh_case["end_sentence_id"] == "c2-s4"
    assert "差使也交卸了" in zh_case["excerpt_text"]

"""Tests for question-aligned case construction helpers."""

from __future__ import annotations

from pathlib import Path

from eval.attentional_v2.question_aligned_case_construction import (
    CLUSTERED_SELECTION_MODE,
    CLUSTERED_TARGET_PROFILE_ORDER,
    TARGET_PROFILE_ORDER,
    MIN_PROFILE_ORDER_SELECTION_PRIORITY,
    _assembled_case,
    _expand_excerpt_window,
    _judge_focus_draft,
    _needs_preceding_sentence,
    _refine_excerpt_window_for_profile,
    _resolve_callback_antecedent,
    _score_sentence_for_profile,
    _selection_reason_anchor_text,
    _selection_reason_draft,
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


def _clustered_opportunity(
    *,
    profile_id: str,
    opportunity_id: str,
    anchor_index: int,
    excerpt_start_index: int,
    excerpt_end_index: int,
    construction_priority: float,
    judgeability_score: float = 4.5,
) -> dict[str, object]:
    source_id = "clustered_source"
    chapter_id = "17"
    excerpt_sentence_ids = [
        f"c{chapter_id}-s{sentence_index + 1}"
        for sentence_index in range(excerpt_start_index, excerpt_end_index + 1)
    ]
    anchor_sentence_id = f"c{chapter_id}-s{anchor_index + 1}"
    return {
        "opportunity_id": opportunity_id,
        "chapter_case_id": f"{source_id}__{chapter_id}",
        "source_id": source_id,
        "book_title": "Clustered Book",
        "author": "Clustered Author",
        "language_track": "en",
        "chapter_id": chapter_id,
        "chapter_number": 17,
        "chapter_title": "Clustered Chapter",
        "selection_role": "argumentative",
        "target_profile_ids": [profile_id],
        "excerpt_sentence_ids": excerpt_sentence_ids,
        "support_sentence_ids": [sentence_id for sentence_id in excerpt_sentence_ids if sentence_id != anchor_sentence_id],
        "anchor_sentence_ids": [anchor_sentence_id],
        "excerpt_start_index": excerpt_start_index,
        "excerpt_end_index": excerpt_end_index,
        "anchor_sentence_index": anchor_index,
        "prior_context_sentence_ids": [],
        "prior_context_excerpt_text": "",
        "context_excerpt_text": " ".join(f"Sentence {sentence_index + 1}." for sentence_index in range(excerpt_start_index, excerpt_end_index + 1)),
        "selection_reason_draft": f"Reason {opportunity_id}",
        "judge_focus_draft": f"Focus {opportunity_id}",
        "construction_priority": construction_priority,
        "judgeability_score": judgeability_score,
        "discriminative_power_score": construction_priority,
        "selection_priority": 1,
        "selection_role": "argumentative",
        "type_tags": ["essay"],
        "role_tags": ["argumentative"],
        "candidate_position_bucket": "middle",
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


def _sentences_zh_with_longer_callback_lookback() -> list[dict[str, str]]:
    return [
        {
            "sentence_id": "c3-s1",
            "text": "他在桥边立下誓言，宁可独行，也不愿再向掌声低头。",
        },
        {
            "sentence_id": "c3-s2",
            "text": "那时同行的人都笑他太倔，只当这句话是一时逞强。",
        },
        {
            "sentence_id": "c3-s3",
            "text": "几年里他一直把这件事压在心底，很少再提起。",
        },
        {
            "sentence_id": "c3-s4",
            "text": "等到旧友重新出现，桥边的风景和从前一样安静。",
        },
        {
            "sentence_id": "c3-s5",
            "text": "走到旧桥头时，他又一次回到那句“宁可独行”的誓言，也重新听见自己当年说话的声音。",
        },
        {
            "sentence_id": "c3-s6",
            "text": "那句旧话并没有改变意思，只是在这一刻重新被他听见。",
        },
    ]


def _sentences_en_with_near_callback_antecedent() -> list[dict[str, str]]:
    return [
        {
            "sentence_id": "c5-s1",
            "text": "At Surrenden the family had already agreed that the establishment would break up in October, and the decision shadowed every conversation.",
        },
        {
            "sentence_id": "c5-s2",
            "text": "He still delayed his departure because he hoped one last appeal might persuade his friend to stay near home.",
        },
        {
            "sentence_id": "c5-s3",
            "text": "Again, as soon as the Surrenden establishment broke up, he prepared for return home and felt the old disappointment sharpen into self-reproach.",
        },
        {
            "sentence_id": "c5-s4",
            "text": "The return looked less like a fresh beginning than a forced replay of the same mistake he thought he had finally outgrown.",
        },
    ]


def _sentences_zh_with_unresolved_callback_cue() -> list[dict[str, str]]:
    return [
        {
            "sentence_id": "c4-s1",
            "text": "他一路沉默，只觉得周围的人声越来越远。",
        },
        {
            "sentence_id": "c4-s2",
            "text": "灯光照在桥面上，把潮湿的石板映得发冷。",
        },
        {
            "sentence_id": "c4-s3",
            "text": "走到中途时，他又一次回到这个问题，却说不清究竟是哪一句话在逼近自己。",
        },
        {
            "sentence_id": "c4-s4",
            "text": "于是他只能继续往前走，心里空空地发紧。",
        },
    ]


def _sentences_en_with_generic_callback_overlap_only() -> list[dict[str, str]]:
    return [
        {
            "sentence_id": "c6-s1",
            "text": "She spoke with deliberate calm, which made the first objection sound milder than it was.",
        },
        {
            "sentence_id": "c6-s2",
            "text": "Nor, again, is it, on the face of it, consistent with those doctrines of individual liberty which he propounded in a later work.",
        },
    ]


def _sentences_en_with_distinctive_callback_overlap() -> list[dict[str, str]]:
    return [
        {
            "sentence_id": "c7-s1",
            "text": "Apart from the general tone, Mill had already identified one specific contribution that shaped the argument.",
        },
        {
            "sentence_id": "c7-s2",
            "text": "The discussion pauses over several political digressions before returning to the claim.",
        },
        {
            "sentence_id": "c7-s3",
            "text": "From this it would appear that she gave Mill that tendency to Socialism which did not accord with his earlier advocacy of peasant proprietorships.",
        },
    ]


def _sentences_en_with_inferential_callback_backlink() -> list[dict[str, str]]:
    return [
        {
            "sentence_id": "c9-s1",
            "text": "She pointed out the need of such a chapter, and the extreme imperfection of the book without it; she was the cause of my writing it.",
        },
        {
            "sentence_id": "c9-s2",
            "text": "From this it would appear that she gave Mill that tendency to Socialism which did not accord with his earlier advocacy of peasant proprietorships.",
        },
        {
            "sentence_id": "c9-s3",
            "text": "Nor, again, is it consistent with those doctrines of individual liberty which he propounded in a later work.",
        },
    ]


def _sentences_en_with_weak_single_term_callback_overlap() -> list[dict[str, str]]:
    return [
        {
            "sentence_id": "c10-s1",
            "text": "He shouldered his pack and started for home.",
        },
        {
            "sentence_id": "c10-s2",
            "text": "Again, as soon as the Surrenden establishment broke up, he prepared for return home and felt the old disappointment sharpen into self-reproach.",
        },
        {
            "sentence_id": "c10-s3",
            "text": "The return looked less like a fresh beginning than a forced replay of the same mistake he thought he had finally outgrown.",
        },
    ]


def _sentences_zh_with_marker_only_callback_overlap() -> list[dict[str, str]]:
    return [
        {
            "sentence_id": "c8-s1",
            "text": "所以他進了Ｋ府中學之後，不上半年又忽然轉了Ｈ府中學來；在Ｈ府中學住了三個月，革命就起來了。",
        },
        {
            "sentence_id": "c8-s2",
            "text": "Ｈ府中學停學之後，他依舊只能回到那小小的書齋裡來。",
        },
    ]


def _sentences_en_with_context_dependent_tension_opener() -> list[dict[str, str]]:
    return [
        {
            "sentence_id": "c11-s1",
            "text": "That disputed influence had already been described as the force that pushed Mill's argument into a new register.",
        },
        {
            "sentence_id": "c11-s2",
            "text": "Whether this was an instance of her steadying influence, or whether it added one more unassimilated element to Mill's diverse intellectual sustenance, may be wisely left an open question.",
        },
        {
            "sentence_id": "c11-s3",
            "text": "We cannot, however, be wrong in attributing to her the parentage of one book of Mill.",
        },
        {
            "sentence_id": "c11-s4",
            "text": "It is true that Mill had before learnt that men and women ought to be equal in legal and domestic relations.",
        },
    ]


def _sentences_en_with_argumentative_tension_followthrough() -> list[dict[str, str]]:
    return [
        {
            "sentence_id": "c12-s1",
            "text": "Be this as it may, she undoubtedly checked the half-recognised leanings of her husband in one important direction.",
        },
        {
            "sentence_id": "c12-s2",
            "text": "Whether this was an instance of her steadying influence, or whether it added one more unassimilated element to his argument, may be wisely left an open question.",
        },
        {
            "sentence_id": "c12-s3",
            "text": "We cannot, however, be wrong in attributing to her the parentage of one later claim.",
        },
        {
            "sentence_id": "c12-s4",
            "text": "It is true that he had already defended equality in general terms.",
        },
        {
            "sentence_id": "c12-s5",
            "text": "This was a point on which he had already argued with his father.",
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


def test_render_excerpt_sentences_normalizes_invisible_whitespace() -> None:
    rendered = render_excerpt_sentences(
        [
            "Gladstone’s offence, “singular and palpable,” was not the speech alone, but its cause\ufeff—the policy that inspired the speech.",
            "“I weakly supposed\u200b \u00a0… I really, though most strangely, believed that it was an act of friendliness.”",
            "Whatever absurdity Gladstone supposed, Russell supposed nothing of the sort.",
        ]
    )

    assert "\ufeff" not in rendered
    assert "\u200b" not in rendered
    assert "\u00a0" not in rendered
    assert "cause—the policy" in rendered
    assert "supposed … I really" in rendered


def test_needs_preceding_sentence_flags_leading_backreference_openers() -> None:
    assert (
        _needs_preceding_sentence(
            "Whether this was an instance of her steadying influence may be wisely left an open question."
        )
        is True
    )
    assert _needs_preceding_sentence("We cannot, however, be wrong in attributing this claim.") is False


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
            "prior_context_sentence_ids": ["c1-s0"],
            "prior_context_excerpt_text": "Sentence 0.",
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
    assert case["prior_context_sentence_ids"] == ["c1-s0"]
    assert case["prior_context_text"] == "Sentence 0."


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


def test_clustered_selection_allows_multiple_same_profile_cases_with_ranked_ids() -> None:
    opportunities = [
        _clustered_opportunity(
            profile_id="distinction_definition",
            opportunity_id="opp_a",
            anchor_index=1,
            excerpt_start_index=0,
            excerpt_end_index=1,
            construction_priority=8.5,
        ),
        _clustered_opportunity(
            profile_id="tension_reversal",
            opportunity_id="opp_duplicate_span",
            anchor_index=1,
            excerpt_start_index=0,
            excerpt_end_index=1,
            construction_priority=8.2,
        ),
        _clustered_opportunity(
            profile_id="distinction_definition",
            opportunity_id="opp_b",
            anchor_index=4,
            excerpt_start_index=3,
            excerpt_end_index=4,
            construction_priority=7.9,
        ),
        _clustered_opportunity(
            profile_id="distinction_definition",
            opportunity_id="opp_too_close",
            anchor_index=6,
            excerpt_start_index=6,
            excerpt_end_index=7,
            construction_priority=7.5,
        ),
        _clustered_opportunity(
            profile_id="callback_bridge",
            opportunity_id="opp_c",
            anchor_index=8,
            excerpt_start_index=8,
            excerpt_end_index=9,
            construction_priority=7.2,
        ),
        _clustered_opportunity(
            profile_id="anchored_reaction_selectivity",
            opportunity_id="opp_reserve",
            anchor_index=11,
            excerpt_start_index=11,
            excerpt_end_index=12,
            construction_priority=6.8,
        ),
    ]

    cases, reserves = _select_cases_and_reserves(
        opportunities,
        cases_per_chapter=3,
        reserves_per_chapter=1,
        target_profile_ids=tuple(CLUSTERED_TARGET_PROFILE_ORDER),
        selection_mode=CLUSTERED_SELECTION_MODE,
        same_profile_anchor_distance=3,
    )

    case_ids = [row["case_id"] for row in cases]
    reserve_ids = [row["case_id"] for row in reserves]

    assert case_ids == [
        "clustered_source__17__distinction_definition__seed_1",
        "clustered_source__17__distinction_definition__seed_2",
        "clustered_source__17__callback_bridge__seed_1",
    ]
    assert reserve_ids == [
        "clustered_source__17__anchored_reaction_selectivity__reserve_1"
    ]
    assert "clustered_source__17__tension_reversal__seed_1" not in case_ids
    assert "clustered_source__17__distinction_definition__seed_3" not in case_ids


def test_clustered_scope_excludes_reconsolidation_profile_from_active_target_list(tmp_path: Path) -> None:
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
        ]
    }
    source_index = {
        "book_en": {"source_id": "book_en", "type_tags": ["essay"], "role_tags": ["argumentative"]}
    }
    documents = {
        str(tmp_path / "outputs" / "book_en"): {
            "chapters": [{"id": "1", "sentences": _sentences_en()}]
        }
    }

    def document_loader(path: Path) -> dict[str, object]:
        return documents[str(path)]

    scope = build_question_aligned_excerpt_scope(
        chapter_rows_by_language=chapter_rows_by_language,
        source_index=source_index,
        root=tmp_path,
        document_loader=document_loader,
        scope_id="clustered_demo_scope",
        cases_per_chapter=4,
        reserves_per_chapter=2,
        target_profile_ids=tuple(CLUSTERED_TARGET_PROFILE_ORDER),
        selection_mode=CLUSTERED_SELECTION_MODE,
    )

    assert scope["selection_mode"] == CLUSTERED_SELECTION_MODE
    assert [profile["target_profile_id"] for profile in scope["target_profiles"]] == list(
        CLUSTERED_TARGET_PROFILE_ORDER
    )
    assert all(
        row["target_profile_id"] != "reconsolidation_later_reinterpretation"
        for row in scope["cases_by_language"]["en"] + scope["reserve_cases_by_language"]["en"]
    )


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


def test_selection_reason_anchor_text_normalizes_invisible_whitespace() -> None:
    merged = _selection_reason_anchor_text(
        anchor_text="“I weakly supposed\u200b \u00a0… I really, though most strangely, believed that it was an act of friendliness.”",
        window_texts=[
            "Gladstone’s offence, “singular and palpable,” was not the speech alone, but its cause\ufeff—the policy that inspired the speech.",
            "“I weakly supposed\u200b \u00a0… I really, though most strangely, believed that it was an act of friendliness.”",
            "Whatever absurdity Gladstone supposed, Russell supposed nothing of the sort.",
        ],
    )

    assert "\ufeff" not in merged
    assert "\u200b" not in merged
    assert "\u00a0" not in merged
    assert "supposed … I really" in merged


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


def test_selection_skips_exact_duplicate_excerpt_cases() -> None:
    cases, reserves = _select_cases_and_reserves(
        [
            {
                "opportunity_id": "demo__1__callback_bridge__opp_1",
                "chapter_case_id": "demo__1",
                "source_id": "demo",
                "book_title": "Demo",
                "author": "Author",
                "language_track": "en",
                "chapter_id": "1",
                "chapter_number": 1,
                "chapter_title": "Chapter 1",
                "selection_role": "argumentative",
                "target_profile_ids": ["callback_bridge"],
                "excerpt_sentence_ids": ["c1-s1", "c1-s2", "c1-s3"],
                "anchor_sentence_ids": ["c1-s2"],
                "support_sentence_ids": ["c1-s1", "c1-s3"],
                "prior_context_sentence_ids": ["c1-s0"],
                "prior_context_excerpt_text": "Earlier line.",
                "context_excerpt_text": "A.\nB.\nC.",
                "selection_reason_draft": "Reason",
                "judge_focus_draft": "Focus",
                "construction_priority": MIN_PROFILE_ORDER_SELECTION_PRIORITY + 0.3,
                "judgeability_score": 4.3,
                "discriminative_power_score": 4.3,
                "candidate_position_bucket": "middle",
                "type_tags": ["essay"],
                "role_tags": ["argumentative"],
            },
            {
                "opportunity_id": "demo__2__callback_bridge__opp_1",
                "chapter_case_id": "demo__2",
                "source_id": "demo",
                "book_title": "Demo",
                "author": "Author",
                "language_track": "en",
                "chapter_id": "2",
                "chapter_number": 2,
                "chapter_title": "Chapter 2",
                "selection_role": "argumentative",
                "target_profile_ids": ["callback_bridge"],
                "excerpt_sentence_ids": ["c2-s1", "c2-s2", "c2-s3"],
                "anchor_sentence_ids": ["c2-s2"],
                "support_sentence_ids": ["c2-s1", "c2-s3"],
                "prior_context_sentence_ids": ["c2-s0"],
                "prior_context_excerpt_text": "Earlier line.",
                "context_excerpt_text": "A.\nB.\nC.",
                "selection_reason_draft": "Reason",
                "judge_focus_draft": "Focus",
                "construction_priority": MIN_PROFILE_ORDER_SELECTION_PRIORITY,
                "judgeability_score": 4.0,
                "discriminative_power_score": 4.0,
                "candidate_position_bucket": "middle",
                "type_tags": ["essay"],
                "role_tags": ["argumentative"],
            },
        ],
        cases_per_chapter=1,
        reserves_per_chapter=1,
    )

    assert [case["chapter_id"] for case in cases] == ["1"]
    assert reserves == []


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


def test_scope_selection_preserves_longer_lookback_for_callback_bridge(tmp_path: Path) -> None:
    chapter_rows_by_language = {
        "zh": [
            _chapter_row(
                source_id="book_zh_callback",
                language="zh",
                output_dir="outputs/book_zh_callback",
                chapter_id="3",
                chapter_title="第三章",
                role="narrative_reflective",
            )
        ]
    }
    source_index = {
        "book_zh_callback": {
            "source_id": "book_zh_callback",
            "type_tags": ["essay"],
            "role_tags": ["narrative_reflective", "reference_heavy"],
        }
    }
    documents = {
        str(tmp_path / "outputs" / "book_zh_callback"): {
            "chapters": [{"id": "3", "sentences": _sentences_zh_with_longer_callback_lookback()}]
        }
    }

    def document_loader(path: Path) -> dict[str, object]:
        return documents[str(path)]

    scope = build_question_aligned_excerpt_scope(
        chapter_rows_by_language=chapter_rows_by_language,
        source_index=source_index,
        root=tmp_path,
        document_loader=document_loader,
        scope_id="callback_scope",
    )

    zh_case = scope["cases_by_language"]["zh"][0]
    assert zh_case["target_profile_id"] == "callback_bridge"
    assert zh_case["anchor_sentence_id"] == "c3-s5"
    assert zh_case["prior_context_sentence_ids"] == ["c3-s1"]
    assert "宁可独行" in zh_case["prior_context_text"]
    assert zh_case["start_sentence_id"] != "c3-s1"


def test_expand_excerpt_window_pulls_in_preceding_sentence_for_whether_this_opener() -> None:
    sentences = _sentences_en_with_context_dependent_tension_opener()

    start, end = _expand_excerpt_window(sentences, start=1, end=4)

    assert (start, end) == (0, 4)
    rendered = render_excerpt_sentences(
        sentence["text"] for sentence in sentences[start:end]
    )
    assert "That disputed influence had already been described" in rendered
    assert "Whether this was an instance of her steadying influence" in rendered


def test_refine_excerpt_window_expands_english_tension_followthrough() -> None:
    sentences = _sentences_en_with_argumentative_tension_followthrough()

    start, end = _refine_excerpt_window_for_profile(
        profile_id="tension_reversal",
        language="en",
        sentences=sentences,
        anchor_index=2,
        start=1,
        end=4,
    )

    assert (start, end) == (0, 5)


def test_scope_selection_inlines_near_callback_antecedent_into_excerpt(tmp_path: Path) -> None:
    chapter_rows_by_language = {
        "en": [
            _chapter_row(
                source_id="book_en_callback",
                language="en",
                output_dir="outputs/book_en_callback",
                chapter_id="5",
                chapter_title="Chapter Five",
                role="narrative_reflective",
            )
        ]
    }
    source_index = {
        "book_en_callback": {
            "source_id": "book_en_callback",
            "type_tags": ["essay"],
            "role_tags": ["narrative_reflective", "reference_heavy"],
        }
    }
    documents = {
        str(tmp_path / "outputs" / "book_en_callback"): {
            "chapters": [{"id": "5", "sentences": _sentences_en_with_near_callback_antecedent()}]
        }
    }

    def document_loader(path: Path) -> dict[str, object]:
        return documents[str(path)]

    scope = build_question_aligned_excerpt_scope(
        chapter_rows_by_language=chapter_rows_by_language,
        source_index=source_index,
        root=tmp_path,
        document_loader=document_loader,
        scope_id="callback_scope_near_inline",
    )

    en_case = next(
        case
        for case in [*scope["cases_by_language"]["en"], *scope["reserve_cases_by_language"]["en"]]
        if case["target_profile_id"] == "callback_bridge"
    )
    assert en_case["target_profile_id"] == "callback_bridge"
    assert en_case["anchor_sentence_id"] == "c5-s3"
    assert en_case["start_sentence_id"] == "c5-s1"
    assert en_case["prior_context_sentence_ids"] == []
    assert "Surrenden" in en_case["excerpt_text"]


def test_scope_selection_keeps_full_english_argumentative_tension_turn(tmp_path: Path) -> None:
    chapter_rows_by_language = {
        "en": [
            _chapter_row(
                source_id="book_en_tension",
                language="en",
                output_dir="outputs/book_en_tension",
                chapter_id="12",
                chapter_title="Chapter Twelve",
                role="narrative_reflective",
            )
        ]
    }
    source_index = {
        "book_en_tension": {
            "source_id": "book_en_tension",
            "type_tags": ["essay"],
            "role_tags": ["narrative_reflective", "reference_heavy"],
        }
    }
    documents = {
        str(tmp_path / "outputs" / "book_en_tension"): {
            "chapters": [{"id": "12", "sentences": _sentences_en_with_argumentative_tension_followthrough()}]
        }
    }

    def document_loader(path: Path) -> dict[str, object]:
        return documents[str(path)]

    scope = build_question_aligned_excerpt_scope(
        chapter_rows_by_language=chapter_rows_by_language,
        source_index=source_index,
        root=tmp_path,
        document_loader=document_loader,
        scope_id="english_tension_scope",
    )

    en_case = scope["cases_by_language"]["en"][0]
    assert en_case["target_profile_id"] == "tension_reversal"
    assert en_case["start_sentence_id"] == "c12-s1"
    assert en_case["end_sentence_id"] == "c12-s5"
    assert "Be this as it may" in en_case["excerpt_text"]
    assert "This was a point" in en_case["excerpt_text"]


def test_callback_bridge_judge_focus_emphasizes_traceability_and_attribution(tmp_path: Path) -> None:
    chapter_rows_by_language = {
        "en": [
            _chapter_row(
                source_id="book_en_callback",
                language="en",
                output_dir="outputs/book_en_callback",
                chapter_id="5",
                chapter_title="Chapter Five",
                role="reference_heavy",
            )
        ]
    }
    source_index = {
        "book_en_callback": {
            "source_id": "book_en_callback",
            "type_tags": ["essay"],
            "role_tags": ["reference_heavy"],
        }
    }
    documents = {
        str(tmp_path / "outputs" / "book_en_callback"): {
            "chapters": [{"id": "5", "sentences": _sentences_en_with_near_callback_antecedent()}]
        }
    }

    def document_loader(path: Path) -> dict[str, object]:
        return documents[str(path)]

    scope = build_question_aligned_excerpt_scope(
        chapter_rows_by_language=chapter_rows_by_language,
        source_index=source_index,
        root=tmp_path,
        document_loader=document_loader,
        scope_id="callback_scope_focus",
    )

    en_case = next(
        case
        for case in [*scope["cases_by_language"]["en"], *scope["reserve_cases_by_language"]["en"]]
        if case["target_profile_id"] == "callback_bridge"
    )
    assert en_case["target_profile_id"] == "callback_bridge"
    assert "trace" in en_case["judge_focus"].lower()
    assert "attribution" in en_case["judge_focus"].lower()
    assert "forward-moving argumentative connection" in en_case["judge_focus"].lower()
    assert "surrenden" in en_case["judge_focus"].lower()
    assert "surrenden" in en_case["selection_reason"].lower()
    assert "source-grounded" in en_case["selection_reason"].lower()


def test_callback_bridge_drafts_name_specific_earlier_target() -> None:
    target_text = (
        "She pointed out the need of such a chapter, and the extreme imperfection "
        "of the book without it; she was the cause of my writing it."
    )

    selection_reason = _selection_reason_draft(
        profile_id="callback_bridge",
        sentence_text=(
            "From this it would appear that she gave Mill that tendency to "
            "Socialism which did not accord with his earlier advocacy of peasant proprietorships."
        ),
        callback_target_text=target_text,
    )
    judge_focus = _judge_focus_draft(
        profile_id="callback_bridge",
        callback_target_text=target_text,
    )

    assert "earlier bridge target" in selection_reason.lower()
    assert "cause of my writing it" in selection_reason.lower()
    assert "specific earlier material" in judge_focus.lower()
    assert "cause of my writing it" in judge_focus.lower()


def test_argumentative_callback_bridge_drafts_anchor_to_target_with_source_attribution() -> None:
    target_text = (
        "Society can and does execute its own mandates: and if it issues wrong "
        "mandates instead of right, or any mandates at all in things with which it "
        "ought not to meddle."
    )
    anchor_text = (
        "Protection, therefore, against the tyranny of the magistrate is not "
        "enough: there needs protection also against the tyranny of the prevailing "
        "opinion and feeling."
    )

    selection_reason = _selection_reason_draft(
        profile_id="callback_bridge",
        sentence_text=anchor_text,
        callback_target_text=target_text,
        selection_role="argumentative",
        author="John Stuart Mill",
        book_title="On Liberty",
    )
    judge_focus = _judge_focus_draft(
        profile_id="callback_bridge",
        sentence_text=anchor_text,
        callback_target_text=target_text,
        selection_role="argumentative",
        author="John Stuart Mill",
        book_title="On Liberty",
    )

    assert "backward bridge from" in selection_reason.lower()
    assert "advances the argument" in selection_reason.lower()
    assert "john stuart mill's on liberty" in selection_reason.lower()
    assert "protection, therefore" in judge_focus.lower()
    assert "john stuart mill's on liberty" in judge_focus.lower()
    assert "forward-moving argumentative connection" in judge_focus.lower()


def test_tension_reversal_drafts_specific_dual_claim_focus() -> None:
    tension_target_text = (
        "Whether this was an instance of her steadying influence, or whether it added "
        "one more unassimilated element to his argument, may be wisely left an open "
        "question. / We cannot, however, be wrong in attributing to her the parentage "
        "of one later claim. / It is true that he had already defended equality in "
        "general terms."
    )

    selection_reason = _selection_reason_draft(
        profile_id="tension_reversal",
        sentence_text="We cannot, however, be wrong in attributing to her the parentage of one later claim.",
        tension_target_text=tension_target_text,
    )
    judge_focus = _judge_focus_draft(
        profile_id="tension_reversal",
        tension_target_text=tension_target_text,
    )

    assert "specific tension" in selection_reason.lower()
    assert "steadying influence" in selection_reason.lower()
    assert "later claim" in judge_focus.lower()
    assert "already defended equality" in judge_focus.lower()


def test_scope_selection_builds_specific_tension_focus_for_followthrough_window(tmp_path: Path) -> None:
    chapter_rows_by_language = {
        "en": [
            _chapter_row(
                source_id="book_en_tension",
                language="en",
                output_dir="outputs/book_en_tension",
                chapter_id="12",
                chapter_title="Chapter Twelve",
                role="argumentative",
            )
        ]
    }
    source_index = {
        "book_en_tension": {
            "source_id": "book_en_tension",
            "type_tags": ["essay"],
            "role_tags": ["argumentative", "reference_heavy"],
        }
    }
    documents = {
        str(tmp_path / "outputs" / "book_en_tension"): {
            "chapters": [{"id": "12", "sentences": _sentences_en_with_argumentative_tension_followthrough()}]
        }
    }

    def document_loader(path: Path) -> dict[str, object]:
        return documents[str(path)]

    scope = build_question_aligned_excerpt_scope(
        chapter_rows_by_language=chapter_rows_by_language,
        source_index=source_index,
        root=tmp_path,
        document_loader=document_loader,
        scope_id="tension_scope_focus",
    )

    en_case = next(
        case
        for case in [*scope["cases_by_language"]["en"], *scope["reserve_cases_by_language"]["en"]]
        if case["target_profile_id"] == "tension_reversal"
    )
    assert "specific tension" in en_case["selection_reason"].lower()
    assert "steadying influence" in en_case["judge_focus"].lower()
    assert "later claim" in en_case["judge_focus"].lower()
    assert "already defended equality" in en_case["judge_focus"].lower()


def test_scope_selection_rejects_callback_bridge_without_resolved_antecedent(tmp_path: Path) -> None:
    chapter_rows_by_language = {
        "zh": [
            _chapter_row(
                source_id="book_zh_unresolved",
                language="zh",
                output_dir="outputs/book_zh_unresolved",
                chapter_id="4",
                chapter_title="第四章",
                role="narrative_reflective",
            )
        ]
    }
    source_index = {
        "book_zh_unresolved": {
            "source_id": "book_zh_unresolved",
            "type_tags": ["essay"],
            "role_tags": ["narrative_reflective"],
        }
    }
    documents = {
        str(tmp_path / "outputs" / "book_zh_unresolved"): {
            "chapters": [{"id": "4", "sentences": _sentences_zh_with_unresolved_callback_cue()}]
        }
    }

    def document_loader(path: Path) -> dict[str, object]:
        return documents[str(path)]

    scope = build_question_aligned_excerpt_scope(
        chapter_rows_by_language=chapter_rows_by_language,
        source_index=source_index,
        root=tmp_path,
        document_loader=document_loader,
        scope_id="callback_scope_negative",
    )

    assert all(
        case["target_profile_id"] != "callback_bridge"
        for case in scope["cases_by_language"]["zh"]
    )


def test_resolve_callback_antecedent_rejects_generic_english_overlap_only() -> None:
    sentences = _sentences_en_with_generic_callback_overlap_only()

    result = _resolve_callback_antecedent(
        sentences=sentences,
        anchor_index=1,
        language="en",
    )

    assert result["resolved"] is False


def test_resolve_callback_antecedent_keeps_distinctive_english_overlap() -> None:
    sentences = _sentences_en_with_distinctive_callback_overlap()

    result = _resolve_callback_antecedent(
        sentences=sentences,
        anchor_index=2,
        language="en",
    )

    assert result["resolved"] is True
    assert result["antecedent_index"] == 0
    assert "mill" in "|".join(result["evidence"]).lower()


def test_resolve_callback_antecedent_keeps_inferential_english_backlink() -> None:
    sentences = _sentences_en_with_inferential_callback_backlink()

    result = _resolve_callback_antecedent(
        sentences=sentences,
        anchor_index=1,
        language="en",
    )

    assert result["resolved"] is True
    assert result["antecedent_index"] == 0
    assert any("inferential_backlink" in evidence for evidence in result["evidence"])


def test_resolve_callback_antecedent_rejects_weak_single_term_english_overlap() -> None:
    sentences = _sentences_en_with_weak_single_term_callback_overlap()

    result = _resolve_callback_antecedent(
        sentences=sentences,
        anchor_index=1,
        language="en",
    )

    assert result["resolved"] is False


def test_resolve_callback_antecedent_rejects_marker_only_chinese_overlap() -> None:
    sentences = _sentences_zh_with_marker_only_callback_overlap()

    result = _resolve_callback_antecedent(
        sentences=sentences,
        anchor_index=1,
        language="zh",
    )

    assert result["resolved"] is False

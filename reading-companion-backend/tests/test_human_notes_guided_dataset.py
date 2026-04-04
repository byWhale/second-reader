from __future__ import annotations

import json
from pathlib import Path

from eval.attentional_v2.human_notes_guided_dataset import (
    HUMAN_NOTES_GUIDED_SOURCE_IDS,
    build_human_notes_guided_cluster_plan,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _chapter_row(
    *,
    source_id: str,
    book_title: str,
    language_track: str,
    chapter_id: str,
    chapter_number: int,
    chapter_title: str,
    sentence_count: int,
) -> dict[str, object]:
    return {
        "chapter_case_id": f"{source_id}__{chapter_id}",
        "source_id": source_id,
        "book_title": book_title,
        "author": f"{book_title} Author",
        "language_track": language_track,
        "chapter_id": chapter_id,
        "chapter_number": chapter_number,
        "chapter_title": chapter_title,
        "sentence_count": sentence_count,
    }


def _entry(
    *,
    notes_id: str,
    entry_id: str,
    linked_source_id: str,
    matched_chapter_id: str,
    quote: str,
    section_label: str,
    raw_locator: str = "",
) -> dict[str, object]:
    return {
        "notes_id": notes_id,
        "entry_id": entry_id,
        "linked_source_id": linked_source_id,
        "alignment_status": "aligned",
        "matched_chapter_id": matched_chapter_id,
        "quote": quote,
        "note": "",
        "section_label": section_label,
        "raw_locator": raw_locator,
        "matched_sentence_ids": [f"{matched_chapter_id}_s1"],
        "matched_sentence_span": {
            "start_sentence_id": f"{matched_chapter_id}_s1",
            "end_sentence_id": f"{matched_chapter_id}_s2",
        },
    }


def test_build_human_notes_guided_cluster_plan_uses_notes_catalog_and_selects_eight_clusters(tmp_path: Path) -> None:
    root = tmp_path
    notes_catalog_path = root / "state" / "dataset_build" / "library_notes_catalog.json"

    source_records = [
        {"source_id": "value_of_others_private_en", "title": "The Value of Others", "language": "en"},
        {"source_id": "xidaduo_private_zh", "title": "悉达多", "language": "zh"},
        {"source_id": "huochu_shengming_de_yiyi_private_zh", "title": "活出生命的意义", "language": "zh"},
        {"source_id": "nawaer_baodian_private_zh", "title": "纳瓦尔宝典", "language": "zh"},
        {"source_id": "mangge_zhi_dao_private_zh", "title": "芒格之道", "language": "zh"},
    ]
    chapter_rows_by_language = {
        "en": [
            _chapter_row(
                source_id="value_of_others_private_en",
                book_title="The Value of Others",
                language_track="en",
                chapter_id="11",
                chapter_number=11,
                chapter_title="Chapter 11",
                sentence_count=92,
            ),
        ],
        "zh": [
            _chapter_row(
                source_id="xidaduo_private_zh",
                book_title="悉达多",
                language_track="zh",
                chapter_id="4",
                chapter_number=4,
                chapter_title="尘世间",
                sentence_count=70,
            ),
            _chapter_row(
                source_id="xidaduo_private_zh",
                book_title="悉达多",
                language_track="zh",
                chapter_id="8",
                chapter_number=8,
                chapter_title="儿子",
                sentence_count=58,
            ),
            _chapter_row(
                source_id="xidaduo_private_zh",
                book_title="悉达多",
                language_track="zh",
                chapter_id="9",
                chapter_number=9,
                chapter_title="唵",
                sentence_count=61,
            ),
            _chapter_row(
                source_id="xidaduo_private_zh",
                book_title="悉达多",
                language_track="zh",
                chapter_id="10",
                chapter_number=10,
                chapter_title="乔文达",
                sentence_count=63,
            ),
            _chapter_row(
                source_id="huochu_shengming_de_yiyi_private_zh",
                book_title="活出生命的意义",
                language_track="zh",
                chapter_id="1",
                chapter_number=1,
                chapter_title="第一部分 在集中营的经历",
                sentence_count=108,
            ),
            _chapter_row(
                source_id="huochu_shengming_de_yiyi_private_zh",
                book_title="活出生命的意义",
                language_track="zh",
                chapter_id="5",
                chapter_number=5,
                chapter_title="追求意义",
                sentence_count=95,
            ),
            _chapter_row(
                source_id="nawaer_baodian_private_zh",
                book_title="纳瓦尔宝典",
                language_track="zh",
                chapter_id="12",
                chapter_number=0,
                chapter_title="第一章 积累财富",
                sentence_count=2,
            ),
            _chapter_row(
                source_id="nawaer_baodian_private_zh",
                book_title="纳瓦尔宝典",
                language_track="zh",
                chapter_id="13",
                chapter_number=0,
                chapter_title="财富正文延续",
                sentence_count=118,
            ),
            _chapter_row(
                source_id="nawaer_baodian_private_zh",
                book_title="纳瓦尔宝典",
                language_track="zh",
                chapter_id="24",
                chapter_number=0,
                chapter_title="第二章 增强判断力",
                sentence_count=2,
            ),
            _chapter_row(
                source_id="nawaer_baodian_private_zh",
                book_title="纳瓦尔宝典",
                language_track="zh",
                chapter_id="25",
                chapter_number=0,
                chapter_title="判断力正文延续",
                sentence_count=104,
            ),
            _chapter_row(
                source_id="mangge_zhi_dao_private_zh",
                book_title="芒格之道",
                language_track="zh",
                chapter_id="2007",
                chapter_number=2007,
                chapter_title="2007年 西科金融股东会讲话",
                sentence_count=52,
            ),
            _chapter_row(
                source_id="mangge_zhi_dao_private_zh",
                book_title="芒格之道",
                language_track="zh",
                chapter_id="2010",
                chapter_number=2010,
                chapter_title="2010年 西科金融股东会讲话",
                sentence_count=56,
            ),
            _chapter_row(
                source_id="mangge_zhi_dao_private_zh",
                book_title="芒格之道",
                language_track="zh",
                chapter_id="2019",
                chapter_number=2019,
                chapter_title="2019年 Daily Journal 股东会讲话",
                sentence_count=64,
            ),
            _chapter_row(
                source_id="mangge_zhi_dao_private_zh",
                book_title="芒格之道",
                language_track="zh",
                chapter_id="2020",
                chapter_number=2020,
                chapter_title="2020年 Daily Journal 股东会讲话",
                sentence_count=66,
            ),
        ],
    }

    assets = [
        {
            "notes_id": f"{source_id}__notes",
            "linked_source_id": source_id,
            "relative_notes_path": f"state/library_notes/raw_exports/{source_id}/raw_export.md",
            "entries_rel_path": f"state/library_notes/entries/{source_id}.jsonl",
        }
        for source_id in HUMAN_NOTES_GUIDED_SOURCE_IDS
    ]
    entries = [
        _entry(
            notes_id="value_of_others_private_en__notes",
            entry_id="value_1",
            linked_source_id="value_of_others_private_en",
            matched_chapter_id="11",
            quote="A page-50 highlight",
            section_label="Band 41-100",
            raw_locator="p.50",
        ),
        _entry(
            notes_id="value_of_others_private_en__notes",
            entry_id="value_2",
            linked_source_id="value_of_others_private_en",
            matched_chapter_id="11",
            quote="A page-76 highlight",
            section_label="Band 41-100",
            raw_locator="p.76",
        ),
        _entry(
            notes_id="value_of_others_private_en__notes",
            entry_id="value_3",
            linked_source_id="value_of_others_private_en",
            matched_chapter_id="11",
            quote="A page-170 highlight",
            section_label="Band 161-200",
            raw_locator="p.170",
        ),
        _entry(
            notes_id="value_of_others_private_en__notes",
            entry_id="value_4",
            linked_source_id="value_of_others_private_en",
            matched_chapter_id="11",
            quote="A page-182 highlight",
            section_label="Band 161-200",
            raw_locator="p.182",
        ),
        _entry(
            notes_id="xidaduo_private_zh__notes",
            entry_id="xidaduo_1",
            linked_source_id="xidaduo_private_zh",
            matched_chapter_id="8",
            quote="儿子让悉达多彻底陷入世人的爱执",
            section_label="儿子",
        ),
        _entry(
            notes_id="xidaduo_private_zh__notes",
            entry_id="xidaduo_2",
            linked_source_id="xidaduo_private_zh",
            matched_chapter_id="9",
            quote="悉达多甚至怀疑自觉的价值被高估",
            section_label="唵",
        ),
        _entry(
            notes_id="xidaduo_private_zh__notes",
            entry_id="xidaduo_3",
            linked_source_id="xidaduo_private_zh",
            matched_chapter_id="10",
            quote="探索意味着拥有目标，发现则意味着自由",
            section_label="乔文达",
        ),
        _entry(
            notes_id="xidaduo_private_zh__notes",
            entry_id="xidaduo_4",
            linked_source_id="xidaduo_private_zh",
            matched_chapter_id="4",
            quote="时间和金钱已经蒙受损失",
            section_label="尘世间",
        ),
        _entry(
            notes_id="huochu_shengming_de_yiyi_private_zh__notes",
            entry_id="huochu_1",
            linked_source_id="huochu_shengming_de_yiyi_private_zh",
            matched_chapter_id="1",
            quote="爱是人类终身追求的最高目标",
            section_label="第一部分 在集中营的经历",
        ),
        _entry(
            notes_id="huochu_shengming_de_yiyi_private_zh__notes",
            entry_id="huochu_2",
            linked_source_id="huochu_shengming_de_yiyi_private_zh",
            matched_chapter_id="5",
            quote="你不应该追问抽象的生命意义",
            section_label="追求意义",
        ),
        _entry(
            notes_id="nawaer_baodian_private_zh__notes",
            entry_id="nawaer_1",
            linked_source_id="nawaer_baodian_private_zh",
            matched_chapter_id="12",
            quote="追求财富，而不是金钱或地位",
            section_label="第一章 积累财富",
        ),
        _entry(
            notes_id="nawaer_baodian_private_zh__notes",
            entry_id="nawaer_2",
            linked_source_id="nawaer_baodian_private_zh",
            matched_chapter_id="24",
            quote="方向比速度更重要",
            section_label="第二章 增强判断力",
        ),
        _entry(
            notes_id="mangge_zhi_dao_private_zh__notes",
            entry_id="mangge_1",
            linked_source_id="mangge_zhi_dao_private_zh",
            matched_chapter_id="2007",
            quote="通往成功之路的第一步都是爱上这行",
            section_label="2007年 西科金融股东会讲话",
        ),
        _entry(
            notes_id="mangge_zhi_dao_private_zh__notes",
            entry_id="mangge_2",
            linked_source_id="mangge_zhi_dao_private_zh",
            matched_chapter_id="2010",
            quote="很多人整天忙得没有时间思考",
            section_label="2010年 Daily Journal 股东会讲话",
        ),
        _entry(
            notes_id="mangge_zhi_dao_private_zh__notes",
            entry_id="mangge_3",
            linked_source_id="mangge_zhi_dao_private_zh",
            matched_chapter_id="2019",
            quote="活得明白的人不会被嫉妒支配",
            section_label="2019年 Daily Journal 股东会讲话",
        ),
        _entry(
            notes_id="mangge_zhi_dao_private_zh__notes",
            entry_id="mangge_4",
            linked_source_id="mangge_zhi_dao_private_zh",
            matched_chapter_id="2020",
            quote="与优秀的人结伴而行，自己先得配得上",
            section_label="2020年 Daily Journal 股东会讲话",
        ),
    ]
    _write_json(
        notes_catalog_path,
        {
            "version": 1,
            "updated_at": "2026-04-04T00:00:00Z",
            "assets": assets,
            "entries": entries,
        },
    )

    plan = build_human_notes_guided_cluster_plan(
        root=root,
        source_records=source_records,
        chapter_rows_by_language=chapter_rows_by_language,
    )

    assert plan["selected_source_ids"] == list(HUMAN_NOTES_GUIDED_SOURCE_IDS)
    assert plan["resolution_summary"]["selected_cluster_count"] == 8
    assert len(plan["selected_clusters"]) == 8
    assert len(plan["selection_groups"]) == 8
    assert len(plan["source_note_summaries"]) == 5
    assert any(len(cluster["chapter_case_ids"]) > 1 for cluster in plan["selected_clusters"])
    assert (
        sum(
            1
            for row in plan["selected_chapter_rows_by_language"]["en"]
            if row["chapter_case_id"] == "value_of_others_private_en__11"
        )
        == 2
    )
    assert any(
        cluster["cluster_id"] == "nawaer_baodian_private_zh__wealth" and len(cluster["chapter_case_ids"]) == 2
        for cluster in plan["selected_clusters"]
    )
    assert any(
        cluster["cluster_id"] == "nawaer_baodian_private_zh__judgment" and len(cluster["chapter_case_ids"]) == 2
        for cluster in plan["selected_clusters"]
    )
    assert any(
        row["selection_group_kind"] == "notes_guided_cluster"
        for rows in plan["selected_chapter_rows_by_language"].values()
        for row in rows
    )
    assert len(plan["selected_chapter_case_ids"]) > len(plan["selected_clusters"])
    assert plan["source_note_summaries"][0]["notes_asset_count"] == 1
    assert any(
        proposal["proposal_status"] == "eligible" and proposal["source_id"] == "value_of_others_private_en"
        for proposal in plan["cluster_proposals"]
    )

"""Tests for managed library notes registration and alignment."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from eval.attentional_v2.user_level_selective_v1 import DATASET_ID as ACTIVE_USER_LEVEL_DATASET_ID
from eval.attentional_v2.library_notes import (
    LibraryNotesPaths,
    align_entry_to_book_document,
    load_notes_catalog,
    parse_google_books_markdown,
    parse_wechat_markdown,
    refresh_registered_notes_asset,
    register_notes_export,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, payload: object) -> None:
    _write(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def test_parse_google_books_markdown_extracts_entries() -> None:
    markdown = """# Walden Notes

## Chapter 3
| *I went to the woods because I wished to live deliberately.* [12](https://books.google.com/) This is the core motive. |
| *Simplify, simplify.* [15](https://books.google.com/) |
"""

    parsed = parse_google_books_markdown(markdown, fallback_title="walden.md")

    assert parsed["source_format"] == "google_books_markdown"
    assert parsed["title"] == "Walden Notes"
    assert len(parsed["entries"]) == 2
    assert parsed["entries"][0]["chapter_hint_number"] == 3
    assert parsed["entries"][0]["page_hint"] == "12"
    assert parsed["entries"][0]["note_text"] == "This is the core motive."


def test_parse_wechat_markdown_extracts_blockquotes() -> None:
    markdown = """# 走出唯一真理观

## 第3章 真理问题
> 真理并不是单数。
我的批注：这是关键转折。

> 方法必须对对象负责。
"""

    parsed = parse_wechat_markdown(markdown, fallback_title="wechat.md")

    assert parsed["source_format"] == "wechat_markdown"
    assert parsed["title"] == "走出唯一真理观"
    assert len(parsed["entries"]) == 2
    assert parsed["entries"][0]["chapter_hint_number"] == 3
    assert parsed["entries"][0]["note_text"] == "这是关键转折。"
    assert parsed["entries"][1]["quote_text"] == "方法必须对对象负责。"


def test_parse_wechat_markdown_extracts_bullets_and_inline_thoughts() -> None:
    markdown = """### **《纳瓦尔宝典》**

### **第一章 积累财富**
- 追求财富，而不是金钱或地位。

- **2023/09/25 发表想法**

  放大！

  > 原文：不需要他人为你打工，也不需要他人给你投资，你就可以把劳动成果放大成百上千倍。
"""

    parsed = parse_wechat_markdown(markdown, fallback_title="naval.md")

    assert len(parsed["entries"]) == 2
    assert parsed["entries"][0]["quote_text"] == "追求财富，而不是金钱或地位。"
    assert parsed["entries"][0]["section_label"] == "第一章 积累财富"
    assert parsed["entries"][1]["quote_text"] == "不需要他人为你打工，也不需要他人给你投资，你就可以把劳动成果放大成百上千倍。"
    assert parsed["entries"][1]["note_text"] == "放大！"


def test_align_entry_to_book_document_returns_sentence_span() -> None:
    book_document = {
        "chapters": [
            {
                "id": 3,
                "chapter_number": 3,
                "title": "真理问题",
                "sentences": [
                    {
                        "sentence_id": "c3-s1",
                        "paragraph_index": 1,
                        "text": "真理并不是单数。",
                        "locator": {"paragraph_index": 1},
                    },
                    {
                        "sentence_id": "c3-s2",
                        "paragraph_index": 2,
                        "text": "方法必须对对象负责。",
                        "locator": {"paragraph_index": 2},
                    },
                ],
            }
        ]
    }
    entry = {
        "chapter_hint_number": 3,
        "chapter_hint_title": "真理问题",
        "quote_text": "方法必须对对象负责。",
    }

    alignment = align_entry_to_book_document(entry, book_document)

    assert alignment["status"] == "aligned"
    assert alignment["sentence_start_id"] == "c3-s2"
    assert alignment["sentence_end_id"] == "c3-s2"


def test_align_entry_to_book_document_falls_back_beyond_title_page_candidate() -> None:
    book_document = {
        "chapters": [
            {
                "id": 12,
                "chapter_number": 0,
                "title": "第一章 积累财富",
                "sentences": [
                    {
                        "sentence_id": "c12-s1",
                        "paragraph_index": 1,
                        "text": "第一章 积累财富",
                    },
                    {
                        "sentence_id": "c12-s2",
                        "paragraph_index": 2,
                        "text": "赚钱不是一件想做就能做的事情，而是一门需要学习的技能。",
                    },
                ],
            },
            {
                "id": 13,
                "chapter_number": 0,
                "title": "认识财富创造的原理",
                "sentences": [
                    {
                        "sentence_id": "c13-s1",
                        "paragraph_index": 1,
                        "text": "认识财富创造的原理",
                    },
                    {
                        "sentence_id": "c13-s2",
                        "paragraph_index": 2,
                        "text": "赚钱跟工作的努力程度没什么必然联系。",
                    },
                ],
            },
        ]
    }
    entry = {
        "chapter_hint_title": "第一章 积累财富",
        "quote": "赚钱跟工作的努力程度没什么必然联系。",
    }

    alignment = align_entry_to_book_document(entry, book_document)

    assert alignment["status"] == "aligned"
    assert alignment["match_type"] == "exact_sentence"
    assert alignment["chapter_id"] == "13"
    assert alignment["sentence_start_id"] == "c13-s2"
    assert alignment["sentence_end_id"] == "c13-s2"


def test_register_notes_export_preserves_unresolved_and_aligns_linked_entries(tmp_path: Path) -> None:
    paths = LibraryNotesPaths.from_root(tmp_path)
    source_catalog_path = tmp_path / "state" / "dataset_build" / "source_catalog.json"
    _write_json(
        source_catalog_path,
        {
            "records": [
                {
                    "source_id": "zouchu_weiyi_zhenliguan_zh",
                    "title": "走出唯一真理观",
                    "output_dir": "output/zouchu-weiyi-zhenliguan",
                }
            ]
        },
    )
    _write_json(
        tmp_path / "output" / "zouchu-weiyi-zhenliguan" / "public" / "book_document.json",
        {
            "chapters": [
                {
                    "id": 3,
                    "chapter_number": 3,
                    "title": "真理问题",
                    "sentences": [
                        {
                            "sentence_id": "c3-s1",
                            "paragraph_index": 1,
                            "text": "真理并不是单数。",
                            "locator": {"paragraph_index": 1},
                        }
                    ],
                }
            ]
        },
    )
    linked_export = tmp_path / "linked.md"
    _write(
        linked_export,
        """# 走出唯一真理观

## 第3章 真理问题
> 真理并不是单数。
我的批注：这是关键转折。
""",
    )
    unresolved_export = tmp_path / "unknown.md"
    _write(
        unresolved_export,
        """# Unknown Book

## Chapter 1
> A line with no linked source.
""",
    )

    register_notes_export(
        paths,
        raw_export_path=linked_export,
        source_catalog_path=source_catalog_path,
        source_format="wechat_markdown",
    )
    register_notes_export(
        paths,
        raw_export_path=unresolved_export,
        source_catalog_path=source_catalog_path,
        source_format="wechat_markdown",
    )

    catalog = load_notes_catalog(paths.notes_catalog_json_path)
    assert catalog["asset_count"] == 2
    assert catalog["entry_count"] == 2
    linked_entry = next(entry for entry in catalog["entries"] if entry["title"] == "走出唯一真理观")
    unresolved_entry = next(entry for entry in catalog["entries"] if entry["title"] == "Unknown Book")
    assert linked_entry["source_link_status"] == "linked"
    assert linked_entry["alignment_status"] == "aligned"
    assert unresolved_entry["source_link_status"] == "unresolved"
    assert unresolved_entry["alignment"]["match_type"] == "unlinked_source"
    assert paths.notes_catalog_md_path.exists()


def test_register_library_notes_cli_writes_catalog(tmp_path: Path) -> None:
    source_catalog_path = tmp_path / "state" / "dataset_build" / "source_catalog.json"
    _write_json(
        source_catalog_path,
        {
            "records": [
                {
                    "source_id": "walden_205_en",
                    "title": "Walden Notes",
                }
            ]
        },
    )
    raw_export = tmp_path / "walden.md"
    _write(
        raw_export,
        """# Walden Notes

## Chapter 3
| *I went to the woods because I wished to live deliberately.* [12](https://books.google.com/) |
""",
    )
    command = [
        sys.executable,
        str(Path(__file__).resolve().parents[1] / "eval" / "attentional_v2" / "register_library_notes.py"),
        "--root",
        str(tmp_path),
        "--source-catalog",
        str(source_catalog_path),
        "--notes-id",
        "walden_notes_en",
        "--linked-source-id",
        "walden_205_en",
        "--title",
        "Walden Notes",
        "--language",
        "en",
        "--origin-path",
        str(raw_export),
        "--notes-format",
        "google_books_markdown",
    ]

    completed = subprocess.run(command, capture_output=True, text=True, check=False)

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["registered_asset_count"] == 1
    catalog = load_notes_catalog(tmp_path / "state" / "dataset_build" / "library_notes_catalog.json")
    assert catalog["asset_count"] == 1


def test_refresh_registered_notes_asset_realigns_with_current_aligner(tmp_path: Path) -> None:
    paths = LibraryNotesPaths.from_root(tmp_path)
    source_catalog_path = tmp_path / "state" / "dataset_build" / "source_catalog.json"
    _write_json(
        source_catalog_path,
        {
            "records": [
                {
                    "source_id": "book_a",
                    "title": "Book A",
                    "output_dir": "output/book_a",
                }
            ]
        },
    )
    _write_json(
        tmp_path / "output" / "book_a" / "public" / "book_document.json",
        {
            "chapters": [
                {
                    "id": 8,
                    "chapter_number": 1,
                    "title": "第一部分",
                    "sentences": [
                        {
                            "sentence_id": "c8-s77",
                            "paragraph_index": 1,
                            "text": "每当看到狱友吸烟时，我们就知道他已失去了生活下去的勇气。",
                            "locator": {"paragraph_index": 1},
                        },
                        {
                            "sentence_id": "c8-s78",
                            "paragraph_index": 1,
                            "text": "勇气一旦失去，几乎就不可能再挽回。",
                            "locator": {"paragraph_index": 1},
                        },
                    ],
                }
            ]
        },
    )
    raw_export = tmp_path / "book_a_notes.md"
    _write(
        raw_export,
        """# Book A

## 第一部分
> 每当看到狱友吸烟时，我们就知道他已失去了生活下去的勇气。勇气一旦失去，几乎就不可能再挽回。
""",
    )

    register_notes_export(
        paths,
        raw_export_path=raw_export,
        source_catalog_path=source_catalog_path,
        source_format="wechat_markdown",
        explicit_source_id="book_a",
    )

    entries_path = tmp_path / "state" / "library_notes" / "entries" / "book_a.jsonl"
    rows = [json.loads(line) for line in entries_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows[0]["alignment_status"] = "aligned"
    rows[0]["matched_chapter_id"] = "8"
    rows[0]["matched_sentence_span"] = {
        "start_sentence_id": "c8-s77",
        "end_sentence_id": "c8-s77",
        "paragraph_start": 1,
        "paragraph_end": 1,
    }
    rows[0]["matched_sentence_ids"] = ["c8-s77"]
    rows[0]["alignment"] = {
        "status": "aligned",
        "match_type": "fuzzy_sentence",
        "score": 77.0,
        "chapter_id": "8",
        "chapter_title": "第一部分",
        "sentence_start_id": "c8-s77",
        "sentence_end_id": "c8-s77",
        "paragraph_start": 1,
        "paragraph_end": 1,
        "aligned_text": "每当看到狱友吸烟时，我们就知道他已失去了生活下去的勇气。",
    }
    entries_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )

    refreshed = refresh_registered_notes_asset(
        paths,
        notes_id="book_a",
        source_catalog_path=source_catalog_path,
    )

    refresh_summary = refreshed["refresh_summary"]
    assert refresh_summary["changed_entry_count"] == 1
    assert refresh_summary["changed_entries"][0]["old_match_type"] == "fuzzy_sentence"
    assert refresh_summary["changed_entries"][0]["new_match_type"] == "exact_chapter_span"
    assert refresh_summary["changed_entries"][0]["new_end_sentence_id"] == "c8-s78"

    updated_rows = [json.loads(line) for line in entries_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    updated_alignment = updated_rows[0]["alignment"]
    assert updated_alignment["match_type"] == "exact_chapter_span"
    assert updated_rows[0]["matched_sentence_span"]["end_sentence_id"] == "c8-s78"


def test_refresh_registered_notes_asset_uses_active_benchmark_fallback_when_refresh_worsens_alignment(
    tmp_path: Path,
) -> None:
    paths = LibraryNotesPaths.from_root(tmp_path)
    source_catalog_path = tmp_path / "state" / "dataset_build" / "source_catalog.json"
    _write_json(
        source_catalog_path,
        {
            "records": [
                {
                    "source_id": "book_a",
                    "title": "Book A",
                    "output_dir": "output/book_a",
                }
            ]
        },
    )
    _write_json(
        tmp_path / "output" / "book_a" / "public" / "book_document.json",
        {
            "chapters": [
                {
                    "id": 8,
                    "chapter_number": 1,
                    "title": "第一部分",
                    "sentences": [
                        {
                            "sentence_id": "c8-s77",
                            "paragraph_index": 1,
                            "text": "每当看到狱友吸烟时，我们就知道他已失去了生活下去的勇气。",
                            "locator": {"paragraph_index": 1},
                        },
                        {
                            "sentence_id": "c29-s195",
                            "paragraph_index": 40,
                            "text": "[1] 译者注：犬儒主义，古希腊四大学派之一，主张清心寡欲，鄙视荣华富贵，力倡回归自然。",
                            "locator": {"paragraph_index": 40},
                        },
                    ],
                }
            ]
        },
    )
    raw_export = tmp_path / "book_a_notes.md"
    _write(
        raw_export,
        """# Book A

## 第一部分
> 斯宾诺莎在《伦理学》中谈到 “作为痛苦的激情，一旦我们对它有了清晰而明确的认识，就不再感到痛苦了”。
""",
    )

    register_notes_export(
        paths,
        raw_export_path=raw_export,
        source_catalog_path=source_catalog_path,
        source_format="wechat_markdown",
        explicit_source_id="book_a",
    )

    active_dataset_dir = (
        tmp_path
        / "state"
        / "eval_local_datasets"
        / "user_level_benchmarks"
        / ACTIVE_USER_LEVEL_DATASET_ID
    )
    active_dataset_dir.mkdir(parents=True, exist_ok=True)
    (active_dataset_dir / "note_cases.jsonl").write_text(
        json.dumps(
            {
                "note_case_id": "book_a__book_a__e0001",
                "note_id": "book_a__e0001",
                "source_chapter_id": 8,
                "chapter_title": "第一部分",
                "source_span_text": "斯宾诺莎在 《伦理学》中谈到 “作为痛苦的激情，一旦我们对它有了清晰而明确的认识，就不再感到痛苦了”。",
                "provenance": {
                    "alignment_match_type": "fuzzy_sentence",
                    "alignment_score": 98.99,
                    "start_sentence_id": "c8-s77",
                    "end_sentence_id": "c8-s77",
                },
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    entries_path = tmp_path / "state" / "library_notes" / "entries" / "book_a.jsonl"
    rows = [json.loads(line) for line in entries_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows[0]["alignment_status"] = "unresolved"
    rows[0]["matched_chapter_id"] = "29"
    rows[0]["matched_sentence_span"] = {
        "start_sentence_id": "c29-s195",
        "end_sentence_id": "c29-s195",
        "paragraph_start": 40,
        "paragraph_end": 40,
    }
    rows[0]["matched_sentence_ids"] = ["c29-s195"]
    rows[0]["alignment"] = {
        "status": "unresolved",
        "match_type": "fuzzy_sentence",
        "score": 10.753,
        "chapter_id": "29",
        "chapter_title": "第一部分",
        "sentence_start_id": "c29-s195",
        "sentence_end_id": "c29-s195",
        "paragraph_start": 40,
        "paragraph_end": 40,
        "aligned_text": "[1] 译者注：犬儒主义，古希腊四大学派之一，主张清心寡欲，鄙视荣华富贵，力倡回归自然。",
    }
    entries_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )

    refreshed = refresh_registered_notes_asset(
        paths,
        notes_id="book_a",
        source_catalog_path=source_catalog_path,
    )

    refresh_summary = refreshed["refresh_summary"]
    assert refresh_summary["changed_entry_count"] == 1
    assert refresh_summary["changed_entries"][0]["new_start_sentence_id"] == "c8-s77"
    assert refresh_summary["changed_entries"][0]["new_match_type"] == "fuzzy_sentence"

    updated_rows = [json.loads(line) for line in entries_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert updated_rows[0]["alignment_status"] == "aligned"
    assert updated_rows[0]["matched_sentence_span"]["start_sentence_id"] == "c8-s77"

"""Tests for chapter markdown rendering."""

from __future__ import annotations

from src.iterator_reader.markdown import render_chapter_markdown


def test_render_chapter_markdown_keeps_reactions_in_reading_order():
    """Rendered markdown should follow paragraph order and separate quotes from notes."""
    chapter = {
        "id": 1,
        "title": "A Beginning",
        "chapter_number": 1,
        "status": "pending",
        "level": 1,
        "segments": [],
    }
    segments = [
        {
            "segment_id": "1.1",
            "summary": "作者把关系理解为一种道德训练",
            "verdict": "pass",
            "reactions": [
                {
                    "type": "highlight",
                    "anchor_quote": "Relationships teach us what self-regard cannot.",
                    "content": "这句话像是在说，人只能在他人那里被迫长大。",
                    "search_results": [],
                },
                {
                    "type": "association",
                    "content": "它让我想到把关系理解成训练场，而不是奖赏池的那些伦理传统。",
                    "search_results": [],
                },
                {
                    "type": "curious",
                    "content": "查了一圈后，我更倾向于把它看成一种把依赖视为道德关系起点的关系伦理，而不只是抽象的成长修辞。",
                    "search_query": "care ethics dependence moral growth",
                    "search_results": [
                        {
                            "title": "Internet Encyclopedia of Philosophy",
                            "url": "https://iep.utm.edu/care-ethics/",
                            "snippet": "Care ethics emphasizes relationships and dependency.",
                            "score": 0.92,
                        }
                    ],
                },
            ],
            "reflection_summary": "保留。",
        },
        {
            "segment_id": "1.2",
            "summary": "这一段主要在重复前文论点",
            "verdict": "skip",
            "reactions": [],
            "reflection_summary": "跳过。",
        },
    ]

    output = render_chapter_markdown(chapter, segments, "zh")

    assert "# Chapter 1: A Beginning" in output
    assert "## 段落 1.1：作者把关系理解为一种道德训练" in output
    assert "💡 划线\n\n> \"Relationships teach us what self-regard cannot.\"" in output
    assert "这句话像是在说，人只能在他人那里被迫长大。" in output
    assert "✍️ 联想\n\n它让我想到把关系理解成训练场" in output
    assert "🔍 好奇\n\n查了一圈后，我更倾向于把它看成一种把依赖视为道德关系起点的关系伦理" in output
    assert "> 🔎 _搜索: care ethics dependence moral growth_" in output
    assert "> 参考: [Internet Encyclopedia of Philosophy](https://iep.utm.edu/care-ethics/)" in output
    assert "1.2" not in output
    assert "跳过" not in output


def test_render_chapter_markdown_uses_english_search_labels():
    """English output should render English labels for curious reactions."""
    chapter = {
        "id": 2,
        "title": "Chapter Two",
        "chapter_number": 2,
        "status": "pending",
        "level": 1,
        "segments": [],
    }
    segments = [
        {
            "segment_id": "2.1",
            "summary": "Selection and fit",
            "verdict": "pass",
            "reactions": [
                {
                    "type": "curious",
                    "content": "After checking a few sources, this idea looks closest to organizational fit arguments about reducing coordination and maintenance costs, though the analogy is still looser than the author suggests.",
                    "search_query": "fit reduces maintenance cost organizational theory",
                    "search_results": [
                        {
                            "title": "A useful source",
                            "url": "https://example.com/source",
                            "snippet": "Snippet",
                            "score": 0.8,
                        }
                    ],
                }
            ],
            "reflection_summary": "Keep.",
        }
    ]

    output = render_chapter_markdown(chapter, segments, "en")

    assert "# Chapter 2: Chapter Two" in output
    assert "## Section 2.1: Selection and fit" in output
    assert "🔍 Curious\n\nAfter checking a few sources, this idea looks closest to organizational fit arguments" in output
    assert "> 🔎 _Search: fit reduces maintenance cost organizational theory_" in output
    assert "> Sources: [A useful source](https://example.com/source)" in output


def test_render_chapter_markdown_supports_discern_and_connect_back():
    """New reaction types should render with their own emojis."""
    chapter = {
        "id": 3,
        "title": "Definition and critique",
        "chapter_number": 3,
        "status": "pending",
        "level": 1,
        "segments": [],
    }
    segments = [
        {
            "segment_id": "3.1",
            "summary": "Definition and critique",
            "verdict": "pass",
            "reactions": [
                {
                    "type": "discern",
                    "anchor_quote": "markets are net positive for society",
                    "content": "这里有个隐含前提：负面效应何时仍能被判为净正面？",
                    "search_results": [],
                },
                {
                    "type": "connect_back",
                    "content": "这和前文 1.4 对关系规则的讨论形成了呼应。",
                    "search_results": [],
                },
            ],
            "reflection_summary": "Keep.",
        }
    ]

    output = render_chapter_markdown(chapter, segments, "zh")

    assert "# Chapter 3: Definition and critique" in output
    assert "⚡ 审辩\n\n> \"markets are net positive for society\"" in output
    assert "这里有个隐含前提：负面效应何时仍能被判为净正面？" in output
    assert "🔗 回溯\n\n这和前文 1.4 对关系规则的讨论形成了呼应。" in output


def test_render_chapter_markdown_appends_chapter_reflection_block():
    """Chapter-level insights should be appended after section notes."""
    chapter = {
        "id": 4,
        "title": "Chapter Four",
        "chapter_number": 4,
        "status": "pending",
        "level": 1,
        "segments": [],
    }
    segments = [
        {
            "segment_id": "4.1",
            "summary": "Key section",
            "verdict": "pass",
            "reactions": [
                {
                    "type": "association",
                    "content": "A useful note.",
                    "search_results": [],
                }
            ],
            "reflection_summary": "Keep.",
        }
    ]

    output = render_chapter_markdown(
        chapter,
        segments,
        "en",
        chapter_reflection={
            "chapter_insights": [
                "The chapter moves from definition to critique.",
                "Its key tension is utility versus reciprocity.",
            ]
        },
    )

    assert "## Chapter Reflection" in output
    assert "- The chapter moves from definition to critique." in output
    assert "- Its key tension is utility versus reciprocity." in output

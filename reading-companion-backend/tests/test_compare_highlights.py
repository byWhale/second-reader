"""Tests for highlight comparison helpers."""

from __future__ import annotations

from pathlib import Path

from eval.compare_highlights import (
    fuzzy_ratio,
    is_direct_match,
    parse_agent_reactions,
    parse_human_highlights,
)


def test_parse_simple_human_highlights(tmp_path: Path):
    """Simple chapter markdown should parse blockquotes and notes."""
    file_path = tmp_path / "highlights.md"
    file_path.write_text(
        """## Chapter 1

> "The essential features of a marketplace don't change."

我的批注：这里是总纲句。

> "Marketplaces don't have illusions about human nature."
""",
        encoding="utf-8",
    )

    items = parse_human_highlights(file_path, 1)

    assert len(items) == 2
    assert items[0].quote == 'The essential features of a marketplace don\'t change.'
    assert items[0].note == "这里是总纲句。"
    assert items[1].quote == "Marketplaces don't have illusions about human nature."


def test_parse_google_books_highlights(tmp_path: Path):
    """Google Books export chapter block should parse quotes and inline notes."""
    file_path = tmp_path / "google.md"
    file_path.write_text(
        """# All your annotations

## *Chapter 1*

|  ![][image2] *Self-interest is the primary driver of mutuality.* 这句很重要 November 1, 2025 [104](http://example.com)  |
| ----- |

## *Chapter 2*
""",
        encoding="utf-8",
    )

    items = parse_human_highlights(file_path, 1)

    assert len(items) == 1
    assert items[0].quote == "Self-interest is the primary driver of mutuality."
    assert items[0].note == "这句很重要"
    assert items[0].source == "p.104"


def test_parse_agent_reactions_reads_blockquotes_and_notes(tmp_path: Path):
    """Agent markdown parser should keep sections, quote anchors, and notes."""
    file_path = tmp_path / "chapter.md"
    file_path.write_text(
        """# Chapter 1

## Section 1.1: Opening

💡 Highlight

> "People want things from other people."

This is the transactional premise.

🔍 Curious

> "move away from others"

Why call this antisocial?

> 🔎 _Search: antisocial vs a-social_
> Sources: [Result](https://example.com)
""",
        encoding="utf-8",
    )

    items = parse_agent_reactions(file_path)

    assert len(items) == 2
    assert items[0].section_ref == "1.1"
    assert items[0].quote == "People want things from other people."
    assert items[0].note == "This is the transactional premise."
    assert items[1].reaction_type == "curious"
    assert items[1].note == "Why call this antisocial?"


def test_parse_agent_reactions_supports_discern_and_connect_back(tmp_path: Path):
    """Agent markdown parser should support the expanded reaction set."""
    file_path = tmp_path / "chapter.md"
    file_path.write_text(
        """# Chapter 3

## Section 3.1: Opening

⚡ 审辩

> "markets are net positive for society"

这里有个隐含前提。

🔗 回溯

> "people must learn reciprocity"

这和前面 1.4 的规则讨论形成呼应。
""",
        encoding="utf-8",
    )

    items = parse_agent_reactions(file_path)

    assert len(items) == 2
    assert items[0].reaction_type == "discern"
    assert items[1].reaction_type == "connect_back"


def test_direct_match_accepts_containment_and_fuzzy_overlap():
    """Direct matching should accept contained excerpts and close paraphrases."""
    contained = is_direct_match(
        "People want things from other people.",
        "People want things from other people. This is why other people represent both a potential solution and a potential problem.",
    )
    fuzzy = is_direct_match(
        "the media in which unequal goods of comparable value are exchanged",
        "As a result, we can refine our definition of relationships even further to be the media in which unequal goods of comparable value are exchanged.",
    )

    assert contained[0] is True
    assert fuzzy[0] is True
    assert fuzzy_ratio("want has a double meaning", "to want has a double meaning") > 70

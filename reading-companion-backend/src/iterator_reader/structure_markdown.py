"""Readable Markdown rendering for book structure output."""

from __future__ import annotations

from .language import markdown_labels
from .models import BookStructure


def render_structure_markdown(structure: BookStructure) -> str:
    """Render structure.json into a readable markdown overview."""
    output_language = structure.get("output_language", "en")
    labels = markdown_labels(output_language)
    book = structure.get("book", "")
    author = structure.get("author", "")
    book_language = structure.get("book_language", "unknown")
    chapters = structure.get("chapters", [])

    if output_language == "zh":
        lines = [
            f"# 结构总览：{book}",
            "",
            f"- 作者：{author or 'Unknown'}",
            f"- 书籍语言：{book_language}",
            f"- 输出语言：{structure.get('output_language', 'unknown')}",
            f"- 章节数：{len(chapters)}",
            "",
            "## 章节目录",
            "",
        ]
        for chapter in chapters:
            lines.append(
                f"- {chapter.get('title')} ({len(chapter.get('segments', []))} 个语义单元)"
            )
        lines.append("")
    else:
        lines = [
            f"# Structure Overview: {book}",
            "",
            f"- Author: {author or 'Unknown'}",
            f"- Book language: {book_language}",
            f"- Output language: {structure.get('output_language', 'unknown')}",
            f"- Chapters: {len(chapters)}",
            "",
            "## Table of Contents",
            "",
        ]
        for chapter in chapters:
            lines.append(
                f"- {chapter.get('title')} ({len(chapter.get('segments', []))} semantic units)"
            )
        lines.append("")

    for chapter in chapters:
        if output_language == "zh":
            lines.append(f"## {chapter.get('title')}")
            lines.append("")
            lines.append(f"- 状态：{chapter.get('status', 'pending')}")
            lines.append(f"- 语义单元数：{len(chapter.get('segments', []))}")
            lines.append("")
            for index, segment in enumerate(chapter.get("segments", []), start=1):
                lines.append(
                    f"### 段落 {index}：{segment.get('summary', '')}"
                )
                lines.append("")
                lines.append(f"- 估算 tokens：{segment.get('tokens', 0)}")
                lines.append(
                    f"- 段落范围：P{segment.get('paragraph_start', 0)}-P{segment.get('paragraph_end', 0)}"
                )
                lines.append("")
        else:
            lines.append(f"## {chapter.get('title')}")
            lines.append("")
            lines.append(f"- Status: {chapter.get('status', 'pending')}")
            lines.append(f"- Semantic units: {len(chapter.get('segments', []))}")
            lines.append("")
            for index, segment in enumerate(chapter.get("segments", []), start=1):
                lines.append(
                    f"### {labels['section']} {index}: {segment.get('summary', '')}"
                )
                lines.append("")
                lines.append(f"- Estimated tokens: {segment.get('tokens', 0)}")
                lines.append(
                    f"- Paragraph span: P{segment.get('paragraph_start', 0)}-P{segment.get('paragraph_end', 0)}"
                )
                lines.append("")

    return "\n".join(lines).rstrip() + "\n"

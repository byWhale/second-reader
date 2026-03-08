"""EPUB output writer for generated reading notes."""

import os
from pathlib import Path

import ebooklib
from ebooklib import epub


def create_notes_epub(
    book_title: str,
    notes: str,
    thought_structure: str = "",
    output_path: str = "notes.epub",
) -> None:
    """Create an EPUB file from generated reading notes.

    Args:
        book_title: Title of the original book
        notes: Generated reading notes content
        thought_structure: Optional thought structure content
        output_path: Path for output EPUB file
    """
    # Create EPUB book
    book = epub.EpubBook()

    # Set metadata
    book.set_identifier(f"notes-{book_title}")
    book.set_title(f"阅读笔记 - {book_title}")
    book.set_language("zh-CN")
    book.add_author("Reading Companion")

    # Create chapters
    chapters = []

    # Notes chapter
    notes_chapter = epub.EpubHtml(
        title="共读笔记",
        file_name="notes.xhtml",
        lang="zh-CN",
    )
    notes_content = f"""
    <html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <title>共读笔记</title>
        <style>
            body {{ font-family: serif; padding: 1em; line-height: 1.6; }}
            h1 {{ text-align: center; color: #333; }}
            p {{ text-indent: 2em; margin-bottom: 1em; }}
        </style>
    </head>
    <body>
        <h1>共读笔记</h1>
        {notes}
    </body>
    </html>
    """
    notes_chapter.content = notes_content
    book.add_item(notes_chapter)
    chapters.append(notes_chapter)

    # Thought structure chapter (if exists)
    if thought_structure:
        structure_chapter = epub.EpubHtml(
            title="思想结构图",
            file_name="structure.xhtml",
            lang="zh-CN",
        )
        structure_content = f"""
        <html xmlns="http://www.w3.org/1999/xhtml">
        <head>
            <title>思想结构图</title>
            <style>
                body {{ font-family: serif; padding: 1em; line-height: 1.6; }}
                h1 {{ text-align: center; color: #333; }}
                p {{ text-indent: 2em; margin-bottom: 1em; }}
            </style>
        </head>
        <body>
            <h1>思想结构图</h1>
            {thought_structure}
        </body>
        </html>
        """
        structure_chapter.content = structure_content
        book.add_item(structure_chapter)
        chapters.append(structure_chapter)

    # Add chapters to book
    book.toc = tuple(chapters)

    # Add spine
    book.spine = ["nav"] + chapters

    # Add nav file
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # Write EPUB file
    epub.write_epub(output_path, book, {})


def create_notes_markdown(
    book_title: str,
    notes: str,
    thought_structure: str = "",
    output_path: str = "notes.md",
) -> None:
    """Create a Markdown file from generated reading notes.

    Args:
        book_title: Title of the original book
        notes: Generated reading notes content
        thought_structure: Optional thought structure content
        output_path: Path for output Markdown file
    """
    content = f"# 阅读笔记 - {book_title}\n\n"
    content += "## 共读笔记\n\n"
    content += notes + "\n\n"

    if thought_structure:
        content += "## 思想结构图\n\n"
        content += thought_structure + "\n\n"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

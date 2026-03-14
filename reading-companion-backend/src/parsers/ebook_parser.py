"""Ebook parsing module for EPUB, MOBI, and PDF formats."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, TypedDict

import ebooklib
from ebooklib import epub
from pymupdf import Document as PdfDocument

try:
    import mobi
except ImportError:
    mobi = None


class Chapter(TypedDict, total=False):
    """Parsed ebook chapter"""
    title: str
    content: str
    level: int  # TOC hierarchy level (1 for main chapters, 2 for subchapters)
    start_page: Optional[int]  # For PDF
    end_page: Optional[int]    # For PDF
    item_id: str
    href: str
    spine_index: int


def parse_ebook(file_path: str) -> list[Chapter]:
    """Parse an ebook file and extract chapter structure and content.

    Args:
        file_path: Path to the ebook file

    Returns:
        List of Chapter dicts with title, content, level, and page info

    Raises:
        ValueError: If the file format is not supported
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".epub":
        return _parse_epub(file_path)
    elif ext == ".pdf":
        return _parse_pdf(file_path)
    elif ext == ".mobi" or ext == ".azw":
        return _parse_mobi(file_path)
    elif ext == ".txt":
        return _parse_txt(file_path)
    else:
        raise ValueError(f"Unsupported ebook format: {ext}")


def _parse_epub(file_path: str) -> list[Chapter]:
    """Parse EPUB file and extract chapters from TOC."""
    book = epub.read_epub(file_path)

    chapters = []
    spine_index_by_id = {
        idref: index
        for index, (idref, _linear) in enumerate(book.spine)
        if idref != "nav"
    }

    # Try to get TOC (Table of Contents)
    toc_id = None
    try:
        toc = book.get_metadata('NCX', 'toc')
        if toc:
            toc_id = toc[0][0] if toc else None
    except (KeyError, AttributeError):
        pass  # NCX metadata not available in newer EPUB format

    # Get all items in the book
    items = {item.get_id(): item for item in book.get_items()}

    # Extract chapters from TOC if available
    if hasattr(book, 'toc') and book.toc:
        chapters = _extract_epub_chapters_from_toc(
            book.toc,
            items,
            spine_index_by_id,
            level=1,
        )
    else:
        # Fallback: parse all HTML items as chapters
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                title = item.get_name()
                content = item.get_content().decode('utf-8', errors='ignore')
                # Try to extract title from HTML
                import re
                title_match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE)
                if title_match:
                    title = title_match.group(1).strip()
                elif item.get_name():
                    title = os.path.basename(item.get_name())
                else:
                    title = f"Chapter {len(chapters) + 1}"

                chapters.append({
                    "title": title,
                    "content": content,
                    "level": 1,
                    "start_page": None,
                    "end_page": None,
                    "item_id": item.get_id(),
                    "href": item.get_name(),
                    "spine_index": spine_index_by_id.get(item.get_id(), len(chapters)),
                })

    # If still no chapters, at least include the full content
    if not chapters:
        full_content = ""
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                full_content += item.get_content().decode('utf-8', errors='ignore') + "\n"

        chapters.append({
            "title": "Full Content",
            "content": full_content,
            "level": 1,
            "start_page": None,
            "end_page": None,
        })

    return chapters


def _extract_epub_chapters_from_toc(toc, items, spine_index_by_id, level=1) -> list[Chapter]:
    """Recursively extract chapters from EPUB TOC."""
    chapters = []

    for item in toc:
        child_items = None
        title = None
        href = None

        if isinstance(item, list):
            chapters.extend(_extract_epub_chapters_from_toc(item, items, spine_index_by_id, level=level + 1))
            continue

        # Handle ebooklib Link objects
        if hasattr(item, 'title') and hasattr(item, 'href'):
            title = item.title
            href = item.href
        elif isinstance(item, tuple):
            entry = item[0] if item else None
            if len(item) > 1 and isinstance(item[1], (list, tuple)):
                child_items = item[1]
            if hasattr(entry, 'title') and hasattr(entry, 'href'):
                title = entry.title
                href = entry.href
            elif len(item) >= 2 and isinstance(item[1], str):
                title, href = item[0], item[1]
            elif len(item) >= 2 and hasattr(item[1], 'href'):
                title = item[0]
                href = item[1].href
        else:
            continue

        content = ""
        matched_item = None

        # Find the corresponding item
        for item_id, item_obj in items.items():
            if not isinstance(href, str):
                continue
            target_href = (href or "").split("#", 1)[0]
            if target_href and target_href in (item_obj.get_name() or ""):
                content = item_obj.get_content().decode('utf-8', errors='ignore')
                matched_item = item_obj
                break

        if content.strip():
            chapters.append({
                "title": title,
                "content": content,
                "level": level,
                "start_page": None,
                "end_page": None,
                "item_id": matched_item.get_id() if matched_item else "",
                "href": matched_item.get_name() if matched_item else (href or ""),
                "spine_index": spine_index_by_id.get(
                    matched_item.get_id() if matched_item else "",
                    len(chapters),
                ),
            })

        if child_items:
            chapters.extend(_extract_epub_chapters_from_toc(child_items, items, spine_index_by_id, level=level + 1))

    return chapters


def _parse_pdf(file_path: str) -> list[Chapter]:
    """Parse PDF file and extract chapters from outline/TOC."""
    doc = PdfDocument(file_path)
    chapters = []

    # Try to get outline (TOC)
    outline = doc.outline

    if outline:
        chapters = _extract_pdf_chapters_from_outline(doc, outline, level=1)
    else:
        # Fallback: split by pages (group every ~10 pages as a chapter)
        total_pages = len(doc)
        pages_per_chapter = max(1, total_pages // 10)

        for i in range(0, total_pages, pages_per_chapter):
            end_page = min(i + pages_per_chapter, total_pages)
            content = ""

            for page_num in range(i, end_page):
                page = doc[page_num]
                content += page.get_text() + "\n"

            chapters.append({
                "title": f"Pages {i + 1}-{end_page}",
                "content": content,
                "level": 1,
                "start_page": i + 1,
                "end_page": end_page,
            })

    # If still no chapters, include full content
    if not chapters:
        full_content = "\n".join([page.get_text() for page in doc])
        chapters.append({
            "title": "Full Content",
            "content": full_content,
            "level": 1,
            "start_page": 1,
            "end_page": len(doc),
        })

    return chapters


def _extract_pdf_chapters_from_outline(doc: PdfDocument, outline, level=1) -> list[Chapter]:
    """Recursively extract chapters from PDF outline."""
    chapters = []

    for item in outline:
        if isinstance(item, list):
            # Nested outline
            chapters.extend(_extract_pdf_chapters_from_outline(doc, item, level + 1))
        else:
            # (title, destination)
            title = item.title
            dest = item.dest

            # Get page number from destination
            start_page = None
            end_page = None

            try:
                if dest:
                    if isinstance(dest, str):
                        # Named destination
                        page = doc.load_bookmark(dest)
                    else:
                        page = doc[dest] if dest else None

                    if page:
                        start_page = page.number + 1  # 0-indexed to 1-indexed
                        end_page = start_page
            except Exception:
                pass

            # Extract content for this chapter
            content = ""
            if start_page:
                for page_num in range(start_page - 1, min(start_page, len(doc))):
                    content += doc[page_num].get_text() + "\n"

            chapters.append({
                "title": title,
                "content": content,
                "level": level,
                "start_page": start_page,
                "end_page": end_page,
            })

    return chapters


def _parse_mobi(file_path: str) -> list[Chapter]:
    """Parse MOBI/AZW file and extract chapter structure."""
    if mobi is None:
        raise ValueError("mobi library not available. Install with: pip install mobi")

    # Extract MOBI to a temporary directory
    import tempfile
    import shutil

    with tempfile.TemporaryDirectory() as tmpdir:
        # Extract the MOBI file
        headers = mobi.parse(file_path)

        # Get the full content
        content = ""

        # Try to get the full text
        if hasattr(headers, 'text'):
            content = headers.text
        else:
            # Use mobi to extract content
            name = mobi.extract(file_path, tmpdir)
            if name:
                # Try to read the extracted HTML
                html_file = os.path.join(tmpdir, name, 'mobi7', 'mobi7.html')
                if os.path.exists(html_file):
                    with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                else:
                    # Try other HTML files
                    for root, dirs, files in os.walk(tmpdir):
                        for f in files:
                            if f.endswith('.html'):
                                with open(os.path.join(root, f), 'r', encoding='utf-8', errors='ignore') as fp:
                                    content += fp.read() + "\n"

        # Try to extract chapters from NCX (table of contents)
        chapters = []

        # Get Kindle-specific metadata
        if hasattr(headers, 'ncx'):
            try:
                ncx_data = headers.ncx
                # Parse NCX structure
                import xml.etree.ElementTree as ET
                root = ET.fromstring(ncx_data)
                ns = {'ncx': 'http://www.daisy.org/z3986/2005/ncx/'}

                for nav_point in root.findall('.//ncx:navPoint', ns):
                    nav_label = nav_point.find('ncx:navLabel/ncx:text', ns)
                    if nav_label is not None and nav_label.text:
                        title = nav_label.text.strip()
                        # Get content src
                        content_src = nav_point.find('ncx:content', ns)
                        if content_src is not None:
                            src = content_src.get('src', '')

                        # Try to find matching content
                        chapter_content = _extract_chapter_from_mobi_content(content, src)

                        chapters.append({
                            "title": title,
                            "content": chapter_content,
                            "level": int(nav_point.get('playOrder', '1')[:1]) if nav_point.get('playOrder') else 1,
                            "start_page": None,
                            "end_page": None,
                        })
            except Exception:
                pass

        # Fallback: if no chapters extracted, use the full content
        if not chapters:
            chapters.append({
                "title": "Full Content",
                "content": content,
                "level": 1,
                "start_page": None,
                "end_page": None,
            })

        return chapters


def _extract_chapter_from_mobi_content(full_content: str, src: str) -> str:
    """Extract a specific chapter from MOBI content based on src reference."""
    if not src:
        return full_content

    # Try to find the matching section in content
    # This is a simplified approach - in reality, MOBI content is more complex
    import re

    # Try to match the src to an HTML element ID or name
    src_id = src.split('#')[-1] if '#' in src else os.path.basename(src)

    # Look for the matching element
    pattern = rf'<[^>]*id=["\']?{re.escape(src_id)}["\']?[^>]*>(.*?)</[^>]+>'
    match = re.search(pattern, full_content, re.DOTALL | re.IGNORECASE)

    if match:
        return match.group(1)

    return full_content


def _parse_txt(file_path: str) -> list[Chapter]:
    """Parse plain text file - returns single chapter with full content."""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    return [{
        "title": "Full Content",
        "content": content,
        "level": 1,
        "start_page": None,
        "end_page": None,
    }]

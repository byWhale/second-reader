"""Tests for parse-stage structure generation."""

from __future__ import annotations

import json
import importlib.util
import zipfile
from pathlib import Path

from src.iterator_reader import parse as parse_module
from src.parsers import ebook_parser as ebook_parser_module
from src.iterator_reader.storage import (
    book_manifest_file,
    chapter_result_file,
    cover_asset_file,
    load_structure,
    save_json,
    save_structure,
    structure_file,
)


def test_build_structure_persists_semantic_segments(tmp_path, monkeypatch):
    """build_structure should write structure.json with semantic segments."""
    book_path = tmp_path / "demo.epub"
    book_path.write_text("placeholder", encoding="utf-8")

    monkeypatch.setattr(parse_module, "extract_book_metadata", lambda _: ("Demo Book", "Tester"))
    monkeypatch.setattr(parse_module, "detect_book_language", lambda *_args, **_kwargs: "en")
    monkeypatch.setattr(
        parse_module,
        "parse_ebook",
        lambda _: [
            {
                "title": "Chapter One",
                "content": "<p>Alpha opens the chapter.</p><p>Beta extends the chapter argument.</p>",
                "level": 1,
                "start_page": None,
                "end_page": None,
            }
        ],
    )
    monkeypatch.setattr(
        parse_module,
        "segment_chapter_semantically",
        lambda *args, **kwargs: [
            {
                "id": "1.1",
                "summary": "作者提出第一个判断",
                "tokens": 12,
                "text": kwargs["chapter_text"],
                "paragraph_start": 1,
                "paragraph_end": 1,
                "status": "pending",
            }
        ],
    )
    monkeypatch.setattr(
        parse_module,
        "resolve_output_dir",
        lambda *_args, **_kwargs: tmp_path / "output" / "demo-book",
    )

    structure, output_dir = parse_module.build_structure(book_path, language_mode="auto")

    assert structure["book"] == "Demo Book"
    assert structure["author"] == "Tester"
    assert structure["book_language"] == "en"
    assert structure["output_language"] == "en"
    assert structure["chapters"][0]["segments"][0]["summary"] == "作者提出第一个判断"

    saved = json.loads((output_dir / "public" / "structure.json").read_text(encoding="utf-8"))
    assert saved["chapters"][0]["status"] == "pending"
    assert saved["chapters"][0]["segments"][0]["id"] == "1.1"
    assert saved["chapters"][0]["segments"][0]["segment_ref"] == "Chapter_One.1"
    assert "locator" not in saved["chapters"][0]["segments"][0]
    assert saved["chapters"][0]["segments"][0]["paragraph_locators"][0]["start_cfi"] is None
    assert "Alpha opens the chapter." == saved["chapters"][0]["segments"][0]["paragraph_locators"][0]["text"]
    assert (output_dir / "_assets" / "source.epub").exists()

    structure_md = (output_dir / "public" / "structure.md").read_text(encoding="utf-8")
    assert "# Structure Overview: Demo Book" in structure_md
    assert "## Chapter One" in structure_md
    assert "### Section 1: 作者提出第一个判断" in structure_md


def test_build_structure_infers_human_chapter_number(tmp_path, monkeypatch):
    """Numeric chapter titles should get a human-facing chapter number."""
    book_path = tmp_path / "demo.epub"
    book_path.write_text("placeholder", encoding="utf-8")

    monkeypatch.setattr(parse_module, "extract_book_metadata", lambda _: ("Demo Book", "Tester"))
    monkeypatch.setattr(parse_module, "detect_book_language", lambda *_args, **_kwargs: "en")
    monkeypatch.setattr(
        parse_module,
        "parse_ebook",
        lambda _: [
            {
                "title": "Chapter 10",
                "content": "<p>Alpha opens the chapter.</p><p>Beta extends the chapter argument.</p>",
                "level": 1,
                "start_page": None,
                "end_page": None,
            }
        ],
    )
    monkeypatch.setattr(
        parse_module,
        "segment_chapter_semantically",
        lambda *args, **kwargs: [
            {
                "id": "1.1",
                "summary": "A segment",
                "tokens": 12,
                "text": kwargs["chapter_text"],
                "paragraph_start": 1,
                "paragraph_end": 1,
                "status": "pending",
            }
        ],
    )
    monkeypatch.setattr(
        parse_module,
        "resolve_output_dir",
        lambda *_args, **_kwargs: tmp_path / "output" / "demo-book",
    )

    structure, _output_dir = parse_module.build_structure(book_path, language_mode="auto")

    assert structure["chapters"][0]["chapter_number"] == 10
    assert structure["chapters"][0]["segments"][0]["segment_ref"] == "10.1"


def test_extract_epub_paragraph_records_skips_duplicate_heading_wrappers():
    """Wrapper divs around heading stacks should not become duplicate paragraphs."""
    content = """
<html xmlns="http://www.w3.org/1999/xhtml">
  <body>
    <div>
      <h1>CHAPTER 1</h1>
      <h2>RELATIONSHIPS ARE THE MEDIA IN WHICH VALUE IS TRANSACTED</h2>
    </div>
    <p>People want things from other people.</p>
  </body>
</html>
"""

    records = parse_module._extract_epub_paragraph_records(
        content,
        href="chapter-1.xhtml",
        item_id="chapter-1",
        spine_index=1,
    )

    assert [record["text"] for record in records] == [
        "CHAPTER 1",
        "RELATIONSHIPS ARE THE MEDIA IN WHICH VALUE IS TRANSACTED",
        "People want things from other people.",
    ]
    assert [record["block_tag"] for record in records] == ["h1", "h2", "p"]


def test_extract_epub_chapters_from_toc_handles_nested_children_and_non_string_href():
    """Nested TOC entries with child lists should recurse instead of crashing on list href values."""

    class _Link:
        def __init__(self, title: str, href: str):
            self.title = title
            self.href = href

    class _Item:
        def __init__(self, item_id: str, name: str, content: str):
            self._id = item_id
            self._name = name
            self._content = content

        def get_id(self):
            return self._id

        def get_name(self):
            return self._name

        def get_content(self):
            return self._content.encode("utf-8")

    chapters = ebook_parser_module._extract_epub_chapters_from_toc(
        [
            (
                _Link("Part One", "part.xhtml"),
                [_Link("Chapter 1", "chapter-1.xhtml"), _Link("Chapter 2", "chapter-2.xhtml")],
            )
        ],
        items={
            "part": _Item("part", "part.xhtml", "<p>Part intro</p>"),
            "chapter-1": _Item("chapter-1", "chapter-1.xhtml", "<p>Chapter one</p>"),
            "chapter-2": _Item("chapter-2", "chapter-2.xhtml", "<p>Chapter two</p>"),
        },
        spine_index_by_id={"part": 0, "chapter-1": 1, "chapter-2": 2},
        level=1,
    )

    assert [chapter["title"] for chapter in chapters] == ["Part One", "Chapter 1", "Chapter 2"]
    assert [chapter["level"] for chapter in chapters] == [1, 2, 2]


def test_classify_paragraph_records_detects_heading_roles_generically():
    """Chapter-opening headings and in-body headings should classify separately from body prose."""
    records = [
        {"text": "CHAPTER 1", "block_tag": "h1", "heading_level": 1, "paragraph_index": 1},
        {"text": "The Market for Value", "block_tag": "h2", "heading_level": 2, "paragraph_index": 2},
        {"text": "People want things from other people.", "block_tag": "p", "heading_level": None, "paragraph_index": 3},
        {"text": "The covert calculator", "block_tag": "p", "heading_level": None, "paragraph_index": 4},
        {
            "text": "Valuation often occurs beneath the threshold of awareness.",
            "block_tag": "p",
            "heading_level": None,
            "paragraph_index": 5,
        },
    ]

    classified = parse_module._classify_paragraph_records(records)

    assert [record["text_role"] for record in classified] == [
        "chapter_heading",
        "chapter_heading",
        "body",
        "section_heading",
        "body",
    ]

    chapter_heading = parse_module._chapter_heading_block(classified)
    assert chapter_heading == {
        "label": "CHAPTER 1",
        "title": "The Market for Value",
        "text": "CHAPTER 1\nThe Market for Value",
    }

    body_groups = parse_module._body_record_groups(classified)
    assert len(body_groups) == 2
    assert [record["text"] for record in body_groups[0]["body_records"]] == [
        "People want things from other people."
    ]
    assert [record["text"] for record in body_groups[1]["heading_records"]] == ["The covert calculator"]
    assert [record["text"] for record in body_groups[1]["body_records"]] == [
        "Valuation often occurs beneath the threshold of awareness."
    ]


def test_build_structure_keeps_chapter_heading_outside_first_body_segment(tmp_path, monkeypatch):
    """Chapter heading stacks should be preserved as chapter metadata, not merged into section text."""
    book_path = tmp_path / "demo.epub"
    book_path.write_text("placeholder", encoding="utf-8")

    captured_calls: list[dict[str, object]] = []

    monkeypatch.setattr(parse_module, "extract_book_metadata", lambda _: ("Demo Book", "Tester"))
    monkeypatch.setattr(parse_module, "detect_book_language", lambda *_args, **_kwargs: "en")
    monkeypatch.setattr(
        parse_module,
        "parse_ebook",
        lambda _: [
            {
                "title": "Chapter 1",
                "content": """
<html xmlns="http://www.w3.org/1999/xhtml">
  <body>
    <div>
      <h1>CHAPTER 1</h1>
      <h2>RELATIONSHIPS ARE THE MEDIA IN WHICH VALUE IS TRANSACTED</h2>
    </div>
    <p>People want things from other people.</p>
    <p>This is why other people represent both a solution and a potential problem.</p>
  </body>
</html>
""",
                "level": 1,
                "href": "chapter-1.xhtml",
                "item_id": "chapter-1",
                "spine_index": 1,
                "start_page": None,
                "end_page": None,
            }
        ],
    )

    def _fake_segment(*args, **kwargs):
        captured_calls.append(
            {
                "paragraphs": list(kwargs["paragraphs"]),
                "chapter_heading_text": kwargs["chapter_heading_text"],
                "section_heading_text": kwargs["section_heading_text"],
            }
        )
        return [
            {
                "id": "1.1",
                "summary": "Body thesis only",
                "tokens": 12,
                "text": "\n\n".join(kwargs["paragraphs"]),
                "paragraph_start": 1,
                "paragraph_end": len(kwargs["paragraphs"]),
                "status": "pending",
            }
        ]

    monkeypatch.setattr(parse_module, "segment_chapter_semantically", _fake_segment)
    monkeypatch.setattr(
        parse_module,
        "resolve_output_dir",
        lambda *_args, **_kwargs: tmp_path / "output" / "demo-book",
    )

    structure, _output_dir = parse_module.build_structure(book_path, language_mode="auto")

    assert len(captured_calls) == 1
    assert captured_calls[0]["paragraphs"] == [
        "People want things from other people.",
        "This is why other people represent both a solution and a potential problem.",
    ]
    assert captured_calls[0]["chapter_heading_text"] == (
        "CHAPTER 1\nRELATIONSHIPS ARE THE MEDIA IN WHICH VALUE IS TRANSACTED"
    )
    assert captured_calls[0]["section_heading_text"] == ""

    chapter = structure["chapters"][0]
    assert chapter["chapter_heading"]["label"] == "CHAPTER 1"
    assert chapter["chapter_heading"]["title"] == "RELATIONSHIPS ARE THE MEDIA IN WHICH VALUE IS TRANSACTED"
    assert chapter["chapter_heading"]["text"] == (
        "CHAPTER 1\nRELATIONSHIPS ARE THE MEDIA IN WHICH VALUE IS TRANSACTED"
    )
    assert chapter["chapter_heading"]["locator"]["href"] == "chapter-1.xhtml"
    assert chapter["chapter_heading"]["locator"]["paragraph_start"] == 1
    assert chapter["chapter_heading"]["locator"]["paragraph_end"] == 2
    assert chapter["chapter_heading"]["locator"]["start_cfi"] is not None
    assert chapter["chapter_heading"]["locator"]["end_cfi"] is not None
    assert chapter["segments"][0]["text"] == (
        "People want things from other people.\n\n"
        "This is why other people represent both a solution and a potential problem."
    )
    assert chapter["segments"][0]["summary"] == "Body thesis only"


def test_upgrade_structure_metadata_backfills_segment_ref(tmp_path):
    """Legacy structures without segment_ref should be upgraded in-place."""
    output_dir = tmp_path / "output" / "demo-book"
    output_dir.mkdir(parents=True, exist_ok=True)
    structure = {
        "book": "Demo Book",
        "author": "Tester",
        "book_language": "en",
        "output_language": "en",
        "source_file": "demo.epub",
        "output_dir": str(output_dir),
        "chapters": [
            {
                "id": 6,
                "title": "Prologue",
                "status": "pending",
                "level": 1,
                "segments": [
                    {
                        "id": "6.1",
                        "summary": "A segment",
                        "tokens": 10,
                        "text": "Alpha",
                        "paragraph_start": 1,
                        "paragraph_end": 1,
                        "status": "pending",
                    }
                ],
            }
        ],
    }

    changed = parse_module._upgrade_structure_metadata(structure, output_dir)

    assert changed is True
    assert structure["chapters"][0]["segments"][0]["segment_ref"] == "Prologue.1"
    assert structure["chapters"][0]["segments"][0]["paragraph_locators"] == []


def _write_test_epub(
    path: Path,
    *,
    manifest_items: list[str],
    metadata_block: str = "",
    guide_block: str = "",
    extra_docs: dict[str, str] | None = None,
    image_payloads: dict[str, bytes] | None = None,
) -> None:
    image_payloads = image_payloads or {}
    extra_docs = extra_docs or {}
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip")
        archive.writestr(
            "META-INF/container.xml",
            """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
""",
        )
        archive.writestr(
            "OEBPS/content.opf",
            f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Demo</dc:title>
    <dc:creator>Tester</dc:creator>
    {metadata_block}
  </metadata>
  <manifest>
    {' '.join(manifest_items)}
  </manifest>
  <spine>
    <itemref idref="cover-page"/>
  </spine>
  {guide_block}
</package>
""",
        )
        if "OEBPS/cover.xhtml" not in extra_docs:
            archive.writestr(
                "OEBPS/cover.xhtml",
                """<html xmlns="http://www.w3.org/1999/xhtml"><body><p>fallback</p></body></html>""",
            )
        for doc_path, content in extra_docs.items():
            archive.writestr(doc_path, content)
        for image_path, payload in image_payloads.items():
            archive.writestr(image_path, payload)


def test_extract_epub_cover_supports_epub3_meta_cover_reference(tmp_path):
    """EPUB 3 meta name=cover should resolve even when filenames omit 'cover'."""
    epub_path = tmp_path / "meta-cover.epub"
    output_dir = tmp_path / "output"
    _write_test_epub(
        epub_path,
        metadata_block='<meta name="cover" content="image_rsrc1NC.jpg"/>',
        manifest_items=[
            '<item id="image_rsrc1NC.jpg" href="image_rsrc1NC.jpg" media-type="image/jpeg"/>',
            '<item id="cover-page" href="cover.xhtml" media-type="application/xhtml+xml"/>',
        ],
        image_payloads={"OEBPS/image_rsrc1NC.jpg": b"meta-cover"},
    )

    cover_path = parse_module._extract_epub_cover(epub_path, output_dir)

    assert cover_path == output_dir / "_assets" / "cover.jpg"
    assert cover_path is not None
    assert cover_path.read_bytes() == b"meta-cover"


def test_extract_epub_cover_supports_manifest_cover_image_property(tmp_path):
    """Manifest items flagged as cover-image should be selected."""
    epub_path = tmp_path / "cover-property.epub"
    output_dir = tmp_path / "output"
    _write_test_epub(
        epub_path,
        manifest_items=[
            '<item id="img-1" href="images/front.png" media-type="image/png" properties="cover-image"/>',
            '<item id="cover-page" href="cover.xhtml" media-type="application/xhtml+xml"/>',
        ],
        image_payloads={"OEBPS/images/front.png": b"cover-property"},
    )

    cover_path = parse_module._extract_epub_cover(epub_path, output_dir)

    assert cover_path == output_dir / "_assets" / "cover.png"
    assert cover_path is not None
    assert cover_path.read_bytes() == b"cover-property"


def test_extract_epub_cover_supports_guide_page_svg_image(tmp_path):
    """Guide cover pages with svg:image href should resolve to the underlying asset."""
    epub_path = tmp_path / "guide-cover.epub"
    output_dir = tmp_path / "output"
    _write_test_epub(
        epub_path,
        manifest_items=[
            '<item id="image-1" href="images/front.jpg" media-type="image/jpeg"/>',
            '<item id="cover-page" href="pages/cover.xhtml" media-type="application/xhtml+xml"/>',
        ],
        guide_block='<guide><reference type="cover" title="Cover" href="pages/cover.xhtml"/></guide>',
        extra_docs={
            "OEBPS/pages/cover.xhtml": """
<html xmlns="http://www.w3.org/1999/xhtml">
  <body>
    <svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
      <image xlink:href="../images/front.jpg" />
    </svg>
  </body>
</html>
"""
        },
        image_payloads={"OEBPS/images/front.jpg": b"guide-cover"},
    )

    cover_path = parse_module._extract_epub_cover(epub_path, output_dir)

    assert cover_path == output_dir / "_assets" / "cover.jpg"
    assert cover_path is not None
    assert cover_path.read_bytes() == b"guide-cover"


def test_extract_epub_cover_returns_none_when_no_cover_is_declared(tmp_path):
    """Undeclared non-cover images should not be guessed as the cover."""
    epub_path = tmp_path / "no-cover.epub"
    output_dir = tmp_path / "output"
    _write_test_epub(
        epub_path,
        manifest_items=[
            '<item id="img-1" href="images/photo.jpg" media-type="image/jpeg"/>',
            '<item id="cover-page" href="cover.xhtml" media-type="application/xhtml+xml"/>',
        ],
        image_payloads={"OEBPS/images/photo.jpg": b"not-cover"},
    )

    cover_path = parse_module._extract_epub_cover(epub_path, output_dir)

    assert cover_path is None
    assert not (output_dir / "_assets").exists()


def test_backfill_missing_epub_covers_updates_manifest_and_is_idempotent(tmp_path):
    """Backfill should extract one missing cover and keep the result stable across reruns."""
    runtime_root = tmp_path
    output_dir = runtime_root / "output" / "demo-book"
    output_dir.mkdir(parents=True, exist_ok=True)
    source_epub = output_dir / "_assets" / "source.epub"
    source_epub.parent.mkdir(parents=True, exist_ok=True)

    _write_test_epub(
        source_epub,
        metadata_block='<meta name="cover" content="image_rsrc1NC.jpg"/>',
        manifest_items=[
            '<item id="image_rsrc1NC.jpg" href="image_rsrc1NC.jpg" media-type="image/jpeg"/>',
            '<item id="cover-page" href="cover.xhtml" media-type="application/xhtml+xml"/>',
        ],
        image_payloads={"OEBPS/image_rsrc1NC.jpg": b"backfill-cover"},
    )

    save_json(
        book_manifest_file(output_dir),
        {
            "book_id": "demo-book",
            "book": "Demo",
            "author": "Tester",
            "cover_image_url": None,
            "book_language": "en",
            "output_language": "en",
            "source_file": "",
            "source_asset": {"format": "epub", "file": "_assets/source.epub"},
            "updated_at": "2026-03-11T00:00:00Z",
            "chapters": [],
        },
    )

    first = parse_module.backfill_missing_epub_covers(runtime_root)
    second = parse_module.backfill_missing_epub_covers(runtime_root)
    manifest = json.loads(book_manifest_file(output_dir).read_text(encoding="utf-8"))

    assert first == [{"book_id": "demo-book", "status": "updated", "cover_image_url": "_assets/cover.jpg"}]
    assert second == [{"book_id": "demo-book", "status": "already_present", "cover_image_url": "_assets/cover.jpg"}]
    assert manifest["cover_image_url"] == "_assets/cover.jpg"
    assert cover_asset_file(output_dir).read_bytes() == b"backfill-cover"


def test_hydrate_legacy_epub_locators_backfills_structure_and_result(tmp_path):
    """Legacy EPUB outputs should gain chapter, segment, and reaction locators without regenerating AI content."""
    output_dir = tmp_path / "output" / "demo-book"
    output_dir.mkdir(parents=True, exist_ok=True)
    source_epub = output_dir / "_assets" / "source.epub"
    source_epub.parent.mkdir(parents=True, exist_ok=True)

    _write_test_epub(
        source_epub,
        manifest_items=[
            '<item id="cover-page" href="cover.xhtml" media-type="application/xhtml+xml"/>',
            '<item id="chapter-1" href="chapter-1.xhtml" media-type="application/xhtml+xml"/>',
        ],
        extra_docs={
            "OEBPS/cover.xhtml": """
<html xmlns="http://www.w3.org/1999/xhtml">
  <head><title>Title Page</title></head>
  <body><p>Title page</p></body>
</html>
""",
            "OEBPS/chapter-1.xhtml": """
<html xmlns="http://www.w3.org/1999/xhtml">
  <head><title>Chapter 1</title></head>
  <body>
    <p>Alpha paragraph.</p>
    <p>Beta anchor quote text.</p>
  </body>
</html>
""",
        },
    )

    structure = {
        "book": "Demo",
        "author": "Tester",
        "book_language": "en",
        "output_language": "en",
        "source_file": str(source_epub),
        "output_dir": str(output_dir),
        "chapters": [
            {
                "id": 2,
                "title": "Chapter 1",
                "chapter_number": 1,
                "status": "done",
                "level": 1,
                "segments": [
                    {
                        "id": "2.1",
                        "segment_ref": "1.1",
                        "summary": "Alpha / Beta",
                        "tokens": 12,
                        "text": "Alpha paragraph.\n\nBeta anchor quote text.",
                        "paragraph_start": 1,
                        "paragraph_end": 2,
                        "status": "done",
                        "paragraph_locators": [],
                    }
                ],
            }
        ],
    }
    save_structure(structure_file(output_dir), structure)
    save_json(
        chapter_result_file(output_dir, structure["chapters"][0]),
        {
            "chapter": {
                "id": 2,
                "title": "Chapter 1",
                "chapter_number": 1,
                "reference": "Chapter 1",
                "status": "done",
            },
            "output_language": "en",
            "generated_at": "2026-03-11T00:00:00Z",
            "sections": [
                {
                    "segment_id": "2.1",
                    "segment_ref": "1.1",
                    "summary": "Alpha / Beta",
                    "original_text": "",
                    "verdict": "pass",
                    "quality_status": "strong",
                    "reflection_summary": "",
                    "reflection_reason_codes": [],
                    "reactions": [
                        {
                            "reaction_id": "legacy-r1",
                            "type": "highlight",
                            "anchor_quote": "Beta anchor quote text.",
                            "content": "Anchor this quote.",
                            "search_query": "",
                            "search_results": [],
                            "target_locator": {},
                        }
                    ],
                }
            ],
            "chapter_reflection": {},
            "featured_reactions": [
                {
                    "reaction_id": "legacy-r1",
                    "type": "highlight",
                    "segment_ref": "1.1",
                    "anchor_quote": "Beta anchor quote text.",
                    "content": "Anchor this quote.",
                    "target_locator": {},
                }
            ],
            "visible_reaction_count": 1,
            "reaction_type_diversity": 1,
            "high_signal_reaction_count": 1,
            "ui_summary": {
                "kept_section_count": 1,
                "skipped_section_count": 0,
                "reaction_counts": {"highlight": 1},
            },
        },
    )

    changes = parse_module.hydrate_legacy_epub_locators(output_dir, structure, source_epub)
    hydrated_structure = load_structure(structure_file(output_dir))
    hydrated_result = json.loads(chapter_result_file(output_dir, structure["chapters"][0]).read_text(encoding="utf-8"))
    segment = hydrated_structure["chapters"][0]["segments"][0]
    reaction = hydrated_result["sections"][0]["reactions"][0]

    assert changes == ["structure_locators", "result_locators"]
    assert hydrated_structure["chapters"][0]["item_id"] == "chapter-1"
    assert hydrated_structure["chapters"][0]["href"] == "chapter-1.xhtml"
    assert hydrated_structure["chapters"][0]["spine_index"] == 1
    assert segment["locator"]["href"] == "chapter-1.xhtml"
    assert len(segment["paragraph_locators"]) == 2
    assert segment["paragraph_locators"][1]["start_cfi"] is not None
    assert hydrated_result["sections"][0]["original_text"] == "Alpha paragraph.\n\nBeta anchor quote text."
    assert reaction["target_locator"]["href"] == "chapter-1.xhtml"
    assert reaction["target_locator"]["match_mode"] == "exact"
    assert hydrated_result["featured_reactions"][0]["target_locator"]["match_mode"] == "exact"


def test_hydrate_legacy_epub_locators_rematches_drifted_segment_ranges(tmp_path):
    """Legacy segments with stale paragraph indices should be rematched by text."""
    output_dir = tmp_path / "output" / "demo-book"
    output_dir.mkdir(parents=True, exist_ok=True)
    source_epub = output_dir / "_assets" / "source.epub"
    source_epub.parent.mkdir(parents=True, exist_ok=True)

    _write_test_epub(
        source_epub,
        manifest_items=[
            '<item id="cover-page" href="cover.xhtml" media-type="application/xhtml+xml"/>',
            '<item id="chapter-1" href="chapter-1.xhtml" media-type="application/xhtml+xml"/>',
        ],
        extra_docs={
            "OEBPS/cover.xhtml": """
<html xmlns="http://www.w3.org/1999/xhtml">
  <head><title>Title Page</title></head>
  <body><p>Title page</p></body>
</html>
""",
            "OEBPS/chapter-1.xhtml": """
<html xmlns="http://www.w3.org/1999/xhtml">
  <head><title>Chapter 1</title></head>
  <body>
    <p>Opening thought.</p>
    <p>Bridge paragraph.</p>
    <p>In the context of sexual relationships, this emotion is desire.</p>
    <p>Closing synthesis for the segment.</p>
  </body>
</html>
""",
        },
    )

    structure = {
        "book": "Demo",
        "author": "Tester",
        "book_language": "en",
        "output_language": "en",
        "source_file": str(source_epub),
        "output_dir": str(output_dir),
        "chapters": [
            {
                "id": 2,
                "title": "Chapter 1",
                "chapter_number": 1,
                "status": "done",
                "level": 1,
                "segments": [
                    {
                        "id": "2.1",
                        "segment_ref": "1.1",
                        "summary": "Desire landing",
                        "tokens": 20,
                        "text": (
                            "In the context of sexual relationships, this emotion is desire.\n\n"
                            "Closing synthesis for the segment."
                        ),
                        "paragraph_start": 10,
                        "paragraph_end": 11,
                        "status": "done",
                        "paragraph_locators": [],
                    }
                ],
            }
        ],
    }
    save_structure(structure_file(output_dir), structure)
    save_json(
        chapter_result_file(output_dir, structure["chapters"][0]),
        {
            "chapter": {
                "id": 2,
                "title": "Chapter 1",
                "chapter_number": 1,
                "reference": "Chapter 1",
                "status": "done",
            },
            "output_language": "en",
            "generated_at": "2026-03-11T00:00:00Z",
            "sections": [
                {
                    "segment_id": "2.1",
                    "segment_ref": "1.1",
                    "summary": "Desire landing",
                    "original_text": "",
                    "verdict": "pass",
                    "quality_status": "strong",
                    "reflection_summary": "",
                    "reflection_reason_codes": [],
                    "reactions": [
                        {
                            "reaction_id": "legacy-r1",
                            "type": "highlight",
                            "anchor_quote": "In the context of sexual relationships, this emotion is desire.",
                            "content": "Anchor this quote.",
                            "search_query": "",
                            "search_results": [],
                            "target_locator": {},
                        }
                    ],
                }
            ],
            "chapter_reflection": {},
            "featured_reactions": [
                {
                    "reaction_id": "legacy-r1",
                    "type": "highlight",
                    "segment_ref": "1.1",
                    "anchor_quote": "In the context of sexual relationships, this emotion is desire.",
                    "content": "Anchor this quote.",
                    "target_locator": {},
                }
            ],
            "visible_reaction_count": 1,
            "reaction_type_diversity": 1,
            "high_signal_reaction_count": 1,
            "ui_summary": {
                "kept_section_count": 1,
                "skipped_section_count": 0,
                "reaction_counts": {"highlight": 1},
            },
        },
    )

    changes = parse_module.hydrate_legacy_epub_locators(output_dir, structure, source_epub)
    hydrated_structure = load_structure(structure_file(output_dir))
    hydrated_result = json.loads(chapter_result_file(output_dir, structure["chapters"][0]).read_text(encoding="utf-8"))
    segment = hydrated_structure["chapters"][0]["segments"][0]
    reaction = hydrated_result["sections"][0]["reactions"][0]

    assert changes == ["structure_locators", "result_locators"]
    assert segment["paragraph_start"] == 3
    assert segment["paragraph_end"] == 4
    assert segment["locator"]["href"] == "chapter-1.xhtml"
    assert len(segment["paragraph_locators"]) == 2
    assert hydrated_result["sections"][0]["locator"]["paragraph_start"] == 3
    assert reaction["target_locator"]["href"] == "chapter-1.xhtml"
    assert reaction["target_locator"]["start_cfi"] == segment["paragraph_locators"][0]["start_cfi"]
    assert reaction["target_locator"]["match_mode"] == "exact"
    assert hydrated_result["featured_reactions"][0]["target_locator"]["match_mode"] == "exact"


def test_hydrate_legacy_epub_locators_detaches_chapter_heading_from_body_text(tmp_path):
    """Legacy segments polluted by chapter headings should be cleaned and re-scoped to body prose."""
    output_dir = tmp_path / "output" / "demo-book"
    output_dir.mkdir(parents=True, exist_ok=True)
    source_epub = output_dir / "_assets" / "source.epub"
    source_epub.parent.mkdir(parents=True, exist_ok=True)

    _write_test_epub(
        source_epub,
        manifest_items=[
            '<item id="cover-page" href="cover.xhtml" media-type="application/xhtml+xml"/>',
            '<item id="chapter-1" href="chapter-1.xhtml" media-type="application/xhtml+xml"/>',
        ],
        extra_docs={
            "OEBPS/cover.xhtml": """
<html xmlns="http://www.w3.org/1999/xhtml">
  <head><title>Title Page</title></head>
  <body><p>Title page</p></body>
</html>
""",
            "OEBPS/chapter-1.xhtml": """
<html xmlns="http://www.w3.org/1999/xhtml">
  <head><title>Chapter 1</title></head>
  <body>
    <div>
      <h1>CHAPTER 1</h1>
      <h2>RELATIONSHIPS ARE THE MEDIA IN WHICH VALUE IS TRANSACTED</h2>
    </div>
    <p>People want things from other people.</p>
    <p>This is why other people represent both a solution and a potential problem.</p>
  </body>
</html>
""",
        },
    )

    structure = {
        "book": "Demo",
        "author": "Tester",
        "book_language": "en",
        "output_language": "en",
        "source_file": str(source_epub),
        "output_dir": str(output_dir),
        "chapters": [
            {
                "id": 2,
                "title": "Chapter 1",
                "chapter_number": 1,
                "status": "done",
                "level": 1,
                "segments": [
                    {
                        "id": "2.1",
                        "segment_ref": "1.1",
                        "summary": "Chapter title and thesis introduction",
                        "tokens": 20,
                        "text": (
                            "CHAPTER 1\n\n"
                            "RELATIONSHIPS ARE THE MEDIA IN WHICH VALUE IS TRANSACTED\n\n"
                            "People want things from other people.\n\n"
                            "This is why other people represent both a solution and a potential problem."
                        ),
                        "paragraph_start": 1,
                        "paragraph_end": 4,
                        "status": "done",
                        "paragraph_locators": [],
                    }
                ],
            }
        ],
    }
    save_structure(structure_file(output_dir), structure)
    save_json(
        chapter_result_file(output_dir, structure["chapters"][0]),
        {
            "chapter": {
                "id": 2,
                "title": "Chapter 1",
                "chapter_number": 1,
                "reference": "Chapter 1",
                "status": "done",
            },
            "output_language": "en",
            "generated_at": "2026-03-11T00:00:00Z",
            "sections": [
                {
                    "segment_id": "2.1",
                    "segment_ref": "1.1",
                    "summary": "Chapter title and thesis introduction",
                    "original_text": "",
                    "verdict": "pass",
                    "quality_status": "strong",
                    "reflection_summary": "",
                    "reflection_reason_codes": [],
                    "reactions": [
                        {
                            "reaction_id": "legacy-r1",
                            "type": "highlight",
                            "anchor_quote": "People want things from other people.",
                            "content": "Anchor the first body paragraph.",
                            "search_query": "",
                            "search_results": [],
                            "target_locator": {},
                        }
                    ],
                }
            ],
            "chapter_reflection": {},
            "featured_reactions": [
                {
                    "reaction_id": "legacy-r1",
                    "type": "highlight",
                    "segment_ref": "1.1",
                    "anchor_quote": "People want things from other people.",
                    "content": "Anchor the first body paragraph.",
                    "target_locator": {},
                }
            ],
            "visible_reaction_count": 1,
            "reaction_type_diversity": 1,
            "high_signal_reaction_count": 1,
            "ui_summary": {
                "kept_section_count": 1,
                "skipped_section_count": 0,
                "reaction_counts": {"highlight": 1},
            },
        },
    )

    changes = parse_module.hydrate_legacy_epub_locators(output_dir, structure, source_epub)
    hydrated_structure = load_structure(structure_file(output_dir))
    hydrated_result = json.loads(chapter_result_file(output_dir, structure["chapters"][0]).read_text(encoding="utf-8"))
    segment = hydrated_structure["chapters"][0]["segments"][0]

    assert changes == ["structure_locators", "result_locators"]
    assert hydrated_structure["chapters"][0]["chapter_heading"]["label"] == "CHAPTER 1"
    assert hydrated_structure["chapters"][0]["chapter_heading"]["title"] == (
        "RELATIONSHIPS ARE THE MEDIA IN WHICH VALUE IS TRANSACTED"
    )
    assert segment["text"] == (
        "People want things from other people.\n\n"
        "This is why other people represent both a solution and a potential problem."
    )
    assert segment["paragraph_start"] == 3
    assert segment["paragraph_end"] == 4
    assert hydrated_result["chapter_heading"]["title"] == "RELATIONSHIPS ARE THE MEDIA IN WHICH VALUE IS TRANSACTED"
    assert hydrated_result["sections"][0]["summary"] == "People want things from other people."
    assert hydrated_result["sections"][0]["original_text"] == segment["text"]
    assert hydrated_result["sections"][0]["locator"]["paragraph_start"] == 3


def test_backfill_output_dir_reports_locator_changes(tmp_path):
    """The default legacy backfill script should include EPUB locator hydration."""
    output_dir = tmp_path / "output" / "demo-book"
    output_dir.mkdir(parents=True, exist_ok=True)
    source_epub = tmp_path / "demo.epub"

    _write_test_epub(
        source_epub,
        manifest_items=[
            '<item id="cover-page" href="cover.xhtml" media-type="application/xhtml+xml"/>',
            '<item id="chapter-1" href="chapter-1.xhtml" media-type="application/xhtml+xml"/>',
        ],
        extra_docs={
            "OEBPS/cover.xhtml": """
<html xmlns="http://www.w3.org/1999/xhtml">
  <head><title>Title Page</title></head>
  <body><p>Title page</p></body>
</html>
""",
            "OEBPS/chapter-1.xhtml": """
<html xmlns="http://www.w3.org/1999/xhtml">
  <head><title>Chapter 1</title></head>
  <body><p>Legacy paragraph.</p></body>
</html>
""",
        },
    )

    structure = {
        "book": "Demo",
        "author": "Tester",
        "book_language": "en",
        "output_language": "en",
        "source_file": str(source_epub),
        "output_dir": str(output_dir),
        "chapters": [
            {
                "id": 2,
                "title": "Chapter 1",
                "chapter_number": 1,
                "status": "done",
                "level": 1,
                "segments": [
                    {
                        "id": "2.1",
                        "segment_ref": "1.1",
                        "summary": "Legacy paragraph",
                        "tokens": 8,
                        "text": "Legacy paragraph.",
                        "paragraph_start": 1,
                        "paragraph_end": 1,
                        "status": "done",
                        "paragraph_locators": [],
                    }
                ],
            }
        ],
    }
    save_structure(structure_file(output_dir), structure)
    save_json(
        chapter_result_file(output_dir, structure["chapters"][0]),
        {
            "chapter": {
                "id": 2,
                "title": "Chapter 1",
                "chapter_number": 1,
                "reference": "Chapter 1",
                "status": "done",
            },
            "output_language": "en",
            "generated_at": "2026-03-11T00:00:00Z",
            "sections": [
                {
                    "segment_id": "2.1",
                    "segment_ref": "1.1",
                    "summary": "Legacy paragraph",
                    "original_text": "",
                    "verdict": "pass",
                    "quality_status": "strong",
                    "reflection_summary": "",
                    "reflection_reason_codes": [],
                    "reactions": [
                        {
                            "reaction_id": "legacy-r1",
                            "type": "highlight",
                            "anchor_quote": "Legacy paragraph.",
                            "content": "Anchor it.",
                            "search_query": "",
                            "search_results": [],
                            "target_locator": {},
                        }
                    ],
                }
            ],
            "chapter_reflection": {},
            "featured_reactions": [],
            "visible_reaction_count": 1,
            "reaction_type_diversity": 1,
            "high_signal_reaction_count": 1,
            "ui_summary": {
                "kept_section_count": 1,
                "skipped_section_count": 0,
                "reaction_counts": {"highlight": 1},
            },
        },
    )

    script_path = Path(__file__).resolve().parents[1] / "scripts" / "backfill_legacy_outputs.py"
    spec = importlib.util.spec_from_file_location("backfill_legacy_outputs", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    changes = module.backfill_output_dir(output_dir)

    assert "source_asset" in changes
    assert "structure_locators" in changes
    assert "result_locators" in changes

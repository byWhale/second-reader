"""Manifest-driven helpers for attentional_v2 benchmark corpus building."""

from __future__ import annotations

from dataclasses import dataclass
import html
import hashlib
import json
import math
import re
import shutil
import subprocess
import statistics
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote_plus

from ebooklib import ITEM_DOCUMENT, epub
from src.reading_runtime.provisioning import ensure_canonical_parse


ROOT = Path(__file__).resolve().parents[2]
STATE_ROOT = ROOT / "state"
STATE_LIBRARY_ROOT = STATE_ROOT / "library_sources"
STATE_LOCAL_DATASET_ROOT = STATE_ROOT / "eval_local_datasets"
ACQUISITION_ROOT = STATE_ROOT / "_acquisition" / "public_first_large_v2"
DATASET_ROOT = ROOT / "eval" / "datasets"
MANIFEST_ROOT = ROOT / "eval" / "manifests"

QUESTION_IDS_BY_FAMILY = {
    "excerpt_cases": [
        "EQ-CM-002",
        "EQ-AV2-001",
        "EQ-AV2-002",
        "EQ-AV2-003",
        "EQ-AV2-004",
        "EQ-AV2-005",
        "EQ-AV2-006",
    ],
    "chapter_corpora": [
        "EQ-CM-001",
        "EQ-CM-003",
        "EQ-CM-004",
        "EQ-GATE-003",
    ],
    "runtime_fixtures": [
        "EQ-CM-005",
        "EQ-AV2-007",
        "EQ-GATE-001",
        "EQ-GATE-003",
    ],
    "compatibility_fixtures": [
        "EQ-AV2-008",
        "EQ-GATE-002",
    ],
}

PROMOTION_ROLE_QUOTAS = {
    "expository": 2,
    "argumentative": 2,
    "narrative_reflective": 1,
    "reference_heavy": 1,
}

CHAPTER_ROLE_QUOTAS = {
    "expository": 4,
    "argumentative": 4,
    "narrative_reflective": 4,
    "reference_heavy": 4,
}

CURATED_BUCKET_QUOTAS = {
    "distinction_definition": 3,
    "tension_reversal": 3,
    "callback_bridge": 3,
    "anchored_reaction_selectivity": 3,
    "reconsolidation_later_reinterpretation": 3,
}

RESERVE_CHAPTER_COUNT = 2
RUNTIME_CHAPTERS_PER_ROLE = 3
RUNTIME_RESUME_KINDS = ("warm", "cold", "reconstitution")
MAX_CHAPTERS_PER_SOURCE_DEFAULT = 2
MAX_CHAPTERS_PER_SOURCE_FALLBACK = 4
MAX_RUNTIME_CHAPTERS_PER_SOURCE = 3

FRONT_MATTER_PATTERNS = {
    "en": [
        re.compile(pattern, re.IGNORECASE)
        for pattern in [
            r"project gutenberg",
            r"license",
            r"table of contents",
            r"contents",
            r"preface",
            r"foreword",
            r"introduction",
            r"dedication",
            r"copyright",
            r"chapter summaries and map",
            r"appendix",
            r"index",
        ]
    ],
    "zh": [
        re.compile(pattern)
        for pattern in [
            r"版權",
            r"目錄",
            r"總目",
            r"小引",
            r"序",
            r"前言",
            r"自序",
            r"凡例",
            r"後記",
            r"附錄",
            r"許可證",
            r"古騰堡",
        ]
    ],
}

CHINESE_SERIAL_HEADING_RE = re.compile(r"^第[〇零一二三四五六七八九十百千兩两○0-9]+[回章节節篇部卷][^\n]{0,60}$")
CHINESE_YEAR_HEADING_RE = re.compile(r"^一九[〇零一二三四五六七八九十]{2}年$")
CHINESE_METADATA_PATTERNS = [
    re.compile(pattern)
    for pattern in [
        r"^作者[:：]?$",
        r"^姊妹计划$",
        r"^维基百科$",
        r"^條目[:：]?$",
        r"^百科$",
        r"^图册分类$",
        r"^數據項$",
        r"^数据项$",
        r"^\[?编辑\]?$",
        r"^←$",
        r"^→$",
        r"^[·:：]+$",
        r"^附錄[:：]?$",
    ]
]


@dataclass(frozen=True)
class CandidateSpec:
    """One manifest-driven candidate source-book spec."""

    source_id: str
    title: str
    author: str
    language: str
    origin: str
    storage_mode: str
    promoted_local_path: str
    acquisition: dict[str, Any]
    type_tags: list[str]
    role_tags: list[str]
    selection_priority: int
    notes: list[str]


def canonicalize_role_tags(role_tags: Iterable[str], type_tags: Iterable[str] | None = None) -> list[str]:
    """Normalize role tags into the stable corpus-selection vocabulary."""

    normalized: set[str] = set()
    for tag in list(role_tags) + list(type_tags or []):
        cleaned = str(tag or "").strip()
        if not cleaned:
            continue
        normalized.add(cleaned)
        if cleaned in {"philosophical", "conceptual_nonfiction", "educational_thought"}:
            normalized.add("expository")
        if cleaned in {"essayistic", "social_thought", "gender_thought", "economic_thought", "modern_political_classic"}:
            normalized.add("argumentative")
        if cleaned in {"novel", "memoir", "travel", "historical_reflection", "short_story", "social_detail"}:
            normalized.add("narrative_reflective")
        if cleaned in {"allusion_dense", "reference_dense"}:
            normalized.add("reference_heavy")
    ordered = [role for role in ("expository", "argumentative", "narrative_reflective", "reference_heavy") if role in normalized]
    for tag in sorted(normalized):
        if tag not in ordered:
            ordered.append(tag)
    return ordered


def load_json(path: Path) -> Any:
    """Load one JSON payload from disk."""

    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    """Persist one JSON payload with stable formatting."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    """Persist one JSONL payload."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def sha256_file(path: Path) -> str:
    """Return the SHA-256 fingerprint for one file."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fetch_bytes(url: str, *, accept: str | None = None) -> bytes:
    """Fetch one remote resource with a stable user-agent."""

    headers = {"User-Agent": "ReadingCompanion/1.0 (+https://github.com/openai/codex)"}
    if accept:
        headers["Accept"] = accept
    command = ["curl", "-L", "--retry", "2", "--retry-delay", "1", "--max-time", "240", "-sS"]
    for key, value in headers.items():
        command.extend(["-H", f"{key}: {value}"])
    command.append(url)
    result = subprocess.run(command, check=True, capture_output=True)
    return result.stdout


def _fetch_text(url: str, *, accept: str | None = None) -> str:
    """Fetch one remote text payload as UTF-8."""

    return _fetch_bytes(url, accept=accept).decode("utf-8", errors="replace")


def _fetch_json(url: str) -> dict[str, Any]:
    """Fetch one remote JSON payload."""

    return json.loads(_fetch_text(url, accept="application/json"))


def _normalize_title(value: str) -> str:
    """Normalize a title or author for looser remote matching."""

    lowered = value.lower()
    lowered = re.sub(r"[\W_]+", "", lowered, flags=re.UNICODE)
    return lowered


def _resolve_standard_ebooks_download(page_url: str) -> str:
    """Resolve the plain EPUB download link from one Standard Ebooks page."""

    html = _fetch_text(page_url)
    matches = re.findall(r'href="(?P<path>/ebooks/[^"]+/downloads/[^"]+\.epub)"', html)
    for path in matches:
        if "kepub" in path or "advanced" in path:
            continue
        return f"https://standardebooks.org{path}?source=download"
    if matches:
        return f"https://standardebooks.org{matches[0]}?source=download"
    raise ValueError(f"Could not resolve a Standard Ebooks EPUB download from {page_url}")


def _resolve_gutendex_download(search_title: str, author_match: str, language: str) -> tuple[str, dict[str, Any]]:
    """Resolve the best Gutendex result and return its download URL."""

    payload = _fetch_json(f"https://gutendex.com/books/?search={quote_plus(search_title)}")
    wanted_title = _normalize_title(search_title)
    wanted_author = _normalize_title(author_match)
    best_result: dict[str, Any] | None = None
    best_score = -math.inf
    for result in payload.get("results", []):
        languages = [str(item) for item in result.get("languages", [])]
        if language not in languages:
            continue
        title = str(result.get("title", ""))
        authors = [str(author.get("name", "")) for author in result.get("authors", [])]
        normalized_title = _normalize_title(title)
        normalized_authors = [_normalize_title(author) for author in authors]
        score = 0
        if normalized_title == wanted_title:
            score += 5
        elif wanted_title in normalized_title or normalized_title in wanted_title:
            score += 3
        if any(wanted_author in author or author in wanted_author for author in normalized_authors):
            score += 4
        if bool(result.get("copyright")) is False:
            score += 1
        if "application/epub+zip" in result.get("formats", {}):
            score += 2
        if score > best_score:
            best_score = score
            best_result = result
    if best_result is None:
        raise ValueError(f"Could not resolve a Gutendex source for {search_title} by {author_match}")
    formats = dict(best_result.get("formats", {}))
    download_url = str(
        formats.get("application/epub+zip")
        or formats.get("text/plain; charset=utf-8")
        or formats.get("text/plain; charset=us-ascii")
        or ""
    )
    if not download_url:
        raise ValueError(f"Gutendex result for {search_title} by {author_match} has no EPUB/TXT download.")
    return download_url, best_result


def _resolve_wikisource_download(page_title: str, language: str) -> str:
    """Resolve one Wikisource export URL."""

    return f"https://ws-export.wmcloud.org/?format=epub&lang={language}&page={quote_plus(page_title)}"


def _fetch_wikisource_plain_text(page_title: str, language: str) -> str:
    """Fallback to rendered plain text for Wikisource pages whose EPUB export is unavailable."""

    api_url = (
        f"https://{language}.wikisource.org/w/api.php?action=parse&format=json&prop=text&page={quote_plus(page_title)}"
    )
    payload = _fetch_json(api_url)
    html_text = str(payload.get("parse", {}).get("text", {}).get("*", "") or "")
    if not html_text:
        raise ValueError(f"Could not fetch rendered text for Wikisource page {page_title}")
    html_text = re.sub(r"<(script|style)[^>]*>.*?</\\1>", "", html_text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", "\n", html_text)
    text = html.unescape(text)
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip() + "\n"


def resolve_candidate_download(spec: CandidateSpec) -> tuple[str, dict[str, Any]]:
    """Resolve the remote download URL and any acquisition metadata for one candidate."""

    acquisition_kind = str(spec.acquisition.get("kind", "") or "")
    if acquisition_kind == "standard_ebooks_page":
        page_url = str(spec.acquisition["page_url"])
        return _resolve_standard_ebooks_download(page_url), {"page_url": page_url}
    if acquisition_kind == "gutendex_search":
        download_url, result = _resolve_gutendex_download(
            search_title=str(spec.acquisition["search_title"]),
            author_match=str(spec.acquisition["author_match"]),
            language=spec.language,
        )
        return download_url, {"gutendex_result": result}
    if acquisition_kind == "wikisource_export":
        page_title = str(spec.acquisition["page_title"])
        return _resolve_wikisource_download(page_title, str(spec.acquisition.get("lang", spec.language))), {
            "page_title": page_title
        }
    raise ValueError(f"Unsupported acquisition kind: {acquisition_kind}")


def _download_extension(download_url: str) -> str:
    """Infer a file extension for one remote source."""

    lowered = download_url.lower()
    if ".txt" in lowered:
        return ".txt"
    return ".epub"


def _epub_bytes_look_valid(data: bytes) -> bool:
    """Return whether one byte payload appears to be a real EPUB zip."""

    return data.startswith(b"PK\x03\x04")


def download_candidate(spec: CandidateSpec) -> tuple[Path, dict[str, Any]]:
    """Download one candidate into the temporary acquisition root."""

    download_url, metadata = resolve_candidate_download(spec)
    extension = _download_extension(download_url)
    local_path = ACQUISITION_ROOT / spec.language / f"{spec.source_id}{extension}"
    txt_fallback_path = local_path.with_suffix(".txt")
    local_path.parent.mkdir(parents=True, exist_ok=True)
    if spec.acquisition.get("kind") == "wikisource_export":
        if txt_fallback_path.exists():
            return txt_fallback_path, {"download_url": download_url, "fallback_mode": "wikisource_parse_text", **metadata}
        if local_path.exists() and _epub_bytes_look_valid(local_path.read_bytes()):
            return local_path, {"download_url": download_url, **metadata}
        plain_text = _fetch_wikisource_plain_text(
            str(spec.acquisition["page_title"]),
            str(spec.acquisition.get("lang", spec.language)),
        )
        txt_fallback_path.write_text(plain_text, encoding="utf-8")
        return txt_fallback_path, {"download_url": download_url, "fallback_mode": "wikisource_parse_text", **metadata}
    should_download = True
    if local_path.exists():
        payload = local_path.read_bytes()
        if extension == ".epub":
            should_download = not _epub_bytes_look_valid(payload)
        else:
            should_download = False
    if should_download:
        payload = _fetch_bytes(download_url)
        if extension == ".epub" and not _epub_bytes_look_valid(payload):
            if spec.acquisition.get("kind") == "wikisource_export":
                plain_text = _fetch_wikisource_plain_text(
                    str(spec.acquisition["page_title"]),
                    str(spec.acquisition.get("lang", spec.language)),
                )
                txt_fallback_path.write_text(plain_text, encoding="utf-8")
                return txt_fallback_path, {
                    "download_url": download_url,
                    "fallback_mode": "wikisource_parse_text",
                    **metadata,
                }
            raise ValueError(f"{spec.source_id} download from {download_url} did not return a valid EPUB payload.")
        local_path.write_bytes(payload)
    return local_path, {"download_url": download_url, **metadata}


def promote_candidate(source_path: Path, promoted_relative_path: str) -> Path:
    """Copy one acquired source into the durable source library."""

    destination = STATE_LIBRARY_ROOT / promoted_relative_path
    if destination.suffix.lower() != source_path.suffix.lower():
        destination = destination.with_suffix(source_path.suffix.lower())
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, destination)
    return destination


def _flatten_document_text(document: dict[str, Any]) -> str:
    """Flatten a parsed book document back into a plain-text stream."""

    lines: list[str] = []
    for chapter in document.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        title = chapter_title(chapter)
        if title:
            lines.append(title)
        for paragraph in chapter.get("paragraphs", []):
            if not isinstance(paragraph, dict):
                continue
            text = str(paragraph.get("text") or "").strip()
            if text:
                lines.append(text)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _extract_epub_plain_text(path: Path) -> str:
    """Extract a plain-text stream from an EPUB document set."""

    book = epub.read_epub(str(path))
    parts: list[str] = []
    for item in book.get_items_of_type(ITEM_DOCUMENT):
        raw = item.get_content().decode("utf-8", errors="replace")
        raw = re.sub(r"<(script|style)[^>]*>.*?</\\1>", "", raw, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<[^>]+>", "\n", raw)
        text = html.unescape(text)
        text = re.sub(r"\r\n?", "\n", text)
        text = re.sub(r"\n{2,}", "\n", text)
        if text.strip():
            parts.append(text.strip())
    return "\n".join(parts).strip() + "\n"


def _is_short_chinese_title_line(line: str) -> bool:
    """Return whether a line is plausible as a Chinese chapter/essay title."""

    stripped = line.strip()
    if not stripped or len(stripped) > 30:
        return False
    if any(pattern.search(stripped) for pattern in CHINESE_METADATA_PATTERNS):
        return False
    if CHINESE_YEAR_HEADING_RE.match(stripped):
        return False
    if re.search(r"[，。！？；：,.!?;:]{2,}", stripped):
        return False
    return True


def _clean_text_lines(text: str) -> list[str]:
    """Normalize a text blob into reasonably clean non-empty lines."""

    lines: list[str] = []
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue
        if ".mw-parser-output" in line or "Project Gutenberg" in line or "Public domain" in line:
            continue
        if "www.gutenberg.org" in line or "ws-export" in line:
            continue
        if any(pattern.search(line) for pattern in CHINESE_METADATA_PATTERNS):
            continue
        if re.search(r"[A-Za-z]", line) and not re.search(r"[\u4e00-\u9fff]", line):
            continue
        if line in {"[", "]"}:
            continue
        lines.append(line)
    return lines


def _extract_chinese_toc_titles(lines: list[str]) -> list[str]:
    """Extract plausible title lines from a Chinese TOC-like block."""

    toc_index = -1
    for index, line in enumerate(lines[:120]):
        if line in {"目次", "目录", "目錄"}:
            toc_index = index
            break
    if toc_index < 0:
        return []

    titles: list[str] = []
    for line in lines[toc_index + 1 : toc_index + 80]:
        if CHINESE_YEAR_HEADING_RE.match(line):
            continue
        if not _is_short_chinese_title_line(line):
            if titles and len(line) > 40:
                break
            continue
        titles.append(line)

    deduped: list[str] = []
    seen: set[str] = set()
    for title in titles:
        if title in seen:
            continue
        seen.add(title)
        deduped.append(title)
    return deduped


def _find_title_positions(lines: list[str], titles: list[str]) -> list[tuple[int, str]]:
    """Locate title occurrences later in a text stream."""

    if not titles:
        return []
    positions: list[tuple[int, str]] = []
    last_index = 0
    search_start = min(len(lines), 40)
    for title in titles:
        found_index: int | None = None
        for index in range(max(search_start, last_index + 1), len(lines)):
            if lines[index] == title:
                found_index = index
                break
        if found_index is None:
            continue
        positions.append((found_index, title))
        last_index = found_index
    return positions


def _segments_from_positions(lines: list[str], positions: list[tuple[int, str]]) -> list[dict[str, str]]:
    """Turn heading positions into title/body segments."""

    if not positions:
        return []
    segments: list[dict[str, str]] = []
    for index, (start, title) in enumerate(positions):
        end = positions[index + 1][0] if index + 1 < len(positions) else len(lines)
        body_lines = [line for line in lines[start + 1 : end] if line and line != title]
        body = "\n".join(body_lines).strip()
        if len(body) < 240:
            continue
        segments.append({"title": title, "body": body})
    return segments


def _segment_chinese_text(text: str) -> list[dict[str, str]]:
    """Segment one Chinese text stream into synthetic chapter-like sections."""

    lines = _clean_text_lines(text)
    serial_positions = [(index, line) for index, line in enumerate(lines) if CHINESE_SERIAL_HEADING_RE.match(line)]
    if len(serial_positions) >= 3:
        segments = _segments_from_positions(lines, serial_positions)
        if len(segments) >= 2:
            return segments

    toc_titles = _extract_chinese_toc_titles(lines)
    toc_positions = _find_title_positions(lines, toc_titles)
    if len(toc_positions) >= 3:
        segments = _segments_from_positions(lines, toc_positions)
        if len(segments) >= 2:
            return segments

    title_positions = [
        (index, line)
        for index, line in enumerate(lines)
        if _is_short_chinese_title_line(line)
        and index > 8
        and not CHINESE_YEAR_HEADING_RE.match(line)
    ]
    if len(title_positions) >= 3:
        segments = _segments_from_positions(lines, title_positions)
        if len(segments) >= 2:
            return segments
    return []


def _write_synthetic_epub(*, title: str, author: str, language: str, segments: list[dict[str, str]], destination: Path) -> Path:
    """Write a simple multi-section EPUB from normalized segments."""

    book = epub.EpubBook()
    book.set_identifier(destination.stem)
    book.set_title(f"{title} (segmented benchmark source)")
    book.set_language(language)
    if author:
        book.add_author(author)

    spine: list[Any] = ["nav"]
    toc: list[Any] = []
    for index, segment in enumerate(segments, start=1):
        body_parts = []
        for paragraph in [part.strip() for part in segment["body"].split("\n") if part.strip()]:
            body_parts.append(f"<p>{html.escape(paragraph)}</p>")
        chapter = epub.EpubHtml(
            title=segment["title"],
            file_name=f"chapter_{index:03d}.xhtml",
            lang=language,
        )
        chapter.content = f"<h1>{html.escape(segment['title'])}</h1>{''.join(body_parts)}"
        book.add_item(chapter)
        toc.append(chapter)
        spine.append(chapter)

    book.toc = tuple(toc)
    book.spine = spine
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    destination.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(destination), book, {})
    return destination


def maybe_normalize_structured_source(
    *,
    spec: CandidateSpec,
    local_path: Path,
    document: dict[str, Any],
) -> tuple[Path | None, dict[str, Any] | None]:
    """Attempt to normalize weak Chinese public sources into a synthetic multi-chapter EPUB."""

    if spec.language != "zh":
        return None, None

    absolute_local_path = local_path if local_path.is_absolute() else ROOT / local_path
    raw_text: str
    if absolute_local_path.suffix.lower() == ".txt":
        raw_text = absolute_local_path.read_text(encoding="utf-8", errors="replace")
    elif absolute_local_path.suffix.lower() == ".epub":
        raw_text = _extract_epub_plain_text(absolute_local_path)
    else:
        raw_text = _flatten_document_text(document)

    segments = _segment_chinese_text(raw_text)
    if len(segments) < 2:
        return None, None

    normalized_path = absolute_local_path.with_suffix(".normalized.epub")
    _write_synthetic_epub(
        title=spec.title,
        author=spec.author,
        language=spec.language,
        segments=segments,
        destination=normalized_path,
    )
    metadata = {
        "normalization_status": "synthetic_multichapter_epub",
        "normalized_from_relative_local_path": str(absolute_local_path.relative_to(ROOT)),
        "normalized_section_count": len(segments),
    }
    return normalized_path, metadata


def load_book_document(output_dir: Path) -> dict[str, Any]:
    """Load the shared parsed-book substrate for one output directory."""

    return load_json(output_dir / "public" / "book_document.json")


def chapter_sentence_count(chapter: dict[str, Any]) -> int:
    """Return one chapter's sentence count from the shared substrate."""

    return len(chapter.get("sentences") or [])


def chapter_paragraph_count(chapter: dict[str, Any]) -> int:
    """Return one chapter's paragraph count."""

    return len(chapter.get("paragraphs") or [])


def chapter_title(chapter: dict[str, Any]) -> str:
    """Return a stable display title for one chapter."""

    return str(chapter.get("title") or chapter.get("chapter_heading") or chapter.get("id") or "").strip()


def is_front_matter(chapter: dict[str, Any], *, language: str, book_title: str, chapter_index: int) -> tuple[bool, str | None]:
    """Return whether one chapter should be excluded from chapter-corpus selection."""

    title = chapter_title(chapter)
    sentence_count = chapter_sentence_count(chapter)
    lowered_title = title.lower()
    if _normalize_title(title) == _normalize_title(book_title) and sentence_count < 40 and chapter_index <= 1:
        return True, "book_title_stub"
    if language == "zh" and title in {"关于", "關於"}:
        return True, "about_stub"
    if "project gutenberg" in lowered_title or "license" in lowered_title:
        return True, "license_stub"
    if language == "zh" and title and re.search(r"[A-Za-z]", title) and not re.search(r"[\u4e00-\u9fff]", title):
        return True, "latin_heading_stub"
    for pattern in FRONT_MATTER_PATTERNS[language]:
        if pattern.search(title if language == "zh" else lowered_title):
            return True, f"title:{pattern.pattern}"
    if chapter_index == 0 and sentence_count < 40:
        return True, "very_short_opening"
    if sentence_count < 12:
        return True, "too_short"
    return False, None


def chapter_quality_score(chapter: dict[str, Any], *, language: str, chapter_index: int, total_chapters: int, book_title: str) -> float:
    """Score one chapter for benchmark usefulness."""

    front_matter, _reason = is_front_matter(
        chapter,
        language=language,
        book_title=book_title,
        chapter_index=chapter_index,
    )
    if front_matter:
        return -1000.0
    sentences = chapter_sentence_count(chapter)
    score = 0.0
    if 60 <= sentences <= 320:
        score += 5.0
    elif 35 <= sentences <= 500:
        score += 4.0
    elif 20 <= sentences <= 700:
        score += 2.5
    else:
        score += 1.0
    fraction = (chapter_index + 1) / max(total_chapters, 1)
    if 0.15 <= fraction <= 0.85:
        score += 1.0
    if chapter_paragraph_count(chapter) >= 8:
        score += 0.5
    title = chapter_title(chapter)
    if title and len(title) < 80:
        score += 0.25
    return score


def choose_candidate_chapters(
    *,
    chapters: list[dict[str, Any]],
    language: str,
    book_title: str,
    limit: int = 4,
) -> list[dict[str, Any]]:
    """Select a spread of chapter candidates for one book."""

    scored: list[dict[str, Any]] = []
    total = len(chapters)
    for index, chapter in enumerate(chapters):
        score = chapter_quality_score(chapter, language=language, chapter_index=index, total_chapters=total, book_title=book_title)
        if score < 0:
            continue
        bucket = "early" if total <= 1 or index / total < 0.33 else "middle" if index / total < 0.66 else "late"
        scored.append(
            {
                "chapter": chapter,
                "chapter_index": index,
                "score": score,
                "position_bucket": bucket,
            }
        )
    chosen: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for bucket_name in ("early", "middle", "late"):
        bucket_items = [item for item in scored if item["position_bucket"] == bucket_name]
        if not bucket_items:
            continue
        best = max(bucket_items, key=lambda item: item["score"])
        chapter_id = str(best["chapter"].get("id") or "")
        if chapter_id in seen_ids:
            continue
        chosen.append(best)
        seen_ids.add(chapter_id)
    for item in sorted(scored, key=lambda entry: entry["score"], reverse=True):
        chapter_id = str(item["chapter"].get("id") or "")
        if chapter_id in seen_ids:
            continue
        chosen.append(item)
        seen_ids.add(chapter_id)
        if len(chosen) >= limit:
            break
    return chosen[:limit]


def median(values: list[int]) -> float | None:
    """Return a median when values are present."""

    if not values:
        return None
    return float(statistics.median(values))


def screen_source_book(
    *,
    spec: CandidateSpec,
    local_path: Path,
    relative_local_path: str,
    acquisition_metadata: dict[str, Any] | None = None,
    selection_priority: int | None = None,
) -> dict[str, Any]:
    """Parse and screen one source book into the unified source-record schema."""

    provisioned = ensure_canonical_parse(local_path)
    document = load_book_document(provisioned.output_dir)
    chapters = [dict(chapter) for chapter in document.get("chapters", []) if isinstance(chapter, dict)]
    sentence_counts = [chapter_sentence_count(chapter) for chapter in chapters]
    paragraph_counts = [chapter_paragraph_count(chapter) for chapter in chapters]
    candidate_chapters = choose_candidate_chapters(
        chapters=chapters,
        language=spec.language,
        book_title=spec.title,
        limit=6,
    )
    corpus_lane = "chapter_corpus_eligible" if len(candidate_chapters) >= 2 else "excerpt_only"
    normalization_metadata: dict[str, Any] | None = None
    if corpus_lane == "excerpt_only":
        normalized_path, normalization_metadata = maybe_normalize_structured_source(
            spec=spec,
            local_path=local_path,
            document=document,
        )
        if normalized_path is not None:
            local_path = normalized_path
            relative_local_path = str(normalized_path.relative_to(ROOT))
            provisioned = ensure_canonical_parse(normalized_path)
            document = load_book_document(provisioned.output_dir)
            chapters = [dict(chapter) for chapter in document.get("chapters", []) if isinstance(chapter, dict)]
            sentence_counts = [chapter_sentence_count(chapter) for chapter in chapters]
            paragraph_counts = [chapter_paragraph_count(chapter) for chapter in chapters]
            candidate_chapters = choose_candidate_chapters(
                chapters=chapters,
                language=spec.language,
                book_title=spec.title,
                limit=6,
            )
            corpus_lane = "chapter_corpus_eligible" if len(candidate_chapters) >= 2 else "excerpt_only"
    if not chapters:
        corpus_lane = "reject"
    output_dir = provisioned.output_dir if provisioned.output_dir.is_absolute() else ROOT / provisioned.output_dir
    record = {
        "source_id": spec.source_id,
        "title": spec.title,
        "author": spec.author,
        "language": spec.language,
        "origin": spec.origin,
        "source_url": acquisition_metadata.get("download_url") if acquisition_metadata else None,
        "storage_mode": spec.storage_mode,
        "relative_local_path": relative_local_path,
        "type_tags": list(spec.type_tags),
        "role_tags": canonicalize_role_tags(spec.role_tags, spec.type_tags),
        "selection_priority": int(selection_priority if selection_priority is not None else spec.selection_priority),
        "notes": list(spec.notes),
        "sha256": sha256_file(local_path),
        "file_size": local_path.stat().st_size,
        "output_dir": str(output_dir.relative_to(ROOT)),
        "detected_book_language": provisioned.book_language,
        "output_language": provisioned.output_language,
        "chapter_count": len(chapters),
        "sentence_count_total": int(sum(sentence_counts)),
        "median_chapter_sentences": median(sentence_counts),
        "median_chapter_paragraphs": median(paragraph_counts),
        "screening_status": "screened_v2",
        "corpus_lane": corpus_lane,
        "candidate_chapters": [
            {
                "chapter_id": str(item["chapter"].get("id") or ""),
                "chapter_number": int(item["chapter"].get("chapter_number") or 0),
                "chapter_title": chapter_title(item["chapter"]),
                "sentence_count": chapter_sentence_count(item["chapter"]),
                "paragraph_count": chapter_paragraph_count(item["chapter"]),
                "href": item["chapter"].get("href"),
                "spine_index": item["chapter"].get("spine_index"),
                "position_bucket": item["position_bucket"],
                "score": round(float(item["score"]), 3),
            }
            for item in candidate_chapters
        ],
    }
    if acquisition_metadata:
        record["acquisition"] = acquisition_metadata
    if normalization_metadata:
        record.update(normalization_metadata)
    return record


def _author_key(record: dict[str, Any]) -> str:
    return _normalize_title(str(record.get("author", "")))


def select_promoted_books(source_records: list[dict[str, Any]], *, language: str, target_count: int = 6) -> list[dict[str, Any]]:
    """Select the promoted book set for one language while enforcing role coverage."""

    candidates = [record for record in source_records if record.get("language") == language]
    if len(candidates) <= target_count:
        return list(candidates)

    def valid_combo(combo: tuple[dict[str, Any], ...]) -> bool:
        author_counts: dict[str, int] = {}
        for record in combo:
            author = _author_key(record)
            author_counts[author] = author_counts.get(author, 0) + 1
            if author_counts[author] > 2:
                return False
        return True

    def combo_score(combo: tuple[dict[str, Any], ...]) -> tuple[float, float, float, float, float]:
        role_counts = {
            role: sum(1 for record in combo if role in list(record.get("role_tags") or []))
            for role in PROMOTION_ROLE_QUOTAS
        }
        quota_score = sum(min(role_counts[role], PROMOTION_ROLE_QUOTAS[role]) for role in PROMOTION_ROLE_QUOTAS)
        depth_score = sum(role_counts.values())
        chapter_eligible_count = sum(1 for record in combo if record.get("corpus_lane") == "chapter_corpus_eligible")
        chapter_capacity = sum(len(record.get("candidate_chapters") or []) for record in combo)
        author_diversity = len({_author_key(record) for record in combo})
        priority_score = -sum(int(record.get("selection_priority", 9999)) for record in combo)
        return (
            quota_score * 100.0 + depth_score * 5.0,
            float(chapter_eligible_count),
            float(chapter_capacity),
            float(author_diversity),
            float(priority_score),
        )

    best_combo: tuple[dict[str, Any], ...] | None = None
    best_score: tuple[float, float, float, float, float] | None = None
    for combo in combinations(candidates, target_count):
        if not valid_combo(combo):
            continue
        score = combo_score(combo)
        if best_score is None or score > best_score:
            best_score = score
            best_combo = combo

    if best_combo is None:
        candidates.sort(
            key=lambda record: (
                int(record.get("selection_priority", 9999)),
                record.get("corpus_lane") != "chapter_corpus_eligible",
                -len(record.get("candidate_chapters") or []),
            )
        )
        return candidates[:target_count]

    selected = sorted(
        best_combo,
        key=lambda record: (
            record.get("corpus_lane") != "chapter_corpus_eligible",
            int(record.get("selection_priority", 9999)),
            -len(record.get("candidate_chapters") or []),
        ),
    )
    return [dict(record) for record in selected]


def build_source_index(source_records: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Index source records by source_id."""

    return {str(record["source_id"]): dict(record) for record in source_records}


def chapter_row_from_candidate(source: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    """Build one chapter-corpus row from a source record and candidate chapter."""

    chapter_id = str(candidate["chapter_id"])
    return {
        "chapter_case_id": f"{source['source_id']}__{chapter_id}",
        "source_id": source["source_id"],
        "book_title": source["title"],
        "author": source["author"],
        "language_track": source["language"],
        "type_tags": list(source.get("type_tags") or []),
        "role_tags": list(source.get("role_tags") or []),
        "output_dir": str(source["output_dir"]),
        "chapter_id": chapter_id,
        "chapter_number": int(candidate["chapter_number"]),
        "chapter_title": str(candidate["chapter_title"]),
        "sentence_count": int(candidate["sentence_count"]),
        "paragraph_count": int(candidate["paragraph_count"]),
        "href": candidate.get("href"),
        "spine_index": candidate.get("spine_index"),
        "candidate_position_bucket": str(candidate["position_bucket"]),
        "candidate_score": float(candidate["score"]),
        "selection_status": "candidate_v2",
        "selected_for_public_benchmark": bool(source.get("selected_for_public_benchmark")),
        "selection_priority": int(source.get("selection_priority", 9999) or 9999),
    }


def _chapter_row_sort_key(row: dict[str, Any]) -> tuple[int, int, float, int, int]:
    """Prefer the newly promoted public-first books when freezing corpus rows."""

    role_tags = list(row.get("role_tags") or [])
    modern_bonus = 0 if "modern_vernacular" in role_tags else 1
    promoted_bonus = 0 if row.get("selected_for_public_benchmark") else 1
    return (
        promoted_bonus,
        modern_bonus,
        -float(row["candidate_score"]),
        int(row.get("selection_priority", 9999)),
        int(row["chapter_number"]),
    )


def build_combined_public_pool(existing_manifest_path: Path, promoted_new_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Re-screen the old tracked public seed books and combine them with the new promoted set."""

    existing_manifest = load_json(existing_manifest_path)
    existing_records: list[dict[str, Any]] = []
    for record in existing_manifest.get("books", []):
        relative_local_path = str(record.get("relative_local_path") or "")
        local_path = ROOT / relative_local_path
        if not local_path.exists():
            continue
        spec = CandidateSpec(
            source_id=str(record["source_id"]),
            title=str(record["title"]),
            author=str(record["author"]),
            language=str(record["language"]),
            origin="public-open-access",
            storage_mode="tracked",
            promoted_local_path=str(record.get("local_path") or relative_local_path.replace("state/library_sources/", "")),
            acquisition={"kind": "legacy_existing_source"},
            type_tags=list(record.get("type_tags") or []),
            role_tags=list(record.get("role_tags") or list(record.get("type_tags") or [])),
            selection_priority=50,
            notes=list(record.get("suitability_notes") or []),
        )
        existing_records.append(
            screen_source_book(
                spec=spec,
                local_path=local_path,
                relative_local_path=relative_local_path,
                acquisition_metadata={"download_url": record.get("source_url")},
                selection_priority=50,
            )
        )
    return existing_records + [dict(record) for record in promoted_new_records]


def select_final_chapter_rows(source_records: list[dict[str, Any]], *, language: str) -> list[dict[str, Any]]:
    """Freeze the chapter corpus for one language from the combined public pool."""

    candidate_rows: list[dict[str, Any]] = []
    for source in source_records:
        if source.get("language") != language or source.get("corpus_lane") != "chapter_corpus_eligible":
            continue
        for candidate in source.get("candidate_chapters", []):
            candidate_rows.append(chapter_row_from_candidate(source, candidate))

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    source_counts: dict[str, int] = {}
    target_count = sum(CHAPTER_ROLE_QUOTAS.values()) + RESERVE_CHAPTER_COUNT

    def can_take(row: dict[str, Any], *, max_per_source: int) -> bool:
        source_id = str(row["source_id"])
        if row["chapter_case_id"] in selected_ids:
            return False
        return source_counts.get(source_id, 0) < max_per_source

    def take_rows_for_role(role: str, count: int, *, max_per_source: int) -> None:
        nonlocal selected
        candidates = [
            row
            for row in sorted(candidate_rows, key=_chapter_row_sort_key)
            if role in list(row.get("role_tags") or [])
        ]
        picked = 0
        for row in candidates:
            if picked >= count:
                break
            if not can_take(row, max_per_source=max_per_source):
                continue
            row = dict(row)
            row["selection_role"] = role
            row["selection_status"] = "selected_v2"
            selected.append(row)
            selected_ids.add(str(row["chapter_case_id"]))
            source_id = str(row["source_id"])
            source_counts[source_id] = source_counts.get(source_id, 0) + 1
            picked += 1
        if picked < count:
            for row in sorted(candidate_rows, key=_chapter_row_sort_key):
                if picked >= count:
                    break
                if row["chapter_case_id"] in selected_ids:
                    continue
                if not can_take(row, max_per_source=max_per_source):
                    continue
                fallback_row = dict(row)
                fallback_row["selection_role"] = role
                fallback_row["selection_status"] = "selected_v2_role_fallback"
                selected.append(fallback_row)
                selected_ids.add(str(row["chapter_case_id"]))
                source_id = str(row["source_id"])
                source_counts[source_id] = source_counts.get(source_id, 0) + 1
                picked += 1

    for max_per_source in (MAX_CHAPTERS_PER_SOURCE_DEFAULT, MAX_CHAPTERS_PER_SOURCE_FALLBACK):
        selected = []
        selected_ids = set()
        source_counts = {}
        for role, quota in CHAPTER_ROLE_QUOTAS.items():
            take_rows_for_role(role, quota, max_per_source=max_per_source)

        remaining = [
            row
            for row in sorted(candidate_rows, key=_chapter_row_sort_key)
            if row["chapter_case_id"] not in selected_ids
        ]
        reserves_added = 0
        for row in remaining:
            if reserves_added >= RESERVE_CHAPTER_COUNT:
                break
            if not can_take(row, max_per_source=max_per_source):
                continue
            reserve_row = dict(row)
            reserve_row["selection_role"] = "reserve"
            reserve_row["selection_status"] = "selected_v2"
            selected.append(reserve_row)
            selected_ids.add(str(row["chapter_case_id"]))
            source_id = str(row["source_id"])
            source_counts[source_id] = source_counts.get(source_id, 0) + 1
            reserves_added += 1

        if len(selected) >= target_count:
            return selected[:target_count]

    return selected[:target_count]


def select_runtime_fixture_chapters(chapter_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Choose the chapter subset used to generate runtime fixtures."""

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    source_counts: dict[str, int] = {}
    target_total = len(CHAPTER_ROLE_QUOTAS) * RUNTIME_CHAPTERS_PER_ROLE
    for role in ("expository", "argumentative", "narrative_reflective", "reference_heavy"):
        role_rows = [
            row
            for row in sorted(chapter_rows, key=_chapter_row_sort_key)
            if row.get("selection_role") == role
        ]
        picked = 0
        for row in role_rows:
            if picked >= RUNTIME_CHAPTERS_PER_ROLE:
                break
            if row["chapter_case_id"] in selected_ids:
                continue
            source_id = str(row["source_id"])
            if source_counts.get(source_id, 0) >= 1:
                continue
            selected.append(dict(row))
            selected_ids.add(str(row["chapter_case_id"]))
            source_counts[source_id] = source_counts.get(source_id, 0) + 1
            picked += 1

    if len(selected) < target_total:
        for row in sorted(chapter_rows, key=_chapter_row_sort_key):
            if len(selected) >= target_total:
                break
            if row["chapter_case_id"] in selected_ids:
                continue
            source_id = str(row["source_id"])
            if source_counts.get(source_id, 0) >= MAX_RUNTIME_CHAPTERS_PER_SOURCE:
                continue
            selected.append(dict(row))
            selected_ids.add(str(row["chapter_case_id"]))
            source_counts[source_id] = source_counts.get(source_id, 0) + 1
    return selected


def make_runtime_fixtures(chapter_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build runtime fixtures for the selected runtime chapter subset."""

    fixtures: list[dict[str, Any]] = []
    for row in chapter_rows:
        sentence_count = int(row["sentence_count"])
        if sentence_count < 18:
            continue
        targets = {
            "warm": max(1, int(sentence_count * 0.2)),
            "cold": max(1, int(sentence_count * 0.5)),
            "reconstitution": max(1, int(sentence_count * 0.8)),
        }
        for resume_kind in RUNTIME_RESUME_KINDS:
            fixtures.append(
                {
                    "fixture_id": f"{row['chapter_case_id']}__{resume_kind}",
                    "source_id": row["source_id"],
                    "language_track": row["language_track"],
                    "chapter_case_id": row["chapter_case_id"],
                    "chapter_number": row["chapter_number"],
                    "chapter_title": row["chapter_title"],
                    "selection_role": row["selection_role"],
                    "resume_kind": resume_kind,
                    "target_sentence_index": targets[resume_kind],
                    "fixture_status": "expanded_v2",
                    "notes": "Runtime/resume fixture derived from the expanded public-first chapter corpus.",
                }
            )
    return fixtures


def _excerpt_window(sentences: list[dict[str, Any]], center_fraction: float, *, radius: int = 3) -> tuple[int, int]:
    if not sentences:
        return (0, 0)
    center = max(0, min(len(sentences) - 1, int(len(sentences) * center_fraction)))
    start = max(0, center - radius)
    end = min(len(sentences), center + radius + 1)
    if end <= start:
        end = min(len(sentences), start + 1)
    return start, end


def _excerpt_bucket_preferences(selection_role: str, position_bucket: str) -> list[str]:
    if selection_role == "expository":
        preferences = ["distinction_definition", "anchored_reaction_selectivity", "reconsolidation_later_reinterpretation"]
    elif selection_role == "argumentative":
        preferences = ["tension_reversal", "callback_bridge", "anchored_reaction_selectivity"]
    elif selection_role == "narrative_reflective":
        preferences = ["anchored_reaction_selectivity", "reconsolidation_later_reinterpretation", "tension_reversal"]
    else:
        preferences = ["callback_bridge", "anchored_reaction_selectivity", "reconsolidation_later_reinterpretation"]
    if position_bucket == "late":
        preferences = sorted(preferences, key=lambda bucket: bucket != "reconsolidation_later_reinterpretation")
    if position_bucket == "middle":
        preferences = sorted(preferences, key=lambda bucket: bucket != "callback_bridge")
    return preferences


def make_excerpt_candidates(chapter_rows: list[dict[str, Any]], source_index: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Build excerpt candidates from the final chapter corpus."""

    candidates: list[dict[str, Any]] = []
    fractions = (0.2, 0.5, 0.8)
    for row in chapter_rows:
        source = source_index[str(row["source_id"])]
        document = load_book_document(ROOT / row["output_dir"])
        chapter = next(ch for ch in document["chapters"] if str(ch["id"]) == str(row["chapter_id"]))
        sentences = chapter.get("sentences") or []
        for index, fraction in enumerate(fractions, start=1):
            start, end = _excerpt_window(sentences, fraction, radius=3 if row["language_track"] == "en" else 2)
            window = sentences[start:end]
            if not window:
                continue
            excerpt_text = "\n".join(str(sentence.get("text", "")) for sentence in window).strip()
            if len(excerpt_text) < 120:
                continue
            excerpt_score = float(row["candidate_score"])
            excerpt_score += 0.5 if 280 <= len(excerpt_text) <= 900 else 0
            position_bucket = "early" if fraction < 0.34 else "middle" if fraction < 0.67 else "late"
            candidates.append(
                {
                    "candidate_case_id": f"{row['chapter_case_id']}__excerpt_{index}",
                    "source_id": row["source_id"],
                    "book_title": row["book_title"],
                    "author": row["author"],
                    "output_language": row["language_track"],
                    "chapter_id": int(row["chapter_id"]),
                    "chapter_number": row["chapter_number"],
                    "chapter_title": row["chapter_title"],
                    "start_sentence_id": window[0]["sentence_id"],
                    "end_sentence_id": window[-1]["sentence_id"],
                    "excerpt_text": excerpt_text,
                    "role_tags": list(source.get("role_tags") or []),
                    "selection_role": str(row["selection_role"]),
                    "position_bucket": position_bucket,
                    "excerpt_score": round(excerpt_score, 3),
                    "bucket_preferences": _excerpt_bucket_preferences(str(row["selection_role"]), position_bucket),
                }
            )
    return candidates


def _curated_bucket_metadata(bucket: str) -> tuple[list[str], list[str], str, str]:
    if bucket == "distinction_definition":
        return (
            ["EQ-CM-002", "EQ-AV2-002", "EQ-AV2-005"],
            ["distinction", "definition_pressure", "anchored_reaction"],
            "Selected to test whether the mechanism can close around a live distinction instead of flattening the passage into generic paraphrase.",
            "Does the mechanism identify the key distinction cleanly and stay answerable to the specific passage?",
        )
    if bucket == "tension_reversal":
        return (
            ["EQ-CM-002", "EQ-AV2-003", "EQ-AV2-005"],
            ["tension_reversal", "controller_move_quality", "anchored_reaction"],
            "Selected to test whether the mechanism notices the passage's pressure or reversal without overblowing it.",
            "Does the mechanism stay with the passage's tension and make a proportionate reading move?",
        )
    if bucket == "callback_bridge":
        return (
            ["EQ-CM-002", "EQ-CM-004", "EQ-AV2-004"],
            ["bridge_potential", "callback", "cross_span_link"],
            "Selected to test whether bridge-worthy or callback-worthy pressure remains text-grounded.",
            "Does the mechanism connect the passage to prior material honestly rather than inventing a loose association?",
        )
    if bucket == "anchored_reaction_selectivity":
        return (
            ["EQ-CM-002", "EQ-AV2-005"],
            ["reaction_anchor", "selective_legibility", "visible_thought"],
            "Selected to test whether the mechanism emits a visible reaction only when the line genuinely earns it.",
            "Is the visible reaction anchored, selective, and worth keeping on reread?",
        )
    return (
        ["EQ-CM-004", "EQ-AV2-006"],
        ["reconsolidation_candidate", "later_reinterpretation", "durable_trace_candidate"],
        "Selected to test whether this passage could later be carried forward or reconsolidated meaningfully.",
        "Does the mechanism preserve what would make this passage valuable to return to later?",
    )


def curate_excerpt_cases(candidates: list[dict[str, Any]], *, language: str) -> list[dict[str, Any]]:
    """Select the curated excerpt benchmark layer for one language."""

    selected: list[dict[str, Any]] = []
    selected_case_ids: set[str] = set()
    chapter_counts: dict[str, int] = {}

    def can_take(candidate: dict[str, Any]) -> bool:
        chapter_key = f"{candidate['source_id']}::{candidate['chapter_id']}"
        if candidate["candidate_case_id"] in selected_case_ids:
            return False
        return chapter_counts.get(chapter_key, 0) < 1

    def add_case(candidate: dict[str, Any], bucket: str, *, fallback: bool = False) -> None:
        question_ids, phenomena, selection_reason, judge_focus = _curated_bucket_metadata(bucket)
        curated_case = {
            "case_id": f"{candidate['source_id']}__{candidate['chapter_id']}__{bucket}__v2",
            "case_title": f"{candidate['book_title']} / {candidate['chapter_title']} / {bucket}",
            "split": "curated_v2",
            "curation_status": "builder_curated_v2_fallback_fill" if fallback else "builder_curated_v2",
            "source_policy": "repo-safe-public-source",
            "source_id": candidate["source_id"],
            "book_title": candidate["book_title"],
            "author": candidate["author"],
            "output_language": language,
            "chapter_id": candidate["chapter_id"],
            "chapter_number": candidate["chapter_number"],
            "chapter_title": candidate["chapter_title"],
            "start_sentence_id": candidate["start_sentence_id"],
            "end_sentence_id": candidate["end_sentence_id"],
            "excerpt_text": candidate["excerpt_text"],
            "question_ids": question_ids,
            "phenomena": phenomena,
            "selection_reason": selection_reason,
            "judge_focus": judge_focus,
            "notes": (
                "Fallback-filled benchmark candidate used to keep the curated bucket quota intact when the strict preference pool was too thin."
                if fallback
                else "Builder-curated benchmark candidate from the public-first large corpus expansion. Still eligible for later human refinement."
            ),
        }
        selected.append(curated_case)
        selected_case_ids.add(str(candidate["candidate_case_id"]))
        chapter_key = f"{candidate['source_id']}::{candidate['chapter_id']}"
        chapter_counts[chapter_key] = chapter_counts.get(chapter_key, 0) + 1

    def fallback_candidates_for_bucket(bucket: str) -> list[dict[str, Any]]:
        preferred_roles = {
            "distinction_definition": {"expository", "argumentative"},
            "tension_reversal": {"argumentative", "narrative_reflective"},
            "callback_bridge": {"argumentative", "reference_heavy", "narrative_reflective"},
            "anchored_reaction_selectivity": {"expository", "argumentative", "narrative_reflective", "reference_heavy"},
            "reconsolidation_later_reinterpretation": {"narrative_reflective", "reference_heavy"},
        }.get(bucket, set())
        return [
            candidate
            for candidate in sorted(candidates, key=lambda item: (-float(item["excerpt_score"]), int(item["chapter_number"])))
            if candidate.get("output_language") == language
            and (
                bucket in list(candidate.get("bucket_preferences") or [])
                or candidate.get("selection_role") in preferred_roles
                or bool(preferred_roles.intersection(set(candidate.get("role_tags") or [])))
            )
        ]

    for bucket, quota in CURATED_BUCKET_QUOTAS.items():
        bucket_candidates = [
            candidate
            for candidate in sorted(candidates, key=lambda item: (-float(item["excerpt_score"]), int(item["chapter_number"])))
            if bucket in list(candidate.get("bucket_preferences") or [])
            and candidate.get("output_language") == language
        ]
        picked = 0
        for candidate in bucket_candidates:
            if picked >= quota:
                break
            if not can_take(candidate):
                continue
            add_case(candidate, bucket)
            picked += 1
        if picked < quota:
            for candidate in fallback_candidates_for_bucket(bucket):
                if picked >= quota:
                    break
                if not can_take(candidate):
                    continue
                add_case(candidate, bucket, fallback=True)
                picked += 1

    reserve_candidates = [
        candidate
        for candidate in sorted(candidates, key=lambda item: (-float(item["excerpt_score"]), int(item["chapter_number"])))
        if candidate.get("output_language") == language and candidate["candidate_case_id"] not in selected_case_ids
    ]
    if reserve_candidates:
        reserve = reserve_candidates[0]
        selected.append(
            {
                "case_id": f"{reserve['source_id']}__{reserve['chapter_id']}__reserve__v2",
                "case_title": f"{reserve['book_title']} / {reserve['chapter_title']} / reserve",
                "split": "curated_v2",
                "curation_status": "builder_curated_v2",
                "source_policy": "repo-safe-public-source",
                "source_id": reserve["source_id"],
                "book_title": reserve["book_title"],
                "author": reserve["author"],
                "output_language": language,
                "chapter_id": reserve["chapter_id"],
                "chapter_number": reserve["chapter_number"],
                "chapter_title": reserve["chapter_title"],
                "start_sentence_id": reserve["start_sentence_id"],
                "end_sentence_id": reserve["end_sentence_id"],
                "excerpt_text": reserve["excerpt_text"],
                "question_ids": ["EQ-CM-002", "EQ-AV2-005"],
                "phenomena": ["reserve_case", "anchored_reaction"],
                "selection_reason": "Reserve benchmark case kept for later swap-in or holdout use.",
                "judge_focus": "If promoted later, would this passage reward a grounded, selective reading move?",
                "notes": "Reserve builder-curated case from the public-first large corpus expansion.",
            }
        )
    return selected


def make_compatibility_fixtures(chapter_rows: list[dict[str, Any]], *, fixture_status_by_case: dict[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Build compatibility fixtures from the chapter corpus."""

    fixture_status_by_case = fixture_status_by_case or {}
    fixtures: list[dict[str, Any]] = []
    for row in chapter_rows:
        chapter_case_id = str(row["chapter_case_id"])
        materialized = fixture_status_by_case.get(chapter_case_id) or {}
        fixture = {
            "fixture_id": f"{chapter_case_id}__compat",
            "source_id": row["source_id"],
            "language_track": row["language_track"],
            "chapter_case_id": chapter_case_id,
            "target_surfaces": ["analysis_state", "activity", "chapter_detail", "marks"],
            "fixture_kind": "compat_projection_audit_spec",
            "fixture_status": str(materialized.get("fixture_status") or "spec_only"),
            "notes": str(materialized.get("notes") or "Compatibility audit fixture generated from the expanded public-first chapter corpus."),
        }
        if materialized:
            fixture.update({key: value for key, value in materialized.items() if key not in {"fixture_status", "notes"}})
        fixtures.append(fixture)
    return fixtures


def dataset_manifest(
    *,
    dataset_id: str,
    family: str,
    language_track: str,
    description: str,
    primary_file: str,
    source_manifest_refs: list[str],
    split_refs: list[str],
    storage_mode: str = "tracked",
) -> dict[str, Any]:
    """Build one dataset manifest payload."""

    return {
        "dataset_id": dataset_id,
        "family": family,
        "language_track": language_track,
        "version": "2",
        "description": description,
        "primary_file": primary_file,
        "question_ids": QUESTION_IDS_BY_FAMILY[family],
        "source_manifest_refs": source_manifest_refs,
        "split_refs": split_refs,
        "storage_mode": storage_mode,
    }

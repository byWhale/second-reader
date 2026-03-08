"""Filesystem helpers for Iterator-Reader outputs."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from .models import BookStructure, StructureChapter


def slugify(value: str) -> str:
    """Create a stable directory slug from book metadata."""
    cleaned = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE).strip().lower()
    cleaned = re.sub(r"[-\s]+", "-", cleaned)
    return cleaned or "book"


def infer_chapter_number(title: str) -> int | None:
    """Infer a human-facing chapter number from a chapter title."""
    normalized = (title or "").strip()
    patterns = (
        r"^chapter\s+(\d+)\b",
        r"^第\s*(\d+)\s*章\b",
    )
    for pattern in patterns:
        match = re.match(pattern, normalized, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def chapter_reference(chapter: StructureChapter) -> str:
    """Return the human-facing chapter reference used in logs and lookup."""
    number = chapter.get("chapter_number")
    if number is None:
        number = infer_chapter_number(chapter.get("title", ""))
    if number is not None:
        return f"Chapter {number}"
    return chapter.get("title", f'Section {chapter.get("id", "")}')


def chapter_anchor_prefix(chapter: StructureChapter) -> str:
    """Return a stable human-readable anchor prefix for non-numbered chapters."""
    title = str(chapter.get("title", "") or "").strip()
    if title:
        normalized = re.sub(r"\s+", " ", title)
        cleaned = re.sub(r"[^\w\s]", " ", normalized, flags=re.UNICODE).strip()
        tokens = [token for token in cleaned.split() if token]
        if tokens:
            prefix = "_".join(tokens[:3]).strip("_")
            if prefix:
                return prefix[:40]
    return f'Part{int(chapter.get("id", 0))}'


def segment_reference(chapter: StructureChapter, segment_id: str) -> str:
    """Render a user-facing segment anchor aligned with chapter numbering rules."""
    raw_id = str(segment_id or "").strip()
    if "." not in raw_id:
        return raw_id
    _raw_prefix, suffix = raw_id.split(".", 1)

    number = chapter.get("chapter_number")
    if number is None:
        number = infer_chapter_number(chapter.get("title", ""))
    if number is not None:
        return f"{number}.{suffix}"
    return f"{chapter_anchor_prefix(chapter)}.{suffix}"


def chapter_output_name(chapter: StructureChapter) -> str:
    """Stable markdown filename for one chapter."""
    number = chapter.get("chapter_number")
    if number is None:
        number = infer_chapter_number(chapter.get("title", ""))
    if number is not None:
        return f"ch{number:02d}_deep_read.md"

    title_slug = slugify(chapter.get("title", "")) or "section"
    return f'part{chapter.get("id", 0):02d}_{title_slug}_deep_read.md'


def display_segment_id(chapter: StructureChapter, segment_id: str) -> str:
    """Render a user-facing segment id aligned with the visible chapter number."""
    return segment_reference(chapter, segment_id)


def resolve_output_dir(
    book_path: Path,
    book_title: str,
    book_language: str,
    output_language: str,
) -> Path:
    """Resolve the output directory for a given book."""
    slug = slugify(book_title or book_path.stem)
    if output_language != book_language:
        slug = f"{slug}-{output_language}"
    return Path("output") / slug


def book_id_from_output_dir(output_dir: Path) -> str:
    """Derive the stable book id from the output directory name."""
    return output_dir.name


def ensure_output_dir(path: Path) -> None:
    """Create output directory if missing."""
    path.mkdir(parents=True, exist_ok=True)


def structure_file(output_dir: Path) -> Path:
    """Path to structure.json inside an output directory."""
    return output_dir / "structure.json"


def structure_markdown_file(output_dir: Path) -> Path:
    """Path to structure.md inside an output directory."""
    return output_dir / "structure.md"


def assets_dir(output_dir: Path) -> Path:
    """Directory storing frontend-accessible source assets."""
    return output_dir / "_assets"


def source_asset_file(output_dir: Path) -> Path:
    """Path to the copied source EPUB asset."""
    return assets_dir(output_dir) / "source.epub"


def cover_asset_file(output_dir: Path, extension: str = ".jpg") -> Path:
    """Path to the copied cover image asset."""
    suffix = extension if extension.startswith(".") else f".{extension}"
    return assets_dir(output_dir) / f"cover{suffix}"


def existing_cover_asset_file(output_dir: Path) -> Path | None:
    """Return the first persisted cover image asset if present."""
    for path in sorted(assets_dir(output_dir).glob("cover.*")):
        if path.is_file():
            return path
    return None


def ensure_source_asset(book_path: Path, output_dir: Path) -> Path:
    """Copy the source EPUB into the output asset directory when needed."""
    destination = source_asset_file(output_dir)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists() or destination.stat().st_mtime < book_path.stat().st_mtime:
        shutil.copy2(book_path, destination)
    return destination


def relative_asset_path(output_dir: Path, asset_path: Path) -> str:
    """Return an output-dir-relative asset path for persisted artifacts."""
    return str(asset_path.relative_to(output_dir))


def chapter_markdown_file(output_dir: Path, chapter: StructureChapter) -> Path:
    """Stable markdown filepath for one chapter."""
    return output_dir / chapter_output_name(chapter)


def chapter_result_name(chapter: StructureChapter) -> str:
    """Stable JSON companion filename for one chapter."""
    return Path(chapter_output_name(chapter)).with_suffix(".json").name


def chapter_result_file(output_dir: Path, chapter: StructureChapter) -> Path:
    """Stable JSON companion filepath for one chapter."""
    return output_dir / chapter_result_name(chapter)


def segment_checkpoint_dir(output_dir: Path) -> Path:
    """Directory storing segment-level checkpoints."""
    return output_dir / "_checkpoints"


def segment_checkpoint_file(output_dir: Path, chapter: StructureChapter) -> Path:
    """Path to one chapter's segment checkpoint file."""
    return segment_checkpoint_dir(output_dir) / f"{chapter_output_name(chapter)}.segments.json"


def analysis_dir(output_dir: Path) -> Path:
    """Directory storing book-analysis intermediate artifacts."""
    return output_dir / "_analysis"


def book_analysis_file(output_dir: Path) -> Path:
    """Path to book-level analysis markdown report."""
    return output_dir / "book_analysis.md"


def book_manifest_file(output_dir: Path) -> Path:
    """Path to the frontend-facing book manifest JSON."""
    return output_dir / "book_manifest.json"


def run_state_file(output_dir: Path) -> Path:
    """Path to the frontend-facing sequential run state JSON."""
    return output_dir / "run_state.json"


def activity_file(output_dir: Path) -> Path:
    """Path to the frontend-facing sequential activity stream JSONL."""
    return output_dir / "activity.jsonl"


def analysis_plan_file(output_dir: Path) -> Path:
    """Path to persisted analysis planning payload."""
    return analysis_dir(output_dir) / "analysis_plan.json"


def segment_skim_cards_file(output_dir: Path) -> Path:
    """Path to segment skim cards JSONL."""
    return analysis_dir(output_dir) / "segment_skim_cards.jsonl"


def deep_targets_file(output_dir: Path) -> Path:
    """Path to selected deep targets JSON."""
    return analysis_dir(output_dir) / "deep_targets.json"


def deep_dossiers_file(output_dir: Path) -> Path:
    """Path to deep-read dossier records JSON."""
    return analysis_dir(output_dir) / "deep_dossiers.json"


def evidence_checks_file(output_dir: Path) -> Path:
    """Path to evidence-check records JSONL."""
    return analysis_dir(output_dir) / "evidence_checks.jsonl"


def analysis_trace_file(output_dir: Path) -> Path:
    """Path to book-analysis execution traces JSONL."""
    return analysis_dir(output_dir) / "analysis_trace.jsonl"


def save_structure(path: Path, structure: BookStructure) -> None:
    """Write structure.json with UTF-8 JSON formatting."""
    path.write_text(
        json.dumps(structure, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_structure(path: Path) -> BookStructure:
    """Load structure.json from disk."""
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: object) -> None:
    """Write a generic JSON payload in UTF-8."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_json(path: Path) -> dict:
    """Load JSON dictionary payload from disk."""
    return json.loads(path.read_text(encoding="utf-8"))


def append_jsonl(path: Path, payload: object) -> None:
    """Append one JSON line payload."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False))
        file.write("\n")

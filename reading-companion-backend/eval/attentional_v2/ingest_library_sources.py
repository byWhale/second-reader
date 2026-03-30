"""Ingest manually provided source books into the managed local source library.

Phase 1 of the dataset-platform work is a managed source intake layer:
- operator drops books into `state/library_inbox/`
- this CLI copies them into canonical paths under `state/library_sources/`
- lightweight source records are persisted in `state/dataset_build/source_catalog.json`
- per-run summaries are written under `state/dataset_build/source_intake_runs/`

This intentionally stops before parse/screen/build. Later dataset-platform stages
should consume the catalog and drive screening, target-case mining, review, and
iterative rebuild from there.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

from src.iterator_reader.language import detect_book_language
from src.iterator_reader.parse import extract_plain_text
from src.parsers import parse_ebook


ROOT = Path(__file__).resolve().parents[2]
STATE_ROOT = ROOT / "state"
LIBRARY_INBOX_ROOT = STATE_ROOT / "library_inbox"
LIBRARY_SOURCE_ROOT = STATE_ROOT / "library_sources"
DATASET_BUILD_ROOT = STATE_ROOT / "dataset_build"
SOURCE_CATALOG_PATH = DATASET_BUILD_ROOT / "source_catalog.json"
SOURCE_CATALOG_MD_PATH = DATASET_BUILD_ROOT / "source_catalog.md"
SOURCE_INTAKE_RUNS_ROOT = DATASET_BUILD_ROOT / "source_intake_runs"
SOURCE_BOOK_MANIFEST_ROOT = ROOT / "eval" / "manifests" / "source_books"

LANGUAGE_CHOICES = ("en", "zh")
VISIBILITY_CHOICES = ("public", "private")
SUPPORTED_SOURCE_SUFFIXES = {".epub"}
SOURCE_METADATA_SUFFIX = ".source.json"
CATALOG_VERSION = 1
BOOTSTRAP_MANIFEST_METADATA_SOURCE = "bootstrap_manifest"
BOOTSTRAP_SCAN_METADATA_SOURCE = "bootstrap_scan"


@dataclass(frozen=True)
class SourceIntakePaths:
    root: Path
    state_root: Path
    manifest_source_books_root: Path
    library_inbox_root: Path
    library_source_root: Path
    dataset_build_root: Path
    source_catalog_path: Path
    source_catalog_md_path: Path
    source_intake_runs_root: Path

    @classmethod
    def from_root(cls, root: Path) -> "SourceIntakePaths":
        resolved = root.expanduser().resolve()
        state_root = resolved / "state"
        dataset_build_root = state_root / "dataset_build"
        return cls(
            root=resolved,
            state_root=state_root,
            manifest_source_books_root=resolved / "eval" / "manifests" / "source_books",
            library_inbox_root=state_root / "library_inbox",
            library_source_root=state_root / "library_sources",
            dataset_build_root=dataset_build_root,
            source_catalog_path=dataset_build_root / "source_catalog.json",
            source_catalog_md_path=dataset_build_root / "source_catalog.md",
            source_intake_runs_root=dataset_build_root / "source_intake_runs",
        )


@dataclass(frozen=True)
class InboxSource:
    source_path: Path
    relative_path: Path
    batch_id: str
    metadata_path: Path | None


@dataclass(frozen=True)
class LibrarySourceFile:
    source_path: Path
    relative_path: Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def default_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object JSON at {path}")
    return payload


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = re.split(r"[|,]", value)
    elif isinstance(value, list):
        items = [str(item) for item in value]
    else:
        items = [str(value)]
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in items:
        normalized = _clean_text(item)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(normalized)
    return cleaned


def _metadata_path_for(source_path: Path) -> Path:
    return source_path.with_suffix(SOURCE_METADATA_SUFFIX)


def _sanitize_filename_stem(value: str) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", _clean_text(value), flags=re.UNICODE)
    cleaned = re.sub(r"_+", "_", cleaned).strip("._-")
    return cleaned.casefold()


def _sanitize_identifier(value: str) -> str:
    cleaned = _sanitize_filename_stem(value)
    cleaned = cleaned.replace("-", "_")
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned


def _guess_title_from_filename(path: Path) -> str:
    stem = path.stem
    guessed = stem.replace("_", " ").replace("-", " ")
    guessed = re.sub(r"\s+", " ", guessed).strip()
    return guessed or stem


def _batch_id_for(relative_path: Path) -> str:
    if len(relative_path.parts) <= 1:
        return ""
    return "/".join(relative_path.parts[:-1])


def _existing_record_by_sha(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for record in records:
        sha = _clean_text(record.get("sha256"))
        if sha:
            indexed[sha] = record
    return indexed


def _relative_catalog_path(path: Path, *, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))


def _version_hint(stem: str) -> int:
    match = re.search(r"_v(\d+)\b", stem)
    if not match:
        return 0
    return int(match.group(1))


def _metadata_richness(record: dict[str, Any]) -> int:
    score = 0
    for field in ("source_id", "title", "author", "language", "relative_local_path", "origin"):
        if _clean_text(record.get(field)):
            score += 1
    for field in ("type_tags", "role_tags", "notes", "candidate_chapters"):
        if list(record.get(field) or []):
            score += 1
    if record.get("selection_priority") not in (None, "", 9999):
        score += 1
    if record.get("source_url"):
        score += 1
    if _clean_text(record.get("screening_status")):
        score += 1
    return score


def _preferred_manifest_record(current: dict[str, Any] | None, candidate: dict[str, Any]) -> dict[str, Any]:
    if current is None:
        return dict(candidate)
    if _metadata_richness(candidate) > _metadata_richness(current):
        return dict(candidate)
    return current


def _catalog_sort_key(record: dict[str, Any]) -> tuple[str, str, str]:
    return (
        _clean_text(record.get("language")),
        _clean_text(record.get("source_id")),
        _clean_text(record.get("visibility")),
    )


def load_catalog(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "version": CATALOG_VERSION,
            "updated_at": "",
            "record_count": 0,
            "records": [],
        }
    payload = load_json(path)
    payload.setdefault("version", CATALOG_VERSION)
    payload.setdefault("updated_at", "")
    payload.setdefault("record_count", len(payload.get("records", [])))
    payload.setdefault("records", [])
    return payload


def _read_source_metadata(source: InboxSource) -> tuple[dict[str, Any], str]:
    if source.metadata_path is None or not source.metadata_path.exists():
        return ({}, "inferred")
    payload = load_json(source.metadata_path)
    return (payload, "sidecar")


def _normalize_language(value: Any) -> str:
    lowered = _clean_text(value).lower()
    if lowered.startswith("zh"):
        return "zh"
    if lowered.startswith("en"):
        return "en"
    raise ValueError(f"Unsupported language override for {value!r}; expected en or zh")


def _normalize_visibility(value: Any) -> str:
    lowered = _clean_text(value).lower()
    if not lowered:
        return "private"
    if lowered in VISIBILITY_CHOICES:
        return lowered
    raise ValueError(f"Unsupported visibility override for {value!r}; expected public or private")


def _sample_source_text(path: Path) -> str:
    if path.suffix.lower() == ".epub":
        try:
            chapters = parse_ebook(str(path))
        except Exception:
            return ""
        samples: list[str] = []
        total_chars = 0
        for chapter in chapters[:3]:
            text = extract_plain_text(str(chapter.get("content", "")))
            if not text:
                continue
            clipped = text[:600]
            samples.append(clipped)
            total_chars += len(clipped)
            if total_chars >= 1500:
                break
        return "\n".join(samples)
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:1500]
    except Exception:
        return ""


def _resolve_source_language(source_path: Path, metadata: dict[str, Any]) -> str:
    override = metadata.get("language")
    if _clean_text(override):
        return _normalize_language(override)
    detected = detect_book_language(source_path, sample_text=_sample_source_text(source_path))
    if detected in LANGUAGE_CHOICES:
        return detected
    raise ValueError(f"Could not resolve supported language for {source_path}")


def _normalize_metadata(source: InboxSource) -> dict[str, Any]:
    payload, metadata_source = _read_source_metadata(source)
    title = _clean_text(payload.get("title")) or _guess_title_from_filename(source.source_path)
    canonical_filename = _clean_text(payload.get("canonical_filename"))
    preferred_stem = _sanitize_filename_stem(Path(canonical_filename).stem if canonical_filename else title)
    if not preferred_stem:
        preferred_stem = _sanitize_filename_stem(source.source_path.stem) or f"source_{sha256_file(source.source_path)[:8]}"
    preferred_suffix = Path(canonical_filename).suffix.lower() if canonical_filename else source.source_path.suffix.lower()
    language = _resolve_source_language(source.source_path, payload)
    visibility = _normalize_visibility(payload.get("visibility"))
    source_id = _clean_text(payload.get("source_id"))
    if not source_id:
        source_id = f"{_sanitize_identifier(preferred_stem) or 'source'}_{language}"
    return {
        "source_id": source_id,
        "title": title,
        "author": _clean_text(payload.get("author")),
        "language": language,
        "visibility": visibility,
        "canonical_stem": preferred_stem,
        "canonical_suffix": preferred_suffix or source.source_path.suffix.lower(),
        "type_tags": _normalize_list(payload.get("type_tags")),
        "role_tags": _normalize_list(payload.get("role_tags")),
        "notes": _normalize_list(payload.get("notes")),
        "selection_priority": int(payload.get("selection_priority", 9999) or 9999),
        "origin": _clean_text(payload.get("origin")) or "manual_library_inbox",
        "metadata_source": metadata_source,
    }


def discover_inbox_sources(
    paths: SourceIntakePaths,
    *,
    limit: int = 0,
) -> tuple[list[InboxSource], list[dict[str, Any]]]:
    discovered: list[InboxSource] = []
    skipped: list[dict[str, Any]] = []
    if not paths.library_inbox_root.exists():
        return discovered, skipped

    for candidate in sorted(path for path in paths.library_inbox_root.rglob("*") if path.is_file()):
        if candidate.name.endswith(SOURCE_METADATA_SUFFIX):
            continue
        relative_path = candidate.relative_to(paths.library_inbox_root)
        if candidate.suffix.lower() not in SUPPORTED_SOURCE_SUFFIXES:
            skipped.append(
                {
                    "status": "skipped_unsupported_extension",
                    "source_path": str(candidate),
                    "reason": f"supported extensions: {sorted(SUPPORTED_SOURCE_SUFFIXES)}",
                }
            )
            continue
        metadata_path = _metadata_path_for(candidate)
        discovered.append(
            InboxSource(
                source_path=candidate,
                relative_path=relative_path,
                batch_id=_batch_id_for(relative_path),
                metadata_path=metadata_path if metadata_path.exists() else None,
            )
        )
        if limit > 0 and len(discovered) >= limit:
            break
    return discovered, skipped


def discover_library_source_files(
    paths: SourceIntakePaths,
    *,
    limit: int = 0,
) -> tuple[list[LibrarySourceFile], list[dict[str, Any]]]:
    discovered: list[LibrarySourceFile] = []
    skipped: list[dict[str, Any]] = []
    if not paths.library_source_root.exists():
        return discovered, skipped

    for candidate in sorted(path for path in paths.library_source_root.rglob("*") if path.is_file()):
        suffix = candidate.suffix.lower()
        if suffix not in SUPPORTED_SOURCE_SUFFIXES:
            continue
        if candidate.name.endswith(".normalized.epub"):
            skipped.append(
                {
                    "status": "skipped_normalized_epub",
                    "source_path": str(candidate),
                    "reason": "derived normalized EPUBs are not treated as canonical managed sources",
                }
            )
            continue
        relative_path = candidate.relative_to(paths.library_source_root)
        discovered.append(
            LibrarySourceFile(
                source_path=candidate,
                relative_path=relative_path,
            )
        )
        if limit > 0 and len(discovered) >= limit:
            break
    return discovered, skipped


def _destination_relative_path(
    *,
    language: str,
    visibility: str,
    canonical_stem: str,
    suffix: str,
) -> Path:
    # Visibility is now compatibility metadata only; canonical managed copies
    # live in one language-rooted source tree regardless of distribution status.
    filename = f"{canonical_stem}{suffix}"
    return Path(language) / filename


def _resolve_destination_path(paths: SourceIntakePaths, relative_path: Path, source_sha: str) -> Path:
    destination = paths.library_source_root / relative_path
    if not destination.exists():
        return destination
    if destination.is_file() and sha256_file(destination) == source_sha:
        return destination
    suffix = destination.suffix
    stem = destination.stem
    candidate = destination.with_name(f"{stem}_{source_sha[:8]}{suffix}")
    if not candidate.exists():
        return candidate
    if candidate.is_file() and sha256_file(candidate) == source_sha:
        return candidate
    raise FileExistsError(f"Could not allocate canonical destination for {relative_path}")


def load_manifest_source_books(paths: SourceIntakePaths) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_relative_path: dict[str, dict[str, Any]] = {}
    by_sha: dict[str, dict[str, Any]] = {}
    if not paths.manifest_source_books_root.exists():
        return by_relative_path, by_sha

    for manifest_path in sorted(paths.manifest_source_books_root.glob("*.json")):
        payload = load_json(manifest_path)
        for record in payload.get("books") or []:
            if not isinstance(record, dict):
                continue
            relative_local_path = _clean_text(record.get("relative_local_path"))
            if relative_local_path:
                by_relative_path[relative_local_path] = _preferred_manifest_record(
                    by_relative_path.get(relative_local_path),
                    record,
                )
            sha = _clean_text(record.get("sha256"))
            if sha:
                by_sha[sha] = _preferred_manifest_record(by_sha.get(sha), record)
    return by_relative_path, by_sha


def _library_source_bootstrap_visibility(relative_path: str, manifest_record: dict[str, Any]) -> str:
    explicit = _clean_text(manifest_record.get("visibility")).lower()
    if explicit in VISIBILITY_CHOICES:
        return explicit
    if "/private/" in relative_path or relative_path.startswith("state/library_sources/private/"):
        return "private"
    source_id = _clean_text(manifest_record.get("source_id")).lower()
    origin = _clean_text(manifest_record.get("origin")).lower()
    if "_public_" in source_id or origin.startswith("public") or manifest_record.get("source_url"):
        return "public"
    return "private"


def _bootstrap_source_record(
    source: LibrarySourceFile,
    *,
    root: Path,
    manifest_record: dict[str, Any],
    generated_at: str,
    source_sha: str,
) -> dict[str, Any]:
    relative_local_path = str(source.source_path.relative_to(root))
    language = _clean_text(manifest_record.get("language"))
    if language not in LANGUAGE_CHOICES:
        language = _normalize_language(source.relative_path.parts[0])
    source_id = _clean_text(manifest_record.get("source_id"))
    if not source_id:
        source_id = f"{_sanitize_identifier(source.source_path.stem) or 'source'}_{language}"
    acquisition_batch_id = _clean_text(
        manifest_record.get("acquisition_batch_id")
        or ((manifest_record.get("acquisition") or {}).get("acquisition_batch_id"))
    )
    relative_local_path_clean = _clean_text(relative_local_path)
    record = {
        "source_id": source_id,
        "title": _clean_text(manifest_record.get("title")) or _guess_title_from_filename(source.source_path),
        "author": _clean_text(manifest_record.get("author")),
        "language": language,
        "visibility": _library_source_bootstrap_visibility(relative_local_path_clean, manifest_record),
        "origin": _clean_text(manifest_record.get("origin")) or "bootstrap_existing_library",
        "relative_local_path": relative_local_path_clean,
        "original_filename": source.source_path.name,
        "inbox_relative_paths": [],
        "ingest_batch_ids": [acquisition_batch_id] if acquisition_batch_id else [],
        "metadata_source": "manifest_bootstrap" if manifest_record else "library_sources_bootstrap",
        "selection_priority": int(manifest_record.get("selection_priority", 9999) or 9999),
        "type_tags": _normalize_list(manifest_record.get("type_tags")),
        "role_tags": _normalize_list(manifest_record.get("role_tags")),
        "notes": _normalize_list(manifest_record.get("notes")),
        "sha256": source_sha,
        "file_size": source.source_path.stat().st_size,
        "file_extension": source.source_path.suffix.lower(),
        "first_seen_at": generated_at,
        "last_seen_at": generated_at,
        "seen_count": 1,
        "parse_status": "not_started",
        "screening_status": "not_started",
        "packaging_status": "not_started",
        "acquisition": {
            "kind": "library_sources_bootstrap",
            "input_filename": source.source_path.name,
            "library_source_relative_path": relative_local_path_clean,
            "ingest_batch_id": acquisition_batch_id,
        },
    }
    if manifest_record.get("source_url"):
        record["source_url"] = manifest_record.get("source_url")
    return record


def _merge_record(existing: dict[str, Any], candidate: dict[str, Any], *, seen_at: str, inbox_relative_path: str, batch_id: str) -> bool:
    updated = False
    existing_metadata_source = _clean_text(existing.get("metadata_source"))
    candidate_metadata_source = _clean_text(candidate.get("metadata_source"))
    for field in ("title", "author"):
        candidate_value = _clean_text(candidate.get(field))
        if not candidate_value:
            continue
        if candidate_metadata_source == "sidecar" and _clean_text(existing.get(field)) != candidate_value:
            existing[field] = candidate[field]
            updated = True
            continue
        if not _clean_text(existing.get(field)):
            existing[field] = candidate[field]
            updated = True
            continue
    if candidate_metadata_source == "sidecar" and existing_metadata_source != "sidecar":
        existing["metadata_source"] = "sidecar"
        updated = True
    if candidate.get("source_id") and _clean_text(existing.get("source_id")) != _clean_text(candidate.get("source_id")):
        if not _clean_text(existing.get("source_id")):
            existing["source_id"] = candidate["source_id"]
            updated = True
    for field in ("type_tags", "role_tags", "notes"):
        merged = list(existing.get(field) or [])
        for item in candidate.get(field) or []:
            if item not in merged:
                merged.append(item)
        if merged != list(existing.get(field) or []):
            existing[field] = merged
            updated = True
    existing_paths = list(existing.get("inbox_relative_paths") or [])
    if inbox_relative_path and inbox_relative_path not in existing_paths:
        existing_paths.append(inbox_relative_path)
        existing["inbox_relative_paths"] = existing_paths
        updated = True
    batch_ids = list(existing.get("ingest_batch_ids") or [])
    if batch_id and batch_id not in batch_ids:
        batch_ids.append(batch_id)
        existing["ingest_batch_ids"] = batch_ids
        updated = True
    seen_count = int(existing.get("seen_count", 1) or 1) + 1
    existing["seen_count"] = seen_count
    existing["last_seen_at"] = seen_at
    return updated


def render_catalog_markdown(catalog: dict[str, Any]) -> str:
    records = list(catalog.get("records") or [])
    language_counts = Counter(_clean_text(record.get("language")) or "unknown" for record in records)
    lines = [
        "# Source Catalog",
        "",
        f"- updated_at: `{catalog.get('updated_at', '')}`",
        f"- record_count: `{len(records)}`",
        f"- language_counts: `{json.dumps(dict(sorted(language_counts.items())), ensure_ascii=False)}`",
        "- visibility is retained only as compatibility metadata and is not a primary intake or build axis.",
        "",
        "## Records",
        "",
    ]
    for record in sorted(records, key=_catalog_sort_key):
        lines.extend(
            [
                f"- `{record.get('source_id', '')}`",
                f"  - title: `{record.get('title', '')}`",
                f"  - author: `{record.get('author', '')}`",
                f"  - language: `{record.get('language', '')}`",
                f"  - relative_local_path: `{record.get('relative_local_path', '')}`",
                f"  - original_filename: `{record.get('original_filename', '')}`",
                f"  - sha256: `{record.get('sha256', '')}`",
                f"  - parse_status: `{record.get('parse_status', '')}`",
                f"  - screening_status: `{record.get('screening_status', '')}`",
                f"  - packaging_status: `{record.get('packaging_status', '')}`",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def render_run_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        f"# Source Intake Run `{summary.get('run_id', '')}`",
        "",
        f"- mode: `{summary.get('mode', 'inbox_intake')}`",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- candidate_count: `{summary.get('candidate_count', 0)}`",
        f"- ingested_count: `{summary.get('ingested_count', 0)}`",
        f"- bootstrapped_count: `{summary.get('bootstrapped_count', 0)}`",
        f"- existing_count: `{summary.get('existing_count', 0)}`",
        f"- skipped_count: `{summary.get('skipped_count', 0)}`",
        "",
        "## Results",
        "",
    ]
    for result in summary.get("results", []):
        lines.append(
            f"- `{result.get('status', '')}` `{result.get('source_id', result.get('source_path', ''))}`"
        )
    return "\n".join(lines).rstrip() + "\n"


def _manifest_book_records(manifest_path: Path) -> list[dict[str, Any]]:
    payload = load_json(manifest_path)
    books = payload.get("books")
    if not isinstance(books, list):
        return []
    return [dict(record) for record in books if isinstance(record, dict)]


def _bootstrap_manifest_root(paths: SourceIntakePaths) -> Path:
    return paths.root / "eval" / "manifests" / "source_books"


def _scan_library_source_files(paths: SourceIntakePaths) -> tuple[list[Path], dict[str, list[Path]], dict[str, list[Path]]]:
    files: list[Path] = []
    by_sha: dict[str, list[Path]] = defaultdict(list)
    by_name: dict[str, list[Path]] = defaultdict(list)
    if not paths.library_source_root.exists():
        return files, by_sha, by_name
    for candidate in sorted(path for path in paths.library_source_root.rglob("*") if path.is_file()):
        if candidate.suffix.lower() not in SUPPORTED_SOURCE_SUFFIXES:
            continue
        files.append(candidate)
        by_name[candidate.name.casefold()].append(candidate)
        by_sha[sha256_file(candidate)].append(candidate)
    return files, by_sha, by_name


def _compat_relative_library_paths(relative_text: str) -> list[Path]:
    cleaned = _clean_text(relative_text)
    if not cleaned.startswith("state/library_sources/"):
        return []
    path = Path(cleaned)
    candidates = [path]
    parts = list(path.parts)
    if len(parts) >= 5 and parts[:2] == ["state", "library_sources"] and parts[3] == "private":
        compat = Path(*(parts[:3] + parts[4:]))
        if compat not in candidates:
            candidates.append(compat)
    return candidates


def _resolve_manifest_library_source_path(
    paths: SourceIntakePaths,
    record: dict[str, Any],
    *,
    files_by_sha: dict[str, list[Path]],
    files_by_name: dict[str, list[Path]],
) -> Path | None:
    relative_candidates: list[Path] = []
    for field in ("relative_local_path", "normalized_from_relative_local_path"):
        for candidate in _compat_relative_library_paths(record.get(field)):
            if candidate not in relative_candidates:
                relative_candidates.append(candidate)

    for relative_candidate in relative_candidates:
        candidate = paths.root / relative_candidate
        if candidate.exists():
            return candidate

    record_sha = _clean_text(record.get("sha256"))
    if record_sha:
        sha_matches = list(files_by_sha.get(record_sha, []))
        if len(sha_matches) == 1:
            return sha_matches[0]
        if len(sha_matches) > 1:
            language = _clean_text(record.get("language"))
            language_matches = [
                match for match in sha_matches if match.parent.name == language
            ]
            if len(language_matches) == 1:
                return language_matches[0]

    for relative_candidate in relative_candidates:
        basename_matches = list(files_by_name.get(relative_candidate.name.casefold(), []))
        if len(basename_matches) == 1:
            return basename_matches[0]
        language = _clean_text(record.get("language"))
        language_matches = [
            match for match in basename_matches if match.parent.name == language
        ]
        if len(language_matches) == 1:
            return language_matches[0]
    return None


def _manifest_bootstrap_visibility(record: dict[str, Any], *, manifest_path: Path) -> str:
    explicit = _clean_text(record.get("visibility"))
    if explicit:
        return _normalize_visibility(explicit)
    source_id = _clean_text(record.get("source_id")).lower()
    relative_text = _clean_text(record.get("relative_local_path")).lower()
    manifest_name = manifest_path.stem.lower()
    if any(token in source_id for token in ("_public_", "public_")):
        return "public"
    if any(token in relative_text for token in ("/public/", "_public_")):
        return "public"
    if "public" in manifest_name:
        return "public"
    return "private"


def _manifest_bootstrap_score(record: dict[str, Any], *, manifest_path: Path) -> int:
    score = 0
    score += _version_hint(manifest_path.stem) * 10
    if _clean_text(record.get("normalized_from_relative_local_path")):
        score += 20
    if _clean_text(record.get("screening_status")).startswith("screened"):
        score += 15
    if isinstance(record.get("candidate_chapters"), list) and record.get("candidate_chapters"):
        score += 15
    if _clean_text(record.get("author")):
        score += 5
    if _normalize_list(record.get("type_tags")):
        score += 5
    if _normalize_list(record.get("role_tags")):
        score += 5
    if _clean_text(record.get("relative_local_path")).startswith("state/library_sources/"):
        score += 10
    return score


def _bootstrap_record_from_manifest(
    paths: SourceIntakePaths,
    record: dict[str, Any],
    *,
    manifest_path: Path,
    resolved_path: Path,
    generated_at: str,
) -> dict[str, Any]:
    acquisition = record.get("acquisition") if isinstance(record.get("acquisition"), dict) else {}
    acquisition_batch_id = _clean_text(
        acquisition.get("acquisition_batch_id") or record.get("acquisition_batch_id")
    )
    screening_status = _clean_text(record.get("screening_status")) or "not_started"
    return {
        "source_id": _clean_text(record.get("source_id")),
        "title": _clean_text(record.get("title")) or _guess_title_from_filename(resolved_path),
        "author": _clean_text(record.get("author")),
        "language": _normalize_language(record.get("language")),
        "visibility": _manifest_bootstrap_visibility(record, manifest_path=manifest_path),
        "origin": _clean_text(record.get("origin")) or "manifest_catalog_bootstrap",
        "relative_local_path": _relative_catalog_path(resolved_path, root=paths.root),
        "original_filename": _clean_text(acquisition.get("input_filename")) or resolved_path.name,
        "inbox_relative_paths": [],
        "ingest_batch_ids": [acquisition_batch_id] if acquisition_batch_id else [],
        "metadata_source": BOOTSTRAP_MANIFEST_METADATA_SOURCE,
        "selection_priority": int(record.get("selection_priority", 9999) or 9999),
        "type_tags": _normalize_list(record.get("type_tags")),
        "role_tags": _normalize_list(record.get("role_tags")),
        "notes": _normalize_list(record.get("notes")),
        "sha256": sha256_file(resolved_path),
        "file_size": resolved_path.stat().st_size,
        "file_extension": resolved_path.suffix.lower(),
        "first_seen_at": generated_at,
        "last_seen_at": generated_at,
        "seen_count": 1,
        "parse_status": "manifest_backfilled",
        "screening_status": screening_status,
        "packaging_status": "not_started",
        "acquisition": {
            "kind": "manifest_source_catalog_bootstrap",
            "input_filename": _clean_text(acquisition.get("input_filename")) or resolved_path.name,
            "ingest_batch_id": acquisition_batch_id,
            "source_manifest_path": _relative_catalog_path(manifest_path, root=paths.root),
        },
    }


def _bootstrap_record_from_scan(
    paths: SourceIntakePaths,
    source_path: Path,
    *,
    generated_at: str,
) -> dict[str, Any]:
    language = _normalize_language(source_path.parent.name)
    stem = _sanitize_filename_stem(source_path.stem) or "source"
    visibility = "public" if "public" in source_path.stem.casefold() else "private"
    return {
        "source_id": f"{_sanitize_identifier(stem) or 'source'}_{language}",
        "title": _guess_title_from_filename(source_path),
        "author": "",
        "language": language,
        "visibility": visibility,
        "origin": "library_source_catalog_bootstrap",
        "relative_local_path": _relative_catalog_path(source_path, root=paths.root),
        "original_filename": source_path.name,
        "inbox_relative_paths": [],
        "ingest_batch_ids": [],
        "metadata_source": BOOTSTRAP_SCAN_METADATA_SOURCE,
        "selection_priority": 9999,
        "type_tags": [],
        "role_tags": [],
        "notes": ["Bootstrapped from existing managed library sources without a manifest-backed metadata record."],
        "sha256": sha256_file(source_path),
        "file_size": source_path.stat().st_size,
        "file_extension": source_path.suffix.lower(),
        "first_seen_at": generated_at,
        "last_seen_at": generated_at,
        "seen_count": 1,
        "parse_status": "bootstrap_scan",
        "screening_status": "not_started",
        "packaging_status": "not_started",
        "acquisition": {
            "kind": "library_source_scan_bootstrap",
            "input_filename": source_path.name,
        },
    }


def run_source_catalog_bootstrap(
    paths: SourceIntakePaths,
    *,
    language: str | None = None,
    visibility: str | None = None,
    limit: int = 0,
    dry_run: bool = False,
    run_id: str | None = None,
    include_unmanifested_library_files: bool = False,
    replace_existing_catalog: bool = False,
) -> dict[str, Any]:
    if paths.source_catalog_path.exists() and not replace_existing_catalog:
        raise FileExistsError(
            f"Source catalog already exists at {paths.source_catalog_path}. "
            "Use replace_existing_catalog only for explicit recovery/bootstrap."
        )
    if not paths.library_source_root.exists():
        raise FileNotFoundError(f"Managed library source root not found: {paths.library_source_root}")

    generated_at = utc_now()
    run_id = run_id or default_run_id()
    files, files_by_sha, files_by_name = _scan_library_source_files(paths)
    selected_by_source_id: dict[str, tuple[int, dict[str, Any]]] = {}
    results: list[dict[str, Any]] = []
    used_relative_paths: set[str] = set()
    candidate_count = 0
    bootstrapped_count = 0

    manifest_root = _bootstrap_manifest_root(paths)
    manifest_paths = sorted(manifest_root.glob("*.json")) if manifest_root.exists() else []
    for manifest_path in manifest_paths:
        for manifest_record in _manifest_book_records(manifest_path):
            source_id = _clean_text(manifest_record.get("source_id"))
            if not source_id:
                continue
            resolved_path = _resolve_manifest_library_source_path(
                paths,
                manifest_record,
                files_by_sha=files_by_sha,
                files_by_name=files_by_name,
            )
            if resolved_path is None:
                relative_hint = _clean_text(manifest_record.get("relative_local_path"))
                if relative_hint.startswith("state/library_sources/"):
                    results.append(
                        {
                            "status": "skipped_manifest_missing_file",
                            "source_id": source_id,
                            "manifest_path": _relative_catalog_path(manifest_path, root=paths.root),
                            "relative_local_path": relative_hint,
                        }
                    )
                continue
            candidate_record = _bootstrap_record_from_manifest(
                paths,
                manifest_record,
                manifest_path=manifest_path,
                resolved_path=resolved_path,
                generated_at=generated_at,
            )
            if language and candidate_record["language"] != language:
                continue
            if visibility and candidate_record["visibility"] != visibility:
                continue
            score = _manifest_bootstrap_score(manifest_record, manifest_path=manifest_path)
            existing = selected_by_source_id.get(source_id)
            if existing is not None and existing[0] >= score:
                continue
            selected_by_source_id[source_id] = (score, candidate_record)

    manifest_records = [
        record for _score, record in selected_by_source_id.values()
    ]
    manifest_records.sort(key=_catalog_sort_key)
    if limit > 0:
        manifest_records = manifest_records[:limit]

    for record in manifest_records:
        candidate_count += 1
        bootstrapped_count += 1
        used_relative_paths.add(record["relative_local_path"])
        results.append(
            {
                "status": "bootstrapped_from_manifest",
                "source_id": record["source_id"],
                "relative_local_path": record["relative_local_path"],
                "sha256": record["sha256"],
            }
        )

    if include_unmanifested_library_files and (limit <= 0 or candidate_count < limit):
        existing_source_ids = {record["source_id"] for record in manifest_records}
        for source_path in files:
            relative_local_path = _relative_catalog_path(source_path, root=paths.root)
            if relative_local_path in used_relative_paths:
                continue
            inferred_record = _bootstrap_record_from_scan(paths, source_path, generated_at=generated_at)
            if inferred_record["source_id"] in existing_source_ids:
                inferred_record["source_id"] = (
                    f"{inferred_record['source_id']}__{inferred_record['sha256'][:8]}"
                )
            if language and inferred_record["language"] != language:
                continue
            if visibility and inferred_record["visibility"] != visibility:
                continue
            if limit > 0 and candidate_count >= limit:
                break
            manifest_records.append(inferred_record)
            existing_source_ids.add(inferred_record["source_id"])
            candidate_count += 1
            bootstrapped_count += 1
            results.append(
                {
                    "status": "bootstrapped_unmanifested_file",
                    "source_id": inferred_record["source_id"],
                    "relative_local_path": inferred_record["relative_local_path"],
                    "sha256": inferred_record["sha256"],
                }
            )

    results.sort(
        key=lambda item: (
            _clean_text(item.get("status")),
            _clean_text(item.get("source_id", item.get("relative_local_path"))),
        )
    )
    summary = {
        "run_id": run_id,
        "mode": "bootstrap_existing_library",
        "generated_at": generated_at,
        "dry_run": dry_run,
        "candidate_count": candidate_count,
        "ingested_count": 0,
        "bootstrapped_count": bootstrapped_count,
        "existing_count": 0,
        "skipped_count": sum(1 for item in results if str(item.get("status", "")).startswith("skipped_")),
        "results": results,
    }
    if dry_run:
        return summary

    catalog = {
        "version": CATALOG_VERSION,
        "updated_at": generated_at,
        "record_count": len(manifest_records),
        "records": sorted(manifest_records, key=_catalog_sort_key),
    }
    write_json(paths.source_catalog_path, catalog)
    write_markdown(paths.source_catalog_md_path, render_catalog_markdown(catalog))
    write_json(paths.source_intake_runs_root / f"{run_id}.json", summary)
    write_markdown(paths.source_intake_runs_root / f"{run_id}.md", render_run_summary_markdown(summary))
    return summary


def run_source_intake(
    paths: SourceIntakePaths,
    *,
    language: str | None = None,
    visibility: str | None = None,
    limit: int = 0,
    dry_run: bool = False,
    run_id: str | None = None,
) -> dict[str, Any]:
    catalog = load_catalog(paths.source_catalog_path)
    records = list(catalog.get("records") or [])
    by_sha = _existing_record_by_sha(records)

    discovered, skipped = discover_inbox_sources(paths)
    generated_at = utc_now()
    run_id = run_id or default_run_id()

    results: list[dict[str, Any]] = []
    ingested_count = 0
    existing_count = 0
    candidate_count = 0

    for source in discovered:
        metadata = _normalize_metadata(source)
        resolved_language = str(metadata["language"])
        resolved_visibility = str(metadata["visibility"])
        if language and resolved_language != language:
            continue
        if visibility and resolved_visibility != visibility:
            continue
        if limit > 0 and candidate_count >= limit:
            break
        candidate_count += 1
        source_sha = sha256_file(source.source_path)
        inbox_relative_path = str(source.relative_path)
        existing = by_sha.get(source_sha)
        if existing is not None:
            _merge_record(
                existing,
                metadata,
                seen_at=generated_at,
                inbox_relative_path=inbox_relative_path,
                batch_id=source.batch_id,
            )
            results.append(
                {
                    "status": "already_cataloged",
                    "source_id": existing.get("source_id", ""),
                    "source_path": str(source.source_path),
                    "relative_local_path": existing.get("relative_local_path", ""),
                    "sha256": source_sha,
                }
            )
            existing_count += 1
            continue

        relative_destination = _destination_relative_path(
            language=resolved_language,
            visibility=resolved_visibility,
            canonical_stem=metadata["canonical_stem"],
            suffix=metadata["canonical_suffix"],
        )
        destination = _resolve_destination_path(paths, relative_destination, source_sha)
        relative_local_path = str(destination.relative_to(paths.root))

        record = {
            "source_id": metadata["source_id"],
            "title": metadata["title"],
            "author": metadata["author"],
            "language": resolved_language,
            "visibility": resolved_visibility,
            "origin": metadata["origin"],
            "relative_local_path": relative_local_path,
            "original_filename": source.source_path.name,
            "inbox_relative_paths": [inbox_relative_path],
            "ingest_batch_ids": [source.batch_id] if source.batch_id else [],
            "metadata_source": metadata["metadata_source"],
            "selection_priority": metadata["selection_priority"],
            "type_tags": metadata["type_tags"],
            "role_tags": metadata["role_tags"],
            "notes": metadata["notes"],
            "sha256": source_sha,
            "file_size": source.source_path.stat().st_size,
            "file_extension": source.source_path.suffix.lower(),
            "first_seen_at": generated_at,
            "last_seen_at": generated_at,
            "seen_count": 1,
            "parse_status": "not_started",
            "screening_status": "not_started",
            "packaging_status": "not_started",
            "acquisition": {
                "kind": "manual_library_inbox",
                "input_filename": source.source_path.name,
                "inbox_relative_path": inbox_relative_path,
                "ingest_batch_id": source.batch_id,
            },
        }
        results.append(
            {
                "status": "planned" if dry_run else "ingested",
                "source_id": record["source_id"],
                "source_path": str(source.source_path),
                "relative_local_path": relative_local_path,
                "sha256": source_sha,
            }
        )
        if not dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source.source_path, destination)
            records.append(record)
            by_sha[source_sha] = record
        ingested_count += 1

    results.extend(skipped)
    results.sort(key=lambda item: (_clean_text(item.get("status")), _clean_text(item.get("source_id", item.get("source_path")))))

    summary = {
        "run_id": run_id,
        "generated_at": generated_at,
        "dry_run": dry_run,
        "candidate_count": candidate_count,
        "ingested_count": ingested_count,
        "existing_count": existing_count,
        "skipped_count": len(skipped),
        "results": results,
    }

    if dry_run:
        return summary

    records.sort(key=_catalog_sort_key)
    catalog["updated_at"] = generated_at
    catalog["record_count"] = len(records)
    catalog["records"] = records
    write_json(paths.source_catalog_path, catalog)
    write_markdown(paths.source_catalog_md_path, render_catalog_markdown(catalog))
    write_json(paths.source_intake_runs_root / f"{run_id}.json", summary)
    write_markdown(paths.source_intake_runs_root / f"{run_id}.md", render_run_summary_markdown(summary))
    return summary


def run_library_source_bootstrap(
    paths: SourceIntakePaths,
    *,
    language: str | None = None,
    visibility: str | None = None,
    limit: int = 0,
    dry_run: bool = False,
    run_id: str | None = None,
) -> dict[str, Any]:
    catalog = load_catalog(paths.source_catalog_path)
    records = list(catalog.get("records") or [])
    by_sha = _existing_record_by_sha(records)
    discovered, skipped = discover_library_source_files(paths)
    manifest_by_path, manifest_by_sha = load_manifest_source_books(paths)
    generated_at = utc_now()
    run_id = run_id or default_run_id()

    results: list[dict[str, Any]] = []
    ingested_count = 0
    existing_count = 0
    candidate_count = 0

    for source in discovered:
        source_sha = sha256_file(source.source_path)
        existing = by_sha.get(source_sha)
        relative_local_path = str(source.source_path.relative_to(paths.root))
        manifest_record = dict(
            manifest_by_path.get(relative_local_path)
            or manifest_by_sha.get(source_sha)
            or {}
        )
        record = _bootstrap_source_record(
            source,
            root=paths.root,
            manifest_record=manifest_record,
            generated_at=generated_at,
            source_sha=source_sha,
        )
        if language and str(record["language"]) != language:
            continue
        if visibility and str(record["visibility"]) != visibility:
            continue
        if limit > 0 and candidate_count >= limit:
            break
        candidate_count += 1

        if existing is not None:
            _merge_record(
                existing,
                record,
                seen_at=generated_at,
                inbox_relative_path="",
                batch_id="",
            )
            results.append(
                {
                    "status": "already_cataloged",
                    "source_id": existing.get("source_id", ""),
                    "source_path": str(source.source_path),
                    "relative_local_path": existing.get("relative_local_path", ""),
                    "sha256": source_sha,
                }
            )
            existing_count += 1
            continue

        results.append(
            {
                "status": "planned_bootstrap" if dry_run else "bootstrapped",
                "source_id": record["source_id"],
                "source_path": str(source.source_path),
                "relative_local_path": record["relative_local_path"],
                "sha256": source_sha,
            }
        )
        if not dry_run:
            records.append(record)
            by_sha[source_sha] = record
        ingested_count += 1

    results.extend(skipped)
    results.sort(key=lambda item: (_clean_text(item.get("status")), _clean_text(item.get("source_id", item.get("source_path")))))

    summary = {
        "run_id": run_id,
        "generated_at": generated_at,
        "mode": "bootstrap_library_sources",
        "dry_run": dry_run,
        "candidate_count": candidate_count,
        "ingested_count": ingested_count,
        "existing_count": existing_count,
        "skipped_count": len(skipped),
        "results": results,
    }

    if dry_run:
        return summary

    records.sort(key=_catalog_sort_key)
    catalog["updated_at"] = generated_at
    catalog["record_count"] = len(records)
    catalog["records"] = records
    write_json(paths.source_catalog_path, catalog)
    write_markdown(paths.source_catalog_md_path, render_catalog_markdown(catalog))
    write_json(paths.source_intake_runs_root / f"{run_id}.json", summary)
    write_markdown(paths.source_intake_runs_root / f"{run_id}.md", render_run_summary_markdown(summary))
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--language", choices=LANGUAGE_CHOICES)
    parser.add_argument(
        "--visibility",
        choices=VISIBILITY_CHOICES,
        help="Optional compatibility-only filter over resolved visibility metadata.",
    )
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-id")
    parser.add_argument(
        "--bootstrap-library-sources",
        action="store_true",
        help="Seed the source catalog from existing managed files under state/library_sources when inbox-driven intake is unavailable.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    paths = SourceIntakePaths.from_root(args.root)
    runner = run_library_source_bootstrap if args.bootstrap_library_sources else run_source_intake
    summary = runner(
        paths,
        language=args.language,
        visibility=args.visibility,
        limit=args.limit,
        dry_run=args.dry_run,
        run_id=args.run_id,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

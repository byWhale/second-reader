"""Validate the public-first large v2 attentional_v2 benchmark packages."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_ROOT = ROOT / "eval" / "manifests"
DATASET_ROOT = ROOT / "eval" / "datasets"

SOURCE_MANIFEST_ID = "attentional_v2_public_benchmark_pool_v2"
SPLIT_MANIFEST_ID = "attentional_v2_public_benchmark_pool_bilingual_v2_splits"

EXPECTED_COUNTS = {
    "chapter_corpora": {"en": 18, "zh": 18},
    "runtime_fixtures": {"en": 36, "zh": 36},
    "curated_excerpt_cases": {"en": 16, "zh": 16},
}

EXPECTED_CHAPTER_ROLE_COUNTS = {
    "expository": 4,
    "argumentative": 4,
    "narrative_reflective": 4,
    "reference_heavy": 4,
    "reserve": 2,
}

EXPECTED_CURATED_BUCKET_COUNTS = {
    "distinction_definition": 3,
    "tension_reversal": 3,
    "callback_bridge": 3,
    "anchored_reaction_selectivity": 3,
    "reconsolidation_later_reinterpretation": 3,
    "reserve": 1,
}

BOILERPLATE_MARKERS = [
    "project gutenberg",
    "license",
    ".mw-parser-output",
    "public domain",
    "www.gutenberg.org",
]


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def require(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def dataset_rows(family: str, dataset_id: str, primary_file: str) -> list[dict[str, object]]:
    manifest_path = DATASET_ROOT / family / dataset_id / "manifest.json"
    data_path = DATASET_ROOT / family / dataset_id / primary_file
    manifest = load_json(manifest_path)
    if not isinstance(manifest, dict):
        raise ValueError(f"Invalid dataset manifest: {manifest_path}")
    return load_jsonl(data_path)


def curated_bucket(case_id: str) -> str:
    if "__reserve__v2" in case_id:
        return "reserve"
    for bucket in EXPECTED_CURATED_BUCKET_COUNTS:
        if bucket != "reserve" and f"__{bucket}__v2" in case_id:
            return bucket
    return "unknown"


def validate() -> int:
    failures: list[str] = []

    source_manifest = load_json(MANIFEST_ROOT / "source_books" / f"{SOURCE_MANIFEST_ID}.json")
    if not isinstance(source_manifest, dict):
        raise ValueError("Invalid source manifest payload")
    books = list(source_manifest.get("books", []))
    promoted = [book for book in books if book.get("selected_for_public_benchmark")]
    promoted_by_lang = Counter(str(book.get("language")) for book in promoted)

    require(len(books) == 22, f"Expected combined public pool size 22, got {len(books)}", failures)
    require(len(promoted) == 12, f"Expected 12 promoted books, got {len(promoted)}", failures)
    require(promoted_by_lang == Counter({"en": 6, "zh": 6}), f"Expected promoted 6/6 by language, got {promoted_by_lang}", failures)

    for book in promoted:
        if book.get("corpus_lane") == "chapter_corpus_eligible":
            require(
                len(book.get("candidate_chapters", [])) >= 2,
                f"Promoted chapter-corpus book {book.get('source_id')} has <2 candidate chapters",
                failures,
            )

    split_manifest = load_json(MANIFEST_ROOT / "splits" / f"{SPLIT_MANIFEST_ID}.json")
    if not isinstance(split_manifest, dict):
        raise ValueError("Invalid split manifest payload")
    splits = split_manifest["splits"]

    for language in ("en", "zh"):
        chapter_rows = dataset_rows("chapter_corpora", f"attentional_v2_chapters_{language}_v2", "chapters.jsonl")
        runtime_rows = dataset_rows("runtime_fixtures", f"attentional_v2_runtime_{language}_v2", "fixtures.jsonl")
        curated_rows = dataset_rows("excerpt_cases", f"attentional_v2_excerpt_{language}_curated_v2", "cases.jsonl")

        require(
            len(chapter_rows) == EXPECTED_COUNTS["chapter_corpora"][language],
            f"{language} chapter corpus count mismatch: {len(chapter_rows)}",
            failures,
        )
        require(
            len(runtime_rows) == EXPECTED_COUNTS["runtime_fixtures"][language],
            f"{language} runtime fixture count mismatch: {len(runtime_rows)}",
            failures,
        )
        require(
            len(curated_rows) == EXPECTED_COUNTS["curated_excerpt_cases"][language],
            f"{language} curated excerpt count mismatch: {len(curated_rows)}",
            failures,
        )

        chapter_role_counts = Counter(str(row.get("selection_role")) for row in chapter_rows)
        require(
            chapter_role_counts == Counter(EXPECTED_CHAPTER_ROLE_COUNTS),
            f"{language} chapter role counts mismatch: {chapter_role_counts}",
            failures,
        )

        curated_counts = Counter(curated_bucket(str(row.get("case_id"))) for row in curated_rows)
        require(
            curated_counts == Counter(EXPECTED_CURATED_BUCKET_COUNTS),
            f"{language} curated bucket counts mismatch: {curated_counts}",
            failures,
        )

        for row in curated_rows:
            excerpt_text = str(row.get("excerpt_text", "")).lower()
            require(bool(excerpt_text.strip()), f"{language} curated case {row.get('case_id')} has empty excerpt text", failures)
            require(
                not any(marker in excerpt_text for marker in BOILERPLATE_MARKERS),
                f"{language} curated case {row.get('case_id')} still contains boilerplate markers",
                failures,
            )

        require(
            len(splits["chapter_corpora_v2"][language]) == EXPECTED_COUNTS["chapter_corpora"][language],
            f"{language} split manifest chapter count mismatch",
            failures,
        )
        require(
            len(splits["runtime_fixture_source_chapters_v2"][language]) * 3 == EXPECTED_COUNTS["runtime_fixtures"][language],
            f"{language} split manifest runtime-source count mismatch",
            failures,
        )
        require(
            len(splits["curated_excerpt_cases_v2"][language]) == EXPECTED_COUNTS["curated_excerpt_cases"][language],
            f"{language} split manifest curated count mismatch",
            failures,
        )

    compatibility_rows = dataset_rows("compatibility_fixtures", "attentional_v2_compat_shared_v2", "fixtures.jsonl")
    require(len(compatibility_rows) >= 18, f"Expected at least 18 compatibility fixtures, got {len(compatibility_rows)}", failures)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print(
        json.dumps(
            {
                "status": "ok",
                "promoted_books": len(promoted),
                "compatibility_fixtures": len(compatibility_rows),
                "chapter_counts": {lang: EXPECTED_COUNTS["chapter_corpora"][lang] for lang in ("en", "zh")},
                "runtime_fixture_counts": {lang: EXPECTED_COUNTS["runtime_fixtures"][lang] for lang in ("en", "zh")},
                "curated_excerpt_counts": {lang: EXPECTED_COUNTS["curated_excerpt_cases"][lang] for lang in ("en", "zh")},
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(validate())

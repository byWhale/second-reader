"""Build the public-first large bilingual attentional_v2 benchmark expansion."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from src.attentional_v2.storage import chapter_result_compatibility_file

from eval.attentional_v2.corpus_builder import (
    ACQUISITION_ROOT,
    DATASET_ROOT,
    MANIFEST_ROOT,
    ROOT,
    CandidateSpec,
    build_combined_public_pool,
    build_source_index,
    curate_excerpt_cases,
    dataset_manifest,
    download_candidate,
    load_json,
    make_compatibility_fixtures,
    make_excerpt_candidates,
    make_runtime_fixtures,
    promote_candidate,
    screen_source_book,
    select_final_chapter_rows,
    select_promoted_books,
    select_runtime_fixture_chapters,
    write_json,
    write_jsonl,
)


CANDIDATE_MANIFEST = Path(__file__).with_name("public_first_large_candidates.json")
EXISTING_PUBLIC_MANIFEST = MANIFEST_ROOT / "source_books" / "attentional_v2_public_domain_seed_v1.json"

NEW_CANDIDATE_MANIFEST_ID = "attentional_v2_public_first_large_candidates_v2"
COMBINED_PUBLIC_MANIFEST_ID = "attentional_v2_public_benchmark_pool_v2"
COMBINED_CORPUS_MANIFEST_ID = "attentional_v2_public_benchmark_pool_bilingual_v2"
COMBINED_SPLIT_MANIFEST_ID = "attentional_v2_public_benchmark_pool_bilingual_v2_splits"


def load_candidate_specs() -> list[CandidateSpec]:
    """Load the manifest-driven candidate specs."""

    payload = load_json(CANDIDATE_MANIFEST)
    return [CandidateSpec(**candidate) for candidate in payload["candidates"]]


def _screen_new_candidates(specs: list[CandidateSpec]) -> list[dict[str, Any]]:
    """Download and screen the new public/open candidates."""

    screened: list[dict[str, Any]] = []
    for spec in specs:
        acquired_path, acquisition_metadata = download_candidate(spec)
        screened.append(
            screen_source_book(
                spec=spec,
                local_path=acquired_path,
                relative_local_path=str(acquired_path.relative_to(ROOT)),
                acquisition_metadata=acquisition_metadata,
            )
        )
    return screened


def _promote_selected(screened_candidates: list[dict[str, Any]], specs: list[CandidateSpec]) -> list[dict[str, Any]]:
    """Promote the selected books into the durable source library and rescreen them from final paths."""

    spec_by_id = {spec.source_id: spec for spec in specs}
    promoted_records: list[dict[str, Any]] = []
    for language in ("en", "zh"):
        selected = select_promoted_books(screened_candidates, language=language, target_count=6)
        for record in selected:
            spec = spec_by_id[str(record["source_id"])]
            acquisition_path = ROOT / record["relative_local_path"]
            promoted_path = promote_candidate(acquisition_path, spec.promoted_local_path)
            promoted_record = screen_source_book(
                spec=spec,
                local_path=promoted_path,
                relative_local_path=str(promoted_path.relative_to(ROOT)),
                acquisition_metadata=dict(record.get("acquisition") or {}),
            )
            promoted_record["promotion_status"] = "promoted_v2"
            promoted_record["selected_for_public_benchmark"] = True
            promoted_records.append(promoted_record)
    return promoted_records


def _mark_candidate_promotions(screened_candidates: list[dict[str, Any]], promoted_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Annotate the new candidate manifest with promotion outcomes."""

    promoted_ids = {str(record["source_id"]) for record in promoted_records}
    annotated: list[dict[str, Any]] = []
    for record in screened_candidates:
        annotated_record = dict(record)
        annotated_record["promotion_status"] = "promoted_v2" if str(record["source_id"]) in promoted_ids else "not_promoted_v2"
        annotated.append(annotated_record)
    return annotated


def _write_source_manifests(screened_candidates: list[dict[str, Any]], combined_public_pool: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    """Write the source and corpus manifests used by the new v2 packages."""

    write_json(
        MANIFEST_ROOT / "source_books" / f"{NEW_CANDIDATE_MANIFEST_ID}.json",
        {
            "manifest_id": NEW_CANDIDATE_MANIFEST_ID,
            "description": "Screened 24-book public/open bilingual candidate pool for the public-first large attentional_v2 corpus expansion.",
            "books": screened_candidates,
        },
    )
    write_json(
        MANIFEST_ROOT / "source_books" / f"{COMBINED_PUBLIC_MANIFEST_ID}.json",
        {
            "manifest_id": COMBINED_PUBLIC_MANIFEST_ID,
            "description": "Combined tracked public/open source-book inventory used by the v2 attentional_v2 benchmark family.",
            "books": combined_public_pool,
        },
    )
    write_json(
        MANIFEST_ROOT / "local_refs" / f"{COMBINED_PUBLIC_MANIFEST_ID}.json",
        {
            "manifest_id": f"{COMBINED_PUBLIC_MANIFEST_ID}_local_refs",
            "description": "Local path references and checksums for the tracked public/open books used by the v2 attentional_v2 benchmark family.",
            "refs": [
                {
                    "source_id": record["source_id"],
                    "relative_local_path": record["relative_local_path"],
                    "sha256": record["sha256"],
                    "file_size": record["file_size"],
                }
                for record in combined_public_pool
            ],
        },
    )
    write_json(
        MANIFEST_ROOT / "corpora" / f"{COMBINED_CORPUS_MANIFEST_ID}.json",
        {
            "manifest_id": COMBINED_CORPUS_MANIFEST_ID,
            "description": "Combined bilingual tracked public/open source pool used to build the expanded v2 attentional_v2 benchmark family.",
            "language_tracks": {
                language: [record["source_id"] for record in combined_public_pool if record["language"] == language]
                for language in ("en", "zh")
            },
        },
    )
    source_manifest_refs = [
        f"eval/manifests/source_books/{COMBINED_PUBLIC_MANIFEST_ID}.json",
        f"eval/manifests/local_refs/{COMBINED_PUBLIC_MANIFEST_ID}.json",
        f"eval/manifests/corpora/{COMBINED_CORPUS_MANIFEST_ID}.json",
    ]
    split_refs = [
        f"eval/manifests/splits/{COMBINED_SPLIT_MANIFEST_ID}.json",
    ]
    return source_manifest_refs, split_refs


def _compat_fixture_status(chapter_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Load any already-materialized compatibility payloads."""

    status: dict[str, dict[str, Any]] = {}
    for row in chapter_rows:
        output_dir = ROOT / str(row["output_dir"])
        chapter_id = int(row["chapter_id"])
        payload_path = chapter_result_compatibility_file(output_dir, chapter_id)
        if not payload_path.exists():
            continue
        payload = load_json(payload_path)
        reactions = payload.get("reactions") or []
        status[str(row["chapter_case_id"])] = {
            "fixture_status": "materialized",
            "compatibility_payload_path": str(payload_path.relative_to(ROOT)),
            "visible_reaction_count": len(reactions),
            "notes": "Materialized from a live attentional_v2 compatibility payload.",
        }
    return status


def _write_split_manifest(
    *,
    combined_public_pool: list[dict[str, Any]],
    chapter_rows_by_language: dict[str, list[dict[str, Any]]],
    runtime_rows_by_language: dict[str, list[dict[str, Any]]],
    curated_rows_by_language: dict[str, list[dict[str, Any]]],
) -> None:
    """Write the v2 split manifest."""

    write_json(
        MANIFEST_ROOT / "splits" / f"{COMBINED_SPLIT_MANIFEST_ID}.json",
        {
            "manifest_id": COMBINED_SPLIT_MANIFEST_ID,
            "description": "Split and freeze manifest for the public-first large v2 attentional_v2 benchmark family.",
            "splits": {
                "candidate_screen_pool": {
                    language: [record["source_id"] for record in combined_public_pool if record["language"] == language]
                    for language in ("en", "zh")
                },
                "chapter_corpora_v2": {
                    language: [row["chapter_case_id"] for row in rows]
                    for language, rows in chapter_rows_by_language.items()
                },
                "runtime_fixture_source_chapters_v2": {
                    language: [row["chapter_case_id"] for row in rows]
                    for language, rows in runtime_rows_by_language.items()
                },
                "curated_excerpt_cases_v2": {
                    language: [row["case_id"] for row in rows]
                    for language, rows in curated_rows_by_language.items()
                },
            },
        },
    )


def _write_dataset_packages(
    *,
    chapter_rows_by_language: dict[str, list[dict[str, Any]]],
    runtime_rows_by_language: dict[str, list[dict[str, Any]]],
    excerpt_seed_rows_by_language: dict[str, list[dict[str, Any]]],
    curated_rows_by_language: dict[str, list[dict[str, Any]]],
    compatibility_rows: list[dict[str, Any]],
    source_manifest_refs: list[str],
    split_refs: list[str],
) -> None:
    """Write the v2 dataset packages."""

    for language in ("en", "zh"):
        chapter_id = f"attentional_v2_chapters_{language}_v2"
        runtime_id = f"attentional_v2_runtime_{language}_v2"
        excerpt_id = f"attentional_v2_excerpt_{language}_v2"
        curated_id = f"attentional_v2_excerpt_{language}_curated_v2"

        write_json(
            DATASET_ROOT / "chapter_corpora" / chapter_id / "manifest.json",
            dataset_manifest(
                dataset_id=chapter_id,
                family="chapter_corpora",
                language_track=language,
                description=f"{language.upper()} expanded public/open chapter corpus for the attentional_v2 v2 benchmark family.",
                primary_file="chapters.jsonl",
                source_manifest_refs=source_manifest_refs,
                split_refs=split_refs,
            ),
        )
        write_jsonl(DATASET_ROOT / "chapter_corpora" / chapter_id / "chapters.jsonl", chapter_rows_by_language[language])

        write_json(
            DATASET_ROOT / "runtime_fixtures" / runtime_id / "manifest.json",
            dataset_manifest(
                dataset_id=runtime_id,
                family="runtime_fixtures",
                language_track=language,
                description=f"{language.upper()} runtime and resume fixtures derived from the v2 chapter corpus.",
                primary_file="fixtures.jsonl",
                source_manifest_refs=source_manifest_refs,
                split_refs=split_refs,
            ),
        )
        write_jsonl(
            DATASET_ROOT / "runtime_fixtures" / runtime_id / "fixtures.jsonl",
            make_runtime_fixtures(runtime_rows_by_language[language]),
        )

        write_json(
            DATASET_ROOT / "excerpt_cases" / excerpt_id / "manifest.json",
            dataset_manifest(
                dataset_id=excerpt_id,
                family="excerpt_cases",
                language_track=language,
                description=f"{language.upper()} seed excerpt cases regenerated from the expanded v2 chapter corpus.",
                primary_file="cases.jsonl",
                source_manifest_refs=source_manifest_refs,
                split_refs=split_refs,
            ),
        )
        write_jsonl(DATASET_ROOT / "excerpt_cases" / excerpt_id / "cases.jsonl", excerpt_seed_rows_by_language[language])

        write_json(
            DATASET_ROOT / "excerpt_cases" / curated_id / "manifest.json",
            dataset_manifest(
                dataset_id=curated_id,
                family="excerpt_cases",
                language_track=language,
                description=f"{language.upper()} curated excerpt benchmark layer for the expanded public-first v2 family.",
                primary_file="cases.jsonl",
                source_manifest_refs=source_manifest_refs,
                split_refs=split_refs,
            ),
        )
        write_jsonl(DATASET_ROOT / "excerpt_cases" / curated_id / "cases.jsonl", curated_rows_by_language[language])

    compat_id = "attentional_v2_compat_shared_v2"
    write_json(
        DATASET_ROOT / "compatibility_fixtures" / compat_id / "manifest.json",
        dataset_manifest(
            dataset_id=compat_id,
            family="compatibility_fixtures",
            language_track="shared",
            description="Shared compatibility fixtures for the expanded public-first v2 attentional_v2 benchmark family.",
            primary_file="fixtures.jsonl",
            source_manifest_refs=source_manifest_refs,
            split_refs=split_refs,
        ),
    )
    write_jsonl(DATASET_ROOT / "compatibility_fixtures" / compat_id / "fixtures.jsonl", compatibility_rows)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""

    return argparse.ArgumentParser(description=__doc__)


def main(argv: list[str] | None = None) -> None:
    """Run the public-first large corpus build."""

    build_parser().parse_args(argv)
    specs = load_candidate_specs()
    screened_candidates = _screen_new_candidates(specs)
    promoted_records = _promote_selected(screened_candidates, specs)
    screened_candidates = _mark_candidate_promotions(screened_candidates, promoted_records)

    combined_public_pool = build_combined_public_pool(EXISTING_PUBLIC_MANIFEST, promoted_records)
    source_manifest_refs, split_refs = _write_source_manifests(screened_candidates, combined_public_pool)

    source_index = build_source_index(combined_public_pool)
    chapter_rows_by_language = {
        language: select_final_chapter_rows(combined_public_pool, language=language)
        for language in ("en", "zh")
    }
    runtime_rows_by_language = {
        language: select_runtime_fixture_chapters(chapter_rows_by_language[language])
        for language in ("en", "zh")
    }
    excerpt_seed_rows_by_language = {}
    curated_rows_by_language = {}
    for language in ("en", "zh"):
        excerpt_candidates = make_excerpt_candidates(chapter_rows_by_language[language], source_index)
        excerpt_seed_rows = []
        for candidate in excerpt_candidates:
            excerpt_seed_rows.append(
                {
                    "case_id": candidate["candidate_case_id"],
                    "split": "seed_v2",
                    "source_id": candidate["source_id"],
                    "book_title": candidate["book_title"],
                    "author": candidate["author"],
                    "output_language": language,
                    "chapter_title": candidate["chapter_title"],
                    "chapter_number": candidate["chapter_number"],
                    "start_sentence_id": candidate["start_sentence_id"],
                    "end_sentence_id": candidate["end_sentence_id"],
                    "excerpt_text": candidate["excerpt_text"],
                    "tags": ["seed_v2", candidate["selection_role"], candidate["position_bucket"]],
                    "notes": "Auto-generated seed excerpt from the expanded public-first v2 chapter corpus.",
                }
            )
        excerpt_seed_rows_by_language[language] = excerpt_seed_rows
        curated_rows_by_language[language] = curate_excerpt_cases(excerpt_candidates, language=language)

    _write_split_manifest(
        combined_public_pool=combined_public_pool,
        chapter_rows_by_language=chapter_rows_by_language,
        runtime_rows_by_language=runtime_rows_by_language,
        curated_rows_by_language=curated_rows_by_language,
    )

    compatibility_rows = make_compatibility_fixtures(
        chapter_rows_by_language["en"] + chapter_rows_by_language["zh"],
        fixture_status_by_case=_compat_fixture_status(chapter_rows_by_language["en"] + chapter_rows_by_language["zh"]),
    )
    _write_dataset_packages(
        chapter_rows_by_language=chapter_rows_by_language,
        runtime_rows_by_language=runtime_rows_by_language,
        excerpt_seed_rows_by_language=excerpt_seed_rows_by_language,
        curated_rows_by_language=curated_rows_by_language,
        compatibility_rows=compatibility_rows,
        source_manifest_refs=source_manifest_refs,
        split_refs=split_refs,
    )

    summary = {
        "candidate_manifest": NEW_CANDIDATE_MANIFEST_ID,
        "combined_manifest": COMBINED_PUBLIC_MANIFEST_ID,
        "new_candidates_screened": len(screened_candidates),
        "new_candidates_promoted": len(promoted_records),
        "combined_public_pool": len(combined_public_pool),
        "chapter_counts": {language: len(rows) for language, rows in chapter_rows_by_language.items()},
        "runtime_fixture_counts": {
            language: len(make_runtime_fixtures(rows))
            for language, rows in runtime_rows_by_language.items()
        },
        "curated_excerpt_counts": {language: len(rows) for language, rows in curated_rows_by_language.items()},
        "compatibility_fixture_count": len(compatibility_rows),
        "acquisition_root": str(ACQUISITION_ROOT.relative_to(ROOT)),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main(sys.argv[1:])

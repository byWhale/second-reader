"""Tests for the managed-catalog private-library supplement wiring."""

from __future__ import annotations

import json
from pathlib import Path

from eval.attentional_v2 import build_private_library_supplement as builder_module
from eval.attentional_v2.build_private_library_supplement import (
    build_private_library_splits,
    load_private_library_source_items,
)
from eval.attentional_v2.corpus_builder import CandidateSpec


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, payload: object) -> None:
    _write(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def test_load_private_library_source_items_uses_catalog_paths_and_manifest_fallbacks(tmp_path: Path) -> None:
    root = tmp_path
    source_path = root / "state" / "library_sources" / "en" / "fooled_by_randomness.epub"
    _write(source_path, "demo")

    catalog_path = root / "state" / "dataset_build" / "source_catalog.json"
    _write_json(
        catalog_path,
        {
            "records": [
                {
                    "source_id": "fooled_by_randomness_private_en",
                    "title": "Fooled by Randomness",
                    "author": "Nassim Nicholas Taleb",
                    "language": "en",
                    "visibility": "private",
                    "origin": "manual_library_inbox",
                    "relative_local_path": "state/library_sources/en/fooled_by_randomness.epub",
                    "original_filename": "Fooled by Randomness.epub",
                    "selection_priority": 9999,
                    "type_tags": [],
                    "role_tags": [],
                    "notes": [],
                    "ingest_batch_ids": ["catalog_batch_a"],
                    "acquisition": {
                        "kind": "manual_library_inbox",
                        "ingest_batch_id": "catalog_batch_a",
                    },
                }
            ]
        },
    )

    tracked_manifest_path = root / "eval" / "manifests" / "source_books" / "attentional_v2_private_library_screen_v2.json"
    _write_json(
        tracked_manifest_path,
        {
            "books": [
                {
                    "source_id": "fooled_by_randomness_private_en",
                    "selection_priority": 6,
                    "type_tags": ["psychology_decision", "modern_nonfiction"],
                    "role_tags": ["argumentative", "reference_heavy"],
                    "notes": ["Legacy private source retained."],
                    "acquisition_batch_id": "legacy_private_downloads_v1",
                }
            ]
        },
    )

    items = load_private_library_source_items(
        root=root,
        catalog_path=catalog_path,
        tracked_manifest_path=tracked_manifest_path,
    )

    assert len(items) == 1
    item = items[0]
    spec = item["spec"]
    assert spec.source_id == "fooled_by_randomness_private_en"
    assert spec.promoted_local_path == "en/fooled_by_randomness.epub"
    assert spec.selection_priority == 6
    assert spec.type_tags == ["psychology_decision", "modern_nonfiction"]
    assert spec.role_tags == ["argumentative", "reference_heavy"]
    assert spec.notes == ["Legacy private source retained."]
    assert item["source_path"] == source_path
    assert item["acquisition_batch_id"] == "legacy_private_downloads_v1"


def test_load_private_library_source_items_prefers_explicit_catalog_metadata_and_ignores_visibility_gating(tmp_path: Path) -> None:
    root = tmp_path
    private_source = root / "state" / "library_sources" / "zh" / "case_a.epub"
    public_source = root / "state" / "library_sources" / "en" / "case_b.epub"
    _write(private_source, "a")
    _write(public_source, "b")

    catalog_path = root / "state" / "dataset_build" / "source_catalog.json"
    _write_json(
        catalog_path,
        {
            "records": [
                {
                    "source_id": "case_a_private_zh",
                    "title": "案例A",
                    "author": "作者A",
                    "language": "zh",
                    "visibility": "private",
                    "origin": "manual_library_inbox",
                    "relative_local_path": "state/library_sources/zh/case_a.epub",
                    "selection_priority": 3,
                    "type_tags": ["history"],
                    "role_tags": ["argumentative"],
                    "notes": ["Catalog metadata wins."],
                    "original_filename": "case_a.epub",
                },
                {
                    "source_id": "case_b_public_en",
                    "title": "Case B",
                    "author": "Author B",
                    "language": "en",
                    "visibility": "public",
                    "origin": "manual_library_inbox",
                    "relative_local_path": "state/library_sources/en/case_b.epub",
                    "selection_priority": 1,
                    "type_tags": ["business"],
                    "role_tags": ["expository"],
                    "notes": ["Visibility should not exclude this managed source."],
                    "original_filename": "case_b.epub",
                },
            ]
        },
    )

    items = load_private_library_source_items(root=root, catalog_path=catalog_path, tracked_manifest_path=root / "missing.json")

    assert len(items) == 2
    specs = {item["spec"].source_id: item["spec"] for item in items}
    assert specs["case_a_private_zh"].selection_priority == 3
    assert specs["case_a_private_zh"].type_tags == ["history"]
    assert specs["case_a_private_zh"].role_tags == ["argumentative"]
    assert specs["case_a_private_zh"].notes == ["Catalog metadata wins."]
    assert specs["case_b_public_en"].selection_priority == 1
    assert specs["case_b_public_en"].type_tags == ["business"]
    assert specs["case_b_public_en"].role_tags == ["expository"]
    assert specs["case_b_public_en"].notes == ["Visibility should not exclude this managed source."]


def test_build_private_library_splits_adds_dynamic_batch_groups() -> None:
    source_records = [
        {
            "source_id": "legacy_en",
            "language": "en",
            "corpus_lane": "chapter_corpus_eligible",
            "acquisition_batch_id": "legacy_private_downloads_v1",
        },
        {
            "source_id": "new_zh",
            "language": "zh",
            "corpus_lane": "excerpt_only",
            "acquisition_batch_id": "batch_20260330",
        },
        {
            "source_id": "reject_en",
            "language": "en",
            "corpus_lane": "reject",
            "acquisition_batch_id": "",
        },
    ]

    splits = build_private_library_splits(source_records)

    assert splits["all_private_library_sources"] == {
        "en": ["legacy_en", "reject_en"],
        "zh": ["new_zh"],
    }
    assert splits["chapter_corpus_eligible"]["en"] == ["legacy_en"]
    assert splits["excerpt_only"]["zh"] == ["new_zh"]
    assert splits["reject_this_pass"]["en"] == ["reject_en"]
    assert splits["legacy_private_downloads_v1"]["en"] == ["legacy_en"]
    assert splits["batch_20260330"]["zh"] == ["new_zh"]


def test_main_wires_question_aligned_excerpt_outputs_without_using_old_seed_builder(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path
    source_path = root / "state" / "library_sources" / "en" / "demo.epub"
    _write(source_path, "demo")
    _write_json(
        root
        / "state"
        / "eval_local_datasets"
        / "excerpt_cases"
        / "attentional_v2_private_library_excerpt_en_v2"
        / "cases.jsonl",
        [],
    )
    legacy_feedback_path = (
        root
        / "state"
        / "eval_local_datasets"
        / "excerpt_cases"
        / "attentional_v2_private_library_excerpt_en_v2"
        / "cases.jsonl"
    )
    legacy_feedback_path.write_text(
        json.dumps(
            {
                "case_id": "legacy_en_case",
                "target_profile_id": "distinction_definition",
                "benchmark_status": "needs_revision",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(builder_module, "ROOT", root)
    monkeypatch.setattr(builder_module, "MANIFEST_ROOT", root / "eval" / "manifests")
    monkeypatch.setattr(builder_module, "STATE_LOCAL_DATASET_ROOT", root / "state" / "eval_local_datasets")
    monkeypatch.setattr(
        builder_module,
        "load_private_library_source_items",
        lambda: [
            {
                "spec": CandidateSpec(
                    source_id="demo_private_en",
                    title="Demo Book",
                    author="Demo Author",
                    language="en",
                    origin="managed-library-source",
                    storage_mode="local-only",
                    promoted_local_path="en/demo.epub",
                    acquisition={"kind": "managed_source_catalog"},
                    type_tags=["essay"],
                    role_tags=["argumentative"],
                    selection_priority=1,
                    notes=[],
                ),
                "source_path": source_path,
                "acquisition_batch_id": "batch_a",
                "origin_filename": "demo.epub",
                "relative_local_path": "state/library_sources/en/demo.epub",
            }
        ],
    )
    monkeypatch.setattr(
        builder_module,
        "screen_source_book",
        lambda **_kwargs: {
            "source_id": "demo_private_en",
            "title": "Demo Book",
            "author": "Demo Author",
            "language": "en",
            "type_tags": ["essay"],
            "role_tags": ["argumentative"],
            "relative_local_path": "state/library_sources/en/demo.epub",
            "sha256": "abc",
            "file_size": 4,
            "output_dir": "outputs/demo_private_en",
            "corpus_lane": "chapter_corpus_eligible",
            "selection_priority": 1,
            "candidate_chapters": [
                {
                    "chapter_id": "1",
                    "chapter_number": 1,
                    "chapter_title": "Chapter 1",
                    "sentence_count": 6,
                    "paragraph_count": 3,
                    "position_bucket": "middle",
                    "score": 4.5,
                }
            ],
        },
    )
    monkeypatch.setattr(
        builder_module,
        "load_book_document",
        lambda _path: {
            "chapters": [
                {
                    "id": "1",
                    "sentences": [
                        {
                            "sentence_id": "c1-s1",
                            "text": "Rather than chasing applause, the author defines integrity as refusing the easy comfort everyone else wants him to accept.",
                        },
                        {
                            "sentence_id": "c1-s2",
                            "text": "But that confidence turns out fragile, and the chapter suddenly asks why the speaker needed public praise after claiming independence.",
                        },
                        {
                            "sentence_id": "c1-s3",
                            "text": "Again the writer returns to the same promise from earlier, comparing this hesitation with the first vow to stand apart.",
                        },
                        {
                            "sentence_id": "c1-s4",
                            "text": "Only then does the chapter admit that the decision would matter differently later, after the public failure had already exposed its weakness.",
                        },
                    ],
                }
            ]
        },
    )
    monkeypatch.setattr(
        builder_module,
        "make_runtime_fixtures",
        lambda rows: [{"fixture_id": row["chapter_case_id"]} for row in rows],
    )
    monkeypatch.setattr(
        builder_module,
        "make_compatibility_fixtures",
        lambda rows: [{"fixture_id": row["chapter_case_id"]} for row in rows],
    )

    builder_module.main()

    new_dataset_dir = (
        root
        / "state"
        / "eval_local_datasets"
        / "excerpt_cases"
        / "attentional_v2_private_library_excerpt_en_question_aligned_v1"
    )
    cases_path = new_dataset_dir / "cases.jsonl"
    manifest_path = new_dataset_dir / "manifest.json"
    adequacy_path = (
        root
        / "state"
        / "dataset_build"
        / "adequacy_reports"
        / "attentional_v2_private_library_excerpt_question_aligned_v1.json"
    )

    assert cases_path.exists()
    assert manifest_path.exists()
    assert adequacy_path.exists()

    cases = [json.loads(line) for line in cases_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    adequacy = json.loads(adequacy_path.read_text(encoding="utf-8"))

    assert len(cases) == 1
    assert cases[0]["target_profile_id"]
    assert manifest["feedback_source_dataset_id"] == "attentional_v2_private_library_excerpt_en_v2"
    assert any(
        ref.endswith("attentional_v2_private_library_excerpt_en_question_aligned_v1.jsonl")
        for ref in manifest["dataset_build_artifact_refs"]
    )
    assert adequacy["recommended_next_action"] == "review_existing_cases"

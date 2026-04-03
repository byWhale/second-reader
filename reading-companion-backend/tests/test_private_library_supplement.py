"""Tests for the managed-catalog private-library supplement wiring."""

from __future__ import annotations

import json
from pathlib import Path

from eval.attentional_v2 import build_private_library_supplement as builder_module
from eval.attentional_v2.build_private_library_supplement import (
    CLUSTERED_BENCHMARK_CHAPTER_CASE_IDS,
    CLUSTERED_BENCHMARK_MODE,
    CLUSTERED_CASES_PER_CHAPTER,
    CLUSTERED_RESERVES_PER_CHAPTER,
    SupplementBuildOptions,
    build_private_library_splits,
    load_private_library_source_items,
    resolve_build_config,
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


def test_resolve_build_config_scratch_redirects_ids_and_paths(tmp_path: Path) -> None:
    config = resolve_build_config(
        SupplementBuildOptions(
            scratch=True,
            run_id="scratch demo",
            feedback_dataset_ids={},
        ),
        root=tmp_path,
        manifest_root=tmp_path / "eval" / "manifests",
        local_dataset_root=tmp_path / "state" / "eval_local_datasets",
    )

    assert config.run_id == "scratch_demo"
    assert config.run_root == tmp_path / "state" / "dataset_build" / "build_runs" / "scratch_demo"
    assert config.manifest_root == config.run_root / "manifests"
    assert config.dataset_build_artifact_root == config.run_root
    assert config.ids.question_aligned_scope_id.endswith("__scratch__scratch_demo")
    assert (
        config.ids.package_ids["excerpt_cases"]["en"]
        == "attentional_v2_private_library_excerpt_en_question_aligned_v1__scratch__scratch_demo"
    )
    assert config.feedback_dataset_ids == {}


def test_resolve_build_config_clustered_mode_uses_cluster_defaults(tmp_path: Path) -> None:
    config = resolve_build_config(
        SupplementBuildOptions(
            benchmark_mode=CLUSTERED_BENCHMARK_MODE,
            scratch=True,
            run_id="clustered_demo",
            feedback_dataset_ids={},
        ),
        root=tmp_path,
        manifest_root=tmp_path / "eval" / "manifests",
        local_dataset_root=tmp_path / "state" / "eval_local_datasets",
    )

    assert config.benchmark_mode == CLUSTERED_BENCHMARK_MODE
    assert config.chapter_case_ids == CLUSTERED_BENCHMARK_CHAPTER_CASE_IDS
    assert config.cases_per_chapter == CLUSTERED_CASES_PER_CHAPTER
    assert config.reserves_per_chapter == CLUSTERED_RESERVES_PER_CHAPTER
    assert config.max_chapters_per_source == 0
    assert (
        config.ids.package_ids["excerpt_cases"]["en"]
        == "attentional_v2_clustered_benchmark_v1_excerpt_en__scratch__clustered_demo"
    )


def test_collect_source_build_state_honors_explicit_chapter_case_ids(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path
    source_path = root / "state" / "library_sources" / "en" / "demo.epub"
    _write(source_path, "demo")

    monkeypatch.setattr(
        builder_module,
        "load_private_library_source_items",
        lambda **_kwargs: [
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
                    "chapter_id": "17",
                    "chapter_number": 17,
                    "chapter_title": "Keep Me",
                    "sentence_count": 80,
                    "paragraph_count": 16,
                    "position_bucket": "middle",
                    "score": 4.5,
                },
                {
                    "chapter_id": "24",
                    "chapter_number": 24,
                    "chapter_title": "Drop Me",
                    "sentence_count": 84,
                    "paragraph_count": 20,
                    "position_bucket": "late",
                    "score": 4.2,
                },
            ],
        },
    )

    config = resolve_build_config(
        SupplementBuildOptions(
            scratch=True,
            run_id="clustered_chapter_filter",
            benchmark_mode=CLUSTERED_BENCHMARK_MODE,
            chapter_case_ids=("demo_private_en__17",),
            feedback_dataset_ids={},
        ),
        root=root,
        manifest_root=root / "eval" / "manifests",
        local_dataset_root=root / "state" / "eval_local_datasets",
    )

    state = builder_module.collect_source_build_state(config)

    assert [row["chapter_case_id"] for row in state.chapter_rows_by_language["en"]] == [
        "demo_private_en__17"
    ]


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
        lambda **_kwargs: [
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

    builder_module.main(["--no-bootstrap-catalog-if-missing"])

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


def test_main_scratch_build_writes_run_scoped_outputs_without_touching_live_ids(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path
    source_path = root / "state" / "library_sources" / "en" / "demo.epub"
    _write(source_path, "demo")
    legacy_feedback_path = (
        root
        / "state"
        / "eval_local_datasets"
        / "excerpt_cases"
        / "attentional_v2_private_library_excerpt_en_v2"
        / "cases.jsonl"
    )
    legacy_feedback_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_feedback_path.write_text("", encoding="utf-8")

    monkeypatch.setattr(builder_module, "ROOT", root)
    monkeypatch.setattr(builder_module, "MANIFEST_ROOT", root / "eval" / "manifests")
    monkeypatch.setattr(builder_module, "STATE_LOCAL_DATASET_ROOT", root / "state" / "eval_local_datasets")
    monkeypatch.setattr(
        builder_module,
        "load_private_library_source_items",
        lambda **_kwargs: [
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

    builder_module.main(
        ["--scratch", "--run-id", "scratch_demo", "--no-bootstrap-catalog-if-missing"]
    )

    scratch_dataset_id = "attentional_v2_private_library_excerpt_en_question_aligned_v1__scratch__scratch_demo"
    scratch_dataset_dir = (
        root
        / "state"
        / "eval_local_datasets"
        / "excerpt_cases"
        / scratch_dataset_id
    )
    run_root = root / "state" / "dataset_build" / "build_runs" / "scratch_demo"
    live_dataset_dir = (
        root
        / "state"
        / "eval_local_datasets"
        / "excerpt_cases"
        / "attentional_v2_private_library_excerpt_en_question_aligned_v1"
    )
    tracked_manifest_path = (
        root / "eval" / "manifests" / "source_books" / "attentional_v2_private_library_screen_v2.json"
    )
    summary_path = run_root / "build_summary.json"
    adequacy_path = (
        run_root
        / "adequacy_reports"
        / "attentional_v2_private_library_excerpt_question_aligned_v1__scratch__scratch_demo.json"
    )
    source_manifest_path = (
        run_root
        / "manifests"
        / "source_books"
        / "attentional_v2_private_library_screen_v2__scratch__scratch_demo.json"
    )

    assert scratch_dataset_dir.exists()
    assert (scratch_dataset_dir / "cases.jsonl").exists()
    assert not live_dataset_dir.exists()
    assert not tracked_manifest_path.exists()
    assert summary_path.exists()
    assert adequacy_path.exists()
    assert source_manifest_path.exists()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    manifest = json.loads((scratch_dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    assert summary["scratch"] is True
    assert summary["dataset_ids"]["excerpt_cases"]["en"] == scratch_dataset_id
    assert manifest["feedback_source_dataset_id"] == "attentional_v2_private_library_excerpt_en_v2"


def test_builder_auto_bootstraps_source_catalog_when_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path
    source_path = root / "state" / "library_sources" / "en" / "walden_205.epub"
    _write(source_path, "demo")
    _write_json(
        root / "eval" / "manifests" / "source_books" / "attentional_v2_public_benchmark_pool_v2.json",
        {
            "books": [
                {
                    "source_id": "walden_205_en",
                    "title": "Walden",
                    "author": "Henry David Thoreau",
                    "language": "en",
                    "origin": "public-open-access",
                    "source_url": "https://www.gutenberg.org/ebooks/205",
                    "relative_local_path": "state/library_sources/en/walden_205.epub",
                    "type_tags": ["essay"],
                    "role_tags": ["argumentative"],
                    "selection_priority": 1,
                    "notes": ["Tracked public source."],
                }
            ]
        },
    )

    monkeypatch.setattr(builder_module, "ROOT", root)
    monkeypatch.setattr(builder_module, "MANIFEST_ROOT", root / "eval" / "manifests")
    monkeypatch.setattr(builder_module, "STATE_LOCAL_DATASET_ROOT", root / "state" / "eval_local_datasets")
    monkeypatch.setattr(
        builder_module,
        "screen_source_book",
        lambda **_kwargs: {
            "source_id": "walden_205_en",
            "title": "Walden",
            "author": "Henry David Thoreau",
            "language": "en",
            "type_tags": ["essay"],
            "role_tags": ["argumentative"],
            "relative_local_path": "state/library_sources/en/walden_205.epub",
            "sha256": "abc",
            "file_size": 4,
            "output_dir": "outputs/walden_205_en",
            "corpus_lane": "chapter_corpus_eligible",
            "selection_priority": 1,
            "candidate_chapters": [
                {
                    "chapter_id": "1",
                    "chapter_number": 1,
                    "chapter_title": "Where I Lived",
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

    builder_module.main(["--scratch", "--run-id", "bootstrap_demo"])

    source_catalog_path = root / "state" / "dataset_build" / "source_catalog.json"
    summary_path = root / "state" / "dataset_build" / "build_runs" / "bootstrap_demo" / "build_summary.json"
    assert source_catalog_path.exists()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["source_catalog_bootstrap"] is not None
    assert summary["source_catalog_bootstrap"]["mode"] == "bootstrap_library_sources"

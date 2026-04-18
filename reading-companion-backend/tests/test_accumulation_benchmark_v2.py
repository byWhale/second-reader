from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval.attentional_v2 import accumulation_benchmark_v2 as accumulation_v2


def _span_slice(*, segment_id: str, paragraph_index: int, char_start: int, char_end: int, text: str) -> dict[str, object]:
    return {
        "coordinate_system": "segment_source_v1",
        "segment_id": segment_id,
        "paragraph_index": paragraph_index,
        "char_start": char_start,
        "char_end": char_end,
        "text": text,
    }


def _span_point(point_id: str, *, segment_id: str, paragraph_index: int, char_start: int, char_end: int, text: str) -> dict[str, object]:
    return {
        "point_id": point_id,
        "label": point_id,
        "span_text": text,
        "span_slices": [
            _span_slice(
                segment_id=segment_id,
                paragraph_index=paragraph_index,
                char_start=char_start,
                char_end=char_end,
                text=text,
            )
        ],
    }


def _case_row(case_id: str = "case_a", *, upstream_count: int = 2) -> dict[str, object]:
    upstream_nodes = []
    for index in range(upstream_count):
        upstream_nodes.append(
            {
                "node_id": f"u{index + 1}",
                "label": f"Node {index + 1}",
                "summary": f"Summary {index + 1}",
                "span_text": f"Earlier text {index + 1}",
                "span_slices": [
                    _span_slice(
                        segment_id="segment_a",
                        paragraph_index=index + 1,
                        char_start=0,
                        char_end=10,
                        text=f"Earlier text {index + 1}",
                    )
                ],
            }
        )
    return {
        "case_id": case_id,
        "source_id": "source_a",
        "book": "Book A",
        "author": "Author A",
        "output_language": "en",
        "window_id": "segment_a",
        "thread_type": "论证型论证线",
        "target_span": _span_point("target", segment_id="segment_a", paragraph_index=5, char_start=0, char_end=12, text="Target text"),
        "upstream_nodes": upstream_nodes,
        "expected_integration": "The target reaction should connect the later claim back to the earlier line of reasoning.",
        "callback_eligible_spans": [
            _span_point("callback_1", segment_id="segment_a", paragraph_index=2, char_start=0, char_end=10, text="Earlier text 2")
        ],
        "non_goal_but_tempting_points": [
            _span_point("tempting_1", segment_id="segment_a", paragraph_index=4, char_start=0, char_end=10, text="Nearby but wrong")
        ],
        "long_range_rationale": "The upstream nodes are materially earlier than the target and the target depends on them.",
        "curation_status": "candidate_review_pending",
        "provenance": {"note": "test"},
    }


def test_target_case_from_row_accepts_variable_upstream_counts() -> None:
    for upstream_count in (2, 3, 4):
        case = accumulation_v2.target_case_from_row(_case_row(case_id=f"case_{upstream_count}", upstream_count=upstream_count))
        assert case.case_id == f"case_{upstream_count}"
        assert len(case.upstream_nodes) == upstream_count


def test_target_case_from_row_requires_target_span_and_expected_integration() -> None:
    row = _case_row()
    row.pop("target_span")
    with pytest.raises(ValueError, match="missing target_span"):
        accumulation_v2.target_case_from_row(row)

    row = _case_row()
    row["expected_integration"] = ""
    with pytest.raises(ValueError, match="expected_integration"):
        accumulation_v2.target_case_from_row(row)


def test_build_draft_manifest_payload_tracks_draft_and_freeze_ready_counts() -> None:
    candidate = _case_row("case_candidate")
    approved = _case_row("case_approved")
    approved["curation_status"] = "approved_draft"

    manifest = accumulation_v2.build_draft_manifest_payload([candidate, approved])

    assert manifest["active_design"] == "target_centered_long_span_accumulation_v2"
    assert manifest["quota_status"]["window_substrate"]["dataset_id"] == accumulation_v2.WINDOW_DATASET_ID
    assert manifest["quota_status"]["accumulation_target_cases"]["target_total"] == 2
    assert manifest["quota_status"]["accumulation_target_cases"]["freeze_ready"] == 1
    assert manifest["splits"]["accumulation_target_cases_draft"]["all"] == ["case_candidate", "case_approved"]
    assert manifest["splits"]["accumulation_target_cases_frozen"]["all"] == ["case_approved"]


def test_write_draft_artifacts_writes_dataset_and_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dataset_dir = tmp_path / "cases_draft"
    manifest_path = tmp_path / "accumulation_v2_manifest.json"
    monkeypatch.setattr(accumulation_v2, "TARGET_CASE_DRAFT_DATASET_DIR", dataset_dir)
    monkeypatch.setattr(accumulation_v2, "DRAFT_MANIFEST_PATH", manifest_path)

    summary = accumulation_v2.write_draft_artifacts([_case_row("case_a")])

    assert summary["case_count"] == 1
    assert json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))["case_count"] == 1
    assert (dataset_dir / "cases.jsonl").exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["splits"]["accumulation_target_cases_draft"]["all"] == ["case_a"]

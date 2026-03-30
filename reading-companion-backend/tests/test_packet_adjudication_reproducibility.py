"""Tests for packet adjudication reproducibility helpers."""

from __future__ import annotations

import csv
import json
from contextlib import nullcontext
from pathlib import Path

from eval.attentional_v2 import auto_review_packet
from eval.attentional_v2 import compare_packet_adjudication_runs as compare_runs
from eval.attentional_v2.compare_packet_adjudication_runs import compare_adjudication_runs
from src.reading_runtime.job_concurrency import JobConcurrencyPolicy


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_packet(packet_dir: Path) -> None:
    _write_json(
        packet_dir / "packet_manifest.json",
        {
            "packet_id": "demo_packet",
            "dataset_id": "demo_dataset",
        },
    )
    with (packet_dir / "cases.review.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "case_id",
                "review__action",
                "review__confidence",
                "review__problem_types",
                "review__revised_bucket",
                "review__revised_selection_reason",
                "review__revised_judge_focus",
                "review__notes",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "case_id": "demo_case",
                "review__action": "",
                "review__confidence": "",
                "review__problem_types": "",
                "review__revised_bucket": "",
                "review__revised_selection_reason": "",
                "review__revised_judge_focus": "",
                "review__notes": "",
            }
        )
    (packet_dir / "cases.source.jsonl").write_text(
        json.dumps(
            {
                "case_id": "demo_case",
                "book_title": "Demo Book",
                "author": "Demo Author",
                "chapter_id": "1",
                "chapter_title": "Demo Chapter",
                "question_ids": ["Q1"],
                "phenomena": ["focus"],
                "selection_reason": "Needs a cleanup pass.",
                "judge_focus": "Does the case stay anchored?",
                "excerpt_text": "Demo excerpt.",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_completed_audit(run_dir: Path) -> None:
    _write_json(
        run_dir / "cases" / "demo_case.json",
        {
            "case_id": "demo_case",
            "factual_audit": {"ok": True},
            "primary_review": {"decision": "revise"},
            "adversarial_review": {"risk_level": "medium"},
        },
    )


def _write_compare_run(
    run_dir: Path,
    *,
    action: str,
    confidence: str,
    packet_fingerprint: str = "same-packet",
    case_fingerprint: str = "same-case",
    source_fingerprint: str = "same-source",
    audit_fingerprint: str = "same-audit",
) -> None:
    _write_json(
        run_dir / "summary.json",
        {
            "packet_id": "demo_packet",
            "run_id": run_dir.name,
            "review_policy": auto_review_packet.REVIEW_POLICY,
            "adjudication_contract_version": auto_review_packet.ADJUDICATION_CONTRACT_VERSION,
            "adjudication_input_fingerprint": packet_fingerprint,
            "action_counts": {action: 1},
        },
    )
    _write_json(
        run_dir / "cases" / "demo_case.json",
        {
            "case_id": "demo_case",
            "adjudication_input_fingerprint": case_fingerprint,
            "source_row_fingerprint": source_fingerprint,
            "audit_row_fingerprint": audit_fingerprint,
            "normalized_review": {
                "review__action": action,
                "review__confidence": confidence,
                "review__problem_types": ["weak_excerpt"] if action == "revise" else ["other"],
            },
            "provider_id": "minimax_highspeed_provider",
            "selected_target_id": "minimax_m27_highspeed",
            "selected_tier_id": "primary",
            "key_slot_id": "primary",
            "contract": "anthropic",
            "model": "MiniMax-M2.7-highspeed",
        },
    )


def _write_legacy_compare_packet(
    packet_dir: Path,
    *,
    packet_id: str,
    audit_run_id: str,
    action: str,
    confidence: str,
    timing_offset: int,
) -> None:
    _write_json(
        packet_dir / "packet_manifest.json",
        {
            "packet_id": packet_id,
            "source_case_audit_run_id": audit_run_id,
        },
    )
    _write_json(
        packet_dir / "llm_review_summary.json",
        {
            "packet_id": packet_id,
            "run_id": f"{packet_id}__llm_review__legacy",
            "review_policy": auto_review_packet.REVIEW_POLICY,
            "adjudication_contract_version": auto_review_packet.ADJUDICATION_CONTRACT_VERSION,
            "source_case_audit_run_id": audit_run_id,
            "action_counts": {action: 1},
        },
    )
    with (packet_dir / "cases.review.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "case_id",
                "review__action",
                "review__confidence",
                "review__problem_types",
                "review__revised_bucket",
                "review__revised_selection_reason",
                "review__revised_judge_focus",
                "review__notes",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "case_id": "demo_case",
                "review__action": action,
                "review__confidence": confidence,
                "review__problem_types": "weak_excerpt" if action == "revise" else "other",
                "review__revised_bucket": "",
                "review__revised_selection_reason": "",
                "review__revised_judge_focus": "",
                "review__notes": "legacy",
            }
        )
    (packet_dir / "cases.source.jsonl").write_text(
        json.dumps(
            {
                "case_id": "demo_case",
                "book_title": "Demo Book",
                "author": "Demo Author",
                "chapter_id": "1",
                "chapter_title": "Demo Chapter",
                "question_ids": ["Q1"],
                "phenomena": ["focus"],
                "selection_reason": "Needs a cleanup pass.",
                "judge_focus": "Does the case stay anchored?",
                "excerpt_text": "Demo excerpt.",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    trace_dir = packet_dir / "llm_review_runs" / f"{packet_id}__llm_review__legacy" / "llm_traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    (trace_dir / "standard.jsonl").write_text("", encoding="utf-8")
    audit_case = {
        "case_id": "demo_case",
        "packet_id": packet_id,
        "status_details": {
            "timing_ms": {
                "factual_audit": 10 + timing_offset,
                "primary_review": 20 + timing_offset,
                "adversarial_review": 30 + timing_offset,
                "total": 60 + timing_offset,
            }
        },
        "factual_audit": {"ok": True},
        "primary_review": {
            "decision": "revise",
            "confidence": "medium",
            "notes": "Benchmark-ready after cleanup.",
        },
        "adversarial_review": {
            "risk_level": "medium",
            "notes": "Still acceptable.",
        },
    }
    _write_json(
        packet_dir.parents[2]
        / "runs"
        / "attentional_v2"
        / "case_audits"
        / audit_run_id
        / "cases"
        / "demo_case.json",
        audit_case,
    )


def test_probe_only_writes_run_artifacts_without_mutating_packet(monkeypatch, tmp_path: Path) -> None:
    packet_dir = tmp_path / "packet"
    audit_run_dir = tmp_path / "audit_run"
    _write_packet(packet_dir)
    _write_completed_audit(audit_run_dir)

    monkeypatch.setattr(
        auto_review_packet,
        "find_latest_case_audit_run",
        lambda *_args, **_kwargs: {"run_dir": str(audit_run_dir)},
    )
    monkeypatch.setattr(
        auto_review_packet,
        "invoke_json",
        lambda *_args, **_kwargs: {
            "benchmark_readiness": "ready",
            "bucket_fit": "correct",
            "focus_clarity": "clear",
            "excerpt_integrity": "strong",
            "review__action": "keep",
            "review__confidence": "high",
            "review__problem_types": ["other"],
            "review__revised_bucket": "",
            "review__revised_selection_reason": "",
            "review__revised_judge_focus": "",
            "review__notes": "Benchmark-ready.",
        },
    )
    monkeypatch.setattr(
        auto_review_packet,
        "resolve_worker_policy",
        lambda **_kwargs: JobConcurrencyPolicy(
            job_kind="packet_adjudication",
            profile_id="dataset_review_high_trust",
            task_count=1,
            llm_budget=1,
            per_worker_parallelism=1,
            worker_count=1,
        ),
    )
    monkeypatch.setattr(auto_review_packet, "llm_invocation_scope", lambda **_kwargs: nullcontext())

    before_csv = (packet_dir / "cases.review.csv").read_text(encoding="utf-8")
    exit_code = auto_review_packet.main(["--packet-dir", str(packet_dir), "--probe-only", "--max-workers", "1"])

    assert exit_code == 0
    assert (packet_dir / "llm_review_summary.json").exists() is False
    assert (packet_dir / "llm_review_report.md").exists() is False
    assert (packet_dir / "cases.review.csv").read_text(encoding="utf-8") == before_csv

    run_dirs = sorted((packet_dir / "llm_review_runs").iterdir())
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert (run_dir / "summary.json").exists()
    assert (run_dir / "report.md").exists()
    assert manifest["adjudication_input_fingerprint"] == summary["adjudication_input_fingerprint"]
    assert manifest["run_dir"] == str(run_dir)
    case_payload = json.loads((run_dir / "cases" / "demo_case.json").read_text(encoding="utf-8"))
    assert case_payload["normalized_review"]["review__action"] == "keep"
    assert case_payload["adjudication_input_fingerprint"]


def test_compare_adjudication_runs_detects_action_drift_for_identical_inputs(tmp_path: Path) -> None:
    run_dir_a = tmp_path / "run_a"
    run_dir_b = tmp_path / "run_b"
    _write_compare_run(run_dir_a, action="keep", confidence="high")
    _write_compare_run(run_dir_b, action="revise", confidence="medium")
    (run_dir_a / "llm_traces").mkdir(parents=True, exist_ok=True)
    (run_dir_b / "llm_traces").mkdir(parents=True, exist_ok=True)
    (run_dir_a / "llm_traces" / "standard.jsonl").write_text("", encoding="utf-8")
    (run_dir_b / "llm_traces" / "standard.jsonl").write_text("", encoding="utf-8")

    payload = compare_adjudication_runs(run_dir_a, run_dir_b)

    assert payload["same_packet_input_fingerprint"] is True
    assert payload["drift_counts"]["action_drift"] == 1
    assert payload["drift_counts"]["confidence_drift"] == 1
    assert payload["drift_counts"]["source_input_drift"] == 0
    assert payload["drift_counts"]["audit_input_drift"] == 0
    assert payload["case_diffs"][0]["same_input_fingerprint"] is True
    assert payload["case_diffs"][0]["same_source_row_fingerprint"] is True
    assert payload["case_diffs"][0]["same_audit_row_fingerprint"] is True
    assert payload["case_diffs"][0]["action_a"] == "keep"
    assert payload["case_diffs"][0]["action_b"] == "revise"


def test_compare_adjudication_runs_reports_routing_drift(tmp_path: Path) -> None:
    run_dir_a = tmp_path / "run_a"
    run_dir_b = tmp_path / "run_b"
    _write_compare_run(run_dir_a, action="keep", confidence="high")
    _write_compare_run(run_dir_b, action="keep", confidence="high")
    (run_dir_a / "llm_traces").mkdir(parents=True, exist_ok=True)
    (run_dir_b / "llm_traces").mkdir(parents=True, exist_ok=True)
    (run_dir_a / "llm_traces" / "standard.jsonl").write_text("", encoding="utf-8")
    (run_dir_b / "llm_traces" / "standard.jsonl").write_text("", encoding="utf-8")
    payload_b = json.loads((run_dir_b / "cases" / "demo_case.json").read_text(encoding="utf-8"))
    payload_b["provider_id"] = "minimax_standard_provider"
    payload_b["selected_target_id"] = "minimax_m27_standard"
    payload_b["selected_tier_id"] = "backup"
    payload_b["key_slot_id"] = "standard_primary"
    payload_b["model"] = "MiniMax-M2.7"
    _write_json(run_dir_b / "cases" / "demo_case.json", payload_b)

    payload = compare_adjudication_runs(run_dir_a, run_dir_b)

    assert payload["drift_counts"]["routing_drift"] == 1
    assert payload["case_diffs"][0]["routing_drift"] is True
    assert payload["case_diffs"][0]["target_a"] == "minimax_m27_highspeed"
    assert payload["case_diffs"][0]["target_b"] == "minimax_m27_standard"
    assert payload["case_diffs"][0]["model_a"] == "MiniMax-M2.7-highspeed"
    assert payload["case_diffs"][0]["model_b"] == "MiniMax-M2.7"


def test_compare_adjudication_runs_reports_audit_input_drift_separately(tmp_path: Path) -> None:
    run_dir_a = tmp_path / "run_a"
    run_dir_b = tmp_path / "run_b"
    _write_compare_run(
        run_dir_a,
        action="keep",
        confidence="high",
        packet_fingerprint="packet-a",
        case_fingerprint="case-a",
        source_fingerprint="shared-source",
        audit_fingerprint="audit-a",
    )
    _write_compare_run(
        run_dir_b,
        action="keep",
        confidence="high",
        packet_fingerprint="packet-b",
        case_fingerprint="case-b",
        source_fingerprint="shared-source",
        audit_fingerprint="audit-b",
    )
    (run_dir_a / "llm_traces").mkdir(parents=True, exist_ok=True)
    (run_dir_b / "llm_traces").mkdir(parents=True, exist_ok=True)
    (run_dir_a / "llm_traces" / "standard.jsonl").write_text("", encoding="utf-8")
    (run_dir_b / "llm_traces" / "standard.jsonl").write_text("", encoding="utf-8")

    payload = compare_adjudication_runs(run_dir_a, run_dir_b)

    assert payload["same_packet_input_fingerprint"] is False
    assert payload["drift_counts"]["source_input_drift"] == 0
    assert payload["drift_counts"]["audit_input_drift"] == 1
    assert payload["case_diffs"][0]["same_source_row_fingerprint"] is True
    assert payload["case_diffs"][0]["same_audit_row_fingerprint"] is False


def test_compare_legacy_runs_ignores_audit_wrapper_metadata_in_input_fingerprint(
    monkeypatch, tmp_path: Path
) -> None:
    archive_root = tmp_path / "eval" / "review_packets" / "archive"
    monkeypatch.setattr(
        compare_runs,
        "CASE_AUDIT_RUNS_ROOT",
        tmp_path / "eval" / "runs" / "attentional_v2" / "case_audits",
    )
    packet_dir_a = archive_root / "packet_a"
    packet_dir_b = archive_root / "packet_b"
    _write_legacy_compare_packet(
        packet_dir_a,
        packet_id="packet_a",
        audit_run_id="audit_run_a",
        action="keep",
        confidence="high",
        timing_offset=0,
    )
    _write_legacy_compare_packet(
        packet_dir_b,
        packet_id="packet_b",
        audit_run_id="audit_run_b",
        action="keep",
        confidence="high",
        timing_offset=99,
    )

    payload = compare_adjudication_runs(packet_dir_a, packet_dir_b)

    assert payload["same_packet_input_fingerprint"] is True
    assert payload["case_diffs"][0]["same_input_fingerprint"] is True
    assert payload["case_diffs"][0]["same_audit_row_fingerprint"] is True
    assert payload["drift_counts"]["action_drift"] == 0
    assert payload["drift_counts"]["audit_input_drift"] == 0

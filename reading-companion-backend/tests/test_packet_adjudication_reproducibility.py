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


def _write_packet(packet_dir: Path, *, packet_id: str = "demo_packet") -> None:
    _write_json(
        packet_dir / "packet_manifest.json",
        {
            "packet_id": packet_id,
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


def _write_saved_probe_input_run(
    packet_dir: Path,
    *,
    run_id: str,
    case_excerpt: str,
    problem_types: list[str] | None = None,
) -> None:
    saved_input_payload = {
        "review_policy": auto_review_packet.REVIEW_POLICY,
        "adjudication_contract_version": auto_review_packet.ADJUDICATION_CONTRACT_VERSION,
        "case": {
            "case_id": "demo_case",
            "book_title": "Frozen Book",
            "author": "Frozen Author",
            "chapter_id": "1",
            "chapter_title": "Frozen Chapter",
            "question_ids": ["Q1"],
            "phenomena": ["focus"],
            "selection_reason": "Frozen selection reason.",
            "judge_focus": "Frozen judge focus.",
            "excerpt_text": case_excerpt,
        },
        "audit_prompt_inputs": {
            "factual_audit": {"ok": True, "issues": []},
            "primary_review": {
                "decision": "revise",
                "problem_types": problem_types or ["weak_excerpt"],
                "bucket_fit_band": "adequate",
                "focus_clarity_band": "adequate",
                "excerpt_strength_band": "weak",
            },
            "adversarial_review": {
                "has_high_risk": False,
                "suspected_problem_types": [],
            },
        },
        "system_prompt_hash": "saved-system",
        "user_prompt_hash": "saved-user",
    }
    _write_json(
        packet_dir / "llm_review_runs" / run_id / "cases" / "demo_case.json",
        {
            "case_id": "demo_case",
            "input_payload": saved_input_payload,
            "adjudication_input_fingerprint": auto_review_packet._fingerprint(saved_input_payload),
            "source_row_fingerprint": auto_review_packet._fingerprint(saved_input_payload["case"]),
            "audit_row_fingerprint": auto_review_packet._fingerprint(saved_input_payload["audit_prompt_inputs"]),
            "normalized_review": {
                "review__action": "revise",
                "review__confidence": "medium",
                "review__problem_types": problem_types or ["weak_excerpt"],
            },
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


def test_probe_only_shortens_review_run_storage_id_for_long_packet_ids(monkeypatch, tmp_path: Path) -> None:
    packet_dir = tmp_path / "packet"
    audit_run_dir = tmp_path / "audit_run"
    long_packet_id = "attentional_v2_private_library_excerpt_en_question_aligned_v1__scratch__" + ("x" * 220)
    _write_packet(packet_dir, packet_id=long_packet_id)
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

    exit_code = auto_review_packet.main(["--packet-dir", str(packet_dir), "--probe-only", "--max-workers", "1"])

    assert exit_code == 0
    run_dirs = sorted((packet_dir / "llm_review_runs").iterdir())
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]
    assert run_dir.name.startswith("llm_review__")
    assert len(run_dir.name) < len(long_packet_id)
    assert len(run_dir.name) < 128
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["packet_id"] == long_packet_id
    assert summary["run_id"] == run_dir.name


def test_probe_only_reuses_saved_input_payload_from_prior_review_run(monkeypatch, tmp_path: Path) -> None:
    packet_dir = tmp_path / "packet"
    audit_run_dir = tmp_path / "audit_run"
    _write_packet(packet_dir)
    _write_completed_audit(audit_run_dir)
    prior_run_id = "llm_review__20260330-120000__savedprobe"
    _write_json(
        packet_dir / "packet_manifest.json",
        {
            "packet_id": "demo_packet",
            "dataset_id": "demo_dataset",
            "llm_review_run_id": prior_run_id,
            "llm_review_run_dir": str(packet_dir / "llm_review_runs" / prior_run_id),
        },
    )
    _write_saved_probe_input_run(
        packet_dir,
        run_id=prior_run_id,
        case_excerpt="Frozen excerpt from saved run.",
        problem_types=["ambiguous_focus"],
    )

    monkeypatch.setattr(
        auto_review_packet,
        "find_latest_case_audit_run",
        lambda *_args, **_kwargs: {"run_dir": str(audit_run_dir)},
    )
    monkeypatch.setattr(
        auto_review_packet,
        "invoke_json",
        lambda system_prompt, user_prompt, **_kwargs: {
            "benchmark_readiness": "ready"
            if "Frozen excerpt from saved run." in user_prompt
            else "reject",
            "bucket_fit": "correct",
            "focus_clarity": "clear",
            "excerpt_integrity": "strong",
            "review__action": "keep" if "Frozen excerpt from saved run." in user_prompt else "drop",
            "review__confidence": "high" if "Frozen excerpt from saved run." in user_prompt else "low",
            "review__problem_types": ["other"] if "Frozen excerpt from saved run." in user_prompt else ["weak_excerpt"],
            "review__revised_bucket": "",
            "review__revised_selection_reason": "",
            "review__revised_judge_focus": "",
            "review__notes": user_prompt,
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

    exit_code = auto_review_packet.main(["--packet-dir", str(packet_dir), "--probe-only", "--max-workers", "1"])

    assert exit_code == 0
    run_dirs = sorted((packet_dir / "llm_review_runs").iterdir())
    assert len(run_dirs) == 2
    new_run_dir = [run_dir for run_dir in run_dirs if run_dir.name != prior_run_id][0]
    summary = json.loads((new_run_dir / "summary.json").read_text(encoding="utf-8"))
    case_payload = json.loads((new_run_dir / "cases" / "demo_case.json").read_text(encoding="utf-8"))

    assert summary["input_payload_source"] == "reused_prior_run"
    assert summary["reused_input_run_id"] == prior_run_id
    assert case_payload["input_payload"]["case"]["excerpt_text"] == "Frozen excerpt from saved run."
    assert case_payload["input_payload"]["review_policy"] == auto_review_packet.REVIEW_POLICY
    assert (
        case_payload["input_payload"]["adjudication_contract_version"]
        == auto_review_packet.ADJUDICATION_CONTRACT_VERSION
    )
    assert case_payload["normalized_review"]["review__action"] == "keep"
    assert (
        case_payload["adjudication_input_fingerprint"]
        == auto_review_packet._fingerprint(case_payload["input_payload"])
    )


def test_probe_only_retries_quota_failed_cases_before_finalizing(monkeypatch, tmp_path: Path) -> None:
    packet_dir = tmp_path / "packet"
    audit_run_dir = tmp_path / "audit_run"
    _write_packet(packet_dir)
    _write_completed_audit(audit_run_dir)

    call_counts = {"demo_case": 0}

    def fake_adjudicate_review_row(row, **_kwargs):
        case_id = row["case_id"]
        call_counts[case_id] += 1
        if call_counts[case_id] == 1:
            return {
                "case_id": case_id,
                "normalized_review": auto_review_packet.default_review(),
                "adjudication_input_fingerprint": "demo-fingerprint",
                "source_row_fingerprint": "demo-source",
                "audit_row_fingerprint": "demo-audit",
                "input_payload": {"case": {"case_id": case_id}},
                "error": {
                    "status": "reader_llm_error",
                    "error_type": "ReaderLLMError",
                    "error_message": "Provider demo quota cooldown remains active for 60.0s but only 0.0s of quota wait budget remain.",
                },
            }
        return {
            "case_id": case_id,
            "normalized_review": {
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
                "review__notes": "Recovered after quota retry.",
            },
            "adjudication_input_fingerprint": "demo-fingerprint",
            "source_row_fingerprint": "demo-source",
            "audit_row_fingerprint": "demo-audit",
            "input_payload": {"case": {"case_id": case_id}},
            "error": {
                "status": "ok",
                "error_type": "",
                "error_message": "",
            },
        }

    monkeypatch.setattr(
        auto_review_packet,
        "find_latest_case_audit_run",
        lambda *_args, **_kwargs: {"run_dir": str(audit_run_dir)},
    )
    monkeypatch.setattr(auto_review_packet, "adjudicate_review_row", fake_adjudicate_review_row)
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

    exit_code = auto_review_packet.main(["--packet-dir", str(packet_dir), "--probe-only", "--max-workers", "1"])

    assert exit_code == 0
    run_dirs = sorted((packet_dir / "llm_review_runs").iterdir())
    assert len(run_dirs) == 1
    summary = json.loads((run_dirs[0] / "summary.json").read_text(encoding="utf-8"))
    case_payload = json.loads((run_dirs[0] / "cases" / "demo_case.json").read_text(encoding="utf-8"))
    assert call_counts["demo_case"] == 2
    assert summary["quota_recovery_attempted_count"] == 1
    assert summary["quota_recovery_succeeded_count"] == 1
    assert summary["quota_failure_remaining_count"] == 0
    assert case_payload["normalized_review"]["review__action"] == "keep"


def test_long_packet_id_uses_short_review_run_storage_id(monkeypatch, tmp_path: Path) -> None:
    packet_id = (
        "attentional_v2_private_library_excerpt_en_question_aligned_v1__scratch__"
        "closed_loop_full_smoke_en_broader_compactadjudication_repeat_20260330__"
        "initial_review__closed_loop_full_smoke_en_broader_compactadjudication_repeat_20260330"
    )
    packet_dir = tmp_path / packet_id
    audit_run_dir = tmp_path / "audit_run"
    _write_packet(packet_dir)
    _write_json(
        packet_dir / "packet_manifest.json",
        {
            "packet_id": packet_id,
            "dataset_id": "demo_dataset",
        },
    )
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

    exit_code = auto_review_packet.main(["--packet-dir", str(packet_dir), "--probe-only", "--max-workers", "1"])

    assert exit_code == 0
    run_dirs = sorted((packet_dir / "llm_review_runs").iterdir())
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]
    assert len(run_dir.name) < 255
    assert run_dir.name.startswith("llm_review__")
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["run_id"] == run_dir.name
    assert summary["packet_id"] == packet_id


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


def test_stable_audit_prompt_inputs_ignore_free_text_only_drift() -> None:
    audit_row_a = {
        "status": "completed",
        "factual_audit": {"ok": True, "issues": []},
        "primary_review": {
            "decision": "revise",
            "confidence": "medium",
            "problem_types": ["weak_excerpt"],
            "bucket_fit": 4,
            "focus_clarity": 3,
            "excerpt_strength": 2,
            "revised_bucket": "callback_bridge",
            "revised_selection_reason": "Needs more bridge context.",
            "revised_judge_focus": "Trace the earlier vow precisely.",
            "notes": "Version A prose.",
        },
        "adversarial_review": {
            "risk_level": "medium",
            "suspected_problem_types": ["weak_excerpt"],
            "alternative_bucket": "callback_bridge",
            "challenge_summary": "Version A summary.",
            "notes": "Version A notes.",
        },
    }
    audit_row_b = {
        **audit_row_a,
        "primary_review": {
            **audit_row_a["primary_review"],
            "revised_selection_reason": "Version B wording only.",
            "revised_judge_focus": "Version B wording only.",
            "notes": "Version B prose.",
        },
        "adversarial_review": {
            **audit_row_a["adversarial_review"],
            "challenge_summary": "Version B summary.",
            "notes": "Version B notes.",
        },
    }

    assert (
        auto_review_packet._fingerprint(auto_review_packet._stable_audit_prompt_inputs(audit_row_a))
        == auto_review_packet._fingerprint(auto_review_packet._stable_audit_prompt_inputs(audit_row_b))
    )


def test_stable_audit_prompt_inputs_ignore_non_high_adversarial_label_jitter() -> None:
    audit_row_a = {
        "status": "completed",
        "factual_audit": {"ok": True, "issues": []},
        "primary_review": {
            "decision": "revise",
            "confidence": "high",
            "problem_types": ["weak_excerpt"],
            "bucket_fit": 4,
            "focus_clarity": 3,
            "excerpt_strength": 3,
            "revised_bucket": "callback_bridge",
        },
        "adversarial_review": {
            "risk_level": "low",
            "suspected_problem_types": ["too_easy"],
            "alternative_bucket": "generic_passage",
            "challenge_summary": "Version A summary.",
        },
    }
    audit_row_b = {
        **audit_row_a,
        "primary_review": {
            **audit_row_a["primary_review"],
            "confidence": "medium",
            "revised_bucket": "cross_span_link",
        },
        "adversarial_review": {
            **audit_row_a["adversarial_review"],
            "risk_level": "medium",
            "suspected_problem_types": ["ambiguous_focus", "weak_excerpt"],
            "alternative_bucket": "callback_bridge",
            "challenge_summary": "Version B summary.",
        },
    }

    assert (
        auto_review_packet._fingerprint(auto_review_packet._stable_audit_prompt_inputs(audit_row_a))
        == auto_review_packet._fingerprint(auto_review_packet._stable_audit_prompt_inputs(audit_row_b))
    )


def test_normalize_saved_input_payload_recomputes_current_contract_hashes() -> None:
    saved_payload = {
        "review_policy": "old_review_policy",
        "adjudication_contract_version": "old_contract_version",
        "case": {
            "case_id": "demo_case",
            "book_title": "Demo Book",
            "author": "Demo Author",
            "chapter_id": "1",
            "chapter_title": "Demo Chapter",
            "question_ids": ["Q1"],
            "phenomena": ["focus"],
            "selection_reason": "Frozen selection reason.",
            "judge_focus": "Frozen judge focus.",
            "excerpt_text": "Frozen excerpt.",
        },
        "audit_prompt_inputs": {
            "factual_audit": {"ok": True, "issues": []},
            "primary_review": {
                "decision": "keep",
                "problem_types": [],
                "bucket_fit_band": "strong",
                "focus_clarity_band": "strong",
                "excerpt_strength_band": "strong",
            },
            "adversarial_review": {
                "has_high_risk": False,
                "suspected_problem_types": [],
            },
        },
        "system_prompt_hash": "saved-system",
        "user_prompt_hash": "saved-user",
    }

    normalized = auto_review_packet._normalize_saved_input_payload(saved_payload)
    expected_prompt = auto_review_packet._review_prompt_from_inputs(
        saved_payload["case"],
        saved_payload["audit_prompt_inputs"],
    )

    assert normalized["review_policy"] == auto_review_packet.REVIEW_POLICY
    assert (
        normalized["adjudication_contract_version"]
        == auto_review_packet.ADJUDICATION_CONTRACT_VERSION
    )
    assert normalized["system_prompt_hash"] == auto_review_packet._prompt_hash(auto_review_packet.SYSTEM)
    assert normalized["user_prompt_hash"] == auto_review_packet._prompt_hash(expected_prompt)


def test_case_prompt_inputs_ignore_workflow_only_metadata_drift() -> None:
    case_a = {
        "case_id": "demo_case",
        "case_title": "Demo / callback bridge",
        "book_title": "Demo Book",
        "author": "Demo Author",
        "chapter_id": "1",
        "chapter_title": "Chapter One",
        "target_profile_id": "callback_bridge",
        "selection_role": "argumentative",
        "question_ids": ["Q1"],
        "phenomena": ["callback_bridge"],
        "role_tags": ["argumentative"],
        "type_tags": ["essay"],
        "selection_reason": "Strong bridge move.",
        "judge_focus": "Does the callback stay explicit?",
        "excerpt_text": "Demo excerpt.",
        "benchmark_status": "unset",
        "curation_status": "question_aligned_builder_seed_v1",
        "construction_priority": 9.7,
        "discriminative_power_score": 5.0,
        "judgeability_score": 5.0,
        "notes": "Question-aligned seed case built from the managed supplement.",
        "review_history": [],
        "review_status": "builder_curated",
        "source_policy": "private-local-source",
        "split": "private_library_seed_v2",
        "replacement_family_id": "demo::family",
        "reserve_group_id": "demo::group",
        "opportunity_id": "demo::opp",
    }
    case_b = {
        **case_a,
        "benchmark_status": "needs_revision",
        "curation_status": "post_review_seed_v2",
        "construction_priority": 1.2,
        "discriminative_power_score": 1.0,
        "judgeability_score": 2.0,
        "notes": "Now with different workflow-only notes.",
        "review_history": [{"status": "revise"}],
        "review_status": "reviewed",
        "source_policy": "another-policy",
        "split": "another_split",
        "replacement_family_id": "other::family",
        "reserve_group_id": "other::group",
        "opportunity_id": "other::opp",
    }

    assert auto_review_packet._case_prompt_inputs(case_a) == auto_review_packet._case_prompt_inputs(case_b)


def test_adjudication_precedence_prefers_clean_strong_low_risk_keep() -> None:
    normalized = auto_review_packet._apply_adjudication_precedence(
        auto_review_packet.normalize_review(
            {
                "benchmark_readiness": "revise",
                "bucket_fit": "correct",
                "focus_clarity": "clear",
                "excerpt_integrity": "strong",
                "review__action": "revise",
                "review__confidence": "low",
                "review__problem_types": ["other"],
                "review__notes": "The case still needs benchmark hardening.",
            }
        ),
        case={"target_profile_id": "callback_bridge"},
        audit_inputs={
            "factual_audit": {"ok": True, "issues": []},
            "primary_review": {
                "decision": "keep",
                "problem_types": [],
                "bucket_fit_band": "strong",
                "focus_clarity_band": "strong",
                "excerpt_strength_band": "strong",
            },
            "adversarial_review": {
                "has_high_risk": False,
                "suspected_problem_types": [],
            },
        },
    )

    assert normalized["benchmark_readiness"] == "ready"
    assert normalized["review__action"] == "keep"
    assert normalized["review__confidence"] == "medium"
    assert normalized["review__problem_types"] == ["other"]
    assert "Resolved in favor of keep" in normalized["review__notes"]


def test_adjudication_precedence_prefers_revise_for_broad_callback_bridge_keep() -> None:
    normalized = auto_review_packet._apply_adjudication_precedence(
        auto_review_packet.normalize_review(
            {
                "benchmark_readiness": "ready",
                "bucket_fit": "correct",
                "focus_clarity": "clear",
                "excerpt_integrity": "strong",
                "review__action": "keep",
                "review__confidence": "high",
                "review__problem_types": ["other"],
                "review__notes": "The callback looks acceptable.",
            }
        ),
        case={"target_profile_id": "callback_bridge"},
        audit_inputs={
            "factual_audit": {"ok": True, "issues": []},
            "primary_review": {
                "decision": "revise",
                "problem_types": ["ambiguous_focus", "weak_excerpt"],
                "bucket_fit_band": "adequate",
                "focus_clarity_band": "adequate",
                "excerpt_strength_band": "adequate",
            },
            "adversarial_review": {
                "has_high_risk": False,
                "suspected_problem_types": [],
            },
        },
    )

    assert normalized["benchmark_readiness"] == "revise"
    assert normalized["review__action"] == "revise"
    assert normalized["review__confidence"] == "medium"
    assert normalized["review__problem_types"] == ["ambiguous_focus", "weak_excerpt"]
    assert "Resolved in favor of revise" in normalized["review__notes"]


def test_adjudicate_review_row_rejects_placeholder_audit_rows(tmp_path: Path) -> None:
    audit_dir = tmp_path / "audit" / "cases"
    source_rows = {"demo_case": {"case_id": "demo_case"}}
    _write_json(
        audit_dir / "demo_case.json",
        {
            "case_id": "demo_case",
            "status": "completed",
            "factual_audit": {"ok": True, "issues": []},
            "primary_review": {
                "decision": "unclear",
                "confidence": "low",
                "problem_types": ["other"],
                "bucket_fit": 0,
                "focus_clarity": 0,
                "excerpt_strength": 0,
                "revised_bucket": "",
                "revised_selection_reason": "",
                "revised_judge_focus": "",
                "notes": "review_unavailable",
            },
            "adversarial_review": {
                "risk_level": "medium",
                "suspected_problem_types": ["other"],
                "alternative_bucket": "",
                "challenge_summary": "adversarial_review_unavailable",
                "notes": "",
            },
        },
    )

    try:
        auto_review_packet.adjudicate_review_row(
            {"case_id": "demo_case"},
            source_rows=source_rows,
            audit_cases_dir=audit_dir,
            standard_trace_path=tmp_path / "standard.jsonl",
            source_case_audit_run_id="audit_run_demo",
        )
    except ValueError as exc:
        assert "not usable for adjudication" in str(exc)
    else:  # pragma: no cover - explicit failure path
        raise AssertionError("Expected placeholder audit rows to be rejected")

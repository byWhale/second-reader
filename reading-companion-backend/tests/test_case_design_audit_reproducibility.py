from __future__ import annotations

import json
from pathlib import Path

from eval.attentional_v2 import run_case_design_audit as audit
from eval.attentional_v2.compare_case_audit_runs import compare_case_audit_runs


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_case_audit_run(
    run_dir: Path,
    *,
    case_id: str = "demo_case",
    primary_decision: str = "keep",
    adversarial_risk: str = "low",
    factual_ok: bool = True,
    factual_issues: list[str] | None = None,
    input_payload: dict[str, object] | None = None,
) -> None:
    factual_issues = factual_issues or []
    prompt_case = {
        "case_id": case_id,
        "case_title": "Demo case",
        "question_ids": ["q1"],
        "phenomena": ["callback"],
        "selection_reason": "Track the callback.",
        "judge_focus": "Check whether the bridge stays grounded.",
        "excerpt_text": "Anchor.\nFollow-up.",
    }
    context = {
        "lookback_sentences": ["Earlier setup."],
        "excerpt_sentences": ["Anchor.", "Follow-up."],
        "lookahead_sentences": ["Later consequence."],
    }
    normalized_input_payload = input_payload or audit.build_audit_prompt_input_payload(prompt_case, context)
    case_payload = {
        "case_id": case_id,
        "packet_id": "demo_packet",
        "status": "completed",
        "factual_audit": {
            "ok": factual_ok,
            "issues": factual_issues,
        },
        "primary_review": {
            "decision": primary_decision,
            "confidence": "high",
            "problem_types": [] if primary_decision == "keep" else ["weak_excerpt"],
            "bucket_fit": 5 if primary_decision == "keep" else 3,
            "focus_clarity": 5 if primary_decision == "keep" else 3,
            "excerpt_strength": 5 if primary_decision == "keep" else 2,
            "revised_bucket": "",
            "revised_selection_reason": "",
            "revised_judge_focus": "",
            "notes": "Fixture payload.",
        },
        "adversarial_review": {
            "risk_level": adversarial_risk,
            "suspected_problem_types": [] if adversarial_risk == "low" else ["weak_excerpt"],
            "alternative_bucket": "",
            "challenge_summary": "Fixture challenge summary.",
            "notes": "",
        },
        "audit_prompt_input_payload": normalized_input_payload,
        "audit_prompt_input_fingerprint": audit._fingerprint(normalized_input_payload),
    }
    summary = {
        "status": "completed",
        "case_count": 1,
        "completed_case_count": 1,
        "failed_case_count": 0,
        "incomplete_case_count": 0,
        "factual_failure_count": 0 if factual_ok else 1,
        "primary_decisions": {primary_decision: 1},
        "adversarial_risk_counts": {adversarial_risk: 1},
        "average_bucket_fit": float(case_payload["primary_review"]["bucket_fit"]),
        "average_focus_clarity": float(case_payload["primary_review"]["focus_clarity"]),
        "average_excerpt_strength": float(case_payload["primary_review"]["excerpt_strength"]),
        "audit_prompt_contract_version": audit.AUDIT_PROMPT_CONTRACT_VERSION,
        "case_input_fingerprints": {
            case_id: case_payload["audit_prompt_input_fingerprint"],
        },
        "run_audit_prompt_input_fingerprint": audit.audit_run_input_fingerprint(
            {case_id: case_payload["audit_prompt_input_fingerprint"]}
        ),
    }
    _write_json(
        run_dir / "run_state.json",
        {
            "packet_id": "demo_packet",
            "run_id": run_dir.name,
            "status": "completed",
            "case_count": 1,
            "completed_case_count": 1,
            "failed_case_count": 0,
        },
    )
    _write_json(run_dir / "summary" / "aggregate.json", summary)
    _write_json(run_dir / "cases" / f"{case_id}.json", case_payload)


def test_build_audit_prompt_input_payload_ignores_non_prompt_case_fields() -> None:
    case_a = {
        "case_id": "demo_case",
        "case_title": "Demo case",
        "question_ids": ["q1"],
        "phenomena": ["callback"],
        "selection_reason": "Track the callback.",
        "judge_focus": "Check whether the bridge stays grounded.",
        "excerpt_text": "Anchor.\nFollow-up.",
        "debug_only_note": "Version A",
    }
    case_b = {
        **case_a,
        "debug_only_note": "Version B",
        "arbitrary_runtime_metadata": {"attempt": 2},
    }
    context = {
        "lookback_sentences": ["Earlier setup."],
        "excerpt_sentences": ["Anchor.", "Follow-up."],
        "lookahead_sentences": ["Later consequence."],
    }

    payload_a = audit.build_audit_prompt_input_payload(case_a, context)
    payload_b = audit.build_audit_prompt_input_payload(case_b, context)

    assert payload_a == payload_b
    assert payload_a["audit_prompt_contract_version"] == audit.AUDIT_PROMPT_CONTRACT_VERSION
    assert payload_a["prompt_hashes"]["primary_user_prompt_hash"]
    assert payload_a["prompt_hashes"]["adversarial_user_prompt_hash"]
    assert audit._fingerprint(payload_a) == audit._fingerprint(payload_b)


def test_compare_case_audit_runs_counts_same_input_output_drift(tmp_path: Path) -> None:
    run_dir_a = tmp_path / "run_a"
    run_dir_b = tmp_path / "run_b"
    shared_payload = audit.build_audit_prompt_input_payload(
        {
            "case_id": "demo_case",
            "case_title": "Demo case",
            "question_ids": ["q1"],
            "phenomena": ["callback"],
            "selection_reason": "Track the callback.",
            "judge_focus": "Check whether the bridge stays grounded.",
            "excerpt_text": "Anchor.\nFollow-up.",
        },
        {
            "lookback_sentences": ["Earlier setup."],
            "excerpt_sentences": ["Anchor.", "Follow-up."],
            "lookahead_sentences": ["Later consequence."],
        },
    )
    _write_case_audit_run(
        run_dir_a,
        primary_decision="keep",
        adversarial_risk="low",
        input_payload=shared_payload,
    )
    _write_case_audit_run(
        run_dir_b,
        primary_decision="revise",
        adversarial_risk="high",
        input_payload=shared_payload,
    )

    payload = compare_case_audit_runs(run_dir_a, run_dir_b)

    assert payload["same_run_input_fingerprint"] is True
    assert payload["drift_counts"]["input_drift"] == 0
    assert payload["drift_counts"]["primary_decision_drift"] == 1
    assert payload["drift_counts"]["adversarial_risk_drift"] == 1
    assert payload["drift_counts"]["factual_drift"] == 0
    assert payload["case_diffs"][0]["same_input_fingerprint"] is True
    assert payload["case_diffs"][0]["primary_decision_a"] == "keep"
    assert payload["case_diffs"][0]["primary_decision_b"] == "revise"


def test_compare_case_audit_runs_separates_context_input_drift(tmp_path: Path) -> None:
    run_dir_a = tmp_path / "run_a"
    run_dir_b = tmp_path / "run_b"
    base_case = {
        "case_id": "demo_case",
        "case_title": "Demo case",
        "question_ids": ["q1"],
        "phenomena": ["callback"],
        "selection_reason": "Track the callback.",
        "judge_focus": "Check whether the bridge stays grounded.",
        "excerpt_text": "Anchor.\nFollow-up.",
    }
    payload_a = audit.build_audit_prompt_input_payload(
        base_case,
        {
            "lookback_sentences": ["Earlier setup."],
            "excerpt_sentences": ["Anchor.", "Follow-up."],
            "lookahead_sentences": ["Later consequence."],
        },
    )
    payload_b = audit.build_audit_prompt_input_payload(
        base_case,
        {
            "lookback_sentences": ["Different setup."],
            "excerpt_sentences": ["Anchor.", "Follow-up."],
            "lookahead_sentences": ["Later consequence."],
        },
    )
    _write_case_audit_run(run_dir_a, input_payload=payload_a)
    _write_case_audit_run(run_dir_b, input_payload=payload_b)

    payload = compare_case_audit_runs(run_dir_a, run_dir_b)

    assert payload["same_run_input_fingerprint"] is False
    assert payload["drift_counts"]["input_drift"] == 1
    assert payload["drift_counts"]["case_input_drift"] == 0
    assert payload["drift_counts"]["context_input_drift"] == 1
    assert payload["drift_counts"]["prompt_drift"] == 1
    assert payload["case_diffs"][0]["same_case_input_fingerprint"] is True
    assert payload["case_diffs"][0]["same_context_input_fingerprint"] is False

from __future__ import annotations

from contextlib import nullcontext
import json
from pathlib import Path

import pytest

from eval.attentional_v2 import run_case_design_audit as audit
from eval.attentional_v2.compare_case_audit_runs import compare_case_audit_runs
from eval.attentional_v2.run_case_design_audit import PRIMARY_PROMPT, normalize_primary


def test_primary_prompt_defines_score_scale() -> None:
    assert "use `strong|adequate|weak`" in PRIMARY_PROMPT
    assert "`keep` means no axis is `weak` and at most one axis is `adequate`" in PRIMARY_PROMPT


def test_primary_prompt_allows_inline_callback_antecedent_when_traceable() -> None:
    assert "it is acceptable for the earlier bridge target to appear inside the excerpt" in PRIMARY_PROMPT
    assert "if the supposed callback is only broad thematic continuation" in PRIMARY_PROMPT


def test_adversarial_prompt_does_not_auto_reject_inline_callback_targets() -> None:
    assert "do not treat an inline earlier bridge target as a defect by itself" in audit.ADVERSARIAL_PROMPT


def test_normalize_primary_repairs_keep_score_inconsistency() -> None:
    normalized = normalize_primary(
        {
            "decision": "keep",
            "confidence": "high",
            "bucket_fit": 1,
            "focus_clarity": 1,
            "excerpt_strength": 1,
            "problem_types": ["ambiguous_focus"],
            "revised_bucket": "callback",
            "revised_selection_reason": "stale",
            "revised_judge_focus": "stale",
            "notes": "This is a strong benchmark case.",
        }
    )

    assert normalized["decision"] == "keep"
    assert normalized["bucket_fit"] == 4
    assert normalized["focus_clarity"] == 4
    assert normalized["excerpt_strength"] == 4
    assert normalized["problem_types"] == []
    assert normalized["revised_bucket"] == ""
    assert normalized["revised_selection_reason"] == ""
    assert normalized["revised_judge_focus"] == ""


def test_normalize_primary_preserves_revise_payload() -> None:
    normalized = normalize_primary(
        {
            "decision": "revise",
            "confidence": "medium",
            "bucket_fit": 2,
            "focus_clarity": 1,
            "excerpt_strength": 3,
            "problem_types": ["weak_excerpt", "ambiguous_focus"],
            "revised_bucket": "callback",
            "revised_selection_reason": "Needs more bridge context.",
            "revised_judge_focus": "Trace the backward link carefully.",
            "notes": "Promising but not benchmark-ready.",
        }
    )

    assert normalized["decision"] == "revise"
    assert normalized["bucket_fit"] == 2
    assert normalized["focus_clarity"] == 2
    assert normalized["excerpt_strength"] == 3
    assert normalized["problem_types"] == ["weak_excerpt", "ambiguous_focus"]
    assert normalized["revised_bucket"] == "callback"


def test_normalize_primary_maps_band_fields_to_canonical_scores() -> None:
    normalized = normalize_primary(
        {
            "decision": "revise",
            "confidence": "medium",
            "bucket_fit_band": "strong",
            "focus_clarity_band": "adequate",
            "excerpt_strength_band": "weak",
            "problem_types": ["weak_excerpt", "ambiguous_focus"],
            "notes": "Borderline but promising.",
        }
    )

    assert normalized["decision"] == "revise"
    assert normalized["bucket_fit"] == 4
    assert normalized["focus_clarity"] == 3
    assert normalized["excerpt_strength"] == 2
    assert normalized["problem_types"] == ["weak_excerpt", "ambiguous_focus"]


def test_normalize_primary_promotes_single_adequate_case_to_keep() -> None:
    normalized = normalize_primary(
        {
            "decision": "revise",
            "confidence": "medium",
            "bucket_fit_band": "strong",
            "focus_clarity_band": "adequate",
            "excerpt_strength_band": "strong",
            "problem_types": ["ambiguous_focus"],
            "notes": "Only one axis is slightly soft.",
        }
    )

    assert normalized["decision"] == "keep"
    assert normalized["bucket_fit"] == 4
    assert normalized["focus_clarity"] == 4
    assert normalized["excerpt_strength"] == 4
    assert normalized["problem_types"] == []


def test_normalize_primary_demotes_multi_adequate_keep_to_revise() -> None:
    normalized = normalize_primary(
        {
            "decision": "keep",
            "confidence": "high",
            "bucket_fit_band": "adequate",
            "focus_clarity_band": "adequate",
            "excerpt_strength_band": "strong",
            "problem_types": [],
            "notes": "Promising but still broad.",
        }
    )

    assert normalized["decision"] == "revise"
    assert normalized["bucket_fit"] == 3
    assert normalized["focus_clarity"] == 3
    assert normalized["excerpt_strength"] == 4
    assert normalized["problem_types"] == ["other"]


def test_normalize_primary_canonicalizes_problem_types_from_axis_scores() -> None:
    normalized = normalize_primary(
        {
            "decision": "revise",
            "confidence": "medium",
            "bucket_fit_band": "strong",
            "focus_clarity_band": "adequate",
            "excerpt_strength_band": "weak",
            "problem_types": ["ambiguous_focus", "weak_excerpt", "text_noise"],
            "notes": "The excerpt is still too brittle.",
        }
    )

    assert normalized["decision"] == "revise"
    assert normalized["problem_types"] == ["weak_excerpt", "ambiguous_focus", "text_noise"]


def test_summarize_primary_consensus_uses_majority_vote_and_median_scores() -> None:
    consensus, exemplar_index = audit.summarize_primary_consensus(
        [
            {
                "decision": "keep",
                "confidence": "high",
                "bucket_fit": 4,
                "focus_clarity": 4,
                "excerpt_strength": 4,
                "problem_types": [],
                "notes": "Replica 1",
            },
            {
                "decision": "revise",
                "confidence": "medium",
                "bucket_fit": 4,
                "focus_clarity": 3,
                "excerpt_strength": 4,
                "problem_types": ["ambiguous_focus"],
                "notes": "Replica 2",
            },
            {
                "decision": "revise",
                "confidence": "medium",
                "bucket_fit": 4,
                "focus_clarity": 3,
                "excerpt_strength": 4,
                "problem_types": ["ambiguous_focus"],
                "notes": "Replica 3",
            },
        ]
    )

    assert consensus["decision"] == "keep"
    assert consensus["bucket_fit"] == 4
    assert consensus["focus_clarity"] == 4
    assert consensus["excerpt_strength"] == 4
    assert consensus["problem_types"] == []
    assert exemplar_index == 1


def test_summarize_primary_consensus_falls_back_to_exemplar_problem_types() -> None:
    consensus, exemplar_index = audit.summarize_primary_consensus(
        [
            {
                "decision": "revise",
                "confidence": "medium",
                "bucket_fit": 4,
                "focus_clarity": 3,
                "excerpt_strength": 4,
                "problem_types": ["ambiguous_focus"],
                "notes": "Replica 1",
            },
            {
                "decision": "revise",
                "confidence": "medium",
                "bucket_fit": 4,
                "focus_clarity": 4,
                "excerpt_strength": 2,
                "problem_types": ["weak_excerpt"],
                "notes": "Replica 2",
            },
            {
                "decision": "revise",
                "confidence": "medium",
                "bucket_fit": 4,
                "focus_clarity": 3,
                "excerpt_strength": 2,
                "problem_types": ["source_parse_problem"],
                "notes": "Replica 3",
            },
        ]
    )

    assert consensus["decision"] == "revise"
    assert consensus["problem_types"] == ["weak_excerpt"]
    assert exemplar_index == 1


def test_primary_validation_issue_rejects_placeholder_payload() -> None:
    issue = audit.primary_validation_issue(audit.default_primary())

    assert issue == "primary_review_unavailable"


def test_adversarial_validation_issue_rejects_placeholder_payload() -> None:
    issue = audit.adversarial_validation_issue(audit.default_adversarial())

    assert issue == "adversarial_review_unavailable"


def test_invoke_review_with_meta_retries_on_placeholder_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = iter(
        [
            {},
            {
                "decision": "revise",
                "confidence": "medium",
                "bucket_fit": 2,
                "focus_clarity": 2,
                "excerpt_strength": 3,
                "problem_types": ["weak_excerpt"],
                "revised_bucket": "",
                "revised_selection_reason": "",
                "revised_judge_focus": "",
                "notes": "Needs a stronger excerpt window.",
            },
        ]
    )

    monkeypatch.setattr(audit, "invoke_json", lambda *args, **kwargs: next(responses))
    monkeypatch.setattr(audit, "llm_invocation_scope", lambda **kwargs: nullcontext())
    monkeypatch.setattr(audit.time, "sleep", lambda _seconds: None)

    normalized, metadata = audit.invoke_review_with_meta(
        stage_name="primary_review",
        system_prompt="system",
        user_prompt="user",
        default_payload=audit.default_primary(),
        normalize=audit.normalize_primary,
        validation_error=audit.primary_validation_issue,
    )

    assert normalized["decision"] == "revise"
    assert metadata["semantic_attempt_count"] == 2
    assert metadata["semantic_retry_count"] == 1
    assert metadata["validation_issue"] == ""


def test_invoke_review_with_meta_accepts_legitimate_unclear_without_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"count": 0}

    def fake_invoke_json(*args, **kwargs):
        calls["count"] += 1
        return {
            "decision": "unclear",
            "confidence": "low",
            "bucket_fit": 1,
            "focus_clarity": 1,
            "excerpt_strength": 1,
            "problem_types": ["other"],
            "revised_bucket": "",
            "revised_selection_reason": "",
            "revised_judge_focus": "",
            "notes": "The evidence is mixed, but the review is still usable.",
        }

    monkeypatch.setattr(audit, "invoke_json", fake_invoke_json)
    monkeypatch.setattr(audit, "llm_invocation_scope", lambda **kwargs: nullcontext())
    monkeypatch.setattr(audit.time, "sleep", lambda _seconds: None)

    normalized, metadata = audit.invoke_review_with_meta(
        stage_name="primary_review",
        system_prompt="system",
        user_prompt="user",
        default_payload=audit.default_primary(),
        normalize=audit.normalize_primary,
        validation_error=audit.primary_validation_issue,
    )

    assert normalized["decision"] == "unclear"
    assert calls["count"] == 1
    assert metadata["semantic_retry_count"] == 0


def test_invoke_review_with_meta_raises_after_exhausted_placeholder_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(audit, "invoke_json", lambda *args, **kwargs: {})
    monkeypatch.setattr(audit, "llm_invocation_scope", lambda **kwargs: nullcontext())
    monkeypatch.setattr(audit.time, "sleep", lambda _seconds: None)

    with pytest.raises(audit.AuditStageError, match="failed to produce a usable payload"):
        audit.invoke_review_with_meta(
            stage_name="primary_review",
            system_prompt="system",
            user_prompt="user",
            default_payload=audit.default_primary(),
            normalize=audit.normalize_primary,
            validation_error=audit.primary_validation_issue,
        )


def test_process_case_with_quota_recovery_retries_failed_case(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = iter(
        [
            {
                "case_id": "demo_case",
                "status": "failed",
                "error": {
                    "error_type": "AuditStageError",
                    "error_message": "quota cooldown remained active",
                },
                "audit_metadata": {
                    "llm_calls": {
                        "primary_review_replica_1": {
                            "problem_code": "llm_quota",
                            "error_message": "quota cooldown remained active",
                        }
                    }
                },
            },
            {
                "case_id": "demo_case",
                "status": "completed",
                "factual_audit": {"ok": True},
                "primary_review": {
                    "decision": "keep",
                    "bucket_fit": 4,
                    "focus_clarity": 4,
                    "excerpt_strength": 4,
                },
                "adversarial_review": {"risk_level": "low"},
                "audit_metadata": {"llm_calls": {}},
            },
        ]
    )

    monkeypatch.setattr(audit, "process_case", lambda *args, **kwargs: next(rows))
    monkeypatch.setattr(audit.time, "sleep", lambda _seconds: None)

    row = audit.process_case_with_quota_recovery(
        {"case_id": "demo_case"},
        packet_id="demo_packet",
        source_index={},
        run_dir=Path("/tmp/demo"),
        trace_context=audit.LLMTraceContext(),
    )

    assert row["status"] == "completed"
    quota_recovery = row["audit_metadata"]["quota_recovery"]
    assert quota_recovery["quota_recovery_attempted_count"] == 1
    assert quota_recovery["quota_recovery_succeeded_count"] == 1
    assert quota_recovery["quota_failure_remaining_count"] == 0
    assert quota_recovery["quota_recovery_passes_used"] == 1


def test_process_case_with_quota_recovery_records_remaining_quota_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failed_row = {
        "case_id": "demo_case",
        "status": "failed",
        "error": {
            "error_type": "AuditStageError",
            "error_message": "quota cooldown remained active",
        },
        "audit_metadata": {
            "llm_calls": {
                "primary_review_replica_1": {
                    "problem_code": "llm_quota",
                    "error_message": "quota cooldown remained active",
                }
            }
        },
    }
    rows = iter([dict(failed_row), dict(failed_row), dict(failed_row)])

    monkeypatch.setattr(audit, "process_case", lambda *args, **kwargs: next(rows))
    monkeypatch.setattr(audit.time, "sleep", lambda _seconds: None)

    row = audit.process_case_with_quota_recovery(
        {"case_id": "demo_case"},
        packet_id="demo_packet",
        source_index={},
        run_dir=Path("/tmp/demo"),
        trace_context=audit.LLMTraceContext(),
    )

    assert row["status"] == "failed"
    quota_recovery = row["audit_metadata"]["quota_recovery"]
    assert quota_recovery["quota_recovery_attempted_count"] == 1
    assert quota_recovery["quota_recovery_succeeded_count"] == 0
    assert quota_recovery["quota_failure_remaining_count"] == 1
    assert quota_recovery["quota_recovery_passes_used"] == audit.CASE_QUOTA_RECOVERY_PASSES


def test_run_primary_uses_zero_temperature_scope_override(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        audit,
        "invoke_json",
        lambda *args, **kwargs: {
            "decision": "keep",
            "confidence": "high",
            "bucket_fit": 4,
            "focus_clarity": 4,
            "excerpt_strength": 4,
            "problem_types": [],
            "revised_bucket": "",
            "revised_selection_reason": "",
            "revised_judge_focus": "",
            "notes": "Strong case.",
        },
    )

    def fake_scope(**kwargs):
        captured["overrides"] = kwargs.get("overrides")
        return nullcontext()

    monkeypatch.setattr(audit, "llm_invocation_scope", fake_scope)

    primary, metadata = audit.run_primary(
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

    assert primary["decision"] == "keep"
    assert metadata["replica_count"] == audit.PRIMARY_REVIEW_REPLICA_COUNT
    assert metadata["selection_policy"] == audit.PRIMARY_REVIEW_CONSENSUS_POLICY
    overrides = captured["overrides"]
    assert isinstance(overrides, audit.LLMInvocationOverrides)
    assert overrides.temperature == 0.0


def test_run_primary_escalates_inline_callback_cases(monkeypatch: pytest.MonkeyPatch) -> None:
    call_count = {"count": 0}

    def fake_invoke_json(*args, **kwargs):
        call_count["count"] += 1
        return {
            "decision": "keep",
            "confidence": "high",
            "bucket_fit_band": "strong",
            "focus_clarity_band": "strong",
            "excerpt_strength_band": "strong",
            "problem_types": [],
            "revised_bucket": "",
            "revised_selection_reason": "",
            "revised_judge_focus": "",
            "notes": "Traceable inline callback.",
        }

    monkeypatch.setattr(audit, "invoke_json", fake_invoke_json)
    monkeypatch.setattr(audit, "llm_invocation_scope", lambda **kwargs: nullcontext())

    primary, metadata = audit.run_primary(
        {
            "case_id": "demo_case",
            "case_title": "Demo / callback_bridge",
            "target_profile_id": "callback_bridge",
            "selection_role": "argumentative",
            "question_ids": ["q1"],
            "phenomena": ["callback", "cross_span_link"],
            "selection_reason": (
                "Selected because the passage invites a backward bridge or callback that should remain "
                "source-grounded rather than associative. Earlier bridge target: Earlier premise. "
                "Anchor line: From this the later claim follows."
            ),
            "judge_focus": "Can the reader trace the backward bridge honestly?",
            "excerpt_text": "Earlier premise.\nFrom this the later claim follows.",
            "prior_context_sentence_ids": [],
        },
        {
            "lookback_sentences": ["Setup."],
            "excerpt_sentences": ["Earlier premise.", "From this the later claim follows."],
            "lookahead_sentences": ["Implication."],
        },
    )

    assert primary["decision"] == "keep"
    assert metadata["callback_replica_escalation_applied"] is True
    assert metadata["base_replica_count"] == audit.PRIMARY_REVIEW_REPLICA_COUNT
    assert metadata["replica_count"] == (
        audit.PRIMARY_REVIEW_REPLICA_COUNT + audit.PRIMARY_REVIEW_CALLBACK_ESCALATION_REPLICA_COUNT
    )
    assert metadata["selection_policy"] == audit.PRIMARY_REVIEW_CALLBACK_ESCALATION_POLICY
    assert call_count["count"] == metadata["replica_count"]


def test_run_adversarial_uses_zero_temperature_scope_override(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        audit,
        "invoke_json",
        lambda *args, **kwargs: {
            "risk_level": "low",
            "suspected_problem_types": [],
            "alternative_bucket": "",
            "challenge_summary": "No serious challenge.",
            "notes": "",
        },
    )

    def fake_scope(**kwargs):
        captured["overrides"] = kwargs.get("overrides")
        return nullcontext()

    monkeypatch.setattr(audit, "llm_invocation_scope", fake_scope)

    adversarial, _ = audit.run_adversarial(
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

    assert adversarial["risk_level"] == "low"
    overrides = captured["overrides"]
    assert isinstance(overrides, audit.LLMInvocationOverrides)
    assert overrides.temperature == 0.0


def test_find_span_and_context_prefers_builder_supplied_prior_context_ids(tmp_path) -> None:
    output_dir = tmp_path / "source_output"
    book_document_path = output_dir / "public" / "book_document.json"
    book_document_path.parent.mkdir(parents=True, exist_ok=True)
    book_document_path.write_text(
        json.dumps(
            {
                "chapters": [
                    {
                        "id": 1,
                        "sentences": [
                            {"sentence_id": "s1", "text": "Earlier vow."},
                            {"sentence_id": "s2", "text": "Bridge context."},
                            {"sentence_id": "s3", "text": "Anchor sentence."},
                            {"sentence_id": "s4", "text": "Follow-up line."},
                        ],
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    case = {
        "case_id": "demo_case",
        "source_id": "demo_source",
        "chapter_id": "1",
        "start_sentence_id": "s3",
        "end_sentence_id": "s4",
        "excerpt_text": "Anchor sentence.\nFollow-up line.",
        "prior_context_sentence_ids": ["s1"],
    }
    source_index = {
        "demo_source": {
            "source_id": "demo_source",
            "output_dir": str(output_dir.relative_to(tmp_path)),
        }
    }

    original_root = audit.ROOT
    audit.ROOT = tmp_path
    try:
        span_info, context = audit.find_span_and_context(case, source_index)
    finally:
        audit.ROOT = original_root

    assert span_info["prior_context_sentence_ids"] == ["s1"]
    assert context["lookback_sentences"] == ["Earlier vow."]


def test_normalize_excerpt_text_for_compare_collapses_formatting_only_differences() -> None:
    expected = "Mrs.\nTouchett had once been like Isabel\uFEFF—so it seemed."
    reconstructed = "Mrs. Touchett had once been like Isabel—so it seemed."

    assert audit.normalize_excerpt_text_for_compare(expected) == audit.normalize_excerpt_text_for_compare(
        reconstructed
    )


def test_factual_audit_ignores_formatting_only_excerpt_differences(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        audit,
        "find_span_and_context",
        lambda _case, _source_index: (
            {
                "source_id": "demo_source",
                "output_dir": "/tmp/demo",
                "book_document_path": "/tmp/demo/public/book_document.json",
                "excerpt_text_reconstructed": "Mrs. Touchett had once been like Isabel—so it seemed.",
                "expected_excerpt_text": "Mrs.\nTouchett had once been like Isabel\uFEFF—so it seemed.",
                "prior_context_sentence_ids": [],
            },
            {"lookback_sentences": [], "excerpt_sentences": [], "lookahead_sentences": []},
        ),
    )

    factual = audit.factual_audit(
        {"case_id": "demo_case", "source_id": "demo_source"},
        {"demo_source": {"source_id": "demo_source", "output_dir": "/tmp/demo"}},
    )

    assert factual["ok"] is True
    assert factual["issues"] == []
    assert factual["normalized_expected_excerpt_text"] == factual["normalized_excerpt_text_reconstructed"]


def test_build_audit_prompt_input_payload_records_contract_and_hashes() -> None:
    payload = audit.build_audit_prompt_input_payload(
        {
            "case_id": "demo_case",
            "case_title": "Demo / callback_bridge",
            "target_profile_id": "callback_bridge",
            "selection_role": "argumentative",
            "question_ids": ["EQ-CM-004"],
            "phenomena": ["callback"],
            "selection_reason": "Selected because the line returns to earlier material.",
            "judge_focus": "Does the mechanism connect the callback honestly?",
            "prior_context_excerpt_text": "Earlier promise.",
            "excerpt_text": "Earlier promise.\nNow the callback arrives.",
        },
        {
            "lookback_sentences": ["Earlier promise."],
            "excerpt_sentences": ["Now the callback arrives."],
            "lookahead_sentences": ["Later implication."],
        },
    )

    assert payload["audit_prompt_contract_version"] == audit.AUDIT_PROMPT_CONTRACT_VERSION
    assert payload["case"]["case_id"] == "demo_case"
    assert payload["case"]["target_profile_id"] == "callback_bridge"
    assert payload["case"]["selection_role"] == "argumentative"
    assert payload["case"]["prior_context_text"] == "Earlier promise."
    assert payload["context"]["lookback_sentences"] == ["Earlier promise."]
    assert payload["prompt_hashes"]["primary_system_prompt_hash"]
    assert payload["prompt_hashes"]["primary_user_prompt_hash"]
    assert payload["prompt_hashes"]["adversarial_system_prompt_hash"]
    assert payload["prompt_hashes"]["adversarial_user_prompt_hash"]


def test_aggregate_includes_quota_recovery_counts() -> None:
    summary = audit.aggregate(
        [
            {
                "case_id": "demo_case",
                "status": "completed",
                "factual_audit": {"ok": True},
                "primary_review": {
                    "decision": "keep",
                    "bucket_fit": 4,
                    "focus_clarity": 4,
                    "excerpt_strength": 4,
                },
                "adversarial_review": {"risk_level": "low"},
                "audit_prompt_input_fingerprint": "abc",
                "audit_metadata": {
                    "quota_recovery": {
                        "quota_recovery_attempted_count": 1,
                        "quota_recovery_succeeded_count": 1,
                        "quota_failure_remaining_count": 0,
                        "quota_recovery_passes_used": 1,
                    }
                },
            }
        ],
        total_case_count=1,
        status="completed",
    )

    assert summary["quota_recovery_attempted_count"] == 1
    assert summary["quota_recovery_succeeded_count"] == 1
    assert summary["quota_failure_remaining_count"] == 0
    assert summary["quota_recovery_passes_used"] == 1


def _write_case_audit_run(tmp_path: Path, run_id: str, packet_id: str, rows: list[dict[str, object]]) -> Path:
    run_dir = tmp_path / run_id
    (run_dir / "cases").mkdir(parents=True)
    (run_dir / "summary").mkdir(parents=True)
    for row in rows:
        case_id = str(row["case_id"])
        (run_dir / "cases" / f"{case_id}.json").write_text(
            json.dumps(row, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    summary = audit.aggregate(rows, total_case_count=len(rows), status="completed")
    (run_dir / "summary" / "aggregate.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (run_dir / "run_state.json").write_text(
        json.dumps({"packet_id": packet_id, "run_id": run_id}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return run_dir


def test_compare_case_audit_runs_counts_primary_drift_without_input_drift(tmp_path: Path) -> None:
    prompt_input = audit.build_audit_prompt_input_payload(
        {
            "case_id": "demo_case",
            "case_title": "Demo / callback_bridge",
            "question_ids": ["EQ-CM-004"],
            "phenomena": ["callback"],
            "selection_reason": "Selected because the line returns to earlier material.",
            "judge_focus": "Does the mechanism connect the callback honestly?",
            "excerpt_text": "Earlier promise.\nNow the callback arrives.",
        },
        {
            "lookback_sentences": ["Earlier promise."],
            "excerpt_sentences": ["Now the callback arrives."],
            "lookahead_sentences": ["Later implication."],
        },
    )
    input_fingerprint = audit._fingerprint(prompt_input)
    factual = {"ok": True, "issues": []}
    row_a = {
        "case_id": "demo_case",
        "packet_id": "packet_a",
        "status": "completed",
        "factual_audit": factual,
        "primary_review": {
            "decision": "keep",
            "confidence": "high",
            "problem_types": [],
            "bucket_fit": 4,
            "focus_clarity": 4,
            "excerpt_strength": 4,
            "revised_bucket": "",
            "revised_selection_reason": "",
            "revised_judge_focus": "",
            "notes": "Strong case.",
        },
        "adversarial_review": {
            "risk_level": "low",
            "suspected_problem_types": [],
            "alternative_bucket": "",
            "challenge_summary": "No serious challenge.",
            "notes": "",
        },
        "audit_prompt_input_payload": prompt_input,
        "audit_prompt_input_fingerprint": input_fingerprint,
    }
    row_b = {
        **row_a,
        "packet_id": "packet_b",
        "primary_review": {
            **row_a["primary_review"],
            "decision": "revise",
            "confidence": "medium",
            "problem_types": ["ambiguous_focus"],
            "focus_clarity": 3,
            "notes": "Needs a tighter focus.",
        },
        "adversarial_review": {
            **row_a["adversarial_review"],
            "risk_level": "medium",
            "suspected_problem_types": ["ambiguous_focus"],
        },
    }

    run_a = _write_case_audit_run(tmp_path, "run_a", "packet_a", [row_a])
    run_b = _write_case_audit_run(tmp_path, "run_b", "packet_b", [row_b])

    payload = compare_case_audit_runs(run_a, run_b)

    assert payload["same_run_audit_prompt_input_fingerprint"] is True
    assert payload["drift_counts"]["audit_input_drift"] == 0
    assert payload["drift_counts"]["primary_decision_drift"] == 1
    assert payload["drift_counts"]["primary_score_drift"] == 1
    assert payload["drift_counts"]["primary_problem_type_drift"] == 1
    assert payload["drift_counts"]["adversarial_risk_drift"] == 1

from __future__ import annotations

from contextlib import nullcontext

import pytest

from eval.attentional_v2 import run_case_design_audit as audit
from eval.attentional_v2.run_case_design_audit import PRIMARY_PROMPT, normalize_primary


def test_primary_prompt_defines_score_scale() -> None:
    assert "`1-5` scale" in PRIMARY_PROMPT
    assert "`keep` should not use `1` or `2`" in PRIMARY_PROMPT


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
    assert normalized["bucket_fit"] == 3
    assert normalized["focus_clarity"] == 3
    assert normalized["excerpt_strength"] == 3
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
    assert normalized["focus_clarity"] == 1
    assert normalized["excerpt_strength"] == 3
    assert normalized["problem_types"] == ["weak_excerpt", "ambiguous_focus"]
    assert normalized["revised_bucket"] == "callback"


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

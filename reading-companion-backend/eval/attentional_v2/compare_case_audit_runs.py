"""Compare two case-audit runs for reproducibility drift."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .case_audit_runs import AGGREGATE_FILE, RUN_STATE_FILE, SUMMARY_DIR
from .run_case_design_audit import audit_run_input_fingerprint, normalize_audit_prompt_input_payload


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object JSON at {path}")
    return payload


def resolve_run_dir(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if (resolved / RUN_STATE_FILE).exists():
        return resolved
    if resolved.name == SUMMARY_DIR and (resolved.parent / RUN_STATE_FILE).exists():
        return resolved.parent
    raise FileNotFoundError(f"Expected a case-audit run dir or summary dir: {resolved}")


def load_summary(run_dir: Path) -> dict[str, Any]:
    aggregate_path = run_dir / SUMMARY_DIR / AGGREGATE_FILE
    if aggregate_path.exists():
        return load_json(aggregate_path)
    return {}


def load_case_records(run_dir: Path) -> dict[str, dict[str, Any]]:
    cases_dir = run_dir / "cases"
    if not cases_dir.exists():
        return {}
    records: dict[str, dict[str, Any]] = {}
    for path in sorted(cases_dir.glob("*.json")):
        payload = load_json(path)
        case_id = str(payload.get("case_id", "")).strip()
        if case_id:
            records[case_id] = payload
    return records


def _payload_component_fingerprints(record: dict[str, Any]) -> tuple[str, str, str]:
    payload = normalize_audit_prompt_input_payload(record.get("audit_prompt_input_payload"))
    if not payload:
        return "", "", ""
    return (
        _fingerprint(payload.get("case", {})),
        _fingerprint(payload.get("context", {})),
        _fingerprint(payload.get("prompt_hashes", {})),
    )


def run_input_fingerprint(summary: dict[str, Any], case_records: dict[str, dict[str, Any]]) -> str:
    existing = str(summary.get("run_audit_prompt_input_fingerprint", "")).strip()
    if existing:
        return existing
    return audit_run_input_fingerprint(
        {
            case_id: str(case_records[case_id].get("audit_prompt_input_fingerprint", "")).strip()
            for case_id in sorted(case_records)
        }
    )


def compare_case_audit_runs(left: Path, right: Path) -> dict[str, Any]:
    run_dir_a = resolve_run_dir(left)
    run_dir_b = resolve_run_dir(right)
    run_state_a = load_json(run_dir_a / RUN_STATE_FILE)
    run_state_b = load_json(run_dir_b / RUN_STATE_FILE)
    summary_a = load_summary(run_dir_a)
    summary_b = load_summary(run_dir_b)
    cases_a = load_case_records(run_dir_a)
    cases_b = load_case_records(run_dir_b)
    common_case_ids = sorted(set(cases_a).intersection(cases_b))
    case_diffs: list[dict[str, Any]] = []

    for case_id in common_case_ids:
        record_a = cases_a[case_id]
        record_b = cases_b[case_id]
        factual_a = dict(record_a.get("factual_audit") or {})
        factual_b = dict(record_b.get("factual_audit") or {})
        primary_a = dict(record_a.get("primary_review") or {})
        primary_b = dict(record_b.get("primary_review") or {})
        adversarial_a = dict(record_a.get("adversarial_review") or {})
        adversarial_b = dict(record_b.get("adversarial_review") or {})
        case_fp_a, context_fp_a, prompt_fp_a = _payload_component_fingerprints(record_a)
        case_fp_b, context_fp_b, prompt_fp_b = _payload_component_fingerprints(record_b)
        factual_issues_a = sorted(str(item).strip() for item in list(factual_a.get("issues") or []) if str(item).strip())
        factual_issues_b = sorted(str(item).strip() for item in list(factual_b.get("issues") or []) if str(item).strip())

        diff = {
            "case_id": case_id,
            "same_input_fingerprint": str(record_a.get("audit_prompt_input_fingerprint", "")).strip()
            == str(record_b.get("audit_prompt_input_fingerprint", "")).strip(),
            "same_case_input_fingerprint": case_fp_a == case_fp_b,
            "same_context_input_fingerprint": context_fp_a == context_fp_b,
            "same_prompt_hash_fingerprint": prompt_fp_a == prompt_fp_b,
            "same_source_row_fingerprint": case_fp_a == case_fp_b,
            "same_audit_row_fingerprint": str(record_a.get("audit_prompt_input_fingerprint", "")).strip()
            == str(record_b.get("audit_prompt_input_fingerprint", "")).strip(),
            "status_a": str(record_a.get("status", "")).strip(),
            "status_b": str(record_b.get("status", "")).strip(),
            "factual_ok_a": bool(factual_a.get("ok")),
            "factual_ok_b": bool(factual_b.get("ok")),
            "factual_issues_a": factual_issues_a,
            "factual_issues_b": factual_issues_b,
            "primary_decision_a": str(primary_a.get("decision", "")).strip(),
            "primary_decision_b": str(primary_b.get("decision", "")).strip(),
            "primary_confidence_a": str(primary_a.get("confidence", "")).strip(),
            "primary_confidence_b": str(primary_b.get("confidence", "")).strip(),
            "primary_problem_types_a": sorted(
                str(item).strip() for item in list(primary_a.get("problem_types") or []) if str(item).strip()
            ),
            "primary_problem_types_b": sorted(
                str(item).strip() for item in list(primary_b.get("problem_types") or []) if str(item).strip()
            ),
            "primary_bucket_fit_a": int(primary_a.get("bucket_fit", 0) or 0),
            "primary_bucket_fit_b": int(primary_b.get("bucket_fit", 0) or 0),
            "primary_focus_clarity_a": int(primary_a.get("focus_clarity", 0) or 0),
            "primary_focus_clarity_b": int(primary_b.get("focus_clarity", 0) or 0),
            "primary_excerpt_strength_a": int(primary_a.get("excerpt_strength", 0) or 0),
            "primary_excerpt_strength_b": int(primary_b.get("excerpt_strength", 0) or 0),
            "adversarial_risk_a": str(adversarial_a.get("risk_level", "")).strip(),
            "adversarial_risk_b": str(adversarial_b.get("risk_level", "")).strip(),
        }
        diff["status_drift"] = diff["status_a"] != diff["status_b"]
        diff["factual_drift"] = (
            diff["factual_ok_a"] != diff["factual_ok_b"] or diff["factual_issues_a"] != diff["factual_issues_b"]
        )
        diff["primary_decision_drift"] = diff["primary_decision_a"] != diff["primary_decision_b"]
        diff["primary_confidence_drift"] = diff["primary_confidence_a"] != diff["primary_confidence_b"]
        diff["primary_problem_type_drift"] = diff["primary_problem_types_a"] != diff["primary_problem_types_b"]
        diff["primary_score_drift"] = any(
            (
                diff["primary_bucket_fit_a"] != diff["primary_bucket_fit_b"],
                diff["primary_focus_clarity_a"] != diff["primary_focus_clarity_b"],
                diff["primary_excerpt_strength_a"] != diff["primary_excerpt_strength_b"],
            )
        )
        diff["adversarial_risk_drift"] = diff["adversarial_risk_a"] != diff["adversarial_risk_b"]
        case_diffs.append(diff)

    run_input_fingerprint_a = run_input_fingerprint(summary_a, cases_a)
    run_input_fingerprint_b = run_input_fingerprint(summary_b, cases_b)
    drift_counts = {
        "input_drift": sum(1 for item in case_diffs if not item["same_input_fingerprint"]),
        "case_input_drift": sum(1 for item in case_diffs if not item["same_case_input_fingerprint"]),
        "context_input_drift": sum(1 for item in case_diffs if not item["same_context_input_fingerprint"]),
        "prompt_drift": sum(1 for item in case_diffs if not item["same_prompt_hash_fingerprint"]),
        "status_drift": sum(1 for item in case_diffs if item["status_drift"]),
        "factual_drift": sum(1 for item in case_diffs if item["factual_drift"]),
        "primary_decision_drift": sum(1 for item in case_diffs if item["primary_decision_drift"]),
        "primary_confidence_drift": sum(1 for item in case_diffs if item["primary_confidence_drift"]),
        "primary_problem_type_drift": sum(1 for item in case_diffs if item["primary_problem_type_drift"]),
        "primary_score_drift": sum(1 for item in case_diffs if item["primary_score_drift"]),
        "adversarial_risk_drift": sum(1 for item in case_diffs if item["adversarial_risk_drift"]),
    }
    drift_counts["source_input_drift"] = drift_counts["case_input_drift"]
    drift_counts["audit_input_drift"] = drift_counts["input_drift"]
    return {
        "run_dir_a": str(run_dir_a),
        "run_dir_b": str(run_dir_b),
        "packet_id_a": str(run_state_a.get("packet_id", "")).strip(),
        "packet_id_b": str(run_state_b.get("packet_id", "")).strip(),
        "run_id_a": str(run_state_a.get("run_id", "")).strip(),
        "run_id_b": str(run_state_b.get("run_id", "")).strip(),
        "run_input_fingerprint_a": run_input_fingerprint_a,
        "run_input_fingerprint_b": run_input_fingerprint_b,
        "same_run_input_fingerprint": run_input_fingerprint_a == run_input_fingerprint_b,
        "same_run_audit_prompt_input_fingerprint": run_input_fingerprint_a == run_input_fingerprint_b,
        "common_case_count": len(common_case_ids),
        "only_in_a": sorted(set(cases_a) - set(cases_b)),
        "only_in_b": sorted(set(cases_b) - set(cases_a)),
        "drift_counts": drift_counts,
        "case_diffs": case_diffs,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Case Audit Run Comparison",
        "",
        f"- run_id_a: `{payload['run_id_a']}`",
        f"- run_id_b: `{payload['run_id_b']}`",
        f"- same_run_input_fingerprint: `{payload['same_run_input_fingerprint']}`",
        f"- drift_counts: `{json.dumps(payload['drift_counts'], ensure_ascii=False, sort_keys=True)}`",
        "",
        "## Case Drift",
        "",
    ]
    for item in payload["case_diffs"]:
        lines.extend(
            [
                f"- `{item['case_id']}`",
                f"  - same_input_fingerprint: `{item['same_input_fingerprint']}`",
                f"  - same_case_input_fingerprint: `{item['same_case_input_fingerprint']}`",
                f"  - same_context_input_fingerprint: `{item['same_context_input_fingerprint']}`",
                f"  - same_prompt_hash_fingerprint: `{item['same_prompt_hash_fingerprint']}`",
                f"  - factual_ok: `{item['factual_ok_a']}` -> `{item['factual_ok_b']}`",
                f"  - primary_decision: `{item['primary_decision_a']}` -> `{item['primary_decision_b']}`",
                f"  - adversarial_risk: `{item['adversarial_risk_a']}` -> `{item['adversarial_risk_b']}`",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--left", required=True, help="Case-audit run dir for the left side.")
    parser.add_argument("--right", required=True, help="Case-audit run dir for the right side.")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = compare_case_audit_runs(Path(args.left), Path(args.right))
    if args.format == "markdown":
        print(render_markdown(payload), end="")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

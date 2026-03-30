"""Compare two packet adjudication runs for reproducibility drift."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .auto_review_packet import (
    ADJUDICATION_CONTRACT_VERSION,
    REVIEW_POLICY,
    SYSTEM,
    _case_input_payload,
    _fingerprint,
    _review_prompt,
    _load_jsonl,
    _prompt_hash,
    _stable_audit_prompt_inputs,
    packet_input_fingerprint as compute_packet_input_fingerprint,
)


ROOT = Path(__file__).resolve().parents[2]
CASE_AUDIT_RUNS_ROOT = ROOT / "eval" / "runs" / "attentional_v2" / "case_audits"


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object JSON at {path}")
    return payload


def parse_review_rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [dict(row) for row in reader]
    return {
        str(row.get("case_id", "")).strip(): row
        for row in rows
        if str(row.get("case_id", "")).strip()
    }


def latest_trace_entry_for_case(trace_path: Path, case_id: str) -> dict[str, Any]:
    matches = [row for row in _load_jsonl(trace_path) if str(row.get("case_id", "")).strip() == case_id]
    return dict(matches[-1]) if matches else {}


@dataclass(frozen=True)
class AdjudicationRunContext:
    packet_dir: Path
    run_dir: Path
    run_manifest_path: Path
    summary_path: Path
    review_csv_path: Path
    source_jsonl_path: Path
    packet_manifest_path: Path
    trace_path: Path


def _packet_dir_from_run_dir(run_dir: Path) -> Path:
    if run_dir.parent.name == "llm_review_runs":
        return run_dir.parent.parent
    return run_dir


def resolve_context(path: Path) -> AdjudicationRunContext:
    resolved = path.expanduser().resolve()
    if (resolved / "packet_manifest.json").exists():
        packet_dir = resolved
        run_id = str(load_json(packet_dir / "llm_review_summary.json").get("run_id", "")).strip()
        if not run_id:
            raise ValueError(f"Could not resolve llm review run id from {packet_dir / 'llm_review_summary.json'}")
        run_dir = packet_dir / "llm_review_runs" / run_id
    elif (resolved / "summary.json").exists():
        run_dir = resolved
        packet_dir = _packet_dir_from_run_dir(run_dir)
    elif (resolved / "llm_traces" / "standard.jsonl").exists():
        run_dir = resolved
        packet_dir = _packet_dir_from_run_dir(run_dir)
    else:
        raise FileNotFoundError(f"Expected a packet dir or llm review run dir: {resolved}")

    summary_path = run_dir / "summary.json"
    if not summary_path.exists():
        summary_path = packet_dir / "llm_review_summary.json"
    return AdjudicationRunContext(
        packet_dir=packet_dir,
        run_dir=run_dir,
        run_manifest_path=run_dir / "manifest.json",
        summary_path=summary_path,
        review_csv_path=packet_dir / "cases.review.csv",
        source_jsonl_path=packet_dir / "cases.source.jsonl",
        packet_manifest_path=packet_dir / "packet_manifest.json",
        trace_path=run_dir / "llm_traces" / "standard.jsonl",
    )


def source_rows_by_case_id(path: Path) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("case_id", "")).strip(): row
        for row in _load_jsonl(path)
        if str(row.get("case_id", "")).strip()
    }


def legacy_case_input_fingerprint(
    *,
    case_id: str,
    source_rows: dict[str, dict[str, Any]],
    audit_rows: dict[str, dict[str, Any]],
    source_case_audit_run_id: str,
) -> str:
    case = source_rows.get(case_id, {})
    audit_row = audit_rows.get(case_id, {})
    if not case or not audit_row:
        return ""
    user_prompt = _review_prompt(case, audit_row)
    payload = _case_input_payload(
        case=case,
        audit_row=audit_row,
        system_prompt=SYSTEM,
        user_prompt=user_prompt,
        source_case_audit_run_id=source_case_audit_run_id,
    )
    return _fingerprint(payload)


def load_audit_rows(source_case_audit_run_id: str) -> dict[str, dict[str, Any]]:
    if not source_case_audit_run_id:
        return {}
    cases_dir = CASE_AUDIT_RUNS_ROOT / source_case_audit_run_id / "cases"
    if not cases_dir.exists():
        return {}
    rows: dict[str, dict[str, Any]] = {}
    for path in sorted(cases_dir.glob("*.json")):
        payload = load_json(path)
        case_id = str(payload.get("case_id", "")).strip()
        if case_id:
            rows[case_id] = payload
    return rows


def load_case_records(context: AdjudicationRunContext, summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    cases_dir = context.run_dir / "cases"
    if cases_dir.exists():
        return {
            str(payload.get("case_id", "")).strip(): payload
            for payload in (load_json(path) for path in sorted(cases_dir.glob("*.json")))
            if str(payload.get("case_id", "")).strip()
        }

    review_rows = parse_review_rows(context.review_csv_path)
    source_rows = source_rows_by_case_id(context.source_jsonl_path)
    packet_manifest = load_json(context.packet_manifest_path)
    audit_run_id = str(
        summary.get("source_case_audit_run_id")
        or packet_manifest.get("source_case_audit_run_id")
        or ""
    ).strip()
    audit_rows = load_audit_rows(audit_run_id)
    legacy_records: dict[str, dict[str, Any]] = {}
    for case_id, review_row in review_rows.items():
        trace_entry = latest_trace_entry_for_case(context.trace_path, case_id)
        legacy_records[case_id] = {
            "case_id": case_id,
            "normalized_review": {
                "review__action": str(review_row.get("review__action", "")).strip(),
                "review__confidence": str(review_row.get("review__confidence", "")).strip(),
                "review__problem_types": [
                    item.strip()
                    for item in str(review_row.get("review__problem_types", "")).split("|")
                    if item.strip()
                ],
                "review__revised_bucket": str(review_row.get("review__revised_bucket", "")).strip(),
                "review__revised_selection_reason": str(review_row.get("review__revised_selection_reason", "")).strip(),
                "review__revised_judge_focus": str(review_row.get("review__revised_judge_focus", "")).strip(),
                "review__notes": str(review_row.get("review__notes", "")).strip(),
            },
            "adjudication_input_fingerprint": legacy_case_input_fingerprint(
                case_id=case_id,
                source_rows=source_rows,
                audit_rows=audit_rows,
                source_case_audit_run_id=audit_run_id,
            ),
            "source_row_fingerprint": _fingerprint(source_rows.get(case_id, {})) if case_id in source_rows else "",
            "audit_row_fingerprint": _fingerprint(_stable_audit_prompt_inputs(audit_rows.get(case_id, {})))
            if case_id in audit_rows
            else "",
            "prompt_hashes": {
                "system_prompt_hash": _prompt_hash(SYSTEM),
                "user_prompt_hash": _prompt_hash(_review_prompt(source_rows.get(case_id, {}), audit_rows.get(case_id, {})))
                if case_id in source_rows and case_id in audit_rows
                else "",
            },
            "selected_target_id": str(trace_entry.get("selected_target_id", "")).strip(),
            "selected_tier_id": str(trace_entry.get("selected_tier_id", "")).strip(),
            "provider_id": str(trace_entry.get("provider_id", "")).strip(),
            "contract": str(trace_entry.get("contract", "")).strip(),
            "model": str(trace_entry.get("model", "")).strip(),
            "key_slot_id": str(trace_entry.get("key_slot_id", "")).strip(),
            "selection_reason": str(trace_entry.get("selection_reason", "")).strip(),
            "selection_override_source": str(trace_entry.get("selection_override_source", "")).strip(),
            "trace_call_id": str(trace_entry.get("call_id", "")).strip(),
            "trace_status": str(trace_entry.get("status", "")).strip(),
            "attempt_count": int(trace_entry.get("attempt_count", 0) or 0),
            "source_case_audit_run_id": audit_run_id,
            "legacy_reconstructed": True,
        }
    return legacy_records


def packet_input_fingerprint(summary: dict[str, Any], case_records: dict[str, dict[str, Any]]) -> str:
    existing = str(summary.get("adjudication_input_fingerprint", "")).strip()
    if existing:
        return existing
    return compute_packet_input_fingerprint(
        review_policy=str(summary.get("review_policy", "")).strip() or REVIEW_POLICY,
        adjudication_contract_version=str(summary.get("adjudication_contract_version", "")).strip()
        or ADJUDICATION_CONTRACT_VERSION,
        source_case_audit_run_id=str(summary.get("source_case_audit_run_id", "")).strip(),
        case_input_fingerprints={
            case_id: str(case_records[case_id].get("adjudication_input_fingerprint", "")).strip()
            for case_id in sorted(case_records)
        },
    )


def compare_adjudication_runs(left: Path, right: Path) -> dict[str, Any]:
    context_a = resolve_context(left)
    context_b = resolve_context(right)
    summary_a = load_json(context_a.summary_path)
    summary_b = load_json(context_b.summary_path)
    cases_a = load_case_records(context_a, summary_a)
    cases_b = load_case_records(context_b, summary_b)
    common_case_ids = sorted(set(cases_a).intersection(cases_b))
    case_diffs: list[dict[str, Any]] = []

    for case_id in common_case_ids:
        record_a = cases_a[case_id]
        record_b = cases_b[case_id]
        review_a = dict(record_a.get("normalized_review") or {})
        review_b = dict(record_b.get("normalized_review") or {})
        provider_fields = (
            "provider_id",
            "selected_target_id",
            "selected_tier_id",
            "key_slot_id",
            "contract",
            "model",
        )
        diff = {
            "case_id": case_id,
            "same_input_fingerprint": str(record_a.get("adjudication_input_fingerprint", "")).strip()
            == str(record_b.get("adjudication_input_fingerprint", "")).strip(),
            "action_a": str(review_a.get("review__action", "")).strip(),
            "action_b": str(review_b.get("review__action", "")).strip(),
            "confidence_a": str(review_a.get("review__confidence", "")).strip(),
            "confidence_b": str(review_b.get("review__confidence", "")).strip(),
            "problem_types_a": list(review_a.get("review__problem_types") or []),
            "problem_types_b": list(review_b.get("review__problem_types") or []),
            "provider_a": str(record_a.get("provider_id", "")).strip(),
            "provider_b": str(record_b.get("provider_id", "")).strip(),
            "target_a": str(record_a.get("selected_target_id", "")).strip(),
            "target_b": str(record_b.get("selected_target_id", "")).strip(),
            "tier_a": str(record_a.get("selected_tier_id", "")).strip(),
            "tier_b": str(record_b.get("selected_tier_id", "")).strip(),
            "key_slot_a": str(record_a.get("key_slot_id", "")).strip(),
            "key_slot_b": str(record_b.get("key_slot_id", "")).strip(),
            "contract_a": str(record_a.get("contract", "")).strip(),
            "contract_b": str(record_b.get("contract", "")).strip(),
            "model_a": str(record_a.get("model", "")).strip(),
            "model_b": str(record_b.get("model", "")).strip(),
            "same_source_row_fingerprint": str(record_a.get("source_row_fingerprint", "")).strip()
            == str(record_b.get("source_row_fingerprint", "")).strip(),
            "same_audit_row_fingerprint": str(record_a.get("audit_row_fingerprint", "")).strip()
            == str(record_b.get("audit_row_fingerprint", "")).strip(),
        }
        diff["action_drift"] = diff["action_a"] != diff["action_b"]
        diff["confidence_drift"] = diff["confidence_a"] != diff["confidence_b"]
        diff["problem_type_drift"] = diff["problem_types_a"] != diff["problem_types_b"]
        diff["routing_drift"] = any(
            str(record_a.get(field, "")).strip() != str(record_b.get(field, "")).strip()
            for field in provider_fields
        )
        case_diffs.append(diff)

    return {
        "run_dir_a": str(context_a.run_dir),
        "run_dir_b": str(context_b.run_dir),
        "packet_dir_a": str(context_a.packet_dir),
        "packet_dir_b": str(context_b.packet_dir),
        "packet_id_a": str(summary_a.get("packet_id", "")).strip(),
        "packet_id_b": str(summary_b.get("packet_id", "")).strip(),
        "run_id_a": str(summary_a.get("run_id", "")).strip(),
        "run_id_b": str(summary_b.get("run_id", "")).strip(),
        "review_policy_a": str(summary_a.get("review_policy", "")).strip() or REVIEW_POLICY,
        "review_policy_b": str(summary_b.get("review_policy", "")).strip() or REVIEW_POLICY,
        "adjudication_contract_version_a": str(summary_a.get("adjudication_contract_version", "")).strip()
        or ADJUDICATION_CONTRACT_VERSION,
        "adjudication_contract_version_b": str(summary_b.get("adjudication_contract_version", "")).strip()
        or ADJUDICATION_CONTRACT_VERSION,
        "packet_input_fingerprint_a": packet_input_fingerprint(summary_a, cases_a),
        "packet_input_fingerprint_b": packet_input_fingerprint(summary_b, cases_b),
        "same_packet_input_fingerprint": packet_input_fingerprint(summary_a, cases_a)
        == packet_input_fingerprint(summary_b, cases_b),
        "action_counts_a": dict(summary_a.get("action_counts") or {}),
        "action_counts_b": dict(summary_b.get("action_counts") or {}),
        "common_case_count": len(common_case_ids),
        "only_in_a": sorted(set(cases_a) - set(cases_b)),
        "only_in_b": sorted(set(cases_b) - set(cases_a)),
        "drift_counts": {
            "action_drift": sum(1 for item in case_diffs if item["action_drift"]),
            "confidence_drift": sum(1 for item in case_diffs if item["confidence_drift"]),
            "problem_type_drift": sum(1 for item in case_diffs if item["problem_type_drift"]),
            "routing_drift": sum(1 for item in case_diffs if item["routing_drift"]),
            "source_input_drift": sum(1 for item in case_diffs if not item["same_source_row_fingerprint"]),
            "audit_input_drift": sum(1 for item in case_diffs if not item["same_audit_row_fingerprint"]),
        },
        "case_diffs": case_diffs,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Packet Adjudication Run Comparison",
        "",
        f"- run_id_a: `{payload['run_id_a']}`",
        f"- run_id_b: `{payload['run_id_b']}`",
        f"- same_packet_input_fingerprint: `{payload['same_packet_input_fingerprint']}`",
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
                f"  - same_source_row_fingerprint: `{item['same_source_row_fingerprint']}`",
                f"  - same_audit_row_fingerprint: `{item['same_audit_row_fingerprint']}`",
                f"  - action: `{item['action_a']}` -> `{item['action_b']}`",
                f"  - confidence: `{item['confidence_a']}` -> `{item['confidence_b']}`",
                f"  - routing_drift: `{item['routing_drift']}`",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--left", required=True, help="Packet dir or llm review run dir for the left side.")
    parser.add_argument("--right", required=True, help="Packet dir or llm review run dir for the right side.")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = compare_adjudication_runs(
        Path(args.left),
        Path(args.right),
    )
    if args.format == "markdown":
        print(render_markdown(payload), end="")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

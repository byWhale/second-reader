"""Build a machine-readable summary of active dataset-review packets."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PENDING_ROOT = ROOT / "eval" / "review_packets" / "pending"
RUNS_ROOT = ROOT / "eval" / "runs" / "attentional_v2" / "case_audits"
OUTPUT_JSON = ROOT / "eval" / "review_packets" / "review_queue_summary.json"
OUTPUT_MD = ROOT / "eval" / "review_packets" / "review_queue_summary.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object JSON at {path}")
    return payload


def latest_audit_for_packet(packet_id: str) -> dict[str, Any] | None:
    matching_dirs = sorted([path for path in RUNS_ROOT.iterdir() if path.is_dir() and path.name.startswith(f"{packet_id}__")])
    if not matching_dirs:
        return None
    latest_dir = matching_dirs[-1]
    aggregate_path = latest_dir / "summary" / "aggregate.json"
    report_path = latest_dir / "summary" / "report.md"
    aggregate = load_json(aggregate_path) if aggregate_path.exists() else {}
    return {
        "run_id": latest_dir.name,
        "run_dir": str(latest_dir),
        "aggregate_path": str(aggregate_path) if aggregate_path.exists() else "",
        "report_path": str(report_path) if report_path.exists() else "",
        "aggregate": aggregate,
    }


def build_summary() -> dict[str, Any]:
    packets: list[dict[str, Any]] = []
    for packet_dir in sorted(PENDING_ROOT.iterdir()):
        if not packet_dir.is_dir():
            continue
        manifest_path = packet_dir / "packet_manifest.json"
        if not manifest_path.exists():
            continue
        manifest = load_json(manifest_path)
        packet_id = str(manifest.get("packet_id", packet_dir.name))
        packets.append(
            {
                "packet_id": packet_id,
                "packet_dir": str(packet_dir),
                "created_at": str(manifest.get("created_at", "")),
                "dataset_id": str(manifest.get("dataset_id", "")),
                "family": str(manifest.get("family", "")),
                "storage_mode": str(manifest.get("storage_mode", "")),
                "case_count": int(manifest.get("case_count", 0) or 0),
                "selection_filters": dict(manifest.get("selection_filters", {})),
                "latest_case_audit": latest_audit_for_packet(packet_id),
            }
        )
    return {
        "generated_at": utc_now(),
        "active_packet_count": len(packets),
        "packets": packets,
    }


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Review Queue Summary",
        "",
        f"Generated: `{summary['generated_at']}`",
        "",
        f"Active packets: `{summary['active_packet_count']}`",
        "",
    ]
    for packet in summary["packets"]:
        lines.extend(
            [
                f"## {packet['packet_id']}",
                "",
                f"- dataset: `{packet['dataset_id']}`",
                f"- storage_mode: `{packet['storage_mode']}`",
                f"- case_count: `{packet['case_count']}`",
                f"- created_at: `{packet['created_at']}`",
            ]
        )
        audit = packet.get("latest_case_audit")
        if isinstance(audit, dict) and audit:
            aggregate = audit.get("aggregate", {})
            lines.extend(
                [
                    f"- latest_case_audit: `{audit.get('run_id', '')}`",
                    f"- audit_primary_decisions: `{json.dumps(aggregate.get('primary_decisions', {}), ensure_ascii=False, sort_keys=True)}`",
                    f"- audit_risk_counts: `{json.dumps(aggregate.get('adversarial_risk_counts', {}), ensure_ascii=False, sort_keys=True)}`",
                    f"- audit_excerpt_strength: `{aggregate.get('average_excerpt_strength', '')}`",
                ]
            )
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    summary = build_summary()
    OUTPUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUTPUT_MD.write_text(render_markdown(summary) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "active_packet_count": summary["active_packet_count"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Maintain the lightweight evaluation evidence catalog.

The catalog is intentionally small: it indexes meaningful evaluation evidence
after runs finish, while raw machine artifacts remain under eval/runs/.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG_JSON = BACKEND_ROOT / "docs" / "evaluation" / "evidence_catalog.json"
DEFAULT_CATALOG_MD = BACKEND_ROOT / "docs" / "evaluation" / "evidence_catalog.md"
RUNS_ROOT = BACKEND_ROOT / "eval" / "runs" / "attentional_v2"
SCHEMA_VERSION = 1

ALLOWED_STATUSES = {
    "current_formal_evidence",
    "historical_evidence",
    "superseded",
    "quality_audit",
    "failed_diagnostic",
    "invalidated_diagnostic",
}

FORMAL_STATUSES = {"current_formal_evidence", "historical_evidence", "superseded"}

SURFACE_DEFAULTS: dict[str, dict[str, str]] = {
    "active_benchmark_bundle": {
        "evaluation_goal": "Active benchmark bundle",
    },
    "user_level_selective_v1": {
        "evaluation_goal": "Selective Legibility",
    },
    "target_centered_accumulation_v2": {
        "evaluation_goal": "Coherent Accumulation",
    },
    "bounded_longspan_accumulation_v1": {
        "evaluation_goal": "Coherent Accumulation",
    },
    "excerpt_surface_v1_1": {
        "evaluation_goal": "Selective Legibility / Insight and Clarification",
    },
    "attentional_v2_quality_audit": {
        "evaluation_goal": "Focused mechanism quality audit",
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json_load(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_catalog(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "updated_at": utc_now(), "entries": []}
    payload = _json_load(path)
    if not isinstance(payload, dict):
        raise ValueError(f"catalog must be a JSON object: {path}")
    payload.setdefault("schema_version", SCHEMA_VERSION)
    payload.setdefault("updated_at", utc_now())
    payload.setdefault("entries", [])
    if not isinstance(payload["entries"], list):
        raise ValueError(f"catalog entries must be a list: {path}")
    return payload


def _rel_backend_path(path: str | Path | None) -> str:
    if path is None:
        return ""
    raw = str(path).strip()
    if not raw:
        return ""
    value = Path(raw).expanduser()
    if not value.is_absolute():
        if raw == BACKEND_ROOT.name or raw.startswith(f"{BACKEND_ROOT.name}/"):
            value = (BACKEND_ROOT.parent / value).resolve()
        else:
            value = (BACKEND_ROOT / value).resolve()
    try:
        return str(value.resolve().relative_to(BACKEND_ROOT))
    except ValueError:
        return str(value.resolve())


def _resolve_catalog_path(path: str) -> Path:
    if path == BACKEND_ROOT.name or path.startswith(f"{BACKEND_ROOT.name}/"):
        return BACKEND_ROOT.parent / path
    value = Path(path)
    if value.is_absolute():
        return value
    return BACKEND_ROOT / value


def _path_exists(path: str | None) -> bool:
    if not path:
        return False
    return _resolve_catalog_path(path).exists()


def _find_run_dir(run_id: str, run_dir: str | Path | None = None) -> Path:
    if run_dir:
        value = Path(run_dir)
        return value if value.is_absolute() else BACKEND_ROOT / value
    return RUNS_ROOT / run_id


def _maybe_load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = _json_load(path)
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _mechanisms_from_aggregate(aggregate: dict[str, Any]) -> list[str]:
    mechanisms = aggregate.get("mechanisms")
    if isinstance(mechanisms, dict):
        return sorted(str(item) for item in mechanisms.keys())
    target_summaries = aggregate.get("target_summaries")
    if isinstance(target_summaries, dict):
        mechanism_keys: set[str] = set()
        for summary in target_summaries.values():
            if isinstance(summary, dict) and isinstance(summary.get("average_scores"), dict):
                mechanism_keys.update(str(item) for item in summary["average_scores"].keys())
        if mechanism_keys:
            return sorted(mechanism_keys)
    if "excerpt" in aggregate and "accumulation" in aggregate:
        return ["attentional_v2", "iterator_v1"]
    return []


def _metric_summary_from_aggregate(aggregate: dict[str, Any]) -> dict[str, Any]:
    if not aggregate:
        return {}
    summary: dict[str, Any] = {}
    for key in (
        "note_case_count",
        "case_count",
        "completed_case_count",
        "failed_case_count",
        "segment_count",
        "question_family",
    ):
        if key in aggregate:
            summary[key] = aggregate[key]

    mechanisms = aggregate.get("mechanisms")
    if isinstance(mechanisms, dict):
        summary["mechanisms"] = {}
        metric_keys = (
            "note_recall",
            "average_quality_score",
            "average_callback_score",
            "exact_match_count",
            "focused_hit_count",
            "incidental_cover_count",
            "miss_count",
            "case_count",
            "note_case_count",
            "judge_unavailable_count",
            "mechanism_unavailable_count",
        )
        for mechanism_key, stats in mechanisms.items():
            if not isinstance(stats, dict):
                continue
            summary["mechanisms"][mechanism_key] = {
                key: stats[key] for key in metric_keys if key in stats
            }
        if isinstance(aggregate.get("derived_comparison"), dict):
            derived = aggregate["derived_comparison"]
            summary["derived_comparison"] = {
                key: derived[key]
                for key in ("winner_counts", "comparison_rule", "case_count")
                if key in derived
            }

    if "excerpt" in aggregate and "accumulation" in aggregate:
        summary["children"] = {
            "excerpt": {
                "run_id": (aggregate.get("excerpt") or {}).get("run_id"),
                "job_id": (aggregate.get("excerpt") or {}).get("job_id"),
            },
            "accumulation": {
                "run_id": (aggregate.get("accumulation") or {}).get("run_id"),
                "job_id": (aggregate.get("accumulation") or {}).get("job_id"),
                "reused_output_run_ids": (aggregate.get("accumulation") or {}).get("reused_output_run_ids", []),
            },
        }
    target_summaries = aggregate.get("target_summaries")
    if isinstance(target_summaries, dict):
        summary["target_summaries"] = {}
        for target_name, target_summary in target_summaries.items():
            if not isinstance(target_summary, dict):
                continue
            summary["target_summaries"][target_name] = {
                key: target_summary[key]
                for key in ("case_count", "winner_counts", "average_scores", "judge_unavailable_count", "mechanism_failure_count")
                if key in target_summary
            }
    return summary


def _run_paths_from_dir(run_dir: Path, analysis_docs: list[str] | None = None) -> dict[str, Any]:
    paths: dict[str, Any] = {"run_dir": _rel_backend_path(run_dir)}
    summary_dir = run_dir / "summary"
    common = {
        "aggregate": summary_dir / "aggregate.json",
        "report": summary_dir / "report.md",
        "case_results": summary_dir / "case_results.jsonl",
        "llm_usage": summary_dir / "llm_usage.json",
        "selection": summary_dir / "selection.json",
    }
    for key, path in common.items():
        if path.exists():
            paths[key] = _rel_backend_path(path)
    if analysis_docs:
        paths["analysis_docs"] = [_rel_backend_path(path) for path in analysis_docs]
    return paths


def _parse_key_value(values: list[str] | None) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for item in values or []:
        if "=" not in item:
            raise ValueError(f"expected KEY=VALUE, got {item!r}")
        key, value = item.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError(f"empty metric key in {item!r}")
        try:
            parsed[key] = json.loads(value)
        except json.JSONDecodeError:
            parsed[key] = value
    return parsed


def build_entry(
    *,
    run_id: str,
    surface: str,
    status: str,
    run_dir: str | Path | None = None,
    evaluation_goal: str | None = None,
    dataset_id: str | None = None,
    dataset_path: str | Path | None = None,
    manifest_path: str | Path | None = None,
    mechanisms: list[str] | None = None,
    metric_overrides: dict[str, Any] | None = None,
    job_ids: list[str] | None = None,
    one_line_conclusion: str | None = None,
    analysis_docs: list[str] | None = None,
) -> dict[str, Any]:
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"Unsupported catalog status: {status}")
    resolved_run_dir = _find_run_dir(run_id, run_dir)
    aggregate = _maybe_load_json(resolved_run_dir / "summary" / "aggregate.json")
    defaults = SURFACE_DEFAULTS.get(surface, {})
    inferred_dataset_path = dataset_path or aggregate.get("dataset_dir")
    inferred_manifest_path = manifest_path or aggregate.get("manifest_path")
    if isinstance(inferred_dataset_path, str) and inferred_dataset_path.startswith(str(BACKEND_ROOT)):
        inferred_dataset_path = Path(inferred_dataset_path)
    if isinstance(inferred_manifest_path, str) and inferred_manifest_path.startswith(str(BACKEND_ROOT)):
        inferred_manifest_path = Path(inferred_manifest_path)
    metric_summary = _metric_summary_from_aggregate(aggregate)
    metric_summary.update(metric_overrides or {})
    inferred_mechanisms = mechanisms or _mechanisms_from_aggregate(aggregate)

    entry = {
        "run_id": run_id,
        "surface": surface,
        "evaluation_goal": evaluation_goal or defaults.get("evaluation_goal", ""),
        "status": status,
        "dataset_id": dataset_id or "",
        "dataset_path": _rel_backend_path(inferred_dataset_path),
        "manifest_path": _rel_backend_path(inferred_manifest_path),
        "mechanisms": sorted(dict.fromkeys(inferred_mechanisms)),
        "metric_summary": metric_summary,
        "run_paths": _run_paths_from_dir(resolved_run_dir, analysis_docs=analysis_docs),
        "job_ids": sorted(dict.fromkeys(job_ids or [])),
        "one_line_conclusion": one_line_conclusion or "",
        "updated_at": utc_now(),
    }
    return entry


def upsert_catalog_entry(
    entry: dict[str, Any],
    *,
    catalog_json_path: Path = DEFAULT_CATALOG_JSON,
    catalog_md_path: Path = DEFAULT_CATALOG_MD,
) -> dict[str, Any]:
    catalog = _read_catalog(catalog_json_path)
    key = (entry["run_id"], entry["surface"])
    if entry.get("status") == "current_formal_evidence":
        for existing in catalog["entries"]:
            if (
                existing.get("surface") == entry.get("surface")
                and existing.get("run_id") != entry.get("run_id")
                and existing.get("status") == "current_formal_evidence"
            ):
                existing["status"] = "historical_evidence"
                existing["updated_at"] = utc_now()
    entries = [
        existing
        for existing in catalog["entries"]
        if (existing.get("run_id"), existing.get("surface")) != key
    ]
    entries.append(entry)
    entries.sort(key=lambda item: (str(item.get("surface", "")), str(item.get("run_id", ""))))
    catalog["entries"] = entries
    catalog["updated_at"] = utc_now()
    _json_dump(catalog_json_path, catalog)
    write_markdown_catalog(catalog, catalog_md_path=catalog_md_path)
    return catalog


def _display_metric_summary(metric_summary: dict[str, Any]) -> str:
    if not metric_summary:
        return ""
    pieces: list[str] = []
    children = metric_summary.get("children")
    if isinstance(children, dict):
        child_bits = []
        for child_name, child in children.items():
            if isinstance(child, dict) and child.get("run_id"):
                child_bits.append(f"{child_name}={child['run_id']}")
        if child_bits:
            pieces.append("; ".join(child_bits))
    mechanisms = metric_summary.get("mechanisms")
    if isinstance(mechanisms, dict):
        for mechanism_key, stats in mechanisms.items():
            if not isinstance(stats, dict):
                continue
            metric_bits = []
            for key in ("note_recall", "average_quality_score", "average_callback_score"):
                if key in stats:
                    metric_bits.append(f"{key}={stats[key]}")
            if metric_bits:
                pieces.append(f"`{mechanism_key}` " + ", ".join(metric_bits))
    target_summaries = metric_summary.get("target_summaries")
    if isinstance(target_summaries, dict):
        for target_name, target_summary in target_summaries.items():
            if not isinstance(target_summary, dict):
                continue
            target_bits = []
            average_scores = target_summary.get("average_scores")
            if isinstance(average_scores, dict):
                target_bits.append(
                    "avg="
                    + ", ".join(f"{mechanism} {score}" for mechanism, score in sorted(average_scores.items()))
                )
            winner_counts = target_summary.get("winner_counts")
            if isinstance(winner_counts, dict):
                target_bits.append(
                    "wins="
                    + ", ".join(f"{mechanism} {count}" for mechanism, count in sorted(winner_counts.items()))
                )
            if target_bits:
                pieces.append(f"{target_name}: " + "; ".join(target_bits))
    for key in ("note_case_count", "case_count", "completed_case_count", "failed_case_count"):
        if key in metric_summary:
            pieces.append(f"{key}={metric_summary[key]}")
    if not pieces and metric_summary:
        pieces.append(json.dumps(metric_summary, ensure_ascii=False))
    return "; ".join(pieces)


def _md_link(catalog_md_path: Path, backend_relative_path: str, label: str) -> str:
    if not backend_relative_path:
        return ""
    target = _resolve_catalog_path(backend_relative_path)
    # Catalog markdown can be rendered in tests or operator scratch dirs outside
    # BACKEND_ROOT, so compute a real relative link instead of assuming backend
    # ancestry.
    try:
        href = os.path.relpath(target.resolve(), start=catalog_md_path.parent.resolve())
    except (OSError, ValueError):
        href = str(target)
    href = href.replace(os.sep, "/")
    return f"[{label}]({href})"


def _table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        safe = [str(cell).replace("\n", "<br>").replace("|", "\\|") for cell in row]
        lines.append("| " + " | ".join(safe) + " |")
    return "\n".join(lines)


def write_markdown_catalog(catalog: dict[str, Any], *, catalog_md_path: Path = DEFAULT_CATALOG_MD) -> None:
    status_order = [
        ("current_formal_evidence", "Current Formal Evidence"),
        ("quality_audit", "Quality Audits"),
        ("historical_evidence", "Historical Evidence"),
        ("superseded", "Superseded Evidence"),
        ("failed_diagnostic", "Failed Diagnostics"),
        ("invalidated_diagnostic", "Invalidated Diagnostics"),
    ]
    entries = list(catalog.get("entries") or [])
    lines = [
        "# Evaluation Evidence Catalog",
        "",
        "This checked-in catalog indexes meaningful evaluation evidence. Raw machine outputs remain under `eval/runs/`; local/private text-bearing datasets remain under `state/eval_local_datasets/`; human interpretation reports remain under `docs/evaluation/`.",
        "",
        f"- Schema version: `{catalog.get('schema_version', SCHEMA_VERSION)}`",
        f"- Last updated: `{catalog.get('updated_at', '')}`",
        "",
        "## Status Meanings",
        "",
        "- `current_formal_evidence`: current evidence for an active benchmark surface.",
        "- `quality_audit`: focused quality audit that informs mechanism work but is not a formal benchmark score.",
        "- `historical_evidence`: preserved evidence from an older but still valid methodology.",
        "- `superseded`: preserved evidence replaced by a newer active run or benchmark contract.",
        "- `failed_diagnostic` / `invalidated_diagnostic`: failure evidence useful for debugging, not mechanism-quality evidence.",
    ]
    for status, heading in status_order:
        rows: list[list[str]] = []
        for entry in entries:
            if entry.get("status") != status:
                continue
            run_paths = entry.get("run_paths") if isinstance(entry.get("run_paths"), dict) else {}
            links = [
                _md_link(catalog_md_path, run_paths.get("run_dir", ""), "run dir"),
                _md_link(catalog_md_path, run_paths.get("aggregate", ""), "aggregate"),
                _md_link(catalog_md_path, run_paths.get("report", ""), "report"),
            ]
            analysis_docs = run_paths.get("analysis_docs") if isinstance(run_paths.get("analysis_docs"), list) else []
            links.extend(
                _md_link(catalog_md_path, str(path), f"analysis {idx}")
                for idx, path in enumerate(analysis_docs, 1)
            )
            links = [link for link in links if link]
            rows.append(
                [
                    f"`{entry.get('run_id')}`",
                    str(entry.get("surface", "")),
                    str(entry.get("evaluation_goal", "")),
                    ", ".join(f"`{item}`" for item in entry.get("mechanisms", [])),
                    _display_metric_summary(entry.get("metric_summary") or {}),
                    str(entry.get("one_line_conclusion", "")),
                    " · ".join(links),
                ]
            )
        lines.extend(["", f"## {heading}", ""])
        if rows:
            lines.append(
                _table(
                    ["run id", "surface", "goal", "mechanisms", "metrics", "conclusion", "evidence"],
                    rows,
                )
            )
        else:
            lines.append("_No entries._")
    catalog_md_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_md_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def validate_catalog(*, catalog_json_path: Path = DEFAULT_CATALOG_JSON) -> list[str]:
    catalog = _read_catalog(catalog_json_path)
    errors: list[str] = []
    seen: set[tuple[str, str]] = set()
    for idx, entry in enumerate(catalog.get("entries") or [], 1):
        run_id = str(entry.get("run_id") or "")
        surface = str(entry.get("surface") or "")
        status = str(entry.get("status") or "")
        key = (run_id, surface)
        if not run_id:
            errors.append(f"entry {idx}: missing run_id")
        if not surface:
            errors.append(f"entry {idx}: missing surface")
        if key in seen:
            errors.append(f"entry {idx}: duplicate run_id+surface {key}")
        seen.add(key)
        if status not in ALLOWED_STATUSES:
            errors.append(f"entry {idx}: invalid status {status!r}")
        run_paths = entry.get("run_paths")
        if not isinstance(run_paths, dict):
            errors.append(f"entry {idx}: run_paths must be an object")
            continue
        run_dir = run_paths.get("run_dir")
        if run_dir and not _path_exists(str(run_dir)):
            errors.append(f"entry {idx}: missing run_dir {run_dir}")
        aggregate = run_paths.get("aggregate")
        report = run_paths.get("report")
        if status in FORMAL_STATUSES:
            if not aggregate or not _path_exists(str(aggregate)):
                errors.append(f"entry {idx}: formal evidence requires aggregate path")
            if not report or not _path_exists(str(report)):
                errors.append(f"entry {idx}: formal evidence requires report path")
        for path_key, path_value in run_paths.items():
            if isinstance(path_value, str) and path_value and not _path_exists(path_value):
                errors.append(f"entry {idx}: missing {path_key} path {path_value}")
            elif isinstance(path_value, list):
                for item in path_value:
                    if item and not _path_exists(str(item)):
                        errors.append(f"entry {idx}: missing {path_key} path {item}")
        for path_key in ("dataset_path", "manifest_path"):
            path_value = entry.get(path_key)
            if path_value and not _path_exists(str(path_value)):
                errors.append(f"entry {idx}: missing {path_key} {path_value}")
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog-json", type=Path, default=DEFAULT_CATALOG_JSON)
    parser.add_argument("--catalog-md", type=Path, default=DEFAULT_CATALOG_MD)
    parser.add_argument("--check", action="store_true", help="Validate the catalog and exit.")
    subparsers = parser.add_subparsers(dest="command")

    upsert = subparsers.add_parser("upsert", help="Create or update one catalog entry.")
    upsert.add_argument("--run-id", required=True)
    upsert.add_argument("--surface", required=True)
    upsert.add_argument("--status", choices=sorted(ALLOWED_STATUSES), required=True)
    upsert.add_argument("--run-dir", default=None)
    upsert.add_argument("--evaluation-goal", default=None)
    upsert.add_argument("--dataset-id", default=None)
    upsert.add_argument("--dataset-path", default=None)
    upsert.add_argument("--manifest-path", default=None)
    upsert.add_argument("--mechanism", dest="mechanisms", action="append", default=[])
    upsert.add_argument("--metric", dest="metrics", action="append", default=[])
    upsert.add_argument("--job-id", dest="job_ids", action="append", default=[])
    upsert.add_argument("--one-line-conclusion", default=None)
    upsert.add_argument("--analysis-doc", dest="analysis_docs", action="append", default=[])
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    catalog_json_path = Path(args.catalog_json).resolve()
    catalog_md_path = Path(args.catalog_md).resolve()
    if args.check:
        errors = validate_catalog(catalog_json_path=catalog_json_path)
        if errors:
            print("\n".join(errors), file=sys.stderr)
            return 1
        catalog = _read_catalog(catalog_json_path)
        write_markdown_catalog(catalog, catalog_md_path=catalog_md_path)
        print(f"catalog ok: {catalog_json_path}")
        return 0
    if args.command == "upsert":
        entry = build_entry(
            run_id=str(args.run_id),
            surface=str(args.surface),
            status=str(args.status),
            run_dir=args.run_dir,
            evaluation_goal=args.evaluation_goal,
            dataset_id=args.dataset_id,
            dataset_path=args.dataset_path,
            manifest_path=args.manifest_path,
            mechanisms=[str(item) for item in args.mechanisms],
            metric_overrides=_parse_key_value(args.metrics),
            job_ids=[str(item) for item in args.job_ids],
            one_line_conclusion=args.one_line_conclusion,
            analysis_docs=[str(item) for item in args.analysis_docs],
        )
        upsert_catalog_entry(entry, catalog_json_path=catalog_json_path, catalog_md_path=catalog_md_path)
        print(json.dumps(entry, ensure_ascii=False, indent=2))
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

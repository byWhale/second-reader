"""Run the curated offline benchmark for subsegment planning."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from eval.common.taxonomy import (
    DETERMINISTIC_METRICS,
    DIRECT_QUALITY,
    LOCAL_IMPACT,
    PAIRWISE_JUDGE,
    TARGET_SUBSEGMENT_SEGMENTATION,
    normalize_methods,
    normalize_scopes,
    validate_target_slug,
)
from eval.subsegment.dataset import BenchmarkCase, BenchmarkDataset, load_benchmark_dataset
from eval.subsegment.judge import judge_downstream_pairwise, judge_plan_pairwise
from eval.subsegment.report import build_markdown_report
from src.iterator_reader.llm_utils import eval_trace_context, llm_invocation_scope
from src.iterator_reader.policy import chapter_budget, default_budget_policy, resolve_skill_policy, segment_budget
from src.iterator_reader.reader import _estimate_tokens, create_reader_state, plan_reader_subsegments, run_reader_segment


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET_DIR = ROOT / "eval" / "datasets" / "subsegment_benchmark_v1"
DEFAULT_RUNS_ROOT = ROOT / "eval" / "runs" / "subsegment"
DEFAULT_USER_INTENT = (
    "Read as a thoughtful co-reader and notice meaningful definitions, turns, causal links, and callbacks."
)
DEFAULT_TARGET = validate_target_slug(TARGET_SUBSEGMENT_SEGMENTATION)
DEFAULT_SCOPES = normalize_scopes([DIRECT_QUALITY])
STRATEGIES = ("heuristic_only", "llm_primary")
COMPARISON_TARGET = "`heuristic_only` vs `llm_primary` on curated subsegment benchmark cases"
RUBRIC_SUMMARY_BY_SCOPE = {
    DIRECT_QUALITY: [
        "Direct Quality (subsegment slicing): self-containedness, minimal sufficiency, one primary reading move.",
    ],
    LOCAL_IMPACT: [
        "Local Impact (section-level carry-through): reaction focus, source-anchor quality, coverage of meaningful turns/definitions/callbacks, coherence after merge.",
    ],
}

JudgeFn = Callable[..., dict[str, Any]]


def _json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _case_to_dict(case: BenchmarkCase) -> dict[str, Any]:
    return asdict(case)


def _build_eval_budget(segment_timeout_seconds: int | None = None) -> dict[str, Any]:
    policy = default_budget_policy()
    policy["max_search_queries_per_segment"] = 0
    policy["max_search_queries_per_chapter"] = 0
    policy["segment_timeout_seconds"] = max(1, int(segment_timeout_seconds or 45))
    chapter_state = chapter_budget(policy)
    return segment_budget(chapter_state, policy)


def _build_reader_state(
    case: BenchmarkCase,
    dataset: BenchmarkDataset,
    strategy: str,
    *,
    segment_timeout_seconds: int | None = None,
) -> dict[str, Any]:
    return create_reader_state(
        chapter_title=case.chapter_title,
        segment_id=case.segment_id,
        segment_summary=case.segment_summary,
        segment_text=case.segment_text,
        memory={},
        output_language=case.output_language,
        user_intent=dataset.default_user_intent or DEFAULT_USER_INTENT,
        skill_policy=resolve_skill_policy("balanced"),
        budget=_build_eval_budget(segment_timeout_seconds),
        max_revisions=0,
        segment_ref=case.segment_ref,
        book_title=case.book_title,
        author=case.author,
        chapter_ref=case.chapter_ref,
        chapter_index=case.chapter_index,
        total_chapters=case.total_chapters,
        primary_role=case.primary_role,
        role_tags=case.role_tags,
        role_confidence=case.role_confidence,
        section_heading=case.section_heading,
        nearby_outline=case.nearby_outline,
        subsegment_strategy_override=strategy,  # type: ignore[arg-type]
    )


def _planner_invalid(diagnostics: dict[str, Any]) -> bool:
    failure = str(diagnostics.get("planner_failure_reason", "")).strip()
    return failure in {
        "non_dict_payload",
        "payload_not_dict",
        "missing_units",
        "too_many_units",
        "unit_not_dict",
        "invalid_sentence_bounds",
        "non_contiguous_sentence_coverage",
        "invalid_reading_move",
        "oversized_or_empty_unit",
        "incomplete_sentence_coverage",
    }


def _base_strategy_result(case_id: str, strategy: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "strategy": strategy,
        "failed": False,
        "error": "",
        "planner_source": "",
        "subsegments": [],
        "diagnostics": {},
        "rendered": {},
        "metrics": {},
    }


def _strategy_direct_result(
    case: BenchmarkCase,
    dataset: BenchmarkDataset,
    strategy: str,
    *,
    segment_timeout_seconds: int | None = None,
) -> dict[str, Any]:
    state = _build_reader_state(case, dataset, strategy, segment_timeout_seconds=segment_timeout_seconds)
    result = _base_strategy_result(case.case_id, strategy)
    try:
        plan, final_state = plan_reader_subsegments(state)
    except Exception as exc:
        result["failed"] = True
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result

    diagnostics = dict(final_state.get("subsegment_plan_diagnostics", {}))
    unit_tokens = [_estimate_tokens(str(item.get("text", ""))) for item in plan if str(item.get("text", "")).strip()]
    result["planner_source"] = final_state.get("subsegment_planner_source", "")
    result["subsegments"] = plan
    result["diagnostics"] = diagnostics
    result["metrics"] = {
        "unit_count": len(plan),
        "avg_unit_tokens": (sum(unit_tokens) / len(unit_tokens)) if unit_tokens else 0.0,
        "fallback_used": final_state.get("subsegment_planner_source") == "fallback",
        "invalid_plan": _planner_invalid(diagnostics),
        "timed_out": False,
    }
    return result


def _strategy_local_impact_result(
    case: BenchmarkCase,
    dataset: BenchmarkDataset,
    strategy: str,
    *,
    segment_timeout_seconds: int | None = None,
) -> dict[str, Any]:
    state = _build_reader_state(case, dataset, strategy, segment_timeout_seconds=segment_timeout_seconds)
    result = _base_strategy_result(case.case_id, strategy)
    try:
        rendered, final_state = run_reader_segment(state)
    except Exception as exc:
        result["failed"] = True
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result

    plan = list(final_state.get("subsegment_plan", []))
    diagnostics = dict(final_state.get("subsegment_plan_diagnostics", {}))
    budget = dict(final_state.get("budget", {}))
    unit_tokens = [_estimate_tokens(str(item.get("text", ""))) for item in plan if str(item.get("text", "")).strip()]
    result["planner_source"] = final_state.get("subsegment_planner_source", "")
    result["subsegments"] = plan
    result["diagnostics"] = diagnostics
    result["rendered"] = rendered
    result["metrics"] = {
        "unit_count": len(plan),
        "avg_unit_tokens": (sum(unit_tokens) / len(unit_tokens)) if unit_tokens else 0.0,
        "fallback_used": final_state.get("subsegment_planner_source") == "fallback",
        "invalid_plan": _planner_invalid(diagnostics),
        "timed_out": bool(budget.get("segment_timed_out", False)),
    }
    return result


def _select_cases(
    dataset: BenchmarkDataset,
    *,
    core_only: bool,
    limit: int | None,
    case_ids: list[str] | None = None,
) -> list[BenchmarkCase]:
    if case_ids:
        by_id = {case.case_id: case for case in dataset.cases}
        unknown = [case_id for case_id in case_ids if case_id not in by_id]
        if unknown:
            raise ValueError(f"unknown benchmark case ids: {', '.join(unknown)}")
        return [by_id[case_id] for case_id in case_ids]

    case_ids = dataset.core_case_ids if core_only else dataset.core_case_ids + dataset.audit_case_ids
    cases = [case for case in dataset.cases if case.case_id in case_ids]
    cases.sort(key=lambda item: case_ids.index(item.case_id))
    if limit is not None:
        return cases[: max(0, int(limit))]
    return cases


def _scope_result(
    scope: str,
    *,
    case: BenchmarkCase,
    dataset: BenchmarkDataset,
    judge_mode: str,
    direct_judge: JudgeFn,
    local_impact_judge: JudgeFn,
    segment_timeout_seconds: int | None,
) -> dict[str, Any]:
    if scope == DIRECT_QUALITY:
        strategies = {
            strategy: _strategy_direct_result(
                case,
                dataset,
                strategy,
                segment_timeout_seconds=segment_timeout_seconds,
            )
            for strategy in STRATEGIES
        }
        judgment = (
            {"winner": "tie", "reason": "judge_disabled"}
            if judge_mode == "none"
            else direct_judge(
                segment_text=case.segment_text,
                segment_summary=case.segment_summary,
                left_label="heuristic_only",
                left_units=strategies["heuristic_only"].get("subsegments", []),
                right_label="llm_primary",
                right_units=strategies["llm_primary"].get("subsegments", []),
            )
        )
    else:
        strategies = {
            strategy: _strategy_local_impact_result(
                case,
                dataset,
                strategy,
                segment_timeout_seconds=segment_timeout_seconds,
            )
            for strategy in STRATEGIES
        }
        judgment = (
            {"winner": "tie", "reason": "judge_disabled"}
            if judge_mode == "none"
            else local_impact_judge(
                segment_text=case.segment_text,
                segment_summary=case.segment_summary,
                left_label="heuristic_only",
                left_rendered=strategies["heuristic_only"].get("rendered", {}),
                right_label="llm_primary",
                right_rendered=strategies["llm_primary"].get("rendered", {}),
            )
        )

    return {
        "scope": scope,
        "strategies": strategies,
        "judgment": judgment,
        "rubric_summary": list(RUBRIC_SUMMARY_BY_SCOPE.get(scope, [])),
    }


def _scope_metrics(case_results: list[dict[str, Any]], scope: str) -> dict[str, Any]:
    scoped = [
        item["scope_results"][scope]
        for item in case_results
        if scope in item.get("scope_results", {})
    ]

    def _strategy_cases(name: str) -> list[dict[str, Any]]:
        return [item["strategies"][name] for item in scoped if name in item.get("strategies", {})]

    llm_results = _strategy_cases("llm_primary")
    heuristic_results = _strategy_cases("heuristic_only")
    llm_total = max(1, len(llm_results))
    heuristic_total = max(1, len(heuristic_results))

    return {
        "case_count": len(scoped),
        "llm_fallback_rate": sum(1 for item in llm_results if item.get("metrics", {}).get("fallback_used")) / llm_total,
        "llm_invalid_plan_rate": sum(1 for item in llm_results if item.get("metrics", {}).get("invalid_plan")) / llm_total,
        "llm_failure_rate": sum(
            1 for item in llm_results if item.get("failed") or item.get("metrics", {}).get("timed_out")
        ) / llm_total,
        "heuristic_failure_rate": sum(
            1 for item in heuristic_results if item.get("failed") or item.get("metrics", {}).get("timed_out")
        ) / heuristic_total,
        "llm_avg_unit_count": sum(item.get("metrics", {}).get("unit_count", 0) for item in llm_results) / llm_total,
        "heuristic_avg_unit_count": sum(item.get("metrics", {}).get("unit_count", 0) for item in heuristic_results)
        / heuristic_total,
    }


def _aggregate(
    *,
    target: str,
    scopes: list[str],
    methods: list[str],
    dataset: BenchmarkDataset,
    cases: list[BenchmarkCase],
    case_results: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "target": target,
        "scopes": list(scopes),
        "methods": list(methods),
        "comparison_target": COMPARISON_TARGET,
        "dataset_id": dataset.dataset_id,
        "dataset_version": dataset.version,
        "case_count": len(case_results),
        "core_case_count": sum(1 for item in case_results if item.get("split") == "core"),
        "audit_case_count": sum(1 for item in case_results if item.get("split") == "audit"),
        "dataset_case_count": len(dataset.cases),
        "selected_case_ids": [case.case_id for case in cases],
        "scope_metrics": {
            scope: _scope_metrics(case_results, scope)
            for scope in scopes
        },
    }


def run_benchmark(
    *,
    dataset_dir: str | Path = DEFAULT_DATASET_DIR,
    runs_root: str | Path = DEFAULT_RUNS_ROOT,
    report_path: str | Path | None = None,
    run_id: str | None = None,
    case_ids: list[str] | None = None,
    core_only: bool = False,
    limit: int | None = None,
    scopes: list[str] | None = None,
    judge_mode: str = "llm",
    include_local_impact: bool = False,
    segment_timeout_seconds: int | None = None,
    direct_judge: JudgeFn | None = None,
    local_impact_judge: JudgeFn | None = None,
) -> dict[str, Any]:
    """Execute the offline benchmark and return the aggregate summary."""
    dataset = load_benchmark_dataset(dataset_dir)
    cases = _select_cases(dataset, core_only=core_only, limit=limit, case_ids=case_ids)
    if not cases:
        raise ValueError("no benchmark cases selected")

    target = DEFAULT_TARGET
    effective_scopes = normalize_scopes(
        scopes if scopes is not None else DEFAULT_SCOPES + ([LOCAL_IMPACT] if include_local_impact else [])
    )
    methods = normalize_methods(
        [DETERMINISTIC_METRICS] + ([PAIRWISE_JUDGE] if judge_mode != "none" else [])
    )

    run_name = run_id or datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_root = Path(runs_root) / run_name
    runtime_root = run_root / "runtime"
    runtime_root.mkdir(parents=True, exist_ok=True)
    _json_dump(
        run_root / "dataset_manifest.json",
        {
            "dataset_id": dataset.dataset_id,
            "dataset_version": dataset.version,
            "target": target,
            "scopes": effective_scopes,
            "methods": methods,
            "comparison_target": COMPARISON_TARGET,
            "selected_case_ids": [case.case_id for case in cases],
            "segment_timeout_seconds": max(1, int(segment_timeout_seconds or 45)),
            "case_ids": list(case_ids or []),
            "core_only": core_only,
            "limit": limit,
            "judge_mode": judge_mode,
        },
    )

    effective_direct_judge = direct_judge if direct_judge is not None else judge_plan_pairwise
    effective_local_impact_judge = (
        local_impact_judge if local_impact_judge is not None else judge_downstream_pairwise
    )

    with llm_invocation_scope(
        trace_context=eval_trace_context(
            run_root,
            eval_target=f"subsegment_benchmark:{run_name}",
        )
    ):
        case_results: list[dict[str, Any]] = []
        for case in cases:
            _json_dump(run_root / "inputs" / f"{case.case_id}.json", _case_to_dict(case))
            scope_results: dict[str, Any] = {}
            for scope in effective_scopes:
                scoped = _scope_result(
                    scope,
                    case=case,
                    dataset=dataset,
                    judge_mode=judge_mode,
                    direct_judge=effective_direct_judge,
                    local_impact_judge=effective_local_impact_judge,
                    segment_timeout_seconds=segment_timeout_seconds,
                )
                scope_results[scope] = scoped
                for strategy, payload in scoped["strategies"].items():
                    _json_dump(
                        run_root / scope / "plans" / f"{case.case_id}.{strategy}.json",
                        {
                            "target": target,
                            "scope": scope,
                            "methods": methods,
                            "case_id": case.case_id,
                            "strategy": strategy,
                            "planner_source": payload.get("planner_source", ""),
                            "diagnostics": payload.get("diagnostics", {}),
                            "subsegments": payload.get("subsegments", []),
                            "metrics": payload.get("metrics", {}),
                            "runtime_root": str(runtime_root),
                        },
                    )
                    if scope == LOCAL_IMPACT:
                        _json_dump(
                            run_root / scope / "sections" / f"{case.case_id}.{strategy}.json",
                            payload.get("rendered", {}),
                        )

                _json_dump(run_root / scope / "judge" / f"{case.case_id}.json", scoped["judgment"])

            case_results.append(
                {
                    "case_id": case.case_id,
                    "split": case.split,
                    "segment_ref": case.segment_ref,
                    "tags": list(case.tags),
                    "scope_results": scope_results,
                }
            )

        aggregate = _aggregate(
            target=target,
            scopes=effective_scopes,
            methods=methods,
            dataset=dataset,
            cases=cases,
            case_results=case_results,
        )
        aggregate["segment_timeout_seconds"] = max(1, int(segment_timeout_seconds or 45))
        aggregate["case_ids"] = [case.case_id for case in cases]
        _json_dump(run_root / "summary" / "case_results.json", case_results)
        _json_dump(run_root / "summary" / "aggregate.json", aggregate)

        markdown = build_markdown_report(
            dataset_id=dataset.dataset_id,
            dataset_version=dataset.version,
            target=target,
            scopes=effective_scopes,
            methods=methods,
            comparison_target=COMPARISON_TARGET,
            rubric_summary_by_scope=RUBRIC_SUMMARY_BY_SCOPE,
            aggregate=aggregate,
            case_results=case_results,
        )
        final_report_path = Path(report_path) if report_path is not None else run_root / "summary" / "report.md"
        final_report_path.parent.mkdir(parents=True, exist_ok=True)
        final_report_path.write_text(markdown, encoding="utf-8")

        return {
            "run_id": run_name,
            "run_root": str(run_root),
            "report_path": str(final_report_path),
            "aggregate": aggregate,
            "case_results": case_results,
        }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the curated offline benchmark for subsegment planning.")
    parser.add_argument("--dataset-dir", default=str(DEFAULT_DATASET_DIR))
    parser.add_argument("--runs-root", default=str(DEFAULT_RUNS_ROOT))
    parser.add_argument("--report-path", default="")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--case-ids", default="")
    parser.add_argument("--scope", action="append", default=[])
    parser.add_argument("--judge-mode", choices=["llm", "none"], default="llm")
    parser.add_argument("--segment-timeout-seconds", type=int, default=0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--core-only", action="store_true")
    parser.add_argument("--include-local-impact", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    explicit_case_ids = [item.strip() for item in args.case_id if str(item).strip()]
    if args.case_ids:
        explicit_case_ids.extend([item.strip() for item in str(args.case_ids).split(",") if item.strip()])
    explicit_scopes = [item.strip() for item in args.scope if str(item).strip()]
    summary = run_benchmark(
        dataset_dir=args.dataset_dir,
        runs_root=args.runs_root,
        report_path=args.report_path or None,
        run_id=args.run_id or None,
        case_ids=explicit_case_ids or None,
        core_only=bool(args.core_only),
        limit=args.limit or None,
        scopes=explicit_scopes or None,
        judge_mode=args.judge_mode,
        include_local_impact=bool(args.include_local_impact),
        segment_timeout_seconds=args.segment_timeout_seconds or None,
    )
    print(json.dumps(summary["aggregate"], ensure_ascii=False, indent=2))
    print(f"run_root={summary['run_root']}")
    print(f"report_path={summary['report_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

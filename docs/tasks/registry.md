# Task Registry

Purpose: provide the canonical workspace task index for agent switching, routing, and traceability.
Use when: choosing what to work on next, recovering a task without chat history, or checking blockers, evidence, and linked truth docs.
Not for: full tracker detail, long-form design rationale, or mutable runtime job state.
Update when: task status, priority, blockers, decision refs, job refs, evidence refs, or next actions change.

This document is the human-readable companion to `docs/tasks/registry.json`.

Last updated: `2026-04-04T00:19:20Z`

## Status Values
- `active`
- `blocked`
- `queued`
- `waiting`
- `parked`
- `done`
- `cancelled`

## Active

### `TASK-PHASE9-CLUSTERED-BENCHMARK` — Freeze clustered benchmark v1 as the active Phase 9 evaluation surface
- Status: `active`
- Lane: `dataset_platform`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/clustered-benchmark-v1-draft.md`
- Next: use the completed English and Chinese smoke2 first-review job records plus imported dataset state as the freeze input, accept only `keep` cases without blocking problem types, top up deficit chapters from reserves only, freeze toward `10` primaries plus `2` reserves per chapter, and then relaunch decisive chapter/excerpt evaluation against the clustered active benchmark rather than the historical broad formal freeze
- Jobs:
  - `bgjob_clustered_benchmark_v1_first_review_en_20260403` (`completed`)
  - `bgjob_clustered_benchmark_v1_first_review_zh_20260403` (`completed`)

## Parked

### `TASK-RUNTIME-VIABILITY-GATES` — Keep runtime viability and non-mainline comparison lanes paused under the reduced eval scope
- Status: `parked`
- Lane: `mechanism_eval`
- Priority: `medium`
- Detail: `docs/implementation/new-reading-mechanism/execution-tracker.md`
- Next: reuse the existing runtime-viability and durable-trace evidence; do not relaunch those lanes unless one of the three kept north-star dimensions later requires them or the cost posture changes explicitly
- Jobs:
  - `bgjob_durable_trace_reentry_gate_20260401` (`failed`)
  - `bgjob_durable_trace_reentry_gate_parallel3_20260401` (`completed`)
  - `bgjob_durable_trace_reentry_gate_personal_serial_20260401` (`abandoned`)
  - `bgjob_runtime_viability_gate_20260401` (`completed`)
  - `bgjob_runtime_viability_gate_serialfix_20260401` (`completed`)

## Waiting

### `TASK-DATASET-QUESTION-ALIGNED-CASE-CONSTRUCTION` — Build question-aligned case construction for evaluation datasets
- Status: `waiting`
- Lane: `dataset_platform`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/execution-tracker.md`
- Next: keep the landed builder available as support infrastructure, but do not open a new general builder wave while `TASK-PHASE9-CLUSTERED-BENCHMARK` is active; the current builder output is already being consumed by the clustered first-review/freeze path; only resume broader construction work if later decisive eval results expose a specific blocker or if one explicitly scoped audit-stage-only reproducibility pass is requested
- Jobs:
  - `bgjob_closed_loop_en_broader_callbackpromptfix_20260331` (`completed`)
  - `bgjob_closed_loop_zh_callbacklookback_20260330` (`completed`)
  - `bgjob_closed_loop_zh_callbackpriorcontext_20260330` (`completed`)
  - `bgjob_closed_loop_zh_cueguard_20260330` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_callbackbridgefix_20260331` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_callbackcontentfix_20260331` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_callbackinferencefix_20260331` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_callbackfocusfix_20260331` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_tensionfocusfix_20260331` (`completed`)
  - `bgjob_callbackslice_auditv4_packet_20260331` (`failed`)
  - `bgjob_callbackslice_auditv4_packet_retry_quota_20260331` (`completed`)
  - `bgjob_callbackslice_probeonly_20260331` (`completed`)
  - `bgjob_callbackslice_auditrerun_20260331` (`completed`)

### `TASK-DATASET-FULL-AUTOMATION` — Make dataset building fully automated as one closed build-review-refine loop
- Status: `waiting`
- Lane: `dataset_platform`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/execution-tracker.md`
- Next: keep the bounded controller scratch-safe and reusable, but do not widen automation while decisive mechanism-eval work is active; with current model cost pressure, do not spend on non-mainline comparison support loops; resume only if later work needs one explicitly scoped audit-stage-only reproducibility pass or another concrete support-lane unblocker
- Jobs:
  - `bgjob_closed_loop_en_broader_callbackpromptfix_20260331` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_callbackpromptfix_20260331` (`failed`)
  - `bgjob_callbackslice_auditv4_packet_20260331` (`failed`)
  - `bgjob_callbackslice_auditv4_packet_retry_quota_20260331` (`completed`)
  - `bgjob_callbackslice_probeonly_20260331` (`completed`)
  - `bgjob_callbackslice_auditrerun_20260331` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_callbackfocusfix_20260331` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_tensionfocusfix_20260331` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_callbackinferencefix_20260331` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_callbackcontentfix_20260331` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_callbackbridgefix_20260331` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_whitespacefix_20260331` (`completed`)
  - `bgjob_closed_loop_en_broader_whitespacefix_20260331` (`completed`)
  - `bgjob_closed_loop_en_henry_whitespacefix_20260331` (`completed`)
  - `bgjob_closed_loop_en_broader_auditconsensusv3_20260331` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_auditconsensusv3_20260331` (`completed`)
  - `bgjob_closed_loop_en_broader_auditcontractv3_20260331` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_auditcontractv3_20260331` (`completed`)
  - `bgjob_closed_loop_en_broader_auditcontractv2_20260331` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_auditcontractv2_20260331` (`completed`)
  - `bgjob_closed_loop_en_broader_auditpair_20260331` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_auditpair_20260331` (`completed`)
  - `bgjob_closed_loop_en_broader_adjudicationv4_20260331` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_adjudicationv4_20260331` (`completed`)
  - `bgjob_closed_loop_en_broader_compactadjudication_20260330` (`completed`)
  - `bgjob_closed_loop_en_broader_compactadjudication_repeat_20260330` (`failed`)
  - `bgjob_closed_loop_en_broader_compactadjudication_repeat_resume_20260330` (`completed`)
  - `bgjob_packet_adjudication_probe_en_compactrepeat_20260330` (`completed`)
  - `bgjob_packet_adjudication_probe_en_compactrepeat_compactauditv2_20260330` (`completed`)
  - `bgjob_closed_loop_en_broader_auditsemanticretry_20260330` (`completed`)
  - `bgjob_closed_loop_en_broader_auditcoherencefix_repeat_20260330` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_auditcoherencefix_20260330` (`completed`)

## Queued

### `TASK-DOC-Q10` — Decide when to promote `attentional_v2` working design into stable docs
- Status: `queued`
- Lane: `documentation`
- Priority: `medium`
- Detail: `docs/implementation/new-reading-mechanism/open-questions.md`
- Blocked by: `TASK-PHASE9-CLUSTERED-BENCHMARK`
- Next: resolve `Q10` once benchmark stabilization has settled enough to freeze stable mechanism behavior intentionally

### `TASK-FE-SECTION-RETIREMENT` — Retire section-first chapter/detail and marks surfaces
- Status: `queued`
- Lane: `migration`
- Priority: `medium`
- Detail: `docs/implementation/new-reading-mechanism/execution-tracker.md`
- Blocked by: `TASK-PHASE9-CLUSTERED-BENCHMARK`, `TASK-DOC-Q10`
- Next: start only after benchmark direction, runtime viability work, and stable-doc promotion timing are intentionally fixed

## Done

### `TASK-BENCH-BACKLOG-RESCUE` — Apply the round-2 backlog-rescue decision from the modern supplement
- Status: `done`
- Lane: `dataset_growth`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/private-library-promotion-round2.md`
- Next: keep the recorded `hold_for_backlog_rescue` outcome in force, do not reopen promotion without genuinely new benchmark-strengthening evidence, and treat the completed gate review as the route-back-to-mainline checkpoint
- Jobs: none

### `TASK-BENCH-ROUND3-CLEANUP` — Finish private-library cleanup and write the round-2 promotion draft
- Status: `done`
- Lane: `dataset_growth`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/execution-tracker.md`
- Next: use the landed round-2 draft plus the March 29 recovery summaries as the source of truth for the next dataset-growth move
- Jobs: none

### `TASK-BENCH-PROMOTION-ROUND2` — Decide the next benchmark-promotion move from the modern supplement
- Status: `done`
- Lane: `dataset_growth`
- Priority: `medium`
- Detail: `docs/implementation/new-reading-mechanism/private-library-promotion-round2.md`
- Next: keep the recorded `hold_for_backlog_rescue` decision in force until a human explicitly reopens the post-recovery gate discussion
- Jobs: none

### `TASK-MECH-EN-RERUN` — Run the focused English round-3 narrative/reference rerun
- Status: `done`
- Lane: `mechanism_eval`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/execution-tracker.md`
- Next: treat the completed backup-tier substantive rerun as evidence only; preserve the `walden` strength, keep the `up_from_slavery` chapter-arc weakness explicit, and do not launch default-cutover or promotion work automatically
- Jobs:
  - `bgjob_en_chapter_core_rerun_round3_caseiso_judged_followup_20260330` (`completed`)
  - `bgjob_en_chapter_core_rerun_round3_caseiso_judged_substantive_backup_20260331` (`completed`)

### `TASK-AGENT-SWITCHING-SYSTEM` — Land the repo-first agent-switching memory system
- Status: `done`
- Lane: `docs_tooling`
- Priority: `high`
- Detail: `docs/source-of-truth-map.md`
- Next: keep `docs/current-state.md` and `docs/tasks/registry.*` updated whenever live work changes

### `TASK-DATASET-SOURCE-GOVERNANCE` — Make source-book intake and intermediate artifacts clear and durable
- Status: `done`
- Lane: `dataset_platform`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/execution-tracker.md`
- Next: keep using the managed inbox plus source catalog as the source of truth for future book additions, and treat public/private only as compatibility metadata instead of a primary workflow branch
- Jobs: none

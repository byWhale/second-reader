# Task Registry

Purpose: provide the canonical workspace task index for agent switching, routing, and traceability.
Use when: choosing what to work on next, recovering a task without chat history, or checking blockers, evidence, and linked truth docs.
Not for: full tracker detail, long-form design rationale, or mutable runtime job state.
Update when: task status, priority, blockers, decision refs, job refs, evidence refs, or next actions change.

This document is the human-readable companion to `docs/tasks/registry.json`.

Last updated: `2026-04-06T11:41:52Z`

## Status Values
- `active`
- `blocked`
- `queued`
- `waiting`
- `parked`
- `done`
- `cancelled`

## Active

### `TASK-PHASE9-DECISIVE-EVAL` — Run the split-surface Phase 9 evaluation lanes
- Status: `active`
- Lane: `mechanism_eval`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/execution-tracker.md`
- Next: treat the completed dual-pool recovery retry3 plus explicit merge as partial evidence only; the bounded `attentional_v2` throughput repair and judged ROI-first micro-slice remain the mechanism-repair proof, and the formal `excerpt surface v1.1` lane is now also complete with machine aggregate/report plus a human interpretation report. The only still-running mainline lane is the judged long-span accumulation comparison; once it finishes, compare it against the now-complete excerpt evidence bundle and decide whether the next move is a narrow `attentional_v2` local-anchor repair or the larger excerpt-surface ROI retune.
- Jobs:
  - `bgjob_human_notes_excerpt_smoke_light_20260404` (`completed`)
  - `bgjob_human_notes_guided_excerpt_eval_v1_judged_20260404` (`completed`)
  - `bgjob_human_notes_guided_excerpt_eval_v1_judged_personal_rerun_20260405` (`abandoned`)
  - `bgjob_human_notes_excerpt_parallel_smoke_20260405` (`abandoned`)
  - `bgjob_human_notes_excerpt_parallel_judged_shard_a_20260405` (`failed`)
  - `bgjob_human_notes_excerpt_parallel_judged_shard_b_20260405` (`failed`)
  - `bgjob_human_notes_excerpt_parallel_judged_shard_a_retry1_20260405` (`failed`)
  - `bgjob_human_notes_excerpt_parallel_judged_shard_b_retry1_20260405` (`failed`)
  - `bgjob_human_notes_excerpt_parallel_judged_shard_a_dualpool_recovery_20260405` (`failed`)
  - `bgjob_human_notes_excerpt_parallel_judged_shard_b_dualpool_recovery_20260405` (`failed`)
  - `bgjob_human_notes_excerpt_parallel_judged_shard_a_dualpool_recovery_retry2_20260405` (`abandoned`)
  - `bgjob_human_notes_excerpt_parallel_judged_shard_b_dualpool_recovery_retry2_20260405` (`abandoned`)
  - `bgjob_human_notes_excerpt_parallel_judged_shard_a_dualpool_recovery_retry3_20260405` (`completed`)
  - `bgjob_human_notes_excerpt_parallel_judged_shard_b_dualpool_recovery_retry3_20260405` (`completed`)
  - `bgjob_attentional_v2_excerpt_micro_slice_smoke_20260405` (`completed`)
  - `bgjob_attentional_v2_excerpt_micro_slice_judged_20260405` (`completed`)
  - `bgjob_excerpt_surface_v1_1_judged_shard_a_20260406` (`completed`)
  - `bgjob_excerpt_surface_v1_1_judged_shard_b_20260406` (`completed`)
  - `bgjob_excerpt_surface_v1_1_judged_shard_c_20260406` (`completed`)
  - `bgjob_excerpt_surface_v1_1_judged_shard_d_20260406` (`completed`)
  - `bgjob_excerpt_surface_v1_1_eval_orchestrator_unitready_retry1_20260406` (`completed`)
  - `bgjob_excerpt_surface_v1_1_smoke_supremacy_recovery_20260406` (`completed`)

### `TASK-ACCUMULATION-BENCHMARK-V1` — Build the bounded long-span window benchmark for `coherent_accumulation`
- Status: `active`
- Lane: `dataset_platform`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/execution-tracker.md`
- Next: keep the honest-short freeze as the active long-span draft and use it now: `huochu_shengming_de_yiyi_private_zh__8` and its `2` revise probes are removed from the mainline, leaving `5` active windows and `7` frozen probes. The judged accumulation lane is now the only active background eval job; the next check is to confirm that it emits the merged `aggregate/report` outputs cleanly and then compare it against the already completed excerpt evidence bundle.
- Jobs:
  - `bgjob_accumulation_benchmark_v1_first_review_20260404` (`completed`)
  - `bgjob_accumulation_benchmark_v1_rejudged_first_review_20260404` (`completed`)
  - `bgjob_accumulation_benchmark_v1_repair_first_review_20260405` (`completed`)
  - `bgjob_accumulation_benchmark_v1_judged_20260406` (`running`)

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
- Next: keep the landed builder available as support infrastructure, but do not open a new general builder wave while `TASK-PHASE9-DECISIVE-EVAL` and `TASK-ACCUMULATION-BENCHMARK-V1` are active; broader construction should resume only if later decisive eval results expose a specific blocker or if one explicitly scoped audit-stage-only reproducibility pass is requested
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
- Blocked by: `TASK-PHASE9-DECISIVE-EVAL`
- Next: resolve `Q10` once benchmark stabilization has settled enough to freeze stable mechanism behavior intentionally

### `TASK-FE-SECTION-RETIREMENT` — Retire section-first chapter/detail and marks surfaces
- Status: `queued`
- Lane: `migration`
- Priority: `medium`
- Detail: `docs/implementation/new-reading-mechanism/execution-tracker.md`
- Blocked by: `TASK-PHASE9-DECISIVE-EVAL`, `TASK-DOC-Q10`
- Next: start only after benchmark direction, runtime viability work, and stable-doc promotion timing are intentionally fixed

## Done

### `TASK-EXCERPT-SURFACE-V1.1` — Retune the next excerpt surface incrementally from the notes-guided freeze
- Status: `done`
- Lane: `dataset_platform`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/excerpt-surface-v1-1-draft.md`
- Next: keep `excerpt surface v1.1` frozen with its explicit `5`-case exception on `nawaer_baodian_private_zh__22`; treat the completed formal judged run plus the new interpretation report as the durable excerpt evidence bundle, and start the next excerpt work from narrow `attentional_v2` local-anchor repair plus later ROI retune rather than rerunning this lane.
- Jobs:
  - `bgjob_excerpt_surface_v1_1_smoke_shard_a_20260406` (`completed`)
  - `bgjob_excerpt_surface_v1_1_smoke_shard_b_20260406` (`completed`)
  - `bgjob_excerpt_surface_v1_1_eval_orchestrator_20260406` (`abandoned`)
  - `bgjob_excerpt_surface_v1_1_eval_orchestrator_reshard4_20260406` (`abandoned`)
  - `bgjob_excerpt_surface_v1_1_eval_orchestrator_unitready_20260406` (`failed`)
  - `bgjob_excerpt_surface_v1_1_eval_orchestrator_unitready_retry1_20260406` (`completed`)
  - `bgjob_excerpt_surface_v1_1_judged_shard_a_20260406` (`completed`)
  - `bgjob_excerpt_surface_v1_1_judged_shard_b_20260406` (`completed`)
  - `bgjob_excerpt_surface_v1_1_judged_shard_c_20260406` (`completed`)
  - `bgjob_excerpt_surface_v1_1_judged_shard_d_20260406` (`completed`)
  - `bgjob_excerpt_surface_v1_1_smoke_supremacy_recovery_20260406` (`completed`)

### `TASK-DATASET-HUMAN-NOTES-GUIDED-V1` — Land the isolated human-notes-guided dataset line from the 5 linked books
- Status: `done`
- Lane: `dataset_platform`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/human-notes-guided-dataset-v1-freeze-draft.md`
- Next: keep the completed `55`-row reviewed freeze stable as the current judged excerpt surface and as base material for `excerpt surface v1.1`; do not repoint the active benchmark automatically from this line alone
- Jobs:
  - `bgjob_human_notes_guided_dataset_v1_scratch_20260404` (`failed`)
  - `bgjob_human_notes_guided_dataset_v1_scratch_retry1_20260404` (`completed`)
  - `bgjob_human_notes_guided_dataset_v1_scratch_retry2_20260404` (`completed`)
  - `bgjob_human_notes_guided_dataset_v1_scratch_retry3_20260404` (`completed`)
  - `bgjob_human_notes_guided_dataset_v1_first_review_en_20260404` (`failed`)
  - `bgjob_human_notes_guided_dataset_v1_first_review_zh_20260404` (`failed`)
  - `bgjob_human_notes_guided_dataset_v1_first_review_en_retry1_20260404` (`failed`)
  - `bgjob_human_notes_guided_dataset_v1_first_review_en_retry2_20260404` (`completed`)
  - `bgjob_human_notes_guided_dataset_v1_first_review_zh_retry1_20260404` (`completed`)

### `TASK-PHASE9-CLUSTERED-BENCHMARK` — Freeze clustered benchmark v1 as the active Phase 9 evaluation surface
- Status: `done`
- Lane: `dataset_platform`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/clustered-benchmark-v1-draft.md`
- Next: keep the frozen clustered benchmark as the active Phase 9 evaluation surface, preserve the honest `reserve = 7 / 8` shortfall, and move back to decisive mechanism-eval rather than reopening builder widening by default
- Jobs:
  - `bgjob_clustered_benchmark_v1_first_review_en_20260403` (`completed`)
  - `bgjob_clustered_benchmark_v1_first_review_zh_20260403` (`completed`)
  - `bgjob_clustered_benchmark_v1_reserve_review_en_20260404` (`completed`)
  - `bgjob_clustered_benchmark_v1_reserve_review_zh_20260404` (`completed`)

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

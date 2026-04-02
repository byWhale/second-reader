# Task Registry

Purpose: provide the canonical workspace task index for agent switching, routing, and traceability.
Use when: choosing what to work on next, recovering a task without chat history, or checking blockers, evidence, and linked truth docs.
Not for: full tracker detail, long-form design rationale, or mutable runtime job state.
Update when: task status, priority, blockers, decision refs, job refs, evidence refs, or next actions change.

This document is the human-readable companion to `docs/tasks/registry.json`.

Last updated: `2026-04-02T06:16:49Z`

## Status Values
- `active`
- `blocked`
- `queued`
- `waiting`
- `parked`
- `done`
- `cancelled`

## Active

### `TASK-RUNTIME-VIABILITY-GATES` — Keep the minimal eval core focused on three north-star dimensions
- Status: `active`
- Lane: `mechanism_eval`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/execution-tracker.md`
- Next: use the updated explicit freeze draft at `reading-companion-backend/eval/manifests/splits/attentional_v2_formal_benchmark_v1_draft.json`; treat `chapter_core` as frozen in draft form and `excerpt_core` as `18 / 24` ready after the completed first tracked wave plus bounded reruns; keep `ouyou_zaji_public_zh__4__distinction_definition__v2`, `ershinian_mudu_public_zh__37__anchored_reaction_selectivity__v2`, `women_and_economics_public_en__9__distinction_definition__v2`, and `rulin_waishi_24032_zh__6__tension_reversal__v2` in the frozen-now slice; keep `portrait_of_a_lady_public_en__10__anchored_reaction_selectivity__v2` deferred; and use the planned Henry Adams local promotions as the next clean EN tension / anchored support lane
- Jobs:
  - `bgjob_durable_trace_reentry_gate_20260401` (`failed`)
  - `bgjob_durable_trace_reentry_gate_parallel3_20260401` (`completed`)
  - `bgjob_durable_trace_reentry_gate_personal_serial_20260401` (`abandoned`)
  - `bgjob_runtime_viability_gate_20260401` (`completed`)
  - `bgjob_runtime_viability_gate_serialfix_20260401` (`completed`)
  - `bgjob_formal_benchmark_v1_excerpt_wave1_en_20260402` (`completed`)
  - `bgjob_formal_benchmark_v1_excerpt_wave1_zh_20260402` (`completed`)
  - `bgjob_formal_benchmark_v1_excerpt_rerun_women_20260402` (`completed`)
  - `bgjob_formal_benchmark_v1_excerpt_rerun_rulin_20260402` (`completed`)

## Waiting

### `TASK-DATASET-QUESTION-ALIGNED-CASE-CONSTRUCTION` — Build question-aligned case construction for evaluation datasets
- Status: `waiting`
- Lane: `dataset_platform`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/execution-tracker.md`
- Next: keep the landed builder available as support infrastructure, but do not open a new general builder wave while `TASK-RUNTIME-VIABILITY-GATES` is active; with current model cost pressure, do not relaunch comparison-driven widening outside the mechanism mainline; only resume if later decisive eval work exposes a specific blocker or if one explicitly scoped audit-stage-only reproducibility pass is requested
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
- Blocked by: `TASK-RUNTIME-VIABILITY-GATES`
- Next: resolve `Q10` once benchmark stabilization has settled enough to freeze stable mechanism behavior intentionally

### `TASK-FE-SECTION-RETIREMENT` — Retire section-first chapter/detail and marks surfaces
- Status: `queued`
- Lane: `migration`
- Priority: `medium`
- Detail: `docs/implementation/new-reading-mechanism/execution-tracker.md`
- Blocked by: `TASK-RUNTIME-VIABILITY-GATES`, `TASK-DOC-Q10`
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

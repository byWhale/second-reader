# Task Registry

Purpose: provide the canonical workspace task index for agent switching, routing, and traceability.
Use when: choosing what to work on next, recovering a task without chat history, or checking blockers, evidence, and linked truth docs.
Not for: full tracker detail, long-form design rationale, or mutable runtime job state.
Update when: task status, priority, blockers, decision refs, job refs, evidence refs, or next actions change.

This document is the human-readable companion to `docs/tasks/registry.json`.

Last updated: `2026-03-30T12:42:11Z`

## Status Values
- `active`
- `blocked`
- `queued`
- `waiting`
- `parked`
- `done`
- `cancelled`

## Active

### `TASK-BENCH-BACKLOG-RESCUE` — Apply the round-2 backlog-rescue decision from the modern supplement
- Status: `active`
- Lane: `dataset_growth`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/private-library-promotion-round2.md`
- Next: keep the post-cleanup gate on `hold`, treat the `0`-new-keep follow-up result as the new benchmark-hardening truth, and only reopen promotion after a human explicitly chooses that route or a more substantive backlog-clearing move lands
- Jobs: none

### `TASK-MECH-EN-RERUN` — Run the focused English round-3 narrative/reference rerun
- Status: `active`
- Lane: `mechanism_eval`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/execution-tracker.md`
- Next: finish the running judged follow-up rerun, then convert its result into one bounded repair plan that preserves the `walden` one-axis threading win while testing whether `up_from_slavery` gains earlier chapter presence and chapter-label trust
- Jobs:
  - `bgjob_en_chapter_core_rerun_round3_caseiso_judged_followup_20260330`

### `TASK-DATASET-QUESTION-ALIGNED-CASE-CONSTRUCTION` — Build question-aligned case construction for evaluation datasets
- Status: `active`
- Lane: `dataset_platform`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/execution-tracker.md`
- Next: keep the cue-guard and fragment-aware anchor fixes, preserve the removal of weak `chenlun` scene-setting / no-cue reconsolidation cases, and make the next bounded Chinese patch about longer lookback context for `chenlun_public_zh__4__callback_bridge__seed_v1`
- Jobs:
  - `bgjob_closed_loop_zh_cueguard_20260330` (`completed`)

### `TASK-DATASET-FULL-AUTOMATION` — Make dataset building fully automated as one closed build-review-refine loop
- Status: `active`
- Lane: `dataset_platform`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/execution-tracker.md`
- Next: rerun a scratch English closed-loop sample under the new audit semantic-retry guard, compare it against the prior post-fix broader English run, and do not widen to the multi-iteration unattended scheduler until source-equal packets stop showing heavy audit-input drift or the new guard turns that instability into an explicit audit failure
- Jobs:
  - `bgjob_closed_loop_en_broader_auditsemanticretry_20260330`
  - `bgjob_closed_loop_en_broader_auditcoherencefix_repeat_20260330` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_auditcoherencefix_20260330` (`completed`)

## Queued

### `TASK-RUNTIME-VIABILITY-GATES` — Run durable-trace, re-entry, and runtime-viability evaluation
- Status: `queued`
- Lane: `mechanism_eval`
- Priority: `medium`
- Detail: `docs/implementation/new-reading-mechanism/execution-tracker.md`
- Blocked by: `TASK-BENCH-BACKLOG-RESCUE`, `TASK-MECH-EN-RERUN`
- Next: launch the remaining runtime-viability gates only after the failed rerun is dispositioned and the post-recovery benchmark gate decision is explicit

### `TASK-DOC-Q10` — Decide when to promote `attentional_v2` working design into stable docs
- Status: `queued`
- Lane: `documentation`
- Priority: `medium`
- Detail: `docs/implementation/new-reading-mechanism/open-questions.md`
- Blocked by: `TASK-BENCH-BACKLOG-RESCUE`
- Next: resolve `Q10` once benchmark stabilization has settled enough to freeze stable mechanism behavior intentionally

### `TASK-FE-SECTION-RETIREMENT` — Retire section-first chapter/detail and marks surfaces
- Status: `queued`
- Lane: `migration`
- Priority: `medium`
- Detail: `docs/implementation/new-reading-mechanism/execution-tracker.md`
- Blocked by: `TASK-RUNTIME-VIABILITY-GATES`, `TASK-DOC-Q10`
- Next: start only after benchmark direction, runtime viability work, and stable-doc promotion timing are intentionally fixed

## Done

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

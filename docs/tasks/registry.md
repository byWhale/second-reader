# Task Registry

Purpose: provide the canonical workspace task index for agent switching, routing, and traceability.
Use when: choosing what to work on next, recovering a task without chat history, or checking blockers, evidence, and linked truth docs.
Not for: full tracker detail, long-form design rationale, or mutable runtime job state.
Update when: task status, priority, blockers, decision refs, job refs, evidence refs, or next actions change.

This document is the human-readable companion to `docs/tasks/registry.json`.

Last updated: `2026-03-29T10:25:32Z`

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
- Next: use the completed English and Chinese follow-up packet summaries as the new benchmark-hardening truth, then prepare a human-owned post-cleanup gate review without reopening promotion or freezing a reviewed slice automatically
- Jobs: none

### `TASK-MECH-EN-RERUN` — Run the focused English round-3 narrative/reference rerun
- Status: `active`
- Lane: `mechanism_eval`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/execution-tracker.md`
- Next: inspect the completed judged two-case rerun as real mechanism evidence, preserve the `walden` win, and diagnose the `up_from_slavery` chapter mismatch before deciding what to repair next
- Jobs: none

### `TASK-DATASET-SOURCE-GOVERNANCE` — Make source-book intake and intermediate artifacts clear and durable
- Status: `active`
- Lane: `dataset_platform`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/execution-tracker.md`
- Next: use the landed managed intake layer as the new source of truth for future book additions, then connect the current private-library builder inputs to the managed source catalog instead of hard-coded external roots
- Jobs: none

## Queued

### `TASK-DATASET-SMART-BUILDER` — Make dataset case mining question-first, smarter, and more effective
- Status: `queued`
- Lane: `dataset_platform`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/execution-tracker.md`
- Blocked by: `TASK-DATASET-SOURCE-GOVERNANCE`
- Next: teach the smart builder to consume the managed source catalog and existing curated/reviewed case signals, then replace fixed excerpt windows and role-and-position proxy buckets with target-case mining
- Jobs: none

### `TASK-DATASET-FULL-AUTOMATION` — Make dataset building fully automated as one closed build-review-refine loop
- Status: `queued`
- Lane: `dataset_platform`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/execution-tracker.md`
- Blocked by: `TASK-DATASET-SOURCE-GOVERNANCE`, `TASK-DATASET-SMART-BUILDER`
- Next: design one reusable orchestration flow that can run intake, screening, target-case generation, dataset packaging, weak-case review, mechanical adjudication/import, adequacy scoring, and targeted regeneration until thresholds are met, the source pool is exhausted, or an explicit human-owned policy stop is reached
- Jobs: none

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

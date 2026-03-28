# Task Registry

Purpose: provide the canonical workspace task index for agent switching, routing, and traceability.
Use when: choosing what to work on next, recovering a task without chat history, or checking blockers, evidence, and linked truth docs.
Not for: full tracker detail, long-form design rationale, or mutable runtime job state.
Update when: task status, priority, blockers, decision refs, job refs, evidence refs, or next actions change.

This document is the human-readable companion to `docs/tasks/registry.json`.

Last updated: `2026-03-28T05:59:20Z`

## Status Values
- `active`
- `blocked`
- `queued`
- `waiting`
- `parked`
- `done`
- `cancelled`

## Active

### `TASK-MECH-EN-RERUN` — Review English chapter-core retry-2 outputs
- Status: `active`
- Lane: `mechanism_eval`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/execution-tracker.md`
- Next: compare retry-2 outputs against round 1 and turn the split result into a bounded implementation queue
- Jobs: `bgjob_en_chapter_core_rerun_retry2_20260328`

### `TASK-BENCH-ROUND3-CLEANUP` — Finish private-library cleanup and write the round-2 promotion draft
- Status: `active`
- Lane: `dataset_growth`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/execution-tracker.md`
- Next: wait for the cleanup orchestrator to finish, then review the draft and choose promotion vs backlog rescue
- Jobs: `bgjob_private_library_cleanup_round3_orchestrator_20260328`

## Blocked

### `TASK-BENCH-PROMOTION-ROUND2` — Decide the next benchmark-promotion move from the modern supplement
- Status: `blocked`
- Lane: `dataset_growth`
- Priority: `medium`
- Detail: `docs/implementation/new-reading-mechanism/private-library-promotion-round1-execution.md`
- Blocked by: `TASK-BENCH-ROUND3-CLEANUP`
- Next: use the round-2 draft to choose curated promotion packet vs backlog/chapter-lane rescue

## Queued

### `TASK-RUNTIME-VIABILITY-GATES` — Run durable-trace, re-entry, and runtime-viability evaluation
- Status: `queued`
- Lane: `mechanism_eval`
- Priority: `medium`
- Detail: `docs/implementation/new-reading-mechanism/execution-tracker.md`
- Blocked by: `TASK-MECH-EN-RERUN`
- Next: launch the remaining runtime viability gates after the current chapter-core follow-up is dispositioned

### `TASK-DOC-Q10` — Decide when to promote `attentional_v2` working design into stable docs
- Status: `queued`
- Lane: `documentation`
- Priority: `medium`
- Detail: `docs/implementation/new-reading-mechanism/open-questions.md`
- Blocked by: `TASK-MECH-EN-RERUN`, `TASK-BENCH-PROMOTION-ROUND2`
- Next: resolve `Q10` once benchmark stabilization has settled enough to freeze stable mechanism behavior

### `TASK-FE-SECTION-RETIREMENT` — Retire section-first chapter/detail and marks surfaces
- Status: `queued`
- Lane: `migration`
- Priority: `medium`
- Detail: `docs/implementation/new-reading-mechanism/execution-tracker.md`
- Blocked by: `TASK-RUNTIME-VIABILITY-GATES`, `TASK-DOC-Q10`
- Next: start only after benchmark direction and stable public-surface timing are intentionally fixed

## Done

### `TASK-AGENT-SWITCHING-SYSTEM` — Land the repo-first agent-switching memory system
- Status: `done`
- Lane: `docs_tooling`
- Priority: `high`
- Detail: `docs/source-of-truth-map.md`
- Next: keep `docs/current-state.md` and `docs/tasks/registry.*` updated as live work changes

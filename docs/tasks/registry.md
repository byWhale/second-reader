# Task Registry

Purpose: provide the canonical workspace task index for agent switching, routing, and traceability.
Use when: choosing what to work on next, recovering a task without chat history, or checking blockers, evidence, and linked truth docs.
Not for: full tracker detail, long-form design rationale, or mutable runtime job state.
Update when: task status, priority, blockers, decision refs, job refs, evidence refs, or next actions change.

This document is the human-readable companion to `docs/tasks/registry.json`.

Last updated: `2026-03-28T12:49:23Z`

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
- Next: use the archived full English cleanup packet and the live English `7 reviewed_active / 3 needs_revision / 6 needs_replacement` counts to decide whether formal curated promotion can reopen now or should stay paused
- Jobs: none

## Queued

### `TASK-RUNTIME-VIABILITY-GATES` — Run durable-trace, re-entry, and runtime-viability evaluation
- Status: `queued`
- Lane: `mechanism_eval`
- Priority: `medium`
- Detail: `docs/implementation/new-reading-mechanism/execution-tracker.md`
- Blocked by: `TASK-BENCH-BACKLOG-RESCUE`
- Next: launch the remaining runtime viability gates after the post-rescue benchmark gate decision is explicit

### `TASK-DOC-Q10` — Decide when to promote `attentional_v2` working design into stable docs
- Status: `queued`
- Lane: `documentation`
- Priority: `medium`
- Detail: `docs/implementation/new-reading-mechanism/open-questions.md`
- Blocked by: `TASK-BENCH-BACKLOG-RESCUE`
- Next: resolve `Q10` once benchmark stabilization has settled enough to freeze stable mechanism behavior

### `TASK-FE-SECTION-RETIREMENT` — Retire section-first chapter/detail and marks surfaces
- Status: `queued`
- Lane: `migration`
- Priority: `medium`
- Detail: `docs/implementation/new-reading-mechanism/execution-tracker.md`
- Blocked by: `TASK-RUNTIME-VIABILITY-GATES`, `TASK-DOC-Q10`
- Next: start only after benchmark direction and stable public-surface timing are intentionally fixed

## Done

### `TASK-MECH-EN-RERUN` — Review English chapter-core retry-2 outputs
- Status: `done`
- Lane: `mechanism_eval`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/execution-tracker.md`
- Next: retry the focused round-3 `up_from_slavery_public_en__10` / `walden_205_en__10` comparison when provider quota headroom returns; the bounded Phase-4 repair is already landed in code and unit-tested
- Jobs: none

### `TASK-BENCH-ROUND3-CLEANUP` — Finish private-library cleanup and write the round-2 promotion draft
- Status: `done`
- Lane: `dataset_growth`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/execution-tracker.md`
- Next: use the landed round-2 draft as the source of truth for the next dataset-growth move
- Jobs: none

### `TASK-BENCH-PROMOTION-ROUND2` — Decide the next benchmark-promotion move from the modern supplement
- Status: `done`
- Lane: `dataset_growth`
- Priority: `medium`
- Detail: `docs/implementation/new-reading-mechanism/private-library-promotion-round2.md`
- Next: apply the recorded `hold_for_backlog_rescue` decision instead of materializing a curated promotion packet immediately
- Jobs: none

### `TASK-AGENT-SWITCHING-SYSTEM` — Land the repo-first agent-switching memory system
- Status: `done`
- Lane: `docs_tooling`
- Priority: `high`
- Detail: `docs/source-of-truth-map.md`
- Next: keep `docs/current-state.md` and `docs/tasks/registry.*` updated as live work changes

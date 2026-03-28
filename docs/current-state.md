# Current State

Purpose: capture the canonical repo-local view of current project status for agent switching and human recovery.
Use when: onboarding a new coding agent, resuming work without chat history, or checking which initiative is current now.
Not for: long-form rationale, full historical detail, or session-only scratch notes.
Update when: the current objective, active tasks, blockers, active jobs, open decisions, risks, or recommended reading path change.

This file is authoritative for durable current status. Do not keep unique active-state information only in `docs/agent-handoff.md`.

Last verified: `2026-03-28T12:49:23Z`

## Current Objective
- Keep Phase 9 of the new reading mechanism project recoverable and decision-ready:
  - carry forward the landed bounded English local-reading repair for the remaining narrative/reference-heavy chapter cases
  - resolve the post-cleanup private-library promotion gate without reopening the whole English backlog blindly
  - preserve later migration and doc-promotion work without letting it disappear into chat memory

## Now
- Treat `attentional_v2` as experimental and `iterator_v1` as the current default mechanism.
- The English chapter-core retry-2 closeout is now dispositioned into a bounded queue:
  - run:
    - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_vs_iterator_v1_chapter_core_en_round2_microselectivity_retry2_20260328/`
  - round-1 vs retry-2 shift:
    - English `local_impact` improved from `0/4` win-or-tie to `2/4` win-or-tie
    - English `system_regression` improved from `2/4` wins to `3/4` wins
  - verified interpretation:
    - the landed micro-selectivity repair helped most on argumentative / expository English chapters
    - the remaining local gap is now concentrated on narrative / reference-heavy English cases rather than on the whole pack
  - live queue record:
    - `docs/implementation/new-reading-mechanism/mechanism-pattern-ledger.md`
    - `docs/implementation/new-reading-mechanism/execution-tracker.md`
- The bounded narrative/reference-heavy Phase 4 repair is now landed in code for:
  - `up_from_slavery_public_en__10`
  - `walden_205_en__10`
  - landed mechanism change:
    - deterministic local cue packets now include `actor_intention`, `social_pressure`, and `causal_stakes`
    - short spans may synthesize one bounded local candidate from those cues when the local gate is genuinely open
    - zoom/closure/emission prompts now prefer one grounded why-now observation or question over retrospective summary in those moments
  - local verification:
    - `reading-companion-backend/tests/test_attentional_v2_nodes.py`
    - `13` node tests passed on `2026-03-28`
  - current blocker on the focused rerun:
    - March 28 smoke attempts for the two-case round-3 comparison hit provider `429` quota pressure before producing a trustworthy completed comparison
- The private-library cleanup orchestrator, first narrow English rescue, and the next full English cleanup packet are all landed and archived:
  - decision artifact:
    - `docs/implementation/new-reading-mechanism/private-library-promotion-round2.md`
    - `docs/implementation/new-reading-mechanism/private-library-promotion-round2.json`
  - rescue packet:
    - `reading-companion-backend/eval/review_packets/archive/attentional_v2_private_library_backlog_rescue_en_round1/`
  - cleanup packet:
    - `reading-companion-backend/eval/review_packets/archive/attentional_v2_private_library_cleanup_en_round_next/`
  - current dataset-growth result after the cleanup:
    - the recorded round-2 decision remains `hold_for_backlog_rescue`
    - English private-library excerpt lane now sits at:
      - `7` `reviewed_active`
      - `3` `needs_revision`
      - `6` `needs_replacement`
      - `154` `unset`
    - Chinese private-library excerpt lane remains preserved at `11` `reviewed_active` against threshold `9`
    - the active packet queue is empty again after the cleanup import/archive
- There are no active long-running background jobs in the registry right now.
- Use the task registry plus the execution tracker as the route back into detailed mechanism work.

## Next
- Retry the focused `up_from_slavery_public_en__10` / `walden_205_en__10` chapter comparison once provider quota headroom is available.
- Make the post-cleanup benchmark gate decision:
  - decide whether crossing the English threshold and clearing the full open revision/replacement backlog mechanically is enough to reopen formal curated promotion
  - or keep promotion paused until the remaining English `3 / 6` open cases are intentionally dispositioned
- Keep the Chinese gains unchanged while that decision is made.
- After the post-rescue benchmark gate is fixed, run durable-trace, re-entry, and runtime-viability evaluation.

## Blocked
- Formal curated promotion from the modern private-library supplement remains paused until the post-rescue English gate decision is explicit.
- The focused round-3 English mechanism comparison remains waiting on provider quota headroom after March 28 smoke attempts failed with `429` rate limits.
- The later frontend/API retirement of section-first chapter/detail and marks surfaces remains blocked on benchmark stabilization plus stable doc promotion timing.
- `Q10` remains open: when the detailed `attentional_v2` working design should be promoted from temp docs into stable mechanism docs.

## Open Decisions
- `OD-PRIVATE-LIBRARY-POST-RESCUE-GATE`
  - With the English lane now at `7` `reviewed_active` and the mechanical cleanup packet imported, should formal curated promotion reopen immediately, or should the remaining English `3` `needs_revision` and `6` `needs_replacement` cases keep promotion paused?
- `OD-BENCHMARK-SIZE`
  - Is the current benchmark family already large enough for high-confidence cross-mechanism judgment, or should the benchmark expand before any default-cutover decision?
- `Q10`
  - When should the detailed `attentional_v2` working design be promoted from temporary implementation docs into stable mechanism docs?

## Active Risks
- Current public chapter/detail surfaces still carry section-shaped compatibility assumptions that may not fit the new mechanism directly.
- Route mismatches between frontend routes and backend-returned targets can still regress the canonical product path.
- Reaction taxonomy drift can reappear between runtime artifacts, API normalization, and frontend filters.
- Resume behavior remains sensitive to artifact placement under `reading-companion-backend/output/` and `reading-companion-backend/state/`.
- Benchmark confidence can look stronger than it really is if corpus growth, promotion, and reviewed-slice confidence gates drift apart.

## Active Task IDs
- `TASK-BENCH-BACKLOG-RESCUE`

## Active Job IDs
- none

## Recommended Reading Path
1. `AGENTS.md`
2. `README.md`
3. `docs/current-state.md`
4. relevant child `AGENTS.md`
5. `docs/tasks/registry.md`
6. `docs/implementation/new-reading-mechanism/execution-tracker.md`
7. `docs/implementation/new-reading-mechanism/private-library-promotion-round2.md`
8. `docs/implementation/new-reading-mechanism/mechanism-pattern-ledger.md`
9. `reading-companion-backend/state/job_registry/active_jobs.md`
10. `docs/source-of-truth-map.md` when you need to decide where durable information belongs

## Machine-Readable Appendix
```json
{
  "updated_at": "2026-03-28T12:49:23Z",
  "last_updated_by": "codex",
  "active_task_ids": [
    "TASK-BENCH-BACKLOG-RESCUE"
  ],
  "blocked_task_ids": [],
  "active_job_ids": [],
  "open_decision_ids": [
    "OD-PRIVATE-LIBRARY-POST-RESCUE-GATE",
    "OD-BENCHMARK-SIZE",
    "Q10"
  ],
  "detail_refs": [
    "docs/implementation/new-reading-mechanism/execution-tracker.md",
    "docs/implementation/new-reading-mechanism/mechanism-pattern-ledger.md",
    "docs/implementation/new-reading-mechanism/open-questions.md",
    "docs/implementation/new-reading-mechanism/private-library-promotion-round1-execution.md",
    "docs/implementation/new-reading-mechanism/private-library-promotion-round2.md"
  ],
  "truth_refs": [
    "docs/source-of-truth-map.md",
    "docs/product-overview.md",
    "docs/backend-reading-mechanism.md",
    "docs/backend-reader-evaluation.md",
    "docs/runtime-modes.md",
    "docs/tasks/registry.json"
  ]
}
```

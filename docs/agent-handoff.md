# Agent Handoff

Purpose: capture current focus, active risks, and temporary migration notes that are useful right now.
Use when: the task depends on current delivery priorities, active risks, or short-lived migration context.
Not for: stable product behavior, public API authority, runtime facts, or standard reading order.
Update when: current focus, active risks, temporary warnings, or migration status changes.

This file is a temporary working note. It is not a source-of-truth document.

Last updated: `2026-03-15`

## Current Focus
- better segment-level reading reactions
- better prompt quality and context packing
- stronger chapter-level coherence
- search supplementation that adds genuine curiosity instead of noise
- reliability features such as checkpoint, resume, and budget control

## Active Risks
- route mismatches between frontend routes and backend-returned targets
- reaction taxonomy drift between runtime artifacts, API normalization, and frontend filters
- upload flow and live progress integration regressions
- resume edge cases around runtime artifacts under `reading-companion-backend/output/` and `reading-companion-backend/state/`

## Migration Status
- Landing remains frontend-owned. Do not reintroduce backend-owned landing or sample endpoints unless the stable docs change first.
- Landing live preview can pin real reactions by public ID. Configure `reading-companion-frontend/src/app/content/landing-content.ts` with `LANDING_PREVIEW_CONFIG.api.bookId`, `chapterId`, and optional `selectedReactionIds`.
- Backend still accepts legacy `connect_back` artifacts on read, but new runtime outputs should write `retrospect`.
- Public IDs are integer contract IDs. Some internal runtime artifacts still use string identifiers and must continue to be normalized at the API layer.

## Temporary Warnings
- If a note here becomes repeated guidance across tasks, promote it into `AGENTS.md` or the relevant stable doc.
- Do not use this file as the first stop for setup, runtime, contract, or product-flow questions; route those back to the control layer and stable docs.

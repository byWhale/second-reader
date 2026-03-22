# Agent Handoff

Purpose: capture current focus, active risks, and temporary migration notes that are useful right now.
Use when: the task depends on current delivery priorities, active risks, or short-lived migration context.
Not for: stable product behavior, public API authority, runtime facts, or standard reading order.
Update when: current focus, active risks, temporary warnings, or migration status changes.

This file is a temporary working note. It is not a source-of-truth document.

Last updated: `2026-03-23`

## Current Focus
- implementation prep for the new reading mechanism design
- use `docs/implementation/new-reading-mechanism/` as the temporary working set for design capture, planning, progress tracking, and open questions
- better segment-level reading reactions
- better prompt quality and context packing
- stronger chapter-level coherence
- search supplementation that adds genuine curiosity instead of noise
- reliability features such as checkpoint, resume, and budget control
- finish the shared substrate/runtime extraction while preserving `iterator_reader` as the current default reader

## Active Risks
- unclear mapping between the new Notion design and the existing `attentional_v2` design-only mechanism key
- sentence-level substrate gaps could force parser or shared-substrate work earlier than expected
- current public analysis and chapter surfaces still carry section-shaped compatibility assumptions that may not fit the new mechanism directly
- the new mechanism design includes state, observability, evaluation, and resume requirements; if those are deferred, the implementation can look finished while still violating the design
- route mismatches between frontend routes and backend-returned targets
- reaction taxonomy drift between runtime artifacts, API normalization, and frontend filters
- upload flow and live progress integration regressions
- resume edge cases around runtime artifacts under `reading-companion-backend/output/` and `reading-companion-backend/state/`
- accidental leakage of `iterator_reader`-specific concepts back into backend-wide `reading_core` / `reading_runtime` boundaries
- over-relying on `structure.json` in places that should treat `book_document.json` as the canonical parsed-book substrate
- leaving mechanism-private artifacts in shared top-level directories and confusing future multi-mechanism work

## Migration Status
- Temporary implementation docs for the new mechanism now live under `docs/implementation/new-reading-mechanism/`.
- The working design source is the Notion page `new reading mechanism design`; the repo-local design capture is temporary until stable mechanism docs are intentionally updated.
- Landing remains frontend-owned. Do not reintroduce backend-owned landing or sample endpoints unless the stable docs change first.
- Landing live preview can pin real reactions by public ID. Configure `reading-companion-frontend/src/app/content/landing-content.ts` with `LANDING_PREVIEW_CONFIG.api.bookId`, `chapterId`, and optional `selectedReactionIds`.
- Backend still accepts legacy `connect_back` artifacts on read, but new runtime outputs should write `retrospect`.
- Public IDs are integer contract IDs. Some internal runtime artifacts still use string identifiers and must continue to be normalized at the API layer.
- `reading_core` now owns the canonical parsed-book substrate (`public/book_document.json`), runtime contracts, and normalized eval/output types.
- `iterator_reader` now derives `_mechanisms/iterator_v1/derived/structure.json` from that substrate instead of acting as the shared parsed-book truth.
- Top-level `public/` and `_runtime/` are now reserved for cross-mechanism artifacts only.
- Iterator-private derived structures, runtime memory/checkpoints, diagnostics, and `book_analysis` artifacts now belong under `_mechanisms/iterator_v1/`.
- Stable mechanism docs are now split between the shared platform doc (`docs/backend-reading-mechanism.md`) and per-mechanism docs under `docs/backend-reading-mechanisms/`.
- Storage helpers still read older shared-path and flat legacy artifacts for compatibility, but new writes should target the namespaced mechanism paths.
- Normal reading runs do not persist normalized eval bundles; those exports are reserved for explicit eval-mode runs.
- Backend mechanism work is still shifting toward a shared runtime shell plus multiple mechanism-specific implementations. During this migration, `iterator_reader` remains the only default/live reader path unless stable docs say otherwise.

## Temporary Warnings
- If a note here becomes repeated guidance across tasks, promote it into `AGENTS.md` or the relevant stable doc.
- Do not use this file as the first stop for setup, runtime, contract, or product-flow questions; route those back to the control layer and stable docs.
- If a task still treats `docs/backend-reading-mechanism.md` as the sole authority for `iterator_v1` internals, update the task's doc routing assumptions before changing reader internals.

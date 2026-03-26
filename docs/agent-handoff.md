# Agent Handoff

Purpose: capture current focus, active risks, and temporary migration notes that are useful right now.
Use when: the task depends on current delivery priorities, active risks, or short-lived migration context.
Not for: stable product behavior, public API authority, runtime facts, or standard reading order.
Update when: current focus, active risks, temporary warnings, or migration status changes.

This file is a temporary working note. It is not a source-of-truth document.

Last updated: `2026-03-26`

## Current Focus
- Phase 9 preparation for the new reading mechanism project
- use `docs/implementation/new-reading-mechanism/` as the temporary working set for design capture, planning, progress tracking, and open questions
- keep the current active route explicit:
  - continue benchmark hardening through a balanced bilingual excerpt round
  - do not trust broader semantic comparison until the next bilingual hardening and reviewed-slice expansion round lands
  - only then trust broader semantic comparison more strongly
- the temporary side branch for a universal shared LLM invocation/traceability layer is now landed
  - shared provider contracts, key-pool failover, task-level profiles, and standard/debug trace sinks now live in backend infrastructure
  - the return path is direct:
    - reviewed-slice rerun of `mechanism_integrity`
    - only then broader semantic comparison
- decide `Q10`: how much of the detailed working design should be promoted from temp docs into stable `attentional_v2` documentation
- keep `iterator_reader` as the current default reader while `attentional_v2` matures as an experimental end-to-end runner
- finish the later frontend/API migration away from section-first chapter/detail and marks surfaces

## Active Risks
- current public analysis and chapter surfaces still carry section-shaped compatibility assumptions that may not fit the new mechanism directly
- the new mechanism now runs live, so missing benchmark-corpus curation could make later evaluation look stronger than it really is
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
- `attentional_v2` is now a live experimental mechanism under `_mechanisms/attentional_v2/` with real parse/read entrypoints, shared runtime-shell integration, and async job lifecycle support.
- Internal job launchers, resume, and incompatible fresh rerun now preserve `mechanism_key` through shared runtime/job plumbing.
- `attentional_v2` remains intentionally unsupported for legacy `book_analysis` mode in this slice.
- Dataset hardening now has an active balanced bilingual hardening round. The Chinese round-2 revision/replacement packet has already been adjudicated and imported through the shared LLM layer, and the reviewed-slice rerun of `mechanism_integrity` has also completed.
- The tracked Chinese curated `v2` dataset still carries `2` `reviewed_active`, `3` `needs_revision`, and `1` `needs_replacement` cases in the round-2 target slice. The reviewed-slice benchmark is cleaner than before, but it is still too thin and still weak on Chinese callback behavior, so broader semantic comparison should remain blocked until the next balanced bilingual excerpt hardening and expansion round lands.
- The first balanced bilingual hardening round is now prepared as a synchronized packet pair under `reading-companion-backend/eval/review_packets/pending/`:
  - `attentional_v2_bilingual_hardening_round3_en`
  - `attentional_v2_bilingual_hardening_round3_zh`
  - that round has now completed end-to-end and is archived
- After the bilingual hardening import, the tracked curated excerpt datasets now stand at:
  - English: `5` `reviewed_active`, `2` `needs_revision`
  - Chinese: `4` `reviewed_active`, `1` `needs_revision`, `1` `needs_replacement`
- The review queue is empty again. The next route is the planned bilingual `6+6` reviewed-slice expansion packet, because the benchmark still remains below the `8`-per-language minimum trust floor.
- Stable mechanism docs are now split between the shared platform doc (`docs/backend-reading-mechanism.md`) and per-mechanism docs under `docs/backend-reading-mechanisms/`.
- Storage helpers still read older shared-path and flat legacy artifacts for compatibility, but new writes should target the namespaced mechanism paths.
- Normal reading runs do not persist normalized eval bundles; those exports are reserved for explicit eval-mode runs.
- Backend mechanism work is still shifting toward one shared runtime shell plus multiple mechanism-specific implementations. During this migration, `iterator_reader` remains the only default mechanism unless stable docs say otherwise.

## Temporary Warnings
- If a note here becomes repeated guidance across tasks, promote it into `AGENTS.md` or the relevant stable doc.
- Do not use this file as the first stop for setup, runtime, contract, or product-flow questions; route those back to the control layer and stable docs.
- If a task still treats `docs/backend-reading-mechanism.md` as the sole authority for `iterator_v1` internals, update the task's doc routing assumptions before changing reader internals.

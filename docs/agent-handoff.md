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
  - keep broader semantic comparison blocked while the current mechanism-repair gate is unresolved
  - the next real choice is:
    - rerun the full `9 + 9` reviewed slice now after repair pass 2
    - or land one more narrow repair on distinction / anchorless-callback handling first
  - keep the next corpus-growth direction explicit too:
    - the benchmark should no longer grow as literature-heavy by default
    - the next acquisition pass should diversify into modern nonfiction with emphasis on management / economics, business, and biography
    - once the books are downloaded, treat that pass as a large supplement build rather than a tiny patch
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
- Dataset hardening has now completed both:
  - the balanced bilingual `4+4` hardening round
  - the first balanced bilingual `6+6` reviewed-slice expansion round
- After the expansion import, the tracked curated excerpt datasets now stand at:
  - English: `9` `reviewed_active`, `4` `needs_revision`
  - Chinese: `9` `reviewed_active`, `2` `needs_revision`, `1` `needs_replacement`
- The refreshed reviewed datasets are now frozen at:
  - `reading-companion-backend/eval/datasets/excerpt_cases/attentional_v2_excerpt_en_curated_v2_llm_reviewed_round3/`
  - `reading-companion-backend/eval/datasets/excerpt_cases/attentional_v2_excerpt_zh_curated_v2_llm_reviewed_round3/`
- The latest reviewed-slice rerun is:
  - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_integrity_reviewed_slice_round3_20260326/`
- Important current interpretation:
  - the reviewed slice is no longer too small to be meaningful
  - dataset cleanup and expansion helped, but they did not erase the problem
  - English is mixed but usable
  - Chinese still shows robust weakness, especially around callback / tension / reconsolidation handling
  - broader semantic comparison should remain blocked for now
- The review queue is empty again. The current route is now active mechanism repair rather than more packet expansion.
- The first mechanism-repair pass has already landed:
  - deterministic bridge candidates now reach live Phase 4
  - zoom-level bridge hints are no longer dropped before controller choice
  - callback-aware broader prior retrieval now exists for explicit backward-looking cues
  - Phase 4 prompts now ask for exact callback cues and distinctions rather than generic scene paraphrase
- First repair-pass evidence:
  - targeted run:
    - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_integrity_repair_pass1_targeted_20260326/`
  - result:
    - `3 fail`
    - `1 partial`
    - one callback case improved from `fail` to `partial`
    - the targeted weak set still remains below trust overall
- The next route is:
  - keep broader semantic comparison blocked
  - continue mechanism repair on:
    - exact callback-cue reading
    - distinction / recognition-gap closure
    - durable-pattern framing for reconsolidation cases
- The second mechanism-repair pass has now landed:
  - Phase 4 zoom/closure receive deterministic local textual cue packets for:
    - `callback_cue`
    - `distinction_cue`
    - `recognition_gap`
    - `durable_pattern`
  - the live runner now passes trigger output, gate state, trigger signals, and callback-anchor ids into the local boundary context
- Second repair-pass evidence:
  - targeted run:
    - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_integrity_repair_pass2_targeted_20260326/`
  - result:
    - `2 pass`
    - `1 partial`
    - `1 fail`
    - major improvement on:
      - one callback case (`jinghua_yuan_25377_zh__34__callback_bridge__v2`)
      - the targeted reconsolidation case (`chenlun_public_zh__4__reconsolidation_later_reinterpretation__v2`)
    - remaining narrow weakness:
      - one distinction / recognition-gap case is still shallow
      - one callback case still misbridges because the actual supporting prior-acquaintance anchor is not honestly resolved
- The next real decision point is now:
  - rerun the full `9 + 9` reviewed slice immediately
  - or land one more narrow repair first
- Stable mechanism docs are now split between the shared platform doc (`docs/backend-reading-mechanism.md`) and per-mechanism docs under `docs/backend-reading-mechanisms/`.
- The next modern source-book expansion is now recorded explicitly in:
  - it now includes both:
    - why these books were selected
    - what we will do with them after download
  - `docs/implementation/new-reading-mechanism/modern-nonfiction-expansion-booklist.md`
  - use that file for:
    - why the current corpus mix is still too literature-heavy
    - the first `16`-book executable shortlist
    - category coverage and priority
    - post-download supplement-build workflow and larger size targets
- Storage helpers still read older shared-path and flat legacy artifacts for compatibility, but new writes should target the namespaced mechanism paths.
- Normal reading runs do not persist normalized eval bundles; those exports are reserved for explicit eval-mode runs.
- Backend mechanism work is still shifting toward one shared runtime shell plus multiple mechanism-specific implementations. During this migration, `iterator_reader` remains the only default mechanism unless stable docs say otherwise.

## Temporary Warnings
- If a note here becomes repeated guidance across tasks, promote it into `AGENTS.md` or the relevant stable doc.
- Do not use this file as the first stop for setup, runtime, contract, or product-flow questions; route those back to the control layer and stable docs.
- If a task still treats `docs/backend-reading-mechanism.md` as the sole authority for `iterator_v1` internals, update the task's doc routing assumptions before changing reader internals.

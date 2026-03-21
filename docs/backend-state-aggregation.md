# Backend State Aggregation

Purpose: explain how backend artifacts are aggregated and normalized into the public state surfaces used by the app.
Use when: changing artifact layout, bookshelf/detail shaping, analysis-state sourcing, marks behavior, or internal-to-public normalization.
Not for: endpoint schema authority, function-level catalog implementation, or the older `book_analysis` capability.
Update when: source artifacts, aggregation responsibilities, or normalization boundaries change.

Use `docs/api-contract.md` for exact fields and routes. Use this file to understand which persisted artifacts feed each public surface and where those artifacts are normalized.

## Terminology Guard
- In this document, `analysis-state` and related `analysis/*` surfaces refer to the current sequential deep-reading workflow.
- They do not refer to the older `book_analysis` capability, even though legacy files and helper names still exist in the repository.

## Source Artifacts
- `public/book_document.json`
  - Canonical parsed-book substrate shared across backend reading mechanisms.
  - Contains chapter order, paragraph records, and locators.
  - Current public API surfaces do not expose it directly, but runtime and future eval tooling can rely on it as the mechanism-neutral text source.
- `_mechanisms/iterator_v1/derived/structure.json`
  - Current `iterator_v1`-owned derived traversal artifact.
  - Carries chapter section trees, `segment_ref`, and iterator-specific traversal metadata.
  - Public aggregation still uses it where section-level backfill or iterator-era chapter structure is required.
- `public/book_manifest.json`
  - Book identity, language metadata, chapter tree, source asset pointers, and chapter result file hints.
  - Legacy flat manifests are still readable through fallback resolution, but public aggregation prefers the canonical `public/` location.
- `_runtime/run_state.json`
  - The live runtime snapshot for the sequential workflow.
  - Carries top-level stage, chapter and segment pointers, `current_phase_step`, `current_reading_activity`, checkpoint metadata, errors, and ETA-like progress hints.
- `_runtime/parse_state.json`
  - Parse-stage checkpoint metadata used before the main run state fully reflects deep-reading progress.
  - Important for deferred upload and for the `parsing_structure` view of resumability.
- `_runtime/activity.jsonl`
  - The historical activity stream used for both the visible mindstream and the internal system-diagnostics trail.
- `_mechanisms/iterator_v1/runtime/reader_memory.json`
  - Iterator-private live reader memory for resume and continuity.
  - Shared aggregation should only read it through storage helpers when compatibility or recovery behavior requires it.
- `_mechanisms/iterator_v1/runtime/checkpoints/*`
  - Iterator-private section progress checkpoints.
  - Shared aggregation should not treat these as universal runtime state.
- `_mechanisms/iterator_v1/runtime/plan_state.json`
  - Iterator-private planner progress state.
- `_mechanisms/iterator_v1/internal/analysis/*`
  - Iterator-private secondary analysis artifacts such as `book_analysis` outputs.
  - These are not part of the primary sequential public state surface.
- `public/chapters/*_deep_read.json`
  - Completed chapter artifacts.
  - Each file contributes rendered chapter content, featured reactions, and `ui_summary` reaction counts.
- `state/user_marks.json`
  - Single-user mark persistence keyed by internal reaction id.
  - Stores user-selected mark values and enough book/chapter metadata to render marks pages quickly.

## Surface Mapping
- `GET /api/books`
  - Built from `book_manifest` plus `run_state`.
  - Uses `state/jobs/*.json` as a guard so the shelf can still show `analyzing` while live runtime files are catching up.
  - Adds per-book mark counts from `state/user_marks.json`.
- `GET /api/books/{book_id}`
  - Uses `book_manifest` for metadata and chapter tree.
  - Uses `run_state` to decide the book's current overall status and in-progress chapter.
  - Uses completed chapter result files to build aggregate reaction counts and result readiness.
  - Uses `user_marks` for `my_mark_count`.
- `GET /api/books/{book_id}/analysis-state`
  - Uses `book_manifest`, `run_state`, `parse_state`, `activity.jsonl`, and chapter result files together.
  - Builds progress metrics, chapter tree statuses, the live `current_reading_activity` snapshot, `resume_available`, `last_checkpoint_at`, recent completed chapters, recent reactions, and the `current_state_panel`.
  - When older runtime snapshots contain a shortened `current_reading_activity.current_excerpt`, catalog backfills the full normalized section text from the current default mechanism's `_mechanisms/iterator_v1/derived/structure.json` by matching `segment_ref`.
- `GET /api/books/{book_id}/activity`
  - Reads `activity.jsonl` and normalizes each event into the public event shape.
  - The routed frontend overview now consumes the `stream=mindstream` view; `stream=system` remains available for diagnostics.
  - Adds canonical chapter result routes where the completed result is ready.
- `GET /api/books/{book_id}/analysis-log`
  - Is the main exception to the catalog-driven view model.
  - It remains an internal diagnostic endpoint and is no longer part of the user-facing overview.
  - It comes from the latest job record plus `state/jobs/<job_id>.log` via `jobs.py`, not from `catalog.py`.
- `GET /api/books/{book_id}/chapters/{chapter_id}`
  - Uses the chapter result file for structured sections, featured reactions, and chapter-level summaries.
  - Uses `user_marks` to attach the current mark state to each returned reaction card.
- `GET /api/books/{book_id}/chapters/{chapter_id}/outline`
  - Starts from the manifest chapter tree, then enriches the outline with section previews from the chapter result file when that result exists.
- `GET /api/marks` and `GET /api/books/{book_id}/marks`
  - Read from `state/user_marks.json`.
  - Rely on previously persisted book/chapter metadata and reaction lookup against chapter results to keep marks anchored to real reading artifacts.

## Aggregation Responsibilities
- `reading-companion-backend/src/library/catalog.py`
  - Owns artifact discovery, legacy-path fallback, view aggregation, and most product-facing payload shaping.
  - Converts raw manifests, runtime files, activity streams, and chapter artifacts into bookshelf, book detail, chapter detail, chapter outline, and analysis-state views.
  - May consume `_mechanisms/iterator_v1/derived/structure.json` for iterator-era section backfill, but should not treat that artifact as the universal parsed-book substrate.
- `reading-companion-backend/src/api/app.py`
  - Owns endpoint-level response shaping and public-ID resolution.
  - Resolves public integer ids back to internal runtime ids, calls catalog/jobs/marks helpers, and normalizes returned marks into the public API field names.
- `reading-companion-backend/src/library/user_marks.py`
  - Owns mark persistence in `state/user_marks.json`.
  - Resolves a reaction back to chapter result artifacts before saving a mark, so marks remain tied to actual reaction payloads instead of a detached UI-only store.
- `reading-companion-backend/src/api/realtime.py`
  - Reuses `refresh_job()` and `get_analysis_state()` to build WebSocket snapshots.
  - It does not define a separate source of truth for live state; it republishes the same aggregated state surfaces used by REST.

## Normalization Boundary
- Internal ids vs public ids
  - Runtime artifacts use internal string ids for books and reactions.
  - Public REST and WebSocket surfaces expose integer `book_id`, `reaction_id`, and `mark_id`.
  - `src/api/contract.py` performs the stable namespace-based mapping between the two.
- Legacy taxonomy vs canonical taxonomy
  - Internal artifacts may still contain legacy values such as `connect_back`, `critique`, `curiosity`, or `known`.
  - Public surfaces normalize them to the canonical taxonomy:
    - `connect_back -> retrospect`
    - `critique -> discern`
    - `curiosity -> curious`
    - `known -> resonance`
- Canonical frontend routes
  - Product-facing URLs returned by the backend should come from contract helpers such as `canonical_book_path()` and `canonical_chapter_path()`.
  - Catalog and realtime payloads should emit canonical frontend routes even when older compatibility routes still exist elsewhere.
- Legacy file layout support
  - Storage helpers still resolve legacy flat files when older output directories have not been migrated.
  - That fallback is an artifact-compatibility concern only; it must not leak legacy paths or legacy naming back into the public contract.
- Shared substrate vs mechanism artifacts
  - `book_document.json` is the canonical parsed-book substrate for runtime and future mechanism work.
  - Top-level `public/` contains only cross-mechanism, product-facing artifacts.
  - Top-level `_runtime/` contains only cross-mechanism live shell state.
  - `_mechanisms/<mechanism_key>/` contains mechanism-private derived structures, runtime memory/checkpoints, diagnostics, and optional eval exports.
  - `_mechanisms/iterator_v1/derived/structure.json` remains a current-mechanism artifact that aggregation may still consult for `iterator_v1`-shaped section views and compatibility backfill.

## Practical Reading Order
- Read `docs/backend-sequential-lifecycle.md` first when the question is "how does the job behave over time?"
- Read `docs/backend-reading-mechanism.md` when the question is "what is shared across mechanisms and which doc owns this concept?"
- Read `docs/backend-reading-mechanisms/iterator_v1.md` when the question is "how does the current default mechanism turn one selected section into local reader work and live attention state?"
- Read this file when the question is "which artifacts feed this payload?" or "where does normalization happen?"
- Only drop into `catalog.py`, `jobs.py`, or `user_marks.py` after the system-level source mapping in this document is no longer enough.

# Backend State Aggregation

Purpose: explain how backend artifacts are aggregated and normalized into the public state surfaces used by the app.
Use when: changing artifact layout, bookshelf/detail shaping, analysis-state sourcing, marks behavior, or internal-to-public normalization.
Not for: endpoint schema authority, function-level catalog implementation, or the older `book_analysis` capability.
Update when: source artifacts, aggregation responsibilities, or normalization boundaries change.

Use `docs/api-contract.md` for exact fields and routes. Use this file to understand which persisted artifacts feed each public surface and where those artifacts are normalized.

## Terminology Guard
- In this document, `analysis-state` and related `analysis/*` surfaces refer to the current sequential deep-reading workflow.
- They do not refer to the older `book_analysis` capability, which is now retired and retained only as legacy compatibility debt even though some old files and helper names still exist in the repository.

## Source Artifacts
- `public/book_document.json`
  - Canonical parsed-book substrate shared across backend reading mechanisms.
  - Contains chapter order, paragraph records, sentence records, and locators.
  - Sentence records are parse-time, source-order, mechanism-neutral substrate entries grounded back to paragraph locators with character offsets.
  - Load/build helpers may backfill missing sentence inventories into older paragraph-only `book_document.json` payloads when the canonical document is reloaded.
  - Current public API surfaces do not expose it directly, but runtime and future eval tooling can rely on it as the mechanism-neutral text source.
- `_mechanisms/iterator_v1/derived/structure.json`
  - Current `iterator_v1`-owned derived traversal artifact.
  - Carries chapter section trees, `segment_ref`, and iterator-specific traversal metadata.
  - Public aggregation still uses it where section-level backfill or iterator-era chapter structure is required.
- `_mechanisms/attentional_v2/derived/chapter_result_compatibility/*.json`
  - `attentional_v2`-owned compatibility chapter results derived from anchored reaction truth.
  - These are the source chapter-result artifacts for the current routed frontend when `attentional_v2` is active.
- `public/book_manifest.json`
  - Book identity, language metadata, chapter tree, source asset pointers, and chapter result file hints.
  - Legacy flat manifests are still readable through fallback resolution, but public aggregation prefers the canonical `public/` location.
  - For non-iterator mechanisms such as `attentional_v2`, the shared manifest can now be built from `book_document.json` plus mechanism-owned compatibility chapter results instead of from `iterator_v1` structure.
  - Aggregation now preserves chapter-level compatibility hints such as `result_file`, `visible_reaction_count`, and `reaction_type_diversity` when the shared manifest is rebuilt from the shared substrate.
- `_runtime/run_state.json`
  - The live runtime snapshot for the sequential workflow.
  - Carries top-level stage, chapter and segment pointers, `current_phase_step`, `current_reading_activity`, checkpoint metadata, errors, and ETA-like progress hints.
- `_runtime/runtime_shell.json`
  - Shared thin runtime envelope for cross-mechanism cursor and active-artifact references.
  - May now contribute additive `reading_locus` and active reaction references for non-section mechanisms even when the current compatibility surfaces still expose `segment_ref`.
  - Phase 8 now also carries `observability_mode` so the shared shell can distinguish thin standard-mode runtime state from debug-only diagnostics.
- `_runtime/parse_state.json`
  - Parse-stage checkpoint metadata used before the main run state fully reflects deep-reading progress.
  - Important for deferred upload and for the `parsing_structure` view of resumability.
- `_runtime/activity.jsonl`
  - The historical activity stream used for the visible mindstream and standard system/runtime events.
  - For `attentional_v2`, checkpoint and resume events may now be written here in standard mode because they are part of trustworthy runtime history rather than debug-only forensics.
- `_mechanisms/attentional_v2/internal/diagnostics/events.jsonl`
  - Debug-only diagnostics stream for `attentional_v2`.
  - Controller-facing forensics, candidate traces, and other deep debug events belong here instead of the shared runtime history.
- `_mechanisms/iterator_v1/runtime/reader_memory.json`
  - Iterator-private live reader memory for resume and continuity.
  - Shared aggregation should only read it through storage helpers when compatibility or recovery behavior requires it.
- `_mechanisms/iterator_v1/runtime/checkpoints/*`
  - Iterator-private section progress checkpoints.
  - Shared aggregation should not treat these as universal runtime state.
- `_mechanisms/iterator_v1/runtime/plan_state.json`
  - Iterator-private planner progress state.
- `_mechanisms/iterator_v1/internal/analysis/*`
  - Iterator-private retired legacy analysis artifacts such as `book_analysis` outputs.
  - These are not part of the primary sequential public state surface.
- `public/chapters/*_deep_read.json`
  - Completed chapter artifacts.
  - Each file contributes rendered chapter content, featured reactions, and `ui_summary` reaction counts.
- `state/user_marks.json`
  - Single-user mark persistence keyed by internal reaction id.
  - Stores user-selected mark values and enough book/chapter metadata to render marks pages quickly.

## Surface Mapping
- `GET /api/books`
  - Built from `book_manifest`, `run_state`, and shared runtime-truth projection.
  - Uses the canonical product job records in `state/job_registry/jobs/*.json` plus runtime freshness to decide whether the shelf should still show `analyzing`.
  - If `run_state` still looks active but there is no active canonical job truth and the runtime heartbeat is older than 45 seconds, aggregation now projects the card to `paused` with `status_reason = runtime_stale` instead of trusting the stale stage literally.
  - `state/jobs/*.json` remains a compatibility shadow during the current migration window.
  - Adds per-book mark counts from `state/user_marks.json`.
  - Hides stale opaque upload/test stub manifests that never became real books, so failed hash-like upload leftovers do not pollute the visible shelf.
- `GET /api/books/{book_id}`
  - Uses `book_manifest` for metadata and chapter tree.
  - Uses shared runtime-truth projection instead of trusting `run_state.stage` directly.
  - Adds optional additive `status_reason` so the frontend can distinguish ordinary paused books from stale/interrupted recovery states without changing the top-level status enum.
  - Uses completed chapter result files to build aggregate reaction counts and result readiness.
  - Uses `user_marks` for `my_mark_count`.
- `GET /api/books/{book_id}/analysis-state`
  - Uses `book_manifest`, `run_state`, `runtime_shell`, `parse_state`, canonical product job truth, `activity.jsonl`, and chapter result files together.
  - Builds progress metrics, chapter tree statuses, `status_reason`, `current_reading_activity`, `resume_available`, `last_checkpoint_at`, recent completed chapters, recent reactions, and the `current_state_panel`.
  - `resume_available` is now projected from usable resume truth, not just from whatever older runtime files last claimed. A stale runtime shell or leftover checkpoint artifact is not enough on its own.
  - When the current public state is `paused` because of `runtime_stale` or `runtime_interrupted`, aggregation preserves the last-known chapter/section/activity pointers but treats them as last-known runtime snapshots rather than live reading claims.
  - For non-iterator mechanisms, additive locus projection now prefers:
    - explicit `reading_locus`
    - shared runtime-shell cursor
    - shared `book_document.json`
    before any iterator-era `segment_ref` structure lookup
  - When older iterator-era runtime snapshots contain a shortened `current_reading_activity.current_excerpt`, catalog may backfill the full normalized section text from `_mechanisms/iterator_v1/derived/structure.json` by matching `segment_ref`.
  - Current public payloads may now additively expose `reading_locus`, `move_type`, `reconstructed_hot_state`, `last_resume_kind`, and `active_reaction_id` while keeping `segment_ref` as a compatibility sidecar.
- `GET /api/books/{book_id}/activity`
  - Reads `activity.jsonl` and normalizes each event into the public event shape.
  - The routed frontend overview now consumes the `stream=mindstream` view; `stream=system` remains available for diagnostics.
  - Adds canonical chapter result routes where the completed result is ready.
  - Event payloads may now also carry additive `reading_locus`, `move_type`, and anchor-native reaction fields without changing the current compatibility route model.
- `GET /api/books/{book_id}/analysis-log`
  - Is the main exception to the catalog-driven view model.
  - It remains an internal diagnostic endpoint and is no longer part of the user-facing overview.
  - It comes from the latest canonical product job record plus `state/jobs/<job_id>.log` via `jobs.py`, not from `catalog.py`.
- `GET /api/books/{book_id}/chapters/{chapter_id}`
  - Uses the chapter result file for structured sections, featured reactions, and chapter-level summaries.
  - Uses `user_marks` to attach the current mark state to each returned reaction card.
  - This surface no longer hard-requires `iterator_v1` structure as long as the manifest points at a valid mechanism-owned chapter result file.
  - When older compatibility manifests are missing `result_file`, aggregation now also falls back directly to `attentional_v2` chapter compatibility payloads under `_mechanisms/attentional_v2/derived/chapter_result_compatibility/`.
  - Reaction cards and featured reaction previews may now additively expose `primary_anchor`, `related_anchors`, and reconsolidation lineage sidecars while the page still remains section-shaped for compatibility.
- `GET /api/books/{book_id}/chapters/{chapter_id}/outline`
  - Starts from the manifest chapter tree, then enriches the outline with section previews from the chapter result file when that result exists.
  - It does not hard-require `iterator_v1` structure; non-iterator runs can now serve outline sections from compatibility chapter payloads alone.
- `GET /api/marks` and `GET /api/books/{book_id}/marks`
  - Read from `state/user_marks.json`.
  - Rely on previously persisted book/chapter metadata and reaction lookup against chapter results to keep marks anchored to real reading artifacts.
  - Marks may now persist additive `primary_anchor` data even while they still expose `section_ref` for the current routed frontend.

## Aggregation Responsibilities
- `reading-companion-backend/src/library/catalog.py`
  - Owns artifact discovery, legacy-path fallback, view aggregation, shared runtime-truth projection, and most product-facing payload shaping.
  - Converts raw manifests, runtime files, activity streams, and chapter artifacts into bookshelf, book detail, chapter detail, chapter outline, and analysis-state views.
  - Must not durably rewrite runtime files in GET paths. Stale/orphan reconciliation belongs to startup/runtime recovery, not to read-only aggregation.
  - May consume `_mechanisms/iterator_v1/derived/structure.json` for iterator-era section backfill, but should not treat that artifact as the universal parsed-book substrate.
  - Must keep non-iterator chapter/result flows functional without forcing every mechanism to emit `structure.json`.
  - Now also projects additive anchor- and locus-native fields upward without removing current compatibility fields prematurely.
- `reading-companion-backend/src/api/app.py`
  - Owns endpoint-level response shaping and public-ID resolution.
  - Resolves public integer ids back to internal runtime ids, calls catalog/jobs/marks helpers, and normalizes returned marks into the public API field names.
- `reading-companion-backend/src/library/user_marks.py`
  - Owns mark persistence in `state/user_marks.json`.
  - Resolves a reaction back to chapter result artifacts before saving a mark, so marks remain tied to actual reaction payloads instead of a detached UI-only store.
- `reading-companion-backend/src/api/realtime.py`
  - Reuses `refresh_job()` and `get_analysis_state()` to build WebSocket snapshots.
  - It does not define a separate source of truth for live state; it republishes the same aggregated state surfaces used by REST.
- `reading-companion-backend/src/library/runtime_truth.py`
  - Owns the shared helper that decides whether a runtime snapshot is truly active, stale-orphaned, or only last-known.
  - Keeps bookshelf, detail, analysis-state, and job polling aligned on the same `status_reason` and resumability truth.

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
  - Its sentence layer is shared substrate, not a mechanism-private derivative.
  - Top-level `public/` contains only cross-mechanism, product-facing artifacts.
  - Top-level `_runtime/` contains only cross-mechanism live shell state.
  - `_mechanisms/<mechanism_key>/` contains mechanism-private derived structures, runtime memory/checkpoints, diagnostics, and optional eval exports.
  - `_mechanisms/iterator_v1/derived/structure.json` remains a current-mechanism artifact that aggregation may still consult for `iterator_v1`-shaped section views and compatibility backfill.
- Additive locus/anchor fields vs section compatibility
  - Public aggregation may now expose richer additive fields such as `reading_locus`, `primary_anchor`, `related_anchors`, and `supersedes_reaction_id`.
  - Existing `segment_ref` / `section_ref` fields remain temporary compatibility sidecars for current frontend surfaces.
  - The later planned migration is to redesign chapter/detail and marks around chapter text plus anchored reactions instead of section-first containers.
- Standard observability vs debug diagnostics
  - Shared `_runtime/runtime_shell.json`, `_runtime/activity.jsonl`, and `_runtime/checkpoint_summaries/*.json` are the standard-mode observability layer.
  - Mechanism-private full checkpoints remain standard-private because they are required for honest resume and baseline evaluation, even though they are not public API surfaces.
  - Deep controller, candidate, and prompt diagnostics belong under `_mechanisms/<mechanism_key>/internal/diagnostics/` and should stay debug-only rather than default shared runtime state.

## Practical Reading Order
- Read `docs/backend-sequential-lifecycle.md` first when the question is "how does the job behave over time?"
- Read `docs/backend-reading-mechanism.md` when the question is "what is shared across mechanisms and which doc owns this concept?"
- Read `docs/backend-reading-mechanisms/attentional_v2.md` when the question is "how does the current default mechanism turn sentence-order intake into meaning-unit reading and live attention state?"
- Read `docs/backend-reading-mechanisms/iterator_v1.md` when the question is "how does the supported section-first fallback mechanism turn one selected section into local reader work and live attention state?"
- Read this file when the question is "which artifacts feed this payload?" or "where does normalization happen?"
- Only drop into `catalog.py`, `jobs.py`, or `user_marks.py` after the system-level source mapping in this document is no longer enough.

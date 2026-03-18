# Backend Sequential Lifecycle

Purpose: explain the system-level lifecycle for the current sequential deep-reading workflow.
Use when: changing upload/start/resume behavior, job status semantics, runtime recovery, or live progress surfaces.
Not for: function-level implementation details, public schema authority, or the older `book_analysis` capability.
Update when: upload flow, job kinds, status progression, runtime recovery rules, or frontend lifecycle dependencies change.

Use `docs/api-contract.md` for route and field authority. Use this file to understand how the current long-running workflow behaves across uploads, jobs, checkpoints, and recovery.
Use `docs/backend-reading-mechanism.md` when the question is how a selected section is processed inside the inner reader loop.

## Terminology Guard
- In this document, `analysis` means the current sequential deep-reading workflow exposed through `POST /api/uploads/epub`, `POST /api/books/{book_id}/analysis/start`, `POST /api/books/{book_id}/analysis/resume`, and `GET /api/books/{book_id}/analysis-state`.
- It does not mean the older `book_analysis` capability. That capability still exists in the codebase, but it is not the primary product path and should not drive default workflow decisions.

## Entry Points
- `POST /api/uploads/epub`
  - Stores the EPUB under `state/uploads/<job_id>.epub`.
  - Provisions a minimal book shell immediately so the frontend can resolve a book card and book route before deep reading starts.
  - `start_mode=immediate` launches a `read` job for the main sequential workflow.
  - `start_mode=deferred` launches a `parse` job that stops after structure parsing.
- `POST /api/books/{book_id}/analysis/start`
  - Starts the main sequential workflow for an uploaded book that is currently `not_started`.
  - Reuses the copied source asset under the book output directory rather than requiring a new upload.
- `POST /api/books/{book_id}/analysis/resume`
  - Resumes the latest paused or interrupted sequential job from the newest compatible checkpoint.
  - In demo/prod mode, an incompatible checkpoint triggers a fresh rerun instead of an unsafe resume.
- `GET /api/jobs/{job_id}`
  - Returns the refreshed job record plus analysis-derived progress when available.
- `GET /api/books/{book_id}/analysis-state`
  - Returns the book-scoped progress snapshot used by the overview page.
- `WS /api/ws/jobs/{job_id}`
  - Streams job-scoped stage changes, activity additions, and progress snapshots.
- `WS /api/ws/books/{book_id}/analysis`
  - Streams the same workflow from the book point of view, which is what the overview page subscribes to.

## Main Lifecycle
1. Upload accepts an EPUB and writes a provisional manifest plus an initial run-state shell so the book exists immediately.
2. A background job record is created in `state/jobs/` with `job_kind=parse` or `job_kind=read`.
3. The job enters `queued`, then begins structure preparation under `parsing_structure`.
4. Deferred uploads stop at `ready`, which means chapter structure exists but deep reading has not started.
5. Immediate uploads or `analysis/start` move from preparation into semantic segmentation and then chapter-by-chapter deep reading on the same long-task surface.
6. While the reader is active, runtime artifacts update chapter pointers, segment pointers, activity events, and checkpoint metadata.
7. If the worker stops cleanly, deferred parse work finishes at `ready` and full read work finishes at `completed`. If runtime guards intervene, the run becomes `paused`. If recovery is no longer safe, the run becomes `error` or is restarted from scratch.
8. Terminal runs are mirrored into `_history/runs/<job_id>/` so the latest live artifacts and run history stay separate.

## Job Kinds And Status Progression
### `parse` jobs
- Used by deferred upload.
- Primary path: `queued -> parsing_structure -> ready`.
- Goal: produce chapter structure, a resumable parse checkpoint, and a book overview that can later be started explicitly.

### `read` jobs
- Used by immediate upload, `analysis/start`, and `analysis/resume`.
- Primary path: `queued -> parsing_structure -> deep_reading -> completed`.
- The `parsing_structure` phase still appears here because structure preparation and semantic segmentation happen before the reader settles into steady-state deep reading.

### Status semantics
- `queued`
  - The accepted job record exists, but the runtime has not yet produced a fresh active state.
- `parsing_structure`
  - The workflow is preparing structure or segmentation state. This covers both deferred parse work and the preparation phase of the main sequential reader.
- `ready`
  - Structure exists and the book can be started from the overview page, but deep reading is not currently running.
- `deep_reading`
  - The sequential reader is actively moving through chapters and segments.
- `chapter_note_generation`
  - A compatibility-stage active status used while a read run is still finalizing chapter notes. Treat it as part of the live read lifecycle, not as a separate product mode.
- `paused`
  - The workflow stopped after a resumable checkpoint. The book overview should present continue/retry affordances rather than treating the run as complete.
- `completed`
  - Deep reading finished and the result surfaces should now read completed chapter artifacts.
- `error`
  - The job cannot continue safely in its current form. Some `error` situations still surface `resume_available`, but they should be treated as recovery cases, not normal progress states.

## Runtime Mode Differences
- Startup recovery
  - Backend startup runs unfinished-job recovery by refreshing every active job record in `state/jobs/`.
  - Recovery decides whether the run should keep going, pause, resume, or restart from scratch.
- Development boot mismatch
  - Development mode treats unfinished jobs from an older backend `boot_id` as untrusted.
  - Those runs are abandoned, written into the internal system activity stream as `dev_run_abandoned`, and left for a fresh manual rerun instead of being auto-resumed.
- `resume_compat_version`
  - Demo/prod resume safety is governed by `resume_compat_version` across the job record, `run_state`, and `parse_state`.
  - If those versions do not match the current runtime, the backend archives the old run, clears live artifacts, emits `resume_incompatible` plus `fresh_rerun_started`, and launches a fresh run without `--continue`.
- Stale runtime handling
  - If the process is still alive but live runtime updates stop arriving, the backend pauses the book, writes a human-facing stalled message, and appends `runtime_stalled` plus `job_paused_by_runtime_guard` into the system stream.
  - The default active-runtime stale threshold is 45 seconds.
- Auto-resume budget
  - Demo/prod may auto-resume a stalled or unexpectedly stopped run once.
  - After the auto-resume budget is exhausted, the run stays `paused` for operator review instead of cycling forever.
- Runtime environment guard
  - Background jobs require Python 3.11+.
  - If the backend is launched under an older interpreter, the job is rejected early and the book records `runtime_environment_error`.

## What The Frontend Depends On
- `analysis-state.current_reading_activity`
  - Drives the live "what the reader is doing now" line on the book overview.
  - This is a realtime snapshot, not a historical activity entry.
- `analysis-state.resume_available`
  - Tells the frontend whether a continue action is meaningful after pauses, stops, or recovery events.
- `analysis-state.last_checkpoint_at`
  - Gives one checkpoint timestamp that works for both parse-stage and deep-reading checkpoints.
- `GET /api/books/{book_id}/activity`
  - Remains the historical feed for mindstream and program-log entries.
  - It complements `current_reading_activity`; it does not replace it.
- `GET /api/jobs/{job_id}` and `WS /api/ws/jobs/{job_id}`
  - Provide machine-readable job lifecycle status for upload/start/resume flows.
- `GET /api/books/{book_id}/analysis-state` and `WS /api/ws/books/{book_id}/analysis`
  - Provide the book-scoped snapshot used by the main overview page.
- `ready` and `paused`
  - Are product-significant states. `ready` means structure is available but deep reading has not started yet. `paused` means recovery should continue from the book overview rather than from a fresh upload.

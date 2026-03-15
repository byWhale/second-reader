# API Integration

This file is the operational companion to [API Contract](api-contract.md).

Use `docs/api-contract.md` for canonical fields, routes, enums, and identifier rules.
Use this file for local runtime notes and the currently connected endpoint surface.

## Local Base URLs
- API base: `http://localhost:8000`
- WS base: `ws://localhost:8000`

Frontend defaults can be overridden with:
- `VITE_API_BASE_URL`
- `VITE_WS_BASE_URL`

## Active Frontend-Used Endpoints
- `POST /api/uploads/epub`
- `POST /api/books/{book_id}/analysis/start`
- `POST /api/books/{book_id}/analysis/resume`
- `GET /api/jobs/{job_id}`
- `GET /api/books`
- `GET /api/books/{book_id}`
- `GET /api/books/{book_id}/analysis-state`
- `GET /api/books/{book_id}/analysis-log`
- `GET /api/books/{book_id}/activity`
- `GET /api/books/{book_id}/marks`
- `GET /api/books/{book_id}/chapters/{chapter_id}`
- `GET /api/marks`
- `PUT /api/marks/{reaction_id}`
- `DELETE /api/marks/{reaction_id}`
- `WS /api/ws/jobs/{job_id}`
- `WS /api/ws/books/{book_id}/analysis`

## Integration Notes
- Backend images and source assets are returned as relative API paths and must be prefixed with the configured API base in the frontend.
- Backend `target_url`, `result_url`, and `open_target` values are frontend routes, not backend URLs.
- Backend analysis state, activity feed, and technical log tail are used by the adaptive `/books/:id` overview when a book is in progress; WebSocket messages trigger refreshes, while polling remains the fallback.
- The top live line in `Reading mindstream` is driven by `analysis-state.current_reading_activity`, which is a realtime snapshot of the active reading phase rather than a persisted history item.
- The historical mindstream list still comes from `GET /api/books/{book_id}/activity` and remains separate from the live activity snapshot.
- Runtime guard events such as stalled heartbeats, timeout detection, unsupported runtime launches, and forced pauses are written into the same activity feed with `stream=system` so they appear in `Program log` rather than only in the technical log.
- Additional system-side recovery events now include `resume_incompatible`, `fresh_rerun_started`, and `dev_run_abandoned`.
- Deferred upload stops after the chapter-level structure parse; `analysis/start` and `analysis/resume` then perform semantic segmentation as the preparation phase before deep reading continues on the same long-task surface.
- Public `book_id`, `reaction_id`, and `mark_id` values are integer IDs even when backend runtime artifacts still use internal string identifiers.
- `analysis-state.last_checkpoint_at` now reflects deep-reading segment checkpoints as well as parse checkpoints, so the overview and runtime guards can point to the latest resumable point with one field.

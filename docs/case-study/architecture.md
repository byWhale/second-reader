# Case Study Architecture

Purpose: explain how the system is put together, why the current main path exists, and how the architecture evolved.
Use when: preparing technical walkthroughs, architecture explanations, or interview answers about system design.
Not for: source-of-truth API schemas, exhaustive file listings, or temporary migration notes.
Update when: the main path, system boundaries, runtime/recovery model, or architecture evolution story materially changes.

## System Boundary
- `reading-companion-backend` owns upload processing, long-running analysis, runtime artifacts, and public payload shaping.
- `reading-companion-frontend` owns route rendering, upload UX, live progress surfaces, result pages, and mark actions.
- The workspace root owns shared commands and cross-project documentation.

## Product Loop
- The current canonical loop is `landing -> upload -> analysis -> book overview -> chapter deep read -> marks`.
- This matters architecturally because every major subsystem supports that loop:
  - frontend routes render it
  - backend APIs drive it
  - runtime artifacts persist it
  - contract docs stabilize it

## Main-Path Modules
- Backend application and public payload entrypoint:
  - `reading-companion-backend/src/api/app.py`
- Backend contract and shaping layer:
  - `reading-companion-backend/src/api/contract.py`
  - `reading-companion-backend/src/api/schemas.py`
  - `reading-companion-backend/src/library/catalog.py`
- Frontend route and adapter entrypoint:
  - `reading-companion-frontend/src/app/routes.tsx`
  - `reading-companion-frontend/src/app/lib/api.ts`

## Why The Current Main Path Exists
- The repo still shows evidence of more abstract or prototype-style agent paths.
- The current implementation favors a narrower but more operable path:
  - easier to run locally
  - easier to validate
  - easier to recover after interruption
  - easier to explain in a product demo
- That trade-off is part of the architecture story, not a weakness to hide.

## Runtime Story
- Development mode prioritizes hot reload and iteration speed.
- Stable/demo mode prioritizes predictability and recovery.
- Long-running analysis is treated as a first-class runtime concern rather than a background afterthought.
- Public analysis-state and job surfaces expose enough structure for the frontend to render progress and resume behavior coherently.

## Why This Is Stronger Than A Prompt Demo
- There is a defined product path instead of a one-off notebook or chat prototype.
- There is a stable public contract between backend and frontend.
- There is explicit runtime behavior for progress, pause, and recovery.
- There are evaluation artifacts that support quality discussion with actual evidence.

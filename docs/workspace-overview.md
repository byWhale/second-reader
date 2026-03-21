# Workspace Overview

Purpose: define workspace structure, ownership boundaries, and shared entrypoints.
Use when: deciding where changes belong or which side owns a behavior.
Not for: startup commands, runtime mode semantics, public API payload details, or temporary migration notes.
Update when: workspace structure, ownership boundaries, or primary shared entrypoints change.

## What This Root Is For
- one place to understand the full product
- one place to understand backend/frontend ownership boundaries
- one place to find shared entrypoints before diving into subproject-local code
- one place to find the top-level product-purpose doc before diving into journey or subsystem details

## Subprojects

### `reading-companion-backend`
- Python project declared in `pyproject.toml`
- FastAPI app in `src/api/app.py`
- public contract helpers in `src/api/contract.py`
- book/catalog shaping in `src/library/catalog.py`
- canonical shared book substrate and cross-mechanism contracts under `src/reading_core/`
- shared reading runtime and mechanism-hosting code under `src/reading_runtime/`
- built-in mechanism adapters under `src/reading_mechanisms/`
- current default reader implementation under `src/iterator_reader/`
- runtime artifacts stored under:
  - `output/`
  - `state/`
  - within `output/<book_id>/`, shared product/runtime artifacts live in top-level `public/` and `_runtime/`, while mechanism-private artifacts live under `_mechanisms/<mechanism_key>/`

### `reading-companion-frontend`
- Vite + React application
- routes in `src/app/routes.tsx`
- API client layer in `src/app/lib/api.ts`
- generated API types in `src/app/lib/generated/`

## Ownership Boundaries
- Backend owns:
  - upload processing
  - background jobs
  - book manifests
  - chapter results
  - marks persistence
  - shared reading runtime and mechanism selection boundaries
  - mechanism-specific reader implementations
  - OpenAPI contract and payload normalization
- Frontend owns:
  - route rendering
  - upload form UX
  - polling/WebSocket UI updates
  - result views and mark actions
  - locale-driven interface copy

## Shared Entry Points
- Product-purpose authority: `docs/product-overview.md`
- Product journey and surface authority: `docs/product-interaction-model.md`
- Shared backend mechanism-platform authority: `docs/backend-reading-mechanism.md`
- Backend mechanism catalog and per-mechanism docs: `docs/backend-reading-mechanisms/`
- Backend application entrypoint: `reading-companion-backend/src/api/app.py`
- Backend read CLI/runtime entrypoint: `reading-companion-backend/main.py`
- Backend contract and payload shaping: `reading-companion-backend/src/api/contract.py`, `reading-companion-backend/src/api/schemas.py`, `reading-companion-backend/src/library/catalog.py`
- Backend canonical book substrate and shared contracts: `reading-companion-backend/src/reading_core/`
- Backend runtime shell and mechanism registry: `reading-companion-backend/src/reading_runtime/`
- Backend built-in mechanism adapters: `reading-companion-backend/src/reading_mechanisms/`
- Backend current default reader implementation: `reading-companion-backend/src/iterator_reader/`
- Frontend route entrypoint: `reading-companion-frontend/src/app/routes.tsx`
- Frontend API adapter entrypoint: `reading-companion-frontend/src/app/lib/api.ts`

## Workflow Notes
- Use the workspace root for shared commands and cross-project work.
- Use child directories when a task is clearly isolated.
- Keep runtime data in `reading-companion-backend/`.
- Keep shared runtime/mechanism boundaries in backend-owned infrastructure, and keep reader-internal ontology inside the specific mechanism that owns it.
- Use `docs/backend-reading-mechanism.md` for shared mechanism boundaries and `docs/backend-reading-mechanisms/<mechanism>.md` for mechanism-private reading logic.
- Treat `reading-companion-backend/output/<book_id>/public/` and `reading-companion-backend/output/<book_id>/_runtime/` as shared cross-mechanism territory.
- Treat `reading-companion-backend/output/<book_id>/_mechanisms/<mechanism_key>/` as mechanism-owned territory for derived structures, runtime memory, checkpoints, and diagnostics.
- The workspace root is the shared Git root for both sub-applications.

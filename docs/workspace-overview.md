# Workspace Overview

Purpose: define workspace structure, ownership boundaries, and shared entrypoints.
Use when: deciding where changes belong or which side owns a behavior.
Not for: startup commands, runtime mode semantics, public API payload details, or temporary migration notes.
Update when: workspace structure, ownership boundaries, or primary shared entrypoints change.

## What This Root Is For
- one place to understand the full product
- one place to understand backend/frontend ownership boundaries
- one place to find shared entrypoints before diving into subproject-local code

## Subprojects

### `reading-companion-backend`
- Python project declared in `pyproject.toml`
- FastAPI app in `src/api/app.py`
- public contract helpers in `src/api/contract.py`
- book/catalog shaping in `src/library/catalog.py`
- runtime artifacts stored under:
  - `output/`
  - `state/`

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
  - OpenAPI contract and payload normalization
- Frontend owns:
  - route rendering
  - upload form UX
  - polling/WebSocket UI updates
  - result views and mark actions
  - locale-driven interface copy

## Shared Entry Points
- Backend application entrypoint: `reading-companion-backend/src/api/app.py`
- Backend contract and payload shaping: `reading-companion-backend/src/api/contract.py`, `reading-companion-backend/src/api/schemas.py`, `reading-companion-backend/src/library/catalog.py`
- Frontend route entrypoint: `reading-companion-frontend/src/app/routes.tsx`
- Frontend API adapter entrypoint: `reading-companion-frontend/src/app/lib/api.ts`

## Workflow Notes
- Use the workspace root for shared commands and cross-project work.
- Use child directories when a task is clearly isolated.
- Keep runtime data in `reading-companion-backend/`.
- The workspace root is the shared Git root for both sub-applications.

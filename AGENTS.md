# Reading Companion Workspace Guide

## Scope
- This parent directory is the shared workspace root for the Reading Companion project.
- Treat the codebase as one product with two sub-applications:
  - `reading-companion-backend`: FastAPI API, sequential deep-reading engine, runtime artifacts
  - `reading-companion-frontend`: Vite/React web client

## Precedence
- Root `AGENTS.md` defines cross-project rules.
- Child `AGENTS.md` files define local rules for that subproject.
- If rules conflict:
  1. obey this root file for workspace-level behavior
  2. obey the child file for subproject-local behavior

## Working Rules
- Start from the parent directory unless a task is explicitly isolated to one subproject.
- Check `README.md` and `docs/` before making structural changes.
- Preserve the two existing subdirectories and their boundaries. Do not collapse them into a new monorepo layout unless explicitly requested.
- Keep API changes synchronized across both sides:
  - backend contract changes require frontend route/client review
  - frontend integration changes require backend contract verification
- Prefer codifying workflows in root scripts and docs instead of leaving process knowledge only in chat.
- Keep runtime artifacts in `reading-companion-backend/` unless a task explicitly migrates them.
- Do not remove the frontend repo’s Figma Make history or generated structure unless the change has a clear maintenance benefit.

## First Files To Read
- Root:
  - `README.md`
  - `docs/workspace-overview.md`
  - `docs/api-contract.md`
  - `docs/api-integration.md`
  - `docs/agent-handoff.md`
- Backend:
  - `reading-companion-backend/AGENTS.md`
  - `reading-companion-backend/src/api/app.py`
  - `reading-companion-backend/src/library/catalog.py`
- Frontend:
  - `reading-companion-frontend/AGENTS.md`
  - `reading-companion-frontend/src/app/lib/api.ts`
  - `reading-companion-frontend/src/app/routes.tsx`

## Default Local Commands
- `make doctor`
- `make setup`
- `make dev-backend`
- `make dev-frontend`
- `make dev`
- `make test`
- `make build`

## Language Governance
- Follow `docs/language-governance.md` before adding or changing visible text.
- Classify user-visible text first:
  - content text
  - interface/control text
  - system/program-state text
  - fixed brand/governed terminology
- Do not handwrite key terminology or key product copy directly in UI components.
- Brand name `书虫` stays fixed; app interface copy follows the frontend locale layer.

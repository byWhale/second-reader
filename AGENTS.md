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

## Documentation Maintenance
- When a change alters how the product behaves, runs, or is maintained, update the relevant docs in the same task.
- Do not treat docs as optional follow-up work when the implementation changes any of the following:
  - runtime/startup/deploy workflows
  - frontend/backend API contract or integration behavior
  - language governance or controlled product copy
  - product interaction models or major UX conventions
- Minimum doc destinations:
  - `README.md` for operator-facing commands and quick-start behavior
  - `docs/api-contract.md` for public contract changes
  - `docs/api-integration.md` for runtime integration changes
  - `docs/language-governance.md` for visible-text governance changes
  - `docs/runtime-modes.md` for launcher, healthcheck, demo, and deploy mode changes
  - `docs/workspace-overview.md` or `docs/agent-handoff.md` when the cross-project working model changes
- If you intentionally leave docs unchanged, you should have a concrete reason, not just “code is self-explanatory.”

## First Files To Read
- Root:
  - `README.md`
  - `docs/workspace-overview.md`
  - `docs/api-contract.md`
  - `docs/api-integration.md`
  - `docs/agent-handoff.md`
  - `docs/runtime-modes.md`
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

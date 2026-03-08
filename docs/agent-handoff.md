# Agent Handoff

## Read This First
1. Root `AGENTS.md`
2. Root `README.md`
3. `docs/workspace-overview.md`
4. `docs/api-contract.md`
5. `docs/api-integration.md`

## If You Are Changing Backend API
- update backend schemas and handlers first
- verify frontend route/client assumptions in `reading-companion-frontend/src/app/lib/api.ts`
- review canonical route expectations in `docs/api-contract.md`

## If You Are Changing Frontend Data Flows
- do not reintroduce mock data as the primary source of truth
- keep canonical route compatibility with backend-returned URLs
- preserve the thin API adapter pattern instead of scattering raw fetch calls

## API Contract Authority
- `docs/api-contract.md` is the current authority for frontend/backend integration.
- If implementation and `docs/api-contract.md` disagree, do not patch one side in isolation. Verify both sides and correct the mismatch.
- `docs/api-integration.md` is the runtime companion doc, not the canonical contract.

## Local Runtime Facts
- backend runtime root defaults to `reading-companion-backend/`
- backend requires Python 3.11+
- backend startup automatically backfills legacy `output/*/structure.json` directories into current manifest/run-state artifacts
- frontend local defaults target backend `localhost:8000`
- two child directories still keep separate Git histories

## High-Risk Areas
- backend path handling for `output/` and `state/`
- route mismatches between frontend and backend-returned URLs
- reaction type mapping drift
- upload flow and live progress integration

## Remaining Migration Notes
- `/api/landing` and `/api/sample` still exist as compatibility endpoints, but the current landing page is frontend-owned and should not depend on them.
- Backend internals still use some legacy reaction naming such as `connect_back`; the public API contract now normalizes that to `retrospect`.
- Public IDs are now integer contract IDs. Internal runtime artifacts still use string identifiers under `reading-companion-backend/output/`, and the API layer is responsible for the translation.

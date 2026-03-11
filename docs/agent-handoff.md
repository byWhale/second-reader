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
- The machine-readable appendix in `docs/api-contract.md` is now part of the root contract drift gate. Keep it aligned with backend `src/api/contract.py` and frontend `src/app/lib/contract.ts`.
- If implementation and `docs/api-contract.md` disagree, do not patch one side in isolation. Verify both sides and correct the mismatch.
- `docs/api-integration.md` is the runtime companion doc, not the canonical contract.
- `make contract-check` is the first guard for contract drift, and `make e2e` is the canonical upload -> analysis -> chapter -> marks regression.

## Local Runtime Facts
- backend runtime root defaults to `reading-companion-backend/`
- backend requires Python 3.11+
- backend startup automatically backfills legacy `output/*/structure.json` directories into current manifest/run-state artifacts
- frontend local defaults target backend `localhost:8000`
- the workspace root is the single Git root for both sub-applications

## High-Risk Areas
- backend path handling for `output/` and `state/`
- route mismatches between frontend and backend-returned URLs
- reaction type mapping drift
- upload flow and live progress integration

## Remaining Migration Notes
- Landing is frontend-only now. Do not reintroduce backend-owned landing/sample endpoints unless the contract doc is updated first.
- Landing live preview can now pin real reactions by public ID. Configure `reading-companion-frontend/src/app/content/landing-content.ts` with `LANDING_PREVIEW_CONFIG.api.bookId`, `chapterId`, and optional `selectedReactionIds`.
- To discover candidate preview IDs for one chapter, run `make preview-reactions BOOK_ID=<bookId> CHAPTER_ID=<chapterId>` while the backend API is running.
- Backend still accepts old `connect_back` artifacts on read, but new runtime outputs should write `retrospect`, and the public API must keep normalizing old payloads.
- Public IDs are now integer contract IDs. Internal runtime artifacts still use string identifiers under `reading-companion-backend/output/`, and the API layer is responsible for the translation.
- Frontend request/response types should come from the committed OpenAPI snapshot via `src/app/lib/generated/api-schema.d.ts` and `src/app/lib/api-types.ts`. Keep runtime helpers in `src/app/lib/api.ts` thin.

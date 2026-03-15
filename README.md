# Reading Companion Workspace

This directory is the unified working root for the Reading Companion project.

The project is maintained as one product with two sub-applications:
- `reading-companion-backend`: FastAPI API, upload/job orchestration, sequential deep-reading engine
- `reading-companion-frontend`: Vite/React web UI

## Structure
- `reading-companion-backend/`: backend code, runtime artifacts, tests, `.env`
- `reading-companion-frontend/`: frontend code, Vite app, `.env.example`
- `docs/`: workspace-level docs for integration and handoff
- `scripts/`: root task wrappers used by the `Makefile`
- `.codex/`: local notes for future Codex threads

## Quick Start
1. Run `make doctor`
2. Install Python 3.11 or newer if the doctor script reports it missing
3. Run `make setup`
4. Start the backend with `make dev-backend`
5. Start the frontend with `make dev-frontend`
6. Or run both together with `make dev`
7. For a more stable local demo loop, use `make run-demo`

## Default Local URLs
- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- Backend docs: `http://localhost:8000/docs`
- Backend health: `http://localhost:8000/api/health`

## Environment

Backend environment lives in `reading-companion-backend/.env`.

Important backend variables:
- `LLM_BASE_URL`
- `LLM_API_KEY`
- `LLM_MODEL`
- `TAVILY_API_KEY`
- `UPLOAD_MAX_BYTES`
- `BACKEND_RUNTIME_ROOT`
- `BACKEND_CORS_ORIGINS`
- `BACKEND_HOST`
- `BACKEND_PORT`

Frontend environment is optional for local development and can be set via `reading-companion-frontend/.env.local`.

Important frontend variables:
- `VITE_API_BASE_URL`
- `VITE_WS_BASE_URL`

## Common Commands
- `make doctor`: validate prerequisites, ports, and env files
- `make setup`: install frontend deps and create/install backend virtualenv
- `make dev-backend`: run FastAPI from the workspace root safely, including legacy output backfill
- `make dev-frontend`: run Vite with the shared API defaults
- `make dev`: run both apps together
- `make run-demo`: run frontend plus a supervised non-reload backend that auto-restarts if it exits
- `make test`: run backend tests, frontend typecheck/build, and contract drift checks
- `make contract-check`: verify docs appendix, backend OpenAPI snapshot, and frontend contract guards
- `make e2e`: run the fixture-backed upload -> analysis -> book -> chapter -> marks Playwright flow
- `make build`: build the frontend bundle
- `make backfill-covers`: scan existing backend outputs, extract missing EPUB covers, and refresh manifests
- `cd reading-companion-frontend && npm run generate-api-types`: refresh generated frontend API types after the backend OpenAPI snapshot changes

## Key Docs
- [Workspace overview](docs/workspace-overview.md)
- [API contract](docs/api-contract.md)
- [API integration](docs/api-integration.md)
- [Agent handoff](docs/agent-handoff.md)

## Contract Validation
- `docs/api-contract.md` remains the human authority for the web/API boundary.
- The machine-readable appendix at the bottom of that file is checked against backend `src/api/contract.py` and frontend `src/app/lib/contract.ts`.
- Frontend API response/request types are generated from `contract/openapi.public.snapshot.json` into `reading-companion-frontend/src/app/lib/generated/api-schema.d.ts`.
- Run `make contract-check` before merging contract changes.
- Run `make e2e` for the fixture-backed canonical-route regression when changing upload, analysis, marks, or route wiring.

## Notes
- Runtime data remains under `reading-companion-backend/`.
- Legacy `structure.json`-only output folders are automatically backfilled into the current API-facing artifact format during `make setup` and `make dev-backend`.
- `make dev-backend` is intentionally a reload-enabled developer server. Use `make run-demo` for interviews or live demos where backend restarts should be automatic.
- The backend is not expected to run correctly with Python 3.9.x.
- The frontend is now wired to the backend API contract instead of the old mock-only flow.

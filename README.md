# Reading Companion Workspace

This directory is the unified working root for the Reading Companion project.

The project is maintained as one product with two sub-applications:
- `reading-companion-backend`: FastAPI API, upload/job orchestration, sequential deep-reading engine
- `reading-companion-frontend`: Vite/React web UI

The two child directories still keep their own Git history. This root exists to standardize local development, docs, agent handoff, and front/back integration.

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

## Default Local URLs
- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- Backend docs: `http://localhost:8000/docs`

## Environment

Backend environment lives in `reading-companion-backend/.env`.

Important backend variables:
- `LLM_BASE_URL`
- `LLM_API_KEY`
- `LLM_MODEL`
- `TAVILY_API_KEY`
- `SAMPLE_BOOK_ID`
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
- `make test`: run backend tests and frontend smoke validation
- `make build`: build the frontend bundle

## Key Docs
- [Workspace overview](docs/workspace-overview.md)
- [API contract](docs/api-contract.md)
- [API integration](docs/api-integration.md)
- [Agent handoff](docs/agent-handoff.md)

## Notes
- Runtime data remains under `reading-companion-backend/`.
- Legacy `structure.json`-only output folders are automatically backfilled into the current API-facing artifact format during `make setup` and `make dev-backend`.
- The backend is not expected to run correctly with Python 3.9.x.
- The frontend is now wired to the backend API contract instead of the old mock-only flow.

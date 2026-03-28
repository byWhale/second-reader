# Reading Companion Workspace

Purpose: provide setup, run, environment, local URL, and verification information for the workspace.
Use when: installing dependencies, starting local services, checking env vars, or running validation commands.
Not for: product flow decisions, public API contract details, runtime semantics, or temporary migration notes.
Update when: install/setup commands, startup commands, environment variables, default URLs, or validation commands change.

This directory is the unified working root for the Reading Companion project.

The project is maintained as one product with two sub-applications:
- `reading-companion-backend`: FastAPI API, upload/job orchestration, sequential deep-reading engine
- `reading-companion-frontend`: Vite/React web UI

## Structure
- `reading-companion-backend/`: backend code, runtime artifacts, tests, `.env`
- `reading-companion-frontend/`: frontend code, Vite app, `.env.example`
- `docs/`: workspace-level stable docs and temporary handoff notes
- `scripts/`: root task wrappers used by the `Makefile`

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
- `LLM_REGISTRY_PATH`
- provider secret env vars referenced by the registry, for example:
  - default local compat registry:
    - `LLM_API_KEY`
    - optional `LLM_API_KEY_SECONDARY`
    - `LLM_MODEL`
    - optional `LLM_DATASET_REVIEW_MODEL`
    - optional `LLM_EVAL_JUDGE_MODEL`
  - richer multi-provider example:
    - `MINIMAX_API_KEY`
    - `ANTHROPIC_API_KEY_PRIMARY`
    - `ANTHROPIC_API_KEY_SECONDARY`
    - `GOOGLE_GENAI_API_KEY`
- legacy compatibility variables still work when a structured registry is not configured:
  - `LLM_PROVIDER_CONTRACT`
  - `LLM_BASE_URL`
  - `LLM_API_KEY`
  - `LLM_MODEL`
  - optional `LLM_DATASET_REVIEW_MODEL`
  - optional `LLM_EVAL_JUDGE_MODEL`
- `TAVILY_API_KEY`
- `UPLOAD_MAX_BYTES`
- `BACKEND_RUNTIME_ROOT`
- `BACKEND_CORS_ORIGINS`
- `BACKEND_HOST`
- `BACKEND_PORT`

The backend ships a structured registry example at
`reading-companion-backend/config/llm_registry.example.json`.
It also ships a Minimax-compatible structured registry for the current local runtime at
`reading-companion-backend/config/llm_registry.minimax_legacy_compatible.json`.
Use that file to define:
- provider contracts such as `anthropic`, `google_genai`, and `openai_compatible`
- key pools for same-model failover
- adaptive same-key concurrency policy:
  - `initial_max_concurrency`
  - `probe_max_concurrency`
  - `min_stable_concurrency`
  - `backoff_window_seconds`
  - `recover_window_seconds`
- pinned task-level profiles:
  - `runtime_reader_default`
  - `dataset_review_high_trust`
  - `eval_judge_high_trust`
  - each profile may also set `default_burst_concurrency`

Current backend defaults are now throughput-oriented for new Python processes:
- same-key parallelism is enabled by default
- provider concurrency starts at `6`, can probe up to `12`, and backs off automatically on sustained timeout/rate-limit pressure
- eval/review worker counts derive from the shared concurrency policy rather than fixed script-local defaults

Frontend environment is optional for local development and can be set via `reading-companion-frontend/.env.local`.

Important frontend variables:
- `VITE_API_BASE_URL`
- `VITE_WS_BASE_URL`

## Common Commands
- `make doctor`: validate prerequisites, ports, and env files
- `make setup`: install frontend deps and create/install backend virtualenv
- `make dev-backend`: run FastAPI from the workspace root safely
- `make dev-frontend`: run Vite with the shared API defaults
- `make dev`: run both apps together
- `make run-demo`: run frontend plus a supervised non-reload backend that auto-restarts if it exits
- `make test`: run backend tests, frontend typecheck/build, and contract drift checks
- `make contract-check`: verify docs appendix, backend OpenAPI snapshot, and frontend contract guards
- `make e2e`: run the fixture-backed upload -> analysis -> book -> chapter -> marks Playwright flow
- `make build`: build the frontend bundle
- `make backfill-covers`: scan existing backend outputs, extract missing EPUB covers, and refresh manifests
- `cd reading-companion-frontend && npm run generate-api-types`: refresh generated frontend API types after the backend OpenAPI snapshot changes

## Long-Running Eval Jobs
Use the backend background-job registry for evaluation, packet review, or dataset jobs that may run for `10-15` minutes or longer.

- Register or update one job:
  - `cd reading-companion-backend && .venv/bin/python scripts/register_background_job.py --task-ref "execution-tracker#example" --lane mechanism_eval --purpose "English chapter-core rerun" --command ".venv/bin/python eval/attentional_v2/run_chapter_comparison.py --help" --cwd "$PWD"`
- Refresh active jobs:
  - `cd reading-companion-backend && .venv/bin/python scripts/check_background_jobs.py`
- Refresh and also execute stored `check_command` probes:
  - `cd reading-companion-backend && .venv/bin/python scripts/check_background_jobs.py --run-check-commands`

Registry files live under `reading-companion-backend/state/job_registry/`:
- `active_jobs.json`: source of truth for active background jobs
- `active_jobs.md`: human-readable mirror for handoff and agent recovery
- `history_jobs.jsonl`: archived terminal jobs

## Validation
- `make contract-check` is the first guard for public contract drift.
- `make e2e` is the canonical upload -> analysis -> book -> chapter -> marks regression.

## Next Docs
- Start with `AGENTS.md` for workspace rules and document routing.
- Read the relevant child `AGENTS.md` before making subproject-local changes.

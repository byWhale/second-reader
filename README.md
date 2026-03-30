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
- `docs/tasks/`: workspace task index for agent switching
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
- `LLM_TARGETS_PATH`
- `LLM_PROFILE_BINDINGS_PATH`
- optional `LLM_TARGETS_JSON`
- optional `LLM_PROFILE_BINDINGS_JSON`
- optional operator overrides: `LLM_FORCE_TARGET_ID`, `LLM_FORCE_TIER_ID`
- compatibility: `LLM_REGISTRY_PATH`, `LLM_REGISTRY_JSON`
- `TAVILY_API_KEY`
- `UPLOAD_MAX_BYTES`
- `BACKEND_RUNTIME_ROOT`
- `BACKEND_CORS_ORIGINS`
- `BACKEND_HOST`
- `BACKEND_PORT`

Recommended local LLM setup:
- point the backend at two untracked local JSON files from `reading-companion-backend/.env`:
  - `LLM_TARGETS_PATH=config/llm_targets.local.json`
  - `LLM_PROFILE_BINDINGS_PATH=config/llm_profile_bindings.local.json`
- edit `reading-companion-backend/config/llm_targets.local.json` to define named runtime targets
  - write the provider `contract`, `base_url`, `model`, and one or more credentials there
  - this is the file where you put URL, model name, and API key information
- edit `reading-companion-backend/config/llm_profile_bindings.local.json` to bind stable project profile ids to those named targets
  - current stable profile ids are:
    - `runtime_reader_default`
    - `dataset_review_high_trust`
    - `eval_judge_high_trust`
  - the recommended universal pattern is ordered `target_tiers`
    - put the preferred high-throughput target in the `primary` tier
    - put backup targets in later tiers
    - each scope chooses one concrete target up front and stays pinned to it for the full runtime, dataset-review, or evaluation scope
  - this is the file where you choose which target tier policy each profile uses and any profile-level overrides such as `temperature`, `max_output_tokens`, `retry_attempts`, `max_concurrency`, `quota_retry_attempts`, and `quota_wait_budget_seconds`

Recommended tiered binding shape:
```json
{
  "profiles": [
    {
      "profile_id": "runtime_reader_default",
      "target_tiers": [
        {
          "tier_id": "primary",
          "target_ids": ["minimax_m27_highspeed"],
          "min_required_stable_concurrency": 4
        },
        {
          "tier_id": "backup",
          "target_ids": ["minimax_m27_standard"]
        }
      ],
      "temperature": 0.2,
      "max_output_tokens": 4096,
      "timeout_seconds": 120,
      "retry_attempts": 3,
      "max_concurrency": 12,
      "default_burst_concurrency": 12,
      "quota_retry_attempts": 2,
      "quota_wait_budget_seconds": 25
    }
  ]
}
```

Tracked templates for the new local setup:
- `reading-companion-backend/config/llm_targets.local.example.json`
- `reading-companion-backend/config/llm_profile_bindings.local.example.json`

Compatibility and fallback modes:
- inline equivalents also work:
  - `LLM_TARGETS_JSON`
  - `LLM_PROFILE_BINDINGS_JSON`
- the older single registry surface still works:
  - `LLM_REGISTRY_PATH`
  - `LLM_REGISTRY_JSON`
- legacy env-only fallback still works when no structured config is provided:
  - `LLM_PROVIDER_CONTRACT`
  - `LLM_BASE_URL`
  - `LLM_API_KEY`
  - `LLM_MODEL`
  - optional `LLM_DATASET_REVIEW_MODEL`
  - optional `LLM_EVAL_JUDGE_MODEL`
  - optional `LLM_RUNTIME_MAX_OUTPUT_TOKENS`
  - optional `LLM_DATASET_REVIEW_MAX_OUTPUT_TOKENS`
  - optional `LLM_EVAL_JUDGE_MAX_OUTPUT_TOKENS`

Reference and compatibility files:
- shared provider/profile registry example:
  - `reading-companion-backend/config/llm_registry.example.json`
- Minimax-focused compatibility-mode registry:
  - `reading-companion-backend/config/llm_registry.minimax_legacy_compatible.json`

The shared LLM layer still supports:
- provider contracts such as `anthropic`, `google_genai`, and `openai_compatible`
- multiple credentials inside one named target for same-model failover
- ordered target tiers for profile routing
  - primary and backup routing is no longer hardcoded to one provider family
  - new scopes pick the first healthy target that meets the tier policy, then stay pinned to that target for the whole scope
- adaptive same-key concurrency policy:
  - `initial_max_concurrency`
  - `probe_max_concurrency`
  - `min_stable_concurrency`
  - `backoff_window_seconds`
  - `recover_window_seconds`
- quota-pressure coordination policy:
  - `quota_cooldown_base_seconds`
  - `quota_cooldown_max_seconds`
  - `quota_state_ttl_seconds`
- stable project profile ids with profile-level invocation settings:
  - `runtime_reader_default`
  - `dataset_review_high_trust`
  - `eval_judge_high_trust`

Temporary operator overrides:
- `LLM_FORCE_TARGET_ID`
  - force new scopes onto one named target for debugging or recovery
- `LLM_FORCE_TIER_ID`
  - force new scopes onto one named tier such as `primary` or `backup`
- these overrides apply only when a new scope starts and should not be the normal policy surface

Current backend defaults are now throughput-oriented for new Python processes:
- same-key parallelism is enabled by default
- provider concurrency starts at `6`, can probe up to `12`, and backs off automatically on sustained timeout/rate-limit pressure
- provider quota cooldown state is shared under `BACKEND_RUNTIME_ROOT/state/llm_gateway/providers/` so sibling Python processes can honor the same bounded wait window
- runtime keeps a short bounded quota wait budget before surfacing `llm_quota`, while dataset review and eval judge profiles keep a longer bounded quota wait budget for offline work
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
- `make agent-context`: print the canonical agent-switching brief from current state, tasks, jobs, and git status
- `make agent-check`: run contract/doc checks plus switching-memory traceability warnings
- `make backfill-covers`: scan existing backend outputs, extract missing EPUB covers, and refresh manifests
- `make dataset-review-pipeline DATASET_REVIEW_PIPELINE_ARGS="..."`: run the reusable mechanical dataset-review packet pipeline from the workspace root
- `make library-source-intake LIBRARY_SOURCE_INTAKE_ARGS="..."`: ingest books from the managed library inbox into canonical local source storage and the source catalog
- `make closed-loop-benchmark-curation CLOSED_LOOP_BENCHMARK_CURATION_ARGS="..."`: run the first scratch-safe closed-loop benchmark-curation pass for the managed local supplement
- `cd reading-companion-frontend && npm run generate-api-types`: refresh generated frontend API types after the backend OpenAPI snapshot changes

## Dataset Source Intake
Use the managed library inbox for future private/public source additions.

`reading-companion-backend/state/` is repo-local mutable operational data. The inbox is meant to stay simple for operators; the system does the classification and canonical copying.

Drop books into:
- `reading-companion-backend/state/library_inbox/`

Nested batch directories are allowed under that root for your own organization.

Optional sidecar metadata:
- place `<book>.source.json` next to the source file
- useful fields:
  - `source_id`
  - `title`
  - `author`
  - `canonical_filename`
  - `language`
  - `visibility`
  - `type_tags`
  - `role_tags`
  - `selection_priority`
  - `notes`
- normal use does not require a sidecar
- `language` is optional and is auto-detected when omitted
- `visibility` is optional compatibility metadata only
- new canonical managed copies no longer route into separate public/private folders
- if you omit `source_id`, the default generated id now follows `<canonical_stem>_<language>`
- most normal product work should ignore `visibility` entirely

Run intake:
- dry-run:
  - `make library-source-intake LIBRARY_SOURCE_INTAKE_ARGS="--dry-run"`
- ingest everything currently in the inbox:
  - `make library-source-intake`
- recover a missing source catalog from existing managed library files when this checkout already has `state/library_sources/` but no catalog:
  - `make library-source-intake LIBRARY_SOURCE_INTAKE_ARGS="--bootstrap-library-sources --run-id bootstrap_existing_sources_20260330"`
- ingest only English sources after automatic language resolution:
  - `make library-source-intake LIBRARY_SOURCE_INTAKE_ARGS="--language en"`
- optional compatibility filter if you need to inspect only explicitly public or private records:
  - `make library-source-intake LIBRARY_SOURCE_INTAKE_ARGS="--visibility public"`

Intake outputs:
- canonical copied books under `reading-companion-backend/state/library_sources/`
- current managed copies are language-rooted, for example:
  - `reading-companion-backend/state/library_sources/en/walden.epub`
  - `reading-companion-backend/state/library_sources/zh/朝花夕拾.epub`
- source catalog:
  - `reading-companion-backend/state/dataset_build/source_catalog.json`
  - `reading-companion-backend/state/dataset_build/source_catalog.md`
- per-run summaries:
  - `reading-companion-backend/state/dataset_build/source_intake_runs/`
- compatibility recovery note:
  - bootstrap mode seeds `source_catalog.json` from existing `state/library_sources/` files plus tracked manifest metadata without copying files again
  - older compatibility paths such as `state/library_sources/en/private/...` can still be backfilled into the catalog even though new operator-driven intake should use the simpler one-inbox workflow

## Dataset Review Pipeline
Use the reusable dataset-review pipeline when the work is limited to the mechanical packet lifecycle:
- generate a revision/replacement packet
- run packet case-design audit
- run LLM packet adjudication
- import and archive the packet
- refresh the review queue summary
- emit a final stop-and-summarize report

The pipeline intentionally stops there. It does not reopen benchmark promotion, freeze reviewed slices, or launch durable-trace, re-entry, or runtime-viability work automatically.

Current local-only English cleanup example:
- `make dataset-review-pipeline DATASET_REVIEW_PIPELINE_ARGS="--dataset-id attentional_v2_private_library_excerpt_en_v2 --family excerpt_cases --storage-mode local-only --packet-id attentional_v2_private_library_cleanup_en_example"`

Long-running wrapper example:
- `cd reading-companion-backend && .venv/bin/python scripts/run_registered_job.py --task-ref "execution-tracker#example" --lane dataset_growth --purpose "English dataset review pipeline" --cwd "$PWD" -- .venv/bin/python -m eval.attentional_v2.run_dataset_review_pipeline --dataset-id attentional_v2_private_library_excerpt_en_v2 --family excerpt_cases --storage-mode local-only --packet-id attentional_v2_private_library_cleanup_en_example`

## Closed-Loop Benchmark Curation
Use the first closed-loop benchmark-curation runner when you want one scratch-safe build-review-import pass over the managed local supplement.

Current scope:
- construct the question-aligned scratch datasets from managed local sources
- export initial `--only-unreviewed` review packets
- run case-design audit
- run LLM adjudication
- import and archive the packets
- optionally run one bounded revision/replacement repair wave
- refresh the queue summary
- emit a final stop-and-summarize report

Current boundaries:
- default mode is scratch-safe and writes run-scoped manifests/artifacts under `reading-companion-backend/state/dataset_build/build_runs/<run_id>/`
- scratch datasets still live under `reading-companion-backend/state/eval_local_datasets/`, but they use unique run-scoped dataset ids
- if the managed source catalog is missing but `state/library_sources/` already exists, the builder path now recovers by bootstrapping the catalog once before continuing
- `--from-stage` / `--through-stage` now support bounded partial runs cleanly, so the controller can stop after construction or export for smoke/recovery work without forcing `final_summary`
- the runner stops after summarizing and does not reopen promotion, freeze reviewed slices, or launch runtime/deployment decisions automatically

Examples:
- dry-run one scratch pass:
  - `make closed-loop-benchmark-curation CLOSED_LOOP_BENCHMARK_CURATION_ARGS="--run-id demo_curate --dry-run"`
- run only the scratch dataset-construction stage through the controller:
  - `make closed-loop-benchmark-curation CLOSED_LOOP_BENCHMARK_CURATION_ARGS="--run-id demo_construct --language en --limit-sources 1 --through-stage construct_dataset"`
- run a bounded English-only scratch pass over two managed sources:
  - `make closed-loop-benchmark-curation CLOSED_LOOP_BENCHMARK_CURATION_ARGS="--run-id demo_curate --language en --limit-sources 2"`
- run the same one-source English scratch smoke plus one repair wave that has already been validated on the recovered catalog:
  - `make closed-loop-benchmark-curation CLOSED_LOOP_BENCHMARK_CURATION_ARGS="--run-id demo_curate --language en --limit-sources 1 --repair-open-backlog"`
- include one bounded repair wave after the initial import:
  - `make closed-loop-benchmark-curation CLOSED_LOOP_BENCHMARK_CURATION_ARGS="--run-id demo_curate --repair-open-backlog"`

Long-running wrapper example:
- `cd reading-companion-backend && .venv/bin/python scripts/run_registered_job.py --task-ref "execution-tracker#dataset-platform" --lane dataset_platform --purpose "Closed-loop benchmark curation scratch pass" --cwd "$PWD" -- .venv/bin/python -m eval.attentional_v2.run_closed_loop_benchmark_curation --run-id demo_curate --repair-open-backlog`

## Long-Running Eval Jobs
Use the backend background-job registry for evaluation, packet review, or dataset jobs that may run for `10-15` minutes or longer.

- Register or update one job:
  - `cd reading-companion-backend && .venv/bin/python scripts/register_background_job.py --task-ref "execution-tracker#example" --lane mechanism_eval --purpose "English chapter-core rerun" --command ".venv/bin/python eval/attentional_v2/run_chapter_comparison.py --help" --cwd "$PWD"`
- Launch one generic job through the registry wrapper:
  - `cd reading-companion-backend && .venv/bin/python scripts/run_registered_job.py --task-ref "execution-tracker#example" --lane mechanism_eval --purpose "English chapter-core rerun" --cwd "$PWD" -- .venv/bin/python eval/attentional_v2/run_chapter_comparison.py --help`
- Launch one generic job through the detached wrapper when the shell/session itself may go away:
  - `cd reading-companion-backend && .venv/bin/python scripts/launch_registered_job_detached.py -- --root "$PWD" --task-ref "execution-tracker#example" --lane mechanism_eval --purpose "English chapter-core rerun" --cwd "$PWD" -- .venv/bin/python eval/attentional_v2/run_chapter_comparison.py --help`
  - this starts `run_registered_job.py` in a new session so the registered job can survive non-interactive tooling shells more reliably
- Refresh active jobs:
  - `cd reading-companion-backend && .venv/bin/python scripts/check_background_jobs.py`
- Refresh and also execute stored `check_command` probes:
  - `cd reading-companion-backend && .venv/bin/python scripts/check_background_jobs.py --run-check-commands`

Registry files live under `reading-companion-backend/state/job_registry/`:
- `jobs/<job_id>.json`: canonical per-job source of truth for product and offline jobs
- `active_jobs.json`: derived active-job view for operator-facing long-running offline work
- `active_jobs.md`: human-readable mirror for handoff and agent recovery
- `history_jobs.jsonl`: archived terminal jobs

## Validation
- `make contract-check` is the first guard for public contract drift.
- `make agent-check` is the canonical switching-memory guard for current state, task routing, and handoff hygiene.
- `make e2e` is the canonical upload -> analysis -> book -> chapter -> marks regression.

## Next Docs
- Start with `AGENTS.md` for workspace rules and document routing.
- Read `docs/current-state.md` for canonical live project status.
- Read the relevant child `AGENTS.md` before making subproject-local changes.
- Read `docs/tasks/registry.md` for the active task router and evidence chain.
- Read `docs/source-of-truth-map.md` when deciding where durable information belongs.

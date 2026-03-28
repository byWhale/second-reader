# Runtime Modes

Purpose: define startup, supervision, healthcheck, deployment, and resume semantics across runtime modes.
Use when: changing launcher behavior, deploy entrypoints, resume/recovery rules, or operator-facing runtime expectations.
Not for: local setup commands, public API field definitions, or temporary migration notes.
Update when: startup commands, reload behavior, supervision, healthchecks, deployment entrypoints, or recovery rules change.

This document defines how the Reading Companion project should be started in different environments.

Unless noted otherwise, the runtime and recovery behavior described here refers to the current sequential deep-reading workflow rather than the older `book_analysis` capability.

## Why This Exists
- The project now has more than one valid way to run.
- Those modes are intentionally different.
- Agents and humans should not have to infer launcher intent from shell scripts alone.

## Modes

### Development mode
Use when you are actively changing code and want hot reload.

Commands:
- `make dev-backend`
- `make dev`

Behavior:
- backend runs with `reload=True`
- backend is not supervised
- if the backend exits, it stays down until you restart it
- this is the right mode for day-to-day coding

Do not use this mode for:
- interview demos
- production
- Railway deployment

### Demo mode
Use when you want a more stable local presentation loop.

Command:
- `make run-demo`

Behavior:
- frontend starts locally
- backend starts in stable mode with `reload=False`
- a simple local restart loop watches the backend
- if the backend process exits unexpectedly, the loop starts it again

Important:
- demo mode only auto-restarts the backend while the outer `run-demo` process is still running
- stopping `make run-demo` with `Ctrl+C` stops the supervisor and the frontend
- this is a local convenience mode, not a production supervisor

### Stable backend mode
Use when a platform or external supervisor should own restarts.

Command:
- `./scripts/run-backend-stable.sh demo`
- `./scripts/run-backend-stable.sh prod`

Behavior:
- backend runs with `reload=False`
- startup logs print:
  - run mode
  - host
  - port
  - runtime root
- no built-in restart loop is attached in this launcher

Use cases:
- `demo`: local stable backend without autoreload
- `prod`: deployment entrypoint for platforms like Railway

## Healthcheck

Endpoint:
- `GET /api/health`

Purpose:
- lightweight liveness probe
- should stay cheap and not depend on heavy runtime scans

Current response includes:
- `status`
- `service`
- `mode`
- `host`
- `port`
- `runtime_root`
- `version` when available

## Railway

Railway should use the stable backend entrypoint, not the development launcher.

Current config:
- `railway.json`

Expected behavior:
- start command uses stable backend mode
- Railway owns restart behavior
- Railway checks `/api/health`

## Frontend Error Handling

When the backend is unreachable:
- the frontend should show a “backend unavailable” style message
- it should not only surface a raw `Failed to fetch`

This distinction belongs to operator/demo reliability, not business logic.

## Maintenance Rule

If a task changes:
- startup commands
- reload behavior
- supervision/restart behavior
- deploy entrypoints
- healthcheck behavior

then update this document in the same task.

## Runtime Guardrails

- Backend CLI and stable-server entrypoints require Python 3.11+ and should fail fast under older interpreters.
- Background jobs inherit the backend interpreter. If the backend is started under an unsupported Python runtime, job launch is rejected and the affected book writes a `runtime_environment_error` event into the internal system activity stream.
- When a job process stays alive but runtime state stops updating, the backend pauses the job and emits system-side activity events such as `runtime_stalled` and `job_paused_by_runtime_guard`.
- Raw stack traces remain in the internal technical diagnostic log; operator-facing summaries belong in the internal system activity stream.
- New backend Python processes also inherit the structured LLM registry and its adaptive concurrency policy at startup.
  - same-key parallelism is enabled by default for configured providers
  - the current local default starts at `6` in-flight calls, can probe upward to `12`, and backs off automatically under sustained provider pressure
  - already-running Python processes keep the code and env they started with; changing the registry or concurrency code on disk does not mutate an in-flight run until restart

## Resume And Recovery

- Sequential deep-reading checkpoints are segment-based. `last_checkpoint_at` now advances during deep reading, not only during structure parse.
- Resume safety is governed by `resume_compat_version`, not by deploy version or git state. Only changes to persisted recovery semantics should bump it.
- Development mode treats cross-boot unfinished jobs as untrusted. If an active job record carries an older `boot_id`, the backend abandons that run, writes `dev_run_abandoned` to the internal system activity stream, and expects a fresh rerun.
- Demo/prod mode resumes only when the job record and persisted runtime artifacts all match the current `resume_compat_version`.
- If demo/prod detects an incompatible live checkpoint, it archives the current run under `_history/runs/<job_id>/`, clears live runtime artifacts, writes `resume_incompatible` plus `fresh_rerun_started`, and launches a fresh run without `--continue`.
- Stalled demo/prod runtimes may auto-resume once from the latest checkpoint. A second stall leaves the run in `paused` for operator review instead of retrying indefinitely.

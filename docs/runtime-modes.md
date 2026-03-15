# Runtime Modes

This document defines how the Reading Companion project should be started in different environments.

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
- [`railway.json`](/Users/baiweijiang/Documents/Projects/reading-companion/railway.json)

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

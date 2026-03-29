# Source Of Truth Map

Purpose: map important project information to one canonical location, one optional machine-readable companion, one validation command, and one update trigger.
Use when: deciding where durable information belongs or checking whether a handoff/state update was written to the right place.
Not for: product behavior, API semantics, or temporary session scratch notes.
Update when: canonical storage locations, machine-readable companions, validation commands, or update triggers change.

This workspace is repo-first. Chat, Notion, and other tools may incubate work, but they are not authoritative for current project state.

## Canonical Categories

| Category | Canonical location | Machine-readable companion | Validation command | Update trigger |
| --- | --- | --- | --- | --- |
| Workspace rules and reading order | `AGENTS.md` | none | `make agent-check` | document layering, load order, routing, or cross-project collaboration rules change |
| Setup, run commands, env, local URLs | `README.md` | none | `make doctor`, `make agent-check` | install/run commands, env vars, validation commands, or default URLs change |
| Workspace structure and ownership boundaries | `docs/workspace-overview.md` | none | `make agent-check` | shared entrypoints, file placement, or ownership boundaries change |
| Product truths and guardrails | `docs/product-overview.md` | none | `make agent-check` | product essence, value channels, or canonical-vs-emerging territory changes |
| Product interaction model | `docs/product-interaction-model.md` | none | `make agent-check` | user journey, route responsibilities, or core UX conventions change |
| Public API contract | `docs/api-contract.md` | fenced JSON appendix | `make contract-check` | public routes, fields, enums, IDs, or stable request/response shapes change |
| Frontend/backend integration wiring | `docs/api-integration.md` | fenced JSON appendix | `make contract-check` | frontend-used endpoints, polling, realtime wiring, or runtime data flow change |
| Runtime modes and recovery rules | `docs/runtime-modes.md` | none | `make agent-check` | launcher behavior, healthchecks, deployment entrypoints, or resume rules change |
| Shared backend mechanism platform | `docs/backend-reading-mechanism.md` | none | `make agent-check` | shared mechanism boundaries, status model, or doc routing change |
| Current mechanism internals | `docs/backend-reading-mechanisms/<mechanism>.md` | fenced JSON appendix when maintained for that mechanism | `make contract-check` for the default mechanism, `make agent-check` otherwise | a mechanism's ontology, loop, prompt assembly, memory model, or private artifacts change |
| Reader evaluation constitution | `docs/backend-reader-evaluation.md` | none | `make agent-check` | quality dimensions, evaluation workflow, judge policy, or artifact routing change |
| Public-state aggregation rules | `docs/backend-state-aggregation.md` | none | `make agent-check` | source artifacts, aggregation responsibilities, or normalization boundaries change |
| Current workspace status | `docs/current-state.md` | fenced JSON appendix | `make agent-check` | current objective, now/next/blocked state, active jobs, open decisions, or recommended reading path change |
| Current workspace task index | `docs/tasks/registry.md` | `docs/tasks/registry.json` | `make agent-check` | task status, priority, blockers, decision refs, job refs, or evidence refs change |
| Dataset-platform source intake state | `reading-companion-backend/state/dataset_build/source_catalog.json` | `reading-companion-backend/state/dataset_build/source_catalog.md`, `reading-companion-backend/state/dataset_build/source_intake_runs/<run_id>.json` | `make library-source-intake LIBRARY_SOURCE_INTAKE_ARGS="--dry-run"`, `make agent-check` | source-book intake workflow, catalog records, or dataset-platform source-governance state change |
| Long-running job runtime state | `reading-companion-backend/state/job_registry/active_jobs.json` | `reading-companion-backend/state/job_registry/active_jobs.md` | `cd reading-companion-backend && .venv/bin/python scripts/check_background_jobs.py`, `make agent-check` | long-running offline job status, observations, or recovery metadata change |
| Detailed initiative trackers | initiative-local tracker such as `docs/implementation/new-reading-mechanism/execution-tracker.md` | initiative-local JSON or manifests when available | initiative-specific checks plus `make agent-check` | a tracker's phase state, open checklist, or evidence-bearing progress changes |
| Decision history | `docs/history/decision-log.md` | stable decision IDs inside the document | `make contract-check`, `make agent-check` | a design-bearing change, reversal, or new inflection point would be hard to reconstruct later |
| Session-only scratch notes | `docs/agent-handoff.md` | none | `make agent-check` warns when scratch content remains | only while a task is actively in-flight and the notes are not yet canonicalized elsewhere |

## Operating Rules
- Keep mutable runtime job state only in the backend job registry.
- Keep durable current state in `docs/current-state.md`, not in `docs/agent-handoff.md`.
- Keep workspace task routing in `docs/tasks/registry.*`, and link each task outward to detailed trackers, truth docs, decisions, jobs, and evidence.
- If a piece of information matters after the current chat ends, it must be stored in one of the canonical locations above.
- If the same durable fact appears in both `docs/agent-handoff.md` and a canonical file, the canonical file wins.

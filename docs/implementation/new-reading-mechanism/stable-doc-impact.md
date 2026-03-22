# New Reading Mechanism Stable Doc Impact Map

Purpose: keep the implementation project aligned with the repo's documentation trigger matrix by showing which stable docs must be updated when a workstream lands.
Use when: a phase starts landing real behavior, runtime semantics, or compatibility changes.
Not for: temporary implementation rationale or progress logging.
Update when: the project scope expands, a workstream changes, or a new stable-doc trigger becomes relevant.

## How To Use This File
- Check this map before merging behavior that changes runtime semantics, mechanism internals, aggregation, or evaluation behavior.
- If a landed change matches a row below, update the listed stable docs in the same task.
- If a row is no longer accurate, fix this file before relying on it.

## Impact Map
| Workstream / landed change | Stable docs that must be updated | Why |
| --- | --- | --- |
| Shared mechanism boundary changes | `docs/backend-reading-mechanism.md` | Shared-vs-mechanism ownership, status routing, artifact boundary rules |
| New mechanism stable ontology, loop, prompts, memory, or artifacts | `docs/backend-reading-mechanisms/<mechanism>.md` | Per-mechanism stable authority |
| Mechanism catalog, status, or naming changes | `docs/backend-reading-mechanisms/README.md` | Catalog and authoring-rule authority |
| Upload/start/resume/job-stage semantics change | `docs/backend-sequential-lifecycle.md` | Job lifecycle and runtime recovery authority |
| Shared artifact sourcing or aggregation behavior changes | `docs/backend-state-aggregation.md` | Source-artifact mapping and normalization boundary |
| Evaluation methodology or eval artifact routing changes | `docs/backend-reader-evaluation.md` | Shared evaluation constitution and artifact routing |
| Public routes, payloads, IDs, reaction taxonomy, or envelopes change | `docs/api-contract.md` | Public contract authority |
| Routed frontend endpoint usage, polling, or WebSocket coordination changes | `docs/api-integration.md` | Operational integration authority |
| Runtime launcher, supervision, healthcheck, or resume-mode behavior changes | `docs/runtime-modes.md` | Runtime mode and recovery authority |
| Product flow, page responsibilities, or canonical route meaning changes | `docs/product-interaction-model.md` | Canonical product journey authority |
| Product purpose, guardrails, or value framing changes | `docs/product-overview.md` | Stable product essence authority |
| Workspace ownership boundaries or shared entrypoints change | `docs/workspace-overview.md` | Workspace structure and responsibility authority |
| Backend-local stable constraints or default mechanism path change | `reading-companion-backend/AGENTS.md` | Backend-local engineering constraints |
| Frontend-local constraints or visible UI integration rules change | `reading-companion-frontend/AGENTS.md` | Frontend-local integration and validation constraints |
| Current temporary migration risks or active implementation warnings change | `docs/agent-handoff.md` | Temporary working note, not source of truth |
| Default mechanism changes or a major architecture direction is fixed | `docs/history/decision-log.md` | Decision-bearing history trail |

## Current Expectation
- During early implementation, most updates should stay in the temporary workspace.
- Stable docs should be updated as soon as behavior becomes real, shared, or decision-bearing.
- Do not wait until the entire mechanism is finished if a landed phase already changed a stable authority surface.

# Reading Companion Workspace Guide

Purpose: define workspace-level rules, document load order, and doc-to-task routing.
Use when: starting any task in this workspace or deciding which docs must be updated together.
Not for: stable product behavior, public API details, runtime semantics, or temporary migration notes.
Update when: document layering, reading order, task routing, or cross-project collaboration rules change.

## Scope
- This parent directory is the shared workspace root for the Reading Companion project.
- Treat the codebase as one product with two sub-applications:
  - `reading-companion-backend`: FastAPI API, sequential deep-reading engine, runtime artifacts
  - `reading-companion-frontend`: Vite/React web client

## Precedence
- Root `AGENTS.md` defines workspace-level behavior.
- Child `AGENTS.md` files define subproject-local constraints.
- If rules conflict:
  1. obey this root file for workspace-level behavior
  2. obey the child file for subproject-local behavior

## Working Rules
- Start from the parent directory unless a task is explicitly isolated to one subproject.
- Preserve the two existing subdirectories and their boundaries. Do not collapse them into a new monorepo layout unless explicitly requested.
- Keep API changes synchronized across both sides:
  - backend contract changes require frontend route/client review
  - frontend integration changes require backend contract verification
- Prefer codifying workflows in root scripts and docs instead of leaving process knowledge only in chat.
- Long-running eval or dataset jobs should not live only in chat memory.
  - If a task is expected to run longer than roughly `10-15` minutes, register it in the backend background-job registry before or immediately after launch.
  - Before starting overlapping long-running work, check the active registry first so a new agent does not duplicate or lose an in-flight run.
- When a task introduces or expands a generated intermediate-artifact directory under tracked repo territory, update `.gitignore` in the same task.
  - Do not leave new runtime, eval, packet, or scratch output directories tracked by accident and plan to clean them up later.
  - If one generated artifact really must be committed as durable evidence, force-add it intentionally and explain why.
- Keep runtime artifacts in `reading-companion-backend/` unless a task explicitly migrates them.
- Do not remove the frontend repo's Figma Make history or generated structure unless the change has a clear maintenance benefit.

## Documentation Layers
### Control Layer
- Root `AGENTS.md`: workspace rules, reading order, and document routing
- Child `AGENTS.md`: subproject-local engineering constraints
- Root `README.md`: setup, run commands, env vars, local URLs, and verification commands

### Agent-Memory Layer
- `docs/source-of-truth-map.md`: canonical storage map for durable project information and validation commands
- `docs/current-state.md`: canonical repo-local current objective, active tasks/jobs, blockers, and recommended reading path
- `docs/tasks/registry.md` and `docs/tasks/registry.json`: canonical workspace task router, traceability index, and evidence links

### Stable Facts Layer
- `docs/workspace-overview.md`: workspace structure, ownership boundaries, and shared entrypoints
- `docs/product-overview.md`: product essence, value channels, guardrails, and canonical-vs-emerging territory
- `docs/product-interaction-model.md`: canonical product journey, page responsibilities, and interaction rules
- `docs/api-contract.md`: public routes, fields, enums, IDs, and stable envelopes
- `docs/api-integration.md`: active endpoint surface, polling/WebSocket coordination, and runtime data flow
- `docs/runtime-modes.md`: startup, supervision, healthchecks, deployment entrypoints, and resume rules
- `docs/language-governance.md`: visible-text governance, terminology ownership, and locale policy
- `docs/frontend-visual-system.md`: frontend typography system, reader-scale boundaries, and core visual tokens
- `docs/backend-sequential-lifecycle.md`: sequential deep-reading job lifecycle, entrypoints, and runtime-state semantics
- `docs/backend-reading-mechanism.md`: shared backend mechanism-platform boundaries, statuses, and doc routing
- `docs/backend-reading-mechanisms/README.md`: backend mechanism catalog, statuses, and authoring rules
- `docs/backend-reading-mechanisms/<mechanism>.md`: mechanism-specific ontology, loop, prompt/context packaging, memory, and private artifacts
- `docs/backend-reader-evaluation.md`: reader quality goals, evaluation layers, and offline evaluation methodology
- `docs/backend-state-aggregation.md`: backend artifact aggregation, public state surfaces, and normalization boundary

### History Layer
- `docs/history/README.md`: retention rules for non-authoritative design and evolution history
- `docs/history/decision-log.md`: key decisions, rejected alternatives, and major design inflection points

### Temporary Working Layer
- `docs/agent-handoff.md`: session-only scratch notes that have not yet been canonicalized elsewhere
- `docs/agent-handoff.md` is a session-only scratchpad, not a source-of-truth doc. Promote durable current-state information into `docs/current-state.md` or `docs/tasks/registry.*`.

### Archive / Reference Layer
- `reading-companion-backend/docs/research/`: historical analysis and planning notes
- `reading-companion-backend/docs/evaluation/`: prompt and output evaluation reports
- `reading-companion-frontend/ATTRIBUTIONS.md`: license and attribution reference

## Load Matrix
### Always Load
- Root `AGENTS.md`
- Root `README.md`
- `docs/current-state.md`
- Relevant child `AGENTS.md`
- `docs/tasks/registry.md`

### Task-Gated Stable Docs
- canonical storage/update location for durable information: `docs/source-of-truth-map.md`
- workspace ownership, file placement, shared entrypoints: `docs/workspace-overview.md`
- product essence, value channels, and canonical-vs-emerging territory: `docs/product-overview.md`
- product flow, canonical routes, page responsibilities: `docs/product-interaction-model.md`
- public API fields, enums, IDs, stable payloads: `docs/api-contract.md`
- current frontend-used endpoints, polling, WebSocket wiring: `docs/api-integration.md`
- startup commands, runtime supervision, deployment, resume rules: `docs/runtime-modes.md`
- UI copy, locale policy, governed terminology: `docs/language-governance.md`
- frontend typography, reader-scale boundaries, and visual token usage: `docs/frontend-visual-system.md`
- backend sequential workflow, job lifecycle, resume behavior: `docs/backend-sequential-lifecycle.md`
- backend mechanism-platform boundaries, statuses, and doc routing: `docs/backend-reading-mechanism.md`
- backend mechanism catalog and authoring rules: `docs/backend-reading-mechanisms/README.md`
- backend mechanism-specific internals such as the current default reader: `docs/backend-reading-mechanisms/<mechanism>.md`
- backend reader quality goals, evaluation layers, and offline eval methodology: `docs/backend-reader-evaluation.md`
- backend artifact aggregation, state surfaces, normalization boundary: `docs/backend-state-aggregation.md`

### History Tasks
- design evolution, rejected alternatives, key decision history: `docs/history/README.md`

### Temporary Only
- `docs/agent-handoff.md`: read only for session scratch notes that have not yet been promoted into canonical current-state/task files

### Archive / Reference Only
- `reading-companion-backend/docs/research/`
- `reading-companion-backend/docs/evaluation/`
- `reading-companion-frontend/ATTRIBUTIONS.md`

## Task Routing
- canonical storage/update location for durable information -> `docs/source-of-truth-map.md`
- current project status, active jobs, blockers, recommended reading path -> `docs/current-state.md`
- workspace task routing, blockers, decision refs, evidence refs -> `docs/tasks/registry.md`, `docs/tasks/registry.json`
- workspace ownership boundaries or shared entrypoints -> `docs/workspace-overview.md`
- product essence, value channels, guardrails, canonical-now vs emerging territory -> `docs/product-overview.md`
- product journey, page responsibilities, canonical user path -> `docs/product-interaction-model.md`
- public routes, fields, enums, IDs, compatibility mappings -> `docs/api-contract.md`
- runtime wiring, long-task coordination, polling/WebSocket behavior -> `docs/api-integration.md`
- setup, env vars, local URLs, verification commands -> `README.md`
- startup mode semantics, healthchecks, deploy entrypoints, resume behavior -> `docs/runtime-modes.md`
- visible text, locale boundaries, governed terminology -> `docs/language-governance.md`
- frontend typography, visual tokens, reader-scale boundaries, and landing exceptions -> `docs/frontend-visual-system.md`
- backend sequential workflow, job lifecycle, start/resume semantics -> `docs/backend-sequential-lifecycle.md`
- backend shared mechanism platform, statuses, and routing -> `docs/backend-reading-mechanism.md`
- backend mechanism catalog or authoring rules -> `docs/backend-reading-mechanisms/README.md`
- backend one-mechanism internals such as ontology, reading loop, prompt assembly, or memory -> `docs/backend-reading-mechanisms/<mechanism>.md`
- backend reader quality goals, evaluation methodology, LLM-as-judge usage, and local-vs-broad eval planning -> `docs/backend-reader-evaluation.md`
- backend artifact aggregation, analysis-state sourcing, normalization boundary -> `docs/backend-state-aggregation.md`
- session-only scratch notes that have not yet been promoted -> `docs/agent-handoff.md`
- design evolution, rejected alternatives, key decision history -> `docs/history/README.md`

## Documentation Maintenance
- Update required docs in the same task when a change alters product behavior, runtime behavior, integration behavior, or maintenance expectations.
- Trigger conditions are additive. One change may require updates in more than one document.
- Keep `AGENTS.md` files rule-oriented and concise. Move detailed reference material into stable docs.
- Avoid duplicating detailed guidance across files. Keep one primary source of truth and add short pointers elsewhere when needed.
- If you intentionally leave docs unchanged, you should have a concrete reason, not just "code is self-explanatory."
- `docs/history/` is not a source-of-truth layer. Its entries must trace back to stable docs, code, archived reports, or repeatable evidence.

### Trigger Matrix
- `README.md`
  - install/setup commands
  - startup commands
  - environment variables
  - default local URLs
  - quick-start or operator-facing verification commands
- `docs/source-of-truth-map.md`
  - canonical storage locations for durable project information
  - machine-readable companions for agent switching
  - validation commands for the switching system
  - update triggers for current-state/task history
- `docs/current-state.md`
  - current objective
  - now / next / blocked state
  - active task ids
  - active job ids
  - open decisions
  - recommended reading path
- `docs/tasks/registry.md` and `docs/tasks/registry.json`
  - task ids
  - task status, lane, and priority
  - blockers
  - decision refs and job refs
  - evidence refs and next actions
- `docs/workspace-overview.md`
  - workspace structure
  - backend/frontend ownership boundaries
  - shared entrypoints
  - cross-project collaboration model
- `docs/product-overview.md`
  - product essence
  - value channels
  - product guardrails
  - canonical-now vs emerging product territory
- `docs/product-interaction-model.md`
  - product interaction model
  - primary user journey or page responsibilities
  - canonical product flow such as landing -> upload -> analysis -> book -> chapter -> marks
  - core UX conventions
  - when a temporary or compatibility flow becomes the primary product path, or the reverse
- `docs/api-contract.md`
  - public API fields
  - public enums
  - canonical routes
  - identifier conventions
  - stable response/request schemas
- `docs/api-integration.md`
  - active frontend-used endpoint surface
  - polling or WebSocket coordination
  - runtime data flow between frontend and backend
  - long-task integration assumptions
- `docs/runtime-modes.md`
  - launcher behavior
  - reload/supervision behavior
  - healthcheck behavior
  - deployment entrypoints
  - recovery or resume runtime rules
- `docs/backend-sequential-lifecycle.md`
  - upload -> parse/deferred -> start/resume -> job -> realtime lifecycle
  - job kinds and status progression
  - frontend-facing lifecycle dependencies
  - runtime-mode-specific recovery semantics
- `docs/backend-reading-mechanism.md`
  - shared mechanism-platform boundaries
  - mechanism status model
  - shared-vs-mechanism doc routing
- `docs/backend-reading-mechanisms/README.md`
  - mechanism catalog
  - defaultness / status changes
  - mechanism-doc authoring rules
- `docs/backend-reading-mechanisms/<mechanism>.md`
  - one mechanism's ontology
  - one mechanism's reading loop
  - one mechanism's prompt/context packaging
  - one mechanism's memory and private artifacts
- `docs/backend-reader-evaluation.md`
  - reader quality dimensions
  - local mechanism eval vs broader regression eval
  - offline LLM-as-judge methodology
  - evaluation artifact routing
- `docs/backend-state-aggregation.md`
  - source artifacts used by backend views
  - how bookshelf, detail, chapter, marks, and analysis-state are assembled
  - endpoint-level shaping vs aggregation responsibilities
  - internal-to-public normalization boundary
- `docs/language-governance.md`
  - visible-text governance
  - terminology ownership
  - locale rules
  - controlled copy sourcing
- `docs/frontend-visual-system.md`
  - frontend typography ramp
  - reader content vs UI typography boundaries
  - core visual token usage
  - landing-page visual exceptions
- `docs/agent-handoff.md`
  - current focus
  - migration status
  - temporary warnings
  - active risks
  - project context that is useful now but not yet a stable rule
- `docs/history/decision-log.md`
  - major architecture or product decisions
  - rejected alternatives worth remembering
  - design reversals and inflection points
- root `AGENTS.md`
  - document layering
  - load matrix
  - cross-project collaboration rules
  - reading order for new agent tasks
- child `AGENTS.md`
  - subproject-local and long-lived engineering constraints
  - implementation boundaries
  - recurring pitfalls that should become stable rules

### Cross-Doc Rules
- If product purpose, value framing, or canonical-vs-emerging product territory changes, update `docs/product-overview.md` in the same task.
- If the same product-purpose change also affects journey framing or reader-quality evaluation, update `docs/product-interaction-model.md` and `docs/backend-reader-evaluation.md` in the same task.
- If the product interaction flow changes and that also changes routes or public payloads, update `docs/product-interaction-model.md`, `docs/api-contract.md`, and `docs/api-integration.md` in the same task.
- If the same change also shifts workspace ownership boundaries or the recommended reading order for agents, update `docs/workspace-overview.md` and root `AGENTS.md`.
- If a backend change materially alters the sequential deep-reading job lifecycle, upload/start/resume semantics, or runtime recovery behavior, update `docs/backend-sequential-lifecycle.md` in the same task.
- If a backend change materially alters shared mechanism boundaries, mechanism status routing, or which docs own mechanism internals, update `docs/backend-reading-mechanism.md` in the same task.
- If a backend change materially alters one mechanism's ontology, reading loop, prompt assembly, memory model, or private artifacts, update `docs/backend-reading-mechanisms/<mechanism>.md` in the same task.
- If a backend change adds a mechanism, archives one, or changes which mechanism is default, update `docs/backend-reading-mechanisms/README.md` in the same task.
- If a backend change changes which mechanism is default, update `docs/backend-reading-mechanism.md`, `docs/workspace-overview.md`, `docs/backend-sequential-lifecycle.md`, `docs/backend-state-aggregation.md`, `reading-companion-backend/AGENTS.md`, and `docs/history/decision-log.md` in the same task.
- If a backend change materially alters reader-quality dimensions, evaluation workflow, offline judge usage, or evaluation artifact routing, update `docs/backend-reader-evaluation.md` in the same task.
- If a meaningful evaluation/comparison or repair pass reveals portable design strengths, causal drivers, or repeatable failure patterns, update the relevant evaluation docs in the same task.
  - keep the stable requirement in `docs/backend-reader-evaluation.md`
  - keep the living implementation record in `docs/implementation/new-reading-mechanism/mechanism-pattern-ledger.md`
  - if the finding changes project direction or would be hard to reconstruct later, also update `docs/history/decision-log.md`
- If the same evaluation/comparison pass produces meaningful findings, do not end the task at documentation alone.
  - investigate what specifically contributed to the result
  - convert high-confidence findings into selective implementation actions or explicit defer reasons
  - avoid letting the ledger become a passive pile of unworked insights
- When reporting a meaningful evaluation/comparison result back to the user, include the selective improvement strategy by default unless the user explicitly asks for result interpretation only.
- When carrying strengths forward from one mechanism into another, preserve the currently approved mechanism's overall framework unless the task explicitly changes that framework.
  - prefer selective adoption over mechanical feature merging
  - defer or reject locally appealing behaviors that do not fit the approved mechanism's control shape, ontology, or memory model
- If a backend change materially alters which artifacts feed public state surfaces, or where normalization between internal and public shapes happens, update `docs/backend-state-aggregation.md` in the same task.
- If a major project change creates a decision, reversal, or design inflection point that would be hard to reconstruct later, update `docs/history/decision-log.md` in the same task.
- Treat a change as decision-bearing when it introduces a new primary mechanism, changes the default product/runtime direction, establishes a new canonical control surface or route model, or promotes a stable doc to subsystem authority.
- If active task status, blockers, active jobs, or the recommended next move change, update `docs/current-state.md` and `docs/tasks/registry.*` in the same task.
- If a temporary handoff note contains durable current-state information, promote it into `docs/current-state.md` or `docs/tasks/registry.*` before closing the task.
- If a new key document becomes part of the standard reading path, add it to the load matrix here before linking it elsewhere.

### History Maintenance Rules
- Default engineering tasks do not need to load `docs/history/`.
- Load `docs/history/README.md` when the task is about design evolution, decision history, or rejected alternatives.
- Update `docs/history/decision-log.md` only when a major decision, reversal, or design inflection point would otherwise be forgotten.
- If a decision-bearing change does not update `docs/history/decision-log.md`, the task close-out should name the concrete reason.
- The repo may emit a warning-only reminder when high-signal design docs change without a matching `decision-log.md` update.
- If `docs/history/` is not updated after a major design change, you should have a concrete reason, such as:
  - the change is fully recoverable later from stable docs and code
  - it is a narrow bugfix or implementation detail
  - it does not represent a real change in direction

## First Files To Read
- `AGENTS.md`
- `README.md`
- `docs/current-state.md`
- the relevant child `AGENTS.md`
- `docs/tasks/registry.md`
- `docs/product-overview.md` when the task touches product purpose, experience framing, or current-vs-emerging product territory
- `docs/source-of-truth-map.md` when the task is about where durable information should live
- `reading-companion-backend/AGENTS.md` when the task touches backend code, prompts, runtime, or API shaping
- `reading-companion-frontend/AGENTS.md` when the task touches frontend routes, API adapters, UI copy, or generated structure
- `docs/backend-reading-mechanism.md` when the task touches shared backend mechanism boundaries or mechanism doc routing
- `docs/backend-reading-mechanisms/iterator_v1.md` when the task touches the current live/default reader internals
- Then load only the task-gated stable doc that matches the work at hand

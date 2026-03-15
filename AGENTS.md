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
- Keep runtime artifacts in `reading-companion-backend/` unless a task explicitly migrates them.
- Do not remove the frontend repo's Figma Make history or generated structure unless the change has a clear maintenance benefit.

## Documentation Layers
### Control Layer
- Root `AGENTS.md`: workspace rules, reading order, and document routing
- Child `AGENTS.md`: subproject-local engineering constraints
- Root `README.md`: setup, run commands, env vars, local URLs, and verification commands

### Stable Facts Layer
- `docs/workspace-overview.md`: workspace structure, ownership boundaries, and shared entrypoints
- `docs/product-interaction-model.md`: canonical product journey, page responsibilities, and interaction rules
- `docs/api-contract.md`: public routes, fields, enums, IDs, and stable envelopes
- `docs/api-integration.md`: active endpoint surface, polling/WebSocket coordination, and runtime data flow
- `docs/runtime-modes.md`: startup, supervision, healthchecks, deployment entrypoints, and resume rules
- `docs/language-governance.md`: visible-text governance, terminology ownership, and locale policy

### Case Study Layer
- `docs/case-study/README.md`: case-study doc map, allowed evidence sources, and writing constraints
- `docs/case-study/overview.md`: one-page project summary for demos and portfolio use
- `docs/case-study/architecture.md`: architecture story, system boundaries, and evolution narrative
- `docs/case-study/decisions.md`: high-value design decisions and trade-offs likely to come up in interviews
- `docs/case-study/evidence.md`: hard evidence index for evals, tests, examples, and quantitative checkpoints
- `docs/case-study/interview-notes.md`: concise interview-ready narratives built from the other case-study docs

### Temporary Working Layer
- `docs/agent-handoff.md`: current focus, active risks, migration status, and temporary warnings
- `docs/agent-handoff.md` is not a source-of-truth doc. Promote repeated guidance into `AGENTS.md` or a stable doc.

### Archive / Reference Layer
- `reading-companion-backend/docs/research/`: historical analysis and planning notes
- `reading-companion-backend/docs/evaluation/`: prompt and output evaluation reports
- `reading-companion-frontend/ATTRIBUTIONS.md`: license and attribution reference

## Load Matrix
### Always Load
- Root `AGENTS.md`
- Relevant child `AGENTS.md`
- Root `README.md`

### Task-Gated Stable Docs
- workspace ownership, file placement, shared entrypoints: `docs/workspace-overview.md`
- product flow, canonical routes, page responsibilities: `docs/product-interaction-model.md`
- public API fields, enums, IDs, stable payloads: `docs/api-contract.md`
- current frontend-used endpoints, polling, WebSocket wiring: `docs/api-integration.md`
- startup commands, runtime supervision, deployment, resume rules: `docs/runtime-modes.md`
- UI copy, locale policy, governed terminology: `docs/language-governance.md`

### Career / Case-Study Tasks
- portfolio packaging, interview prep, demo storytelling, technical summaries: `docs/case-study/README.md`

### Temporary Only
- `docs/agent-handoff.md`: read only when the task needs current focus, open risks, or active migration notes

### Archive / Reference Only
- `reading-companion-backend/docs/research/`
- `reading-companion-backend/docs/evaluation/`
- `reading-companion-frontend/ATTRIBUTIONS.md`

## Task Routing
- workspace ownership boundaries or shared entrypoints -> `docs/workspace-overview.md`
- product journey, page responsibilities, canonical user path -> `docs/product-interaction-model.md`
- public routes, fields, enums, IDs, compatibility mappings -> `docs/api-contract.md`
- runtime wiring, long-task coordination, polling/WebSocket behavior -> `docs/api-integration.md`
- setup, env vars, local URLs, verification commands -> `README.md`
- startup mode semantics, healthchecks, deploy entrypoints, resume behavior -> `docs/runtime-modes.md`
- visible text, locale boundaries, governed terminology -> `docs/language-governance.md`
- current focus, temporary risks, active migration notes -> `docs/agent-handoff.md`
- portfolio packaging, interview prep, demo storytelling, technical summaries -> `docs/case-study/README.md`

## Documentation Maintenance
- Update required docs in the same task when a change alters product behavior, runtime behavior, integration behavior, or maintenance expectations.
- Trigger conditions are additive. One change may require updates in more than one document.
- Keep `AGENTS.md` files rule-oriented and concise. Move detailed reference material into stable docs.
- Avoid duplicating detailed guidance across files. Keep one primary source of truth and add short pointers elsewhere when needed.
- If you intentionally leave docs unchanged, you should have a concrete reason, not just "code is self-explanatory."
- `docs/case-study/` is not a source-of-truth layer. Its facts must trace back to stable docs, code, tests, evaluation reports, or repeatable command output.

### Trigger Matrix
- `README.md`
  - install/setup commands
  - startup commands
  - environment variables
  - default local URLs
  - quick-start or operator-facing verification commands
- `docs/workspace-overview.md`
  - workspace structure
  - backend/frontend ownership boundaries
  - shared entrypoints
  - cross-project collaboration model
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
- `docs/language-governance.md`
  - visible-text governance
  - terminology ownership
  - locale rules
  - controlled copy sourcing
- `docs/agent-handoff.md`
  - current focus
  - migration status
  - temporary warnings
  - active risks
  - project context that is useful now but not yet a stable rule
- `docs/case-study/overview.md`
  - core product positioning for demos
  - primary user path summary for external presentation
  - project completion or showcase status
  - top showcase points or demo framing
- `docs/case-study/architecture.md`
  - architecture story
  - system boundaries
  - main-path module map
  - runtime/recovery story
  - prototype-to-main-path evolution
- `docs/case-study/decisions.md`
  - high-value architecture or product trade-offs
  - superseded decisions that matter for interview discussion
  - non-obvious choices likely to be questioned in interviews
- `docs/case-study/evidence.md`
  - evaluation report references
  - before/after comparisons
  - tests, validation commands, and quantitative checkpoints worth citing
  - example outputs and demos worth showing
- `docs/case-study/interview-notes.md`
  - interview talk tracks
  - STAR stories
  - frequent follow-up questions
  - concise positioning statements for recruiting contexts
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
- If the product interaction flow changes and that also changes routes or public payloads, update `docs/product-interaction-model.md`, `docs/api-contract.md`, and `docs/api-integration.md` in the same task.
- If the same change also shifts workspace ownership boundaries or the recommended reading order for agents, update `docs/workspace-overview.md` and root `AGENTS.md`.
- If a major project change alters demo framing, interview positioning, high-value trade-offs, or showcase evidence, update the affected files under `docs/case-study/` in the same task.
- If a task adds or replaces quantitative evaluation evidence, update `docs/case-study/evidence.md` instead of relying on memory or chat-only notes.
- If a temporary handoff note repeats across tasks, promote it into the relevant `AGENTS.md` or stable doc.
- If a new key document becomes part of the standard reading path, add it to the load matrix here before linking it elsewhere.

### Case-Study Maintenance Rules
- Default engineering tasks do not need to load `docs/case-study/`.
- Tasks about portfolio packaging, interview prep, demo storytelling, technical summaries, or project highlight extraction must load `docs/case-study/README.md` and maintain the relevant files.
- Even when a task is not explicitly about job-search materials, update the relevant `docs/case-study/` file if the task makes a major change to:
  - the primary product path or top showcase value
  - the main architecture or ownership boundaries
  - a decision likely to be explained in interviews
  - available hard evidence such as evals, validation runs, or output comparisons
- If `docs/case-study/` is not updated after a major change, you should have a concrete reason, such as:
  - it is a narrow bugfix
  - it does not change the project story, evidence, or meaningful trade-offs
  - it does not materially affect later interview preparation

## First Files To Read
- `AGENTS.md`
- `README.md`
- `reading-companion-backend/AGENTS.md` when the task touches backend code, prompts, runtime, or API shaping
- `reading-companion-frontend/AGENTS.md` when the task touches frontend routes, API adapters, UI copy, or generated structure
- Then load only the task-gated stable doc that matches the work at hand

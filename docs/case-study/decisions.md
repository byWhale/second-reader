# Case Study Decisions

Purpose: record the highest-value design decisions and trade-offs that are likely to be discussed in interviews.
Use when: preparing to explain why the project works this way instead of another way.
Not for: routine change logs, bugfix notes, or source-of-truth engineering definitions.
Update when: a major architecture or product decision is added, replaced, or becomes interview-relevant.

## Decision 1
**Decision**: Treat `sequential` deep reading as the primary product and engineering path.

**Context**: The repo contains evidence of broader or more prototype-style agent paths, but the product needs a dependable main loop.

**Alternatives considered**: Keep a more generalized graph-first architecture as the default path.

**Why chosen**: A single main path makes the product easier to run, validate, explain, and recover.

**Trade-offs**: It narrows the default architecture and makes more experimental capabilities secondary.

**Evidence**: `docs/product-interaction-model.md`, `docs/runtime-modes.md`, `reading-companion-backend/AGENTS.md`

## Decision 2
**Decision**: Keep public naming, route, and ID normalization at the API layer.

**Context**: Internal runtime artifacts and older compatibility shapes do not always match the web-facing contract.

**Alternatives considered**: Push normalization logic into the frontend or require internal runtime storage to mirror the public API exactly.

**Why chosen**: The API layer is the cleanest place to preserve a stable web contract while allowing internal implementation evolution.

**Trade-offs**: The backend carries some compatibility and translation complexity.

**Evidence**: `docs/api-contract.md`, `docs/api-integration.md`

## Decision 3
**Decision**: Keep the frontend contract-driven with centralized routes and a thin API adapter.

**Context**: The frontend needs to stay aligned with backend-returned route targets and generated API types.

**Alternatives considered**: Let page components issue ad-hoc fetch calls and own more normalization locally.

**Why chosen**: Centralization reduces contract drift and makes route behavior easier to validate.

**Trade-offs**: The API adapter becomes a critical integration layer that must stay clean.

**Evidence**: `reading-companion-frontend/AGENTS.md`, `docs/api-contract.md`, `docs/workspace-overview.md`

## Decision 4
**Decision**: Treat resume and runtime recovery as first-class product behavior.

**Context**: Long-running reading jobs can stall, restart, or cross process boundaries.

**Alternatives considered**: Treat failures as disposable runs and rely on manual reruns.

**Why chosen**: A book-length analysis flow is easier to trust and demo when progress state and recovery are part of the design.

**Trade-offs**: Runtime semantics, compatibility versioning, and stale-run handling become part of system complexity.

**Evidence**: `docs/runtime-modes.md`, `docs/api-contract.md`

## Decision 5
**Decision**: Preserve evaluation artifacts as evidence, but keep them outside the default development context.

**Context**: Quality and prompt claims are stronger when backed by explicit comparison artifacts, but those files are noisy for everyday implementation work.

**Alternatives considered**: Delete evaluation materials entirely or keep them mixed into day-to-day docs.

**Why chosen**: The project benefits from hard evidence without paying the cost of loading those reports into every engineering task.

**Trade-offs**: Evidence has to be intentionally maintained and indexed rather than discovered incidentally.

**Evidence**: `reading-companion-backend/docs/README.md`, `reading-companion-backend/docs/evaluation/`

# Decision Log

Purpose: preserve design evolution, key decisions, and rejected alternatives that would be difficult to reconstruct later from current-state docs alone.
Use when: tracing why the project converged on its current shape or recording a major change in direction.
Not for: routine change logs, source-of-truth engineering definitions, or interview-ready wording.
Update when: a major product or engineering decision is made, reversed, or becomes historically important to future contributors.

## Entry 1
**Decision / Inflection**: Converge on `sequential` as the primary product and engineering path.

**Period**: Early workspace baseline through the March 2026 cleanup period.

**Problem**: The repository still contained broader, more experimental reading paths, but the product needed one dependable loop that could be run, recovered, validated, and explained without splitting attention across competing architectures.

**Alternatives considered**: Keep a more generalized graph-first direction as the main path, or let `book_analysis`-style capabilities define the default product story.

**Why this path won**: A single sequential path created a cleaner basis for runtime recovery, frontend integration, and later documentation. It also made the product easier to demo as a coherent reading experience instead of a bundle of agent experiments.

**What changed in the system**: Product and backend rules now explicitly treat `sequential` as primary, while `book_analysis` remains secondary and non-authoritative for default decisions.

**Why it matters later**: This is the clearest example of the project choosing focus over maximal flexibility. Without recording it, later readers would see the remaining experimental traces but miss why the main path narrowed.

**Primary evidence**:
- `5d5c7b2` `Remove high-signal logic`
- `reading-companion-backend/AGENTS.md`
- `docs/product-interaction-model.md`

## Entry 2
**Decision / Inflection**: Shape the current long-task model around upload, deferred parse, and explicit `analysis/start` / `analysis/resume`.

**Period**: March 2026, especially the book-overview consolidation work.

**Problem**: The system needed a user-facing flow that could handle both "start immediately" and "prepare structure first" without splitting the product into separate tools or one-off routes.

**Alternatives considered**: Make upload always start full analysis immediately, keep parsing and deep reading as more disconnected workflows, or hide continuation behind internal-only recovery behavior.

**Why this path won**: The upload -> deferred parse -> explicit start/resume model made the book overview a real control surface. It gave the product a stable way to present structure readiness, continue actions, and long-running progress in one place.

**What changed in the system**: Upload provisioning, book overview state, and long-task orchestration converged on the current `POST /api/uploads/epub`, `analysis/start`, and `analysis/resume` model, with a clearer `ready` state between parse and deep reading.

**Why it matters later**: This is one of the core product-shaping decisions. It explains why the overview page is not just a result screen, but the operational center for a book.

**Primary evidence**:
- `3657e9e` `统一 Book overview 单页布局`
- `docs/product-interaction-model.md`
- `docs/backend-sequential-lifecycle.md`

## Entry 3
**Decision / Inflection**: Treat runtime recovery, checkpointing, and resume as product behavior rather than hidden operations.

**Period**: March 2026, first with stable runtime work and then with minimal resume recovery.

**Problem**: Book-length reading jobs can stall, restart, or cross process boundaries. A "just rerun it" model would have made the experience fragile and hard to trust.

**Alternatives considered**: Accept frequent reruns, keep recovery mostly invisible to the product layer, or handle failures manually as operator-only concerns.

**Why this path won**: For long-running reading, trust depends on visible continuity. Recovery had to show up in public state, user-facing controls, and documented runtime semantics.

**What changed in the system**: The backend gained explicit checkpoint-aware resume behavior, demo/prod runtime guardrails, paused states, recovery events, and surfaced fields like `resume_available` and `last_checkpoint_at`.

**Why it matters later**: This inflection marks the moment the project stopped behaving like a fragile background script and started behaving like a recoverable product system.

**Primary evidence**:
- `554fe5a` `Implement Railway health and demo`
- `d2650be` `Implement minimal resume recovery`
- `docs/runtime-modes.md`
- `docs/backend-sequential-lifecycle.md`

## Entry 4
**Decision / Inflection**: Make the API layer the normalization boundary for public routes, IDs, and taxonomy.

**Period**: Early March 2026 contract hardening.

**Problem**: Internal runtime artifacts, compatibility routes, and legacy taxonomy values did not line up cleanly with the frontend-facing contract.

**Alternatives considered**: Push normalization into the frontend, or require internal artifacts to match the public contract exactly before any response could be emitted.

**Why this path won**: The API layer was the narrowest place to preserve a stable external contract while allowing runtime artifacts and migration steps to evolve more gradually.

**What changed in the system**: OpenAPI snapshots, contract tests, generated frontend types, and API mapping logic were tightened so the public contract became explicit and checkable instead of implicit.

**Why it matters later**: This explains why current handlers and helpers still translate internal ids, routes, and taxonomy values instead of assuming the runtime storage format is already public-ready.

**Primary evidence**:
- `8ff9b14` `Align API contract documentation`
- `c3f39c6` `加强 API 合约校验步骤化执行方案`
- `docs/api-contract.md`
- `reading-companion-backend/src/api/contract.py`

## Entry 5
**Decision / Inflection**: Productize Reading Mindstream so "the reader is thinking now" becomes part of the main experience.

**Period**: March 2026.

**Problem**: The project needed to preserve the feeling of an active co-reader instead of flattening the experience into static results and generic summaries.

**Alternatives considered**: Keep progress updates mostly mechanical, leave the live reading trace in low-visibility backend artifacts, or center the UX on finished outputs only.

**Why this path won**: Surfacing the live reading trace made the system feel like an ongoing reading process rather than a delayed report generator. It also reinforced the product promise that the AI is reading with the user, not only after the fact.

**What changed in the system**: Realtime payloads, overview rendering, and runtime language were reshaped around live activity, pulse messages, and the current-reading snapshot.

**Why it matters later**: This is one of the clearest product differentiators. It records why the app now has a visible "mindstream" instead of a purely task-centric progress widget.

**Primary evidence**:
- `fa5157e` `Implement Reading Mindstream plan`
- `docs/product-interaction-model.md`
- `docs/api-integration.md`
- `reading-companion-backend/src/api/realtime.py`

## Entry 6
**Decision / Inflection**: Converge frontend routes and the book overview into the canonical control surface.

**Period**: March 2026, especially around the overview unification and chapter drawer work.

**Problem**: The product needed a more coherent route story and fewer split entrypoints between upload, analysis, overview, and chapter consumption.

**Alternatives considered**: Keep multiple parallel overview-like pages, continue relying on compatibility routes, or let upload and analysis live as more isolated screens.

**Why this path won**: Pulling state, controls, and chapter navigation into the book overview made the frontend easier to understand and better aligned with the long-task model.

**What changed in the system**: Canonical routes and overview responsibilities tightened around `/books`, `/books/:id`, and `/books/:id/chapters/:chapterId`, while compatibility routes became secondary.

**Why it matters later**: This explains why the current route model looks intentional rather than accidental, and why the overview page carries so much operational responsibility.

**Primary evidence**:
- `3657e9e` `统一 Book overview 单页布局`
- `63ccadf` `Add chapter drawer navigation`
- `docs/product-interaction-model.md`
- `reading-companion-frontend/src/app/routes.tsx`

## Entry 7
**Decision / Inflection**: Stabilize local demo and deployment runtime instead of treating development mode as the only supported way to run.

**Period**: March 2026.

**Problem**: Hot-reload development mode was not a good fit for demos or deployment-like reliability, and the project needed an operator story beyond "run the dev server and hope it stays up."

**Alternatives considered**: Continue using dev mode everywhere, rely on ad hoc manual restarts, or leave deployment/runtime expectations implicit in scripts.

**Why this path won**: Introducing explicit demo/stable runtime modes created a cleaner separation between coding ergonomics and presentation or deployment reliability.

**What changed in the system**: Healthcheck behavior, Railway entrypoints, stable backend launchers, and demo supervision became documented and script-backed parts of the workspace.

**Why it matters later**: This records the point where the project started behaving like a presentable, operable app rather than a dev-only sandbox.

**Primary evidence**:
- `554fe5a` `Implement Railway health and demo`
- `docs/runtime-modes.md`
- `railway.json`
- `scripts/run-backend-stable.sh`

## Entry 8
**Decision / Inflection**: Split documentation into stable facts, temporary handoff, archive material, and history instead of keeping mixed-purpose notes.

**Period**: Mid-March 2026.

**Problem**: Rules, current state, research notes, and archival material had started to bleed into one another, which made both agent context and human reading noisier.

**Alternatives considered**: Keep a flatter docs layout, continue using one-off handoff notes as semi-authoritative references, or leave research/evaluation materials mixed into regular reading paths.

**Why this path won**: A layered docs system reduced context pollution and made it clearer which documents define current behavior versus which ones preserve historical or reference-only material.

**What changed in the system**: Workspace docs were reorganized into control, stable facts, temporary working notes, archive/reference material, and now explicit engineering history.

**Why it matters later**: This entry explains why the repo now has separate stable docs and history docs, and why some old notes were intentionally demoted rather than deleted.

**Primary evidence**:
- `b7adf3d` `Redesign AGENTS documentation plan`
- `0b01400` `Reorganize docs hierarchy`
- `231c396` `Remove case study docs`
- `AGENTS.md`

## Entry 9
**Decision / Inflection**: Introduce a frontend visual-system document and separate core UI typography from reader-content scaling.

**Period**: Mid-March 2026.

**Problem**: The frontend already had a recognizable visual language, but typography rules were still scattered across page-local inline styles. At the same time, the chapter reading workspace needed a clear answer to which text should respect user-controlled reading scale and which text should remain fixed application chrome.

**Alternatives considered**: Keep page-local typography decisions implicit, force every page including landing into one typography system immediately, or let reader scale continue affecting both content and chrome without a documented boundary.

**Why this path won**: A documented visual system created a stable way to align the core application without erasing intentional special cases like the landing page. Separating UI typography from reader-content typography also preserved adjustable reading comfort without turning navigation and controls into moving targets.

**What changed in the system**: The workspace gained a stable frontend visual-system document, new theme tokens for core typography roles, and explicit reader-scale boundaries that distinguish scalable reading content from fixed application chrome.

**Why it matters later**: This is the point where typography stopped being a page-by-page implementation detail and became an explicit frontend system. Future contributors will need this context to understand why landing remains a controlled exception and why reader-scale logic is intentionally narrower than "all text in the chapter page."

**Primary evidence**:
- `docs/frontend-visual-system.md`
- `AGENTS.md`
- `reading-companion-frontend/AGENTS.md`
- `reading-companion-frontend/src/styles/theme.css`

## Entry 10
**Decision / Inflection**: Move runtime subsegment selection from heuristic-first slicing to LLM-primary planning with deterministic validation and heuristic fallback.

**Period**: Mid-March 2026.

**Problem**: The reader's smallest runtime work unit directly shapes what the model can notice, question, and say. The earlier slicing path was useful as an engineering guardrail, but it still optimized mainly for length and density control instead of for the smallest self-contained local reading move.

**Alternatives considered**: Keep the previous length/density-driven heuristic as the main selector, hard-code a richer rule engine for discourse boundaries, or add a more elaborate multi-model arbitration layer for only a few difficult sections.

**Why this path won**: An LLM-primary planner better matches the product goal of a thoughtful co-reader because subsegment choice is fundamentally a semantic judgment, not only a sizing problem. Keeping deterministic validation plus the existing sentence-boundary heuristic as fallback preserved runtime safety without letting safety logic define the semantic target.

**What changed in the system**: Multi-sentence sections now go through a planner prompt that proposes the fewest self-contained runtime units needed for one local nonfiction reading move at a time. The runtime validates full sentence coverage, ordering, reading-move labels, per-unit hard token caps, and the safety cap before materializing the plan. If any of those checks fail, the reader falls back to the older heuristic slicer. The default `slice_max_subsegments` cap was also widened and reframed as a safety guard rather than a semantic objective.

**Why it matters later**: This is a reader-core design shift, not a routine tuning pass. Future contributors will otherwise see both the planner and the fallback code paths but miss why the project stopped treating heuristic chunking as the primary definition of the attention unit.

**Primary evidence**:
- `docs/backend-reading-mechanism.md`
- `reading-companion-backend/src/iterator_reader/reader.py`
- `reading-companion-backend/src/prompts/templates.py`
- `reading-companion-backend/src/iterator_reader/policy.py`

## Entry 11
**Decision / Inflection**: Freeze the evaluation frame as product-first and mechanism-agnostic.

**Period**: March 2026, after the first stable subsegment benchmark baselines and benchmark taxonomy cleanup.

**Problem**: The project needed a durable way to judge reader quality without assuming that the current `section` / `subsegment` pipeline was the final architecture. Without that frame, later mechanism changes could be debated as implementation preference instead of product evidence.

**Alternatives considered**: Keep evaluation centered on the existing slicing pipeline, treat benchmark reports as the only meaningful authority, or delay a stable methodology until a future architecture change forced one.

**Why this path won**: A product-first evaluation constitution makes the reader architecture comparable across implementations. It preserves the existing `target` / `scope` / `method` taxonomy while letting future mechanisms compete on the same north-star criteria instead of on internal shape.

**What changed in the system**: The stable evaluation doc now explicitly treats `section`, `subsegment`, memory packing, search, and future reader designs as evaluable mechanisms rather than protected truths. It also separates stable methodology from evolving benchmark composition and per-run evidence.

**Why it matters later**: This is the point where evaluation becomes the project-level constitution for reader work. Future contributors should be able to ask whether a different mechanism is better without first accepting the current pipeline as canonical.

**Primary evidence**:
- `2187335` `Record runtime-first subsegment benchmark outputs`
- `6738155` `Refine subsegment eval taxonomy and direct-quality benchmark`
- `b18043c` `Add reader evaluation methodology documentation`
- `docs/backend-reader-evaluation.md`
- `reading-companion-backend/eval/subsegment/run_benchmark.py`

## Entry 12
**Decision / Inflection**: Reframe the product purpose around a living co-reader mind rather than a narrower outcome-led promise.

**Period**: March 2026, after the evaluation constitution was stabilized.

**Problem**: The product promise was still dominated by outcome language such as helping readers notice blind spots or unknown unknowns. That language captured part of the value, but it was narrower than the actual product surfaces, which already emphasized live thought, resonance, saved marks, and the feeling of reading alongside an active mind.

**Alternatives considered**: Keep the old purpose centered mainly on user blind-spot discovery, define the product through a fixed closed list of downstream benefits, or broaden the purpose immediately into explicit user-agent dialogue and steering.

**Why this path won**: Centering the product on a genuinely curious co-reading mind preserves what feels special about the experience without locking the product to one narrow benefit channel. It also gives later evaluation and mechanism choices a deeper standard than "did it produce more surprises?" while avoiding premature commitment to a dialogue-first product.

**What changed in the system**: The stable product-purpose language now lives explicitly in `docs/product-interaction-model.md` and defines the product through essence, lived reading experience, and illustrative value channels. The evaluation methodology doc now aligns to that framing instead of competing with it, and explicit user-agent steering remains marked as emerging rather than canonical.

**Why it matters later**: This is the framing shift that lets future reader work optimize for a living reading intelligence rather than for a single visible outcome such as blind-spot discovery. It also explains why resonance, delight, recall, and companionship should be understood as important expressions of the product rather than as competing product identities.

**Primary evidence**:
- `docs/product-interaction-model.md`
- `docs/backend-reader-evaluation.md`
- `reading-companion-frontend/src/app/content/landing-content.ts`
- `reading-companion-frontend/src/app/config/product-lexicon.ts`

## Entry 13
**Decision / Inflection**: Promote product purpose into its own stable authority document and separate it from interaction-flow authority.

**Period**: March 2026, immediately after the living co-reader reframing.

**Problem**: `docs/product-interaction-model.md` had started carrying both the deeper product-purpose framing and the route/page interaction model. That made one document do two jobs at once and blurred the difference between "what this product fundamentally is" and "how the current product is organized on screen."

**Alternatives considered**: Keep product-purpose authority inside the interaction-model doc, duplicate the same product-purpose language across multiple stable docs, or create an overview doc but leave it outside the standard reading path.

**Why this path won**: A dedicated product-overview doc creates a clearer authority chain. It gives the product essence, value channels, and canonical-vs-emerging boundaries one stable home, while letting the interaction-model and evaluation docs align to that purpose without competing with it.

**What changed in the system**: `docs/product-overview.md` now owns product essence and value framing. `docs/product-interaction-model.md` now focuses on journey, routes, page responsibilities, and interaction rules. `docs/backend-reader-evaluation.md` now points to the overview doc as product-purpose authority. Root and child `AGENTS.md` files were updated so the new overview doc is part of the standard reading path.

**Why it matters later**: This split makes future product, design, and evaluation work easier to reason about. Contributors can refine purpose without accidentally rewriting flow rules, and they can refine flow without accidentally redefining the product's core identity.

**Primary evidence**:
- `docs/product-overview.md`
- `docs/product-interaction-model.md`
- `docs/backend-reader-evaluation.md`
- `AGENTS.md`

## Entry 14
**Decision / Inflection**: Make the reader evaluation constitution decision-complete around reader character, reader value, and runtime viability.

**Period**: Late March 2026, after product-purpose authority moved into `docs/product-overview.md`.

**Problem**: The evaluation frame was already product-first and mechanism-agnostic, but it still left important ambiguity about what the north star actually contained, how strong anti-goals should be, and which questions belonged in stable methodology versus in benchmark reports. Without that clarification, future contributors could still overfit evaluation to a flat blended checklist, over-police surprise or resonance, or quietly move benchmark policy into the constitution.

**Alternatives considered**: Keep the earlier north star as a looser blended list, make stronger anti-goals that discouraged surprise or resonance as such, elevate recall and re-entry to first-class north-star territory, or let benchmark reports continue filling in the missing methodology by convention.

**Why this path won**: Splitting the north star into `reader_character` and `reader_value`, with `runtime_viability` as a standing gate, makes the evaluation system clearer without hard-freezing current mechanisms. Narrowing anti-goals to anti-reduction rules preserves room for text-earned surprise, resonance, and delight while still protecting the product from collapsing into proxy optimization. Keeping recall and re-entry as secondary durable-trace audits also keeps the framework aligned with the actual product surfaces instead of forcing extra recap structure into the reader.

**What changed in the system**: `docs/backend-reader-evaluation.md` now defines the stable evaluation constitution around two north-star families plus one runtime gate, reframes evaluation layers as mechanism-agnostic product lenses, makes `pairwise_judge` and `rubric_judge` the default semantic tools, keeps human review optional calibration, and sharpens the boundary between stable methodology and evolving benchmark/report policy.

**Why it matters later**: This is the clarification that makes the evaluation constitution more usable as a day-to-day decision tool instead of only a high-level principle. Future contributors should be able to compare a subsegment-based reader, a non-slicing reader, or a search-heavy reader with the same framework without accidentally turning benchmark details, surprise effects, or recap-oriented audits into the product definition.

**Primary evidence**:
- `docs/backend-reader-evaluation.md`
- `docs/product-overview.md`
- `reading-companion-backend/docs/evaluation/subsegment/subsegment_benchmark_v1_baseline.md`

## Entry 15
**Decision / Inflection**: Introduce a shared backend runtime shell for multiple reader mechanisms while freezing `iterator_reader` as the current default implementation.

**Period**: Late March 2026.

**Problem**: The project now has at least two materially different reader directions in view: the existing `section` / `subsegment` pipeline and newer designs built around different attention and progression logic. Evolving all of that inside `iterator_reader` would either force incompatible mechanisms into one internal ontology or split the backend into ad hoc parallel stacks with duplicated runtime and integration code.

**Alternatives considered**: Keep extending `iterator_reader` as the only backend architecture, build a "universal" internal reader model that every mechanism must conform to, or fork separate end-to-end backends per mechanism.

**Why this path won**: A narrow shared runtime shell preserves one place for jobs, checkpoints, public-state projection, and evaluation wiring, while allowing each reader mechanism to keep its own internal ontology. That keeps future mechanisms comparable without pretending they share the same attention unit, memory shape, or movement logic.

**What changed in the system**: Workspace and backend docs now distinguish backend-wide runtime/mechanism boundaries from the current default `iterator_reader` implementation. The backend direction is now "shared shell plus mechanism-specific readers," with `iterator_reader` retained as the only default/live mechanism during the first scaffold step.

**Why it matters later**: This is the decision that prevents future reader work from becoming either a maze of duplicated orchestration code or a fake abstraction layer that weakens every mechanism. Later contributors need to know that compatibility is expected at the runtime/evaluation boundary, not by forcing identical internal structures.

**Primary evidence**:
- `docs/workspace-overview.md`
- `reading-companion-backend/AGENTS.md`
- `reading-companion-backend/main.py`
- `reading-companion-backend/src/iterator_reader/`

## Entry 16
**Decision / Inflection**: Make `book_document.json` the canonical parsed-book substrate and treat `structure.json` as a current-mechanism derived artifact.

**Period**: Late March 2026, immediately after the first shared runtime/mechanism scaffold landed.

**Problem**: The first runtime scaffold still depended on `iterator_reader.models`, which meant the backend's supposed shared layer was still inheriting the current mechanism's ontology. That would have made future mechanisms compare against `section` / `subsegment` assumptions even when their real reading logic wanted different internal units.

**Alternatives considered**: Keep `BookStructure` as the de facto shared parsed-book model, move every future mechanism onto the same `structure.json` assumptions, or delay the shared substrate split until a second mechanism was already live.

**Why this path won**: Separating the canonical book substrate from current-mechanism traversal state creates a real narrow waist. The backend can now share chapter/paragraph/locator truth, mechanism-neutral runtime contracts, and normalized comparison outputs without pretending that all reader mechanisms share one internal planning shape.

**What changed in the system**: The backend now has `src/reading_core/` for canonical book substrate, runtime contracts, and normalized cross-mechanism output types. Parse flow writes `public/book_document.json` first, then `iterator_v1` derives `public/structure.json` from that substrate. Shared runtime, library, and search modules now import neutral types from `reading_core` instead of from `iterator_reader.models`.

**Why it matters later**: This is the design boundary that should let future readers differ radically in internal ontology while still sharing the same runtime shell and evaluation seam. Later contributors need to know that `structure.json` is not the universal parsed-book truth anymore, even if the current public surfaces still consult it for iterator-shaped section views.

**Primary evidence**:
- `reading-companion-backend/src/reading_core/`
- `reading-companion-backend/src/reading_runtime/`
- `reading-companion-backend/src/iterator_reader/parse.py`
- `docs/backend-state-aggregation.md`

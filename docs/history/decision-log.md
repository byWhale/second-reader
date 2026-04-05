# Decision Log

Purpose: preserve design evolution, key decisions, and rejected alternatives that would be difficult to reconstruct later from current-state docs alone.
Use when: tracing why the project converged on its current shape or recording a major change in direction.
Not for: routine change logs, source-of-truth engineering definitions, or interview-ready wording.
Update when: a major product or engineering decision is made, reversed, or becomes historically important to future contributors.

## Entry 1
**ID**: DEC-001
**Status**: superseded by `DEC-039`

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
**ID**: DEC-002
**Status**: active

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
**ID**: DEC-003
**Status**: active

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
**ID**: DEC-004
**Status**: active

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
**ID**: DEC-005
**Status**: active

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
**ID**: DEC-006
**Status**: active

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
**ID**: DEC-007
**Status**: active

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
**ID**: DEC-008
**Status**: active

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
**ID**: DEC-009
**Status**: active

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
**ID**: DEC-010
**Status**: active

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
- `reading-companion-backend/src/iterator_reader/prompts.py`
- `reading-companion-backend/src/iterator_reader/policy.py`

## Entry 11
**ID**: DEC-011
**Status**: active

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
**ID**: DEC-012
**Status**: active

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
**ID**: DEC-013
**Status**: active

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
**ID**: DEC-014
**Status**: active

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
**ID**: DEC-015
**Status**: active

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
**ID**: DEC-016
**Status**: active

**Decision / Inflection**: Make `book_document.json` the canonical parsed-book substrate and treat `structure.json` as a current-mechanism derived artifact.

**Period**: Late March 2026, immediately after the first shared runtime/mechanism scaffold landed.

**Problem**: The first runtime scaffold still depended on `iterator_reader.models`, which meant the backend's supposed shared layer was still inheriting the current mechanism's ontology. That would have made future mechanisms compare against `section` / `subsegment` assumptions even when their real reading logic wanted different internal units.

**Alternatives considered**: Keep `BookStructure` as the de facto shared parsed-book model, move every future mechanism onto the same `structure.json` assumptions, or delay the shared substrate split until a second mechanism was already live.

**Why this path won**: Separating the canonical book substrate from current-mechanism traversal state creates a real narrow waist. The backend can now share chapter/paragraph/locator truth, mechanism-neutral runtime contracts, and normalized comparison outputs without pretending that all reader mechanisms share one internal planning shape.

**What changed in the system**: The backend now has `src/reading_core/` for canonical book substrate, runtime contracts, and normalized cross-mechanism output types. Parse flow writes `public/book_document.json` first, then `iterator_v1` derives its own structure artifact from that substrate. Shared runtime, library, and search modules now import neutral types from `reading_core` instead of from `iterator_reader.models`.

**Why it matters later**: This is the design boundary that should let future readers differ radically in internal ontology while still sharing the same runtime shell and evaluation seam. Later contributors need to know that `structure.json` is not the universal parsed-book truth anymore, even if the current public surfaces still consult it for iterator-shaped section views.

**Primary evidence**:
- `reading-companion-backend/src/reading_core/`
- `reading-companion-backend/src/reading_runtime/`
- `reading-companion-backend/src/iterator_reader/parse.py`
- `docs/backend-state-aggregation.md`

## Entry 17
**ID**: DEC-017
**Status**: active

**Decision / Inflection**: Separate transient uploads, durable source-library books, runtime book copies, and evaluation packages into distinct source-asset territories.

**Period**: March 2026, during the first serious `attentional_v2` evaluation-corpus planning pass.

**Problem**: The backend already had user uploads, runtime book copies, local data files, fixtures, and benchmark assets, but they were too easy to blur together conceptually. Without an explicit territory model, future contributors could quietly treat `state/uploads/` as a de facto library, build evaluation corpora from ad hoc runtime files, or lose the difference between one analyzed `book_id` and a durable source-book identity.

**Alternatives considered**: Keep all source books informally under one "backend data" idea, treat runtime book copies as the natural evaluation corpus, or let uploads flow into evaluation use without an explicit promotion boundary.

**Why this path won**: A territory model makes upstream and downstream responsibilities clearer. It preserves the product/runtime upload flow while also giving evaluation work a cleaner, more reproducible path. It also keeps manually curated backend books distinct from transient user uploads without forcing every durable source into the repo.

**What changed in the system**: Stable docs now distinguish:
- `state/uploads/` as transient intake
- per-book runtime copies under `output/<book_id>/...` as one analyzed book's reproducible source territory
- `state/library_sources/` as the durable local source-library territory for manually curated books
- `eval/datasets/` and `eval/manifests/` as evaluation-package territory

**Why it matters later**: This is the storage rule that should stop future evaluation work from becoming "whatever books happened to be uploaded recently." It also explains why user uploads are not automatically part of the durable library or benchmark corpus, and why promotion into those roles should remain explicit.

**Primary evidence**:
- `docs/workspace-overview.md`
- `docs/backend-sequential-lifecycle.md`
- `docs/backend-reader-evaluation.md`
- `reading-companion-backend/AGENTS.md`

## Entry 18
**ID**: DEC-018
**Status**: active

**Decision / Inflection**: Organize benchmark inputs by evidence family and language track instead of by one active mechanism's folder tree.

**Period**: March 2026, during the first bilingual `attentional_v2` benchmark preparation pass.

**Problem**: The project now needs multiple kinds of benchmark inputs at once: excerpt cases, chapter corpora, runtime fixtures, and compatibility fixtures. Without a durable dataset layout, those assets would drift into ad hoc folders, silently mix tracked inputs with generated outputs, and make it harder to reuse the same structure for later mechanisms.

**Alternatives considered**: Keep adding one-off benchmark folders per mechanism, store all benchmark inputs in one flat dataset directory, or let manifests and tracked datasets live together without a stronger boundary.

**Why this path won**: A family-first layout matches the evaluation-question structure more closely than a mechanism-first pile. It also makes bilingual handling clearer by separating `en`, `zh`, and `shared` tracks at the package level, while keeping source-book inventories and corpus-selection manifests in their own manifest territory.

**What changed in the system**: The stable evaluation doc now defines dataset-organization rules for `excerpt_cases`, `chapter_corpora`, `runtime_fixtures`, and `compatibility_fixtures` under `reading-companion-backend/eval/datasets/`. The repo now also has tracked family roots and manifest roots under `reading-companion-backend/eval/manifests/` for source-book inventories, corpus manifests, split manifests, and local-path references.

**Why it matters later**: This is the storage rule that should keep future benchmark work reproducible and comparable across mechanisms. It also prevents the first `attentional_v2` benchmark package shape from becoming an accidental one-off that later mechanisms have to work around.

**Primary evidence**:
- `docs/backend-reader-evaluation.md`
- `reading-companion-backend/eval/datasets/README.md`
- `reading-companion-backend/eval/manifests/README.md`
- `docs/implementation/new-reading-mechanism/evaluation-dataset-layout.md`

## Entry 19
**ID**: DEC-019
**Status**: active

**Decision / Inflection**: Mirror the family-first evaluation dataset layout under a local-only package territory for private books instead of forcing copyrighted inputs into tracked benchmark packages.

**Period**: Late March 2026, when the first serious private-book supplement from the user's local Downloads corpus entered `attentional_v2` evaluation planning.

**Problem**: The project already had a stable tracked dataset layout under `eval/datasets/`, but that layout alone was not enough once private contemporary books became part of the evaluation plan. We needed a way to use those books for excerpt, chapter, and runtime packages without quietly checking copyrighted source text into the repo or losing the same family-first structure that later evaluation code should rely on.

**Alternatives considered**: Keep all benchmark packages tracked and hope contributors avoid private books, store private excerpt/chapter packages in ad hoc local folders without a stable rule, or avoid using valuable local books entirely and limit the benchmark corpus to public-domain sources.

**Why this path won**: A local-only mirror keeps the legal and storage boundary honest while preserving the same package contract across tracked and private benchmark inputs. That lets the project benefit from richer modern books without making future evaluation code depend on a second informal layout.

**What changed in the system**: Stable docs now reserve `reading-companion-backend/state/eval_local_datasets/` as the local-only mirror for excerpt, chapter, runtime, and compatibility packages derived from private books. Tracked manifests under `reading-companion-backend/eval/manifests/` now explicitly cover both local source-book references and local dataset-package references, while tracked `eval/datasets/` remains the home for repo-safe benchmark packages.

**Why it matters later**: This is the rule that lets the benchmark corpus grow beyond public-domain books without making the repo itself a dumping ground for copyrighted text. Later contributors need to know that "private local package" is a first-class evaluation territory, not an ad hoc exception.

**Primary evidence**:
- `docs/backend-reader-evaluation.md`
- `docs/workspace-overview.md`
- `docs/backend-sequential-lifecycle.md`
- `reading-companion-backend/AGENTS.md`
- `docs/implementation/new-reading-mechanism/evaluation-corpus-requirements.md`

## Entry 17
**ID**: DEC-020
**Status**: active

**Decision / Inflection**: Move mechanism-private reading artifacts under `_mechanisms/<mechanism_key>/` and reserve top-level `public/` plus `_runtime/` for shared cross-mechanism state.

**Period**: Late March 2026, immediately after the shared substrate extraction.

**Problem**: Even after `book_document.json` became the canonical parsed-book substrate, iterator-specific artifacts such as `structure.json`, `reader_memory.json`, checkpoints, and `book_analysis` outputs still lived in shared-looking top-level directories. That kept the output tree visually and semantically blurred, making it too easy for future contributors to mistake mechanism-private artifacts for universal runtime truth.

**Alternatives considered**: Keep the mixed top-level layout and rely on naming discipline alone, duplicate artifacts into both shared and mechanism-specific paths, or postpone output-layout cleanup until a second reader mechanism was already live.

**Why this path won**: Namespacing mechanism-private artifacts under `_mechanisms/<mechanism_key>/` finishes the same boundary that `reading_core` and `reading_runtime` were designed to create. It keeps shared product/runtime surfaces obvious, gives each mechanism room for its own derived structures and runtime state, and preserves backward compatibility through helper-based fallback instead of messy duplicate writes.

**What changed in the system**: `iterator_v1` now writes derived section structure to `_mechanisms/iterator_v1/derived/structure.json`, private runtime memory/checkpoints/plan state to `_mechanisms/iterator_v1/runtime/`, and secondary analysis artifacts to `_mechanisms/iterator_v1/internal/`. Shared helpers still resolve older shared-path and flat legacy artifacts on read, but new writes use the namespaced canonical layout. Normal runs no longer persist normalized eval bundles; explicit eval runs may write `_mechanisms/iterator_v1/exports/normalized_eval_bundle.json`.

**Why it matters later**: This is the artifact-layout decision that keeps future multi-mechanism work from collapsing back into top-level iterator assumptions. Later contributors need to know that top-level `public/` and `_runtime/` are shared shell territory, while `_mechanisms/` is where mechanism ontology, checkpoints, diagnostics, and optional eval exports belong.

**Primary evidence**:
- `reading-companion-backend/src/reading_runtime/artifacts.py`
- `reading-companion-backend/src/iterator_reader/storage.py`
- `reading-companion-backend/src/iterator_reader/iterator.py`
- `reading-companion-backend/src/reading_mechanisms/iterator_v1.py`
- `docs/backend-sequential-lifecycle.md`
- `docs/backend-state-aggregation.md`

## Entry 18
**ID**: DEC-021
**Status**: active

**Decision / Inflection**: Split backend reading documentation into a shared mechanism-platform doc plus per-mechanism docs.

**Period**: Late March 2026, after the shared runtime, substrate, and artifact boundaries were already established.

**Problem**: The repo already needed to support multiple reader mechanisms, but the documentation still treated `docs/backend-reading-mechanism.md` as if one file could be both the shared platform authority and the full internal authority for the current default mechanism. That shape would have made future mechanism docs either second-class notes or would have silently universalized `iterator_v1` concepts such as `section` and `subsegment`.

**Alternatives considered**: Keep one shared mechanism doc and let it grow appendices for every mechanism, hard-rename the existing doc into `iterator_v1` immediately and replace it everywhere, or keep future mechanism designs only in research notes until implementation.

**Why this path won**: Keeping `docs/backend-reading-mechanism.md` as the shared platform/router doc preserves one stable shared entrypoint, while a dedicated `docs/backend-reading-mechanisms/` folder gives each mechanism equal documentary standing. That makes design-only mechanisms visible early, keeps shared boundaries clean, and prevents one mechanism's ontology from becoming implicit backend law.

**What changed in the system**: `docs/backend-reading-mechanism.md` now owns only shared mechanism-platform rules, status model, and doc routing. `docs/backend-reading-mechanisms/README.md` now owns the mechanism catalog and authoring rules. `docs/backend-reading-mechanisms/iterator_v1.md` now owns the live mechanism internals that previously lived in the shared doc, and `docs/backend-reading-mechanisms/attentional_v2.md` records the future design as a stable `design-only` mechanism doc.

**Why it matters later**: This is the documentation boundary that should keep future multi-mechanism work legible. Later contributors need to know which facts are shared platform rules, which facts belong to one mechanism, and how to add a new mechanism doc without re-centering the whole repo on the current default reader.

**Primary evidence**:
- `docs/backend-reading-mechanism.md`
- `docs/backend-reading-mechanisms/README.md`
- `docs/backend-reading-mechanisms/iterator_v1.md`
- `docs/backend-reading-mechanisms/attentional_v2.md`
- `AGENTS.md`
- `reading-companion-backend/AGENTS.md`

## Entry 19
**ID**: DEC-022
**Status**: active

**Decision / Inflection**: Split prompt ownership by boundary instead of keeping one global live prompt bank.

**Period**: Late March 2026, after the shared mechanism/runtime boundaries and the multi-mechanism doc split were already in place.

**Problem**: The repo still kept live parse, reader, book-analysis, shared fragment, and legacy prompt text together in one global `src/prompts/templates.py` module. That was workable while there was effectively one active reader, but it blurred which prompts belonged to a mechanism, which belonged to a reusable capability, and which fragments were truly shared infrastructure.

**Alternatives considered**: Keep the global prompt bank and rely on naming discipline, build a global cross-mechanism prompt registry, or postpone prompt ownership cleanup until a second live mechanism was already implemented.

**Why this path won**: Prompt ownership now matches the backend architecture. Shared fragments stay in `src/prompts/`, capability prompts such as `book_analysis` stay in capability-scoped modules, and mechanism-private prompts live with the mechanism implementation that owns them. That keeps future prompt work local to the reader or capability it actually changes, while the old `templates.py` can survive temporarily as a compatibility shim instead of remaining the canonical source of truth.

**What changed in the system**: Shared language/query fragments moved into `src/prompts/shared.py`. `iterator_v1` parse and reader prompts moved into `src/iterator_reader/prompts.py` with a typed `IteratorV1PromptSet`. `book_analysis` prompts moved into `src/prompts/capabilities/book_analysis.py` with a typed `BookAnalysisPromptSet`. Legacy unused prompt families moved into `src/prompts/legacy.py`. The current mechanism adapter now selects prompt bundles explicitly, and the old `src/prompts/templates.py` only re-exports from the new modules for migration compatibility.

**Why it matters later**: This is the prompt-boundary decision that keeps multi-mechanism work from collapsing back into one giant global template file. Later contributors need to know that prompt dispatch happens by mechanism or capability ownership, not by editing a universal prompt bank every time a reader changes.

**Primary evidence**:
- `reading-companion-backend/src/prompts/shared.py`
- `reading-companion-backend/src/prompts/capabilities/book_analysis.py`
- `reading-companion-backend/src/prompts/legacy.py`
- `reading-companion-backend/src/iterator_reader/prompts.py`
- `reading-companion-backend/src/reading_mechanisms/iterator_v1.py`
- `reading-companion-backend/src/prompts/templates.py`

## Entry 20
**ID**: DEC-023
**Status**: active

**Decision / Inflection**: Expand `book_document.json` from paragraph-only shared truth into a paragraph-plus-sentence canonical substrate.

**Period**: March 2026, during the first `attentional_v2` implementation phases.

**Problem**: The backend had already separated `book_document.json` from `iterator_v1`'s derived `structure.json`, but the shared substrate still stopped at paragraph records. That was enough for section-first readers, but not for a sentence-order mechanism that needs stable sentence ids, precise anchors, bounded look-back, and honest resume/reconstitution inputs without borrowing another mechanism's private splitter.

**Alternatives considered**: Keep sentence splitting entirely mechanism-private, create a second shared sentence artifact parallel to `book_document.json`, or force future mechanisms to derive their own sentence cursors from paragraph-only substrate at runtime.

**Why this path won**: Sentence order is substrate, not `attentional_v2`-only ontology. Extending `book_document.json` preserves one shared parsed-book truth while giving future mechanisms a stable chapter-local sentence inventory with grounded locators. Keeping the sentence layer parse-time and mechanism-neutral also avoids making `iterator_v1`'s `section` or `subsegment` logic the accidental universal authority for sentence-level reading.

**What changed in the system**: `src/reading_core/book_document.py` now models sentence records and locator character offsets. Parse flow now writes sentence inventories into each chapter of `public/book_document.json`, and load/build helpers backfill missing sentence layers into older paragraph-only documents when they are reloaded. `attentional_v2`'s Phase 1 scaffold also now rests on a real shared sentence substrate instead of on a planned placeholder.

**Why it matters later**: This is the substrate change that makes sentence-order mechanisms possible without introducing a second shared text authority. Future contributors will need to know that sentence ids and sentence-span locators belong to the canonical book document, even though current public surfaces may still remain section-shaped for compatibility.

**Primary evidence**:
- `reading-companion-backend/src/reading_core/book_document.py`
- `reading-companion-backend/src/reading_core/sentences.py`
- `reading-companion-backend/src/iterator_reader/parse.py`
- `docs/backend-reading-mechanism.md`
- `docs/backend-state-aggregation.md`

## Entry 21
**ID**: DEC-024
**Status**: active

**Decision / Inflection**: Keep `attentional_v2`'s v1 search design fully represented, but make search a rare escape hatch instead of a normal reading behavior.

**Period**: March 2026, during Phase 5 of the first `attentional_v2` implementation push.

**Problem**: The mechanism design explicitly included separate knowledge-use and search-policy state, but the implementation still had to choose whether version one would become search-heavy, silently defer real search to a later redesign, or preserve the full design while keeping the reading mind text-grounded.

**Alternatives considered**: Remove real search from v1 entirely and treat it as future-only, make search a common loop action whenever curiosity appeared, or collapse search decisions into the broader prior-knowledge mode instead of giving them their own state machine.

**Why this path won**: The project's core value is the visible reading mind, not a research reflex. Preserving `no_search`, `defer_search`, and `search_now` as real states keeps the design intact, but making `no_search` the normal posture protects the text-grounded reading direction. `defer_search` captures genuine curiosity without interrupting the read, while `search_now` survives only as a narrow escape hatch for identity-critical references or obscure allusions that would make continued reading less honest.

**What changed in the system**: `attentional_v2` now has a real knowledge-activation lifecycle, a conservative search-policy helper, and a Phase 5 `bridge_resolution` layer that judges earlier source anchors over a deterministic candidate set. The mechanism also now writes durable anchor-memory updates, typed anchor relations, motif and unresolved-reference indexes, trace links, and bridge move history instead of leaving those behaviors as prompt-only intentions.

**Why it matters later**: This is the decision that should stop future contributors from accidentally turning `attentional_v2` into a search-first reader while still preserving the original design's full control surface. It also marks the point where Phase 5 stopped being a design promise and became real durable state behavior in code.

**Primary evidence**:
- `reading-companion-backend/src/attentional_v2/knowledge.py`
- `reading-companion-backend/src/attentional_v2/bridge.py`
- `reading-companion-backend/src/attentional_v2/prompts.py`
- `docs/backend-reading-mechanisms/attentional_v2.md`
- `docs/implementation/new-reading-mechanism/open-questions.md`

## Entry 22
**ID**: DEC-025
**Status**: active

**Decision / Inflection**: Make mechanism-authored anchored reactions the durable Phase 6 source of truth, and treat current chapter/API shapes as compatibility projections.

**Period**: March 2026, during Phase 6 of the first `attentional_v2` implementation push.

**Problem**: The new mechanism design says the durable visible object is an anchored reaction, but the existing app still depends on section-shaped chapter results, current reaction cards, integer reaction ids, and mark lookup through persisted chapter payloads. The implementation needed a way to preserve the original thought object without breaking future compatibility work.

**Alternatives considered**: Store only current chapter-result reaction cards and treat them as truth, re-key marks on anchors instead of reactions, or postpone durable reaction truth until after all top-layer/API redesign work.

**Why this path won**: A dual-layer model preserves the product's real value. The mechanism now owns the original anchored reaction record, while the current chapter-result-style envelope becomes a compatibility projection derived from that truth. That keeps history append-only, lets reconsolidation create later linked thoughts instead of mutating earlier ones, and avoids letting current section-shaped transport fields silently redefine the mechanism's ontology.

**What changed in the system**: `attentional_v2` now writes a `reaction_records.json` runtime ledger, has Phase 6 node contracts for `reflective_promotion`, `reconsolidation`, and `chapter_consolidation`, and can project mechanism-authored reactions into a mechanism-private current-contract chapter-result compatibility payload. Reconsolidation now produces append-and-link records, and chapter-end slow-cycle helpers can cool pressure, carry forward live questions, promote reflective summaries, and optionally emit a chapter-level anchored reaction.

**Why it matters later**: This is the historical-integrity boundary for the new mechanism. Future contributors need to know that `section_ref` and similar fields are compatibility sidecars, not the source of truth, and that earlier persisted reactions must remain immutable even when later reading materially changes their meaning.

**Primary evidence**:
- `reading-companion-backend/src/attentional_v2/slow_cycle.py`
- `reading-companion-backend/src/attentional_v2/schemas.py`
- `reading-companion-backend/src/attentional_v2/storage.py`
- `reading-companion-backend/src/attentional_v2/prompts.py`
- `docs/backend-reading-mechanisms/attentional_v2.md`
- `docs/implementation/new-reading-mechanism/open-questions.md`

## Entry 23
**ID**: DEC-026
**Status**: active

**Decision / Inflection**: Make `attentional_v2` resume bounded, chapter-local, and explicitly reconstructive instead of silently restoring large hidden hot-state windows.

**Period**: March 2026, during Phase 7 of the first `attentional_v2` implementation push.

**Problem**: The mechanism design required warm, cold, and reconstitution resume, but the implementation still had to choose how much source text each mode should reread, where continuity should be persisted, and how to preserve the identity of the same reading mind without pretending a reconstructed state was the same thing as a truly warm in-memory continuation.

**Alternatives considered**: Restore all hot state as if it were still warm, reread large unbounded source tails to fake continuity, or leave resume semantics implicit until a later live runner existed.

**Why this path won**: A bounded chapter-local resume policy preserves honesty. `warm_resume` keeps reread at zero, `cold_resume` rebuilds near-term continuity from a small source window, and `reconstitution_resume` uses a larger but still capped current-chapter window tied to recent meaning units instead of hidden cross-chapter rereads. Persisting compact local continuity plus resume metadata also makes it explicit when hot state was reconstructed rather than warmed.

**What changed in the system**: `attentional_v2` now persists `local_continuity.json` and `resume_metadata.json`, writes full mechanism checkpoints alongside shared thin checkpoint summaries, and exposes helper functions for warm, cold, and reconstitution resume. The default reader policy now encodes the concrete reread window contract, and non-warm resume marks reconstructed hot state explicitly instead of silently treating it as warm continuity.

**Why it matters later**: This is the resume-honesty boundary for the new mechanism. Future contributors need to know that persisted slow-cycle state, not hidden large rereads, is the primary source of continuity, and that any non-warm rebuild must remain visible as a reconstruction rather than a perfect continuation.

**Primary evidence**:
- `reading-companion-backend/src/attentional_v2/resume.py`
- `reading-companion-backend/src/attentional_v2/schemas.py`
- `reading-companion-backend/src/attentional_v2/storage.py`
- `docs/backend-reading-mechanisms/attentional_v2.md`
- `docs/implementation/new-reading-mechanism/open-questions.md`

## Entry 24
**ID**: DEC-027
**Status**: active

**Decision / Inflection**: Treat section-era public fields as temporary compatibility sidecars and begin the public migration toward locus- and anchor-native `attentional_v2` surfaces.

**Period**: March 2026, during the first Phase 8 shared-surface integration pass.

**Problem**: The product had already decided that future frontend/API surfaces should not keep chapter `section` as the long-term primary container, because not every reading mechanism has that ontology. At the same time, the current routed frontend, chapter views, and marks pages still depended heavily on `section_ref` / `segment_ref`.

**Alternatives considered**: Keep the public model section-first indefinitely, break the current frontend immediately in favor of a new non-section contract, or hide `attentional_v2`'s richer locus/anchor truth until a later all-at-once rewrite.

**Why this path won**: An additive migration preserves product honesty without forcing a destabilizing rewrite. The backend can now expose the mechanism's real reading locus and anchored thought structure directly enough for future product work, while still serving the current section-era frontend through compatibility sidecars. This keeps the top layer closer to mechanism-authored truth without pretending the full frontend migration is already done.

**What changed in the system**: Public schemas and payload shaping now additively expose `reading_locus`, `primary_anchor`, `related_anchors`, `supersedes_reaction_id`, `move_type`, and runtime-shell-backed active reaction references on analysis-state, activity, chapter, and mark payloads. `section_ref` / `segment_ref` remain in place for compatibility, but the stable docs now describe them as migration-era sidecars rather than the future public ontology.

**Why it matters later**: This entry records the moment the project explicitly chose a de-sectionized long-term direction for new mechanisms without forcing an immediate frontend break. Future contributors will need this context to understand why both section-era fields and richer anchor/locus fields coexist for a while, and why later work still needs to redesign chapter/detail and marks around chapter text plus anchored reactions.

**Primary evidence**:
- `reading-companion-backend/src/api/schemas.py`
- `reading-companion-backend/src/library/catalog.py`
- `reading-companion-backend/src/library/user_marks.py`
- `docs/api-contract.md`
- `docs/backend-state-aggregation.md`
- `docs/backend-reading-mechanisms/attentional_v2.md`

## Entry 25
**ID**: DEC-028
**Status**: active

**Decision / Inflection**: Split `attentional_v2` observability into thin standard runtime history and optional debug-only diagnostics.

**Period**: March 2026, during the later Phase 8 observability pass.

**Problem**: The mechanism now had enough runtime state, resume behavior, and shared-surface projection that observability could no longer stay implicit. The project needed enough default traceability for trustworthy resume, public/runtime history, and evaluation, but persisting all controller/candidate/prompt internals on every run would have inflated storage and blurred the product-facing trace.

**Alternatives considered**: Keep all observability thin and shared even if evaluation and diagnosis became weak, persist all controller forensics by default in the shared runtime path, or postpone the split until a live end-to-end runner existed.

**Why this path won**: A two-tier observability model preserves both runtime honesty and implementation discipline. Shared `_runtime/` artifacts and public-facing activity now remain thin enough to represent real product/runtime history, while mechanism-private full checkpoints keep resume-correctness state, and deeper controller forensics stay in optional debug-only diagnostics. This matches the broader `mechanism-authored core, shell-authored envelope` direction instead of letting debug needs redefine the runtime shell.

**What changed in the system**: `reader_policy.logging` now explicitly records `observability_mode` plus standard/debug logging toggles. Shared `runtime_shell.json` and checkpoint summaries now carry `observability_mode`. Checkpoint writes and resume restores now emit standard shared activity events, while debug-mode diagnostics continue under `_mechanisms/attentional_v2/internal/diagnostics/events.jsonl`. Stable docs now also distinguish standard evaluation evidence from optional debug forensics.

**Why it matters later**: This is the project’s first explicit observability boundary for a future non-default mechanism. Future contributors will need this context to understand why standard traces should be sufficient for baseline evaluation and trustworthy resume, why full checkpoints remain standard-private instead of public, and why deep controller forensics should remain optional rather than silently becoming the default runtime posture.

**Primary evidence**:
- `reading-companion-backend/src/attentional_v2/observability.py`
- `reading-companion-backend/src/attentional_v2/resume.py`
- `reading-companion-backend/src/attentional_v2/storage.py`
- `reading-companion-backend/src/reading_runtime/shell_state.py`
- `docs/backend-state-aggregation.md`
- `docs/backend-reader-evaluation.md`
- `docs/backend-reading-mechanisms/attentional_v2.md`

## Entry 26
**ID**: DEC-029
**Status**: active

**Decision / Inflection**: Promote `attentional_v2` from a design-only scaffold to an experimental end-to-end mechanism behind the shared runtime shell.

**Period**: March 2026, during the Phase 8.5 live-runner integration pass.

**Problem**: The project had already landed sentence substrate, node contracts, slow-cycle state, resume helpers, observability, and eval exports, but `attentional_v2` still was not honestly live. Parse and read entrypoints still needed to run through shared provisioning, CLI `--mechanism`, async job launch/resume/recovery, and non-iterator compatibility aggregation without pretending `iterator_v1`'s `structure.json` was universal.

**Alternatives considered**: Keep `attentional_v2` marked design-only until the later evaluation corpus existed, fork more of `iterator_v1`'s job/runtime wiring into a second silo, or universalize the old mechanism's reader mind instead of extracting only the neutral lifecycle and provisioning helpers.

**Why this path won**: The backend direction is one shared runtime shell with multiple mechanism-specific reading minds. The right move was to extract mechanism-neutral provisioning and job plumbing into shared runtime helpers, keep mechanism ontology private, and then let `attentional_v2` run end to end as an experimental non-default mechanism. That preserves `iterator_v1` as default, keeps the public HTTP contract stable, and records that unsupported legacy `book_analysis` behavior should fail explicitly rather than by accident.

**What changed in the system**: Shared canonical provisioning now routes through `src/reading_runtime/`. Internal job launchers, resume, auto-resume, and incompatible fresh rerun now preserve `mechanism_key` with runtime-shell precedence. `AttentionalV2Mechanism()` is registered as a built-in experimental mechanism, `parse_book` and `read_book` are real entrypoints, CLI `--mechanism attentional_v2` is functional, and the backend can build manifests, analysis-state, chapter results, and marks-compatible payloads for non-iterator runs without requiring `iterator_v1` structure.

**Why it matters later**: This is the inflection point where `attentional_v2` stopped being a design promise and became a real backend runtime path. Future contributors need to know that experimental does not mean design-only anymore, that mechanism selection continuity across recovery now matters, and that the remaining work shifted from “make it runnable” to “evaluate it honestly and migrate the product surfaces intentionally.”

**Primary evidence**:
- `reading-companion-backend/src/reading_runtime/provisioning.py`
- `reading-companion-backend/src/library/jobs.py`
- `reading-companion-backend/src/attentional_v2/runner.py`
- `reading-companion-backend/src/reading_mechanisms/attentional_v2.py`
- `docs/backend-sequential-lifecycle.md`
- `docs/backend-reading-mechanism.md`
- `docs/backend-reading-mechanisms/README.md`
- `docs/backend-reading-mechanisms/attentional_v2.md`

## Entry 27
**ID**: DEC-030
**Status**: active

**Decision / Inflection**: Treat benchmark quality as a first-class evaluation concern and require dual diagnosis plus packet-based human review for high-impact case hardening.

**Period**: March 2026, immediately after the first corrected `attentional_v2` `mechanism_integrity` run on the tracked curated `v2` excerpt family.

**Problem**: The first serious local benchmark pass proved that the new bilingual excerpt benchmark family was viable, but it also showed that some weak results could plausibly come from benchmark-case design or harness behavior rather than the mechanism alone. Without an explicit rule, future work could overfit to mislabeled or under-reviewed cases and mistake benchmark weakness for mechanism weakness.

**Alternatives considered**: Treat the versioned curated dataset as de facto ground truth after the first full run, rely on ad hoc chat-based human feedback when a case looked suspicious, or keep all hardening inside LLM-only case-audit prompts without a durable human-review loop.

**Why this path won**: Evaluation needs stronger discipline than "run benchmark, trust score." The project now distinguishes factual dataset truth from reviewable benchmark judgment targets, requires dual diagnosis of mechanism versus dataset/harness problems, and adds a lightweight packet-based human review loop that works on the shared local machine without a frontend website. This keeps the benchmark executable and fast while making it much harder for weak cases to quietly steer the mechanism in the wrong direction.

**What changed in the system**: Stable evaluation docs now include a dataset trust model and the dual-diagnosis rule, the backend agent guide reminds coding agents not to blame mechanism or benchmark by default, and the backend now ships export/import tooling for packet-based benchmark review under `eval/review_packets/`. The temp implementation docs now record the full dataset-hardening method and the specific packet workflow for excerpt-case review and reimport.

**Why it matters later**: This is the point where dataset quality stopped being implicit benchmark hygiene and became an explicit project rule. Future contributors need this context to understand why some evaluation work now pauses for case hardening, why builder-curated cases are not automatically treated as final ground truth, and why packet-based human review exists even though there is no frontend review tool.

**Primary evidence**:
- `docs/backend-reader-evaluation.md`
- `reading-companion-backend/AGENTS.md`
- `docs/implementation/new-reading-mechanism/dataset-quality-hardening.md`
- `reading-companion-backend/eval/attentional_v2/export_dataset_review_packet.py`
- `reading-companion-backend/eval/attentional_v2/import_dataset_review_packet.py`
- `reading-companion-backend/eval/review_packets/README.md`

## Entry 28
**ID**: DEC-031
**Status**: active

**Decision / Inflection**: Replace manual packet review with multi-prompt LLM adjudication as the operational default for current benchmark hardening.

**Period**: March 2026, during the first dataset-hardening loop after the initial weak-case packets were created.

**Problem**: The benchmark hardening workflow had become executable, but in practice it still depended on scarce human review time. That made the review loop the new bottleneck and risked leaving the benchmark in a half-hardened state where the project knew weak cases existed but could not clear them quickly enough to keep evaluation moving.

**Alternatives considered**: Keep manual review as the default blocker, let the dataset builder make ad hoc untracked judgments in chat, or rely only on the earlier primary/adversarial case-audit prompts without a distinct final adjudication step.

**Why this path won**: The project needed an operational reviewer that was independent enough from the builder logic to reduce self-confirming drift, but still executable without manual review bandwidth. The chosen answer was a multi-prompt LLM review stack: primary case audit, adversarial disagreement audit, and a separate final adjudication pass that writes packet decisions back into the dataset under `llm_reviewed`. Manual human review remains possible later for higher-trust promotion work, but it is no longer the default blocker for current packet hardening.

**What changed in the system**: Stable evaluation docs and the backend agent guide now say that multi-prompt LLM adjudication is the default packet reviewer until explicitly reversed. Packet imports now preserve `review_origin` and `review_policy`, datasets now distinguish `llm_reviewed` from `human_reviewed`, and the first round of weak-case packets was imported under the new rule. The hardening loop now freezes reviewed slices based on `reviewed_active` cases rather than waiting on manual packet completion.

**Why it matters later**: Future contributors need to know that the project deliberately traded human-review dependence for an explicit multi-prompt LLM review policy, not because human review became worthless, but because current benchmark hardening needed to remain executable. Without this context, later readers could misinterpret `llm_reviewed` slices as accidental stopgaps rather than the official operational review state for this period.

**Primary evidence**:
- `docs/backend-reader-evaluation.md`
- `reading-companion-backend/AGENTS.md`
- `docs/implementation/new-reading-mechanism/dataset-quality-hardening.md`
- `reading-companion-backend/eval/attentional_v2/import_dataset_review_packet.py`
- `reading-companion-backend/eval/attentional_v2/auto_review_packet.py`
- `reading-companion-backend/eval/review_packets/README.md`

## Entry 29
**ID**: DEC-032
**Status**: active

**Decision / Inflection**: Promote project-owned LLM invocation, provider/profile policy, and trace emission into one shared backend layer.

**Period**: March 2026, during the benchmark-hardening side branch for universal LLM invocation and traceability.

**Problem**: The backend had accumulated multiple prompt-to-provider paths: iterator-specific helpers, eval scripts with direct provider clients, and a newer packet-audit tracing path that only covered one review workflow. That made failover policy, model-profile policy, and LLM traceability inconsistent across runtime and evaluation work. It also made the new packet-audit observability improvements look like a local tool instead of a backend capability.

**Alternatives considered**: Keep provider logic inside `src/iterator_reader/llm_utils.py` and patch more call sites around it, let each eval script keep its own provider client as long as it used the same API key, or support broad silent cross-model fallback for resilience.

**Why this path won**: The project needed one explicit invocation boundary that could separate operational concerns from semantic ones. A shared backend layer made it possible to keep same-model key failover as an operational fallback while forbidding silent cross-model switching inside one runtime or evaluation run. It also made task-level model policy concrete: cheaper/stabler runtime profiles, stronger pinned judge profiles, and explicit optional cross-model disagreement only when deliberately invoked. Centralizing trace emission also made runtime and eval observability comparable without requiring every mechanism or script to reinvent it.

**What changed in the system**: `src/reading_runtime/` now owns a structured provider/profile registry, contract adapters for `anthropic`, `google_genai`, and `openai_compatible`, one shared invocation gateway, and standard/debug trace helpers. The legacy iterator helper path is now a compatibility wrapper over that gateway. Runtime/eval call sites for packet audits, packet adjudication, integrity judging, `attentional_v2`, `iterator_v1`, and one-off comparison helpers now run through the shared layer. Backend setup now includes a registry example file plus env guidance for provider-specific secrets and task-level profiles.

**Why it matters later**: Future contributors need to know that failover policy, model choice, and traceability are now platform concerns, not mechanism-local conveniences. Without this entry, later readers could mistake the profile split between runtime and judge paths for ad hoc tuning, or reintroduce direct provider clients that silently bypass the shared trace contract.

**Primary evidence**:
- `reading-companion-backend/src/reading_runtime/llm_registry.py`
- `reading-companion-backend/src/reading_runtime/llm_gateway.py`
- `reading-companion-backend/src/iterator_reader/llm_utils.py`
- `docs/backend-reading-mechanism.md`
- `docs/backend-reader-evaluation.md`
- `README.md`

## Entry 30
**ID**: DEC-033
**Status**: active

**Decision / Inflection**: Treat reviewed-slice hardening plus mechanism repair as the gate for broader semantic comparison, then explicitly unblock chapter-scale comparison once the repaired reviewed slice generalized.

**Period**: Late March 2026, after the bilingual hardening and reviewed-slice expansion rounds, through repair pass 2.

**Problem**: The project had reached the point where `attentional_v2` was runnable and benchmarkable, but the first serious local excerpt results still mixed benchmark weakness with mechanism weakness. Moving straight into chapter-scale cross-mechanism comparison too early would have risked comparing architectures on a half-hardened benchmark and then overreacting to whatever the first broad results happened to say.

**Alternatives considered**: Start broader comparison as soon as the first reviewed slice existed, keep delaying broader comparison until every weak local case was repaired, or tune the mechanism directly against the still-small early reviewed slice without first proving that repairs generalized.

**Why this path won**: The project needed one explicit gate between local benchmark trust-building and broader comparison. The chosen rule was: harden the excerpt benchmark until the reviewed slice is meaningful, run narrowly targeted repair passes against the clearly weak local behaviors, then rerun the full reviewed slice. Only once that rerun showed strong generalization would broader chapter-scale comparison be unblocked. This protected the project from both premature broad claims and endless local overfitting.

**What changed in the system**: The tracker and handoff now record benchmark hardening as an explicit gating lane rather than a side chore. The project ran bilingual `4+4` hardening, bilingual `6+6` reviewed-slice expansion, a first reviewed-slice floor check, two mechanism-repair passes, and then a repaired full reviewed-slice rerun before allowing broader chapter comparison to proceed. The resulting first chapter-core comparison then produced split evidence instead of a flat win/loss story: `iterator_v1` remained stronger on English chapter-local reading, while `attentional_v2` was stronger on span trajectory overall and especially in Chinese.

**Why it matters later**: This is the historical hinge between “make the new mechanism evaluable” and “compare it honestly at chapter scale.” Later contributors need to know that broader semantic comparison was not simply delayed or rushed by instinct; it was explicitly gated by benchmark hardening and repaired-slice generalization, and the first broad comparison produced mixed evidence rather than a simplistic promotion signal.

**Primary evidence**:
- `docs/implementation/new-reading-mechanism/dataset-quality-hardening.md`
- `docs/implementation/new-reading-mechanism/execution-tracker.md`
- `docs/agent-handoff.md`
- `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_integrity_reviewed_slice_round3_repair_pass2_20260326/summary/report.md`
- `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_vs_iterator_v1_chapter_core_en_round1_20260326/summary/report.md`
- `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_vs_iterator_v1_chapter_core_zh_round1_20260326/summary/report.md`

## Entry 31
**ID**: DEC-034
**Status**: active

**Decision / Inflection**: Turn the modern private-library supplement into the formal benchmark-diversification and growth lane, instead of leaving copyright-restricted nonfiction as an ad hoc local side pool.

**Period**: Late March 2026, after the `/Users/baiweijiang/Documents/BOOK` batch was merged with the earlier private local books.

**Problem**: The tracked public/open benchmark family had become strong enough for first serious evaluation, but it was still skewed toward older public-domain material and literary/nonfiction mixes that did not reflect the user's actual reading priorities. The project needed a way to widen genre coverage toward modern business, management, biography, history, science, and other nonfiction without pretending that copyrighted books could live in the tracked repo dataset.

**Alternatives considered**: Keep relying on the public/open corpus as the main long-term benchmark source, add modern private books only opportunistically when a specific gap appeared, or treat the private books as useful local reading material but not as a formal benchmark-growth lane.

**Why this path won**: The project needed both breadth and honesty. A local-only supplement preserves copyright boundaries while still letting the benchmark grow in the directions that matter for real reading quality. Formalizing the supplement as its own manifest-backed source pool also keeps the process reproducible: ingest, fingerprint, parse, screen, package, then promote into the formal benchmark through balanced curation instead of ad hoc cherry-picking.

**What changed in the system**: The repo now treats the combined private library as a first-class local-only source family with source manifests, local refs, corpus manifests, split manifests, and generated local-only dataset packages. The current combined pool contains the newly supplied `/Users/baiweijiang/Documents/BOOK` titles plus the earlier private books, and the execution plan now includes a frozen round-1 promotion-preparation pass to lift balanced English/Chinese chapter and excerpt candidates from that supplement into the next formal curation/review cycle. The category strategy also shifted explicitly toward a more diversified benchmark mix, with special weight on business, management, and biography.

**Why it matters later**: This is the moment where benchmark growth stopped meaning “find more public-domain books” and started meaning “grow a diversified bilingual benchmark family across tracked public sources and local-only modern sources.” Later contributors need this context to understand why local-only manifests and package families exist, why modern nonfiction expansion is now part of the main evaluation roadmap, and why benchmark size and genre coverage are expected to grow together.

**Primary evidence**:
- `docs/implementation/new-reading-mechanism/modern-nonfiction-expansion-booklist.md`
- `docs/implementation/new-reading-mechanism/private-library-promotion-round1.md`
- `docs/implementation/new-reading-mechanism/private-library-promotion-round1-execution.md`
- `docs/implementation/new-reading-mechanism/execution-tracker.md`
- `reading-companion-backend/eval/manifests/source_books/attentional_v2_private_library_screen_v2.json`
- `reading-companion-backend/eval/manifests/local_refs/attentional_v2_private_library_v2.json`

## Entry 32
**ID**: DEC-035
**Status**: active

**Decision / Inflection**: Make evaluation preserve portable strengths and repeatable failures, not only winner/loser conclusions.

**Period**: Late March 2026, after the first broader chapter-core comparison made the split result concrete.

**Problem**: The evaluation process had become strong enough to identify mixed results across mechanisms, but a plain winner/loser summary was not enough to support later mechanism synthesis. If the project only remembered which mechanism won each scope, it would lose the more valuable design memory: which local reading habits were genuinely strong, which chapter-scale accumulation behaviors were worth carrying forward, and which failures should not be repeated.

**Alternatives considered**: Keep comparison results mostly as run artifacts plus prose interpretation, store only high-level winner summaries in the tracker, or leave strength/failure extraction to later ad hoc chat reconstruction when synthesis work starts.

**Why this path won**: The project is not trying to preserve two permanently separate reader tribes. It is trying to build a better reader over time. That means evaluation must preserve both adoption candidates and anti-pattern memory. Turning this into an explicit rule keeps strong observed behaviors portable across mechanisms and keeps repeated mistakes visible before they re-enter future prompt, retrieval, memory, or controller work.

**What changed in the system**: Stable evaluation docs now require meaningful comparison and repair passes to preserve both positive adoption candidates and negative anti-patterns. The backend agent guide now reminds coding agents not to stop at winner/loser language when a run exposes transferable strengths or repeatable mistakes. The implementation workspace now also has a dedicated mechanism-pattern ledger that records concrete strengths, adoption candidates, failure modes, evidence links, and adoption status.

**Why it matters later**: This is the policy that makes later synthesis work possible without relying on fragile memory. Future contributors should be able to look back and answer not only "who won this run?" but also "what should survive into the next mechanism?" and "what must not be repeated?"

**Primary evidence**:
- `docs/backend-reader-evaluation.md`
- `reading-companion-backend/AGENTS.md`
- `docs/implementation/new-reading-mechanism/mechanism-pattern-ledger.md`
- `docs/implementation/new-reading-mechanism/execution-tracker.md`
- `docs/agent-handoff.md`

## Entry 33
**ID**: DEC-036
**Status**: active

**Decision / Inflection**: Require each meaningful evaluation round to close the loop from result -> causal interpretation -> selective implementation or explicit deferment, instead of treating the ledger as a passive archive.

**Period**: Late March 2026, after the first broader comparison had already produced usable causal findings and the project recognized the risk of letting them pile up faster than they were absorbed.

**Problem**: The project had already created a stronger evaluation memory system by preserving strengths, anti-patterns, and causal findings. But that improvement carried a new risk: the ledger could become a large graveyard of good ideas and warnings that never shaped the active mechanism soon enough to matter. That would weaken context, delay learning, and make later synthesis feel like a one-time salvage exercise instead of a live engineering loop.

**Alternatives considered**: Keep the ledger as a long-term reference only, rely on future ad hoc synthesis passes to decide what to implement, or immediately copy every attractive behavior from the winning mechanism into the approved one.

**Why this path won**: The project needed a middle path between passive note-taking and mechanical feature-merging. The chosen rule is: every meaningful evaluation round should identify likely contributing causes, choose a small number of high-value actions that fit the currently approved mechanism, and either implement them promptly or record a concrete defer reason. This preserves context while avoiding two opposite mistakes: waiting too long to absorb real lessons, and copying behaviors without respecting the approved mechanism's framework.

**What changed in the system**: Stable evaluation docs now define an evaluation-to-implementation rule plus a selective synthesis rule. Root and backend agent guides now require agents to go beyond storing findings in docs: they must investigate what contributed to the result, convert high-confidence findings into selective implementation actions or explicit defer reasons, and preserve the approved mechanism's framework when carrying strengths forward. The mechanism-pattern ledger now carries dispositions and next actions rather than only descriptive findings.

**Why it matters later**: Future contributors need to know that evaluation memory is now operational, not archival. A later reader should be able to reconstruct not just what the project learned, but how those lessons were filtered, when they were acted on, and why some attractive ideas were deferred or rejected as misaligned.

**Primary evidence**:
- `docs/backend-reader-evaluation.md`
- `reading-companion-backend/AGENTS.md`
- `AGENTS.md`
- `docs/implementation/new-reading-mechanism/mechanism-pattern-ledger.md`

## Entry 34
**ID**: DEC-037
**Status**: active

**Decision / Inflection**: Add a durable registry for long-running eval and dataset background jobs so agent handoffs no longer depend on chat memory.

**Period**: Late March 2026, after repeated multi-minute and multi-hour evaluation runs made agent changes and overlapping reruns harder to manage safely.

**Problem**: The project increasingly relied on long-running offline work such as chapter comparison reruns, packet audits, packet adjudication, and dataset-construction passes. Those runs often lasted far longer than one chat turn or one active agent session. Without a durable job registry, later agents had to infer what was still running from scattered chat history, half-written handoff notes, or raw process output. That made it too easy to duplicate work, lose check commands, or forget what decision a still-running job was supposed to inform.

**Alternatives considered**: Keep relying on `docs/agent-handoff.md` plus informal chat summaries, reuse the product-runtime `state/jobs/` records even though they describe user-upload analysis jobs rather than offline eval work, or leave long-running eval jobs untracked except for their run directories.

**Why this path won**: The project needed a lightweight but durable workflow boundary for agent-owned offline work. A separate background-job registry keeps product runtime jobs and offline evaluation jobs distinct while still giving future agents one source of truth for what is running, what should be checked next, and what decision the job belongs to. Pairing the machine-readable registry with a generated human summary preserves handoff readability without forcing agents to hand-edit dynamic state into docs.

**What changed in the system**: Backend infrastructure now includes a shared background-job registry helper plus two scripts: one to create/update/archive job records and one to refresh and inspect them. The registry lives under `reading-companion-backend/state/job_registry/`. This entry's original `active_jobs.json` authority model was later superseded by `DEC-039`, which made per-job records under `jobs/<job_id>.json` canonical and left `active_jobs.json` / `active_jobs.md` as derived active-only mirrors. Workspace and backend agent rules now require jobs expected to run longer than roughly `10-15` minutes to be registered, and require later agents to refresh the registry before starting overlapping long-running work.

**Why it matters later**: Future contributors will otherwise see the registry files and helper scripts without understanding why the project chose a separate eval/agent job ledger instead of overloading product runtime jobs. This entry records that the registry exists to preserve task linkage, check commands, and decision context across agent changes, not simply to list processes.

**Primary evidence**:
- `reading-companion-backend/src/reading_runtime/background_job_registry.py`
- `reading-companion-backend/scripts/register_background_job.py`
- `reading-companion-backend/scripts/check_background_jobs.py`
- `docs/backend-reader-evaluation.md`
- `docs/agent-handoff.md`
- `AGENTS.md`
- `reading-companion-backend/AGENTS.md`

## Entry 35
**ID**: DEC-038
**Status**: active

## Entry 36
**ID**: DEC-039
**Status**: active

**Decision / Inflection**: Realign Phase 9 evaluation into separate local excerpt and bounded long-span surfaces instead of forcing one benchmark family to answer every remaining reader-quality question.

**Period**: Early April 2026, after the clustered benchmark v1 freeze and the completed human-notes-guided excerpt reviewed freeze made the mismatch between local and accumulation surfaces explicit.

**Problem**: The project had already built two strong but differently shaped dataset lines. The clustered benchmark v1 was good for fast iteration and preserved a frozen `chapter_core`, but its chapter surface was still too coupled to the same texts as the excerpt surface and too pressure-imbalanced to remain the sole design center for `coherent_accumulation`. Meanwhile the human-notes-guided line had become highly efficient and credible for local excerpt evaluation, but its chapter-facing structures were cluster-shaped rather than a ready-made decisive chapter benchmark. Treating all three kept north-star dimensions as if they required one shared text surface was starting to blur the real evaluation questions.

**Alternatives considered**: Keep the clustered benchmark as the one active surface for chapter and excerpt work, promote the notes-guided line wholesale into the active benchmark pointer, or postpone local judged evaluation until a new universal benchmark family could be built.

**Why this path won**: The project needed to separate “what kind of reading span is being tested?” from “what kind of output value is being judged?”. `selective_legibility` fits a local excerpt surface where many cases can be reused per read. `coherent_accumulation` fits a bounded long-span window surface where continuity, carryover, and callback pressure are actually visible. `insight_and_clarification` is not a third span family; it is an orthogonal output-value axis that can score both local and long-span cases. This split lets the project start judged local eval immediately while building a better-fitting long-span benchmark in parallel.

**What changed in the system**: Stable evaluation docs now state that excerpt/local and long-span/window are separate evaluation surfaces. `coherent_accumulation` is now interpreted operationally as bounded long-span continuity and carryover rather than generic whole-book memory. The completed human-notes-guided excerpt reviewed freeze is now treated as a real runnable local eval surface. A new bounded long-span namespace, `attentional_v2_accumulation_benchmark_v1`, becomes the next dataset-construction lane, with `window_cases` and `accumulation_probes` rather than plain chapter rows. Clustered benchmark v1 remains preserved and readable, but it is no longer the sole design center for the next accumulation dataset.

**Why it matters later**: Future contributors should not assume that “one benchmark” always means “one text surface for every reader-quality question.” This decision records that the project deliberately chose better-fit surfaces over forced uniformity, while still keeping the resulting evaluation strategy bounded and interview-legible.

**Primary evidence**:
- `docs/backend-reader-evaluation.md`
- `docs/current-state.md`
- `docs/tasks/registry.md`
- `docs/implementation/new-reading-mechanism/execution-tracker.md`

**Decision / Inflection**: Make new runtime and evaluation processes concurrency-adaptive by default instead of relying on fixed worker counts inside individual scripts.

**Period**: Late March 2026, after the project had already introduced a structured LLM registry and identified case-level serial execution as a major source of wasted eval time.

**Problem**: Independent cases, packet reviews, and benchmark comparisons were still leaving throughput on the table because worker widths were hardcoded per runner, while the shared LLM layer already had enough structure to manage concurrency centrally. This made speed tuning inconsistent and encouraged local flags instead of one coherent default policy.

**Alternatives considered**: Keep adding runner-local `--max-workers` overrides while leaving defaults conservative, require multiple API keys before allowing real parallelism, or continue treating each script's fixed worker count as the main safety mechanism.

**Why this path won**: The project needed one place to own same-key parallelism, adaptive backoff, and default worker sizing. A shared adaptive budget makes new jobs faster by default while still preserving one explicit safety boundary for rate limits, timeouts, and malformed responses.

**What changed in the system**: Structured registry entries now carry explicit concurrency-policy fields, the shared gateway adapts provider-wide same-key concurrency for new processes, and major eval/review runners derive their default case fanout from a shared job-concurrency helper instead of fixed `1` or `2` worker defaults. `iterator_v1` background segmentation defaults are also now derived from the runtime budget unless explicit env overrides are present.

**Why it matters later**: Future contributors will otherwise see higher default parallelism and multiple thread pools across the codebase without understanding that this was an intentional system-wide redesign, not a set of unrelated speed tweaks.

**Primary evidence**:
- `reading-companion-backend/src/reading_runtime/llm_gateway.py`
- `reading-companion-backend/src/reading_runtime/llm_registry.py`
- `reading-companion-backend/src/reading_runtime/job_concurrency.py`
- `docs/backend-reader-evaluation.md`
- `docs/runtime-modes.md`

## Entry 36
**ID**: DEC-039
**Status**: active

**Decision / Inflection**: Unify product and offline long-running jobs under one canonical registry while keeping public product job/status behavior stable.

**Period**: Late March 2026, after a completed English chapter-core eval run was misclassified as `abandoned` because the registry relied too heavily on optional status files.

**Problem**: The project had two separate job systems: product reading jobs under `state/jobs/` and offline eval/dataset jobs under `state/job_registry/active_jobs.json`. That split made storage authority ambiguous, forced some jobs to “serve the registry” by writing explicit completion markers, and let successful offline runs fall through to `abandoned` when they exited cleanly without a status file.

**Alternatives considered**: Keep the split system and only tighten the `abandoned` heuristic, push all lifecycle responsibility into individual job scripts, or expose a brand-new public API job model in the same pass.

**Why this path won**: The project needed one canonical job ledger that could observe both product and offline work, infer terminal state from objective evidence, and still leave public product routes untouched. A unified per-job registry under `state/job_registry/jobs/` keeps one source of truth for pid, exit code, runtime state, logs, and success evidence, while compatibility shadows and API mapping avoid a disruptive frontend change.

**What changed in the system**: Canonical job records now live under `reading-companion-backend/state/job_registry/jobs/<job_id>.json` for both product reading jobs and offline eval/dataset jobs. `active_jobs.json` and `active_jobs.md` became derived operator-facing mirrors rather than the primary store. Product `state/jobs/<job_id>.json` remains a compatibility shadow during the migration window. The registry now infers `completed` from successful outputs/checks even without a status file, narrows `abandoned` to genuinely orphaned cases, and adds a wrapper-first launcher for generic offline jobs.

**Why it matters later**: Future contributors will otherwise see both `state/jobs/` and `state/job_registry/` and assume the split is still intentional. This entry records that the system has one canonical job store now, that `abandoned` is intentionally rare, and that wrapper-based observation should be the default for generic long-running jobs.

**Primary evidence**:
- `reading-companion-backend/src/reading_runtime/background_job_registry.py`
- `reading-companion-backend/src/library/jobs.py`
- `reading-companion-backend/scripts/run_registered_job.py`
- `docs/runtime-modes.md`
- `docs/backend-sequential-lifecycle.md`
- `docs/backend-reader-evaluation.md`

## Entry 37
**ID**: DEC-040
**Status**: active

**Decision / Inflection**: Establish a repo-first agent-switching memory system with canonical current-state and task-router docs.

**Period**: Late March 2026, after the workspace had already accumulated strong stable docs, a detailed initiative tracker, and a durable job registry but still lacked one canonical repo-local switching surface.

**Problem**: The project was already fairly handoff-friendly, but live status still had to be reconstructed from several places: stable docs for rules, `docs/agent-handoff.md` for temporary summaries, initiative trackers for detailed progress, and the job registry for mutable runtime truth. That made agent switching possible, but slower and more drift-prone than it needed to be.

**Alternatives considered**: Keep relying on the existing handoff note plus initiative trackers, move current state authority into an external tool such as Notion, or let each coding agent invent its own working-memory convention.

**Why this path won**: A repo-first switching system keeps the workflow tool-agnostic and Git-traceable. Markdown remains the human-facing layer, JSON remains the machine-facing layer, and shell commands remain the common interface across Codex, Claude Code, Gemini CLI, and other agents. Adding canonical current-state and task-router docs closes the gap between stable truths and live work without replacing the detailed tracker or job-registry infrastructure that already holds the evidence.

**What changed in the system**: The workspace now has a source-of-truth map, a canonical `docs/current-state.md` with a machine-readable appendix, a workspace task registry in Markdown plus JSON, and two new commands: `make agent-context` and `make agent-check`. Root onboarding docs now route active work through the current-state/task layer, and `docs/agent-handoff.md` is reduced to session-only scratch space. Decision-log entries now also carry stable IDs plus lifecycle status so live task records can point to historical decisions directly.

**Why it matters later**: Future contributors and agents should now be able to switch in without chat history, recover the current objective quickly, trace any task to its detailed tracker and evidence, and trust that mutable job status still lives only in the job registry. This is the point where agent switching becomes an explicitly designed repo capability rather than a side effect of good documentation habits.

**Primary evidence**:
- `docs/source-of-truth-map.md`
- `docs/current-state.md`
- `docs/tasks/registry.md`
- `docs/tasks/registry.json`
- `scripts/print-agent-context.py`
- `scripts/check-agent-traceability.py`
- `AGENTS.md`

## Entry 38
**ID**: DEC-041
**Status**: active

**Decision / Inflection**: Shift local LLM operator setup from provider-first registry editing to named model targets plus profile bindings.

**Period**: Late March 2026, after the shared LLM layer had already centralized invocation, retry, cooldown, tracing, and adaptive concurrency but the editing surface still made multi-provider local setup awkward.

**Problem**: The shared LLM platform had become strong enough to support multiple providers, URLs, models, and pooled credentials, but the main local editing surface still exposed that power as one provider-first registry. In practice this made a simple operator question harder than it should have been: “where do I write the URL, model name, and key for this concrete target, and where do I decide which project profile uses it?” The older shape was workable for one provider or one compatibility file, but it became harder to edit safely once runtime, packet review, and evaluation judging could point at different endpoints or key pools.

**Alternatives considered**: Keep recommending the single provider/profile registry as the main editing path, fall back to env-only configuration for local secrets and target swapping, or redesign the gateway and call sites around a brand-new runtime abstraction instead of compiling a clearer operator surface into the existing registry.

**Why this path won**: The project needed a better operator experience without destabilizing the shared runtime policy layer. Splitting local setup into named targets plus profile bindings makes editing clearer: one file owns endpoint identity and credentials, the other owns project-role assignment and profile-level invocation settings. Compiling those files back into the existing provider/profile registry keeps the shared gateway, retry, cooldown, tracing, and concurrency logic intact while making multi-provider local configuration easier to reason about and safer to edit.

**What changed in the system**: The backend now supports `LLM_TARGETS_PATH` / `LLM_PROFILE_BINDINGS_PATH` plus inline JSON variants as the preferred structured local setup. Operators can define named targets in `reading-companion-backend/config/llm_targets.local.json`, bind stable project profile ids in `reading-companion-backend/config/llm_profile_bindings.local.json`, and keep those real local files untracked under `config/*.local.json`. The registry layer now compiles the new target/binding format into the existing internal provider/profile model, supports direct raw keys or env-backed credentials inside one neutral key-slot pool, and preserves the older `LLM_REGISTRY_PATH` / `LLM_REGISTRY_JSON` and legacy single-provider env fallback as compatibility modes.

**Why it matters later**: Future contributors will otherwise see both the target/binding files and the older registry files and assume the duplication is accidental. This entry records that the shared LLM platform itself still centers on one compiled registry and one gateway, while the local operator-facing surface intentionally changed to make endpoint/model/key editing and profile assignment clearer in multi-provider setups.

**Primary evidence**:
- `reading-companion-backend/src/reading_runtime/llm_registry.py`
- `reading-companion-backend/src/config.py`
- `reading-companion-backend/config/llm_targets.local.example.json`
- `reading-companion-backend/config/llm_profile_bindings.local.example.json`
- `reading-companion-backend/config/llm_registry.minimax_legacy_compatible.json`
- `README.md`
- `docs/backend-reader-evaluation.md`

## Entry 39
**ID**: DEC-042
**Status**: active

**Decision / Inflection**: Make profile routing tier-based and scope-pinned so target selection stays universal while each run keeps one consistent model/provider.

**Period**: Late March 2026, after the project had already moved local setup to named targets plus profile bindings and needed a cleaner answer to “primary now, backup only when headroom is not enough.”

**Problem**: The target-first editing model solved where operators write URLs, model names, and keys, but profile routing still leaned too much on one selected target plus fallback semantics that looked provider-specific and could still be interpreted as call-by-call failover. That was not a good fit for evaluation and dataset-review quality, where one scope should keep one model identity, and it was not a good long-term fit for future non-MiniMax primary/backup combinations.

**Alternatives considered**: Keep one hardcoded primary target plus provider-style fallback fields, move target switching into each individual call, or redesign the gateway around a brand-new planner layer instead of refining the existing profile-binding model.

**Why this path won**: Ordered target tiers keep the operator surface simple and universal. One profile can now express “prefer this pool, then that pool” without baking MiniMax-specific rules into the shared platform. Scope-start target selection preserves semantic consistency because runtime, packet review, and evaluation scopes now choose one concrete target up front and stay pinned to it, while same-target key-slot failover remains available inside that chosen target.

**What changed in the system**: `llm_profile_bindings.local.json` now supports ordered `target_tiers`, legacy `target_id` / `fallback_target_ids` compile into tiers for compatibility, and the shared gateway resolves one concrete target when an invocation scope starts. The gateway records the selected target/tier plus override reason in traces, supports temporary operator pins with `LLM_FORCE_TARGET_ID` and `LLM_FORCE_TIER_ID`, and only considers backup tiers when a new scope begins or when manual overrides request them. The current three shared profiles now all follow the same two-tier policy: prefer `MiniMax-M2.7-highspeed`, then fall back to `MiniMax-M2.7` when the primary tier cannot carry the required stable concurrency or is under quota pressure.

**Why it matters later**: Future contributors will otherwise see tier metadata, pinned-target trace fields, and override env vars without understanding why the project did not keep simpler per-call fallback. This entry records that the platform intentionally separates two concerns: within-target key failover can happen during a run, but cross-target model/provider choice is a scope-start decision so review and evaluation semantics stay stable.

**Primary evidence**:
- `reading-companion-backend/src/reading_runtime/llm_registry.py`
- `reading-companion-backend/src/reading_runtime/llm_gateway.py`
- `reading-companion-backend/tests/test_llm_gateway.py`
- `reading-companion-backend/config/llm_profile_bindings.local.example.json`
- `README.md`
- `docs/backend-reader-evaluation.md`

## Entry 40
**ID**: DEC-043
**Status**: active

**Decision / Inflection**: Introduce a managed library-inbox plus source-catalog layer as the default operator path for future dataset-source additions.

**Period**: Late March 2026, after the dataset platform was re-scoped from one-pass corpus building toward a full closed build-review-refine loop.

**Problem**: The project already had a durable source library under `state/library_sources/` and strong parse/package/review machinery, but future private-library growth still depended too much on hard-coded external roots such as `/Users/.../BOOK` and `~/Downloads`. That made book addition workable for one-off rescue passes, but too brittle for the closed-loop automation target where future case mining, review, and regeneration should all consume one project-owned source of truth.

**Alternatives considered**: Keep relying on the existing hard-coded external roots, store future books only in chat or ad hoc local paths until the smart builder was ready, or jump directly to a full dataset orchestrator before defining a stable source-intake surface.

**Why this path won**: The shortest safe path was to land the source-governance foundation first. A managed inbox plus source catalog gives operators one simple workflow for future book additions while preserving the existing durable source-library convention. It also keeps provenance lightweight: filename, hash, batch, canonical path, and status are enough for repeatable automation without turning dataset work into paperwork.

**What changed in the system**: The backend now recognizes `state/library_inbox/` as the operator drop-zone for future books, `state/library_sources/` remains the canonical managed copy territory, and `state/dataset_build/` now stores the durable source catalog and intake-run summaries. The operator contract was later simplified further to one inbox folder instead of separate language/visibility folders: language is auto-resolved, `visibility` is optional sidecar metadata, and new sources default to private/local-only storage unless explicitly marked public. The CLI at `reading-companion-backend/eval/attentional_v2/ingest_library_sources.py` plus the root `make library-source-intake` command copies inbox books into canonical paths, reads optional sidecar metadata, writes `source_catalog.json` / `source_catalog.md`, and records per-run summaries. The current private-library supplement builder was then rewired to consume that managed source catalog and canonical `state/library_sources/` copies instead of reaching back to `/Users/.../BOOK` or `~/Downloads`. This is still Phase 1 only: it does not replace screening, smart case mining, or packet review, but it gives those later phases a stable source-input layer that current supplement refreshes already use.

**Why it matters later**: Future contributors will otherwise see `state/library_inbox/`, `state/dataset_build/`, and the new intake CLI as incidental clutter. This entry records that they are part of the deliberate dataset-platform direction: the project now expects future source additions to enter through a managed intake layer before parse/screen/build/review automation takes over.

**Primary evidence**:
- `reading-companion-backend/eval/attentional_v2/ingest_library_sources.py`
- `reading-companion-backend/tests/test_source_intake.py`
- `scripts/library-source-intake.sh`
- `README.md`
- `reading-companion-backend/AGENTS.md`
- `docs/workspace-overview.md`
- `docs/source-of-truth-map.md`
- `docs/implementation/new-reading-mechanism/dataset-platform-closed-loop.md`

## Entry 41
**ID**: DEC-044
**Status**: active

**Decision / Inflection**: Make Phase 2 of the dataset platform explicitly question-aligned case construction, and postpone the full unattended controller until those construction artifacts stabilize.

**Period**: Late March 2026, after managed source intake and catalog wiring had already landed and the next dataset-platform question became how to build stronger evaluation cases instead of merely automating the old heuristic builder.

**Problem**: The project already had strong source intake, parsing, screening, packaging, and packet-review machinery, but its weakest layer was still semantic case construction. The current excerpt path in `corpus_builder.py` was still heavily shaped by fixed windows, role tags, and chapter-position heuristics. At the same time, the phrase "smart builder" was too vague to guide implementation well. If the project jumped directly into an unattended loop, it would risk automating today's weaker heuristics instead of automating a genuinely stronger benchmark-construction method.

**Alternatives considered**: Keep the vague "smart builder" label and continue iterating heuristics informally, jump directly to the full unattended dataset loop before the new construction artifacts existed, or replace the current builder with a single monolithic LLM pass that handled source mining and dataset packaging together.

**Why this path won**: The project needed a clearer Phase 2 contract before more automation. `Question-Aligned Case Construction` names the real job: build cases because they answer explicit evaluation questions under judgeable conditions. It preserves the current deterministic strengths, introduces semantic intermediate artifacts such as target profiles and opportunity cards, and gives the future unattended loop a stable contract to orchestrate. Designing the loop boundary now is enough to avoid rework; fully designing the controller later avoids hardening the wrong semantics too early.

**What changed in the system**: The implementation workspace now treats Phase 2 as `Question-Aligned Case Construction` instead of `smart target-case mining`. The new design doc defines target profiles, opportunity cards, case assembly, adequacy reporting, and the deterministic-vs-LLM ownership split. The active dataset-platform task was renamed to match that design direction. The unattended loop remains a Phase 3 concern, but its artifact boundary is now explicitly defined: Phase 2 must emit stable target-profile, opportunity-card, reserve/replacement, and adequacy-report artifacts before the full unattended controller is finalized.

**Why it matters later**: Future contributors will otherwise see the automation goal and assume the next step was simply "make the builder autonomous." This entry records that the intended sequence is more deliberate: first build a stronger question-aligned semantic construction layer, then automate that stronger layer. It also records that Phase 3 should orchestrate stable construction artifacts instead of implicitly defining them.

**Primary evidence**:
- `docs/implementation/new-reading-mechanism/question-aligned-case-construction.md`
- `docs/implementation/new-reading-mechanism/dataset-platform-closed-loop.md`
- `docs/implementation/new-reading-mechanism/execution-tracker.md`
- `docs/tasks/registry.md`
- `docs/tasks/registry.json`

## Entry 42
**ID**: DEC-045
**Status**: active

**Decision / Inflection**: Stop treating public/private as a primary dataset-platform organizing rule; keep it only as compatibility metadata while the project optimizes for product quality, automation, and speed.

**Period**: Late March 2026, after the managed inbox, source catalog, and first question-aligned supplement landing had already clarified that the main product bottlenecks were case quality and automation rather than source-distribution handling.

**Problem**: The dataset platform had already simplified operator intake to one inbox folder, but `visibility` still leaked into canonical source paths, generated source ids, and parts of the dataset-platform narrative as if public/private distribution were a first-class product concern. That added friction and made future automation look more complicated than the actual product goal required. The project's immediate goal is stronger reader evaluation data and faster closed-loop improvement, not distribution packaging.

**Alternatives considered**: Keep the current visibility split everywhere because old manifests used it, remove all visibility metadata immediately and migrate every historical manifest/path, or build a heavier dual-track public/private architecture before the unattended loop landed.

**Why this path won**: The best tradeoff was to simplify the live platform without forcing a risky migration. New managed copies now use one language-rooted source tree, default generated source ids no longer bake visibility into the identifier, and the current managed supplement loader no longer treats visibility as its primary admission gate. Historical dataset ids, manifests, and older `/private/` paths still work, but they are explicitly compatibility baggage rather than the design center.

**What changed in the system**: `reading-companion-backend/eval/attentional_v2/ingest_library_sources.py` now treats `visibility` as optional compatibility metadata, writes new canonical copies under `state/library_sources/<language>/`, and generates default source ids as `<canonical_stem>_<language>`. `reading-companion-backend/eval/attentional_v2/build_private_library_supplement.py` now loads managed source records without filtering them by visibility. Stable docs and current-state/task routing now say explicitly that future dataset-platform work should optimize around managed-source quality and automation rather than around public/private branching. Historical `private_library` naming remains in some dataset ids and manifests for continuity with existing evidence.

**Why it matters later**: Future contributors would otherwise keep reintroducing public/private branching into primary jobs just because those words still existed in older ids and manifests. This entry records the intended rule clearly: unless a task is explicitly about distribution, export policy, or legacy recovery, public/private should stay in the background and must not slow the main product-quality and automation lanes.

**Primary evidence**:
- `reading-companion-backend/eval/attentional_v2/ingest_library_sources.py`
- `reading-companion-backend/eval/attentional_v2/build_private_library_supplement.py`
- `reading-companion-backend/tests/test_source_intake.py`
- `reading-companion-backend/tests/test_private_library_supplement.py`
- `README.md`
- `docs/current-state.md`
- `docs/tasks/registry.md`
- `docs/implementation/new-reading-mechanism/dataset-platform-closed-loop.md`
- `docs/implementation/new-reading-mechanism/question-aligned-case-construction.md`

## Entry 43
**ID**: DEC-046
**Status**: active

**Decision / Inflection**: Land the dataset-platform controller as a scratch-safe bounded closed loop first, and keep the full unattended multi-iteration scheduler deferred until real scratch runs validate the new construction artifacts.

**Period**: Late March 2026, after question-aligned case construction had landed in code and the next practical problem became how to automate build-review-import work without touching live benchmark truth prematurely.

**Problem**: The project wanted to move quickly toward full dataset automation, but the new question-aligned builder was still fresh and the live `v2` review-truth datasets remained valuable feedback truth. A direct jump to a fully unattended multi-iteration scheduler would have mixed two risks together at once: weak semantic construction and unbounded control-loop behavior. The system needed a way to validate end-to-end build-review-import automation safely, without overwriting live manifests or live dataset ids.

**Alternatives considered**: Keep automation at the design-doc level only until every later scheduler detail was specified, let the new builder write directly into the live dataset ids and tracked manifests during validation, or build an entirely separate parallel builder instead of refactoring the current managed supplement path.

**Why this path won**: The safest fast path was a bounded scratch-safe controller. The existing managed supplement builder now resolves a run-scoped namespace when asked, so scratch validation runs can write manifests and build artifacts under `state/dataset_build/build_runs/<run_id>/` while still using normal local dataset package conventions through unique scratch dataset ids. The new `run_closed_loop_benchmark_curation.py` controller then reuses the proven packet-review machinery instead of replacing it: initial candidate review is exported with `--only-unreviewed`, bounded repair reuses `run_dataset_review_pipeline.py`, and the run stops with a final summary instead of silently crossing into promotion or cutover decisions.

**What changed in the system**: `reading-companion-backend/eval/attentional_v2/build_private_library_supplement.py` now has a reusable scratch-safe mode with run-scoped ids, manifests, and build summaries. `reading-companion-backend/eval/attentional_v2/run_closed_loop_benchmark_curation.py` plus the root `make closed-loop-benchmark-curation` surface now orchestrate the first bounded closed loop: construct scratch datasets, export initial review packets, audit, adjudicate, import, optionally run one repair wave, refresh the queue summary, and emit a final stop-and-summarize report. The task registry and current-state docs now treat this as an active dataset-platform lane rather than a purely queued future idea.

**Why it matters later**: Future contributors might otherwise assume the only meaningful automation step was a final always-on unattended scheduler. This entry records the intended staging clearly: first prove the question-aligned builder and bounded controller on isolated scratch runs, then widen the scheduler only after real evidence shows the new artifacts are trustworthy enough to automate aggressively.

**Primary evidence**:
- `reading-companion-backend/eval/attentional_v2/build_private_library_supplement.py`
- `reading-companion-backend/eval/attentional_v2/run_closed_loop_benchmark_curation.py`
- `reading-companion-backend/tests/test_private_library_supplement.py`
- `reading-companion-backend/tests/test_closed_loop_benchmark_curation.py`
- `README.md`
- `docs/current-state.md`
- `docs/tasks/registry.md`
- `docs/tasks/registry.json`
- `docs/implementation/new-reading-mechanism/question-aligned-case-construction.md`
- `docs/implementation/new-reading-mechanism/dataset-platform-closed-loop.md`
- `docs/implementation/new-reading-mechanism/execution-tracker.md`

## Entry 44
**ID**: DEC-047
**Status**: active

**Decision / Inflection**: Treat the dataset builder as a bounded enabling system, and make frozen-slice comparison cadence the rule that pulls the project back to the main evaluation goal.

**Period**: Late March 2026, after the question-aligned builder and bounded closed-loop controller had both landed and the main project risk shifted from missing infrastructure to infrastructure drift.

**Problem**: The repo now had real dataset-platform capabilities: managed source intake, question-aligned case construction, packetized review, and a scratch-safe controller. But those wins created a new risk. Without an explicit strategy rule, the project could keep refining the builder, packet audits, and automation breadth indefinitely, while decisive mechanism-eval lanes such as durable-trace / re-entry and runtime viability stayed queued. The original goal is still cross-mechanism judgment and a stronger reading mechanism, not a perpetually improving builder.

**Alternatives considered**: Keep treating builder progress as the implicit main mission until the dataset felt "good enough," force an immediate stop to dataset-platform work regardless of unresolved benchmark blockers, or leave the balance as an informal chat-only norm instead of writing it into the docs.

**Why this path won**: The best tradeoff was to keep dataset-platform work but bound it tightly. Builder and packet-hardening work remain necessary whenever they remove a specific evaluation blocker or shorten time-to-next-comparison, but they are no longer allowed to expand by default. Once a benchmark slice is good enough for diagnosis, the next move is frozen-slice comparison cadence rather than another open-ended builder wave. This also preserves the distinction between "good enough for diagnosis" and "good enough for final cutover confidence."

**What changed in the system**: The stable evaluation methodology now says explicitly that dataset building, dataset hardening, and automation are enabling lanes rather than independent success targets. The dataset-platform implementation docs now describe the current work as bounded hardening focused only on callback-bridge excerpt shaping and same-input audit/adjudication reproducibility. Current-state and task-routing docs now say the next default move after one bounded repair wave is to freeze a slice and hand comparison cadence back to the mechanism-eval lane, while durable-trace / re-entry and runtime-viability work remain visible as decisive pending evaluation lanes.

**Why it matters later**: Future contributors might otherwise see the large amount of dataset-platform infrastructure and assume the project was still primarily trying to perfect the builder before resuming evaluation. This entry records the intended discipline clearly: infrastructure exists to serve mechanism comparison, and frozen-slice comparison cadence is the rule that prevents infrastructure drift.

**Primary evidence**:
- `docs/backend-reader-evaluation.md`
- `docs/current-state.md`
- `docs/tasks/registry.md`
- `docs/tasks/registry.json`
- `docs/implementation/new-reading-mechanism/dataset-platform-closed-loop.md`
- `docs/implementation/new-reading-mechanism/execution-tracker.md`

## Entry 45
**ID**: DEC-048
**Status**: active

**Decision / Inflection**: Replace the older broad `40 / 40` formal benchmark as the active Phase 9 benchmark pointer with a four-chapter clustered benchmark v1, and treat the older broad freeze as historical evidence only.

**Period**: Early April 2026, after the eval scope had already been reduced to three north-star dimensions and the project had enough builder/review infrastructure to stop widening blindly.

**Problem**: The project still needed serious mechanism evidence, but the broad formal benchmark shape was too slow for fast iteration. Too many excerpt judgments were effectively paying for whole-chapter reads one at a time across a wide book spread. That made the path back to the next mechanism decision too slow, while also encouraging continued dataset growth as a substitute for evaluation. The project needed a benchmark shape that stayed honest and reviewable but got much more value out of each chapter read.

**Alternatives considered**: Keep the broad formal freeze as the active benchmark and simply rerun it more patiently, keep expanding the broad benchmark until it felt unquestionably large enough, or hand-design a brand-new review stack just for clustered evaluation instead of reusing the existing builder and packet-review machinery.

**Why this path won**: The clustered shape makes one chapter read support many excerpt judgments, which is exactly the right tradeoff under the current time and cost posture. Four carefully chosen chapters preserve language balance and meaningful pressure variety while making the benchmark far more iteration-friendly and easier to explain in an interview. Reusing the existing question-aligned builder, audit, adjudication, and import pipeline also keeps the system legible: the change is in benchmark shape and clustered duplicate control, not in inventing a second review universe.

**What changed in the system**: The active benchmark pointer now lives in `attentional_v2_clustered_benchmark_v1_draft.json` plus `clustered-benchmark-v1-draft.md`. The builder gained clustered mode with explicit chapter whitelisting, multiple same-profile cases per chapter, stronger same-chapter dedup rules, and ranked same-profile ids such as `__seed_1` and `__reserve_1`. The excerpt comparison runner now defaults to the clustered manifest. The earlier broad formal freeze remains preserved in the repo, but the later formal decisive chapter/excerpt jobs were abandoned once the active pointer changed. A real smoke build over the four chosen chapters produced `24 + 24` primary candidates and `8 + 8` reserves, and the first bilingual review wave was launched directly from that clustered scratch output.

**Why it matters later**: Future contributors will otherwise see both the broad formal freeze and the clustered benchmark and wonder whether the latter was just an experiment. This entry records that the swap was deliberate. The active benchmark is now optimized for fast iteration and interview-legible mechanism evidence, while the broader formal freeze remains as recoverable historical evidence rather than as the live decision surface.

**Primary evidence**:
- `reading-companion-backend/eval/manifests/splits/attentional_v2_clustered_benchmark_v1_draft.json`
- `docs/implementation/new-reading-mechanism/clustered-benchmark-v1-draft.md`
- `reading-companion-backend/eval/attentional_v2/question_aligned_case_construction.py`
- `reading-companion-backend/eval/attentional_v2/build_private_library_supplement.py`
- `reading-companion-backend/eval/attentional_v2/run_excerpt_comparison.py`
- `reading-companion-backend/state/dataset_build/build_runs/clustered_benchmark_v1_smoke2_20260403/build_summary.json`
- `docs/current-state.md`
- `docs/tasks/registry.md`
- `docs/tasks/registry.json`

## Entry 46
**ID**: DEC-049
**Status**: active

**Decision / Inflection**: Rejudge long-span source fit before freezing accumulation v1, and prefer genuinely continuous books plus compact note-backed windows over topical collections or weakly connected essay/talk surfaces.

**Period**: April 4, 2026, after the first accumulation review packet returned `0 keep / 10 revise / 8 drop`.

**Problem**: The first bounded long-span draft had enough harness support to run, but it still mixed good and bad source/window choices. The review packet showed a pattern that was too strong to ignore: many failures were not “the mechanism cannot accumulate,” but “this window does not actually carry forward one live thread.” `纳瓦尔宝典` windows fragmented into topical advice blocks, and the current `走出唯一真理观` window kept topic-shifting inside one chapter. If the project had simply repaired judge wording on top of that old window set, it would have locked a weak accumulation surface into Phase 9.

**Alternatives considered**: Keep the old six-window draft and only tweak probe wording, widen immediately to a fresh English long-span builder wave around new books such as `Shoe Dog`, or pause long-span work until a perfect broad benchmark existed.

**Why this path won**: The project needed a bounded but honest middle path. It now keeps only window/source pairs that are already materializable from current reviewed excerpt support and aligned human notes, while demoting the clearly weak source-fit windows. That preserves momentum and runtime efficiency without pretending the old draft was sound. The first reserve for later widening is now `shoe_dog_private_en`, but it stays a reserve because adding it cleanly would require new excerpt/window support construction rather than a small repair.

**What changed in the system**: `attentional_v2_accumulation_benchmark_v1` now rebuilds around six rejudged windows:
- `supremacy_private_en__13`
- `steve_jobs_private_en__17`
- `value_of_others_private_en__8_10`
- `xidaduo_private_zh__13_15`
- `huochu_shengming_de_yiyi_private_zh__8`
- `huochu_shengming_de_yiyi_private_zh__13_16`

The old active windows `nawaer_baodian_private_zh__wealth`, `nawaer_baodian_private_zh__judgment`, and `zouchu_weiyi_zhenliguan_private_zh__14` are demoted from long-span v1. The accumulation builder also now emits cleaner single-vs-cross-chapter judge focus and non-duplicative prior-context payloads before the rebuilt first-review lane runs again.

**Why it matters later**: Future contributors could easily look at the old packet and conclude only that “accumulation is hard.” This entry preserves the more useful lesson: long-span evaluation depends heavily on source/window fit, and a good accumulation surface often comes from compact multi-chapter continuity or one genuinely long chapter, not from whatever text happened to already be in a benchmark.

**Primary evidence**:
- `reading-companion-backend/eval/review_packets/archive/accumulation_benchmark_v1_probe_first_review_20260404/dataset_review_pipeline_summary.json`
- `reading-companion-backend/eval/review_packets/archive/accumulation_benchmark_v1_probe_first_review_20260404/llm_review_report.md`
- `reading-companion-backend/eval/attentional_v2/accumulation_benchmark_v1.py`
- `reading-companion-backend/eval/manifests/splits/attentional_v2_accumulation_benchmark_v1_draft.json`
- `docs/current-state.md`
- `docs/tasks/registry.md`
- `docs/tasks/registry.json`
- `docs/implementation/new-reading-mechanism/execution-tracker.md`

## Entry 47
**ID**: DEC-050
**Status**: active

**Decision / Inflection**: Separate global local-ceiling configuration from per-process launch budgets, and make comparison work artifact-staged (`bundle -> judge -> merge`) so eval restarts become an explicit ETA-gated choice instead of a blunt kill-and-rerun habit.

**Period**: April 5, 2026, after the first personal-key judged excerpt rerun was already in flight and the project needed higher utilization without losing control of one-key contention.

**Problem**: The software still had two different bottlenecks mixed together. One was artificial: local target/profile ceilings were still low enough that the runtime could self-throttle far below the practical key budget. The other was structural: excerpt and accumulation comparison work still behaved like one monolithic batch, so partial progress was hard to reuse and “should we restart?” had to be argued from intuition instead of from reusable artifacts plus measured throughput.

**Alternatives considered**: Keep the low local ceilings and only tune runner-local worker flags, add a hard in-gateway RPM limiter plus a cross-process coordinator immediately, or restart the in-flight judged rerun blindly as soon as the staged runner landed.

**Why this path won**: The project needed a bounded but real lift. Raising the global ceiling removes the purely local software bottleneck. Per-process caps preserve deliberate budgeting without inventing a heavier coordinator too early. The staged runner shape then makes restart decisions concrete: bundle work, case judgments, and merge outputs can be measured and resumed independently. That lets the project use a recorded ETA gate instead of killing expensive in-flight work on hope alone.

**What changed in the system**: Local target/profile ceilings were raised substantially, while new per-process env caps now clamp `runtime_reader_default`, `dataset_review_high_trust`, and `eval_judge_high_trust` budgets per launched Python process. `run_excerpt_comparison.py` and `run_accumulation_comparison.py` now both support staged/sharded execution with explicit shard ownership, `--skip-existing`, and merge-only summary emission. Lightweight `llm_usage.json` summaries are now written for shard/run observability. A short `run_llm_capacity_probe.py` path now validates software-side concurrency without involving reader-quality judgment. The first dual-heavy excerpt smoke then established a concrete gate outcome: the new runner architecture is valid, but the in-flight old judged rerun should continue because the observed throughput gain was not large enough to overcome already-sunk work plus the recorded `90` minute restart rule.

**Why it matters later**: Future contributors will otherwise see very high local ceilings, per-process cap envs, staged comparison CLIs, and a deliberately preserved old-format run all at once and assume the posture is inconsistent. This entry records the intended rule: keep the software ceiling high, budget each launched process explicitly, make comparison work resumable by artifact, and restart only when measured ETA evidence actually justifies it.

**Primary evidence**:
- `reading-companion-backend/config/llm_targets.local.json`
- `reading-companion-backend/config/llm_profile_bindings.local.json`
- `reading-companion-backend/src/reading_runtime/llm_registry.py`
- `reading-companion-backend/src/reading_runtime/llm_gateway.py`
- `reading-companion-backend/eval/attentional_v2/run_excerpt_comparison.py`
- `reading-companion-backend/eval/attentional_v2/run_accumulation_comparison.py`
- `reading-companion-backend/eval/attentional_v2/llm_usage_summary.py`
- `reading-companion-backend/eval/attentional_v2/run_llm_capacity_probe.py`
- `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_excerpt_parallel_smoke_20260405/shards/smoke_dual_heavy/summary/llm_usage.json`
- `reading-companion-backend/eval/runs/attentional_v2/llm_capacity_probe_personal_20260405/summary/llm_usage.json`
- `docs/backend-reader-evaluation.md`
- `docs/current-state.md`
- `docs/tasks/registry.md`
- `docs/tasks/registry.json`
- `docs/implementation/new-reading-mechanism/execution-tracker.md`

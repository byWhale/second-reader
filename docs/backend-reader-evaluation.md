# Backend Reader Evaluation

Purpose: define the stable constitution for evaluating reader quality across current and future mechanisms.
Use when: aligning eval work to product purpose, choosing between reader mechanisms, deciding what belongs in stable methodology versus benchmark reports, or designing offline reader evals.
Not for: public API contract authority, runtime lifecycle semantics, prompt-text authority, or one-off benchmark conclusions.
Update when: north-star dimensions, anti-goals, taxonomy, method policy, or evaluation artifact routing materially change.

Use `docs/backend-reading-mechanism.md` for shared mechanism-platform boundaries and `docs/backend-reading-mechanisms/<mechanism>.md` for one mechanism's actual design. Use this file for the stable comparison frame that any current or future reader mechanism should be judged against. Product-purpose authority lives in `docs/product-overview.md`; this file operationalizes that purpose for evaluation rather than redefining it.

## Evaluation Constitution
- The evaluation system is product-first.
  - The reader exists to preserve a living, curious, self-propelled co-reading mind, not to maximize one local benchmark proxy.
- The evaluation system is mechanism-agnostic.
  - `section`, `subsegment`, memory packing, search, reflection, and any future reader architecture are candidate mechanisms, not protected truths.
- The evaluation system should judge outputs and runtime behavior against the product target, not defend the current implementation shape.
- A mechanism wins only if it improves the product under realistic constraints.
- A mechanism does not win just because it is elegant, locally clever, or easier to explain.
- Stable docs should preserve the constitution, the naming frame, and the benchmark/report boundary.
- Benchmark code and reviewed reports should carry the living case sets, rubrics, thresholds, and per-run evidence.
- The core question is not "is the current architecture correct?"
  - The core question is "what reader mechanism best preserves the product goal?"

## Why Reader Evaluation Exists
- Reader evaluation exists to guide optimization first and preserve evidence second.
- Its first job is to make mechanism work legible:
  - what changed
  - what "better" means for this change
  - whether the change improved the intended reader behavior
- Records still matter because they:
  - preserve baselines
  - prevent "it feels better" drift
  - make later mechanism decisions easier to explain
- A good evaluation practice should therefore support both:
  - local mechanism attribution
  - longer-term reader quality memory
- The same frame should let us compare competing architectures fairly without inventing new product definitions for each implementation.

## North Star
- Reader quality is a vector, not a single score.
- The first-class north star has two families plus one standing gate.

### Family A: `reader_character`
- `text_groundedness`
  - the reading mind stays answerable to the source text instead of drifting into free-floating cleverness
- `self_propelled_curiosity`
  - the reader moves out of genuine curiosity about the text rather than procedural obligation or generic helpfulness
- `selective_legibility`
  - the reader notices worthwhile things and expresses them in a way another person can follow
- `coherent_accumulation`
  - understanding compounds across span instead of becoming a pile of disconnected local sparks

### Family B: `reader_value`
- `insight_and_clarification`
  - the reader surfaces meaningful turns, definitions, tensions, unknown unknowns, or clarifying distinctions
- `resonance_and_delight_when_earned`
  - the reading trail can produce resonance, surprise, or intellectual echo when those effects genuinely arise from good reading
- `companionship`
  - the experience feels like reading with a mind rather than consuming a report

### Standing Gate: `runtime_viability`
- A reader mechanism must remain reliable enough to trust in realistic use.
- Quality that appears only at unrealistic fallback, latency, or cost levels is not a full product win.
- Runtime viability includes:
  - reliability and recoverability
  - fallback and timeout health
  - latency and cost acceptability
  - operational trust under realistic conditions

## Anti-Goals
- Do not collapse the product into summary optimization.
- Do not collapse the product into user-pleasing service behavior.
- Do not reward self-enclosed or text-detached thinking.
- Do not let benchmark proxies become the product.
  - More reactions, longer notes, tighter lexical overlap, or more human-like surface style are not automatic wins.
- Do not mistake a more complex mechanism for a better reader if the product result is not better.
- Naturally arising surprise and resonance are permitted and valuable.
  - The anti-goal is reducing the product to those effects as isolated targets, not their honest presence.

## What Good Means
- Product-good is the primary question.
  - Does the system preserve a genuinely curious, text-grounded co-reading mind that produces real value and remains worth trusting?
- Mechanism-good is subordinate but still important.
  - Did one internal mechanism improve the product without violating realistic constraints?
- Good evaluation should therefore avoid collapsing everything into one vague judgment such as "smarter," "more human," or "more useful."

## Evaluation Taxonomy
- Reader eval naming should continue to separate:
  - `target`
    - what mechanism or object is under evaluation
  - `scope`
    - how far the evaluation follows the effect of that target
  - `method`
    - how the judgment is produced
- This taxonomy remains stable.
- Evaluation layers and north-star dimensions shape rubric design, but they do not replace `target / scope / method` as the run-labeling frame.

### Target
- `target` names the evaluated mechanism or object, not the layer or scoring method.
- Targets are deliberately mechanism-neutral.
  - They may describe a current implementation object such as subsegment planning, or a higher-level reading behavior such as end-to-end reading.
- Targets should use stable snake_case slugs.
- Current examples:
  - `subsegment_segmentation`
  - `reaction_generation`
  - `memory_carryover`
  - `section_merge`
  - `reader_end_to_end`

### Scope
- `direct_quality`
  - evaluate the target's own direct output
- `local_impact`
  - evaluate the target's effect on the next meaningful output layer
- `system_regression`
  - evaluate the broader reader after multiple interacting changes
- Scope should follow the question we are asking, not the shape of the current pipeline.

### Method
- `deterministic_metrics`
- `pairwise_judge`
- `rubric_judge`
- `human_spot_check`

- Reports and run artifacts should record:
  - `target`
  - `scope`
  - `method`
  - dataset version
  - comparison target
  - mechanism key
  - config fingerprint
  - normalized attention trail, reactions, chapter outputs, and memory summaries when the runtime exposes them

## Evaluation Layers
- Evaluation layers are mechanism-agnostic lenses for designing rubrics and benchmark plans.
- They are not permanent claims about today's pipeline.

### End-To-End Product Fit
- Ask whether the overall reader still feels like the right kind of co-reader mind.
- This layer is where the two north-star families come together most directly.
- Use it when comparing whole architectures or major behavior shifts.

### Local Reading Behavior
- Ask whether the reader takes good passage-level reading steps.
- This can apply to any local working object:
  - a planned runtime unit
  - a local reaction
  - a fused search result
  - a non-slicing local read pass
- Typical concerns include:
  - focus
  - source anchoring
  - selectivity
  - meaningful curiosity

### Span Trajectory
- Ask whether understanding develops coherently across larger spans.
- Typical concerns include:
  - thread continuity
  - memory carry-over
  - callback quality
  - chapter or book-level arc quality

### Runtime Viability
- Ask whether the reader remains operationally healthy while pursuing quality.
- Typical concerns include:
  - fallback rate
  - timeout rate
  - invalid-structure or planner failure modes
  - latency and cost under intended usage

### Durable-Trace Audits
- Audit whether saved marks, traces, or other durable surfaces preserve enough orientation for later return.
- This includes recall and re-entry questions when they matter.
- Durable-trace quality is important, but it is a secondary audit territory rather than a first-class north-star family.
- It should not force the reader into extra recap structure when the core product surfaces already preserve position and traceability.

## Evaluation Methods
### Deterministic Metrics
- Use deterministic metrics for structure, runtime, and guardrail questions.
- Typical examples:
  - unit count
  - average unit size
  - fallback rate
  - timeout rate
  - repeated-reaction rate
- These metrics are useful for trend lines and safety checks, but they are not semantic winners by themselves.

### LLM-Led Semantic Evaluation
- `pairwise_judge` and `rubric_judge` are the default semantic tools.
- Use `pairwise_judge` when the core question is:
  - which version is better overall for this specific product question?
- Use `rubric_judge` when the core question is:
  - what exactly improved or regressed, and along which named dimensions?
- In practice, the two methods often work best together:
  - pairwise for the outcome judgment
  - rubric for the diagnostic explanation
- In this project, these methods should be treated as offline evaluators, not runtime reader agents.
- The value of the judge comes from the rubric, the matched comparison, and the product question being asked.

### Human Spot-Checking
- Human review is optional calibration, not a standing requirement for every eval.
- Human spot-checking is especially useful for:
  - validating whether a rubric still matches product intent
  - catching judge drift
  - distinguishing real regressions from defensible reading-style differences

## Fair Comparison Rules
- Compare mechanisms on the same product question whenever possible.
- Keep comparisons grounded in realistic constraints rather than unconstrained demo conditions.
- The stable methodology should not freeze exact budget-matching policy, threshold policy, or benchmark packaging into the constitution.
- Those details belong in benchmark code and reviewed reports.

## When To Evaluate
- Run local mechanism evaluation after major reader-core changes when the goal is attribution.
- Run broader regression evaluation after clusters of changes to prompts, memory, search, reflection, synthesis, or other interacting mechanisms.
- Do not wait for every mechanism to change before first evaluation.
- If evaluation is deferred too long, improvement and regression become hard to attribute.
- If a different architecture becomes plausible, evaluate it with the same north-star frame instead of inventing a new metric language for each implementation.

## Same Frame Across Mechanisms
- The same evaluation constitution should work for:
  - the current subsegment-based reader
  - a future non-slicing reader
  - a future search-heavy or reflection-heavy reader
- The mechanism may change.
- The north star, layer model, and naming frame should not need to be reinvented each time.

## Artifact Layout
- Stable methodology belongs in `docs/`.
- Reviewed, checked-in evaluation reports belong in `reading-companion-backend/docs/evaluation/`.
- Executable evaluation code belongs in `reading-companion-backend/eval/`.
- Tracked benchmark datasets belong in `reading-companion-backend/eval/datasets/`.
- Machine-generated benchmark runs belong in `reading-companion-backend/eval/runs/` and should stay out of normal runtime `state/` / `output/` paths.
- Runtime-first per-run markdown summaries may live under `reading-companion-backend/eval/runs/<benchmark>/<run_id>/summary/` until they are reviewed and promoted into `reading-companion-backend/docs/evaluation/`.
- Temporary experiment logs belong in `reading-companion-backend/docs/research/` only when they are not yet stable reports.
- Stable docs should explain the constitution, the comparison frame, and the report boundary.
- Benchmarks and reports should carry the living case sets, rubrics, thresholds, run settings, sample sizes, and per-run conclusions.
- Cross-mechanism comparison should prefer the shared normalized eval bundle emitted from the runtime boundary over direct dependence on mechanism-private runtime files.
- Normal product runs should not persist normalized comparison bundles into book output directories.
- If a runtime-backed eval explicitly asks for export persistence, the mechanism may write `_mechanisms/<mechanism_key>/exports/normalized_eval_bundle.json` for that run.

### Expectations For Evaluation Reports
- Per-run or per-change reports should state:
  - target
  - scope
  - method
  - comparison target
  - sample set
  - dataset version
  - rubric used
  - summary conclusion
  - known caveats
- This stable methodology document should not be used as a running benchmark log.

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

## Dataset Trust Model
- Evaluation should distinguish between:
  - factual dataset truth
    - source text
    - provenance
    - stable boundaries
    - split membership
    - version identity
  - benchmark judgment targets
    - why the case exists
    - what pressure it is meant to test
    - what kinds of reading behavior would count as strong, weak, or misleading
- Factual dataset truth should be reproducible and auditable.
- Benchmark judgment targets should be reviewable and improvable.
- A versioned benchmark package is not automatically gold-standard just because it is machine-valid.
- Strong evaluation practice therefore includes:
  - documented curation rationale
  - provenance manifests
  - structural validation
  - explicit case-purpose metadata
  - targeted adjudicated review for ambiguous or high-impact cases
  - when human review capacity is unavailable, multi-prompt LLM adjudication may replace manual review as the operational reviewer
- When LLM audit or adjudication rubrics use ordinal scores, the rubric contract should define the score direction explicitly and guard against impossible decision/score combinations before those payloads are treated as downstream benchmark evidence.
- When audit rubrics compress case quality into coarse bands, the normalized keep gate should not be stricter than the real benchmark-readiness intent.
  - if the intended meaning is "benchmark-usable now unless a real weak axis is present," prefer a deterministic rule such as "no weak axes and at most one adequate axis" over an "all axes must be perfect" gate that can turn a single `4 -> 3` wobble into same-input decision drift
- When multi-stage packet review uses LLM audit plus final adjudication, the final adjudicator should consume a compact structured audit summary rather than raw audit prose.
  - free-text audit notes and disagreement narratives remain useful operator evidence
  - they should not be treated as canonical adjudication input when reproducibility matters
- The final adjudicator should also see case-quality-bearing fields rather than builder workflow bookkeeping.
  - scratch ids, internal build scores, empty review-history markers, and similar workflow metadata are useful operator evidence
  - they should not be allowed to bias benchmark-readiness decisions when the question is the excerpt case itself
- When reproducibility is the question, isolate the layer that is being measured.
  - same-packet adjudication reproducibility should be measured on frozen packet inputs, for example by rerunning `auto_review_packet.py --probe-only` on an archived packet
  - same-input case-audit reproducibility should persist stable prompt inputs/fingerprints per case so later comparisons can distinguish audit-model variance from builder/input drift
  - if callback-style case validity depends on structured builder identity such as `target_profile_id`, `selection_role`, or carried `prior_context_text`, those fields should be part of the audit prompt payload rather than left as operator-only metadata
  - callback audit contracts should also say explicitly when an inline antecedent is an intentional self-containment choice rather than an automatic defect
    - otherwise same-input callback cases can wobble between `keep` and `drop` just because the audit model alternates between "traceable inline bridge" and "malformed callback" readings
  - builder-emitted excerpt, anchor, and selection-reason text should normalize invisible Unicode formatting and non-breaking whitespace before the audit layer sees it
    - otherwise a text-corruption defect can masquerade as audit-model drift even when the real issue is upstream excerpt rendering
  - if a real case-audit comparison shows `audit_input_drift = 0` while primary decisions, scores, or problem types still move materially, treat the next repair as audit-stage reproducibility hardening rather than as builder/input debugging
  - when one prompt-contract adjustment still leaves same-input audit drift materially high, a small repeated-review consensus pass is an acceptable next repair before redesigning builder inputs
    - for example, repeat the primary audit on the same pinned target and same prompt inputs, then aggregate with deterministic majority/median rules
  - when a packet already has a prior `llm_review_run`, `--probe-only` should prefer replaying that stored run's adjudication input payloads instead of regenerating them from newer compact-audit logic
  - replayed saved-input probes should still record the currently active rubric/prompt identity so later comparisons do not mistake a cross-rubric replay for same-contract evidence
  - transient quota exhaustion on the pinned target should not be treated as benchmark evidence by default
    - a bounded same-target recovery pass is acceptable before a packet-review batch finalizes `unclear` rows from quota-only failures
  - closed-loop repeats that rebuild after importing into live feedback datasets should not be treated as same-input reproducibility evidence unless the feedback inputs are frozen deliberately

## Dual Diagnosis Rule
- Every meaningful evaluation pass should inspect two possibilities:
  - the mechanism is weak
  - the dataset, case framing, or evaluation harness is weak
- Every meaningful promotion-oriented evaluation pass should also inspect a third possibility:
  - the current benchmark family is too small or too narrow to support a confident judgment
- We should not attribute a bad score to the mechanism alone unless the dataset and harness have survived the same scrutiny.
- We should also not protect the mechanism by assuming every bad result is a benchmark flaw.
- The required practice is dual diagnosis:
  - inspect the evaluation result itself
  - inspect whether the dataset, case label, case boundary, or harness design may have produced a misleading signal
- When the project is making a promotion or default-cutover decision, treat benchmark-size adequacy as an explicit gate rather than an implicit hope.
- This rule is especially important for:
  - builder-curated cases
  - new mechanism-specific buckets
  - new judge prompts or scoring contracts
  - the first serious run on a newly expanded benchmark family

## Benchmark-Size Adequacy Rule
- A benchmark family can be:
  - coverage-adequate for first serious diagnosis
  - yet still too small for final product-confidence or default-cutover judgment
- Stable evaluation practice should therefore separate:
  - first serious evaluation readiness
  - final promotion confidence
- If reviewed runs reveal that conclusions still depend too heavily on a small number of cases, narrow buckets, or thin chapter coverage, the correct next step is benchmark expansion before stronger product conclusions.
- Runtime and compatibility fixtures often reach adequacy earlier than semantic excerpt and chapter-comparison datasets.
- Reports and implementation trackers should explicitly record when:
  - the benchmark is good enough for early diagnosis
  - but not yet large enough for high-confidence cross-mechanism or default-cutover decisions

## Split-Surface Evaluation Rule
- The evaluation system may intentionally use different text surfaces for different north-star questions.
- `reader_character.selective_legibility` should usually prefer a local excerpt surface:
  - dense local pressure
  - many reusable cases per read
  - efficient comparison cadence
- `reader_character.coherent_accumulation` should usually prefer a bounded long-span surface:
  - one long chapter or one contiguous multi-chapter window
  - visible continuity, carryover, and callback pressure
  - enough span to test whether understanding compounds rather than resets
- `reader_value.insight_and_clarification` is an orthogonal output-value axis.
  - it may be scored on local excerpt cases
  - it may also be scored on long-span window cases
- Stable evaluation practice should therefore avoid forcing excerpt and long-span datasets to share the same books or chapters when that coupling weakens fit or runtime efficiency.

## Coherent-Accumulation Interpretation Rule
- `reader_character.coherent_accumulation` is not the same thing as generic whole-book memory.
- The current operational target is bounded long-span continuity and carryover:
  - does the reader keep earlier material alive across a meaningful span
  - does it connect later developments back to earlier pressure honestly
  - does understanding accumulate instead of restarting locally
- A valid accumulation case may therefore be:
  - one long chapter
  - one contiguous two-to-four chapter window
- Accumulation benchmark design should optimize for spans where:
  - arguments deepen
  - narrative consequences settle
  - callbacks matter
  - later distinctions depend on earlier reading
- Books or chapters whose sections are largely independent are poor default accumulation surfaces even if they remain strong local excerpt surfaces.

## Long-Span Probe Grounding Rule
- A long-span accumulation probe is benchmark-ready only when the later anchor explicitly carries forward earlier material.
- Shared theme alone is not enough.
- Strong long-span probes usually show at least one of:
  - a callback or textual echo
  - a consequence or resolution of an earlier tension
  - a later distinction that depends on earlier setup
  - a concrete continuation of one narrative or argumentative state
- If the reader would have to supply most of the connection by outside inference, the probe should be treated as weak or ambiguous rather than as true accumulation evidence.
- When a window only yields `1-2` such probes, freeze honestly short instead of forcing a third weaker probe.

## Active Benchmark Pointer Rule
- Stable docs may name one active benchmark pointer while keeping earlier benchmark packages as historical evidence.
- An active benchmark does not need to maximize breadth if the current project constraint is iteration speed under real token and time pressure.
- A chapter-clustered benchmark is acceptable when it improves time-to-next-comparison by letting one chapter read support multiple excerpt judgments.
- The clustered shape should still be explicit and reviewable:
  - selected chapters must be named directly
  - excerpt and reserve quotas must be documented
  - the active benchmark doc must say clearly whether excerpt membership is still draft, partial, or frozen
- Historical broad freezes should remain readable, but they should not keep acting as the active benchmark pointer once a deliberate replacement has been recorded.

## Bounded Dataset-Platform Strategy Rule
- Dataset building, dataset hardening, and dataset automation are enabling lanes for evaluation, not independent success targets.
- Once a benchmark family is good enough for diagnosis, the default next move is frozen-slice comparison rather than open-ended builder refinement.
- A builder or packet-review hardening change should continue only when it improves at least one of:
  - question coverage
  - benchmark trust or reproducibility
  - discriminative power between mechanisms
  - time-to-next-comparison
- Decisive evaluation lanes such as durable-trace / re-entry and runtime viability must remain visible and must not be postponed indefinitely by general builder work.
- Stable evaluation practice should therefore separate two states clearly:
  - builder work that is still removing a specific evaluation blocker
  - comparison cadence that has resumed on a frozen slice after that blocker is bounded
- Reports and implementation trackers should record when the project has crossed from bounded hardening back into frozen-slice comparison so later work does not mistake infrastructure refinement for the main evaluation goal.

## Chapter-Presence Interpretation Rule
- Judged chapter-core comparisons should separate:
  - lower-volume but cumulative interpretive threading
  - sparse late cherry-picking
- A mechanism should not be penalized merely for producing fewer reactions if those reactions stay on one live interpretive axis and compound honestly across the chapter.
- A mechanism also should not be credited for a few plausible late reactions when it misses the opening pressure, never establishes chapter presence, or leaves the judge doubting chapter alignment.
- When a judged result turns on this distinction, the closeout should record both:
  - whether the mechanism sustained one coherent chapter-level thread
  - whether it maintained enough early and mid-chapter contact to make that thread trustworthy

## Parallel Eval Execution Rule
- Evaluation throughput may improve by parallelizing independent work, but parallelism must not change what is being judged.
- When offline lanes are isolated and parallelism does not change the judgment semantics, prefer running them in parallel rather than serializing them by habit.
- Unnecessary serialization is discouraged for long-running dataset-building, cleanup, and evaluation work.
  - prefer sequencing only when there is a true dependency, a shared destructive write, or a decision-bearing quality risk
- Safe parallel evaluation examples include:
  - running different mechanisms for the same case in isolated processes and isolated output directories
  - running independent judge scopes over the same completed artifacts
- Unsafe parallel evaluation includes:
  - shared mutable artifact paths between concurrently running mechanisms
  - parallel execution that changes prompt content, evidence packaging, or judgment order in a way that affects the meaning of the result
- When full mechanism bundles contain lifecycle or operational noise that is not part of the quality question, a judged rerun may use a judge-only evidence filter.
  - for example, chapter comparison may filter `parse`, `waiting`, `error`, `transition`, `segment_complete`, and `chapter_complete` out of the judge-facing bundle while preserving the full bundle on disk
  - keep this as a prompt-input control, not a destructive rewrite of the underlying mechanism artifacts
- Same-key parallel LLM usage is allowed when the configured provider and profile concurrency support it.
  - multiple API keys are not required for basic parallelism
  - extra keys mainly help with throughput headroom, failover, or rate-limit resilience
- When multiple heavy jobs share one provider/profile budget, set explicit per-job worker caps instead of letting each job assume it owns the full shared budget.
- Heavy comparison runners should support a staged shardable workflow instead of one monolithic all-or-nothing pass.
  - preferred shape:
    - `bundle -> judge -> merge`
  - the bundle stage should read each chapter/window once per mechanism and persist a normalized reusable bundle
  - the judge stage should consume only completed bundles, preserve per-case or per-probe failure isolation, and allow `skip-existing` resume behavior
  - the merge stage should be the only stage that writes the final aggregate/report outputs
  - shard ownership should stay explicit so two processes never write the same `(unit, mechanism)` or final summary concurrently
- Offline comparison runs should emit lightweight LLM-usage summaries in addition to product-judgment outputs.
  - minimum useful fields include request counts, retries, approximate RPM, inflight estimates, gate-wait time, quota-wait time, and shard/profile/mechanism breakdowns
  - this observability exists to diagnose software bottlenecks and launch posture, not to become a new benchmark target
- New scaling work should target the shared `src/reading_runtime/` LLM registry and gateway layer rather than adding new mechanism-local provider clients.
- Structured registry configuration is preferred over legacy environment compatibility when tuning concurrency, key pools, or failover because it makes those choices explicit and reviewable.
  - the recommended local operator surface is now the split target catalog plus profile-binding pair under `reading-companion-backend/config/llm_targets.local.json` and `reading-companion-backend/config/llm_profile_bindings.local.json`
  - the profile-binding file should prefer ordered `target_tiers` over one hardcoded target plus ad hoc fallback fields
  - those two local files still compile into one shared backend registry and one shared gateway policy surface
  - the shared gateway now chooses one concrete target when a runtime, dataset-review, or evaluation scope starts and keeps that target pinned for the whole scope
  - cross-target or cross-model fallback is allowed only when a new scope starts; the gateway should not mix models/providers mid-run
- New eval/review runners should default to shared-policy worker counts instead of hardcoded local worker limits.
  - case-level fanout is preferred when cases are independent
  - deterministic artifact ordering must still be preserved in final summaries and reports
- Decisive eval runners should isolate case-level mechanism, provider, and harness failures instead of aborting the whole lane on the first broken case.
  - preserve per-case failure payloads explicitly
  - still emit aggregate/report outputs from the cases that did complete
  - treat a run with no aggregate/report as harness failure, not as usable evaluation evidence
- Global derived artifacts should be coordinated explicitly during concurrent work.
  - packet-local and run-local artifacts should stay owned by each job
  - shared summaries should usually be refreshed once after concurrent imports or job completions finish
- The shared gateway now owns adaptive same-key concurrency for new processes.
  - the provider-wide gate starts from a configured initial limit, backs off on sustained timeout/rate-limit or malformed-response pressure, and recovers slowly after clean windows
  - profile-level default worker sizing should follow the current stable shared budget rather than guessing a fixed number like `1` or `2`
- If a judged lane completes with aggregate/report files but every case is `mechanism_unavailable` because provider cooldown or quota wait-budget exhaustion, treat the run as harness failure rather than mechanism evidence.
  - zero-score ties from `mechanism_unavailable` fallback payloads are not valid comparison results
  - the correct next move is a quota-safe rerun, not product interpretation

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

## Mechanism Pattern Capture Rule
- Evaluation should preserve both:
  - positive adoption candidates
    - behaviors, design choices, prompt shapes, retrieval choices, control heuristics, or representation choices that proved genuinely strong
  - negative anti-patterns
    - failure modes, brittle shortcuts, misleading reaction habits, weak retrieval patterns, or benchmark-triggered regressions we do not want to repeat
- We should not treat a comparison run as finished once it only names the winner.
- Every meaningful cross-mechanism or repair-oriented evaluation pass should try to answer four questions:
  - what worked well in mechanism A
  - what worked well in mechanism B
  - what failed in mechanism A
  - what failed in mechanism B
- Positive findings should be treated as portable design candidates rather than as property of one mechanism forever.
  - The later goal is not to keep a permanent winner/loser story.
  - The later goal is to extract the best preserved behaviors into a stronger reader.
- Negative findings should be preserved as explicit anti-pattern memory rather than left as one-off chat conclusions.
  - This helps prevent repeating the same mistakes during later prompt, retrieval, memory, or controller redesigns.
- The stable rule is:
  - stable methodology docs define the capture requirement
  - a living ledger tracks concrete strengths, adoption candidates, anti-patterns, and evidence links
  - decision-bearing adoptions or rejections should eventually be promoted into stable mechanism docs or the decision log
- A useful ledger entry should record at least:
  - source mechanism
  - pattern kind: `strength`, `adoption_candidate`, `failure_mode`, or `anti_pattern`
  - concise description
  - why it mattered
  - likely contributing causes
  - evidence links
  - adoption status
  - next action or explicit defer reason

## Evaluation-To-Implementation Rule
- A meaningful evaluation round is not complete once it only:
  - produces scores
  - names a winner
  - writes findings into a ledger
- After each meaningful evaluation, the project should also investigate:
  - what specifically contributed to the result
  - which factors are likely causal rather than decorative
  - which findings deserve immediate mechanism action
  - which findings should be explicitly deferred and why
- The required closeout is:
  - evaluation result
  - causal interpretation
  - selective implementation plan
- The goal is not to let valuable findings accumulate as an unworked pile for a hypothetical later rewrite.
- The goal is to keep evaluation and mechanism improvement in a live loop:
  - evaluate
  - explain the result
  - choose a small number of high-value actions
  - implement or explicitly defer them
  - rerun to see whether the change really helped
- A round may legitimately defer a finding, but deferment must be explicit.
  - acceptable examples:
    - benchmark still too small
    - the finding conflicts with the approved mechanism framework
    - another repair has higher priority
    - the finding still lacks causal confidence
- When presenting an evaluation result to the user, the default closeout should include:
  - what the result was
  - what likely contributed to it
  - what selective improvement strategy follows from it
- The only time to omit the strategy is when the user explicitly asks for interpretation only.

## Selective Synthesis Rule
- We should not combine mechanism strengths mechanically.
- Good synthesis means:
  - preserve the approved mechanism's overall framework and control shape
  - import only the parts that genuinely improve the target behavior
  - avoid copying surface reactions or prompt style without matching structural support
- Positive findings should therefore be filtered into three buckets:
  - `adopt_now`
    - small, high-confidence improvements that fit the current approved mechanism cleanly
  - `defer_for_later_synthesis`
    - valuable ideas that need a broader redesign, more evidence, or a different mechanism phase
  - `reject_as_misaligned`
    - locally appealing behavior that would distort the approved mechanism's design or product target
- The filter question is not:
  - "can we copy this good-looking behavior?"
- The filter question is:
  - "does this behavior improve the approved mechanism while respecting its ontology, loop, memory shape, and control strategy?"
- Negative findings should be handled with the same seriousness.
  - preserve them as explicit anti-pattern memory
  - check whether any proposed repair risks reintroducing them
  - do not repeat a known failure just because it worked in a different local context

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
  - the reader surfaces meaningful turns, definitions, tensions, unknown unknowns, clarifying distinctions, or cross-text connections that are genuinely enabled by strong reading plus broad prior knowledge
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
  - Does the system preserve a genuinely curious, text-grounded co-reading mind that produces real value, makes good use of broad prior knowledge without drifting away from the text, and remains worth trusting?
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

### Current Operational Review Rule
- Until explicitly reversed in the docs, benchmark-case hardening should default to multi-prompt LLM adjudication rather than manual packet review.
- The minimum independent review shape for current dataset hardening is:
  - primary case-design review
  - adversarial disagreement review
  - final adjudication review with a separate prompt role
- Packet-level case audits should remain traceable while they run.
  - packet-level `run_state.json` should expose status and progress
  - per-case state artifacts should expose the active stage
  - partial summaries should be written before the whole packet finishes so slow judge calls do not look like silent failure
- Packet-level case audits should not treat schema-valid placeholder payloads as trustworthy evidence.
  - if a primary or adversarial review normalizes into the audit runner's explicit unavailable sentinel shape, the runner should retry that stage
  - if the stage still cannot produce a usable payload after bounded retries, the audit run should fail clearly instead of flowing placeholder review content into downstream adjudication or import
- Case-level parallelism is acceptable for packet audits when:
  - primary and adversarial review remain ordered inside each case
  - concurrency stays bounded by the backend LLM semaphore or a stricter packet-local limit
  - queue/reporting artifacts still distinguish `running`, `completed`, and `incomplete` audit runs honestly
- This rule exists to keep dataset hardening executable even when human review capacity is limited.
- Manual human review remains valuable, but it is optional escalation for later higher-trust promotion work rather than a default blocker for current packet review tasks.

### Judge Model Policy
- Judge quality and runtime-reader cost should be treated as different concerns.
- The project may therefore use different model profiles for:
  - live runtime reading
  - dataset hardening / packet review
  - evaluation judging
- Those profiles should be resolved through one shared backend provider registry rather than ad hoc per-script model config.
  - operators should therefore edit named targets separately from profile bindings instead of hardcoding URL/model/key choices into each task runner
- Default policy:
  - dataset hardening and evaluation judging should prefer the strongest trustworthy pinned model profile available
  - live runtime reading may prefer a cheaper/stabler pinned model profile when book-scale cost and throughput matter
- Operational failover and semantic model choice must not be conflated.
  - rotating across keys for the same provider/model profile is an operational fallback
  - switching to a different model family is a semantic change
- For benchmark trust and comparability:
  - one packet review run should pin one primary judge model profile
  - one evaluation run should pin one primary judge model profile
  - do not silently mix different model families inside one packet review run or one evaluation run
- Cross-model review is still valuable, but it should be explicit and selective.
  - use a second strong model family mainly for disagreement, adjudication, or high-impact spot checks
  - do not require multi-model judging on every routine case if it would make the workflow too expensive or too noisy

### Shared LLM Invocation Boundary
- Project-owned prompt-to-provider calls should flow through one shared backend invocation layer.
- That shared layer should own:
  - provider-contract adaptation
  - key-pool failover within the same pinned model family
  - task-level profile resolution
  - retry and concurrency policy
  - standard/debug trace emission
- Silent cross-model switching inside one packet review run or one evaluation run is not allowed.
- Eval reports should be able to recover which provider/model profile actually judged the run from the trace artifacts.

### Background Eval Job Tracking
- Long-running offline evaluation and dataset jobs should be tracked durably instead of relying on one agent's chat memory.
- The canonical source of truth is:
  - `reading-companion-backend/state/job_registry/jobs/<job_id>.json`
- The operator-facing mirrors are:
  - `reading-companion-backend/state/job_registry/active_jobs.json`
  - `reading-companion-backend/state/job_registry/active_jobs.md`
  - these mirrors should contain only still-active jobs, not completed or failed historical records
- Terminal jobs should be archived into:
  - `reading-companion-backend/state/job_registry/history_jobs.jsonl`
- Register a job when:
  - the run is expected to last longer than roughly `10-15` minutes
  - the output matters enough that another agent may need to resume, inspect, or avoid duplicating it later
- Default generic launch path:
  - use `reading-companion-backend/scripts/run_registered_job.py` so plain eval/dataset commands can stay registry-agnostic
  - keep explicit status-file updates only for custom orchestrators that need richer multi-phase control
- Each registered job should record at least:
  - `job_id`
  - `domain`
  - `task_ref`
  - `lane`
  - `purpose`
  - `command`
  - `cwd`
  - `pid`
  - `log_file`
  - `run_dir` when the job owns a primary output directory
  - `status_file` when the job exposes richer phase detail
  - `expected_outputs` and/or `check_command` so completion can be inferred without a status file
  - `next_check_hint`
  - `decision_if_success`
  - `decision_if_failure`
  - `status`
- Before starting a new long-running evaluation or dataset task, refresh the registry first so overlapping work does not silently duplicate or overwrite in-flight runs.
- `abandoned` should now be rare.
  - use it only when a job is genuinely orphaned or ambiguous
  - if the process is gone but outputs/checks show success, infer `completed` even without a status file
- Product reading jobs now share the same canonical registry.
  - `state/jobs/<job_id>.json` remains a compatibility shadow during the migration window rather than the primary source of truth

## Observability Posture For Evaluation
- Default evaluation should rely on `standard` observability first.
  - Standard mode should preserve enough runtime history for trustworthy resume, durable trace audits, and baseline cross-mechanism comparison.
- `debug` observability is for diagnosis, not for defining the baseline benchmark requirement.
  - Candidate traces, controller forensics, prompt diagnostics, and other deep internal records are useful when explaining regressions or tuning a mechanism, but they should remain optional.
- A mechanism should not need debug mode just to be legible in normal evaluation.
  - If baseline evaluation only works when deep diagnostics are on, the standard trace is too thin.
- Conversely, stable evaluation should not require every normal product run to persist full controller forensics.
  - The benchmark/report layer may opt into debug runs when needed for attribution or failure analysis.

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

## Stable Evaluation Questions
- These are the stable question families that any serious reader-mechanism evaluation should be able to answer.
- They are intentionally question-shaped rather than dataset-shaped.
- Exact case sets, thresholds, and benchmark packaging belong in benchmark code, reviewed reports, or temporary implementation docs.

### Cross-Mechanism Product Questions
- `whole_reader_product_fit`
  - Under realistic constraints, which mechanism better preserves the product's intended co-reading mind?
- `local_reading_behavior`
  - Which mechanism takes better passage-level reading steps when faced with the same source text?
- `span_trajectory`
  - Which mechanism accumulates understanding more coherently across a larger span such as a chapter?
- `durable_trace_and_reentry`
  - Which mechanism leaves behind a more useful trail for later return, recall, and re-entry?
- `runtime_viability_and_compatibility`
  - Which mechanism remains more operationally trustworthy and integration-safe while pursuing product quality?

### Mechanism-Specific Attribution Questions
- Stable evaluation may also ask whether one mechanism is actually honoring its own distinctive promises.
- These questions are still evaluated under the same north-star frame, but they do not need to be symmetrical across all mechanisms.
- Mechanism-specific questions should live in the relevant mechanism doc plus temporary working docs when they are still being operationalized.

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
- Tracked corpus manifests and local-source reference files belong in `reading-companion-backend/eval/manifests/`.
- Local-only evaluation packages derived from private or copyrighted books belong in `reading-companion-backend/state/eval_local_datasets/`.
- Machine-generated benchmark runs belong in `reading-companion-backend/eval/runs/` and should stay out of normal runtime `state/` / `output/` paths.
- Runtime-first per-run markdown summaries may live under `reading-companion-backend/eval/runs/<benchmark>/<run_id>/summary/` until they are reviewed and promoted into `reading-companion-backend/docs/evaluation/`.
- Temporary experiment logs belong in `reading-companion-backend/docs/research/` only when they are not yet stable reports.
- Stable docs should explain the constitution, the comparison frame, and the report boundary.
- Benchmarks and reports should carry the living case sets, rubrics, thresholds, run settings, sample sizes, and per-run conclusions.
- Cross-mechanism comparison should prefer the shared normalized eval bundle emitted from the runtime boundary over direct dependence on mechanism-private runtime files.
- When a mechanism can expose richer comparison truth without breaking the shared bundle shape, additive fields such as locus, anchor, or lineage context are preferred over flattening everything back into older section-era semantics.
- Normal product runs should not persist normalized comparison bundles into book output directories.
- If a runtime-backed eval explicitly asks for export persistence, the mechanism may write `_mechanisms/<mechanism_key>/exports/normalized_eval_bundle.json` for that run.
- Tracked benchmark datasets remain the source of truth for benchmark inputs.
  - Conceptually, one benchmark family may span more than one storage mode.
  - The difference between `tracked` and `local-only` is packaging and portability, not evaluation meaning.
  - Excerpt-case datasets may carry the excerpt text they need directly.
  - End-to-end chapter/book comparisons should use an intentional evaluation corpus rather than ad hoc runtime `output/` or `state/uploads/` files.
  - User uploads and runtime book copies should only enter the benchmark corpus after explicit promotion and screening.
  - The operator-facing intake territory for future benchmark-source additions is `reading-companion-backend/state/library_inbox/`.
  - The durable local source-library territory for that screening flow is `reading-companion-backend/state/library_sources/`.
  - The durable dataset-platform catalog / run-summary territory for that flow is `reading-companion-backend/state/dataset_build/`.
  - When the source books are private or copyrighted, keep the text-bearing package in `reading-companion-backend/state/eval_local_datasets/` and point to it through tracked manifests instead of checking that package into the repo.

## Dataset Organization Rules
- Organize benchmark inputs by evidence family first, not by whichever mechanism happens to be under active development.
- Organize benchmark inputs by evaluation-relevant structure, not by book-acquisition history.
  - benchmark stratification may use dimensions such as target pressure, language, reading role, genre/book type, or chapter/excerpt scale
  - benchmark stratification must not use source-origin labels such as `public`, `private`, `manual download`, or `agent-downloaded` as if they were product-meaningful categories
- The primary tracked dataset families under `reading-companion-backend/eval/datasets/` are:
  - `excerpt_cases/`
  - `chapter_corpora/`
  - `runtime_fixtures/`
  - `compatibility_fixtures/`
- The same benchmark family may also have `storage_mode = local-only` packages under `reading-companion-backend/state/eval_local_datasets/` when the package contains private or copyrighted source text.
- Keep English and Chinese as separate language tracks.
  - Use `en` and `zh` package tracks for language-bound datasets.
  - Use `shared` only when a dataset is intentionally language-agnostic.
- Each concrete dataset package should live in its own directory under the correct family root.
- Each concrete dataset package must include:
  - `manifest.json`
  - one primary payload file such as `cases.jsonl`, `chapters.jsonl`, or `fixtures.jsonl`
- Tracked corpus/source metadata should not be mixed into the dataset package itself.
  - Put source-book inventories, corpus-selection manifests, split manifests, and local-path references under `reading-companion-backend/eval/manifests/`.
- The local-only mirror should keep the same family roots and package contract so tracked and local packages stay comparable as one benchmark family.
- Machine-generated run output must stay under `reading-companion-backend/eval/runs/`, never inside tracked dataset packages.
- Detailed package naming and payload-shape rules may evolve in repo-local READMEs and benchmark code, but the family-first plus separate-language-track structure is the stable rule.

### Storage Mode Rule
- Every benchmark package should be thought of as belonging to one benchmark family first.
- `storage_mode` only answers:
  - can this package live in the tracked repo dataset tree?
  - or must it stay in the local-only mirror?
- Use:
  - `tracked`
    - for repo-safe packages under `reading-companion-backend/eval/datasets/`
  - `local-only`
    - for packages kept under `reading-companion-backend/state/eval_local_datasets/`
- Do not let `storage_mode` create a fake conceptual split based on source origin when the evaluation question and package role are the same.
- Do not let source-origin metadata create a fake conceptual split either.
  - whether a book was downloaded manually, obtained by the agent, or happens to be open-access is provenance/compliance metadata only
  - those facts may matter for storage, distribution, and repo-check-in policy
  - they do not define different reader-value categories and should not be used as benchmark strata by default

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

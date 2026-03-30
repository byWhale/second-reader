# Question-Aligned Case Construction

Purpose: define the concrete Phase 2 design for building evaluation cases, datasets, and fixture inputs from managed books without relying on coarse fixed-window heuristics.
Use when: implementing the next dataset-platform phase, designing evaluation-case generation, or deciding what the unattended loop should depend on.
Not for: final benchmark decisions, public API behavior, or one-off case review outcomes.
Update when: the case-construction artifacts, target-profile model, adequacy scoring, or loop handoff contract changes.

## Why This Phase Exists
- The project already has strong machinery for:
  - managed source intake
  - canonical parsing
  - source screening
  - dataset packaging
  - packetized audit, adjudication, import, and archive
- The weakest current layer is the semantic construction of evaluation cases.
- The current excerpt builder still leans too much on:
  - fixed windows inside otherwise good chapters
  - role-based bucket preference tables
  - coarse position heuristics such as early/middle/late chapter placement
- That is not strong enough for the current product and evaluation goal:
  - create cases that answer explicit reader-evaluation questions
  - expose meaningful mechanism differences
  - remain judgeable, reviewable, and replaceable

## Naming
- Phase 2 should be called:
  - `Question-Aligned Case Construction`
- The later full automation phase should be called:
  - `Closed-Loop Benchmark Curation`
- Avoid `smart builder` as the primary name.
  - it is too vague
  - it does not reveal what the system is actually trying to optimize

## Design Goal
The system should construct benchmark assets from source books by answering this question:

`What case should exist because it helps evaluate one explicit reader-quality question under judgeable conditions?`

This is stronger than:
- "what passages look interesting?"
- "what windows are easy to extract?"
- "what book categories do we still need more of?"

## Core Principles
- Question first, dataset second.
- Phenomenon first, window second.
- Judgeability is required, not optional.
- Keep deterministic infrastructure where reproducibility matters.
- Use LLMs where semantic detection, ambiguity checking, and case shaping are genuinely needed.
- Reuse current review outcomes instead of rebuilding from zero each round.
- Preserve the current case schema where it is already good.
- Keep decision-bearing promotion, freeze, and cutover actions human-owned.

## Scope
Question-Aligned Case Construction should eventually support four benchmark-asset families:
- excerpt cases
- chapter corpora
- runtime / resume fixtures
- compatibility / durable-trace fixtures

The first implementation focus should be:
- excerpt cases

Because excerpt cases are where:
- the current heuristic weakness is strongest
- the benchmark hardening loop already exists
- review feedback is richest

## First Landing
The first live implementation is now landed on the managed local supplement path, and it now has a reusable scratch-safe build mode for validation runs.

The current dataset ids still use `private_library` for continuity with existing evidence and review artifacts, but that naming is now historical rather than a preferred platform boundary.

Current code entrypoints:
- `reading-companion-backend/eval/attentional_v2/question_aligned_case_construction.py`
- `reading-companion-backend/eval/attentional_v2/build_private_library_supplement.py`

Current private-library outputs:
- candidate datasets:
  - `attentional_v2_private_library_excerpt_en_question_aligned_v1`
  - `attentional_v2_private_library_excerpt_zh_question_aligned_v1`
- scratch-safe candidate datasets:
  - `attentional_v2_private_library_excerpt_en_question_aligned_v1__scratch__<run_id>`
  - `attentional_v2_private_library_excerpt_zh_question_aligned_v1__scratch__<run_id>`
- durable intermediate artifacts under `reading-companion-backend/state/dataset_build/`:
  - `target_profiles/`
  - `opportunity_maps/`
  - `candidate_cases/`
  - `reserve_cases/`
  - `adequacy_reports/`
- scratch build runs keep their own artifact and manifest namespace under:
  - `reading-companion-backend/state/dataset_build/build_runs/<run_id>/`
  - this includes:
    - `target_profiles/`
    - `opportunity_maps/`
    - `candidate_cases/`
    - `reserve_cases/`
    - `adequacy_reports/`
    - `manifests/`
    - `build_summary.json`
    - `build_summary.md`

Current feedback source:
- the live reviewed local-only datasets stay separate and are read as feedback truth:
  - `attentional_v2_private_library_excerpt_en_v2`
  - `attentional_v2_private_library_excerpt_zh_v2`
- this means the first landing does not overwrite the current review-truth datasets while the new construction path is still being validated
- feedback can also be disabled or overridden explicitly when a scratch run needs to test construction behavior in isolation

## Latest Scratch Evidence
The first real quality-fix wave is now landed in the builder and audit reconstruction paths:
- `reading-companion-backend/eval/attentional_v2/question_aligned_case_construction.py`
- `reading-companion-backend/eval/attentional_v2/run_case_design_audit.py`

Current bounded fixes:
- preserve the full excerpt span in stored sentence ids instead of collapsing to anchor/support bounds
- stitch parser-fragment splits and expand windows around broken edges before rendering the final excerpt
- require explicit backward-link markers for callback candidates
- reject obvious reported-speech false positives for anchored-reaction candidates
- penalize context-dependent fragment anchors
- reject paratext / bibliographic windows
- keep low-priority profile-order filler candidates from outranking much stronger same-chapter opportunities

Current real-run evidence:
- narrow English builder validation:
  - `reading-companion-backend/state/dataset_build/build_runs/scratch_validation_en_qualityfix_20260330/build_summary.json`
  - result: `4` English candidate cases and `4` reserves from `education_of_henry_adams_public_en`
- narrow English bounded full smoke after the fix:
  - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_en_qualityfix_20260330/closed_loop_benchmark_curation_summary.json`
  - result: `keep = 2`, `revise = 2`, `drop = 0`
  - this replaced the earlier narrow-English result of `drop = 2`, `revise = 2`, `keep = 0`
- broader English bounded full smoke:
  - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_en_broader_qualityfix_20260330/closed_loop_benchmark_curation_summary.json`
  - result: `keep = 4`, `revise = 4`, `drop = 0`
- bilingual scratch sequence:
  - `closed_loop_full_smoke_bilingual_qualityfix_20260330`
    - English `revise = 4`
    - Chinese `drop = 1`
    - diagnosis: Chinese still selected publication metadata instead of literary prose
  - `closed_loop_full_smoke_bilingual_paratextfix_20260330`
    - English `keep = 2`, `revise = 2`
    - Chinese `revise = 1`
    - diagnosis: front-matter selection was fixed, but the chosen Chinese excerpt still carried residual edge noise
  - `closed_loop_full_smoke_bilingual_selectionfix_20260330`
    - English `revise = 4`
    - Chinese `keep = 1`
    - diagnosis:
      - the Chinese lane improved again because `tension_reversal` displaced the weaker early filler case
      - the English packet payload was byte-identical to the previous bilingual rerun, so the English shift points to adjudication variability rather than to new builder changes

Current interpretation:
- the excerpt-boundary / fragment-quality bug was real and materially important
- English question-aligned construction improved materially
- Chinese construction also improved materially and can now produce a real prose `keep`
- the next blocker for wider automation is no longer intake plumbing alone; it is bilingual reproducibility across both builder quality and packet adjudication

## What We Keep
Preserve these current strengths:
- managed source intake from `state/library_inbox/`
- canonical source catalog under `state/dataset_build/source_catalog.json`
- canonical parsing and screening in `reading-companion-backend/eval/attentional_v2/corpus_builder.py`
- tracked/local dataset row schema fields such as:
  - `question_ids`
  - `phenomena`
  - `selection_reason`
  - `judge_focus`
- review-state fields such as:
  - `benchmark_status`
  - `review_status`
  - `review_history`
  - `review_latest`
- mechanical packet review lifecycle in:
  - `generate_revision_replacement_packet.py`
  - `run_case_design_audit.py`
  - `auto_review_packet.py`
  - `import_dataset_review_packet.py`
  - `run_dataset_review_pipeline.py`

## What Must Change
Replace or heavily refactor the current excerpt-creation layer:
- fixed-window excerpt candidate generation
- bucket preference logic driven mainly by role and position
- fallback filling that does not yet reason from explicit target-case semantics

The new construction layer should create intermediate semantic artifacts before it creates final benchmark rows.

## Five Construction Layers
### 1. Source Screening
This layer stays mostly as it is now.

Responsibilities:
- canonical parse
- language control
- structural normalization
- chapter viability
- source-level tags and metadata
- chapter candidate screening

Outputs:
- screened source records
- candidate chapter list

### 2. Opportunity Mapping
This is the new missing middle layer.

An `opportunity card` is not yet a benchmark case.
It is a structured candidate reading pressure discovered inside a chapter.

Responsibilities:
- scan one chapter or meaning-unit sequence for target-relevant signals
- identify the local anchor lines and required prior context
- describe why this pressure may be benchmark-worthy
- estimate whether the opportunity is judgeable and discriminative

Outputs:
- opportunity cards for one source/chapter pair

### 3. Target Profiles
Each evaluation target should be a first-class profile, not an inferred bucket.

Each `target_profile` should define:
- `target_profile_id`
- supported `question_ids`
- expected `phenomena`
- what evidence shape makes the case strong
- what ambiguity patterns make the case weak
- required prior-context rules
- preferred excerpt-length and context policy
- case-shaping guidance for `selection_reason`
- case-shaping guidance for `judge_focus`
- replacement strategy if review later says `revise` or `drop`

Initial excerpt-focused profiles:
- `distinction_definition`
- `tension_reversal`
- `callback_bridge`
- `anchored_reaction_selectivity`
- `reconsolidation_later_reinterpretation`

This profile layer should stay extensible so future evaluation targets can be added without redesigning the builder.

### 4. Case Assembly
This layer turns opportunity cards into actual dataset rows.

Responsibilities:
- choose final excerpt boundaries
- include enough context for fair judging
- assign `question_ids`
- assign `phenomena`
- write concrete `selection_reason`
- write concrete `judge_focus`
- set reserve candidates and replacement lineage

This is where a benchmark case becomes an evaluation asset instead of a raw semantic hint.

### 5. Dataset Curation And Adequacy
This layer selects from assembled cases into benchmark packages.

Responsibilities:
- enforce target-profile quotas
- enforce English/Chinese balance
- enforce source diversity
- enforce holdout/reserve structure
- calculate adequacy for the current dataset family
- surface where replacement or additional mining is still needed

## Opportunity Card Schema
The opportunity card should be durable enough to drive review and later regeneration, but still remain a local operational artifact rather than a tracked benchmark truth layer.

Recommended fields:
- `opportunity_id`
- `source_id`
- `chapter_id`
- `language_track`
- `target_profile_ids`
- `anchor_sentence_ids`
- `support_sentence_ids`
- `prior_context_sentence_ids`
- `anchor_excerpt_text`
- `context_excerpt_text`
- `phenomenon_evidence`
- `judgeability_score`
- `discriminative_power_score`
- `ambiguity_risk`
- `construction_priority`
- `selection_reason_draft`
- `judge_focus_draft`
- `rejection_reasons`
- `reserve_rank`
- `derived_from_review_feedback`

Recommended storage territory:
- `reading-companion-backend/state/dataset_build/opportunity_maps/`

These artifacts are:
- reproducible from current sources plus code
- useful for debugging and regeneration
- not the final benchmark truth layer

## Target Profile Contract
Each target profile should have two parts.

### Semantic definition
- what kind of reading pressure it is
- what makes it genuinely present
- what makes it absent or too weak

### Construction policy
- how much prior context is usually needed
- whether the case should prefer a tight local span or broader setup
- whether later reinterpretation is required
- whether multiple reading moves might still be fair
- how strict the ambiguity filter should be

That separation matters because:
- one profile may be semantically clear
- but still need careful packaging to become a fair benchmark case

## Detection Methods
The system should not rely on one mining trick.
Use several methods together.

### Phenomenon-first detection
- ask directly whether a passage contains a target phenomenon
- this is the primary method

### Contrastive-difference detection
- prefer cases likely to reveal a meaningful mechanism difference
- avoid cases that every reasonable reader would handle identically

### Review-feedback mining
- use `needs_revision`, `needs_replacement`, review rationales, and adjudication outcomes to guide the next search
- replacements should learn from why the previous case failed

### Reserve-family mining
- mine nearby or sibling opportunities from the same source and chapter family
- keep replacement supply close to the current case rather than restarting the whole search

### Trajectory-aware chapter selection
- for chapter corpora and later fixture families, prefer chapters that support accumulation, callbacks, and later reinterpretation
- do not optimize only for chapter length or position

## Division Of Labor: Deterministic Rules vs LLMs
### Deterministic rules should own
- source discovery
- file and manifest handling
- canonical parsing
- language and storage-policy routing
- structural boundary extraction
- dedupe and quota enforcement
- dataset manifest generation
- packet orchestration
- final deterministic adequacy summaries

### LLMs should own
- semantic opportunity detection
- ambiguity checking
- discriminative-power estimation
- drafting `selection_reason`
- drafting `judge_focus`
- adversarial case-quality critique
- replacement suggestions when a case is dropped

This split gives us stronger semantics without sacrificing reproducibility where it matters.

## Quality Gates For One Case
A constructed case should pass all of these gates before it is promoted into a benchmark package:
- `text_grounded`
  - the phenomenon is clearly answerable to the source text
- `judgeable`
  - a reviewer can explain why the case exists and what a strong/weak reading would look like
- `nontrivial`
  - the case is not too easy or too generic
- `discriminative`
  - there is plausible room for mechanisms to differ meaningfully
- `bounded`
  - the excerpt is not so broad that judgment becomes diffuse
- `context_sufficient`
  - enough prior context is included for fair evaluation
- `reviewable`
  - if the case later fails review, the system can revise or replace it without guessing blindly

## Adequacy For A Dataset Family
Adequacy should not be just row count.

The adequacy report for one dataset family should include:
- total case counts by language
- total case counts by target profile
- reviewed-active counts by language and profile
- open weak-case counts by language and profile
- reserve depth by profile
- source diversity
- chapter diversity
- unresolved ambiguity concentration

Recommended output territory:
- `reading-companion-backend/state/dataset_build/adequacy_reports/`

## Relationship To Review
Question-Aligned Case Construction should feed the existing review machinery, not replace it.

The intended loop is:
- construction creates cases and reserves
- packet review audits case design
- adjudication/import updates benchmark truth
- review outcomes guide the next opportunity search and case replacement

This means review is not a sidecar.
It is part of the construction feedback system.

## Relationship To The Unattended Loop
We should define the unattended-loop contract now, but not fully design or implement the full controller yet.

### What should be designed now
- the artifact contract between construction and orchestration
- the target-profile system
- the opportunity-card system
- adequacy report outputs
- replacement lineage and reserve handling
- the stop-condition inputs the future loop will read

### What should wait until after the construction layer lands
- the full long-running unattended scheduler
- retry and resume policy across many build/review iterations
- automatic regeneration budgeting
- parallel fanout strategy across long-running mining/review waves
- loop-level recovery behavior after partial failures

### Why this split is better
- if we automate too early, we will automate today's weaker heuristics
- the loop should orchestrate stable construction artifacts, not define them by accident
- once opportunity cards, target profiles, and adequacy reports are real code artifacts, the unattended loop becomes much easier to specify correctly

So the right answer is:
- design the loop boundary now
- implement the full unattended loop after the construction layer is stable enough to be worth automating

## Initial Implementation Sequence
### Phase 2A
- define target-profile configs
- define opportunity-card schema
- create one local operational artifact layout under `state/dataset_build/`

### Phase 2B
- replace fixed-window excerpt mining with opportunity mapping
- generate candidate cases for the five current excerpt target profiles

### Phase 2C
- add ambiguity filtering, reserve-family generation, and adequacy reporting
- connect review outcomes back into replacement ranking

### Phase 2D
- extend the same method to:
  - chapter corpora
  - runtime / resume fixtures
  - compatibility / durable-trace fixtures

### Phase 3
- build the unattended controller around the stabilized Phase 2 artifacts
- current first controller landing:
  - `reading-companion-backend/eval/attentional_v2/run_closed_loop_benchmark_curation.py`
  - root surface:
    - `make closed-loop-benchmark-curation`
  - current scope:
    - construct scratch datasets
    - export initial `--only-unreviewed` packets
    - audit, adjudicate, import, archive
    - optionally run one bounded revision/replacement repair wave
    - refresh the queue summary
    - emit one final stop-and-summarize report
  - current boundary:
    - this is a first bounded controller, not the final unattended multi-iteration scheduler

## Immediate Next Code Targets
- `reading-companion-backend/eval/attentional_v2/corpus_builder.py`
  - carve out the current excerpt-generation logic behind a cleaner interface
- new question-aligned construction helpers under:
  - `reading-companion-backend/eval/attentional_v2/`
- current local/private supplement build path:
  - `reading-companion-backend/eval/attentional_v2/build_private_library_supplement.py`
  - keep it using the managed source catalog while the new construction layer is added
  - keep validating the scratch-safe build namespace before promoting that path into the unquestioned default for real source runs
- first closed-loop controller path:
  - `reading-companion-backend/eval/attentional_v2/run_closed_loop_benchmark_curation.py`
  - validate it on real managed inputs, then widen its stop-condition and regeneration policy only after the scratch build outputs look trustworthy

## Non-Goals For This Phase
- do not reopen benchmark promotion automatically
- do not freeze reviewed slices automatically
- do not redesign the packet-review machinery
- do not redesign the whole LLM gateway or provider-routing layer
- do not let Phase 3 orchestration pressure collapse the semantic design quality of Phase 2

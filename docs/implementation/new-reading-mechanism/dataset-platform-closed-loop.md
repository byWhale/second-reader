# Dataset Platform Closed Loop

Purpose: define the full automation target for benchmark dataset growth and quality refinement, and pin the Phase 1 source-intake contract that the later phases should build on.
Use when: designing or implementing the dataset platform, adding new local books, or deciding how source intake, case mining, review, and iteration fit together.
Not for: stable public API behavior, final benchmark decisions, or one-off packet results.
Update when: the dataset-platform phases, control loop, operator workflow, or artifact chain changes.

## Why This Exists
- The project already has strong pieces for:
  - canonical parse and source screening
  - dataset packaging
  - packetized audit / adjudication / import
- The missing piece is the controller that makes those parts one automatic system.
- The real target is not a better one-pass builder.
- The real target is:
  - original books
  - first candidate cases
  - automated review
  - automated refinement / replacement
  - repeated iteration until the dataset is good enough

## What We Keep
Do not rebuild the current dataset machinery from scratch.

The next platform should preserve:
- source screening and candidate-chapter scoring in `reading-companion-backend/eval/attentional_v2/corpus_builder.py`
- explicit case schema fields already used by curated and reviewed datasets:
  - `question_ids`
  - `phenomena`
  - `selection_reason`
  - `judge_focus`
- packetized review and adjudication:
  - `generate_revision_replacement_packet.py`
  - `run_case_design_audit.py`
  - `auto_review_packet.py`
  - `import_dataset_review_packet.py`
  - `run_dataset_review_pipeline.py`
- review feedback signals already stored in dataset rows:
  - `benchmark_status`
  - `review_status`
  - `review_history`
  - `review_latest`

## What Must Change
The weakest current layer is semantic case mining.

Current limitations:
- excerpt seeds are still often fixed-window slices
- bucket assignment still depends too much on role and position heuristics
- the current private-library builder is now catalog-wired, but semantic case mining still does not start from explicit target phenomena
- the builder stops after packaging instead of iterating from review outcomes

## Closed Loop Target
The full system should operate as one loop:

1. Source intake
- operator drops new books into the managed inbox
- the system copies them into canonical project-owned paths
- lightweight source metadata is cataloged

2. Parse and screen
- canonical parse runs over newly ingested sources
- screened source records are written in the existing schema
- parse / screen failures remain explicit instead of disappearing into later stages

3. Target-case generation
- case mining starts from evaluation targets, not from convenient windows
- the builder proposes chapter spans and excerpt cases that match target phenomena
- case rows are generated using the current case schema

4. Package and evaluate adequacy
- datasets are rebuilt or refreshed
- adequacy is measured by:
  - reviewed-active counts
  - target-phenomenon coverage
  - weak-bucket concentration
  - reserve / replacement availability

5. Packetized review and import
- weak or uncertain cases are routed into the existing packet pipeline
- audit, adjudication, import, and archive stay mechanical
- decision-bearing promotion or freeze remains human-owned

6. Refinement and replacement
- review outcomes drive the next candidate search:
  - `revise` means improve the span, focus, or bucket fit
  - `drop` means mine a replacement from the same source family or broader pool
  - `unclear` means escalate only if the policy says it is worth another pass

7. Stop condition
- the loop stops only when one of these is true:
  - adequacy thresholds are satisfied
  - the source pool is exhausted
  - a human-owned policy stop is reached

## Phase Plan
### Phase 1: Managed Source Intake
Goal:
- remove dependence on ad hoc external paths
- create a stable source catalog and artifact chain for later automation

### Phase 2: Question-Aligned Case Construction
Goal:
- replace coarse heuristic excerpt generation with question-aligned case construction
- introduce target profiles, opportunity cards, case assembly, and adequacy reporting as the stable semantic layer that later automation will orchestrate
- learn from existing curated cases and review outcomes instead of ignoring them

### Phase 3: Closed-Loop Orchestration
Goal:
- connect source intake, mining, packaging, review, adequacy scoring, and regeneration into one automatic loop
- current first landing:
  - `reading-companion-backend/eval/attentional_v2/run_closed_loop_benchmark_curation.py`
  - root surface:
    - `make closed-loop-benchmark-curation`
  - default safety mode:
    - scratch-safe
    - run-scoped manifests and build artifacts go under `reading-companion-backend/state/dataset_build/build_runs/<run_id>/`
    - scratch dataset ids stay isolated under `reading-companion-backend/state/eval_local_datasets/`
  - current stage order:
    1. `construct_dataset`
    2. `export_review_packets`
    3. `audit_packets`
    4. `adjudicate_packets`
    5. `import_packets`
    6. optional `repair_open_backlog`
    7. `refresh_queue_summary`
    8. `final_summary`
  - current mechanical mapping:
    - initial candidate review uses `export_dataset_review_packet.py --only-unreviewed`
    - bounded repair uses `run_dataset_review_pipeline.py`
  - current boundary:
    - one bounded build-review-import pass plus an optional one-wave repair follow-up
    - not yet the final unattended multi-iteration scheduler

## Phase Boundary Rule
We should design the unattended-loop boundary now, but not finalize or implement the full unattended controller until Phase 2 artifacts are real and stable.

Design now:
- target-profile contract
- opportunity-card contract
- case-construction outputs
- adequacy-report outputs
- reserve/replacement lineage
- stop-condition inputs

Design later, after Phase 2 lands in code:
- long-running unattended scheduling behavior
- retry/resume behavior across repeated construction/review waves
- regeneration budgeting and fanout policy
- loop-level recovery after partial failures

Reason:
- otherwise we would risk automating today's heuristic excerpt builder instead of automating a stronger semantic construction layer

## Phase 1 Contract
### Drop-folder workflow
Operators should add new books under:
- `reading-companion-backend/state/library_inbox/`

Nested batch directories are allowed below that root for batch organization only. They are not semantic language or visibility folders.

Examples:
- `reading-companion-backend/state/library_inbox/2026-03-29/steve_jobs.epub`
- `reading-companion-backend/state/library_inbox/2026-03-29/走出唯一真理观.epub`

### Optional sidecar metadata
Each source file may have a sidecar JSON with the same stem:
- `steve_jobs.source.json`

Supported fields:
- `source_id`
- `title`
- `author`
- `canonical_filename`
- `language`
- `visibility`
- `type_tags`
- `role_tags`
- `selection_priority`
- `notes`
- `origin`

This is the preferred place to refine title/author/tags without editing code.
- `language` is optional and overrides automatic language detection when needed.
- `visibility` is optional compatibility metadata only and should not shape normal product-side source intake.
- Most normal drops should not need a sidecar unless the operator wants to override metadata or other descriptive fields.

### Ingest command
- root command:
  - `make library-source-intake`
- dry-run:
  - `make library-source-intake LIBRARY_SOURCE_INTAKE_ARGS="--dry-run"`
- filtered example:
  - `make library-source-intake LIBRARY_SOURCE_INTAKE_ARGS="--language en"`
- compatibility recovery when `state/library_sources/` already exists but `source_catalog.json` does not:
  - `make library-source-intake LIBRARY_SOURCE_INTAKE_ARGS="--bootstrap-library-sources --run-id <run_id>"`
  - this seeds the managed source catalog from existing managed files plus tracked manifest metadata without copying source files again

### Output locations
Canonical copied sources:
- `reading-companion-backend/state/library_sources/`
  - new managed copies now use one language-rooted layout regardless of visibility metadata:
    - `state/library_sources/en/<file>.epub`
    - `state/library_sources/zh/<file>.epub`
  - older `/private/` paths remain valid compatibility inputs and should not be treated as the future platform shape

Catalog and run summaries:
- `reading-companion-backend/state/dataset_build/source_catalog.json`
- `reading-companion-backend/state/dataset_build/source_catalog.md`
- `reading-companion-backend/state/dataset_build/source_intake_runs/<run_id>.json`
- `reading-companion-backend/state/dataset_build/source_intake_runs/<run_id>.md`

### Lightweight provenance only
The source catalog should stay lightweight and operational.

Required facts:
- original filename
- inbox-relative path
- content hash
- file size
- canonical managed path
- first seen / last seen timestamps
- batch id
- parse / screening / packaging status

Not required in this phase:
- heavy legal paperwork
- deep external provenance narratives
- a second registry system

## Artifact Chain
The explicit Phase 1 handoff chain is:

`library_inbox` source file
-> canonical copy in `state/library_sources`
-> source catalog record in `state/dataset_build/source_catalog.json`
-> later canonical parse
-> screened source record
-> candidate chapters / target spans
-> dataset package rows
-> review packets
-> archived review outcomes

## Relationship To Current Builders
Phase 1 does not replace the current builders immediately.

It gives them a better upstream source territory:
- the current private-library supplement builder now pulls from the managed catalog and canonical library
- public/private is no longer the intended source-selection axis for future automation; current `private_library` names are historical dataset-family labels, not a platform-wide policy requirement
- later builders should do the same instead of reaching back to ad hoc external roots

## Current Next Work
1. Keep using the recovered managed source catalog and bounded controller, but treat the current bottleneck as case quality plus bilingual reproducibility rather than as intake plumbing.
2. Preserve the working builder/controller evidence already earned:
   - narrow English post-fix smoke:
     - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_en_qualityfix_20260330/closed_loop_benchmark_curation_summary.json`
     - result: `keep = 2`, `revise = 2`, `drop = 0`
   - broader English post-fix smoke:
     - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_en_broader_qualityfix_20260330/closed_loop_benchmark_curation_summary.json`
     - result: `keep = 4`, `revise = 4`, `drop = 0`
3. Keep tightening the bilingual route before unattended widening:
   - the first bilingual post-fix run still selected Chinese front matter and ended `zh drop = 1`
   - the paratext filter rerun moved that to `zh revise = 1`
   - the stronger-selection rerun moved that again to `zh keep = 1`
   - this proves builder-side bilingual quality can improve, but it does not yet prove stable unattended widening
4. Treat adjudication variability as part of the controller-hardening problem:
   - the English source rows remained identical between the last two bilingual reruns
   - but the regenerated audit inputs drifted on all `4` English cases, and the final adjudication shifted from `keep = 2`, `revise = 2` to `revise = 4`
   - so the next controller-hardening step must distinguish builder improvement from audit/adjudication variability
5. Only widen toward the multi-iteration unattended scheduler after the current bilingual stability pass:
   - finish the remaining Chinese scene/bucket shaping
   - bound or explain source-equal bilingual drift with the adjudication compare tooling
   - then run the next broader English and bilingual scratch validation wave

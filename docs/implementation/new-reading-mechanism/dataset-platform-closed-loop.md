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
- `visibility` is optional and defaults to `private`.
- Most normal drops should not need a sidecar unless the operator wants to override metadata or explicitly mark a source as `public`.

### Ingest command
- root command:
  - `make library-source-intake`
- dry-run:
  - `make library-source-intake LIBRARY_SOURCE_INTAKE_ARGS="--dry-run"`
- filtered example:
  - `make library-source-intake LIBRARY_SOURCE_INTAKE_ARGS="--language en"`

### Output locations
Canonical copied sources:
- `reading-companion-backend/state/library_sources/`
  - explicit `public` sources keep the existing language-root convention:
    - `state/library_sources/en/<file>.epub`
    - `state/library_sources/zh/<file>.epub`
  - default `private` sources keep the existing private subfolders:
    - `state/library_sources/en/private/<file>.epub`
    - `state/library_sources/zh/private/<file>.epub`

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
- later builders should do the same instead of reaching back to ad hoc external roots

## Immediate Next Work After Phase 1
1. Land the Question-Aligned Case Construction design:
   - target profiles
   - opportunity cards
   - case assembly
   - adequacy reporting
2. Reuse current curated cases and review outcomes as feedback signals for question-aligned construction and later replacement.
3. Define the unattended-loop contract now, but wait to finalize the full controller until the Phase 2 artifacts above are stable enough to orchestrate safely.

# New Reading Mechanism Design Capture

Purpose: keep a repo-local, implementation-oriented capture of the current Notion design so execution can proceed without losing scope or detail.
Use when: translating the Notion design into workstreams, code tasks, schemas, tests, or migration steps.
Not for: stable mechanism authority or prompt-text authority.
Update when: the Notion design materially changes or when the source-to-workstream mapping becomes inaccurate.

## Source
- Upstream design page:
  - `https://www.notion.so/new-reading-mechanism-design-32ad8f1822a5805e9864cf1c3cd0551b`
- Repo-local capture date:
  - `2026-03-23`
- Capture policy:
  - preserve design intent and coverage
  - improve hierarchy for implementation
  - avoid freezing exact prompt wording

## Design Skeleton

### 1. Product Goal And Reading Principles
- The mechanism is designed from first principles for the product goal of exposing a living, text-grounded co-reading mind.
- Every sentence must be seen in source order.
- The mechanism must not deliberate from scratch on every sentence.
- Broad prior knowledge is allowed only when text-activated and reading-productive.
- The mechanism must stay text-accountable, not oracle-like or generically clever.
- User-visible thought must remain legible and source-anchored.

### 2. Runtime Ontology And Tiered State
- Perceptual unit:
  - `sentence`
- Local accumulation:
  - `local buffer`
- Cognitive unit:
  - `meaning unit`
- Control signal:
  - `trigger`
- Hot local state:
  - `working pressure`
- Retrieval-facing earlier state:
  - `anchor memory`
- Slower promoted understanding:
  - `reflective summaries`
- Prior-knowledge object:
  - `knowledge activation`
- Next-step control choice:
  - `move = advance | dwell | bridge | reframe`

### 3. Explicit State Operations
- State mutation is explicit, not hidden prompt drift.
- Core operations:
  - `create`
  - `update`
  - `cool`
  - `drop`
  - `retain_anchor`
  - `link_anchors`
  - `promote`
  - `supersede`
  - `reactivate`
- Important invariants:
  - no durable interpretive item without source grounding
  - no silent promotion
  - no silent overwrite of reflective meaning
  - cooling is not rejection
  - dropping from `working_pressure` must not erase historical anchors or reflective history

### 4. Core Online Reading Loop
- Ingest next sentence.
- Mark it as seen.
- Update local buffer.
- Run always-on cheap trigger detection.
- Combine trigger signals with `working_pressure`.
- Keep accumulating unless pressure or boundaries justify escalation.
- Use hybrid meaning-unit closure:
  - cheap boundary nomination
  - structured LLM closure evaluation
  - controller-led close vs continue
- Trigger `zoom read` only when local honesty requires higher resolution.
- Update tiered state.
- Ask controller for next move.
- Emit user-visible reaction only when warranted.
- Continue from the correct sentence cursor.

### 5. Triggering, Gates, And Boundary Control
- Qualitative gates:
  - `quiet`
  - `watch`
  - `hot`
  - `must_evaluate`
- Candidate-boundary signals:
  - discourse turn
  - definition or distinction
  - claim pressure
  - sentence role shift
  - local cohesion drop
  - callback activation
  - pressure update proxy
  - cadence guardrail
- Trigger ensemble classes:
  - integrity triggers
  - salience triggers
  - knowledge-risk triggers
- Trigger outputs:
  - `no_zoom`
  - `monitor`
  - `zoom_now`

### 6. Control, Knowledge, Search, And Bridge Behavior
- Controller is LLM-first with hard-veto guardrails.
- Bridge targets must be source anchors, not reactions.
- Bridge retrieval is memory-first, then bounded look-back source space.
- Knowledge activation separates:
  - `recognition_confidence`
  - `reading_warrant`
- Knowledge-use modes:
  - `book-grounded only`
  - `book-grounded + prior knowledge`
- Search policy is separate from knowledge-use mode:
  - `no_search`
  - `defer_search`
  - `search_now`

### 7. User-Visible Trace And Historical Integrity
- Durable visible object is an anchored reaction, not a section-centered wrapper.
- Reaction schema centers on:
  - `reaction_id`
  - `primary_anchor`
  - `thought`
  - optional `related_anchors`
  - optional `reconsolidation_record_id`
  - `created_at`
- Reconsolidation is `append + link`, never rewrite-in-place.
- Earlier persisted thoughts remain immutable.
- Later thoughts stay independently anchored to later reading moments.

### 8. Persistence, Resume, And Continuity
- Persist:
  - reading position
  - local continuity state
  - durable tiered state
  - resume metadata
- Resume modes:
  - `warm_resume`
  - `cold_resume`
  - `reconstitution_resume`
- Invariants:
  - no loss of durable anchors
  - no loss of visible reactions
  - no silent mutation of reflective summaries
  - no pretending reconstructed hot state is warm state

### 9. Calibration, Failure Taxonomy, Observability, And Evaluation
- Versioned `reader_policy` tunes behavior without changing ontology.
- Policy domains:
  - gate
  - controller
  - knowledge
  - search
  - bridge
  - resume
  - logging
- Canonical failure families:
  - coverage
  - attention
  - meaning unit
  - controller pacing
  - knowledge
  - bridge memory
  - state-memory health
  - historical integrity
- Required observability layers:
  - `event_stream`
  - `checkpoint_summaries`
- Evaluation must align to shared project evaluation, with mechanism-specific integrity and trace criteria.

### 10. Prompt Contracts And Node Handoffs
- Deterministic by default:
  - sentence ingest
  - cheap trigger signals
  - candidate retrieval
  - schema validation
  - hard guardrails
- LLM-driven by default:
  - `zoom_read`
  - `meaning_unit_closure`
  - `controller_decision`
  - `reflective_promotion`
  - `reconsolidation`
- Hybrid:
  - `bridge_resolution`
  - later if needed, `knowledge_activation_assessment`
- Behavior-defining node contracts exist for:
  - `zoom_read`
  - `meaning_unit_closure`
  - `controller_decision`
  - `bridge_resolution`
  - `candidate_generation`
  - `reaction_emission`
  - `reflective_promotion`
  - `reconsolidation`
  - `book_survey`
  - `chapter_consolidation`
- Node handoff rules are explicit, especially for:
  - `zoom_read -> meaning_unit_closure`
  - `meaning_unit_closure -> controller_decision`
  - `controller_decision -> candidate_generation -> bridge_resolution`
  - chapter-end `chapter_consolidation -> reflective_promotion -> next-chapter state`

## Source-To-Workstream Coverage Map
| Source block from Notion | Implementation domain | Main execution phase |
| --- | --- | --- |
| Goal / First Principles / Core Principle / Success Standard | product alignment and acceptance gates | Phase 0, Phase 9 |
| What Broad Prior Knowledge Is For / Knowledge Activation Objects / Knowledge-Use Policy / Search Policy | knowledge state, knowledge policy, search gating | Phase 4, Phase 5 |
| Core Runtime Objects / Tiered Reading State / Working Pressure / Anchor Memory / Reflective Summaries / State Operations | runtime schemas and state operations | Phase 1, Phase 5 |
| Main Reading Loop / Controller / How Focus Is Selected | core runtime loop and controller | Phase 3, Phase 4 |
| Candidate-Boundary Signals / Trigger Ensemble / Trigger Output / When To Zoom | deterministic intake, gates, trigger pipeline | Phase 3 |
| LLM Call Policy / Zoom Read Call / What Each Interpretive Call Should Return / Prompt Packet / Non-Cheating Constraint | prompt node runtime and packet design | Phase 4 |
| User-Visible Output / Reaction Emission / Reconsolidation / Anti-Miss Safeguards | output persistence and historical integrity | Phase 6 |
| Persistence and Resume | checkpointing and resume logic | Phase 7 |
| Relationship To The Existing Mechanism / Decisions Made So Far | migration boundaries and reuse rules | Phase 0, Phase 8, Phase 9 |
| Calibration and Configuration Layer | policy objects and tuning controls | Phase 1, Phase 8 |
| Failure Modes / Instrumentation / Evaluation Mapping | observability and evaluation harness | Phase 8 |
| Open Design Questions / Prompt Design Workstream / Prompt Versioning | temporary decision log and prompt eval traceability | Phase 0, Phase 8, ongoing |
| `book_survey` contract | orientation call and survey artifacts | Phase 2 |
| `zoom_read` / `meaning_unit_closure` / `controller_decision` contracts | core LLM loop | Phase 4 |
| `candidate_generation` / `bridge_resolution` contracts | deterministic retrieval plus bounded LLM bridge judgment | Phase 5 |
| `reflective_promotion` / `reconsolidation` / `chapter_consolidation` contracts | slow-cycle reasoning and chapter transitions | Phase 6 |

## Working Interpretation Of The Design
- This design is much larger than a prompt rewrite or a single new reader module.
- It is a multi-layer mechanism project that touches:
  - substrate expectations
  - runtime state schemas
  - control flow
  - retrieval
  - output persistence
  - resume semantics
  - observability
  - evaluation
- Implementation must therefore be phased and traceable.
- The most important way to avoid losing detail is not a raw paste alone; it is a repo-local capture plus a coverage map plus a tracker that forces every major design block to land somewhere concrete.

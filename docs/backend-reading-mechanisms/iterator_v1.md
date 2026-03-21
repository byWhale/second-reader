# Iterator V1 Mechanism

Purpose: explain how the current default sequential reader selects its working unit, assembles prompt context, and projects live attention state.
Use when: changing `iterator_v1` reader-unit selection, prompt assembly, memory packing, search expansion, or live `current_reading_activity` semantics.
Not for: shared mechanism-platform rules, upload/start/resume lifecycle rules, or endpoint-level aggregation responsibilities.
Update when: `iterator_v1` section/subsegment boundaries, reader-loop stages, prompt inputs, memory-packet composition, or attention projection rules change.

- Status: `default`
- Mechanism key: `iterator_v1`
- Defaultness: `current default`
- Artifact root: `_mechanisms/iterator_v1/`
- Authority scope: current live `iterator_v1` ontology, execution loop, prompt assembly, memory packet, runtime artifacts, and live attention projection

Use `docs/backend-reading-mechanism.md` for shared mechanism-platform boundaries. Use `docs/backend-sequential-lifecycle.md` for the job-level workflow over time. Use `docs/backend-state-aggregation.md` for how runtime artifacts become public payloads.

## Purpose And Status
- `iterator_v1` is the current live/default backend reader mechanism.
- It is a section-first sequential reader with a local subsegment planner inside each selected section.
- It remains the shipped mechanism while the backend platform is being generalized for additional reader mechanisms.

## Core Primitives / Ontology
- `chapter`
  - One source-ordered chapter or major part from the parsed book structure.
- `book document`
  - The shared parsed-book substrate persisted at `public/book_document.json`.
  - It contains chapter order, paragraph records, and locators only.
- `section`
  - The persisted semantic unit created before deep reading begins.
  - Backend runtime code still often calls this unit a `segment`.
  - Public/UI language should treat this concept as `section`.
- `structure`
  - The `iterator_v1`-owned derived artifact persisted at `_mechanisms/iterator_v1/derived/structure.json`.
  - It contains `section` records and other iterator-shaped traversal state.
- `body group`
  - One parse-only contiguous body-text block formed before semantic section segmentation.
  - It is separated by detected `section_heading` or `auxiliary` boundaries.
  - It is an internal hygiene layer, not a product-facing reading unit.
- `subsegment`
  - The runtime-only work unit created inside one selected section by the subsegment planner.
  - The active planner is LLM-primary for normal multi-sentence sections, with a heuristic sentence-boundary slicer as fallback.
  - This is the smallest orchestration-level unit the reader actively feeds into the inner loop.
- `excerpt` / `current_excerpt`
  - A live attention projection derived from the currently active text span.
  - It is not a scheduling unit and it is not guaranteed to equal the full current `subsegment.text`.
- `anchor_quote`
  - A reaction-level quote recovered from the current text span.
  - It is a reaction anchor, not a reading unit.

## Reading Progression Logic
- Canonical parse first preserves the source book order as `book_document` chapters plus paragraph records and locators.
- `iterator_v1` then derives semantic sections from that canonical substrate before the main read run starts.
- The outer iterator reads in source order:
  - book
  - chapter
  - section
- `continue` / resume behavior does not pick a new attention target globally. It skips chapters or sections already marked done and resumes at the next unfinished persisted section.
- Once one section is selected, `run_reader_segment()` calls the subsegment planner.
- Planner behavior is local to the current section:
  - effectively single-sentence sections short-circuit and stay as one runtime unit
  - normal multi-sentence sections go through an LLM planner that proposes the fewest self-contained reading units needed for one local nonfiction reading move at a time
  - malformed, structurally invalid, over-budget, or planner-unavailable cases fall back to the heuristic sentence-boundary slicer
- The planner preserves source order and full sentence coverage.
- The heuristic fallback still uses sentence boundaries plus token/density heuristics, but those heuristics are now safety behavior, not the semantic target.
- The public locus remains section-level even while the inner loop advances through runtime `subsegments`.

### Parse-Side Section Formation
- Raw source chapters are extracted first from the input book format.
- The canonical parse writes `public/book_document.json` before any iterator-specific section derivation happens.
- Each canonical chapter is normalized into paragraph-sized text blocks called `paragraph records`.
  - EPUB prefers XHTML block extraction so the records can retain href, CFI, block-tag, and paragraph-index metadata.
  - When structured extraction is unavailable, the parser falls back to plain-text paragraph splitting.
- `iterator_v1` derives its parse-time `section` contexts from that canonical chapter/paragraph substrate rather than treating `_mechanisms/iterator_v1/derived/structure.json` as shared truth.
- Parse-time classification labels each paragraph record as one of:
  - `chapter_heading`
  - `section_heading`
  - `body`
  - `auxiliary`
- `body groups` are formed before semantic section segmentation.
  - A body group collects contiguous `body` records.
  - A detected `section_heading` starts the next body group and is carried forward as boundary context, not as body prose.
  - A detected `auxiliary` block acts as a hygiene boundary and can end the current body group without becoming section body text.
- Semantic section segmentation runs per `body group`, not over the whole chapter at once.
  - The prompt receives group-local numbered body paragraphs such as `[P1]`, `[P2]`, and so on.
  - The prompt also receives chapter-heading and section-heading context as framing or boundary hints only.
  - The prompt must return contiguous paragraph ranges plus short summaries in source order.
- Prompt-local paragraph numbering is temporary.
  - After the prompt returns group-local paragraph ranges, the parser remaps those ranges back onto the chapter's persisted paragraph indexes before writing the final section records.
- Post-processing then rebalances obviously poor section outputs.
  - Empty or invalid segmentation falls back to coarse coverage of the current body group.
  - Very long under-segmented groups may be re-chunked into coarse sections.
  - Obviously low-value section summaries may be dropped.
  - Undersized adjacent sections may be merged back together.
- Persisted `section` records are the output of this parse-side path.
  - They carry stable text spans, paragraph ranges, locators, and `segment_ref`.
  - They live in `_mechanisms/iterator_v1/derived/structure.json`, not in `book_document.json`.
  - Runtime `subsegment` planning only begins after the outer iterator selects one persisted section for live reading.

### Why This Layer Exists
- `body group` is a deterministic hygiene layer that keeps obvious structure text and auxiliary noise from defining the semantic target by accident.
- `section` is the persisted semantic anchor that the outer iterator, checkpoints, and public state can rely on across runs.
- `subsegment` remains the runtime execution unit used to take smaller reading steps inside one already-selected section.
- Ownership is intentionally split:
  - `book -> chapter -> paragraph/locator` belongs to the shared `book_document`
  - `chapter -> sections` belongs to the iterator-derived `structure`
  - `section -> subsegments` plus planner state and memory belong to iterator runtime artifacts under `_mechanisms/iterator_v1/runtime/`

### Coverage And Limits
- The parser aims not to lose `body` prose coverage.
  - If semantic section segmentation returns nothing useful, the system falls back to coarse section coverage instead of leaving the body group unread.
- Not all raw chapter text is intended to become section body text.
  - `chapter_heading`, `section_heading`, and `auxiliary` content may remain context-only or be excluded from deep-reading body coverage altogether.
- Heading and auxiliary detection are heuristic.
  - Books with unusual formatting, title-like prose, dense metadata, or design-heavy layouts can still be misclassified at this parse-side stage.

## LLM Call Schedule
- The main inner loop is:
  - `read`
  - `think`
  - `express`
  - optional `search`
  - optional `fuse`
  - `reflect`
- `read`
  - Prepares the current text span plus reading memory for the next reasoning step.
- `think`
  - Decides whether the current subsegment is worth expressing, chooses a source excerpt, and estimates curiosity potential.
- `express`
  - Produces mixed reactions for the current subsegment, including `highlight`, `association`, `curious`, `discern`, `retrospect`, or `silent`.
- `search`
  - Runs only when the current thought has enough curiosity potential and the segment/chapter budget still allows search queries.
- `fuse`
  - Rewrites a `curious` reaction after search so the reaction absorbs the search results instead of appending them as a log.
- `reflect`
  - Self-reviews the produced reactions and decides whether the reactions should pass or be skipped.
- Current runtime behavior is a single through-pass per subsegment.
  - Graph-shaped helpers remain in the codebase, but the active `run_reader_segment()` path currently does not perform multi-round revise loops for live section execution.
- After the inner loop finishes, reactions from multiple subsegments are merged back into one section-level result before the iterator advances and writes checkpoints/memory updates.

## Context Packaging
- The reader does not send only raw subsegment text to the model.
- The first model step inside one multi-sentence section is the subsegment planner prompt.
  - It receives numbered sentence-like units in source order.
  - It also receives `book_context`, `current_part_context`, the current section ref/summary, `user_intent`, and the output-language contract.
  - It does not receive the full `memory_text` packet.
- After planning, each reader-stage prompt is assembled around the current `subsegment.text` plus stable context:
  - `book_context`
    - book title
    - author
    - current chapter index
    - nearby outline entries
  - `current_part_context`
    - chapter ref
    - chapter title
    - chapter primary role
    - role tags
    - role confidence
    - current section heading when available
    - one role-aware note about the likely function of the current chapter
  - `memory_text`
    - a budget-aware packet assembled from reader memory
  - `user_intent`
    - explicit user intent when provided, otherwise a fallback label
  - output language contract
    - the shared language instructions that keep reactions and summaries in the configured output language
- Stage-specific additions:
  - `subsegment_plan`
    - numbered sentence list
    - section ref and summary
    - planner-only JSON schema for sentence coverage and reading moves
  - `think`
    - current section summary and current subsegment text
  - `express`
    - the normalized `thought_json` plus any revision instruction placeholder
  - `fuse`
    - the current `curious` reaction, `anchor_quote`, `search_query`, and normalized search results
  - `reflect`
    - `reactions_json` for the current subsegment plus the same contextual packet
- Prompt wording is owned by `reading-companion-backend/src/prompts/templates.py`.
  - This document describes prompt responsibilities and inputs, not the full prompt text.

## Memory And Revisit Logic
- `_assemble_memory_packet()` builds `memory_text` per prompt node, not once for the whole run.
- The packet is budget-aware:
  - larger current text spans reduce the available memory budget
  - different prompt nodes use different memory caps
- The packet is also relevance-aware:
  - memory candidates are ranked against lexical terms from the current subsegment text, section summary, section heading, and chapter title
  - the packet prefers open or still-relevant items and trims to fit the node budget
- Logical packet components are:
  - book arc summary
    - the current whole-book through-line
  - open threads
    - unresolved questions or tensions still marked open
  - findings
    - provisional or durable findings worth carrying forward
  - salience ledger
    - active concepts, characters, institutions, places, or motifs and their working notes
  - recent segment flow
    - the newest section-to-section reading trail
  - chapter memory summaries
    - recent chapter-level memory summaries

## Runtime Artifacts
- Shared substrate dependency
  - `public/book_document.json`
- Mechanism-private derived artifacts
  - `_mechanisms/iterator_v1/derived/structure.json`
  - `_mechanisms/iterator_v1/derived/structure.md`
- Mechanism-private runtime artifacts
  - `_mechanisms/iterator_v1/runtime/reader_memory.json`
  - `_mechanisms/iterator_v1/runtime/checkpoints/*`
  - `_mechanisms/iterator_v1/runtime/plan_state.json`
- Mechanism-private internal artifacts
  - `_mechanisms/iterator_v1/internal/diagnostics/*`
  - `_mechanisms/iterator_v1/internal/qa/*`
  - `_mechanisms/iterator_v1/internal/analysis/*`
- Optional exports
  - `_mechanisms/iterator_v1/exports/normalized_eval_bundle.json` for explicit eval-mode runs

## Public-State Projection
- The runtime reader loop emits structured progress events while the outer iterator owns the persistent live snapshot.
- The public-facing live snapshot is `current_reading_activity`.
- `segment_ref` in that snapshot remains section-level, even when the inner loop is already working through smaller `subsegments`.
- `current_excerpt` is a short projection of the current attention target:
  - usually derived from the active `subsegment.text`
  - sometimes derived from an `anchor_quote`
  - normalized and shortened for live-state transport
- `search_query` is also part of the live snapshot when the reader is actively expanding curiosity.
- External surfaces should interpret attention context in this priority order:
  - `search_query`
  - `current_excerpt`
- This is why the live overview can appear more fine-grained than the persisted section locus:
  - the locus still points at the current section
  - the projected attention text can point at a smaller runtime span inside that section
- Catalog aggregation may widen that projection again.
  - When older runtime snapshots only retain a shortened `current_excerpt`, catalog can backfill the normalized full section text by resolving `segment_ref` against `_mechanisms/iterator_v1/derived/structure.json`.
  - Public state therefore reflects the runtime attention target as best effort, not as a strict copy of the current subsegment payload.

## Known Limits / Drift Notes
- The active reader path is `run_reader_segment()`.
  - Graph-shaped helpers remain in the codebase, but they are not the authoritative description of the current live section execution path.
- `section`, `subsegment`, and `excerpt` should not be treated as interchangeable:
  - `section` is the persisted semantic unit
  - `subsegment` is the runtime work unit
  - `excerpt` is the projected live attention text
- `slice_max_subsegments` is now a safety cap, not the primary semantic target for segmentation.
  - The reader first asks the planner for the fewest self-contained units.
  - The hard cap only rejects pathological plans and bounds the fallback slicer.
- API and runtime payloads may still expose compatibility names such as `segment_ref`.
  - That does not change the product-language expectation that user-facing terminology should say `section`.
- Prompt wording is allowed to evolve more frequently than this document.
  - If prompt responsibilities, inputs, or outputs change, update this document.
  - If only prompt phrasing changes, the code remains the authority.

## Machine-Readable Appendix
The JSON block below is the machine-readable appendix used by the reading-mechanism drift check.

```json
{
  "selection_pipeline": [
    "book",
    "chapter",
    "section",
    "subsegment"
  ],
  "persisted_unit_labels": {
    "chapter": "chapter",
    "semantic_unit": "section",
    "backend_internal_alias": "segment"
  },
  "runtime_attention_unit": "subsegment",
  "segment_execution_mode": "single_pass",
  "reader_loop_nodes": [
    "read",
    "think",
    "express",
    "search",
    "fuse",
    "reflect"
  ],
  "reader_prompt_nodes": [
    "subsegment_plan",
    "think",
    "express",
    "reflect"
  ],
  "live_activity_phases": [
    "reading",
    "thinking",
    "searching",
    "fusing",
    "reflecting",
    "waiting",
    "preparing"
  ],
  "internal_reaction_types": [
    "highlight",
    "association",
    "curious",
    "discern",
    "retrospect",
    "silent"
  ],
  "memory_packet_sections": [
    "book_arc_summary",
    "open_threads",
    "findings",
    "salience_ledger",
    "recent_segment_flow",
    "chapter_memory_summaries"
  ],
  "attention_context_priority": [
    "search_query",
    "current_excerpt"
  ],
  "subsegment_slicing_defaults": {
    "planner_mode": "llm_primary",
    "fallback_mode": "heuristic_sentence_boundary",
    "safety_cap_role": "absolute_cap",
    "slice_target_tokens": 420,
    "slice_max_tokens": 700,
    "slice_max_subsegments": 8,
    "density_trigger_gte": 3.2
  },
  "search_budget_defaults": {
    "max_search_queries_per_segment": 2,
    "max_search_queries_per_chapter": 12
  }
}
```

# Attentional V2 Mechanism

Purpose: define the future attention-frontier reading mechanism that reads every sentence, reasons mainly over meaning units, and moves forward through unresolved interpretive pressure rather than fixed section traversal.
Use when: refining the future attention-frontier mechanism design, clarifying its ontology, or preparing later implementation planning.
Not for: shared mechanism-platform rules, live/default behavior claims, or the internals of `iterator_v1`.
Update when: the planned ontology, progression logic, LLM schedule, memory model, or artifact design for `attentional_v2` materially changes.

- Status: `design-only`
- Mechanism key: `attentional_v2`
- Defaultness: `not default`
- Artifact root: `_mechanisms/attentional_v2/` (planned)
- Authority scope: future `attentional_v2` mechanism design, including ontology, control loop, sparse-LLM schedule, memory model, and planned mechanism-private artifacts

Use `docs/backend-reading-mechanism.md` for shared platform boundaries. Use `docs/backend-state-aggregation.md` for shared public-state surfaces.

## Purpose And Status
- `attentional_v2` is the planned future mechanism for a more self-propelled reading mind.
- It is not implemented and does not describe live product behavior today.
- Its goal is to preserve sentence-level fidelity while shifting the main reasoning unit from fixed sections toward dynamic meaning units and an explicit attention frontier.

## Core Primitives / Ontology
- `sentence stream`
  - the ingestion stream of source-order sentences
  - every sentence is seen in order; none are skipped at intake
- `meaning unit`
  - the primary reasoning unit
  - usually one paragraph or a short paragraph span
  - sometimes one sentence when a line is unusually dense, pivotal, or ambiguous
- `survey map`
  - the initial structural map of the book or chapter
  - built from chapter order, headings, openings, closings, and obvious pivots
- `attention candidate`
  - a span that may deserve focused reading next
  - can represent a fresh local span or a revisit target
- `attention frontier`
  - the ranked set of current attention candidates
  - this is the mechanism's main control surface for choosing what deserves thought next
- `open tension`
  - an unresolved interpretive pressure such as contradiction, ambiguity, instability, motif recurrence, or unexplained significance
- `working hypothesis`
  - a provisional claim about what the chapter or book is doing
- `revisit link`
  - a connection from a new span back to an earlier sentence or meaning unit that has become newly important

## Reading Progression Logic
- The mechanism starts with a survey pass.
  - It uses the shared `book document` to build a rough structural map of chapters, headings, and likely pivots.
- It then reads through the text in sentence order.
  - Sentence order is the intake discipline.
  - Meaning-unit consolidation is the reasoning discipline.
- The main control loop is:
  - ingest sentence
  - update local salience and open tensions
  - consolidate into a meaning unit when enough text has accumulated
  - update the attention frontier
  - choose the next move
- The next move is one of:
  - `advance`
    - move to the next unresolved local span when understanding is good enough
  - `dwell`
    - stay on the current span and zoom further in when interpretive pressure remains high
  - `bridge`
    - revisit an earlier span that has become newly relevant
  - `reframe`
    - update the broader hypothesis about the chapter/book, then continue with changed attention priorities
- Reading is pushed forward by unresolved interpretive pressure under coverage constraints.
  - Coverage prevents wandering forever.
  - Interpretive pressure prevents mechanical traversal.
- The mechanism should not see future text beyond the current reading frontier.
  - Survey context may include coarse chapter structure, but live interpretive calls must not use future paragraphs as if they were already read.

## LLM Call Schedule
- The main LLM is not called on every sentence.
- Default call types are:
  - `chapter opening`
    - set initial expectations and open questions using title, chapter heading, and opening span
  - `meaning-unit consolidation`
    - interpret a completed paragraph or short span after enough text has accumulated
  - `trigger call`
    - fire early when one sentence becomes unusually important
  - `chapter consolidation`
    - update broader hypotheses and unresolved tensions at a local milestone
- Sentence-level trigger calls happen only when a sentence earns that attention through signals such as:
  - reversal
  - unusually compressed claim
  - contradiction
  - metaphorical charge
  - recurrence of an active motif
  - reference instability
  - downstream consequence for the current hypothesis

## Context Packaging
- Each LLM call should receive a structured packet rather than arbitrary raw chunks.
- The packet contains:
  - `structural frame`
    - book title
    - author
    - chapter title
    - position within chapter/book
  - `focal span`
    - the sentence, paragraph, or short span that triggered the call
  - `local context`
    - immediately surrounding sentences or paragraphs already read
  - `working memory`
    - active hypotheses
    - open tensions
    - unresolved questions
    - active motifs and recurrence notes
  - `retrieved anchors`
    - a small set of earlier spans selected because they are semantically, structurally, or motif-recurrently relevant
- Retrieved anchors are chosen by a mix of:
  - semantic similarity
  - motif recurrence
  - unresolved-question linkage
  - structural centrality
  - recency when helpful, but not as the only signal

## Memory And Revisit Logic
- The mechanism keeps a live state that separates:
  - what seems settled
  - what remains open
  - what may need revisiting later
- Memory should minimally track:
  - chapter/book hypotheses
  - open questions
  - tensions and contradictions
  - active motifs or concepts
  - important anchor lines
  - revisit links
- Sentence-level trigger detection should happen continuously during intake.
  - This protects against missing a crucial single sentence even when the main reasoning unit is larger.
- Retroactive resurfacing is first-class.
  - A later span can promote an earlier sentence or paragraph into renewed focus.
- Chapter-end backward sweeps should check:
  - which earlier lines turned out to matter most
  - which open tensions remain live
  - whether the chapter-level hypothesis changed

## Runtime Artifacts
- Shared substrate dependency
  - `public/book_document.json`
- Planned mechanism-private derived artifacts
  - `_mechanisms/attentional_v2/derived/survey_map.json`
  - `_mechanisms/attentional_v2/derived/revisit_index.json`
- Planned mechanism-private runtime artifacts
  - `_mechanisms/attentional_v2/runtime/frontier_state.json`
  - `_mechanisms/attentional_v2/runtime/memory_state.json`
  - `_mechanisms/attentional_v2/runtime/checkpoints/*`
- Planned mechanism-private internal artifacts
  - `_mechanisms/attentional_v2/internal/diagnostics/*`
  - `_mechanisms/attentional_v2/internal/analysis/*`
- Planned optional exports
  - `_mechanisms/attentional_v2/exports/normalized_eval_bundle.json` for explicit eval-mode runs

## Public-State Projection
- `attentional_v2` should adapt its private state into the same shared public-state surfaces as other mechanisms.
- Shared public surfaces should continue to expose stable transport fields such as:
  - `current_reading_activity`
  - `current_excerpt`
  - `search_query` when applicable
- The mechanism's internal locus will not necessarily be a fixed `section`.
  - Adapters must project the current focal span and reading phase into shared public fields without claiming that the private ontology is section-based.
- When possible, the projected live attention text should reflect:
  - the current focal span
  - or the current interpretive question if that better explains what the mechanism is doing now

## Known Limits / Drift Notes
- This is a stable design doc, not an implementation doc.
- The precise storage schemas for survey maps, frontier state, and revisit indexes are still open implementation details.
- The survey stage must stay coarse enough that it does not become hidden full-book cheating.
- Retrieval pressure and revisit behavior will likely need careful budget control during implementation.
- Public adapter behavior may need compatibility compromises if existing transport fields remain section-shaped.

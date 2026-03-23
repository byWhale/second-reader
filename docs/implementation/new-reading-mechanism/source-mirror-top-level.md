# New Reading Mechanism Source Mirror: Top-Level Blocks

Purpose: preserve the top-level Notion design blocks in repo-local form with high fidelity and original ordering.
Use when: checking the detailed source design before normalization or requirement decomposition.
Not for: implementation sequencing or simplified digesting.
Update when: the upstream Notion design changes or the mirror is found incomplete.

## 1. Goal
- Design a reading mechanism from first principles for the product's actual goal: giving the user access to a living, text-grounded co-reading mind.
- The mechanism should not be derived from the current reader's implementation conveniences.
- It may reuse useful infrastructure later, but reuse is not itself a design goal.

## 2. First Principles
- The mechanism serves the final product goal, not the shape of the existing architecture.
- The reader should see every sentence in source order.
- The reader should not deliberate from scratch on every sentence.
- The mechanism should preserve the feeling of a genuinely curious mind reading, not a report generator post-processing text.
- Broad prior knowledge is one of the mechanism's working advantages, but it must be activated by the text rather than replacing the text.
- The reader should be allowed to notice more than an individual human reader might notice, but it should not become text-detached, oracle-like, or generically clever.
- The mechanism should make user-visible thoughts legible and anchor them back to the source text.

## 3. Core Principle
- Sentence is the perceptual unit.
- Meaning unit is the cognitive unit.
- The reader sees every sentence, but usually integrates understanding over a larger local span.
- Sentence-level `zoom read` is a triggered mode, not the default mode.

## 4. What Broad Prior Knowledge Is For
- What a reader notices depends partly on what the reader already knows.
- A strong AI reader can bring unusually broad prior knowledge and associative range to reading.
- That breadth should surface references, patterns, tensions, and implications that are not obvious from surface reading alone.
- That breadth should recognize when a sentence belongs to a larger conceptual, historical, literary, or argumentative pattern.
- That breadth should sharpen interpretation by bringing the right background to the right passage at the right time.
- That breadth should not replace close reading with generic commentary.
- That breadth should not impose a detached theory on the text without textual activation.
- That breadth should not treat broad knowledge as permission for certainty when the text remains ambiguous.
- Prior knowledge is valid when it is activated by the current text and improves reading.
- Prior knowledge is invalid when it outruns the text and starts substituting for reading.

## 5. Core Runtime Objects
- `sentence`
  - the smallest source-ordered perceptual unit
- `local buffer`
  - the current rolling span of recently ingested sentences, usually around a paragraph or a short run of paragraphs
- `meaning unit`
  - a dynamically consolidated local span that is large enough to support one real interpretive move
- `trigger`
  - a local signal that the current sentence or span deserves closer reading
- `working pressure`
  - the hot hypotheses, open questions, tensions, motifs, and active local focus needed for the current reading step
- `anchor memory`
  - retained source-linked spans, callbacks, unresolved references, and bridgeable earlier records
- `reflective summaries`
  - slower-moving promoted understandings that should survive beyond the current local step
- `knowledge activation`
  - an epistemic object representing prior knowledge or associative context activated by the current text
- `move`
  - the next reading decision chosen from `advance`, `dwell`, `bridge`, or `reframe`

## 6. Tiered Reading State
- The engine of progress is unresolved interpretive pressure.
- Live reading state should be treated as tiered rather than as one mixed scratchpad.
- `working_pressure` contains the current hypotheses, open questions, tensions, motifs, settled versus unsettled distinctions, and immediate local focus that matter for the next move.
- `anchor_memory` contains retained anchors from earlier text, source-linked callbacks, unresolved references, bridgeable earlier traces, and motif-bearing records that may become newly important later.
- `reflective_summaries` contains promoted understandings that have enough repeated support to survive beyond the current local span.
- Writes, promotions, evictions, and retrievals should be explicit state operations rather than hidden prompt text.
- The point of the split is to keep hot interpretive pressure, bridgeable earlier material, and slower promoted understanding from collapsing into one blob.

## 7. Working Pressure
- `working_pressure` is the hot, controller-facing state for the current local reading moment.
- It should stay small, but it should not be aggressively pruned.
- It should contain:
  - `current_focus_span`
  - `current_frame`
  - `active_hypotheses`
  - `open_questions`
  - `active_tensions`
  - `live_motifs`
  - `bridge_candidates`
  - `local_unresolved_items`
  - `pressure_snapshot`
- Each hypothesis, open question, tension, and motif item should be typed and anchor-linked rather than free-form prompt text.
- Motifs in `working_pressure` should live as small typed motif objects rather than bare labels.
- `pressure_snapshot` should remain compact and controller-oriented, including dominant pressure kind, dominant pressure strength, interpretive temperature, local clarity, bridge-pull presence, and reframe-pressure presence.

## 8. Anchor Memory
- `anchor_memory` is retrieval-facing state for earlier material that may become newly important later.
- It should contain:
  - `anchor_records`
  - `anchor_relations`
  - `motif_index`
  - `unresolved_reference_index`
  - `trace_links`
- Each `anchor_record` should include sentence span, quote, locator, anchor kind, why it mattered, current status, and linked reaction or activation ids.
- Typed relations should be first-class in version one.
- Useful relation types include `echo`, `contrast`, `cause`, `support`, `question_opened_by`, `question_resolved_by`, and `callback`.
- `anchor_memory` should preserve bridgeable earlier material rather than summarize it away.

## 9. Reflective Summaries
- `reflective_summaries` is slower promoted understanding rather than hot local pressure.
- Promotion into `reflective_summaries` should be balanced rather than strict or permissive.
- Promotion should be chapter-first, but rare early book-level frames are allowed.
- It should contain:
  - `chapter_understandings`
  - `book_level_frames`
  - `durable_definitions`
  - `stabilized_motifs`
  - `resolved_questions_of_record`
  - `chapter_end_notes`
- Each reflective item should include statement, support anchor ids, confidence band, promoted_from, and status.
- Reflective summaries should preserve superseded history rather than replacing old items in place.
- Unresolved questions may persist across chapter boundaries by default if they are still live.
- State operations should stay explicit, including create, update, cool, drop, retain-anchor, link-anchors, promote, supersede, and reactivate.

## 10. State Operations
- State change should happen through explicit operations rather than hidden prompt drift.
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
- `working_pressure` should allow `create`, `update`, `cool`, `drop`, and `reactivate`.
- Every created or updated hot item should cite at least one source anchor or current sentence span.
- `working_pressure` should use balanced staged cooling rather than aggressive pruning or sticky permanence.
- Reactivation should create a new active item linked back to the old source rather than pretending the old item stayed continuously hot.
- `anchor_memory` should allow `retain_anchor`, `update`, `link_anchors`, and reactivation-through-source`.
- `anchor_memory` should not allow semantic drop by default at the mechanism layer.
- `reflective_summaries` should allow `promote`, `supersede`, and reactivation into `working_pressure`, but should not be direct bridge targets.
- Reflective meaning should not be silently updated in place; real revision should happen through `supersede`.
- `knowledge_activations` should allow `create`, `update`, `cool`, `drop`, and rejection.
- Event-to-operation mapping:
  - sentence ingest may create or update weak activations, local unresolved items, or bridge candidates, but should not usually create durable summaries
  - `zoom read` may strengthen or reject activations, create or update local hypotheses or tensions, identify a weight-bearing sentence, and justify `retain_anchor`
  - meaning-unit closure is the main mutation point for `retain_anchor`, hot-state updates, `link_anchors`, cooling, and occasional promotion
  - bridge success should strengthen linked anchors and relations and reactivate the target, but should not auto-promote reflective understanding
  - reframe should create a new active frame in `working_pressure`, and only later supersede reflective frames once stability is earned
  - chapter end is an opportunity for cooling and promotion, but moderate evidence alone is not enough for promotion
  - reconsolidation should append a revision record, may supersede reflective items, and must not erase earlier visible thought
- Invariants:
  - no durable interpretive item without source grounding
  - no silent promotion
  - no silent overwrite of reflective meaning
  - no bridge without a source-anchor target
  - cooling is not rejection
  - dropping from `working_pressure` must not erase meaningful earlier anchors or reflective history
  - reactivation should preserve historical continuity

## 11. Knowledge Activation Objects
- Knowledge activations should be tracked as epistemic objects rather than casual commentary.
- A knowledge activation is a text-triggered candidate use of prior knowledge that temporarily enters the reading state because it may sharpen interpretation.
- The mechanism should distinguish `recognition_confidence` from `reading_warrant`.
- `recognition_confidence` asks how confidently the system recognizes what outside source, concept, pattern, or echo is being invoked.
- `reading_warrant` asks how justified it is to use that activation in the current reading.
- Activation types may include exact quote, named reference, semantic echo, structural echo, conceptual invocation, rhetorical homage, and similar open-ended categories.
- Evidence should not be treated as a closed exhaustive taxonomy.
- Each activation should carry:
  - `trigger_anchor_id`
  - `activation_type`
  - `source_candidate`
  - `recognition_confidence`
  - `reading_warrant`
  - `role_assessment`
  - `evidence_hints`
  - `evidence_rationale`
  - `support_anchor_ids`
  - `conflict_anchor_ids`
  - `introduced_at_sentence_id`
  - `last_touched_sentence_id`
- `role_assessment` should distinguish ornamental, local, structural, or unresolved use.
- Lifecycle states:
  - `weak`
  - `plausible`
  - `strong`
  - `rejected`
  - `dropped`
- Recognition and reading warrant may rise or fall separately.
- A direct famous quote or named reference may enter with strong recognition quickly, but still needs reading warrant.
- Semantic or structural homage may begin weaker and strengthen through converging evidence.
- The mechanism should distinguish `book-grounded only`, `book-grounded + prior knowledge`, and separate search policy.

## 12. Knowledge-Use Policy
- Knowledge-use policy governs how the mechanism interprets the current span relative to outside knowledge.
- `book-grounded only` means the current interpretive step uses only book text up to the current point, plus high-level structure from the same book and earlier anchors or summaries derived from the same book.
- `book-grounded + prior knowledge` means prior knowledge is allowed to inform the current interpretive step because there is enough reading warrant to carry it.
- The default should be `book-grounded only`.
- Move into `book-grounded + prior knowledge` only when a live activation is text-earned and worth carrying.
- Strong recognition alone does not force prior-knowledge use.
- Allow prior-knowledge mode when `reading_warrant` is at least `plausible` and either recognition is strong or the local passage strongly supports the activation.
- The decision should usually be made after `zoom read` or during meaning-unit consolidation, not on every sentence.

## 13. Search Policy
- Search is not the same thing as knowledge-use mode.
- Version one should distinguish:
  - `no_search`
  - `defer_search`
  - `search_now`
- `no_search` means keep reading without outside lookup.
- `defer_search` means curiosity is real and text-earned, but reading is not blocked enough to justify interruption now.
- `search_now` means unresolved outside context materially affects the current reading, current trust is too weak without checking, or the current interpretive step is genuinely blocked.
- External search should remain rare and controller-approved.
- Good `search_now` cases include obscure allusions, half-recognized named references, or concepts whose identity materially affects the passage.
- Good `defer_search` cases include genuine curiosity where honest reading can still continue.
- Bad search cases include ornamental curiosity, proving weak associations the text has not earned, or interrupting reading just because the model wants more context.

## 14. Bridge Retrieval
- Bridge retrieval finds the earlier text the current span now depends on.
- It is not generic similarity search and not generic memory retrieval.
- Two target spaces:
  - first `anchor_memory`
  - fallback bounded `look-back source space`
- `look-back source space` remains book-grounded, not external search.
- The mechanism should try memory first; if memory is insufficient but backward dependency remains strong, use bounded look-back.
- If look-back finds the needed span, create or strengthen an anchor and then bridge through that source anchor.
- Trigger bridge retrieval when the controller detects real `bridge_pull`, when `zoom read` returns a `bridge_candidate`, or when the current span strongly activates a live motif, unresolved question, earlier definition, or active tension.
- Retrieval channels:
  - `direct relation channel`
  - `motif channel`
  - `unresolved pressure channel`
  - `structural echo channel`
  - `semantic fallback channel`
- Candidate records should contain:
  - `target_anchor_id`
  - `target_space`
  - `retrieval_channel`
  - `relation_type`
  - `supporting_evidence`
  - `pressure_link`
  - `score`
  - `why_now`
- Scoring should consider dependency strength, pressure relevance, relation quality, anchor importance, text-earnedness, and recency only as a weak factor.
- Version one should usually return one primary bridge anchor and may keep up to two supporting anchors.
- Prior reactions may help explanation or evaluation, but bridge targets should remain source anchors rather than reaction objects.
- One-hop traversal is the default; deeper traversal should remain rare and strongly supported.
- If retrieval is weak, do not fake a bridge; fall back to `dwell` or `advance`.

## 15. Book Survey First
- Before deep reading, the reader performs a light survey pass to build orientation.
- The survey should include title, table of contents, chapter boundaries, openings, closings, and obvious structural pivots.
- The survey is for orientation only.
- It must not replace sequential reading.
- It must not import future paragraph-level knowledge into the live reading process.

## 16. Qualitative Escalation Gates
- The mechanism needs escalation gates because selective reading still has to decide when to keep accumulating, when to `zoom read`, and when to force reevaluation.
- At the design layer, these gates should remain qualitative rather than pretending to have false numeric precision.
- Core gate states:
  - `quiet`
  - `watch`
  - `hot`
  - `must_evaluate`
- Integrity pressure should outrank ordinary salience.
- Strong callback pressure plus live unresolved pressure may push a span toward bridge-oriented attention.
- Cadence may force reevaluation, but may never force false closure.
- Paragraph boundaries may lower the bar for reevaluation, but may never decide by themselves.
- Numeric cutoffs may later be introduced only if evaluation or algorithmic support shows they describe desired behavior rather than fake it.

## 17. Main Reading Loop
- Ingest the next sentence in source order.
- Mark it as seen.
- Update the local buffer.
- Run lightweight trigger detection as an always-on ensemble of cheap signals rather than a full interpretive call.
- Combine trigger signals with current `working_pressure` to estimate whether escalation is warranted.
- Keep accumulating unless pressure or boundary conditions justify escalation.
- Use hybrid meaning-unit closure rather than naive fixed segmentation.
- Trigger `zoom read` only when local honesty requires higher resolution.
- Update tiered state through explicit operations.
- Ask the controller for the next move.
- Emit a user-visible reaction only when warranted.
- Continue from the correct sentence cursor without skipping coverage.

## 18. Controller
- The controller chooses the next move from `advance`, `dwell`, `bridge`, or `reframe`.
- The controller should be LLM-first with hard-veto guardrails rather than a fully deterministic router.
- The controller should route according to unresolved interpretive pressure under coverage discipline.
- `bridge` requires a real source-anchor target rather than vague similarity.
- `reframe` requires genuine frame pressure rather than decorative abstraction.

## 19. Version-One Candidate-Boundary Signals
- Candidate-boundary signals are cheap local heuristics, not full interpretive judgments.
- They may include:
  - discourse turn
  - definition or distinction
  - claim pressure
  - sentence role shift
  - local cohesion drop
  - callback activation
  - pressure update proxy
  - cadence guardrail

## 20. How Focus Is Selected
- Focus selection should follow unresolved interpretive pressure rather than fixed section traversal.
- Integrity pressure should outrank ordinary salience when deciding whether to stay, bridge, or escalate.
- Live unresolved motifs, questions, tensions, bridge pull, and callback pressure should all influence focus.
- Coverage still matters; the mechanism must not wander indefinitely.

## 21. Version-One Trigger Ensemble
- Trigger detection should be an always-on ensemble of cheap signals rather than a single expensive interpretive call.
- Trigger families include:
  - integrity triggers
  - salience triggers
  - knowledge-risk triggers
- Triggering exists to protect important lines from being flattened by ordinary accumulation.

## 22. Trigger Ensemble Output Schema
- Trigger output states should distinguish:
  - `no_zoom`
  - `monitor`
  - `zoom_now`
- The trigger layer should be controller-facing and cheap enough to run continuously.

## 23. When To Zoom To Sentence Level
- Sentence-level zoom is reserved for lines that actually earn higher resolution.
- Zoom should be triggered by interpretive need, not by generic importance or local novelty alone.
- The design explicitly rejects sentence-by-sentence deliberation as the default mode.

## 24. LLM Call Policy
- The main LLM should not be called on every sentence.
- Deterministic or cheap mechanisms should handle ordinary intake, signal gathering, retrieval preparation, schema validation, and hard guardrails where possible.
- LLM-heavy nodes should be reserved for behavior-defining interpretation and control.

## 25. Zoom Read Call
- `zoom_read` is the sentence-level interpretive zoom for locally hot lines.
- It should clarify what the line is doing, identify weight-bearing language, update local state, and justify anchor retention when warranted.
- It must remain text-grounded and must not over-promote local observations into durable summaries.

## 26. What Each Interpretive Call Should Return
- Behavior-defining calls should return structured results rather than raw prose.
- Expected outputs include:
  - interpretation or closure decision
  - explicit state updates
  - anchor and bridge relevance
  - optional reaction candidacy
  - explicit uncertainty or refusal where warranted

## 27. Prompt Packet
- Interpretive calls should receive a structured packet rather than arbitrary chunks.
- The packet should include:
  - structural frame
  - focal span
  - local context
  - working memory / pressure state
  - retrieved anchors
  - policy snapshot
  - output language contract

## 28. Non-Cheating Constraint
- Live interpretive calls must not use future unseen text.
- Survey context may include coarse structural orientation, but not future paragraph-level interpretive knowledge.
- The design treats this as a hard constraint, not a style preference.

## 29. User-Visible Output
- The durable visible object is an anchored reaction, not a section-centered wrapper.
- A reaction should center on:
  - `reaction_id`
  - `primary_anchor`
  - `thought`
  - optional `related_anchors`
  - optional `reconsolidation_record_id`
  - `created_at`
- Reactions should be optional and quality-gated rather than emitted at every interpretive step.

## 30. Reconsolidation
- Reconsolidation is `append + link`, never rewrite-in-place.
- Earlier persisted thoughts remain immutable.
- Later thoughts must stay independently anchored to later reading moments.
- Reconsolidation is reserved for material interpretive change, not every minor refinement.

## 31. Anti-Miss Safeguards
- Anti-miss behavior should exist across the mechanism rather than in one fallback node.
- Important lines should be protected through:
  - sentence-order intake
  - trigger detection
  - bridge retrieval
  - backward sweep
  - chapter consolidation

## 32. Persistence and Resume
- Persist:
  - reading position
  - local continuity state
  - durable tiered state
  - resume metadata
- Resume modes:
  - `warm_resume`
  - `cold_resume`
  - `reconstitution_resume`
- Resume invariants:
  - no loss of durable anchors
  - no loss of visible reactions
  - no silent mutation of reflective summaries
  - no pretending reconstructed hot state is warm state

## 33. Relationship To The Existing Mechanism
- The new mechanism is not defined by `iterator_v1`'s ontology or convenience structures.
- Shared runtime infrastructure may be reused when it genuinely serves the design.
- The new mechanism should live behind shared runtime boundaries rather than becoming another isolated silo.
- `iterator_v1` remains the live/default mechanism until an explicit promotion decision is made.

## 34. Success Standard
- Success is not “it runs.”
- Success means the mechanism preserves the product target:
  - text-groundedness
  - self-propelled curiosity
  - selective legibility
  - coherent accumulation
  - reader value under realistic runtime constraints

## 35. Decisions Made So Far
- The design already fixes several architectural positions:
  - sentence intake in source order
  - meaning-unit cognition
  - triggered zoom rather than sentence-by-sentence deliberation
  - explicit tiered state
  - explicit state operations
  - source-anchor bridge targets
  - append-and-link reconsolidation

## 36. Calibration and Configuration Layer
- The design includes a versioned `reader_policy` layer.
- Policy domains include:
  - gate
  - controller
  - knowledge
  - search
  - bridge
  - resume
  - logging
- Policy tuning should not silently redefine the mechanism's ontology.

## 37. Failure Modes And Degradation Patterns
- The design expects explicit failure taxonomy rather than vague “quality drift.”
- Canonical failure families include:
  - coverage
  - attention
  - meaning-unit
  - controller pacing
  - knowledge
  - bridge memory
  - state-memory health
  - historical integrity

## 38. Instrumentation and Observability Contract
- Required observability layers include:
  - `event_stream`
  - `checkpoint_summaries`
- The mechanism should leave enough evidence to debug behavior and evaluate it without exposing raw private traces as the primary product surface.

## 39. Evaluation Mapping And Acceptance Criteria
- Evaluation must align with the shared project evaluation frame rather than inventing a new product definition.
- The design expects:
  - node-level quality checks
  - end-to-end product-fit checks
  - runtime-viability checks
  - prompt-traceability metadata
- Acceptance should be grounded in realistic runtime conditions.

## 40. Open Design Questions
- The design still leaves some implementation-level questions open.
- These should be made explicit rather than implicitly decided in code.
- Current repo-local tracking for those questions lives in `open-questions.md`.

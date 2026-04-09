# Attentional V2 Phase 9 Compatibility Cutover Roadmap

Purpose: define the remaining Phase 9 route for switching the product's main reading path onto `attentional_v2` without mixing that cutover with later frontend-native redesign work.
Use when: planning or implementing the remaining default-cutover work for `attentional_v2`.
Not for: stable mechanism authority, field-level API schemas, or the later post-cutover presentation initiative.
Update when: the Phase 9 cutover boundary, workstreams, gates, or task routing change.

## Status
- Completed on `2026-04-08`.
- Landed results:
  - normal product deep-reading launches now default to `attentional_v2`
  - `iterator_v1` remains callable as an explicit fallback and legacy-resume path
  - the current routed frontend surfaces were validated on the compatibility-first overview/chapter/marks path
  - stable docs, current-state, and task routing now all treat V2-native presentation as the next separate lane rather than as unfinished Phase 9 scope
- Current post-Phase-9 posture as of `2026-04-09`:
  - the next active migration lane is `V2-native reading presentation`
  - do not keep the old `iterator_v1` / section-first presentation as a co-equal product design target
  - keep that older presentation shape only as a temporary compatibility shell while V2-native surfaces land
  - do not spend on a cleanup-only V1 display pass before the V2-native lane starts

## Summary
- Phase 9 now ends at `compatibility cutover`, not at a full frontend-native redesign.
- `attentional_v2` should become the product's main reading mechanism through the current compatibility layer first.
- `long-span` repair remains a parallel evidence lane, but it is not a hard blocker on Phase 9 compatibility implementation.
- `iterator_v1` remains available as an explicit fallback or override during and after the cutover slice.

## Phase 9 Boundary
- Inside Phase 9:
  - backend default-mechanism cutover for normal deep-reading runs
  - compatibility validation on the current routed frontend surfaces
  - stable-doc and task-routing updates for the new default direction
  - explicit default-cutover decision
- Outside Phase 9:
  - redesigning the routed frontend around `reading_locus`, `primary_anchor`, and chapter-text-native rendering
  - retiring section-first chapter/detail and marks surfaces
  - broader product polish, presentation refinement, and portfolio packaging

## Mainline Workstreams
- `Workstream A: parallel long-span evidence repair`
  - Finish the targeted same-run repair for `value_of_others_private_en__8_10`.
  - Treat this as a parallel evidence-cleanup lane, not as the gate that blocks compatibility implementation from starting.
  - Only reopen the cutover decision if the repaired long-span result surfaces a severe contradiction to current product-readiness claims.
- `Workstream B: backend default-cutover prep`
  - Inventory every place where `iterator_v1` is still treated as the implicit default for normal product runs.
  - Switch normal deep-reading launches to default to `attentional_v2` once compatibility validation passes.
  - Keep explicit mechanism override and fallback support so `iterator_v1` remains callable for debugging, recovery, or comparison.
  - Do not revive the retired `book_analysis` lane as part of this cutover.
- `Workstream C: routed frontend compatibility validation`
  - Keep the current routed frontend section-era UI model for this slice.
  - Validate that the existing overview, chapter, activity, and marks surfaces work correctly against `attentional_v2` compatibility outputs.
  - Use additive `reading_locus` and anchor-native fields only as migration helpers in this slice, not as the main UI model yet.
  - Fix compatibility gaps only to the extent needed for the current product path to function cleanly on `attentional_v2`.
- `Workstream D: explicit cutover decision and landing`
  - Make one explicit decision that the product's default deep-reading path now runs on `attentional_v2`.
  - Update the stable/shared docs that define defaultness, runtime expectations, and public-state sourcing in the same task.
  - Preserve `iterator_v1` as a non-default fallback rather than deleting it in Phase 9.

## Phase 9 Acceptance
- Product runs default to `attentional_v2` for the normal deep-reading path.
- Current routed frontend surfaces remain usable through compatibility outputs without a section-model rewrite.
- `excerpt surface v1.1` remains the primary formal excerpt evidence bundle for the cutover decision.
- The long-span repair lane is either:
  - cleanly repaired, or
  - still running but no longer showing evidence that contradicts the cutover decision strongly enough to block it.
- Stable docs, current-state, and task routing all agree that:
  - `attentional_v2` is the default direction
  - V2-native frontend work is a post-Phase-9 initiative

## Post-Phase-9 Initiatives
- `V2-native reading presentation`
  - redesign routed frontend surfaces around chapter text plus anchored reactions
  - promote `reading_locus`, `primary_anchor`, and `related_anchors` from additive helpers to primary UI truth
  - current implementation order:
    - first fix truth/visibility gaps on the routed in-progress overview surface
    - then make live V2 reading state legible on `/books/:id`
    - then redesign chapter and marks surfaces around anchors, loci, and thought lineage
  - do not preserve the old section-first presentation as a parallel product model during this lane
- `Section-first retirement`
  - intentionally remove the old section-first dependency from chapter/detail and marks surfaces
  - retire compatibility requirements only after the V2-native presentation is stable
  - this remains a follow-on cleanup lane, not the first move
- `Product polish`
  - refine presentation, interaction polish, and portfolio/demo packaging after the main mechanism cutover is already done

## Task Routing
- Completed implementation lane:
  - `TASK-PHASE9-COMPAT-CUTOVER`
- Active next migration lane:
  - `TASK-V2-NATIVE-READING-PRESENTATION`
- Parallel evidence-cleanup lane:
  - `TASK-ACCUMULATION-BENCHMARK-V1`
- Parallel but narrower blocked eval lane:
  - `TASK-PHASE9-DECISIVE-EVAL`
- Post-Phase-9 deferred UI retirement lane:
  - `TASK-FE-SECTION-RETIREMENT`

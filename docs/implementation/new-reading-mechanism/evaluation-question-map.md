# New Reading Mechanism Evaluation Question Map

Purpose: turn the current evaluation work into an explicit question map before dataset and corpus design begins.
Use when: deciding what benchmark datasets to curate, which questions belong to this implementation project, or how to separate cross-mechanism evaluation from attentional-specific proof work.
Not for: stable evaluation constitution, one-off benchmark reports, or final acceptance conclusions.
Update when: a new evaluation question is added, a question changes owner, or a question moves from temporary planning into a stable doc/report.

## Working Rules
- Question-first, dataset-second.
- Dataset and corpus design must answer explicit questions instead of collecting convenient texts first.
- Cross-mechanism evaluation work is still part of the current `attentional_v2` implementation job.
  - We cannot decide whether the new mechanism is viable without comparing it against `iterator_v1`.
  - The stable owner of the comparison frame is still `docs/backend-reader-evaluation.md`.
- Mechanism-specific attribution questions are also part of the current `attentional_v2` implementation job.
  - They tell us whether the mechanism is honoring its own promises rather than merely staying schema-valid.
- Runtime and compatibility gate questions are not optional.
  - A mechanism that looks good locally but fails resume, marks, or shared-surface compatibility is not ready.

## Question Families
- `cross_mechanism_product_comparison`
  - compare `attentional_v2` against `iterator_v1` under the shared product/evaluation frame
- `attentional_specific_attribution`
  - test whether `attentional_v2`'s own distinctive design promises are actually being met
- `runtime_and_compatibility_gate`
  - test whether the mechanism remains operationally trustworthy and integration-safe

## Question Map
| ID | Family | Exact question | Why this belongs in the current `attentional_v2` job | Stable owner | Likely evidence shape | Dataset / corpus need | Current status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EQ-CM-001 | `cross_mechanism_product_comparison` | Under realistic constraints, does `attentional_v2` preserve the product's intended co-reading mind better than `iterator_v1` overall? | This is the actual product-level promotion question for the new mechanism. | `docs/backend-reader-evaluation.md` | pairwise + rubric end-to-end comparison | chapter corpus | `initial chapter evidence exists` |
| EQ-CM-002 | `cross_mechanism_product_comparison` | On local passages, does `attentional_v2` take better reading steps than `iterator_v1`? | We need local comparison evidence, not only whole-run impressions. | `docs/backend-reader-evaluation.md` | excerpt-case pairwise + rubric | excerpt dataset | `not started` |
| EQ-CM-003 | `cross_mechanism_product_comparison` | Across larger spans, does `attentional_v2` accumulate understanding more coherently than `iterator_v1`? | Coherent accumulation is one of the mechanism's main promised wins. | `docs/backend-reader-evaluation.md` | chapter trajectory comparison | chapter corpus | `initial chapter evidence exists` |
| EQ-CM-004 | `cross_mechanism_product_comparison` | Does `attentional_v2` leave behind a more useful durable reading trail than `iterator_v1`? | The product includes marks, return, and later recall, not only first-pass reading. | `docs/backend-reader-evaluation.md` | durable-trace audit + re-entry judging | excerpt cases + persisted trace fixtures | `in_progress` |
| EQ-CM-005 | `cross_mechanism_product_comparison` | Is `attentional_v2` operationally viable enough relative to `iterator_v1` for controlled product use? | A mechanism does not win if quality appears only at unrealistic reliability, latency, or cost. | `docs/backend-reader-evaluation.md` | deterministic runtime metrics + gate checks | runtime fixtures + chapter runs | `in_progress` |
| EQ-AV2-001 | `attentional_specific_attribution` | Does `attentional_v2` preserve sentence-order intake honesty and avoid future-text leakage? | This is a core design promise, not a generic reader question. | `docs/backend-reading-mechanisms/attentional_v2.md` | deterministic integrity checks + targeted rubric cases | excerpt dataset | `partially scaffolded` |
| EQ-AV2-002 | `attentional_specific_attribution` | Does `attentional_v2` produce strong meaning-unit closure instead of shallow sentence sparks or vague paragraph blur? | Meaning-unit reasoning is the mechanism's main interpretive unit. | `docs/backend-reading-mechanisms/attentional_v2.md` | local rubric judging | excerpt dataset | `initial judged evidence exists` |
| EQ-AV2-003 | `attentional_specific_attribution` | Does `attentional_v2` choose `advance`, `dwell`, `bridge`, and `reframe` well? | Controller-move quality is central to whether the mechanism feels alive rather than procedural. | `docs/backend-reading-mechanisms/attentional_v2.md` | attributed local-case judging | excerpt dataset | `initial judged evidence exists` |
| EQ-AV2-004 | `attentional_specific_attribution` | When `attentional_v2` bridges backward, are the links honest, source-grounded, and worth making? | Bridge resolution is a signature mechanism behavior and a likely failure mode. | `docs/backend-reading-mechanisms/attentional_v2.md` | targeted bridge-case judging | excerpt dataset | `initial judged evidence exists` |
| EQ-AV2-005 | `attentional_specific_attribution` | Are emitted visible reactions selective, worthwhile, and faithfully anchored? | Good runtime does not help if visible thoughts become noisy or weakly anchored. | `docs/backend-reading-mechanisms/attentional_v2.md` | local rubric judging + structural anchor checks | excerpt dataset | `partially scaffolded` |
| EQ-AV2-006 | `attentional_specific_attribution` | Does reconsolidation preserve historical integrity through append-and-link rather than silent overwrite? | This is one of the clearest places where the mechanism must prove it is not regressing into convenience. | `docs/backend-reading-mechanisms/attentional_v2.md` | structural checks + judged later-interpretation cases | excerpt dataset + persisted history fixtures | `partially scaffolded` |
| EQ-AV2-007 | `attentional_specific_attribution` | Is resume and reconstitution honest enough to feel like the same reading mind without hidden oversized rereads? | Resume quality is part of the mechanism's identity, not just an ops feature. | `docs/backend-reading-mechanisms/attentional_v2.md` | runtime fixtures + judged re-entry cases | resume fixtures + chapter excerpts | `in_progress` |
| EQ-AV2-008 | `attentional_specific_attribution` | Do public/API compatibility projections preserve attentional thought direction faithfully enough during the migration period? | The mechanism should not lose its value when adapted upward into current surfaces. | `docs/backend-reading-mechanisms/attentional_v2.md` | compatibility audit + spot judging | persisted chapter/activity/marks fixtures | `partially scaffolded` |
| EQ-GATE-001 | `runtime_and_compatibility_gate` | Are shared cursor ids, anchor locators, reaction ids, and resume bounds always structurally valid? | These are hard gates, not style preferences. | temp implementation docs now; later reports | deterministic integrity checks | runtime fixtures | `partially scaffolded` |
| EQ-GATE-002 | `runtime_and_compatibility_gate` | Do analysis-state, activity, chapter, and marks surfaces stay schema-valid and usable during migration? | Current product compatibility still matters while section-first surfaces exist. | temp implementation docs now; later reports | compatibility tests + fixture audits | persisted API fixtures | `partially scaffolded` |
| EQ-GATE-003 | `runtime_and_compatibility_gate` | Can the mechanism complete runs, resume correctly, and stay within acceptable latency/cost bounds? | Runtime viability is a standing gate for promotion. | `docs/backend-reader-evaluation.md` | deterministic runtime metrics | runtime fixtures + chapter corpus | `in_progress` |

## First Pass Status
- `2026-03-24`: the first corrected `mechanism_integrity` run completed over the tracked curated `v2` excerpt packs at [attentional_v2_integrity_v2_20260324-152539](/Users/baiweijiang/Documents/Projects/reading-companion/reading-companion-backend/eval/runs/attentional_v2/attentional_v2_integrity_v2_20260324-152539).
- Questions materially advanced by that run:
  - `EQ-AV2-001`
  - `EQ-AV2-002`
  - `EQ-AV2-003`
  - `EQ-AV2-004`
  - `EQ-AV2-005`
  - the judged local-case slice of `EQ-AV2-006`
- What the run established:
  - the tracked curated `v2` excerpt family is viable as a real benchmark input set
  - the local harness can evaluate all `32` cases without structural failure
  - `attentional_v2` is not yet at the planned local acceptance bar
- `2026-03-28` to `2026-03-31`: chapter-core cross-mechanism reruns produced real but still limited evidence for `EQ-CM-001` and `EQ-CM-003`.
  - the English retry-2 broader rerun and the later focused two-case judged rerun now show that broader semantic comparison is active rather than hypothetical
  - current evidence is still mixed and too narrow to close the overall product-level promotion question
- Main first-pass weaknesses:
  - Chinese local-case quality trails English sharply
  - `callback_bridge` and `reconsolidation_later_reinterpretation` are the weakest buckets
  - all evaluated local cases still selected `advance`, so move-diversity evidence is still immature
- What is still not answered by this run:
  - cross-mechanism local comparison against `iterator_v1`
  - chapter-scale trajectory comparison
  - durable-trace / re-entry comparison
  - runtime viability / latency / cost comparison
  - the structural persisted-history half of `EQ-AV2-006`

## What This Means For Current Work
- The current new-mechanism implementation project still has to do both:
  - cross-mechanism comparison work
  - attentional-specific attribution work
- Cross-mechanism work is not "someone else's later project."
  - It is part of deciding whether `attentional_v2` is actually good enough.
- The source-type mapping is now explicit enough to use as a routing rule rather than as an unfinished prep task:
  - excerpt-case dataset
  - chapter corpus
  - runtime/resume fixture set
  - persisted compatibility fixture set
- The practical next control step is:
  - keep excerpt hardening bounded to the cases that still block trusted comparison
  - return the main cadence to chapter-corpus and runtime/resume questions once that blocker is either accepted or cleared
- `2026-04-01` minimum-focus compression for the current project stage:
  - keep as the only primary eval dimensions:
    - `reader_character.selective_legibility`
      - can be answered with the smallest local reading pack that still shows whether the mechanism notices worthwhile things and expresses them clearly
    - `reader_character.coherent_accumulation`
      - is still best answered by `EQ-CM-003`
      - chapter-scale accumulation remains the clearest "why the new mechanism is better or worse" interview question
    - `reader_value.insight_and_clarification`
      - should be judged as real clarifying value, not as generic pleasantness or verbosity
  - keep only as cheap sanity guards, not as primary success targets:
    - `EQ-AV2-001`
    - `EQ-GATE-001`
    - `EQ-GATE-002`
  - pause as active judged targets:
    - `EQ-CM-001`
    - `EQ-CM-002`
    - `EQ-CM-004`
    - `EQ-CM-005`
    - `EQ-AV2-002`
    - `EQ-AV2-003`
    - `EQ-AV2-004`
    - `EQ-AV2-005`
    - `EQ-AV2-006`
    - `EQ-AV2-007`
    - `EQ-AV2-008`
    - `EQ-GATE-003`
  - interpretation:
    - this project no longer aims to answer every evaluation question before moving forward
    - it aims to answer only the three north-star dimensions that most directly support product improvement and a strong interview explanation of mechanism tradeoffs
- `2026-04-01`: MVP gate runners are now landed and the first diagnostic launches have completed.
  - `reading-companion-backend/eval/attentional_v2/run_durable_trace_reentry.py`
  - `reading-companion-backend/eval/attentional_v2/run_runtime_viability.py`
  - first diagnostic launches:
    - `bgjob_durable_trace_reentry_gate_20260401` failed before summary output because case failures were not yet isolated
    - `bgjob_runtime_viability_gate_20260401` completed, but the result mix is diagnostic-only because unsupported-plan, quota, and runtime failures are still entangled
  - completed follow-up:
    - `bgjob_runtime_viability_gate_serialfix_20260401`
    - unsupported-plan/model entanglement is cleared, but the fresh runtime summary still shows shared quota cooldown as the dominant blocker
  - completed next-lane probe:
    - `bgjob_durable_trace_reentry_gate_parallel3_20260401`
    - the durable-trace / re-entry rerun completed with `0` evaluated cases and `8` partial failures, so it is provider-pressure evidence rather than usable comparison evidence
    - repeated direct probes against `MiniMax-M2.7-highspeed` still return raw `429 rate_limit_error: usage limit exceeded (2056)`
    - local same-target concurrency is now capped at `2`
    - the next durable rerun default is reset back to `--case-workers 1`
- After the first corrected local run, there is now one more explicit rule:
  - broader semantic comparison work should not be treated as authoritative until the weak local excerpt buckets have gone through dataset-quality hardening
  - see [dataset-quality-hardening.md](/Users/baiweijiang/Documents/Projects/reading-companion/docs/implementation/new-reading-mechanism/dataset-quality-hardening.md)

## Dataset Design Implications
- `excerpt dataset`
  - best for local reading behavior, bridge, reaction, reconsolidation, and some durable-trace questions
- `chapter corpus`
  - best for whole-reader product fit, span trajectory, and runtime viability comparison
- `runtime/resume fixtures`
  - best for resume honesty, mechanism-key continuity, and hard structural gates
- `persisted compatibility fixtures`
  - best for activity, chapter, marks, and public-surface faithfulness during migration

## Promotion Rule
- Promote stable cross-mechanism question families into `docs/backend-reader-evaluation.md`.
- Promote stable mechanism-specific proof questions into `docs/backend-reading-mechanisms/attentional_v2.md`.
- Keep dataset design, case packaging, sample sizes, thresholds, and current implementation status in the temporary workspace until they become reviewed benchmark assets or stable methodology.

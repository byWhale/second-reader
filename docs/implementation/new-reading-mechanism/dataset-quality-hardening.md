# New Reading Mechanism Dataset Quality Hardening

Purpose: define how the `attentional_v2` benchmark family should be strengthened from a benchmark-grade dataset into a higher-trust evaluation asset.
Use when: deciding whether to keep evaluating on the current dataset, how to review weak cases, or how to combine automated judges with human review.
Not for: stable evaluation constitution, one-off benchmark results, or source-book acquisition rules.
Update when: the review workflow changes, status tiers change, or the hardening gate for broader evaluation changes.

## Why This Work Exists
- Dataset quality is now a first-class Phase 9 concern.
- A weak dataset can push the mechanism work in the wrong direction.
- The first corrected `mechanism_integrity` run proved that:
  - the tracked curated `v2` excerpt family is viable as a benchmark input set
  - but some weak-bucket failures may reflect case-quality problems, mechanism-quality problems, or both
- We therefore need a hardening layer before trusting broader semantic evaluation too much.

Authoritative first-pass evidence:
- `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_integrity_v2_20260324-152539/`

## Current Decision
- Do **not** treat the current curated `v2` excerpt packs as final ground truth.
- Do treat them as:
  - structurally trustworthy benchmark inputs
  - serious first-pass semantic cases
  - still eligible for review and promotion
- Pause broader semantic comparison work until the weakest local buckets are reviewed.
- It is still acceptable to continue purely structural or runtime-gate work in parallel when that work does not depend on the semantic case labels being final.

## Truth Layers
### Strong factual truth
These parts should already be treated as high-trust:
- source-book provenance
- canonical parse outputs
- sentence ids and excerpt boundaries
- dataset manifests, split manifests, and package versioning
- language-track assignment
- chapter-role and bucket-count quotas

### Reviewable evaluative truth
These parts are not final by default:
- whether a passage is the right case for a given question family
- whether the assigned bucket is the best bucket
- whether the current `judge_focus` captures the live pressure
- whether the expected local move is underdetermined or overdetermined
- whether a case is too noisy, too easy, or too misleading

## Review Status Ladder
Every semantic case should eventually carry one of these meanings, whether or not the exact field is stored in the dataset immediately:

1. `builder_curated`
- selected by the corpus builder plus current curation rules
- suitable for first-pass benchmarking
- not yet strong enough to be treated as final ground truth

2. `llm_reviewed`
- reviewed by one or more offline judge passes focused on the case itself
- good for scaling review coverage
- still not sufficient as the only authority

3. `human_reviewed`
- explicitly checked by a human against the source passage and question family
- suitable for stronger benchmark trust

4. `gold`
- human-reviewed and retained after disagreement or adversarial review
- use for the highest-trust local comparison slices

## What Must Be Improved First
The first hardening pass should focus on the buckets that were weakest in the first corrected `mechanism_integrity` run:
- `callback_bridge`
- `reconsolidation_later_reinterpretation`

Also prioritize:
- Chinese curated excerpt cases
- any case where the current harness always yields `advance` and the case is supposed to test richer move pressure
- any case where the judged failure might come from label ambiguity rather than obvious mechanism weakness

## Hardening Workflow
### Stage 1: Factual audit
For each targeted case, verify:
- source book and chapter are correct
- sentence ids match the stored excerpt text
- excerpt boundaries are not off by one
- no boilerplate or truncation artifacts remain
- the case still belongs to the intended language track

This stage can be done mechanically and should remove obvious broken cases before semantic review.

### Stage 2: LLM case audit
Run one or more offline judge passes that review the **case design**, not the mechanism output.

For each case, ask:
- is the assigned bucket plausible?
- is the `judge_focus` specific and fair?
- is the `selection_reason` aligned with the actual excerpt?
- is this case ambiguous enough that multiple local moves could be reasonable?
- is this case too weak, too noisy, or too trivial for benchmark use?

Desired output:
- `keep`
- `rewrite_focus`
- `relabel_bucket`
- `demote_to_reserve`
- `drop`

### Stage 3: Adversarial disagreement pass
Use a separate review prompt or separate judge call to argue the opposite side:
- why might this case be mislabeled?
- what would make a different move defensible?
- where could the current label induce unfair penalization?

This is especially important for:
- bridge cases
- reconsolidation-worthiness cases
- subtle Chinese narrative passages

### Stage 4: Human review on flagged cases
Human review should be reserved for:
- cases where automated reviewers disagree
- cases in the weak buckets
- cases intended for `gold` status
- cases that materially influence acceptance decisions

The human reviewer should decide:
- keep as-is
- rewrite the focus
- relabel the bucket
- move to reserve
- drop and replace

### Stage 5: Re-freeze and rerun
After edits:
- freeze a new reviewed split or reviewed dataset version
- rerun `mechanism_integrity`
- compare whether the failures still point at the mechanism instead of case ambiguity

## How LLM-As-Judge Can Help
### Good uses
LLM review is useful for:
- scaling first-pass review over all cases
- spotting mislabeled buckets
- checking whether the stated case purpose matches the actual excerpt
- finding over-broad or under-specified `judge_focus`
- surfacing disagreement candidates for human review

### What it should not replace
LLM review should **not** be treated as the final authority for:
- the strongest “ground truth” designation
- the final decision on ambiguous or high-impact cases
- the only review on weak buckets when the mechanism direction could change because of the result

### Recommended review pattern
- `single-pass reviewer`
  - cheap first-pass audit over the whole curated set
- `dual-pass disagreement`
  - one prompt argues for the current label, one tries to break it
- `human-on-flagged`
  - a person only reviews disputed or high-impact cases

That gives us leverage without pretending automated review is identical to expert truth.

## Practical Quality Gate
Before trusting broader semantic comparison too much, the excerpt family should satisfy all of these:
- no factual boundary errors in the targeted review slice
- weak buckets have gone through at least LLM review and disagreement review
- flagged cases have explicit keep/relabel/drop decisions
- at least the first high-impact weak cases have human review
- rerun of `mechanism_integrity` shows the same failures are not mostly caused by mislabeled cases

## To-Do Now
1. Add a case-audit workflow for semantic dataset review.
2. Build an offline LLM case-review harness for curated excerpt cases.
3. Run the first case audit over:
   - `callback_bridge`
   - `reconsolidation_later_reinterpretation`
   - weakest Chinese local cases
4. Promote reviewed cases out of `builder_curated` where justified.
5. Freeze the reviewed local benchmark slice.
6. Rerun `mechanism_integrity` on that reviewed slice before trusting broader semantic evaluation.

## Recommendation For Immediate Next Step
- Do not jump straight into broader semantic comparison yet.
- First harden the local excerpt benchmark slice.
- The best immediate move is:
  - build the LLM-based case-audit workflow
  - run it on the weak buckets
  - then decide which cases require human review

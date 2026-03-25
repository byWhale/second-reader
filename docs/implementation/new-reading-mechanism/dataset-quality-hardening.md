# New Reading Mechanism Dataset Quality Hardening

Purpose: define how the `attentional_v2` benchmark family should be strengthened from a benchmark-grade dataset into a higher-trust evaluation asset.
Use when: deciding whether to keep evaluating on the current dataset, how to review weak cases, or how to combine automated judges with human review.
Not for: stable evaluation constitution, one-off benchmark results, or source-book acquisition rules.
Update when: the review workflow changes, status tiers change, or the hardening gate for broader evaluation changes.

## External Design Inputs
This hardening workflow is informed by a small set of external benchmark and data-governance references:
- [Data Statements for NLP](https://aclanthology.org/Q18-1041/)
- [Datasheets for Datasets](https://cacm.acm.org/research/datasheets-for-datasets/)
- [Hugging Face Dataset Cards](https://huggingface.co/docs/hub/en/datasets-cards)
- [Klie et al. 2024 on annotation quality management](https://aclanthology.org/2024.cl-3.1/)

We are not copying those frameworks literally. We are using their strongest practical ideas:
- document provenance and curation rationale
- keep review guidance visible
- use iterative quality management
- include human inspection where benchmark trust matters
- avoid treating versioned data as automatically trustworthy

## Why This Work Exists
- Dataset quality is now a first-class Phase 9 concern.
- A weak dataset can push the mechanism work in the wrong direction.
- The first corrected `mechanism_integrity` run proved that:
  - the tracked curated `v2` excerpt family is viable as a benchmark input set
  - but some weak-bucket failures may reflect case-quality problems, mechanism-quality problems, or both
- We therefore need a hardening layer before trusting broader semantic evaluation too much.

Authoritative first-pass evidence:
- `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_integrity_v2_20260324-152539/`
- first packet-level machine-side case audit:
  - `reading-companion-backend/eval/runs/attentional_v2/case_audits/attentional_v2_zh_weak_buckets_round1__20260325-003459/`

## Current Decision
- Do **not** treat the current curated `v2` excerpt packs as final ground truth.
- Do treat them as:
  - structurally trustworthy benchmark inputs
  - serious first-pass semantic cases
  - still eligible for review and promotion
- Pause broader semantic comparison work until the weakest local buckets are reviewed.
- It is still acceptable to continue purely structural or runtime-gate work in parallel when that work does not depend on the semantic case labels being final.
- The first packet-level machine-side audit already indicates real benchmark-design weakness in the targeted Chinese weak-bucket slice, so that slice should now be treated as review-required rather than merely review-optional.

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

## Packet-Based Human Review Workflow
The human loop should stay intentionally simple and not require a frontend website.

### Packet folders
- `reading-companion-backend/eval/review_packets/pending/`
- `reading-companion-backend/eval/review_packets/archive/`

### Current active packets
- `attentional_v2_zh_weak_buckets_round1`
  - tracked Chinese `callback_bridge` and `reconsolidation_later_reinterpretation`
- `attentional_v2_en_weak_cases_round1`
  - the six non-pass English local cases from the first corrected `mechanism_integrity` run

### Export tool
- `reading-companion-backend/eval/attentional_v2/export_dataset_review_packet.py`

Codex uses this tool to create a packet under:
- `reading-companion-backend/eval/review_packets/pending/<packet_id>/`

Packet contents:
- `packet_manifest.json`
- `cases.review.csv`
- `cases.preview.md`
- `cases.source.jsonl`
- `README.md`

### What the human reviewer does
1. Read `cases.preview.md`.
2. Open `cases.review.csv` in Numbers, Excel, Google Sheets, VS Code, or any CSV-capable editor.
3. Edit only the `review__...` columns.
4. Save the file in place.
5. Tell Codex that the packet is ready.

### Required marking field
- `review__action`
  - `keep`
  - `revise`
  - `drop`
  - `unclear`

### Recommended marking fields
- `review__confidence`
  - `high`
  - `medium`
  - `low`
- `review__problem_types`
  - separate multiple codes with `|`
- `review__revised_bucket`
- `review__revised_selection_reason`
- `review__revised_judge_focus`
- `review__notes`

### Recommended problem-type codes
- `wrong_bucket`
- `weak_excerpt`
- `ambiguous_focus`
- `text_noise`
- `duplicate_case`
- `too_easy`
- `too_hard`
- `source_parse_problem`
- `other`

### Import tool
- `reading-companion-backend/eval/attentional_v2/import_dataset_review_packet.py`

Codex imports the completed packet with:
- `python -m eval.attentional_v2.import_dataset_review_packet --packet-id <packet_id> --archive`

The importer:
- validates the review file
- writes `import_summary.json`
- saves `dataset_before_import.jsonl`
- merges review metadata into the dataset rows
- archives the packet under `eval/review_packets/archive/`

### Why this workflow exists
- It keeps review executable on the same machine with no upload ceremony.
- It keeps the human task readable.
- It preserves provenance and pre-import state.
- It lets later dataset rebuilding use review metadata instead of relying only on memory or chat.

### Stage 5: Re-freeze and rerun
After edits:
- freeze a new reviewed split or reviewed dataset version
- rerun `mechanism_integrity`
- compare whether the failures still point at the mechanism instead of case ambiguity

### Reviewed-slice support tools
- baseline metadata backfill:
  - `reading-companion-backend/eval/attentional_v2/backfill_case_review_metadata.py`
- reviewed-slice freezing:
  - `reading-companion-backend/eval/attentional_v2/freeze_reviewed_dataset_slice.py`

The current tracked curated `v2` excerpt datasets now carry baseline fields such as:
- `review_status`
- `benchmark_status`
- `case_provenance`
- `review_history`
- `metadata_sync`

That makes the later freeze step explicit and reproducible instead of depending on one-off dataset edits.

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
  - use the active human-review packets:
    - `attentional_v2_zh_weak_buckets_round1`
    - `attentional_v2_en_weak_cases_round1`
  - use the companion machine audits:
    - `reading-companion-backend/eval/runs/attentional_v2/case_audits/attentional_v2_zh_weak_buckets_round1__20260325-003459/`
    - `reading-companion-backend/eval/runs/attentional_v2/case_audits/attentional_v2_en_weak_cases_round1__20260325-004347/`
  - prioritize the Chinese packet first because the machine-side audit is much weaker there
  - import the reviewed packet(s)
  - freeze the reviewed local slice and rerun `mechanism_integrity`

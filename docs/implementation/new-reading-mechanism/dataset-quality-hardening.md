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
- include independent inspection where benchmark trust matters
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
- The current operational rule is now LLM-led review by default:
  - multi-prompt LLM adjudication replaces manual human packet review unless the user explicitly requests manual review
  - human review is now optional later escalation for higher-trust `gold` slices, not the default blocker for current hardening work
- Do **not** broadly retune the mechanism against the current reviewed slice while it remains tiny and skewed.
  - no-regret mechanism fixes are still allowed
  - broad mechanism tuning should wait for a larger reviewed excerpt slice

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
- optional future escalation when we want stronger benchmark trust than `llm_reviewed`

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

## Balance Rule
- Distinguish:
  - targeted repair
  - benchmark growth
- Targeted repair may inspect the currently weakest language or bucket first.
- Benchmark growth must stay balanced across English and Chinese.
- For the excerpt benchmark family, do not run a formal expansion round that grows only one language track.
- Keep both of these balanced whenever we expand:
  - raw reviewed-case count
  - phenomenon coverage across buckets

## Next Planned Work
The next work should happen in two lanes:

### Lane A: Targeted hardening round
Purpose:
- repair the remaining explicitly flagged weak cases
- remove or rewrite cases that are still distorting the benchmark

Rule:
- although the current weakness is stronger on Chinese, the next formal packet round should be bilingual rather than Chinese-only

Round shape:
- one bilingual hardening packet
- target size:
  - `4` English cases
  - `4` Chinese cases

Recommended selection policy:
- English:
  - the remaining `needs_revision` rows
  - plus, if needed to reach `4`, one analogous builder-curated weak-family candidate
- Chinese:
  - the remaining `needs_revision` and `needs_replacement` rows

Expected result:
- convert the clearly salvageable rows into `reviewed_active`
- retire the clearly bad rows
- identify which weak-family gaps still need true replacement rather than relabeling

### Lane B: Balanced reviewed-slice expansion
Purpose:
- make the reviewed excerpt slice large enough to guide mechanism work more safely
- avoid tuning against a tiny, callback-heavy subset

Round shape:
- one bilingual reviewed-slice expansion packet after Lane A
- target size:
  - `6` English promotion candidates
  - `6` Chinese promotion candidates

Selection order:
1. current tracked curated `v2` rows that are still `builder_curated`
2. if that is not enough, promote from the tracked seed `v2` excerpt pool into the curated pack first
3. only if the current tracked public pool cannot supply enough trustworthy candidates do we return to source-book/corpus expansion

Per-language coverage target for this expansion packet:
- `1` `distinction_definition`
- `1` `tension_reversal`
- `2` `callback_bridge`
- `1` `anchored_reaction_selectivity`
- `1` `reconsolidation_later_reinterpretation` or strongest available reserve replacement

Immediate reviewed-slice gate after Lane A + Lane B:
- aim for at least `8` `reviewed_active` excerpt cases per language before broader semantic comparison
- do not trust broader semantic comparison if one language remains far below that floor
- status:
  - reached on `2026-03-26` after the first balanced bilingual `6+6` reviewed-slice expansion round
  - current reviewed-active counts:
    - English: `9`
    - Chinese: `9`

Preferred next confidence gate after the following round:
- `10-12` `reviewed_active` excerpt cases per language
- at that point, broader mechanism tuning and comparison work becomes much safer

## Later Dataset Expansion
If the current tracked `v2` curated/seed pool still cannot support a trustworthy reviewed slice after the two lanes above, expand the bilingual excerpt benchmark itself.

Balanced bilingual excerpt-growth target:
- grow curated excerpt packs from `16` to `24` cases per language

Recommended added coverage per language:
- `+1` `distinction_definition`
- `+1` `tension_reversal`
- `+2` `callback_bridge`
- `+2` `anchored_reaction_selectivity`
- `+2` `reconsolidation_later_reinterpretation`

Important scope rule:
- this immediate hardening/expansion plan is excerpt-first because the current blocked decision is a local `mechanism_integrity` question
- chapter/runtime/compatibility families should remain unchanged in this round unless the local excerpt evidence says a broader corpus change is actually needed

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

### Stage 4: Final adjudication review
The current operational reviewer is a final LLM adjudicator that is separate from:
- the dataset builder
- the primary case auditor
- the adversarial disagreement auditor

This adjudication pass should decide:
- keep as-is
- rewrite the focus
- relabel the bucket
- move to reserve
- drop and replace

Manual human review is now optional later escalation for:
- cases intended for `gold` status
- especially high-impact disagreement cases
- future benchmark-promotion work when we want stronger trust than the current operational mode

## Packet-Based Review Workflow
The review loop should stay intentionally simple and not require a frontend website.

### Packet folders
- `reading-companion-backend/eval/review_packets/pending/`
- `reading-companion-backend/eval/review_packets/archive/`
- `reading-companion-backend/eval/review_packets/review_queue_summary.json`
- `reading-companion-backend/eval/review_packets/review_queue_summary.md`

### Current packet status
- active queue:
  - currently `0` active packets
  - see `reading-companion-backend/eval/review_packets/review_queue_summary.md`
  - immediate next hardening step:
    - none
    - the first balanced bilingual `6+6` reviewed-slice expansion round is complete
  - current decision point:
    - the reviewed slice is no longer too small to be meaningful
    - broader semantic comparison should still remain blocked for now
    - the first two targeted mechanism-repair passes are now landed
    - the next real choice is:
      - rerun the full `9 + 9` reviewed slice now
      - or land one more narrow repair on distinction / anchorless-callback handling first
  - most recent bilingual hardening round:
    - implementation note:
      - the current import path is dataset-local, so one balanced bilingual round is represented as a synchronized packet pair rather than one mixed packet
    - English packet:
      - `attentional_v2_bilingual_hardening_round3_en`
      - `4` cases
      - `3` remaining `needs_revision`
      - `1` analogous builder-curated reconsolidation candidate
      - machine-side case audit:
        - `reading-companion-backend/eval/runs/attentional_v2/case_audits/attentional_v2_bilingual_hardening_round3_en__20260326-033106/`
        - `4` completed
        - primary decisions: `3 keep`, `1 revise`
        - adversarial risk counts: `4 medium`
      - final adjudication/import:
        - `2 keep`
        - `2 revise`
    - Chinese packet:
      - `attentional_v2_bilingual_hardening_round3_zh`
      - `4` cases
      - `3` `needs_revision`
      - `1` `needs_replacement`
      - machine-side case audit:
        - `reading-companion-backend/eval/runs/attentional_v2/case_audits/attentional_v2_bilingual_hardening_round3_zh__20260326-033106/`
        - `4` completed
        - primary decisions: `3 keep`, `1 unclear`
        - adversarial risk counts: `2 low`, `1 medium`, `1 high`
      - final adjudication/import:
        - `2 keep`
        - `1 revise`
        - `1 drop`
    - imported status effect on tracked curated `v2` datasets:
      - English:
        - `5` `reviewed_active`
        - `2` `needs_revision`
      - Chinese:
        - `4` `reviewed_active`
        - `1` `needs_revision`
        - `1` `needs_replacement`
- archived round 1 packet results:
  - `attentional_v2_zh_weak_buckets_round1`
    - `0 keep`
    - `4 revise`
    - `2 drop`
  - `attentional_v2_en_weak_cases_round1`
    - `3 keep`
    - `3 revise`
    - `0 drop`
  - `attentional_v2_zh_revision_replacement_round2`
    - source dataset: tracked `attentional_v2_excerpt_zh_curated_v2`
    - purpose: run the next Chinese hardening pass directly on the status-marked weak cases
    - completed machine-side case audit:
      - `reading-companion-backend/eval/runs/attentional_v2/case_audits/attentional_v2_zh_revision_replacement_round2__20260325-143403/`
      - `6` completed
      - `0` factual failures
      - primary decisions: `4 keep`, `2 revise`
      - adversarial risk counts: `4 medium`, `1 high`, `1 low`
    - completed final LLM adjudication/import through the shared universal backend LLM layer
    - packet outcome:
      - `2 keep`
      - `3 revise`
      - `1 drop`
    - imported status effect on tracked `attentional_v2_excerpt_zh_curated_v2`:
      - `2` `reviewed_active`
      - `3` `needs_revision`
      - `1` `needs_replacement`
  - reviewed-slice rerun:
    - frozen reviewed datasets:
      - `reading-companion-backend/eval/datasets/excerpt_cases/attentional_v2_excerpt_en_curated_v2_llm_reviewed_round2/`
      - `reading-companion-backend/eval/datasets/excerpt_cases/attentional_v2_excerpt_zh_curated_v2_llm_reviewed_round2/`
    - benchmark run:
      - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_integrity_reviewed_slice_round2_20260326/`
    - result:
      - `5` total cases
      - `2 pass`
      - `1 partial`
      - `2 fail`
      - `0` structural failures
      - global averages: all `3.000`
      - English: `2 pass`, `1 fail`, average `3.667`
      - Chinese: `1 partial`, `1 fail`, average `2.000`
    - interpretation:
      - the reviewed slice is cleaner, but not yet broad enough for high-confidence comparison work
      - Chinese callback handling still shows real mechanism weakness even after dataset cleanup
      - broader semantic comparison should remain blocked until the next balanced bilingual reviewed-slice expansion round lands
      - the later bilingual hardening round improved the reviewed-active counts, but the benchmark still remains below the `8`-per-language minimum trust floor for broader semantic comparison
  - reviewed-slice expansion round 1:
    - implementation note:
      - the current import path remains dataset-local, so one balanced bilingual expansion round is represented as a synchronized packet pair rather than one mixed packet
    - English packet:
      - `attentional_v2_reviewed_slice_expansion_round1_en`
      - `6` cases
      - source policy:
        - current tracked curated `v2` rows still marked `builder_curated`
      - machine-side case audit:
        - `reading-companion-backend/eval/runs/attentional_v2/case_audits/attentional_v2_reviewed_slice_expansion_round1_en__20260326-040401/`
        - `6` completed
        - primary decisions: `4 keep`, `2 revise`
        - adversarial risk counts: `2 low`, `4 medium`
      - final adjudication/import:
        - `4 keep`
        - `2 revise`
    - Chinese packet:
      - `attentional_v2_reviewed_slice_expansion_round1_zh`
      - `6` cases
      - source policy:
        - current tracked curated `v2` rows still marked `builder_curated`
      - machine-side case audit:
        - `reading-companion-backend/eval/runs/attentional_v2/case_audits/attentional_v2_reviewed_slice_expansion_round1_zh__20260326-040401/`
        - `6` completed
        - primary decisions: `5 keep`, `1 revise`
        - adversarial risk counts: `2 low`, `4 medium`
      - final adjudication/import:
        - `5 keep`
        - `1 revise`
    - imported status effect on tracked curated `v2` datasets:
      - English:
        - `9` `reviewed_active`
        - `4` `needs_revision`
      - Chinese:
        - `9` `reviewed_active`
        - `2` `needs_revision`
        - `1` `needs_replacement`
  - reviewed-slice rerun after expansion:
    - frozen reviewed datasets:
      - `reading-companion-backend/eval/datasets/excerpt_cases/attentional_v2_excerpt_en_curated_v2_llm_reviewed_round3/`
      - `reading-companion-backend/eval/datasets/excerpt_cases/attentional_v2_excerpt_zh_curated_v2_llm_reviewed_round3/`
    - benchmark run:
      - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_integrity_reviewed_slice_round3_20260326/`
    - result:
      - `18` total cases
      - `7 pass`
      - `1 partial`
      - `10 fail`
      - `0` structural failures
      - global averages:
        - `text_groundedness`: `3.278`
        - `meaning_unit_quality`: `2.889`
        - `move_quality`: `3.111`
        - `reaction_quality`: `3.167`
        - `case_fit`: `2.667`
      - English:
        - `6 pass`
        - `3 fail`
        - `3.444` average on `meaning_unit_quality`, `move_quality`, and `case_fit`
      - Chinese:
        - `1 pass`
        - `1 partial`
        - `7 fail`
        - `1.889` `case_fit`
    - interpretation:
      - the benchmark is now large enough to give a real signal instead of only a tiny-slice hint
      - dataset weakness was part of the earlier problem, but it is no longer the whole story
      - real mechanism weakness remains, especially on the Chinese slice and especially around `callback_bridge`, `tension_reversal`, and `reconsolidation_later_reinterpretation`
      - broader semantic comparison should still remain blocked
      - the next real decision is whether to:
        - start mechanism repair from this `9 + 9` reviewed slice
        - or keep expanding toward the preferred `10-12` reviewed-active cases per language before broader mechanism tuning
  - first mechanism-repair pass:
    - route chosen:
      - start mechanism repair from the current `9 + 9` reviewed slice
    - code changes:
      - restore deterministic bridge candidates into the live Phase 4 runner instead of dropping them before `controller_decision`
      - merge zoom-level bridge hints into the Phase 4 controller candidate pool
      - make deterministic retrieval callback-aware:
        - better Chinese tokenization
        - broader already-read source scan only when explicit backward-looking markers are present
      - tighten Phase 4 prompt instructions so zoom/closure name exact callback cues and distinctions instead of generic scene summary
    - focused verification:
      - targeted tests passed for retrieval, Phase 4 node behavior, and live runner bridge-candidate handoff
      - targeted rerun:
        - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_integrity_repair_pass1_targeted_20260326/`
        - cases:
          - `jinghua_yuan_25377_zh__15__callback_bridge__v2`
          - `jinghua_yuan_25377_zh__34__callback_bridge__v2`
          - `gushi_xinbian_public_zh__4__distinction_definition__v2`
          - `chenlun_public_zh__4__reconsolidation_later_reinterpretation__v2`
    - result:
      - `3 fail`
      - `1 partial`
      - the strongest improvement was `jinghua_yuan_25377_zh__34__callback_bridge__v2`, which moved from `fail` to `partial` after real cross-span callback candidates started surfacing
      - the pass did **not** resolve:
        - explicit prior-acquaintance callback detection
        - distinction / recognition-gap closure
        - durable-pattern framing for reconsolidation candidates
    - next repair focus:
      - keep broader semantic comparison blocked
      - continue mechanism repair on:
        - exact callback-cue reading
        - exact distinction / recognition-gap reading
        - durable-pattern recognition before withholding reaction or defaulting to generic biography summary
  - second mechanism-repair pass:
    - code changes:
      - Phase 4 zoom/closure now receive deterministic local textual cue packets for:
        - `callback_cue`
        - `distinction_cue`
        - `recognition_gap`
        - `durable_pattern`
      - the live runner now passes richer boundary context into the local cycle:
        - trigger output
        - gate state
        - trigger signals
        - callback-anchor ids
    - focused verification:
      - targeted tests passed for cue packaging, prompt-version manifests, and runner boundary-context handoff
      - targeted rerun:
        - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_integrity_repair_pass2_targeted_20260326/`
        - same four weak Chinese reviewed cases as repair pass 1
    - result:
      - `2 pass`
      - `1 partial`
      - `1 fail`
      - strongest improvements:
        - `jinghua_yuan_25377_zh__34__callback_bridge__v2`: `partial -> pass`
        - `chenlun_public_zh__4__reconsolidation_later_reinterpretation__v2`: `fail -> pass`
        - `gushi_xinbian_public_zh__4__distinction_definition__v2`: `fail -> partial`
      - remaining hard failure:
        - `jinghua_yuan_25377_zh__15__callback_bridge__v2`
    - interpretation:
      - the repair work is now changing the benchmark outcome materially instead of only cosmetically
      - the remaining weakness is narrower than before:
        - one distinction / recognition-gap case is still too shallow
        - one callback case still misbridges when the cue is explicit but the strongest supporting anchor is absent or wrong in the retrieved already-read space
      - this is now the next decision gate:
        - rerun the full reviewed slice immediately
        - or land one more narrow repair on distinction / anchorless-callback handling first

### Export tool
- `reading-companion-backend/eval/attentional_v2/export_dataset_review_packet.py`
- `reading-companion-backend/eval/attentional_v2/generate_revision_replacement_packet.py`

Codex uses this tool to create a packet under:
- `reading-companion-backend/eval/review_packets/pending/<packet_id>/`

Use the revision/replacement generator when the next packet should be selected automatically from dataset rows that already landed in:
- `needs_revision`
- `needs_replacement`
- optionally `needs_adjudication`

Packet contents:
- `packet_manifest.json`
- `cases.review.csv`
- `cases.preview.md`
- `cases.source.jsonl`
- `README.md`

### Case-audit run artifacts
- `reading-companion-backend/eval/runs/attentional_v2/case_audits/<packet_id>__<timestamp>/`
- Each packet-level case audit should now produce:
  - `run_state.json`
    - packet status and progress
  - `case_states/<case_id>.json`
    - per-case stage state and LLM timing metadata
  - `summary/aggregate.partial.json`
  - `summary/report.partial.md`
  - `summary/aggregate.json`
  - `summary/report.md`
- Queue/report surfaces should treat only completed runs as landed evidence.
  - Incomplete or stale runs should remain visible for diagnosis, but they should not silently replace the latest completed audit summary.

### Current operational review mode
- Default reviewer:
  - multi-prompt LLM adjudication
- Optional later escalation:
  - manual human review
- The LLM reviewer should use at least:
  - primary case-design review
  - adversarial disagreement review
  - final adjudication review with a separate prompt role
- The packet-level case-audit runner may use bounded case-level parallelism.
  - primary and adversarial review still remain ordered within each case
  - packet-level concurrency should stay conservative enough that the provider path remains stable and traceable
- Model policy for packet review:
  - prefer one pinned high-trust judge model profile for the whole packet
  - same-model key failover is acceptable when needed
  - do not silently switch to a different model family in the middle of one packet review run
  - if a second strong model family is used, treat it as explicit disagreement/adjudication work rather than routine hidden mixing

### What Codex does in the current operational mode
1. Run factual audit.
2. Run primary case audit.
3. Run adversarial disagreement audit.
4. Run final LLM adjudication and fill the `review__...` columns automatically.
5. Import the packet back into the dataset.
6. Rebuild or reuse the reviewed slice and rerun `mechanism_integrity` before trusting broader semantic comparison.
7. If the reviewed slice is still thin or still concentrated in one weak bucket, run another targeted hardening round before broader semantic comparison.

### Optional manual override mode
If manual review is explicitly requested later:
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

### Final LLM adjudication tool
- `reading-companion-backend/eval/attentional_v2/auto_review_packet.py`

Codex imports the completed packet with:
- `python -m eval.attentional_v2.import_dataset_review_packet --packet-id <packet_id> --archive`

The importer:
- validates the review file
- writes `import_summary.json`
- saves `dataset_before_import.jsonl`
- merges review metadata into the dataset rows
- archives the packet under `eval/review_packets/archive/`

Imported packets now drive the reviewed benchmark slice through:
- `review_status`
  - `builder_curated`
  - `llm_reviewed`
  - `human_reviewed`
- `benchmark_status`
  - `reviewed_active`
  - `needs_revision`
  - `needs_replacement`
  - `needs_adjudication`

Important rule:
- `revise` should not be treated as immediately freezeable.
- A `revise` decision means the case still needs a follow-up edit or relabel before it can enter the reviewed slice.

### Why this workflow exists
- It keeps review executable on the same machine with no upload ceremony.
- It keeps the human task readable.
- It preserves provenance and pre-import state.
- It lets later dataset rebuilding use review metadata instead of relying only on memory or chat.
- It avoids making current dataset quality depend on scarce human review capacity.

### Stage 5: Re-freeze and rerun
After edits:
- freeze a new reviewed split or reviewed dataset version
- rerun `mechanism_integrity`
- compare whether the failures still point at the mechanism instead of case ambiguity

### Reviewed-slice support tools
- baseline metadata backfill:
  - `reading-companion-backend/eval/attentional_v2/backfill_case_review_metadata.py`
- final LLM packet adjudication:
  - `reading-companion-backend/eval/attentional_v2/auto_review_packet.py`
- reviewed-slice freezing:
  - `reading-companion-backend/eval/attentional_v2/freeze_reviewed_dataset_slice.py`
- queue summary generation:
  - `reading-companion-backend/eval/attentional_v2/build_review_queue_summary.py`

The current curated excerpt datasets now carry baseline fields such as:
- `review_status`
- `benchmark_status`
- `case_provenance`
- `review_history`
- `metadata_sync`

That baseline metadata now exists across:
- tracked curated excerpt datasets
- local-only curated excerpt datasets

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
- `gold` benchmark designation
- later higher-trust benchmark promotion work if we explicitly choose to reintroduce human review

### Recommended review pattern
- `single-pass reviewer`
  - cheap first-pass audit over the whole curated set
- `dual-pass disagreement`
  - one prompt argues for the current label, one tries to break it
- `final adjudicator`
  - a separate prompt role decides the operational review action for the packet
- `human-on-escalation`
  - optional later layer only when explicitly requested or when pursuing `gold`

That gives us leverage without pretending automated review is identical to expert truth, while still keeping the current hardening loop executable.

## Practical Quality Gate
Before trusting broader semantic comparison too much, the excerpt family should satisfy all of these:
- no factual boundary errors in the targeted review slice
- weak buckets have gone through at least LLM review and disagreement review
- flagged cases have explicit keep/relabel/drop decisions
- at least the first high-impact weak cases have final adjudication review
- rerun of `mechanism_integrity` shows the same failures are not mostly caused by mislabeled cases

## To-Do Now
1. Keep the packet queue current and visible through `review_queue_summary.md`.
2. Create replacement or revised packets for the cases that landed in `needs_revision` or `needs_replacement`.
3. Promote reviewed cases out of `builder_curated` where justified.
4. Freeze the next reviewed local benchmark slice.
5. Rerun `mechanism_integrity` on that reviewed slice before trusting broader semantic evaluation.

## Recommendation For Immediate Next Step
- Do not jump straight into broader semantic comparison yet.
- First harden the local excerpt benchmark slice.
- The best immediate move is:
  - use the queue summary:
    - `reading-companion-backend/eval/review_packets/review_queue_summary.md`
  - treat the archived round 1 packet results as now authoritative for the reviewed cases:
    - `reading-companion-backend/eval/review_packets/archive/attentional_v2_zh_weak_buckets_round1/`
    - `reading-companion-backend/eval/review_packets/archive/attentional_v2_en_weak_cases_round1/`
  - prioritize Chinese replacement work first because the first round produced:
    - `0 keep`
    - `4 revise`
    - `2 drop`
  - use the first frozen reviewed slices:
    - `reading-companion-backend/eval/datasets/excerpt_cases/attentional_v2_excerpt_en_curated_v2_llm_reviewed_round1/`
    - `reading-companion-backend/eval/datasets/excerpt_cases/attentional_v2_excerpt_zh_curated_v2_llm_reviewed_round1/`
  - rerun `mechanism_integrity` on the reviewed slice before trusting broader semantic comparison

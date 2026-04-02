# Revision/Replacement Packet `attentional_v2_formal_benchmark_v1_excerpt_rerun_women_20260402`

This packet was generated automatically from cases whose current `benchmark_status` requires another hardening round.

## Dataset
- dataset_id: `attentional_v2_excerpt_en_curated_v2`
- family: `excerpt_cases`
- language_track: `en`
- version: `2`
- targeted_statuses: `needs_revision|needs_replacement|needs_revision`

## Review Actions
- `keep`
- `revise`
- `drop`
- `unclear`

## Confidence
- `high`
- `medium`
- `low`

## 1. `women_and_economics_public_en__9__distinction_definition__v2`

- benchmark_status: `needs_revision`
- review_status: `llm_reviewed`
- book: `Women and Economics`
- author: `Charlotte Perkins Gilman`
- chapter: `IV` (`9`)
- question_ids: `EQ-CM-002|EQ-AV2-002|EQ-AV2-005`
- phenomena: `distinction|definition_pressure|anchored_reaction`
- selection_reason: Selected to test whether the mechanism can close around a live distinction instead of flattening the passage into generic paraphrase.
- judge_focus: Does the mechanism identify the key distinction cleanly and stay answerable to the specific passage?
- latest_review_action: `revise`
- latest_problem_types: `other`
- latest_revised_bucket: ``
- latest_notes: The factual audit flags an excerpt_text_mismatch, which is a concrete integrity issue that warrants verification rather than a clean pass. The passage itself contains strong distinction-related content (the contrast between permitted domestic labor and forbidden public/professional work), and primary review rates bucket fit, focus clarity, and excerpt strength as strong. Recommend verifying the text against source before finalizing, but the case has genuine value for testing distinction extraction. Keep the case active pending text resolution.

```text
But in the ever-growing human impulse to create, the power and will to make, to do, to express one’s new spirit in new forms﻿—here she has been utterly debarred.
She might work as she had worked from the beginning﻿—at the primitive labors of the household; but in the inevitable expansion of even those industries to professional levels we have striven to hold her back.
To work with her own hands, for nothing, in direct body-service to her own family﻿—this has been permitted﻿—yes, compelled.
But to be and do anything further from this she has been forbidden.
Her labor has not only been limited in kind, but in degree.
Whatever she has been allowed to do must be done in private and alone, the firsthand industries of savage times.
Our growth in industry has been not only in kind, but in class.
```

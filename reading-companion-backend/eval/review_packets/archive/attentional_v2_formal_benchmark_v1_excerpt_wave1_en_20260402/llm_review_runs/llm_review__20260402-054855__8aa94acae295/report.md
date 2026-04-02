# LLM Packet Review: `attentional_v2_formal_benchmark_v1_excerpt_wave1_en_20260402`

- run_id: `llm_review__20260402-054855__8aa94acae295`
- generated_at: `2026-04-02T05:50:19.306710Z`
- case_count: `2`
- action_counts: `{"revise": 2}`
- adjudication_input_fingerprint: `f24d309175b0bda6f49a442596fdd9e61953e82475a2c9cad26007c91a9a41c8`
- probe_only: `False`
- quota_recovery_attempted_count: `0`
- quota_recovery_succeeded_count: `0`
- quota_failure_remaining_count: `0`

## Case Decisions

- `women_and_economics_public_en__9__distinction_definition__v2`
  - action: `revise`
  - confidence: `medium`
  - problem_types: `other`
  - adjudication_input_fingerprint: `f0053d5e95cbda1f5a4852c6c55ef3b02411c57003f0967ce191fe692d08be69`
  - notes: The factual audit flags an excerpt_text_mismatch, which is a concrete integrity issue that warrants verification rather than a clean pass. The passage itself contains strong distinction-related content (the contrast between permitted domestic labor and forbidden public/professional work), and primary review rates bucket fit, focus clarity, and excerpt strength as strong. Recommend verifying the text against source before finalizing, but the case has genuine value for testing distinction extraction. Keep the case active pending text resolution.
- `portrait_of_a_lady_public_en__10__anchored_reaction_selectivity__v2`
  - action: `revise`
  - confidence: `medium`
  - problem_types: `text_noise|ambiguous_focus`
  - adjudication_input_fingerprint: `8758e87fbcea4d16c04995530beec64327c686bd505555e2f19c1891ffb73d54`
  - notes: The factual audit found an excerpt_text_mismatch, which is a concrete excerpt integrity defect that must be corrected. Additionally, the judge focus ('Is the visible reaction anchored, selective, and worth keeping on reread?') is too diffuse—it asks three loosely-related questions without isolating a single mechanism behavior. The primary reviewer's 'ambiguous_focus' flag is valid. The case shows promise: the contrast between Mrs. Touchett and Isabel and the old man's benevolent feelings are legible, suggesting the reaction-anchor and selective-legibility phenomena are present in the source text. However, the excerpt needs verification against the source, and the judge focus should be sharpened to test one specific mechanism claim rather than three simultaneously.

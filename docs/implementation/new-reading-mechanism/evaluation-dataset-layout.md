# New Reading Mechanism Evaluation Dataset Layout

Purpose: define the concrete dataset-package design for the current `attentional_v2` evaluation buildout.
Use when: creating dataset folders, naming packages, or deciding which evaluation question family maps to which tracked dataset family.
Not for: stable evaluation constitution or final benchmark reports.
Update when: package naming changes, new dataset families are added, or the bilingual evaluation layout changes.

## Working Rule
- Stable project rule:
  - family-first dataset layout under `reading-companion-backend/eval/datasets/`
- Current project rule:
  - build one `attentional_v2` benchmark family per evidence family and language track
  - let each package declare or imply `storage_mode = tracked` or `storage_mode = local-only`
  - keep the same family-first structure under `reading-companion-backend/state/eval_local_datasets/` whenever the package contains copyrighted or otherwise private source text

## Family Mapping
### `excerpt_cases`
Use for:
- `EQ-CM-002`
- `EQ-AV2-001`
- `EQ-AV2-002`
- `EQ-AV2-003`
- `EQ-AV2-004`
- `EQ-AV2-005`
- `EQ-AV2-006` (when the case itself is excerpt-centered)

Language tracks:
- `en`
- `zh`

Primary payload:
- `cases.jsonl`

### `chapter_corpora`
Use for:
- `EQ-CM-001`
- `EQ-CM-003`
- parts of `EQ-CM-004`
- chapter-scale parts of `EQ-GATE-003`

Language tracks:
- `en`
- `zh`

Primary payload:
- `chapters.jsonl`

### `runtime_fixtures`
Use for:
- `EQ-CM-005`
- `EQ-AV2-007`
- `EQ-GATE-001`
- runtime parts of `EQ-GATE-003`

Language tracks:
- `en`
- `zh`

Primary payload:
- `fixtures.jsonl`

### `compatibility_fixtures`
Use for:
- `EQ-AV2-008`
- `EQ-GATE-002`
- persisted-trace audit inputs used for migration checks

Language tracks:
- usually `shared`
- only split by language when the fixture content itself must remain language-specific

Primary payload:
- `fixtures.jsonl`

## Current Package Set
The benchmark family now has two tracked generations:

### Seed generation
- English:
  - `attentional_v2_excerpt_en_v1`
  - `attentional_v2_chapters_en_v1`
  - `attentional_v2_runtime_en_v1`
- Chinese:
  - `attentional_v2_excerpt_zh_v1`
  - `attentional_v2_chapters_zh_v1`
  - `attentional_v2_runtime_zh_v1`
- Shared:
  - `attentional_v2_compat_shared_v1`

### Current benchmark generation
- English:
  - `attentional_v2_excerpt_en_v2`
  - `attentional_v2_excerpt_en_curated_v2`
  - `attentional_v2_chapters_en_v2`
  - `attentional_v2_runtime_en_v2`
- Chinese:
  - `attentional_v2_excerpt_zh_v2`
  - `attentional_v2_excerpt_zh_curated_v2`
  - `attentional_v2_chapters_zh_v2`
  - `attentional_v2_runtime_zh_v2`
- Shared:
  - `attentional_v2_compat_shared_v2`

The `v2` generation is the current serious public-first bilingual benchmark layer.

## Package Contract
Every concrete package should contain:
- `manifest.json`
- one primary payload file

Recommended optional files:
- `README.md`
- `judge_notes.md`

### `manifest.json` required keys
- `dataset_id`
- `family`
- `language_track`
- `version`
- `description`
- `primary_file`
- `question_ids`
- `source_manifest_refs`
- `split_refs`

Recommended additional key:
- `storage_mode`
  - `tracked`
  - `local-only`

### Primary payload rules
- `cases.jsonl`
  - one record per excerpt case
- `chapters.jsonl`
  - one record per chapter comparison unit
- `fixtures.jsonl`
  - one record per runtime or compatibility fixture

## Relationship To Manifests
Dataset packages should stay lean.

The following belong in `reading-companion-backend/eval/manifests/`, not inside each dataset package:
- source-book inventory files
- corpus selection manifests
- bilingual split manifests
- local-path reference files for private/local corpora
- local package reference files for private/local dataset packages

## Unified Benchmark Family Rule
- Tracked packages and local-only packages are not different benchmark concepts when they answer the same evaluation questions.
- They are the same benchmark family in different storage modes.
- The real organizing dimensions are:
  - `family`
  - `language_track`
  - `version`
  - `storage_mode`
- The purpose of `storage_mode` is operational:
  - whether the package can live in the tracked repo dataset tree
  - or must stay in the local-only mirror

## Bilingual Rule
- English and Chinese stay in separate tracked packages.
- Do not put both languages into the same package for the first benchmark generation.
- If we later add multilingual comparative methodology, that should create new explicit packages rather than silently mixing these first-track datasets.

## Folder Skeleton
The project should have these family roots available now:
- `reading-companion-backend/eval/datasets/excerpt_cases/`
- `reading-companion-backend/eval/datasets/chapter_corpora/`
- `reading-companion-backend/eval/datasets/runtime_fixtures/`
- `reading-companion-backend/eval/datasets/compatibility_fixtures/`
- `reading-companion-backend/eval/datasets/templates/`

The local-only mirror should also exist for private packages:
- `reading-companion-backend/state/eval_local_datasets/excerpt_cases/`
- `reading-companion-backend/state/eval_local_datasets/chapter_corpora/`
- `reading-companion-backend/state/eval_local_datasets/runtime_fixtures/`
- `reading-companion-backend/state/eval_local_datasets/compatibility_fixtures/`
- `reading-companion-backend/state/eval_local_datasets/templates/`

The manifest side should have these roots available now:
- `reading-companion-backend/eval/manifests/source_books/`
- `reading-companion-backend/eval/manifests/corpora/`
- `reading-companion-backend/eval/manifests/splits/`
- `reading-companion-backend/eval/manifests/local_refs/`

## Public-First Large `v2` Build
The current public-first large corpus expansion is now complete.

### Builder and validator
- builder:
  - `reading-companion-backend/eval/attentional_v2/build_public_first_large_corpus.py`
- validator:
  - `reading-companion-backend/eval/attentional_v2/validate_public_first_large_corpus.py`
- shared manifest-driven helper layer:
  - `reading-companion-backend/eval/attentional_v2/corpus_builder.py`
- candidate specification:
  - `reading-companion-backend/eval/attentional_v2/public_first_large_candidates.json`

### Tracked manifest ids
- candidate screen:
  - `attentional_v2_public_first_large_candidates_v2`
- combined tracked public pool:
  - `attentional_v2_public_benchmark_pool_v2`
- bilingual corpus manifest:
  - `attentional_v2_public_benchmark_pool_bilingual_v2`
- split manifest:
  - `attentional_v2_public_benchmark_pool_bilingual_v2_splits`

### Current tracked `v2` counts
- `24` new public/open-access candidates screened
- `12` newly promoted public/open-access books
- `22` books in the combined tracked public pool
- `18` English chapter rows
- `18` Chinese chapter rows
- `36` English runtime fixtures
- `36` Chinese runtime fixtures
- `54` English seed excerpt cases
- `24` Chinese seed excerpt cases
- `16` English curated excerpt cases
- `16` Chinese curated excerpt cases
- `36` shared compatibility fixtures

### Current promoted `v2` books
- English:
  - `on_liberty_public_en`
  - `varieties_of_religious_experience_public_en`
  - `portrait_of_a_lady_public_en`
  - `darkwater_public_en`
  - `women_and_economics_public_en`
  - `up_from_slavery_public_en`
- Chinese:
  - `ouyou_zaji_public_zh`
  - `chenlun_public_zh`
  - `gushi_xinbian_public_zh`
  - `ershinian_mudu_public_zh`
  - `beiying_public_zh`
  - `fen_public_zh`

### Current quota status
- chapter corpus:
  - English and Chinese both meet:
    - `4` expository
    - `4` argumentative
    - `4` narrative_reflective
    - `4` reference_heavy
    - `2` reserve
- curated excerpts:
  - English and Chinese both meet:
    - `3` distinction_definition
    - `3` tension_reversal
    - `3` callback_bridge
    - `3` anchored_reaction_selectivity
    - `3` reconsolidation_later_reinterpretation
    - `1` reserve

Important build nuance:
- weak public Chinese sources may be normalized into clean synthetic segmented EPUBs before screening when the underlying text is usable but the original public packaging is too structurally weak for fair chapter selection
- this normalization is part of the tracked `v2` build process, not an ad hoc exception

## Immediate Next Step
- Treat the tracked `v2` public benchmark family as ready for real evaluation work.
- Use the local-only supplement only to fill any remaining uncovered phenomenon bucket, not as the main acquisition path.
- Stop expanding the corpus by default.
- Start the first serious evaluation runs:
  - mechanism-integrity
  - local reading comparison
  - span trajectory
  - durable trace / re-entry
  - runtime viability

## Expansion Reminder For Later Confidence
- The current `v2` benchmark family is intended to be:
  - large enough for first serious evaluation work
  - but not automatically assumed large enough for final promotion confidence
- After the reviewed-slice rerun and the first broader comparison passes, the project should explicitly decide whether benchmark-size expansion is needed before any strong default-cutover claim.
- If sample-size confidence is still too weak, the default next targets should be:
  - curated excerpt cases:
    - expand from `16` per language toward roughly `25-30` per language
  - chapter corpus:
    - expand from `18` per language toward roughly `24-30` per language
  - runtime fixtures:
    - expand only if runtime-gate coverage, not semantic confidence, is still weak
- This expansion is conditional future work, not an automatic immediate task.

## Current Seed Build Status
The first public-domain bilingual seed build has now landed in the repo/runtime workspace:

- tracked manifests:
  - `reading-companion-backend/eval/manifests/source_books/attentional_v2_public_domain_seed_v1.json`
  - `reading-companion-backend/eval/manifests/local_refs/attentional_v2_public_domain_seed_v1.json`
  - `reading-companion-backend/eval/manifests/corpora/attentional_v2_public_domain_seed_bilingual_v1.json`
  - `reading-companion-backend/eval/manifests/splits/attentional_v2_public_domain_seed_bilingual_v1.json`
- concrete dataset packages:
  - `reading-companion-backend/eval/datasets/chapter_corpora/attentional_v2_chapters_en_v1/`
  - `reading-companion-backend/eval/datasets/chapter_corpora/attentional_v2_chapters_zh_v1/`
  - `reading-companion-backend/eval/datasets/runtime_fixtures/attentional_v2_runtime_en_v1/`
  - `reading-companion-backend/eval/datasets/runtime_fixtures/attentional_v2_runtime_zh_v1/`
  - `reading-companion-backend/eval/datasets/excerpt_cases/attentional_v2_excerpt_en_v1/`
  - `reading-companion-backend/eval/datasets/excerpt_cases/attentional_v2_excerpt_zh_v1/`
  - `reading-companion-backend/eval/datasets/compatibility_fixtures/attentional_v2_compat_shared_v1/`

Important status nuance:
- chapter corpora are real seed inputs grounded in canonical parsed substrate
- runtime fixtures are real seed inputs grounded in selected chapter units
- excerpt cases are auto-extracted seed inputs and still require later manual curation before benchmark promotion
- compatibility fixtures are spec-level audit inputs and still require live runtime outputs to become fully materialized audit fixtures

## Curated Excerpt Status
The first curated excerpt benchmark family has now been frozen on top of the seed pool:

- `storage_mode = tracked` packages:
  - `reading-companion-backend/eval/datasets/excerpt_cases/attentional_v2_excerpt_en_curated_v1/`
  - `reading-companion-backend/eval/datasets/excerpt_cases/attentional_v2_excerpt_zh_curated_v1/`
- `storage_mode = local-only` packages:
  - `reading-companion-backend/state/eval_local_datasets/excerpt_cases/attentional_v2_private_excerpt_en_curated_v1/`
  - `reading-companion-backend/state/eval_local_datasets/excerpt_cases/attentional_v2_private_excerpt_zh_curated_v1/`
- supporting manifests:
  - `reading-companion-backend/eval/manifests/splits/attentional_v2_excerpt_curated_v1.json`
  - `reading-companion-backend/eval/manifests/local_refs/attentional_v2_private_excerpt_curated_v1.json`

Current curated counts:
- legacy `v1` tracked curated cases:
  - English:
    - `5`
  - Chinese:
    - `2`
- legacy `v1` local-only curated cases:
  - English:
    - `10`
  - Chinese:
    - `4`
- current `v2` tracked curated cases:
  - English:
    - `16`
  - Chinese:
    - `16`

Curated-case rules in this pass:
- every curated case has explicit:
  - `question_ids`
  - `phenomena`
  - `selection_reason`
  - `judge_focus`
- curated cases use stable sentence anchors from canonical `book_document.json`
- the curated layer intentionally does not inherit the duplicate/weak `case_id` patterns from the raw seed layer

Important status nuance:
- the old `v1` curated layer remains useful as a seed/reference generation
- the new tracked `v2` curated layer is now the primary local benchmark layer for both English and Chinese
- the local-only supplement still matters for fallback and later gap-filling, but it is no longer the primary answer to the Chinese tracked-curation gap

## Local-Only Supplement Status
The first `storage_mode = local-only` supplement sourced from the user's Downloads EPUB pool has now landed in the local package mirror:

- tracked manifests:
  - `reading-companion-backend/eval/manifests/source_books/attentional_v2_private_downloads_screen_v1.json`
  - `reading-companion-backend/eval/manifests/local_refs/attentional_v2_private_downloads_seed_v1.json`
  - `reading-companion-backend/eval/manifests/corpora/attentional_v2_private_downloads_bilingual_v1.json`
  - `reading-companion-backend/eval/manifests/splits/attentional_v2_private_downloads_bilingual_v1.json`
- promoted private source books:
  - `reading-companion-backend/state/library_sources/en/private/`
  - `reading-companion-backend/state/library_sources/zh/private/`
- `storage_mode = local-only` package mirror:
  - `reading-companion-backend/state/eval_local_datasets/chapter_corpora/attentional_v2_private_chapters_en_v1/`
  - `reading-companion-backend/state/eval_local_datasets/chapter_corpora/attentional_v2_private_chapters_zh_v1/`
  - `reading-companion-backend/state/eval_local_datasets/runtime_fixtures/attentional_v2_private_runtime_en_v1/`
  - `reading-companion-backend/state/eval_local_datasets/runtime_fixtures/attentional_v2_private_runtime_zh_v1/`
  - `reading-companion-backend/state/eval_local_datasets/excerpt_cases/attentional_v2_private_excerpt_en_v1/`
  - `reading-companion-backend/state/eval_local_datasets/excerpt_cases/attentional_v2_private_excerpt_zh_v1/`
  - `reading-companion-backend/state/eval_local_datasets/compatibility_fixtures/attentional_v2_private_compat_shared_v1/`

Current counts:
- `9` promoted local-only supplement books
- `14` English chapter rows
- `4` Chinese chapter rows
- `36` English runtime fixtures
- `6` Chinese runtime fixtures
- `24` English excerpt cases
- `4` Chinese excerpt cases
- `18` shared compatibility fixture specs

Important status nuance:
- these `storage_mode = local-only` packages are structurally real and grounded in canonical parse
- their text-bearing payloads intentionally remain outside the tracked repo dataset tree
- the local-only excerpt cases are still primarily seed/support material in the current public-first strategy
- after the tracked `v2` public benchmark build, these local-only packages should now be treated as fallback or gap-filling material rather than as the main benchmark layer

## Private Local Supplement Rule
- Use the tracked `eval/datasets/` tree for `storage_mode = tracked` packages.
- Use `state/eval_local_datasets/` for `storage_mode = local-only` packages, including local excerpt packages that carry copyrighted source text.
- Keep the family roots, package contract, and manifest shape aligned across both trees so later evaluation code can treat them as one benchmark family with two storage modes.

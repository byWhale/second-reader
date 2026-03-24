# New Reading Mechanism Evaluation Dataset Layout

Purpose: define the concrete dataset-package design for the current `attentional_v2` evaluation buildout.
Use when: creating dataset folders, naming packages, or deciding which evaluation question family maps to which tracked dataset family.
Not for: stable evaluation constitution or final benchmark reports.
Update when: package naming changes, new dataset families are added, or the bilingual evaluation layout changes.

## Working Rule
- Stable project rule:
  - family-first dataset layout under `reading-companion-backend/eval/datasets/`
- Current project rule:
  - build the first `attentional_v2` evaluation packages inside that stable family-first layout
  - mirror the same family-first structure under `reading-companion-backend/state/eval_local_datasets/` whenever the package contains copyrighted or otherwise private source text

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

## Planned First Package Set
The first serious bilingual build should aim for these tracked package ids:

### English
- `attentional_v2_excerpt_en_v1`
- `attentional_v2_chapters_en_v1`
- `attentional_v2_runtime_en_v1`

### Chinese
- `attentional_v2_excerpt_zh_v1`
- `attentional_v2_chapters_zh_v1`
- `attentional_v2_runtime_zh_v1`

### Shared
- `attentional_v2_compat_shared_v1`

These package ids are the first intended targets, not yet populated datasets.

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

## Immediate Next Step
- Keep the folder skeleton fixed.
- Wait for the candidate book pool.
- Then create the first real source-book manifests.
- After screening, create the first populated package directories listed above.

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
The first curated excerpt layer has now been frozen on top of the seed pool:

- tracked curated packs:
  - `reading-companion-backend/eval/datasets/excerpt_cases/attentional_v2_excerpt_en_curated_v1/`
  - `reading-companion-backend/eval/datasets/excerpt_cases/attentional_v2_excerpt_zh_curated_v1/`
- local-only curated packs:
  - `reading-companion-backend/state/eval_local_datasets/excerpt_cases/attentional_v2_private_excerpt_en_curated_v1/`
  - `reading-companion-backend/state/eval_local_datasets/excerpt_cases/attentional_v2_private_excerpt_zh_curated_v1/`
- supporting manifests:
  - `reading-companion-backend/eval/manifests/splits/attentional_v2_excerpt_curated_v1.json`
  - `reading-companion-backend/eval/manifests/local_refs/attentional_v2_private_excerpt_curated_v1.json`

Current curated counts:
- tracked English curated cases: `5`
- tracked Chinese curated cases: `2`
- local English curated cases: `10`
- local Chinese curated cases: `4`

Curated-case rules in this pass:
- every curated case has explicit:
  - `question_ids`
  - `phenomena`
  - `selection_reason`
  - `judge_focus`
- curated cases use stable sentence anchors from canonical `book_document.json`
- the curated layer intentionally does not inherit the duplicate/weak `case_id` patterns from the raw seed layer

Important status nuance:
- the curated English packs are strong enough for a first-pass local evaluation run
- the repo-safe Chinese curated pack is intentionally thin, because the public-domain Chinese seed pool yielded much weaker parse-safe excerpt material than the local supplement
- later corpus work should expand public-safe Chinese sources if we want a larger tracked Chinese excerpt benchmark instead of relying mostly on local supplements

## Private Downloads Supplement Status
The first private-local supplement sourced from the user's Downloads EPUB pool has now landed outside the tracked dataset tree:

- tracked manifests:
  - `reading-companion-backend/eval/manifests/source_books/attentional_v2_private_downloads_screen_v1.json`
  - `reading-companion-backend/eval/manifests/local_refs/attentional_v2_private_downloads_seed_v1.json`
  - `reading-companion-backend/eval/manifests/corpora/attentional_v2_private_downloads_bilingual_v1.json`
  - `reading-companion-backend/eval/manifests/splits/attentional_v2_private_downloads_bilingual_v1.json`
- promoted private source books:
  - `reading-companion-backend/state/library_sources/en/private/`
  - `reading-companion-backend/state/library_sources/zh/private/`
- local-only package mirror:
  - `reading-companion-backend/state/eval_local_datasets/chapter_corpora/attentional_v2_private_chapters_en_v1/`
  - `reading-companion-backend/state/eval_local_datasets/chapter_corpora/attentional_v2_private_chapters_zh_v1/`
  - `reading-companion-backend/state/eval_local_datasets/runtime_fixtures/attentional_v2_private_runtime_en_v1/`
  - `reading-companion-backend/state/eval_local_datasets/runtime_fixtures/attentional_v2_private_runtime_zh_v1/`
  - `reading-companion-backend/state/eval_local_datasets/excerpt_cases/attentional_v2_private_excerpt_en_v1/`
  - `reading-companion-backend/state/eval_local_datasets/excerpt_cases/attentional_v2_private_excerpt_zh_v1/`
  - `reading-companion-backend/state/eval_local_datasets/compatibility_fixtures/attentional_v2_private_compat_shared_v1/`

Current counts:
- `9` promoted private source books
- `14` English chapter rows
- `4` Chinese chapter rows
- `36` English runtime fixtures
- `6` Chinese runtime fixtures
- `24` English excerpt cases
- `4` Chinese excerpt cases
- `18` shared compatibility fixture specs

Important status nuance:
- these private-local packages are structurally real and grounded in canonical parse
- their text-bearing payloads intentionally remain outside the tracked repo dataset tree
- the private excerpt cases are still auto-extracted seed cases and still require later manual curation before benchmark promotion

## Private Local Supplement Rule
- Use the tracked `eval/datasets/` tree for public-domain or otherwise repo-safe packages.
- Use `state/eval_local_datasets/` for packages derived from private books, including local excerpt packages that carry copyrighted source text.
- Keep the family roots, package contract, and manifest shape aligned across both trees so later evaluation code can treat them as parallel package territories.

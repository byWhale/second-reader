# Modern Nonfiction Expansion Booklist

Purpose: record why the next dataset-expansion pass should diversify beyond fiction-heavy sources, and freeze the first executable shortlist of modern books to acquire for that pass.
Use when: selecting books for the next local-only acquisition round, explaining why these books were chosen, or preparing user-provided downloads for ingestion.
Not for: stable evaluation constitution, final benchmark results, or source-policy authority.
Update when: the shortlist changes, the category mix changes, or a book is promoted/replaced.

## Why This Document Exists
- The current benchmark family is no longer too small to give a signal, but its source-book mix is still too literature-heavy.
- That means the benchmark is currently better at exposing:
  - literary callback / bridge behavior
  - scene-level ambiguity
  - subtle local distinction in narrative prose
- And still not broad enough at exposing:
  - argument / evidence matching
  - principles and anti-principles in nonfiction
  - decision-quality framing
  - timeline and causality over real people and institutions
  - explanatory pattern detection in biography, business, and management prose

The next acquisition pass should therefore expand genre coverage while still keeping literature as one continuing control category.

## Category Framework
This pass should cover all of these categories:
- `business`
- `management_economics`
- `biography`
- `history`
- `social_reportage`
- `science_technology`
- `psychology_decision`
- `literature`

### Weighting
This first modern gap-filling pass is intentionally not even across all categories.

Preferred emphasis:
1. `management_economics`
2. `business`
3. `biography`

Supporting categories:
- `history`
- `social_reportage`
- `science_technology`
- `psychology_decision`
- `literature`

## External Selection Signals
The shortlist below is not based on one source alone.

It uses a blend of:
- reader-popularity and reception signals
  - Goodreads annual categories such as `History & Biography`
- Chinese-reader reception and current-category breadth
  - Douban annual category coverage such as `历史文化`, `社会纪实`, `科学新知`, and `商业经管`
- stronger business-book curation
  - Financial Times / Schroders Business Book of the Year shortlist and winner coverage

Useful reference pages:
- Goodreads 2024 `History & Biography` category:
  - [Goodreads Choice Awards 2024](https://www.goodreads.com/choiceawards/readers-favorite-history-bio-books-2024)
- Douban 2024 annual category index:
  - [Curated Douban annual list mirror](https://fantribe.github.io/books/douban/annual/2024/)
- FT / Schroders Business Book of the Year 2024 shortlist summary:
  - [Yale summary of FT shortlist](https://guides.library.yale.edu/business/FT-BOTYY24)

## Acquisition / Storage Rules
- Preferred source format:
  - `EPUB`
- Acceptable fallback formats:
  - `AZW3`
  - `MOBI`
- Avoid if possible:
  - `PDF`

- For this modern-nonfiction pass, expect most books to be copyrighted and therefore local-only.
- Operational rule:
  - source books live under `reading-companion-backend/state/library_sources/`
  - text-bearing derived evaluation packages live under `reading-companion-backend/state/eval_local_datasets/`
  - tracked manifests and tracked split/corpus bookkeeping still stay under `reading-companion-backend/eval/manifests/`

### Edition-language rule
- For modern copyrighted books, download the original-language edition by default.
- Do not prefer a translation just because it matches current reading convenience.
- Use a translated edition only when:
  - the original-language edition is not practically obtainable
  - or a later explicit benchmark plan needs that translation as a separate language-track acquisition
- This means:
  - English-origin business / management / biography books should usually be downloaded in English first
  - Chinese-origin modern books should usually be downloaded in Chinese first

## First Executable Shortlist (`16` books)
This is the first concrete download list to execute when the files are available.

### Business (`4`)
1. `Poor Charlie's Almanack` / `《穷查理宝典》`
- Priority: `A`
- Preferred download language: `English original`
- Why:
  - strong for principle extraction
  - strong for mapping stories/examples to principles
  - strong for checking whether the mechanism over-generalizes advice

2. `The Almanack of Naval Ravikant` / `《纳瓦尔宝典》`
- Priority: `A`
- Preferred download language: `English original`
- Why:
  - dense aphoristic nonfiction
  - good for testing compressed claims and whether the mechanism can stay restrained
  - good for distinguishing worthy anchor lines from generic highlights

3. `Supremacy` by Parmy Olson
- Priority: `A`
- Preferred download language: `English original`
- Why:
  - modern technology-business rivalry
  - good for multi-actor conflict, institutional incentives, and AI-company causality
  - useful for modern nonfiction compared with the current literary-heavy pool

4. `Shoe Dog` / `《鞋狗》`
- Priority: `B`
- Preferred download language: `English original`
- Why:
  - entrepreneurial narrative nonfiction
  - strong for long-horizon decisions, company turning points, and reflective self-justification

### Management / Economics (`3`)
5. `Good Strategy Bad Strategy` / `《好战略，坏战略》`
- Priority: `A`
- Preferred download language: `English original`
- Why:
  - strong diagnostic / guiding-policy / action logic
  - excellent for argument-structure evaluation
  - good for detecting whether the mechanism confuses slogan-like advice with real strategy

6. `Principles` / `《原则》`
- Priority: `A`
- Preferred download language: `English original`
- Why:
  - strong rule system and abstraction ladders
  - good for principle / exception handling
  - good for evaluating whether the mechanism keeps high-level rules tied to concrete evidence

7. `The Corporation in the 21st Century` by John Kay
- Priority: `B`
- Preferred download language: `English original`
- Why:
  - modern corporate theory and anti-common-sense argument
  - useful for concept-definition, argument chain, and institution-level reasoning

### Biography (`3`)
8. `Steve Jobs` / `《乔布斯传》`
- Priority: `A`
- Preferred download language: `English original`
- Why:
  - strong long-range人物一致性与反复决策风格
  - good for timeline, causality, and reinterpretation of earlier traits

9. `Elon Musk` / `《马斯克传》`
- Priority: `A`
- Preferred download language: `English original`
- Why:
  - strong multi-project, high-conflict biography
  - useful for separating fact, evaluation, and myth-making pressure

10. `The Snowball` / `《滚雪球》`
- Priority: `A`
- Preferred download language: `English original`
- Why:
  - strong for capital-allocation reasoning
  - strong for long-term character pattern and business judgment over decades

### History (`2`)
11. `Team of Rivals`
- Priority: `B`
- Preferred download language: `English original`
- Why:
  - strong multi-person political causality
  - useful for long-range historical comparison and interpretation of conflicting motives

12. `《康熙的红票》`
- Priority: `A`
- Preferred download language: `Chinese original`
- Why:
  - high-value recent Chinese history book
  - useful for state / religion / diplomacy /制度因果链
  - helps keep the Chinese nonfiction track from becoming too business-only

### Social Reportage (`1`)
13. `Evicted` / `《扫地出门》`
- Priority: `A`
- Preferred download language: `English original`
- Why:
  - dense fact-rich social reportage
  - strong for institution-individual interaction and evidence-heavy explanation
  - useful for testing whether the mechanism can remain grounded without drifting into generic moral summary

### Science / Technology (`1`)
14. `《我看见的世界》`
- Priority: `A`
- Preferred download language: `Chinese original`
- Why:
  - modern Chinese-accessible science/technology narrative
  - useful for technical explanation, AI/vision context, and career/field evolution

### Psychology / Decision (`1`)
15. `Fooled by Randomness` / `《随机漫步的傻瓜》`
- Priority: `A`
- Preferred download language: `English original`
- Why:
  - strong for probability, luck-versus-skill, and anti-intuitive argument
  - useful for testing whether the mechanism can preserve conceptual distinctions cleanly

### Literature Control (`1`)
16. `《一句顶一万句》`
- Priority: `B`
- Preferred download language: `Chinese original`
- Why:
  - literature remains necessary as a control category
  - strong for dialogue pressure, implicit social meaning, and long-distance echo
  - keeps the benchmark from drifting into a purely expository nonfiction corpus

## Why This `16`-Book Mix Is Reasonable
- It covers the full target category set rather than expanding only one genre.
- It still matches the desired emphasis:
  - `business + management_economics + biography = 10 / 16`
- It adds enough non-literary prose to expose new failure modes:
  - argument structure
  - concept distinction
  - advice restraint
  - pattern establishment in real-world prose
  - historical and institutional causality

## Download Priority
If only part of the list can be acquired first, use this `8`-book starter subset:
1. `Poor Charlie's Almanack`
2. `The Almanack of Naval Ravikant`
3. `Fooled by Randomness`
4. `Steve Jobs`
5. `Elon Musk`
6. `Good Strategy Bad Strategy`
7. `《我看见的世界》`
8. `《康熙的红票》`

Why this subset first:
- it keeps the preferred emphasis
- it covers both Chinese and English
- it already introduces argument-heavy, biography-heavy, and science/history material into the current corpus mix

## Language Guidance
- If both Chinese and English editions are available, it is not necessary to download both in the first pass.
- For the first practical acquisition round, prefer the original-language edition by default.
- Treat translated editions as fallback rather than default.
- Long-term benchmark goal:
  - both English and Chinese tracks should eventually have enough nonfiction coverage
  - do not let all modern nonfiction land in only one language track

## Next Execution Step
When the files are available, the next acquisition pass should:
1. fingerprint and register the books in source manifests
2. import them into `state/library_sources/`
3. parse them through the canonical pipeline
4. screen them for:
   - chapter usability
   - excerpt richness
   - runtime-fixture suitability
5. build local-only benchmark packages from them under `state/eval_local_datasets/`
6. update the reviewed excerpt benchmark and later chapter corpus from the strongest resulting material

## Post-Download Expansion Workflow
This pass should happen in two layers so we can grow the dataset aggressively without losing benchmark discipline.

### Layer A: Large local-only modern supplement build
Purpose:
- ingest the downloaded books quickly
- create a much larger candidate pool than the current literature-heavy corpus
- avoid prematurely promoting weak or one-language-heavy material into the formal reviewed benchmark

Steps:
1. register all downloaded books in source manifests
2. assign each book:
   - category tags
   - language tag
   - storage mode
   - acquisition batch id
3. canonical-parse every usable book
4. produce a screening report:
   - `chapter_corpus_eligible`
   - `excerpt_only`
   - `reserve`
   - `reject_this_pass`
5. build a local-only modern supplement family under `state/eval_local_datasets/`

### Layer B: Balanced benchmark promotion
Purpose:
- take the strongest modern-nonfiction material and promote it into the formal benchmark family without breaking the benchmark rules

Promotion rules:
- do not promote from the supplement pool blindly
- promote only reviewed cases / units that are:
  - strong enough
  - category-useful
  - language-balanced at the benchmark layer
- if the downloaded pool is skewed toward one language edition, keep the full supplement local, but promote only the portion that preserves formal benchmark balance

## Larger Size Targets For This Pass
This pass should be larger than the earlier small hardening rounds.

### Book-level targets
- downloaded books:
  - target `16`
- parseable books:
  - target `12-16`
- books promoted into the modern local supplement:
  - target `12+`

### Candidate-pool targets
These are deliberately larger than the final reviewed benchmark targets.

- excerpt seed candidates:
  - target `8-12` strong candidate excerpts per usable book
  - expected total: roughly `120-160`
- chapter candidates:
  - target `2-4` chapter-scale units per usable book
  - expected total: roughly `30-50`
- runtime candidates:
  - derive from the chapter-eligible set
  - expected total: roughly `50-80` local-only fixtures

### Formal benchmark-growth targets
After review and promotion from the supplement pool, the next target sizes should be:

- curated excerpt benchmark:
  - grow from `16` per language toward `30` per language
- reviewed-active excerpt slice:
  - grow from the current `9` per language toward `12+` per language
- chapter corpus:
  - grow from `18` per language toward `30` per language
- runtime fixtures:
  - grow from `36` per language toward `54` per language when the new books materially improve chapter-position and resume coverage
- compatibility fixtures:
  - grow from `36` shared toward `54` shared after new live outputs are materialized

## What The New Books Should Improve
The modern-nonfiction pass should not only add quantity. It should improve what kinds of failures the benchmark can expose.

Priority failure surfaces:
- `argument_evidence_linkage`
  - does the mechanism keep an author's claim tied to the evidence actually given?
- `principle_boundary_control`
  - does it over-generalize management or self-help advice?
- `timeline_and_causality`
  - can it preserve long-range cause/effect in biography and history?
- `pattern_establishment_in_nonfiction`
  - can it detect enduring character, institutional, or market patterns without turning everything into generic summary?
- `concept_definition_and_distinction`
  - can it keep economically or psychologically precise distinctions intact?

## Output Of The Pass
When this pass is done, we should have:
- a registered local-only modern source pool
- a modern supplement screening report
- local-only modern supplement dataset packages
- a promotion list showing which supplement cases/chapters are strong enough for the formal benchmark
- an updated reviewed excerpt slice and expanded chapter corpus
- reruns that tell us whether the mechanism improves only on literary cases or also on modern nonfiction

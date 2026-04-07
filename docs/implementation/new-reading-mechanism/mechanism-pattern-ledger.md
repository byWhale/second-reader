# Mechanism Pattern Ledger

Purpose: preserve portable strengths, adoption candidates, failure modes, and anti-patterns discovered during evaluation and repair work.
Use when: interpreting evaluation runs, planning mechanism repairs, deciding what to carry forward from competing mechanisms, or avoiding repeated mistakes.
Not for: stable methodology authority, public API decisions, or one-off benchmark scores without interpretation.
Update when: a meaningful evaluation pass, repair pass, or cross-mechanism comparison reveals a reusable strength or a repeatable failure pattern.

This file is a living working ledger. Stable rules still belong in `docs/backend-reader-evaluation.md`. Decision-bearing adoptions or rejections should later be promoted into stable mechanism docs or `docs/history/decision-log.md`.

## Entry Format
- `Pattern kind`
  - `strength`
  - `adoption_candidate`
  - `failure_mode`
  - `anti_pattern`
- `Source mechanism`
  - where the behavior was observed first
- `Potential destination`
  - where we may adopt it, if anywhere
- `Why it matters`
  - what reader-quality dimension it improves or harms
- `Evidence`
  - reports, bundles, excerpts, or code links
- `Status`
  - `observed`
  - `candidate_for_adoption`
  - `adopt_now`
  - `defer_for_later_synthesis`
  - `reject_as_misaligned`
  - `partially_adopted`
  - `adopted`
  - `avoid`
- `Next action`
  - the immediate implementation move, or the explicit reason this entry is deferred

## Working Rule
- This ledger is not a parking lot for insights.
- After a meaningful evaluation round:
  - keep only the findings that look causally useful or protective against repeated mistakes
  - assign each kept finding a concrete disposition
  - prefer a small number of real implementation moves over a large pile of vague "maybe later" notes
- When a good behavior comes from another mechanism, do not copy it mechanically.
  - keep the currently approved mechanism's overall framework intact
  - adopt only the parts that fit that framework cleanly
  - defer or reject ideas that would require an unapproved redesign or would reintroduce known anti-patterns

## Current High-Value Patterns

### 1. Iterator V1 local micro-selectivity
- Pattern kind: `adoption_candidate`
- Source mechanism: `iterator_v1`
- Potential destination: `attentional_v2` local-reading loop and future merged mechanism
- Why it matters:
  - It notices and reacts to small but decisive local expressions instead of jumping too quickly to chapter-level summary.
  - This improves `local_impact`, especially on close-reading passages with compact but meaningful wording.
- Contributing causes:
  - the express prompt explicitly permits a free list of repeated local reactions instead of one compressed meaning-unit reaction
  - the runtime can keep multiple `highlight` / `curious` / `discern` reactions from one segment rather than forcing one surfaced output
  - curiosity/search is allowed to extend local investigation when a phrase genuinely opens a line of inquiry
- Evidence:
  - `attentional_v2_vs_iterator_v1_chapter_core_zh_round1_20260326`
  - `attentional_v2_vs_iterator_v1_chapter_core_en_microselectivity_probe_pass3_20260327`
  - `attentional_v2_vs_iterator_v1_chapter_core_en_round2_microselectivity_retry2_20260328`
  - `ouyou_zaji_public_zh__4`
  - `women_and_economics_public_en__9`
  - `on_liberty_public_en__10`
  - Example local expressions and reactions:
    - original excerpt:
      - `大運河穿過威尼斯像反寫的S；這就是大街。`
      - `好像我們戲裡大將出場，後面一杆旗子總是偏著取勢；這方場中的建築，節奏其實是和諧不過的。`
    - iterator-style reactions:
      - `「反写的S」这个比喻是否当时旅欧文学中的常见套语？还是作者的原创观察？`
      - `作者用中国传统看戏经验来理解威尼斯建筑布局的视角——不对称本身就可以是美。`
- Status: `partially_adopted`
- Next action:
  - treat the landed phrase-level cue and prompt repair as the new baseline inside the approved `attentional_v2` framework
  - treat the landed actor-intention / social-pressure / causal-stakes Phase-4 repair as the next bounded extension of that baseline
  - use the completed judged two-case rerun as the new bounded evidence source:
    - keep the `walden_205_en__10` win as proof that denser local coverage is not the only success pattern
    - diagnose why `up_from_slavery_public_en__10` still under-covers the chapter before widening the repair again

### 2. Attentional V2 chapter-scale thematic threading
- Pattern kind: `strength`
- Source mechanism: `attentional_v2`
- Potential destination: preserve and deepen in future merged mechanism
- Why it matters:
  - It can turn repeated local signals into a chapter-level thematic thread instead of leaving them as isolated reactions.
  - This improves `system_regression`, especially `coherent_accumulation` and `chapter_arc_clarity`.
- Contributing causes:
  - the loop is organized around meaning-unit closure and then chapter-level accumulation rather than around a flat list of local reactions
  - callback / distinction / durable-pattern cues are explicitly surfaced to the local cycle
  - retrospect reactions can compress repeated local signals into one chapter-level theme instead of keeping them episodic
- Evidence:
  - `attentional_v2_vs_iterator_v1_chapter_core_zh_round1_20260326`
  - `jinghua_yuan_25377_zh__34`
  - `attentional_v2_vs_iterator_v1_chapter_core_en_round3_narrative_reference_repair_parallel_caseiso_judged_20260329`
  - `walden_205_en__10`
  - Example original signals:
    - `屢次要尋自盡，無奈眾人日夜提防，真是求生不能，求死不得。`
  - Attentional V2 repeatedly lifted the same phrase across multiple chapter moments and then closed with:
    - `此八字在本章四度標記極端困境……形成情感共振，凝結為本章最核心的主題訊號。`
  - `walden` judged lesson:
    - a lower-volume but disciplined chain of reactions can still beat broader local coverage when every move advances one live interpretive axis instead of restarting from scratch
- Status: `observed`
- Next action:
  - preserve as a protected design strength while borrowing local-reading improvements; do not sacrifice chapter-scale accumulation for denser surface reactions
  - treat `walden_205_en__10` as the concrete reference case for one-axis narrative/reference-heavy threading inside `attentional_v2`

### 3. Attentional V2 callback-cue and durable-pattern repair
- Pattern kind: `partially_adopted`
- Source mechanism: `attentional_v2`
- Potential destination: retain as baseline in future merged mechanism
- Why it matters:
  - The second repair pass showed that explicit cue packets can materially improve weak local cases instead of only changing wording.
  - This is one of the strongest examples of a repair changing benchmark outcomes in a trustworthy way.
- Contributing causes:
  - deterministic local cue packets keep the model centered on the exact textual pressure
  - merged bridge candidates now reach controller choice instead of being dropped before decision time
  - the repaired prompts now ask for exact callback / distinction / pattern naming instead of generic scene paraphrase
- Evidence:
  - targeted repair reports:
    - `attentional_v2_integrity_repair_pass1_targeted_20260326`
    - `attentional_v2_integrity_repair_pass2_targeted_20260326`
  - code:
    - `reading-companion-backend/src/attentional_v2/nodes.py`
    - `reading-companion-backend/src/attentional_v2/prompts.py`
    - `reading-companion-backend/src/attentional_v2/runner.py`
  - observed repair targets:
    - `callback_cue`
    - `distinction_cue`
    - `recognition_gap`
    - `durable_pattern`
- Status: `partially_adopted`
- Next action:
  - treat cue-packet support as part of the new baseline and continue narrow repairs on honest anchor resolution and distinction closure

## Current High-Value Failure Memory

### 4. Sparse but globally correct reading is not enough for strong `local_impact`
- Pattern kind: `anti_pattern`
- Source mechanism: `attentional_v2`
- Potential destination: avoid in future merged mechanism
- Why it matters:
  - A mechanism can be globally coherent yet still lose passage-level comparison if it reacts too sparsely and skips the tiny local expressions that make the reading feel earned.
  - On long chapters, a few plausible late reactions are not enough if the mechanism never establishes chapter presence from the opening pressure onward.
- Contributing causes:
  - `reaction_emission` is intentionally gated and often withholds visible output
  - closure pressure encourages one distilled meaning-unit reading rather than multiple local observations
  - this can produce correct chapter sense while still missing the small local expression that the judge rewards in `local_impact`
  - ambiguous chapter metadata can make that sparse pattern look even less trustworthy because the judge starts doubting whether the mechanism stayed on the intended chapter at all
- Evidence:
  - `attentional_v2_vs_iterator_v1_chapter_core_en_round1_20260326`
  - `attentional_v2_vs_iterator_v1_chapter_core_en_round2_microselectivity_retry2_20260328`
  - `attentional_v2_vs_iterator_v1_chapter_core_en_round3_narrative_reference_repair_parallel_caseiso_judged_20260329`
  - `women_and_economics_public_en__9`
  - `on_liberty_public_en__10`
  - `up_from_slavery_public_en__10`
  - `walden_205_en__10`
  - pattern seen in judge reasons:
    - V2 often read correctly but felt like retrospective summary rather than live local investigation.
    - `up_from_slavery_public_en__10` is the cleanest recent example:
      - only a few late reactions over a long chapter
      - missed the opening cues the judge treated as decisive
      - judge trust was worsened by ambiguous chapter numbering metadata even though the underlying chapter row appears internally consistent
- Status: `avoid`
- Next action:
  - use this as a guardrail when testing local-reading improvements; reject repairs that only improve chapter summary polish without increasing earned local contact
  - the next repair should target sustained chapter presence, earlier cue uptake, and metadata clarity on long narrative / reference-heavy chapters instead of just adding more summary polish

### 5. Wrong-chapter or wrong-target traversal corrupts chapter-scale evaluation even if local reactions look rich
- Pattern kind: `anti_pattern`
- Source mechanism: `iterator_v1`
- Potential destination: avoid in future merged mechanism
- Why it matters:
  - Rich local reactions are not a product win if they happen on the wrong chapter or never accumulate on the assigned target text.
- Contributing causes:
  - section-first traversal can still fail catastrophically at chapter targeting
  - once the mechanism is misaligned with the target chapter, local reaction richness becomes misleading rather than helpful
- Evidence:
  - `attentional_v2_vs_iterator_v1_chapter_core_en_round1_20260326`
  - `women_and_economics_public_en__9`
  - `ouyou_zaji_public_zh__4`
  - judge reason examples:
    - `Iterator V1 ... never accesses Chapter IV at all`
    - `Iterator V1 ... only processed Chapter 1 (封面), completely missing the target chapter`
- Status: `avoid`
- Next action:
  - preserve as a cross-mechanism negative gate; no mechanism should be treated as strong if target-chapter alignment is unstable

### 6. Callback cue without honest anchor resolution still causes false confidence
- Pattern kind: `failure_mode`
- Source mechanism: `attentional_v2`
- Potential destination: future bridge-resolution refinement
- Why it matters:
  - The mechanism may notice an explicit callback cue but still bridge to the wrong earlier material instead of saying the anchor is not honestly available.
  - This creates misleading fluency in bridge cases.
- Contributing causes:
  - cue detection can succeed before source-anchor resolution is actually honest
  - the current bridge path is better than before, but still sometimes prefers a weak earlier echo over an explicit "anchor not available" outcome
- Evidence:
  - repaired reviewed-slice work on:
    - `jinghua_yuan_25377_zh__15__callback_bridge__v2`
    - `nahan_27166_zh__2__callback_bridge__v2`
  - post-repair interpretation in:
    - `attentional_v2_integrity_repair_pass2_targeted_20260326`
    - `attentional_v2_integrity_reviewed_slice_round3_repair_pass2_20260326`
- Status: `observed`
- Next action:
  - prioritize a future narrow repair that teaches the mechanism to say "callback cue present but honest anchor unavailable" instead of forcing a weak bridge

### 7. Benchmark winner/loser language alone is insufficient memory
- Pattern kind: `anti_pattern`
- Source mechanism: evaluation process itself
- Potential destination: all future comparison passes
- Why it matters:
  - If we preserve only who won, we lose the transferable strengths and the repeated mistakes that should shape the next mechanism.
  - This was the direct motivation for this ledger.
- Evidence:
  - first broader chapter-core comparison:
    - `attentional_v2_vs_iterator_v1_chapter_core_en_round1_20260326`
    - `attentional_v2_vs_iterator_v1_chapter_core_zh_round1_20260326`
- Status: `avoid`
- Next action:
  - require each meaningful evaluation closeout to include result, causal interpretation, and selective implementation disposition rather than winner/loser prose alone

### 8. A full judged lane can finish cleanly yet still be unusable if every case falls back to `mechanism_unavailable`
- Pattern kind: `anti_pattern`
- Source mechanism: evaluation harness / provider posture
- Potential destination: all future judged eval launches
- Why it matters:
  - A run can emit `summary/aggregate.json` and `summary/report.md` while still containing no valid product evidence.
  - If that output is misread as a giant tie, the project can draw false mechanism conclusions from pure provider failure.
- Contributing causes:
  - the full human-notes-guided excerpt judged lane used one forced `MiniMax-M2.7-highspeed` target
  - the run's quota wait budget was shorter than the provider cooldown windows that appeared during full-chapter reading
  - once each shared chapter unit failed at the mechanism stage, downstream judge surfaces emitted zero-score `mechanism_unavailable` ties
- Evidence:
  - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_human_notes_guided_excerpt_eval_v1_judged_20260404/summary/aggregate.json`
  - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_human_notes_guided_excerpt_eval_v1_judged_20260404/summary/report.md`
  - `reading-companion-backend/state/job_registry/logs/bgjob_human_notes_guided_excerpt_eval_v1_judged_20260404.log`
- Status: `avoid`
- Next action:
  - rerun the judged local excerpt lane only under a quota-safe target / wait-budget posture
  - do not convert this failed lane into mechanism findings

### 9. Long-span probes that share a theme but lack explicit carryforward are false positives for `coherent_accumulation`
- Pattern kind: `anti_pattern`
- Source mechanism: accumulation benchmark v1 probe construction
- Potential destination: all future long-span benchmark building
- Why it matters:
  - The benchmark starts measuring general thematic resemblance instead of bounded carryover from earlier reading.
  - This wastes long reads while still failing to answer the real north-star question.
- Contributing causes:
  - later anchors often remain philosophically related to earlier anchors without explicitly depending on them
  - judge focus becomes too broad, so the case tries to test several things at once
  - chapter/span metadata defects further weaken judge trust even when the source window itself is better chosen
- Evidence:
  - `reading-companion-backend/eval/review_packets/archive/accumulation_benchmark_v1_rejudged_first_review_20260404/dataset_review_pipeline_summary.json`
  - `reading-companion-backend/eval/review_packets/archive/accumulation_benchmark_v1_rejudged_first_review_20260404/llm_review_report.md`
- Status: `avoid`
- Next action:
  - tighten the long-span probe contract so later anchors must show explicit callback, continuation, consequence, or distinction carryforward
  - fix chapter/span metadata before rerunning review
  - allow `1-2` strong probes per window instead of forcing weak thirds

### 10. Attentional V2 local-cycle call amplification can make a semantically promising run operationally unusable
- Pattern kind: `failure_mode`
- Source mechanism: `attentional_v2`
- Potential destination: immediate `attentional_v2` throughput repair
- Why it matters:
  - The mechanism can preserve a plausible reading shape while still demanding too many LLM calls per chapter to support fast judged iteration.
  - Under real quota pressure, this turns one judged excerpt lane into hours of work with very little two-mechanism overlap.
- Contributing causes:
  - the active local cycle repeatedly calls `meaning_unit_closure` and `controller_decision` at very high frequency
  - `reaction_emission` is still triggered often enough to add another large layer of calls
  - long chapters and low-ROI speech-like chapters magnify this loop dramatically
- Evidence:
  - completed retry3 excerpt lane:
    - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_human_notes_guided_excerpt_eval_v1_judged_parallel_retry1_20260405/summary/llm_usage.json`
    - `reading-companion-backend/state/job_registry/logs/bgjob_human_notes_excerpt_parallel_judged_shard_a_dualpool_recovery_retry3_20260405.log`
    - `reading-companion-backend/state/job_registry/logs/bgjob_human_notes_excerpt_parallel_judged_shard_b_dualpool_recovery_retry3_20260405.log`
  - concrete per-unit comparisons from the same run:
    - `nawaer_baodian_private_zh__chapter_22`: `220` vs `28` reader calls, about `5.25x` wall-clock
    - `nawaer_baodian_private_zh__chapter_23`: `126` vs `26` reader calls, about `3.2x` wall-clock
    - `huochu_shengming_de_yiyi_private_zh__chapter_8`: `922` vs `71` reader calls, about `6.78x` wall-clock before failure
    - `value_of_others_private_en__chapter_8`: `1105` vs `123` reader calls, about `2.65x` wall-clock before failure
  - dominant node families in the same traces:
    - `meaning_unit_closure`
    - `controller_decision`
    - `reaction_emission`
- repair proof:
  - bounded throughput-repair smoke:
    - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_excerpt_micro_slice_v1_smoke_throughput_repair_20260405/summary/aggregate.json`
    - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_excerpt_micro_slice_v1_smoke_throughput_repair_20260405/summary/llm_usage.json`
    - `reading-companion-backend/state/job_registry/logs/bgjob_attentional_v2_excerpt_micro_slice_smoke_20260405.log`
  - judged proof on the same bounded slice:
    - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_excerpt_micro_slice_v1_judged_throughput_repair_20260405/summary/aggregate.json`
    - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_excerpt_micro_slice_v1_judged_throughput_repair_20260405/summary/report.md`
    - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_excerpt_micro_slice_v1_judged_throughput_repair_20260405/summary/llm_usage.json`
  - landed code and tests:
    - `reading-companion-backend/src/attentional_v2/nodes.py`
    - `reading-companion-backend/src/attentional_v2/runner.py`
    - `reading-companion-backend/tests/test_attentional_v2_nodes.py`
    - `reading-companion-backend/tests/test_attentional_v2_scaffold.py`
  - measured post-repair micro-slice totals:
    - `nawaer_baodian_private_zh__chapter_22`: `220 -> 21`
    - `xidaduo_private_zh__chapter_15`: `513 -> 64`
    - combined two-unit baseline: `733 -> 85` reader calls (`-88.4%`)
- judged bounded-slice outcome after the repair:
  - `selective_legibility`:
    - `13` cases
    - winner counts:
      - `attentional_v2 = 8`
      - `iterator_v1 = 4`
      - `tie = 1`
    - average scores:
      - `attentional_v2 = 2.277`
      - `iterator_v1 = 0.938`
  - `insight_and_clarification`:
    - `8` cases
    - winner counts:
      - `attentional_v2 = 6`
      - `iterator_v1 = 1`
      - `tie = 1`
    - average scores:
      - `attentional_v2 = 2.25`
      - `iterator_v1 = 0.6`
  - no `judge_unavailable`
  - no `mechanism_failure`
- Status: `adopted`
- Next action:
  - keep the landed bounded schedule repair as the new baseline:
    - no-LLM watch path for `no_zoom` and `monitor`
    - deterministic controller fast path for straightforward `advance`
    - lazy deterministic bridge retrieval
    - tighter `reaction_emission` eligibility
  - do not open a second broad throughput pass immediately
  - keep the next narrow mechanism follow-up focused on exact target-anchor coverage in the remaining `xidaduo` local misses before revisiting deeper schedule changes

### 11. Full-surface judged excerpt runs can waste most of their budget on early heavy low-ROI chapters
- Pattern kind: `anti_pattern`
- Source mechanism: evaluation launch posture
- Potential destination: all future excerpt judged launches
- Why it matters:
  - A run can spend hours on a few heavy chapters before later units even begin, which means the project learns almost nothing new while still paying near-full cost.
  - This is especially damaging when one mechanism is much more expensive than the other.
- Contributing causes:
  - shard worker slots are occupied by the first submitted heavy units
  - low-ROI speech / anthology chapters can still consume a large share of wall-clock and quota budget
  - later higher-value units may start only after the provider posture is already degraded
- Evidence:
  - completed retry3 excerpt lane:
    - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_human_notes_guided_excerpt_eval_v1_judged_parallel_retry1_20260405`
  - observed completion split from the run:
    - `7 / 55` cases finished with both mechanisms
    - `34 / 55` finished with only `iterator_v1`
    - `14 / 55` finished with both mechanisms failed
  - late-start examples from the same run:
    - `nawaer_baodian_private_zh__chapter_13` and `xidaduo_private_zh__chapter_15` only began issuing `attentional_v2` calls near the very end of the run window
- Status: `adopted`
- Next action:
  - keep treating the explicit ROI-first micro-slice as the default judged repair harness
  - the completed bounded judged proof run is:
    - `bgjob_attentional_v2_excerpt_micro_slice_judged_20260405`
    - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_excerpt_micro_slice_v1_judged_throughput_repair_20260405`
  - with that gate now cleared, move next to the fuller excerpt surface rather than rerunning another large judged lane immediately

### 12. Attentional V2 can stay chapter-locally coherent yet still miss the exact designated anchor line
- Pattern kind: `failure_mode`
- Source mechanism: `attentional_v2`
- Potential destination: narrow `zoom_now` / closure anchor-carrythrough refinement
- Why it matters:
  - On excerpt cases, nearby strong reading is not enough when the case is testing whether the mechanism really noticed one designated local reversal or statement.
  - A chapter-local thematic thread can therefore still underperform if the matched reactions land near the target instead of on it.
- Contributing causes:
  - the repaired schedule is now much more selective, which is good for throughput, but that selectivity can stay attached to the dominant nearby thread instead of the exact anchor line
  - compressed philosophical lines late in a chapter can be especially easy to under-cover if earlier nearby pressure already captured the mechanism's local loop
- Evidence:
  - bounded judged micro-slice:
    - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_excerpt_micro_slice_v1_judged_throughput_repair_20260405/summary/report.md`
    - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_excerpt_micro_slice_v1_judged_throughput_repair_20260405/shards/default/cases/xidaduo_private_zh__15__anchored_reaction_selectivity__seed_3.json`
    - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_excerpt_micro_slice_v1_judged_throughput_repair_20260405/shards/default/cases/xidaduo_private_zh__15__anchored_reaction_selectivity__seed_4.json`
    - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_excerpt_micro_slice_v1_judged_throughput_repair_20260405/shards/default/cases/xidaduo_private_zh__15__tension_reversal__seed_1.json`
  - judge pattern:
    - V2 often remained text-grounded and chapter-relevant
    - but some matched reactions centered on `15.25`, `15.6`, or `15.45` rather than the designated anchors at `15.19` or `15.34`
- Status: `observed`
- Next action:
  - inspect these exact `xidaduo` misses before the next broad judged rerun
  - prefer a narrow anchor-carrythrough repair inside the existing `zoom_now` / closure flow rather than reopening generic reaction density

### 13. Attentional V2 excerpt-surface strength survives the throughput repair when the pressure is chapter-local and tension-heavy
- Pattern kind: `strength`
- Source mechanism: `attentional_v2`
- Potential destination: preserve as the protected excerpt-reading baseline
- Why it matters:
  - The full formal excerpt run shows that the bounded throughput repair did not erase V2's main comparative advantage.
  - V2 still wins when the case rewards staying with one live chapter-local pressure line instead of only hitting one narrow local phrase.
- Contributing causes:
  - the repaired schedule still leaves enough local interpretive depth to track chapter pressure and rhetorical reversal
  - V2 remains especially effective when the case asks for legible notice plus downstream clarification rather than one brittle pinpoint callback
- Evidence:
  - formal excerpt run:
    - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_excerpt_surface_v1_1_judged_20260406/summary/aggregate.json`
    - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_excerpt_surface_v1_1_judged_20260406/summary/report.md`
    - `reading-companion-backend/docs/evaluation/excerpt/attentional_v2_excerpt_surface_v1_1_judged_20260406_interpretation.md`
  - strongest chapter/profile evidence:
    - `huochu_shengming_de_yiyi_private_zh__8`
    - `nawaer_baodian_private_zh__22`
    - `anchored_reaction_selectivity`
    - `tension_reversal`
- Status: `observed`
- Next action:
  - preserve this chapter-local pressure tracking as a design invariant
  - do not trade it away for a brittle exact-anchor hack that only improves a narrow bucket

### 14. Attentional V2 still loses when the benchmark demands exact late-local anchor carrythrough rather than nearby same-chapter pressure
- Pattern kind: `failure_mode`
- Source mechanism: `attentional_v2`
- Potential destination: narrow local-anchor refinement inside `zoom_now` / closure
- Why it matters:
  - The formal excerpt run confirms that V2's remaining local weakness is not generic under-reading but anchor drift.
  - It can read the right neighborhood, or even the right chapter argument, and still lose because the case is testing one exact local reversal.
- Contributing causes:
  - once V2 locks onto a nearby dominant thread, later compressed anchor lines can inherit only partial carrythrough
  - the repaired schedule's selectivity makes this more visible on philosophical and embodied-paradox passages
- Evidence:
  - formal excerpt interpretation cases:
    - `xidaduo_private_zh__15__tension_reversal__seed_1`
    - `meiguoren_de_xingge_private_zh__19__tension_reversal__seed_5`
    - `reading-companion-backend/docs/evaluation/excerpt/attentional_v2_excerpt_surface_v1_1_judged_20260406_interpretation.md`
- Status: `observed`
- Next action:
  - keep the next mechanism repair narrow:
    - improve exact anchor carrythrough on late-local reversals
    - do not reopen broad reaction-density or throughput work first

### 15. Iterator V1 still retains a narrow local-anchor and small backward-bridge advantage worth selective reuse
- Pattern kind: `adoption_candidate`
- Source mechanism: `iterator_v1`
- Potential destination: `attentional_v2`
- Why it matters:
  - The formal excerpt run shows that V1 can still beat V2 when the case rewards exact local placement or a small backward callback.
  - This is a useful reminder that V2 has not yet subsumed V1's finest-grained local precision.
- Contributing causes:
  - V1 is more willing to stay on one tight local hinge instead of widening toward chapter-level thematic explanation
  - this helps on embodied paradox lines and short callback bridges, even though it can drift into over-association elsewhere
- Evidence:
  - formal excerpt interpretation cases:
    - `xidaduo_private_zh__15__tension_reversal__seed_1`
    - `nawaer_baodian_private_zh__22__callback_bridge__seed_1`
    - `reading-companion-backend/docs/evaluation/excerpt/attentional_v2_excerpt_surface_v1_1_judged_20260406_interpretation.md`
- Status: `candidate_for_adoption`
- Next action:
  - look for a selective way to preserve V1-style exact local placement and tiny backward-bridge honesty inside V2
  - do not import V1's external-theory drift or loose associative expansion

### 16. Late low-pressure open meaning units can stay alive and turn a repaired local cycle back into overread
- Pattern kind: `failure_mode`
- Source mechanism: `attentional_v2`
- Potential destination: next narrow stale-unit closure guard inside `zoom_now` / local-cycle control
- Why it matters:
  - The second narrow-repair smoke shows that V2 can reintroduce operational drag even after the throughput repair if a late open meaning unit never closes.
  - This is not just "slow reading"; it is a concrete mechanism failure where the local cycle keeps living on a cooled span that no longer carries strong live pressure.
- Contributing causes:
  - cadence / question-mark escalation can keep reopening attention even after `working_pressure` has cooled out
  - the current local-hinge narrowing is not yet enough when no anchored closure actually lands
  - once the open span keeps growing, later local cycles become less honest and more expensive at the same time
- Evidence:
  - round-2 smoke blocker:
    - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_excerpt_micro_slice_v1_smoke_narrow_repair_round2_20260406/shards/default/outputs/xidaduo_private_zh__chapter_15/attentional_v2/_mechanisms/attentional_v2/runtime/local_buffer.json`
    - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_excerpt_micro_slice_v1_smoke_narrow_repair_round2_20260406/shards/default/outputs/xidaduo_private_zh__chapter_15/attentional_v2/_mechanisms/attentional_v2/runtime/trigger_state.json`
    - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_excerpt_micro_slice_v1_smoke_narrow_repair_round2_20260406/shards/default/outputs/xidaduo_private_zh__chapter_15/attentional_v2/_mechanisms/attentional_v2/runtime/working_pressure.json`
  - concrete observed state:
    - `current_sentence_id = c15-s248`
    - `open_meaning_unit_sentence_ids = c15-s158 .. c15-s248`
    - open span size `= 91`
    - `working_pressure.pressure_snapshot` had already cooled out
- Status: `observed`
- Next action:
  - if the narrow repair loop is reopened later, prioritize a deterministic stale-unit close/reset rule before adding more prompt pressure or more local read depth

### 17. Callback-cue widening alone still collapses into chapter-end retrospect unless an explicit earlier target is forced
- Pattern kind: `failure_mode`
- Source mechanism: `attentional_v2`
- Potential destination: next narrow bridge-specificity refinement
- Why it matters:
  - The second narrow-repair smoke showed that seeing `前面`-style callback pressure is not the same as producing an honest callback bridge.
  - Without a concrete earlier source target, the mechanism still tends to satisfy the pressure with a generic retrospective chapter reaction.
- Contributing causes:
  - explicit callback-cue routing widened retrieval pressure, but the controller/bridge path still allowed chapter-end retrospect to absorb the case
  - bridge-specificity is still weaker than the cue-detection path
- Evidence:
  - round-2 smoke blocker:
    - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_excerpt_micro_slice_v1_smoke_narrow_repair_round2_20260406/shards/default/outputs/nawaer_baodian_private_zh__chapter_22/attentional_v2/_mechanisms/attentional_v2/runtime/reaction_records.json`
    - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_excerpt_micro_slice_v1_smoke_narrow_repair_round2_20260406/shards/default/outputs/nawaer_baodian_private_zh__chapter_22/attentional_v2/_mechanisms/attentional_v2/runtime/move_history.json`
  - concrete observed output:
    - the only visible reaction remained `rx:Chapter_22:c22-s87:retrospect:1`
- Status: `observed`
- Next action:
  - if the repair loop is reopened, require bridge resolution to either name a concrete earlier target or decline explicitly; do not let retrospective chapter summary count as bridge satisfaction

## Current Selective Implementation Queue

### Priority 0. Prevent late low-pressure open spans from dragging through the chapter tail
- Why now:
  - the second narrow-repair smoke failed before judged promotion because `xidaduo` turned into a `91`-sentence stale open span
- Boundaries:
  - do not solve this by flattening the mechanism into denser always-on local reactions
  - keep the existing no-LLM watch path, controller fast path, and lazy bridge retrieval as baseline
- Concrete implementation direction:
  - if a later third round is approved, start with a deterministic stale-unit close/reset rule when:
    - an open span is already large
    - working pressure is cool
    - no anchored hinge, bridge pull, or reframe pressure remains live
  - do not add more prompt sophistication before that control bug is fixed

### Priority 1. Continue honest callback resolution until bridge specificity is real
- Why now:
  - `nawaer` still ended round 2 as a chapter-end retrospect instead of a concrete earlier-target callback bridge
- Concrete implementation direction:
  - if the loop is reopened, force `bridge_resolution` to either:
    - name a concrete earlier source target and relation
    - or decline explicitly
  - do not allow callback pressure to be "satisfied" by thematic retrospect alone

### Priority 2. Preserve local-anchor carrythrough without benchmark injection
- Why now:
  - the original narrow repair target is still real: `xidaduo`-style late-local reversals and `meiguoren`-style definition closure should get closer to the current passage, not just the surrounding chapter argument
- Concrete implementation direction:
  - keep the repair grounded in local text, local state, and nearby backcheck only
  - reject any future change that depends on benchmark metadata or turns V2 into a sentence-matching solver

### Priority 3. Preserve chapter-scale thematic threading as a protected invariant
- Why now:
  - the formal excerpt run still shows that chapter-local pressure tracking is one of `attentional_v2`'s strongest real differentiators
- Concrete implementation direction:
  - reject any future repair that improves one brittle exact-anchor bucket by sacrificing motif threading, callback carryover, or chapter-arc closure

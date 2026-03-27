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
  - `ouyou_zaji_public_zh__4`
  - Example local expressions and reactions:
    - original excerpt:
      - `大運河穿過威尼斯像反寫的S；這就是大街。`
      - `好像我們戲裡大將出場，後面一杆旗子總是偏著取勢；這方場中的建築，節奏其實是和諧不過的。`
    - iterator-style reactions:
      - `「反写的S」这个比喻是否当时旅欧文学中的常见套语？还是作者的原创观察？`
      - `作者用中国传统看戏经验来理解威尼斯建筑布局的视角——不对称本身就可以是美。`
- Status: `adopt_now`
- Next action:
  - trial a narrowly bounded increase in local micro-selectivity inside the approved `attentional_v2` framework without abandoning gated reaction emission or meaning-unit closure

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
  - Example original signals:
    - `屢次要尋自盡，無奈眾人日夜提防，真是求生不能，求死不得。`
  - Attentional V2 repeatedly lifted the same phrase across multiple chapter moments and then closed with:
    - `此八字在本章四度標記極端困境……形成情感共振，凝結為本章最核心的主題訊號。`
- Status: `observed`
- Next action:
  - preserve as a protected design strength while borrowing local-reading improvements; do not sacrifice chapter-scale accumulation for denser surface reactions

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
- Contributing causes:
  - `reaction_emission` is intentionally gated and often withholds visible output
  - closure pressure encourages one distilled meaning-unit reading rather than multiple local observations
  - this can produce correct chapter sense while still missing the small local expression that the judge rewards in `local_impact`
- Evidence:
  - `attentional_v2_vs_iterator_v1_chapter_core_en_round1_20260326`
  - `women_and_economics_public_en__9`
  - `on_liberty_public_en__10`
  - pattern seen in judge reasons:
    - V2 often read correctly but felt like retrospective summary rather than live local investigation.
- Status: `avoid`
- Next action:
  - use this as a guardrail when testing local-reading improvements; reject repairs that only improve chapter summary polish without increasing earned local contact

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

## Current Selective Implementation Queue

### Priority 1. Increase local micro-selectivity inside `attentional_v2`
- Why now:
  - the last chapter-core comparison showed the clearest remaining weakness is chapter-local reading behavior, especially on the English pack
  - this is also the cleanest high-confidence positive adoption candidate from `iterator_v1`
- Boundaries:
  - keep gated reaction emission
  - keep meaning-unit closure as the controlling frame
  - do not convert `attentional_v2` into a flat multi-reaction stream
- Concrete implementation direction:
  - let the local cycle surface one additional micro-observation when a compact phrase carries real local pressure
  - improve explicit handling of analogy, unusual wording, and compact rhetorical turns
  - prefer "small earned local contact" over broader retrospective summary in those moments

### Priority 2. Preserve chapter-scale thematic threading as a protected invariant
- Why now:
  - the same comparison showed this is one of `attentional_v2`'s strongest differentiators in `system_regression`
  - a local-reading repair that damages this strength would be a bad trade
- Concrete implementation direction:
  - treat chapter-scale accumulation as non-negotiable when testing local-reading improvements
  - reject any local-reading change that increases surface activity but weakens motif threading, callback carryover, or chapter-arc closure

### Priority 3. Continue honest callback resolution instead of forced bridging
- Why now:
  - one of the remaining narrow failures still comes from seeing callback pressure without handling missing anchors honestly
- Concrete implementation direction:
  - add a stronger explicit outcome for:
    - callback cue present
    - honest supporting anchor not available
  - prefer unresolved-but-honest bridge state over a weak earlier echo

### Priority 4. Deepen distinction / recognition-gap closure without broad redesign
- Why now:
  - the repair passes improved distinction handling, but some cases still become shallow rather than fully centered on the recognition gap
- Concrete implementation direction:
  - strengthen closure-time prioritization when the local cue packet marks a distinction or recognition gap
  - keep this as a bounded prompt/controller refinement, not a mechanism rewrite

### Priority 5. Keep target-alignment failure as a hard comparative anti-pattern
- Why now:
  - the broader comparison also showed that rich local behavior is worthless when the mechanism drifts off the target chapter
- Concrete implementation direction:
  - preserve this as a negative gate in future cross-mechanism evaluation and synthesis
  - do not adopt any local-reading behavior from another mechanism without checking target-alignment reliability

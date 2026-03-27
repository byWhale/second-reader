## Private-Library Promotion Round 1 Chapter Sanity Results

Date: `2026-03-27`  
Checklist source: [private-library-promotion-round1-chapter-sanity-checklist.md](/Users/baiweijiang/Documents/Projects/reading-companion/docs/implementation/new-reading-mechanism/private-library-promotion-round1-chapter-sanity-checklist.md)  
Selection source: [private-library-promotion-round1-selection.json](/Users/baiweijiang/Documents/Projects/reading-companion/docs/implementation/new-reading-mechanism/private-library-promotion-round1-selection.json)

## Method

This pass was grounded in the actual local chapter artifacts, not only the checklist prose.

Artifacts checked:
- [chapters_en_v2/chapters.jsonl](/Users/baiweijiang/Documents/Projects/reading-companion/reading-companion-backend/state/eval_local_datasets/chapter_corpora/attentional_v2_private_library_chapters_en_v2/chapters.jsonl)
- [chapters_zh_v2/chapters.jsonl](/Users/baiweijiang/Documents/Projects/reading-companion/reading-companion-backend/state/eval_local_datasets/chapter_corpora/attentional_v2_private_library_chapters_zh_v2/chapters.jsonl)
- [attentional_v2_private_library_screen_v2.json](/Users/baiweijiang/Documents/Projects/reading-companion/reading-companion-backend/eval/manifests/source_books/attentional_v2_private_library_screen_v2.json)
- each selected source book’s `public/book_document.json`

Judgment criteria:
- chapter alignment
- boundary cleanliness
- size safety
- role fit
- duplication pressure

Assumptions:
- several chapter-corpora records do not carry start/end CFI boundaries, so boundary judgment had to rely on `chapter_id` / `chapter_title`, `href`, and visible opening/closing text from `public/book_document.json`
- `pass` here means sanity-cleared for round-1 comparison preparation, not final benchmark promotion approval

## Overall Finding

English is sanity-cleared as selected. All `8` English chapter candidates can move to the next chapter-lane preparation step.

Chinese is not sanity-cleared as a full `8`-chapter pack. Only `2` Chinese chapter candidates are ready immediately. The other `6` should wait for recut, replacement, or reparsing before they enter a formal chapter comparison pack.

Summary:

| Language | Pass | Revise | Defer |
| --- | ---: | ---: | ---: |
| English | 8 | 0 | 0 |
| Chinese | 2 | 3 | 3 |

Promote next:
- English: all selected `8`
- Chinese: `biji_de_fangfa_private_zh__13`, `zouchu_weiyi_zhenliguan_private_zh__14`

Wait:
- `kangxi_hongpiao_private_zh__12`
- `kangxi_hongpiao_private_zh__27`
- `fooled_by_randomness_private_zh__19`
- `meiguoren_de_xingge_private_zh__8`
- `zhangzhongmou_zizhuan_private_zh__10`
- `zhangzhongmou_zizhuan_private_zh__11`

## English Findings

### Ready To Promote Next

`good_strategy_bad_strategy_private_en__22`
- Status: `pass`
- Why: clean leverage chapter, moderate size, concrete pivot-point examples, and a real ending rather than summary-only drift
- Grounding:
  - opens on “A good strategy draws power from focusing minds, energy, and action”
  - closes on the Getty example and “the power of concentration”

`good_strategy_bad_strategy_private_en__55`
- Status: `pass`
- Why: the “late-book synthesis” risk is real, but the actual artifact stays anchored in the Nvidia case and closes on the Tesla/Tegra pincer rather than generic recap
- Grounding:
  - opens on Nvidia’s rise
  - closes on the two-pronged pincer and the uncertainty of both paths

`evicted_private_en__10`
- Status: `pass`
- Why: true chapter content, clean opening, clean handoff into Arleen, and strong expository grounding through scene-based nonfiction
- Grounding:
  - opens on Milwaukee / Sherrena / landlord route through the North Side
  - closes on the Wraparound call and Arleen’s arrival

`fooled_by_randomness_private_en__14`
- Status: `pass`
- Why: coherent argumentative chapter on induction with a self-contained ending; no front matter or appendix contamination
- Grounding:
  - chapter heading is “THE PROBLEM OF INDUCTION”
  - closes on Pascal, stop-loss, and “THANK YOU, SOLON”

`supremacy_private_en__13`
- Status: `pass`
- Why: clear DeepMind spin-out / ethics-pressure chapter, structurally clean, and distinct from the later AGI-race chapter
- Grounding:
  - opens inside DeepMind / Google structure
  - closes on whether meaningful AI ethics work can happen inside a large corporation

`supremacy_private_en__23`
- Status: `pass`
- Review-first item: cleared
- Why: late-book governance / monopoly argument is real and clearly distinct from `supremacy_private_en__13`
- Grounding:
  - opens on AGI moving from fringe dream to serious public belief
  - closes on tactics vs strategy and the winners of the tournament

`steve_jobs_private_en__17`
- Status: `pass`
- Why: clean causal biography chapter about Lisa / Xerox / GUI pressure and Jobs losing control
- Grounding:
  - opens on Apple II success and Jobs’s restlessness
  - closes on the 1980 reorganization and Jobs losing control of the Lisa division

`steve_jobs_private_en__24`
- Status: `pass`
- Why: chapter-clean launch narrative, strong event pressure, and clearly distinct from the Lisa chapter
- Grounding:
  - opens on the launch package
  - closes on the Macintosh reveal and Jobs presenting machines to the team

## Chinese Findings

### Ready To Promote Next

`biji_de_fangfa_private_zh__13`
- Status: `pass`
- Why: short but clean expository method chapter with explicit principle framing and a proper closing summary
- Grounding:
  - opens on “如何夺取主动权，避免信息成瘾，跳出信息茧房”
  - closes by restating the three principles and their common purpose

`zouchu_weiyi_zhenliguan_private_zh__14`
- Status: `pass`
- Why: interview-format exposition stays on one philosophical problem and closes cleanly; role fit still holds as `expository`
- Grounding:
  - opens on “讲道理” and the relation between thought and practice
  - closes on Chinese logical vocabulary and cross-civilizational dialogue

### Revise Before Promotion

`kangxi_hongpiao_private_zh__12`
- Status: `revise`
- Why: the historical argument is real, but it is oversized for round 1 and ends in a dense citation tail
- Grounding:
  - opening is strong and aligned: missionizing, court institutions, and hidden patronage
  - ending is not chapter-comparison-friendly: the tail collapses into citation blocks like `[95]…[97]`
- Recommendation:
  - keep as a valuable source
  - do not promote as a full chapter until it is recut or note-trimmed

`fooled_by_randomness_private_zh__19`
- Status: `revise`
- Review-first item: still not clean enough
- Why: this override successfully avoided front matter, but the selected artifact is a part-level unit with a duplicated opening paragraph
- Grounding:
  - chapter heading is “第三篇 活在随机世界中”
  - the same opening sentence appears twice in a row
  - the close is coherent, but the start is not clean enough yet
- Recommendation:
  - keep only after boundary cleanup or a tighter child-chapter replacement

`meiguoren_de_xingge_private_zh__8`
- Status: `revise`
- Why: the core argument does fit the intended role, but the artifact opens under the previous chapter heading and therefore fails boundary cleanliness
- Grounding:
  - selected title is `4 不令人服输的成功`
  - actual chapter heading at the artifact start is `3 有条件的父母之爱`
  - the tail does reach the expected competition / conditional-love argument, so this looks like recut territory rather than total rejection
- Recommendation:
  - do not promote as-is
  - recut from the same source if possible

### Defer / Replace

`kangxi_hongpiao_private_zh__27`
- Status: `defer`
- Review-first item: failed size safety for round 1
- Why: this is a real history argument, but `924` sentences plus a citation-heavy tail make it too traversal-heavy for the first chapter-comparison lift
- Grounding:
  - the opening on Ao Bai / Kangxi / Jesuit political role is strong
  - the tail degenerates into citations `[98]…[101]`
- Recommendation:
  - keep for excerpt or later split use
  - replace or split before round-1 chapter comparison

`zhangzhongmou_zizhuan_private_zh__10`
- Status: `defer`
- Review-first item: failed chapter alignment
- Why: this is not a chapter-clean artifact; it collapses back into one appendix container with no finer recorded boundary
- Grounding:
  - `href` is `text00001.html`
  - chapter heading is only `附录`
  - the tail contains appendix contents / chronology material like `张忠谋大事年表`
- Recommendation:
  - do not use in round 1
  - replace or reparse

`zhangzhongmou_zizhuan_private_zh__11`
- Status: `defer`
- Review-first item: failed chapter alignment and distinctness
- Why: same appendix-container problem as `__10`, and not a distinct clean chapter artifact at the chapter-lane level
- Grounding:
  - same `href`
  - same `附录` container
  - same appendix-style tail
- Recommendation:
  - do not use in round 1
  - replace or reparse

## Promotion Recommendation

Promote next:
- English:
  - `good_strategy_bad_strategy_private_en__22`
  - `good_strategy_bad_strategy_private_en__55`
  - `evicted_private_en__10`
  - `fooled_by_randomness_private_en__14`
  - `supremacy_private_en__13`
  - `supremacy_private_en__23`
  - `steve_jobs_private_en__17`
  - `steve_jobs_private_en__24`
- Chinese:
  - `biji_de_fangfa_private_zh__13`
  - `zouchu_weiyi_zhenliguan_private_zh__14`

Wait for recut / replacement / reparse:
- `kangxi_hongpiao_private_zh__12`
- `kangxi_hongpiao_private_zh__27`
- `fooled_by_randomness_private_zh__19`
- `meiguoren_de_xingge_private_zh__8`
- `zhangzhongmou_zizhuan_private_zh__10`
- `zhangzhongmou_zizhuan_private_zh__11`

Bottom line:
- English chapter lift can continue as selected.
- Chinese chapter lift should not advance as a full `8`-chapter pack yet.
- The clearest immediate Chinese keeps are the two expository chapters.
- The two `张忠谋自传` candidates should be treated as chapter-lane drops for round 1 unless reparsed.

# Revision/Replacement Packet `attentional_v2_bilingual_hardening_round3_zh`

This packet was generated automatically from cases whose current `benchmark_status` requires another hardening round.

## Dataset
- dataset_id: `attentional_v2_excerpt_zh_curated_v2`
- family: `excerpt_cases`
- language_track: `zh`
- version: `2`
- targeted_statuses: `needs_revision|needs_replacement|needs_revision|needs_replacement`

## Review Actions
- `keep`
- `revise`
- `drop`
- `unclear`

## Confidence
- `high`
- `medium`
- `low`

## 1. `chenlun_public_zh__4__reconsolidation_later_reinterpretation__v2`

- benchmark_status: `needs_revision`
- review_status: `llm_reviewed`
- book: `沉淪`
- author: `郁達夫`
- chapter: `了他的哥哥到日本來留學。` (`4`)
- question_ids: `EQ-CM-004|EQ-AV2-006`
- phenomena: `reconsolidation_candidate|later_reinterpretation|durable_trace_candidate`
- selection_reason: Selected to test whether the mechanism captures the character's pattern of frequently changing schools and being criticized for inconsistency (無恆性), which establishes an educational instability narrative that could serve as a character foundation.
- judge_focus: Does the excerpt clearly establish the educational-instability pattern through specific behavioral evidence (frequent school changes, family criticism), rather than presenting vague biographical summary?
- latest_review_action: `revise`
- latest_problem_types: `weak_excerpt|ambiguous_focus|wrong_bucket`
- latest_revised_bucket: `educational_instability_pattern`
- latest_notes: The adversarial challenge is valid: this excerpt shows an early instability pattern but no actual 'later reinterpretation' of it—only continued instability. The 'reconsolidation_later_reinterpretation' bucket requires evidence of both the early pattern AND a later passage that reinterprets it. Without that second half, the bucket is premature. Either the excerpt needs to be expanded to include the reinterpretation passage, or relabeled to 'educational_instability_pattern' which this excerpt actually supports.

```text
Ｗ大學卒了業，回到北京，考了一個進士，分發在法部當差，不上兩年，武昌的
革命起來了。
那時候他已在縣立小學堂卒了業，正在那裡換來換去的換中學堂。
他家裡的人都怪他無恆性，說他的心思太活；然而依他自己講來，他以為他一個
人同別的學生不同，不能按部就班的同他們同在一處求學的。
```

## 2. `jinghua_yuan_25377_zh__34__callback_bridge__v2`

- benchmark_status: `needs_revision`
- review_status: `llm_reviewed`
- book: `鏡花緣`
- author: `李汝珍`
- chapter: `第三十四回 觀麗人女主定吉期 訪良友老翁得凶信` (`34`)
- question_ids: `EQ-CM-002|EQ-CM-004|EQ-AV2-004`
- phenomena: `bridge_potential|callback|cross_span_link`
- selection_reason: Selected to test whether the mechanism can keep a callback modest and text-grounded when two nearby narrative threads compete for attention.
- judge_focus: Does the mechanism identify the most defensible backward link here without collapsing the palace scene and the search thread into one blurry association?
- latest_review_action: `revise`
- latest_problem_types: `weak_excerpt|ambiguous_focus`
- latest_revised_bucket: ``
- latest_notes: The case tests a genuine phenomenon (callback via 唐敖's 機關) but the current excerpt design doesn't cleanly isolate it. The palace scene and search thread are parallel rather than hierarchically bridged, and the callback's referent isn't text-grounded within the visible excerpt—requiring external context to resolve. A tighter excerpt that foregrounds the bridge point would make this a stronger test case.

```text
眾宮人攙扶林之洋，顫顫巍巍，如鮮花一枝，走到國王面前，只得彎著腰兒，拉著袖兒，深深萬福叩拜。
各王妃也上前叩賀。
正要進宮，忽聽外面鬧鬧吵吵，喊聲不絕，國王嚇的驚疑不止。
原來這個喊聲卻是唐敖用的機關。
唐敖自從那日同多九公尋訪林之洋下落，訪來訪去，絕無消息。
```

## 3. `zhaohua_xishi_25271_zh__20__reconsolidation_later_reinterpretation__v2`

- benchmark_status: `needs_revision`
- review_status: `llm_reviewed`
- book: `朝花夕拾`
- author: `魯迅`
- chapter: `然而人們一見他，為什麼就都有些緊張，而且高興起來呢？` (`20`)
- question_ids: `EQ-CM-004|EQ-AV2-006`
- phenomena: `reconsolidation_candidate|later_reinterpretation|durable_trace_candidate`
- selection_reason: Selected to test whether the mechanism recognizes a sharply quotable social observation and surfaces it as a selective anchored reaction rather than generic commentary.
- judge_focus: Does the mechanism preserve the cynical force and bitter讽刺 of this life-trajectory observation as a worthwhile anchored thought, recognizing it as memorable social critique rather than generic commentary?
- latest_review_action: `revise`
- latest_problem_types: `wrong_bucket`
- latest_revised_bucket: `anchored_reaction_selectivity`
- latest_notes: The phenomena labels (reconsolidation_candidate, later_reinterpretation) are fundamentally misaligned - the excerpt presents a present-tense cynical observation about life's predetermined path, with no memory reconsolidation or retrospective reinterpretation. The anchored_reaction_selectivity bucket (as initially suggested in the review_history) correctly captures this as a sharp, quotable social observation requiring selective anchoring. The primary review's durable_trace_candidate is plausible but anchored_reaction is more directly testable for the mechanism focus described.

```text
少。
這些“下等人”，要他們發什麼“我們現在走的是一條狹窄險阻的小路，左面是一
個廣漠無際的泥潭，右面也是一片廣漠無際的浮砂，前面是遙遙茫茫蔭在薄霧的裏面的
目的地”那樣熱昏似的妙語，是辦不到的，可是在無意中，看得住這“蔭在薄霧的裏面
的目的地”的道路很明白：求婚，結婚，養孩子，死亡。
```

## 4. `chenlun_public_zh__7__reconsolidation_later_reinterpretation__v2`

- benchmark_status: `needs_replacement`
- review_status: `llm_reviewed`
- book: `沉淪`
- author: `郁達夫`
- chapter: `旅館裡住下了之後，他覺得前途好像有許多歡樂在那裡等他的樣子。` (`7`)
- question_ids: `EQ-CM-004|EQ-AV2-006`
- phenomena: `reconsolidation_candidate|later_reinterpretation|durable_trace_candidate`
- selection_reason: Selected to test whether this passage could later be carried forward or reconsolidated meaningfully.
- judge_focus: Does the mechanism preserve what would make this passage valuable to return to later?
- latest_review_action: `drop`
- latest_problem_types: `wrong_bucket|weak_excerpt|ambiguous_focus`
- latest_revised_bucket: ``
- latest_notes: The excerpt is straightforward atmospheric setting description—protagonist alone in a hotel observing dark scenery. It contains no clear memory reactivation, cognitive shift, or interpretive moment that would justify the reconsolidation/later_reinterpretation labels. The phenomena claims are unsupported by the text itself; this is descriptive narrative, not a mechanism demonstration.

```text
便是一條如發的大道，前後都是稻田，西面是一方池水，並且因為學校還沒有開
課，別的學生還沒有到來，這一間寬曠的旅館裡，只住了他一個客人。
白天倒還
可以支吾過去，一到了晚上，他開窗一望，四面都是沉沉的黑影，並且因Ｎ市的
附近是一大平原，所以望眼連天，四面並無遮障之處，遠遠裡有一點燈火，明滅
```

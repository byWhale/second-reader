# Revision/Replacement Packet `attentional_v2_private_library_cleanup_round3_zh_ready`

This packet was generated automatically from cases whose current `benchmark_status` requires another hardening round.

## Dataset
- dataset_id: `attentional_v2_private_library_excerpt_zh_v2`
- family: `excerpt_cases`
- language_track: `zh`
- version: `2`
- targeted_statuses: `needs_revision|needs_replacement`

## Review Actions
- `keep`
- `revise`
- `drop`
- `unclear`

## Confidence
- `high`
- `medium`
- `low`

## 1. `biji_de_fangfa_private_zh__13__seed_1`

- benchmark_status: `needs_revision`
- review_status: `llm_reviewed`
- book: `笔记的方法`
- author: `刘少楠, 刘白光`
- chapter: `# 三项原则，掌握获取信息的主动权` (`13`)
- question_ids: ``
- phenomena: ``
- selection_reason: Excerpt uses local optima/mountain climbing metaphors to advise readers to specialize in one or a few core areas rather than becoming experts in every field. This is classic self-improvement/productivity advice about learning strategy and information acquisition, well-suited for testing understanding of analogical reasoning in this domain. The original 'wrong_bucket' claim was incorrect - meta-strategies about information acquisition and focus ARE relevant to note-taking methodology (what to capture, how to specialize your knowledge system), and regardless, the excerpt clearly fits self-improvement bucket on its own merits.
- judge_focus: Evaluate understanding of analogical reasoning in self-improvement advice (local optima metaphor for specialization decisions)
- latest_review_action: `revise`
- latest_problem_types: `other`
- latest_revised_bucket: `self_improvement`
- latest_notes: The 'wrong_bucket' classification was mistaken - the excerpt clearly fits self-improvement/learning_strategy bucket and does not represent a bucket mismatch. The book title being about note-taking doesn't require every excerpt to cover note-taking mechanics; strategic advice about what/where to focus is relevant to knowledge management methodology. Only the selection_reason text needs correction. Recommend keeping with corrected reasoning.

```text
关于这一点，Light 做过一个有趣的比喻：局部最优的叠加，总是导不向全局最优。
这就像爬山，你要登上最高峰，最好的办法肯定不是把每座小山坡都登一遍，而是先找到最高的山，再去攀登。
获取信息也一样。
你不必在每个领域都成为专家，更不要做皓首穷经的学究，选择一个或几个核心领域精进就好。
这不是一种无奈的妥协，而是一种主动的选择，让自己专注于最值得精进的核心领域。
```

## 2. `kangxi_hongpiao_private_zh__12__seed_1`

- benchmark_status: `needs_revision`
- review_status: `llm_reviewed`
- book: `康熙的红票：全球化中的清朝`
- author: `孙立天`
- chapter: `消除奴籍` (`12`)
- question_ids: ``
- phenomena: ``
- selection_reason: The content is a straightforward linguistic and historical explanation of the term '包衣' - essentially a reference definition with some context. The 'argumentative' role label appears mismatched; this reads more as reference_heavy factual content than argumentative material. Additionally, the excerpt is relatively simple, testing basic historical vocabulary comprehension rather than complex analysis.
- judge_focus: Whether the examinee can correctly understand the definition and basic historical evolution of the Manchu term '包衣' as background context for analyzing why certain figures rose to prominence
- latest_review_action: `revise`
- latest_problem_types: `wrong_bucket|too_easy`
- latest_revised_bucket: `reference_heavy`
- latest_notes: Change role_tag from 'argumentative' to 'reference_heavy'. The excerpt is too straightforward for meaningful complexity testing but works as factual reference material. Consider whether this should be paired with a more complex test item (as suggested in adversarial review) rather than used as standalone passage.

```text
“包衣”是满语的音译。
据清史前辈孟森解释：“包”是满语“家”的意思，而“衣”相当于汉语中的虚字，类似于“之”字。
包衣奴才就是指跟主子关系最近的、家周围的奴才。
[26]满人入关以后，包衣奴才专指满人权贵家里面的奴才，是整个奴才群体中地位最高的一群。
后来许多清朝名人都是包衣奴才出身。
```

## 3. `zhangzhongmou_zizhuan_private_zh__10__seed_1`

- benchmark_status: `needs_revision`
- review_status: `llm_reviewed`
- book: `张忠谋自传(1931-1964)`
- author: `张忠谋`
- chapter: `伊莉莎伯` (`10`)
- question_ids: ``
- phenomena: ``
- selection_reason: Reflective narrative depicting romantic disappointment and regret over a past mistake; the emotional arc centers on coping with heartbreak and interpreting a cautionary note from a former romantic interest.
- judge_focus: Evaluate whether the model correctly identifies the emotional tone (regret, lingering pain, attempted rationalization) and understands the contextual ambiguity of the warning message.
- latest_review_action: `revise`
- latest_problem_types: `other`
- latest_revised_bucket: `emotional_hurt_or_regret`
- latest_notes: The excerpt itself is coherent and depicts a clear emotional scenario, but critical benchmark metadata (question_ids, phenomena, selection_reason, judge_focus) is entirely missing. This case cannot function as a benchmark without defined evaluation criteria. The content supports a bucket of emotional_hurt_or_regret based on the romantic disappointment context, but the reference to '伊莉莎伯' remains unexplained which creates some focus ambiguity. Recommend metadata population and clarification of the Elizabeth reference before reconsideration.

```text
心头的创痕已是深钜,再也没有什么法子可以弥补的了。
临去,他从剑桥邮政局寄了一张便条给我,上面只有寥寥的几句话：
“举足偶误,竟铸终生之恨,今者一念既寒,万缘俱寂,愿杜门简出,深思谢过而已。
覆辙之鉴,足下戒之,戒之!”
我倒没很注意他的“戒之戒之”,只觉得他太悲凉了些,然而转念一想,这也未始不是好兆头。
```

## 4. `zhangzhongmou_zizhuan_private_zh__4__seed_2`

- benchmark_status: `needs_revision`
- review_status: `llm_reviewed`
- book: `张忠谋自传(1931-1964)`
- author: `张忠谋`
- chapter: `第一章 “大时代”中的幼少年` (`4`)
- question_ids: ``
- phenomena: ``
- selection_reason: 
- judge_focus: 
- latest_review_action: `revise`
- latest_problem_types: `ambiguous_focus|weak_excerpt`
- latest_revised_bucket: ``
- latest_notes: Critical metadata fields (case_title, question_ids, phenomena, selection_reason, judge_focus) are empty. The excerpt discusses 1950s US economy, civil rights timeline, highway construction, and personal travel without a clear thematic focus. Cannot function as a benchmark case until proper pedagogical framing and metadata are added.

```text
内政方面，经济快速增长，物价平稳，失业率低，人民的收人逐年增加。
很少人怀疑“这一代比上一代过得好，下一代会更好”。
黑人民权问题还在酝酿阶段，要10年后才爆发。
1958年是艾森豪威尔总统连任后的第二年，他最大政绩之一是建筑美囯跨州公路，今日这些跨州公路早已四通八达。
但在我们去达拉斯时，有许多尚未完成。
```

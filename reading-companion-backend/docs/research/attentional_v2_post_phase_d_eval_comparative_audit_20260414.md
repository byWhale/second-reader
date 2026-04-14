# Post-Phase-D 评测对照审计报告

- 生成日期: `2026-04-14`
- 对照 run: `attentional_v2_excerpt_surface_v1_1_judged_20260406` vs `attentional_v2_post_phase_d_excerpt_regression_20260413`；`attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407` vs `attentional_v2_post_phase_d_longspan_judged_20260413`
- 比较机制: `attentional_v2` 与 `iterator_v1`

## 1. 比较对象与证据边界
这份报告做的是同一批正式可用 case / probe 的跨 run 审计，不是再写一版单 run 结果摘要。比较范围固定为：
- `excerpt`: 同一批 `59` 个 frozen case，比较 `2026-04-06` 的正式 excerpt run 与 `2026-04-13` 的 post-Phase-D excerpt regression。
- `long-span`: 同一批 `7` 个 frozen probe，比较 `2026-04-07` 的 cleaned long-span 正式 rerun 与 `2026-04-13` 的 post-Phase-D long-span judged validation。
- `iterator_v1` 不重跑，统一复用同 case / probe 的正式 baseline bundle。
- 不纳入无效 harness lane，也不把 excerpt micro-slice repair lane 混进主结论。

这意味着这里的所有比较都满足 apples-to-apples：case / probe 身份、judge target、formal 原文都不变，变的是 `attentional_v2` 的实现与其产生的证据。

## 2. 评分方法说明
- `selective_legibility`: 看机制是否在局部文本上留下可读、可解释、可回看的阅读动作。
- `coherent_accumulation`: 看机制是否把 earlier / mid / late 的同一条线真正积累起来，而不是把后文读成孤立条目。
- `insight_and_clarification`: 看阅读结果是否在 formal target 上提供了真正的澄清价值，而不是只做泛泛总结。
- 每个 case / probe 的 `winner`、rubric 分数和 `reason` 都来自对应 payload 中的 `target_results.judgment`。本报告的解释不从 aggregate 倒推，而是逐条回到 payload。

## 3. 顶层结果对照
### 3.1 Excerpt 总盘
| target | 2026-04-06 winner_counts | 2026-04-13 winner_counts | 2026-04-06 average_scores | 2026-04-13 average_scores |
| --- | --- | --- | --- | --- |
| selective_legibility | {'attentional_v2': 27, 'iterator_v1': 21, 'tie': 11} | {'attentional_v2': 24, 'tie': 11, 'iterator_v1': 24} | {'attentional_v2': 1.98, 'iterator_v1': 1.427} | {'attentional_v2': 1.525, 'iterator_v1': 1.475} |
| insight_and_clarification | {'tie': 8, 'iterator_v1': 16, 'attentional_v2': 19} | {'tie': 7, 'attentional_v2': 15, 'iterator_v1': 21} | {'attentional_v2': 2.2, 'iterator_v1': 1.688} | {'attentional_v2': 1.684, 'iterator_v1': 1.758} |

### 3.2 Long-span 总盘
| target | 2026-04-07 winner_counts | 2026-04-13 winner_counts | 2026-04-07 average_scores | 2026-04-13 average_scores |
| --- | --- | --- | --- | --- |
| coherent_accumulation | {'iterator_v1': 5, 'attentional_v2': 2} | {'iterator_v1': 4, 'attentional_v2': 3} | {'attentional_v2': 2.457, 'iterator_v1': 3.486} | {'attentional_v2': 2.257, 'iterator_v1': 3.057} |
| insight_and_clarification | {'iterator_v1': 4, 'attentional_v2': 2, 'tie': 1} | {'iterator_v1': 5, 'tie': 1, 'attentional_v2': 1} | {'attentional_v2': 2.457, 'iterator_v1': 3.086} | {'attentional_v2': 1.971, 'iterator_v1': 3.114} |

目前最关键的两条异常是：
- 长距离并没有整体超过 `iterator_v1`，而且出现了非常强的语言分裂：英文 `3/3` 赢下 `coherent_accumulation`，中文 `0/4`。
- excerpt 层面旧 V2 的优势明显回落：`selective_legibility` 从 `27:21:11` 变成 `24:24:11`，`insight_and_clarification` 从 `19:16:8` 变成 `15:21:7`。

## 4. 根因导向总览
### 4.1 已确认的硬信号：V2 的 matched reaction 量级显著塌缩
| surface | run | avg matched reactions | median matched reactions | exact-hit total / avg anchor-hit | avg reaction match score |
| --- | --- | --- | --- | --- | --- |
| excerpt | 2026-04-06 formal V2 | 7.0 | 5 | 15 | 2.17 |
| excerpt | 2026-04-13 post-Phase-D V2 | 1.0 | 1 | 2 | 2.22 |
| long-span | 2026-04-07 formal V2 | 19.71 | 16 | 2.14 | 2.86 |
| long-span | 2026-04-13 post-Phase-D V2 | 2.29 | 3 | 2.43 | 2.5 |

这里最重要的不是“分数变了”，而是 `attentional_v2` 自己的可见证据密度变了：
- `excerpt` 平均 matched reaction 从 `7.0 -> 1.0`。
- `long-span` 平均 matched reaction 从 `19.71 -> 2.29`。
- 因此这次结果不能只读 winner counts；必须把 winner 变化和“现在 V2 只留下了多少条、命中方式是什么”一起读。

### 4.2 Long-span：为什么英文有提升、中文没有
当前 `7` 个 probe 中，winner 真正发生变化的只有少数几项，但这些变化已经足够说明问题：
| probe_id | target | old winner | new winner | old V2 score sum | new V2 score sum |
| --- | --- | --- | --- | --- | --- |
| steve_jobs_private_en__17__probe_1 | insight_and_clarification | attentional_v2 | iterator_v1 | 20 | 6 |
| supremacy_private_en__13__probe_1 | insight_and_clarification | attentional_v2 | tie | 24 | 5 |
| value_of_others_private_en__8_10__probe_1 | coherent_accumulation | iterator_v1 | attentional_v2 | 9 | 21 |
| value_of_others_private_en__8_10__probe_1 | insight_and_clarification | iterator_v1 | attentional_v2 | 10 | 19 |
| xidaduo_private_zh__13_15__probe_1 | insight_and_clarification | tie | iterator_v1 | 8 | 5 |

从逐 probe 审计看，长-span 不是“全面变强”，而是发生了选择性变化：
- `value_of_others_private_en__8_10__probe_1` 是最明确的改善点：`coherent_accumulation` 与 `insight_and_clarification` 都从旧 run 的 `iterator_v1` 胜，变成当前 V2 胜。
- `steve_jobs_private_en__17__probe_1` 则出现反向变化：旧 run 里 `insight_and_clarification` 是 V2 胜，当前变成 `iterator_v1` 胜。
- `supremacy_private_en__13__probe_1` 旧 run 的 `insight_and_clarification` 是 V2 胜，当前掉成 `tie`；而它的 `coherent_accumulation` 虽然 winner 仍是 V2，但 V2 自身分数从 `24 -> 5`，是一次很明显的证据收缩。
- 中文 4 个 probe 在 `coherent_accumulation` 上全部仍由 `iterator_v1` 胜；这不是 judge 换口径造成的，而是从 payload 可以直接看到，当前 V2 往往只剩 `2-3` 条 retrospective，且很多是 chapter-only supporting evidence。

更具体地说：
- 英文窗口当前更像“少量高价值反应还留住了主线”。例如 `value_of_others`，V2 反应数量大幅下降，但仍留下了足以支撑 judge 的关键桥接。
- 中文窗口当前更像“formal probe 所需的 carryover closure 不够了”。例如 `huochu` 虽然 anchor-hit 从 `0/1` 提到了 `3`，但 judge 仍更偏向 V1，因为 V1 把 13→15→16 的 arc 讲成了明确回答，而当前 V2 更像若干分离的好反应。
- 因此“英文全胜 / 中文全输”目前最可疑的不是单一语言能力差异，而是：中文 probe 更依赖明确 closure、callback precision、责任链条说清楚；而当前 V2 证据密度塌缩后，更容易退化成 supporting-only 的章节感受。

### 4.3 Excerpt：为什么旧 V2 的优势掉了
Excerpt 上的变化不是个别 case 抖动，而是大量 winner flip 叠加。
| case_id | target | old winner | new winner | old V2 score sum | new V2 score sum |
| --- | --- | --- | --- | --- | --- |
| huochu_shengming_de_yiyi_private_zh__8__distinction_definition__seed_1 | selective_legibility | attentional_v2 | tie | 5 | 8 |
| huochu_shengming_de_yiyi_private_zh__8__distinction_definition__seed_2 | insight_and_clarification | tie | attentional_v2 | 0 | 10 |
| huochu_shengming_de_yiyi_private_zh__8__tension_reversal__seed_1 | selective_legibility | tie | attentional_v2 | 5 | 10 |
| huochu_shengming_de_yiyi_private_zh__8__tension_reversal__seed_2 | insight_and_clarification | attentional_v2 | tie | 12 | 5 |
| huochu_shengming_de_yiyi_private_zh__8__tension_reversal__seed_3 | selective_legibility | tie | attentional_v2 | 0 | 5 |
| meiguoren_de_xingge_private_zh__19__tension_reversal__seed_10 | selective_legibility | tie | attentional_v2 | 8 | 20 |
| meiguoren_de_xingge_private_zh__19__tension_reversal__seed_5 | insight_and_clarification | tie | iterator_v1 | 8 | 8 |
| meiguoren_de_xingge_private_zh__19__tension_reversal__seed_8 | selective_legibility | iterator_v1 | attentional_v2 | 6 | 10 |
| nawaer_baodian_private_zh__13__anchored_reaction_selectivity__seed_2 | selective_legibility | attentional_v2 | tie | 10 | 6 |
| nawaer_baodian_private_zh__13__tension_reversal__seed_3 | selective_legibility | tie | iterator_v1 | 5 | 1 |
| nawaer_baodian_private_zh__22__callback_bridge__seed_1 | insight_and_clarification | tie | iterator_v1 | 8 | 7 |
| nawaer_baodian_private_zh__22__tension_reversal__seed_1 | insight_and_clarification | attentional_v2 | tie | 23 | 6 |
| nawaer_baodian_private_zh__22__tension_reversal__seed_2 | selective_legibility | attentional_v2 | iterator_v1 | 22 | 5 |
| nawaer_baodian_private_zh__22__tension_reversal__seed_2 | insight_and_clarification | attentional_v2 | iterator_v1 | 19 | 7 |
| nawaer_baodian_private_zh__22__tension_reversal__seed_3 | selective_legibility | attentional_v2 | tie | 11 | 7 |
| supremacy_private_en__13__anchored_reaction_selectivity__seed_4 | selective_legibility | attentional_v2 | tie | 21 | 5 |
| supremacy_private_en__13__callback_bridge__seed_1 | selective_legibility | tie | iterator_v1 | 0 | 8 |
| supremacy_private_en__13__callback_bridge__seed_1 | insight_and_clarification | iterator_v1 | tie | 5 | 5 |
| supremacy_private_en__13__callback_bridge__seed_2 | selective_legibility | tie | attentional_v2 | 5 | 5 |
| supremacy_private_en__13__callback_bridge__seed_2 | insight_and_clarification | tie | iterator_v1 | 0 | 0 |
| supremacy_private_en__13__callback_bridge__seed_4 | insight_and_clarification | tie | iterator_v1 | 0 | 5 |
| supremacy_private_en__13__callback_bridge__seed_5 | insight_and_clarification | iterator_v1 | tie | 8 | 5 |
| supremacy_private_en__13__tension_reversal__seed_2 | selective_legibility | iterator_v1 | attentional_v2 | 8 | 8 |
| supremacy_private_en__13__tension_reversal__seed_2 | insight_and_clarification | tie | attentional_v2 | 18 | 9 |
| value_of_others_private_en__8__anchored_reaction_selectivity__seed_1 | selective_legibility | tie | iterator_v1 | 5 | 5 |

完整 flip 清单见附录；这里只先点三个已经足够稳定的结构性现象：
- `value_of_others_private_en__8` 这一章是回落最严重的典型。多个 case 的 V2 matched reaction 都从 `20 -> 1`，例如 `distinction_definition__seed_1/2/3`、`anchored_reaction_selectivity__seed_1/3/5`、`tension_reversal__seed_1/2`。
- `huochu_shengming_de_yiyi_private_zh__8` 也有类似塌缩，多数 case 从 `11 -> 1`。这说明不是某一两个 case 的偶然问题，而是当前 V2 在整章可见反应密度上整体收紧了。
- 旧 V2 很多时候是“多条同章反应共同支撑一个 case”；当前 V2 则经常只剩 1 条 retrospective。judge 于是更容易把它看成 broad chapter comment，而不是对 formal excerpt 的选择性阅读。

这也解释了为什么 excerpt 的 aggregate 看起来不像“完全崩了”：
- 有些 case 里，哪怕只剩 1 条反应，仍然可能足够赢下 judge。
- 但一旦 case 需要 distinction precision、local reversal、或者 callback bridge，多条 supporting reaction 被压缩成单条 broad retrospective 后，V2 的优势就会明显回落。

### 4.4 这更像“读少了 / 读偏了 / judge 变严了”中的哪一种？
当前证据更支持“首先是读少了，其次是读偏了”，暂时不支持“主要是 judge 变严了”。
- 读少了：这是最硬的信号，matched reaction count 的全面下降已经足够说明。
- 读偏了：在 reaction 数量变少后，留下来的单条 reaction 更容易是 chapter-level supporting evidence，而不是 formal excerpt / probe hit。
- judge 变严了：目前没有证据表明 `2026-04-13` 的 judge 口径单独收紧到足以解释整体变化；相反，同一套 frozen case / probe 上，winner flip 往往能在 payload 里找到具体的证据收缩或命中方式变化。

## 5. 需要继续补充的观察维度
- 单位级 `matched_reaction_count`、`exact-hit`、`average match score` 应持续作为 post-Phase-D 之后的基本诊断指标。
- 每个 case / probe 都要继续严格区分 `formal hit` 与 `supporting evidence`，因为当前 V2 最常见的问题不是“完全没读到”，而是“只剩 supporting-only”。
- 需要专门追踪 judge 对“same chapter but wrong formal anchor”的容忍度，避免把章节感受误写成 probe fit。
- 中文 case 需要单独观察 exact closure / callback precision 的依赖程度，因为当前语言分裂很可能主要出在这里。

## 6. 附录索引
- [Long-span 完整附录](./attentional_v2_post_phase_d_eval_comparative_audit_20260414_longspan_appendix.md)
- [Excerpt 完整附录](./attentional_v2_post_phase_d_eval_comparative_audit_20260414_excerpt_appendix.md)
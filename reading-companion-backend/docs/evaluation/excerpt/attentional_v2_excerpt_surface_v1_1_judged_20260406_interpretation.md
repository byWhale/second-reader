# Excerpt Surface v1.1 正式 Judged Eval 解读报告

- Run ID: `attentional_v2_excerpt_surface_v1_1_judged_20260406`
- Surface: `excerpt surface v1.1`
- Compared mechanisms: `attentional_v2` vs `iterator_v1`
- Machine outputs:
  - [aggregate.json](../../../eval/runs/attentional_v2/attentional_v2_excerpt_surface_v1_1_judged_20260406/summary/aggregate.json)
  - [report.md](../../../eval/runs/attentional_v2/attentional_v2_excerpt_surface_v1_1_judged_20260406/summary/report.md)
  - [llm_usage.json](../../../eval/runs/attentional_v2/attentional_v2_excerpt_surface_v1_1_judged_20260406/summary/llm_usage.json)

## 1. 范围与置信度

这份报告只解读 `excerpt surface v1.1` 的正式 judged eval，不包含仍在运行的 long-span judged lane。因此，它回答的是“在 excerpt 这个语义面上，两套机制谁更强、强弱点分别在哪里”，不是整个 split-surface Phase 9 的最终结论。

这次 run 是第一轮真正完整跑通的 excerpt-level formal judged eval。它和此前几轮最关键的区别是：
- `59` 个 `selective_legibility` case 全部完成。
- `43` 个 `insight_and_clarification` case 全部完成。
- `judge_unavailable = 0`。
- `mechanism_failure_count = 0`。

本次 surface 固定为 `7` 个 chapter-scoped unit，覆盖 `2` 个英文章节和 `5` 个中文章节：

| Unit | 书 / 章 | 语言 | 来源 | Primary cases | Insight cases |
| --- | --- | --- | --- | --- | --- |
| `supremacy_private_en__chapter_13` | Supremacy / Chapter 7. Playing Games | `en` | `imported_clustered` | `12` | `8` |
| `value_of_others_private_en__chapter_8` | The Value of Others / Chapter 2 | `en` | `notes_guided_kept` | `8` | `5` |
| `huochu_shengming_de_yiyi_private_zh__chapter_8` | 活出生命的意义 / 第一部分　在集中营的经历 | `zh` | `notes_guided_kept` | `8` | `7` |
| `meiguoren_de_xingge_private_zh__chapter_19` | 美国人的性格 / 5 幸福单车的脱节 | `zh` | `imported_clustered` | `12` | `12` |
| `nawaer_baodian_private_zh__chapter_13` | 纳瓦尔宝典 / 认识财富创造的原理 | `zh` | `notes_guided_kept` | `6` | `3` |
| `nawaer_baodian_private_zh__chapter_22` | 纳瓦尔宝典 / 如何获得运气 | `zh` | `notes_guided_kept` | `5` | `5` |
| `xidaduo_private_zh__chapter_15` | 悉达多 / 乔文达 | `zh` | `notes_guided_kept` | `8` | `3` |

这里还要明确一个解释边界：benchmark anchor 是评测参考，不是阅读质量的唯一真理。一个机制如果偏离了指定锚点，我们仍然需要区分两种情况：
- 它是真的读偏了，跑到了不该读的别处。
- 它没有压中指定锚点，但仍然抓住了同段或同章真实存在的压力。

后文会把这两种情况分开说，不把“没压中 anchor”简单等同于“完全没读到东西”。

## 2. 顶层结果

顶层结论很直接：`attentional_v2` 赢下了这次 excerpt surface v1.1 的两项主指标，而且这是第一轮可以真正当作 formal excerpt evidence 来看的完整 judged run。

| Target | Case count | Winner counts | Average scores |
| --- | --- | --- | --- |
| `selective_legibility` | `59` | `attentional_v2 = 27`, `iterator_v1 = 21`, `tie = 11` | `attentional_v2 = 1.98`, `iterator_v1 = 1.427` |
| `insight_and_clarification` | `43` | `attentional_v2 = 19`, `iterator_v1 = 16`, `tie = 8` | `attentional_v2 = 2.2`, `iterator_v1 = 1.688` |

如果只看总盘，这次可以先记住三句话：
- `attentional_v2` 不是靠“少数漂亮样例”侥幸获胜，而是在两个 target 上都拿到了总盘领先。
- 这次领先不是绝对碾压，`iterator_v1` 仍然拿下了不少 chapter-local 精准命中 case。
- 这次结果最值得重视的地方，不只是“V2 赢了”，而是它在 throughput repair 之后仍然能赢，这说明前面的降调用修补并没有把 excerpt 质量直接修没。

## 3. 公平性与偏置检查

### 3.1 来源层

这次 surface 不是纯 notes-guided，也不是纯 imported clustered，而是两类来源混合：
- `notes_guided_kept`：`5` 章
- `imported_clustered`：`2` 章

按来源拆开后，结果并不支持“数据集故意偏袒 attentional_v2”的说法：

| Target | 来源 | `attentional_v2` | `iterator_v1` | `tie` |
| --- | --- | --- | --- | --- |
| `selective_legibility` | `notes_guided_kept` | `18` | `11` | `6` |
| `selective_legibility` | `imported_clustered` | `9` | `10` | `5` |
| `insight_and_clarification` | `notes_guided_kept` | `13` | `7` | `3` |
| `insight_and_clarification` | `imported_clustered` | `6` | `9` | `5` |

这组数的意义很重要：
- 如果数据面在“主观上偏袒 attentional_v2”，通常 imported clustered 这种外来章节也会一起偏向它。
- 但这里恰好相反，`imported_clustered` 在两个 target 上都没有明显偏向 `attentional_v2`，甚至更接近 `iterator_v1`。
- 所以这次总盘不是“因为我们把 surface 构造成了只会奖励 V2 的题”，而更像是：V2 在 notes-guided kept chapters 上确实抓住了更多我们关心的章节局部压力。

### 3.2 语言层

按语言看，也不是单靠某一门语言拉分：

| Target | 语言 | Winner counts | Average scores |
| --- | --- | --- | --- |
| `selective_legibility` | `en` | `attentional_v2 = 10`, `iterator_v1 = 4`, `tie = 6` | `1.9` vs `1.35` |
| `selective_legibility` | `zh` | `attentional_v2 = 17`, `iterator_v1 = 17`, `tie = 5` | `2.021` vs `1.467` |
| `insight_and_clarification` | `en` | `attentional_v2 = 5`, `iterator_v1 = 4`, `tie = 4` | `1.985` vs `1.692` |
| `insight_and_clarification` | `zh` | `attentional_v2 = 14`, `iterator_v1 = 12`, `tie = 4` | `2.293` vs `1.687` |

这里最有意思的是中文 `selective_legibility`：
- 胜负个数上两边打成 `17 : 17`。
- 但平均分仍然是 `attentional_v2` 更高。

这说明 V2 的优势并不只是“赢得更多”，还包括“赢的时候往往更像一个完整的读法”，而不是险胜。

### 3.3 当前 surface 更偏向什么压力

这次 surface 也不是完全均衡的。它更容易放大这些能力：
- chapter-local pressure tracking
- anchored reaction 的可见度
- tension reversal 的读法质量

按 target profile 拆开看，最能区分两套机制的是：

| Target | Profile | `attentional_v2` | `iterator_v1` | `tie` | 解释 |
| --- | --- | --- | --- | --- | --- |
| `selective_legibility` | `anchored_reaction_selectivity` | `9` | `5` | `2` | V2 更常把“为什么这一句值得读”说出来 |
| `selective_legibility` | `tension_reversal` | `12` | `11` | `4` | 两边接近，但 V2 更稳 |
| `insight_and_clarification` | `tension_reversal` | `15` | `9` | `3` | 这是 V2 最明显的优势桶 |
| `insight_and_clarification` | `distinction_definition` | `3` | `5` | `2` | V1 在一些窄而准的定义/转折上仍更利落 |
| `insight_and_clarification` | `callback_bridge` | `1` | `2` | `3` | 两边都不够强，V2 也没有占优 |

所以更准确的说法不是“数据集偏袒 V2”，而是：
- 这次 excerpt surface 更偏向测试章节局部压力、张力翻转、反应可见度。
- 在这些压力下，V2 的长项确实比 V1 更突出。
- 但 callback bridge 和窄 local anchor closure 仍然更像 V1 的保留地，或者至少不是 V2 的强项。

## 4. 按章节 / case family 拆解

### 4.1 按章节

| Chapter | `selective_legibility` | `insight_and_clarification` | 解读 |
| --- | --- | --- | --- |
| `huochu_shengming_de_yiyi_private_zh__8` | `attentional_v2 5`, `tie 3` | `attentional_v2 5`, `tie 2` | V2 在“章节整体压力抓取”上最有代表性的胜场 |
| `nawaer_baodian_private_zh__22` | `attentional_v2 4`, `iterator_v1 1` | `attentional_v2 4`, `tie 1` | V2 在这章的局部推进明显更稳，但 callback bridge 仍未真正拉开 |
| `supremacy_private_en__13` | `attentional_v2 6`, `iterator_v1 2`, `tie 4` | `attentional_v2 2`, `iterator_v1 2`, `tie 4` | V2 在 selective 上更强，但 insight 面没有形成压倒性优势 |
| `value_of_others_private_en__8` | `attentional_v2 4`, `iterator_v1 2`, `tie 2` | `attentional_v2 3`, `iterator_v1 2` | V2 有优势，但这章也暴露出 section mismatch 容易被 judge 容忍的问题 |
| `meiguoren_de_xingge_private_zh__19` | `iterator_v1 8`, `attentional_v2 3`, `tie 1` | `iterator_v1 7`, `attentional_v2 4`, `tie 1` | 这是 V1 最强的整章胜场，说明 V2 在 imported chapter 上仍会出现错误 section 绑定 |
| `xidaduo_private_zh__15` | `iterator_v1 5`, `attentional_v2 3` | `iterator_v1 2`, `attentional_v2 1` | 这是“V2 读到东西，但常常没压中指定 local anchor”的集中暴露点 |
| `nawaer_baodian_private_zh__13` | `iterator_v1 3`, `attentional_v2 2`, `tie 1` | `iterator_v1 3` | V1 在这章的局部闭合更窄更准 |

如果只看章节，最重要的观察是：
- `attentional_v2` 真正拉开差距的，不是“句句都更准”，而是它在 `活出生命的意义 8`、`纳瓦尔宝典 22` 这类章节里更能持续抓住同一条章节局部压力。
- `iterator_v1` 真正占优的，也不是“更懂整章”，而是它更容易在 `美国人的性格 19`、`悉达多 15` 这种窄 local reversal 上打出精准命中。

### 4.2 结合原文看几类最能区分两套机制的 pressure

第一类是 V2 擅长的“章节局部压力”型：

> “正常工人不是生活在屈从的精神压力下，也不是生活在不知家中亲人是送进了集中营还是毒气室的担忧中，更不是在时刻受到死亡威胁的情况下工作的。”

这里最关键的，不是某一个漂亮词，而是整段把“正常劳动”与“集中营劳动”拉开了三层定义差。V2 在这种 case 上经常能沿着整章的 existential pressure 往下读。

第二类是 V1 擅长的“窄 local reversal”型：

> “世尊的精辟法义则明了、简洁、易懂，不含任何古怪疯狂或荒谬的内容。  
> 但悉达多的手脚、他的双眼、额头，他的微笑、问候和姿态却不同于他的思想。  
> 自世尊佛陀步入涅槃，悉达多是唯一一位我见过的圣人……”

这里最关键的是一个很窄的反转: “教义看似疯狂” 与 “身体存在却显出神圣”。V1 更容易卡住这个点，V2 则更容易顺着同章别的哲学张力滑走。

第三类是目前两边都还没真正做好的 callback bridge：

> “前面举了潜水员的例子……  
> 再进一步，如果你值得信赖，做事靠谱，诚信正直，目光长远，那么其他人在跟陌生人合作时，保险起见，他们会选择通过你来达成交易。”

这类 case 不是只要讲“信誉很重要”就够，而是要真的回桥到前文那个指定例子。这里两边都还有欠账。

## 5. 代表性案例精读

### 5.1 `huochu_shengming_de_yiyi_private_zh__8__distinction_definition__seed_1`

> 但他们也明白，正常工人每天的饭量可不是近300克面包……  
> 正常工人不是生活在屈从的精神压力下，也不是生活在不知家中亲人是送进了集中营还是毒气室的担忧中，更不是在时刻受到死亡威胁的情况下工作的。  
> 我曾经对一位温良的工头说……

- 这个 case 在测什么:
  - 看机制能不能抓住“正常工人”和“集中营劳动者”之间那条定义线，而不是泛泛谈苦难。
- `attentional_v2` 实际读到什么:
  - 它没有直接打中锚点 `8.73`，而是读到了 `8.102`、`8.141`、`8.144`、`8.162` 等同章别处。
  - 这些反应围绕去人化、死亡压力、存在确认、极端处境中的选择自由，构成了一条很强的章节局部压力线。
- `iterator_v1` 实际读到什么:
  - 这一题里几乎没有留下可用的局部匹配，judge 看到的是 `zero matched reactions`。
- Judge 为什么这么判:
  - `selective_legibility` 上，judge 说两边都没真正把这条定义句读出来，但 V2 至少有持续的章节参与感，所以只给了一个边际胜。
  - `insight_and_clarification` 上，judge 认为 V2 虽未显式命名定义句，却明显更能照亮本章的核心存在压力。
- 这说明了什么机制差异:
  - 这是 V2 很典型的一类胜法: 不是 exact anchor hit，而是 chapter-local pressure tracking 足够强，强到即便 anchor 没命中，仍然能把 V1 甩开。
  - 同时这也是一个提醒: V2 的胜法还不够“干净”，因为它赢得并不靠精准定义闭合。

### 5.2 `value_of_others_private_en__8__tension_reversal__seed_1`

> Some destinations are difficult to reach on one’s own; others are unobtainable with the excess weight.  
> Ensuring that your destination is of the former type will not only provide a compelling enticement with which to attract passengers but will also supply the basis of frame management further out to sea.  
> I can’t overstate the practical significance of this first point.

- 这个 case 在测什么:
  - 看机制能不能抓住这里的张力翻转: 别人既可能是“帮你到达”的必要条件，也可能是“多余重量”。
- `attentional_v2` 实际读到什么:
  - 它也有 section mismatch，实际反应落在 `8.104`、`8.105`、`8.107`、`8.109` 等别处。
  - 但这些反应里，它很清楚地在抓修辞转折、逻辑对冲和“however / despite” 这种结构枢纽。
- `iterator_v1` 实际读到什么:
  - 它的反应主要落在 `8.1`、`8.10`，更容易把文本压成泛化的 relationship-advice 或外部搜索。
- Judge 为什么这么判:
  - judge 明说两边都有 section-reference mismatch。
  - 但它仍偏向 V2，因为 V2 至少读出了“这句为什么是张力枢纽”，而 V1 更像在借题发挥。
- 这说明了什么机制差异:
  - 这题是 V2 的另一个典型优势: 即便它没有压中精确 section，也更容易抓到“结构上的为什么是这里”。
  - 但这类胜法的含义必须谨慎解释，因为它依赖 judge 对“结构理解”比对“锚点命中”更宽容。

### 5.3 `xidaduo_private_zh__15__tension_reversal__seed_2`

> 我听便灵魂与肉体的安排，去经历罪孽，追逐肉欲和财富……以学会热爱世界。  
> 我不再将这个世界与我所期待的，塑造的圆满世界比照，而是接受这个世界，爱它，属于它。  
> ——哦，乔文达，这就是我的一些思考和感悟。

- 这个 case 在测什么:
  - 看机制能不能抓住“从比照理想世界，到接受现实世界”的局部反转。
- `attentional_v2` 实际读到什么:
  - 它的 case anchor 在 `15.21`，但实际匹配主要落在 `15.25`、`15.29`、`15.45`，也就是同一段对话里相邻或稍后的位置。
  - 这些反应围绕“乔文达追问确定性”“悉达多用悖论松动这种确定性依赖”展开，虽然不完全等于 anchor 句，但仍然在同一组真实压力里。
- `iterator_v1` 实际读到什么:
  - 这一题里它几乎没有可用匹配。
- Judge 为什么这么判:
  - judge 认为 V2 抓住了本章最重要的 tension: 从寻求确定真理转向接受世界本身。
  - 同时它也诚实指出，V2 读的是“本章的张力群”，不是只钻到这一句的字面对比。
- 这说明了什么机制差异:
  - 这是一个“偏离 anchor 但不算坏读”的边界案例。
  - 偏离发生在同章同段邻近位置，不是明显错章。
  - 所以这类 case 不该被粗暴计为“完全读错”，但也不能假装它已经完成了 exact anchor resolution。

### 5.4 `meiguoren_de_xingge_private_zh__19__tension_reversal__seed_5`

> 华侨的理想人物是陈嘉庚。  
> ——这是说，我们这片旧大陆尽管够荒瘠，够黑暗，但是还不失其温暖，还是个“家”。  
> 海外的华侨心心念念着祖国……

- 这个 case 在测什么:
  - 看机制能不能抓住“祖国既荒瘠/黑暗，又仍然温暖/是家”的情感反转。
- `attentional_v2` 实际读到什么:
  - 它的匹配主要跑到了 `19.3`、`19.4`、`19.16`，在读英国血统、美国化表演、丘吉尔那条张力链。
  - 这些内容不是胡说，但不是这道题的指定反转。
- `iterator_v1` 实际读到什么:
  - 它至少压在了正确 section 上，能读出“出外是手段，不是目的”这条结构线。
  - 它也没有完全吃透“荒瘠/黑暗 yet 温暖/家”这个情感逆转，但站位比 V2 正。
- Judge 为什么这么判:
  - `selective_legibility` 上给了 V1，因为它起码在对的地方读。
  - `insight_and_clarification` 最后给 `tie`，因为两边都没有真正把 anchor line 的情感反转解释透。
- 这说明了什么机制差异:
  - 这题说明 V2 现在最危险的失败模式不是“没想法”，而是“想法很完整，但落在了错误 section 上”。
  - 对 formal benchmark 来说，这种错位不能因为它读得漂亮就被原谅。

### 5.5 `xidaduo_private_zh__15__tension_reversal__seed_1`

> 世尊的精辟法义则明了、简洁、易懂，不含任何古怪疯狂或荒谬的内容。  
> 但悉达多的手脚、他的双眼、额头，他的微笑、问候和姿态却不同于他的思想。  
> 自世尊佛陀步入涅槃，悉达多是唯一一位我见过的圣人……

- 这个 case 在测什么:
  - 看机制能不能压住一个非常窄的局部反转: “思想显得疯狂” 与 “身体存在显得神圣”。
- `attentional_v2` 实际读到什么:
  - 指定 anchor 是 `15.34`。
  - 它实际命中的主要 section 是 `15.11`、`15.25`、`15.29`、`15.45`、`15.7`。
  - 最近的一次实质接近是 `15.29`，属于同章邻近偏离；`15.45` 则更像后面的总结性回望。
  - 也就是说，它不是跨章乱飞，但就是没有压住“怪异教义 vs 神圣身体”这一针眼。
- `iterator_v1` 实际读到什么:
  - 它直接锚在这段上，抓住了两个关键点：
  - 乔文达说“神圣”的对象其实是悉达多这个人，不是他的教义。
  - 乔文达真正被打动的是身体存在方式，而不是思想命题。
- Judge 为什么这么判:
  - judge 认为 V1 精准抓到了 case 的核心 reversal。
  - 同时明确指出 V2 虽然读到了同章真实问题，但不是这道题在测的那个问题。
- 这说明了什么机制差异:
  - 这是 V2 当前最该修的短板之一。
  - 它说明“同章相关”还不够，late-local philosophical reversal 需要更强的 anchor carrythrough。

### 5.6 `nawaer_baodian_private_zh__22__callback_bridge__seed_1`

> 我认为，赚钱很关键的一点就是知名度和信誉度……  
> 前面举了潜水员的例子……  
> 再进一步，如果你值得信赖，做事靠谱，诚信正直，目光长远，那么其他人在跟陌生人合作时……会选择通过你来达成交易。

- 这个 case 在测什么:
  - 看机制能不能把“后文的信任/信誉”明确回桥到“前文潜水员例子”的那一段。
- `attentional_v2` 实际读到什么:
  - 它只给了一个很泛的章节级判断，说本章最后回收到了“外部策略最终收敛为内部条件”。
  - 这不是错，但没有把 callback bridge 真的搭出来。
- `iterator_v1` 实际读到什么:
  - 它更清楚地抓到了“信誉/声誉是机制桥”这一点。
  - 但它又容易往外扩，把分析带到“第四种杠杆”“credible commitment”这些外部框架里。
- Judge 为什么这么判:
  - `selective_legibility` 上，judge 还是偏向 V1，因为它起码把桥认出来了。
  - `insight_and_clarification` 给 `tie`，因为两边都没有真的回到指定 earlier material 并把 attribution 收紧。
- 这说明了什么机制差异:
  - 这是最能说明 callback bridge 当前状态的一题：
  - V2 的问题是桥没搭出来。
  - V1 的问题是桥搭出来了，但容易越桥越远，开始外推。

## 6. 机制层因果分析与下一步

### 6.1 这次结果里最可信的机制结论

`attentional_v2` 的强项现在可以说得更具体一些：
- 它在 excerpt surface 上确实更擅长沿着同一章的局部压力持续推进，而不是只留下零散局部笔记。
- 这种优势在 `anchored_reaction_selectivity` 和大量 `tension_reversal` case 上最明显。
- 更关键的是，这个优势是在 throughput repair 之后仍然成立的，所以不是靠“多打很多电话”硬堆出来的。

`attentional_v2` 当前最明确的局部弱点也已经足够清楚：
- exact local anchor resolution 仍不稳定。
- 晚段、压缩、哲学性强的 local reversal 最容易被它读成“同章相关但不是这句”。
- callback bridge 目前也不够硬，经常只读出章节结构，而没有回到指定 earlier material。

`iterator_v1` 这次仍然保留了值得吸收的能力：
- 在窄 local anchor 上，它更容易把针扎到指定句子上。
- 在一些 embodied paradox、late-local reversal、backward bridge 小题上，它的命中更准。
- 但它也有老问题: 一旦打开外部搜索或关联推演，容易越读越远，牺牲 source-groundedness。

### 6.2 下一步动作

这次 excerpt formal eval 之后，最窄也最明确的后续项应该是：

1. 做一轮 `attentional_v2` 的 local anchor resolution 窄修补。
   - 重点不是再增加总 reaction 数，而是让 `zoom_now -> closure -> controller` 这一段更稳定地把注意力带到指定 anchor。
   - 最直接的 harness 就是 `xidaduo_private_zh__15` 这类 late-local case。

2. 把 late-local case 命中率单独当成一个小问题来打。
   - 这次最痛的不是“完全没读”，而是“读到了同章别处”。
   - 这说明下一轮更值得修的是 carrythrough，而不是重新扩大章节级 reaction density。

3. 继续推进 excerpt 数据集的 ROI 调整，但不要把它和这次 formal run 的机制结论混在一起。
   - `excerpt surface v1.1` 已经足够完成这一轮 formal 证明。
   - 更大的 excerpt surface retune 仍然值得做，但它解决的是“单位阅读产出更多有效 case”的问题，不是替代这次结果本身。

这份报告因此给项目留下的最重要结论不是一句“V2 赢了”，而是两句更可执行的话：
- `attentional_v2` 已经证明自己可以在 excerpt formal eval 上赢，而且不是靠旧的高调用姿势赢。
- 它现在最该修的，已经从“整体读不动”缩小成了“窄 local anchor 和 callback bridge 仍不够稳”。

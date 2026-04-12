# Long-Span 正式 Judged Eval 解释报告

- Run ID: `attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407`
- Surface: `bounded long-span accumulation comparison`
- Compared mechanisms: `attentional_v2` vs `iterator_v1`
- 机器摘要：
  - [aggregate.json](../../../eval/runs/attentional_v2/attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407/summary/aggregate.json)
  - [report.md](../../../eval/runs/attentional_v2/attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407/summary/report.md)
  - [case_results.jsonl](../../../eval/runs/attentional_v2/attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407/summary/case_results.jsonl)
- 关键反应附录：
  - [attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407_score_impact_reaction_appendix.md](./attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407_score_impact_reaction_appendix.md)

## 1. 文档定位

这份文档的目标不是重复机器输出，而是把这轮 long-span judged eval 写成一份人能直接读懂的解释报告。

它重点回答四个问题：

- 每道题到底在问什么。
- 这道题里两套机制分别留下了什么可审计证据。
- 为什么 judge 会把这一题判给其中一边。
- 这轮结果整体上说明了什么。

这份主报告只保留“最小充分证据链”。

- 如果你只想快速理解胜负，读这份主报告就够。
- 如果你要逐条核对关键 reaction，请看附录。
- 如果你要看完整 case payload 和本地 runtime 证据，请从附录里的 case payload 链接继续进入。

## 2. 这次报告的证据口径

为了避免前几版里反复出现的混写问题，这一版统一采用四层证据口径：

- `formal benchmark target`
  - 指这道 probe 在 `probes.jsonl` / case payload 里真正的 `EARLY / MID / LATE` 题面。
- `direct evidence`
  - 指真正附着在 formal target 上的 matched reaction 或明确 scored evidence。
- `supporting evidence`
  - 指同章、同节或邻近位置的证据，它能帮助解释判分，但不是 formal anchor 本句上的 clean direct hit。
- `negative evidence`
  - 指缺失本身，例如关键 `LATE` 锚点没有 matched reaction、没有 matched attention，或者机制明显跑离了本题主线。

因此：

- `anchor_hit = 3/3` 不自动等于三个正式锚点都有 clean direct hit。
- 有阅读价值，不自动等于对这道 probe 贴题。
- supporting evidence 可以影响判分，但必须按 supporting evidence 来写，不能伪装成 formal hit。

## 3. 总体结论

这轮 long-span judged eval 已经完成，而且结果可直接使用：

- `coherent_accumulation`
  - `iterator_v1 = 5` 胜
  - `attentional_v2 = 2` 胜
  - 平均分 `3.486 vs 2.457`
- `insight_and_clarification`
  - `iterator_v1 = 4` 胜
  - `attentional_v2 = 2` 胜
  - `tie = 1`
  - 平均分 `3.086 vs 2.457`
- `judge_unavailable_count = 0`
- `mechanism_failure_count = 0`

如果把这轮结果压缩成一句话，就是：

- `iterator_v1` 仍然更擅长 long-span 的 retrospective bridge 和窗口尾部闭合。
- `attentional_v2` 的真实优势更偏向主线约束、局部精度和少跑偏。

所以这轮结果支持的结论不是“V2 不可用”，而是：

- `attentional_v2` 更像一个更干净、更稳的阅读器。
- 但它目前还没有在 bounded long-span accumulation 上超过 `iterator_v1`。

## 4. 总览表

| Probe | 书 / window | 这题真正要看什么 | `coherent_accumulation` | `insight_and_clarification` |
| --- | --- | --- | --- | --- |
| `huochu...probe_1` | 《活出生命的意义》13-16 | 把“意义让人活下去”读到后面的“责任 / 三种发现意义的方式” | `iterator_v1` | `iterator_v1` |
| `huochu...probe_2` | 《活出生命的意义》13-16 | 把“张力 -> 虚无”带到“意义在世界中发现” | `iterator_v1` | `iterator_v1` |
| `steve_jobs...probe_1` | 《史蒂夫·乔布斯》17 | 把 GUI 突破、大众化愿景和 Lisa 团队冲突串起来 | `attentional_v2` | `attentional_v2` |
| `supremacy...probe_1` | `Supremacy` 13 | 沿着 DeepMind 自治权主线读到最后的治理妥协 | `attentional_v2` | `attentional_v2` |
| `value_of_others...probe_1` | 《The Value of Others》8-10 | 把 captain/passenger 框架带到谈判逻辑和市场原则 | `iterator_v1` | `iterator_v1` |
| `xidaduo...probe_1` | 《悉达多》13-15 | 把痛苦与伤口带到最后的接受世界 | `iterator_v1` | `tie` |
| `xidaduo...probe_2` | 《悉达多》13-15 | 把犯错、受苦和理解世人带到“学会爱世界” | `iterator_v1` | `iterator_v1` |

## 5. 逐题解读

### 5.1 《活出生命的意义》probe 1

- Probe ID: `huochu_shengming_de_yiyi_private_zh__13_16__probe_1`
- Case payload：
  - [huochu probe 1](../../../eval/runs/attentional_v2/attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407/shards/main/cases/huochu_shengming_de_yiyi_private_zh__13_16__probe_1.json)
- 这题真正要看什么：
  - 这题不是在问“有没有提到意义、责任、三种方式”。
  - 它真正要看的是：后面的“三种方式”有没有被读成对前面“为什么意义能让人活下去”的回答。
- 完整 probe 题面：
  - `EARLY (13)`：世界上再没有别的能比知道自己的生活有意义更能有效地帮助人活下去（哪怕是在最恶劣的环境下）。尼采的一句话很有智慧：“知道为什么而活的人，便能生存。”
  - `MID (15)`：简单地说，生命对每个人都提出了问题，他必须通过对自己生命的理解来回答生命的提问。对待生命，他只能担当起自己的责任。因此，意义疗法认为，负责任就是人类存在之本质。
  - `LATE (16)`：按照意义疗法，我们可以用三种不同的方式来发现生命之意义：(1)通过创立某项工作或从事某种事业；(2)通过体验某种事情或面对某个人；(3)在忍受不可避免的苦难时采取某种态度。
- 结果：
  - `coherent_accumulation = iterator_v1`
  - `insight_and_clarification = iterator_v1`
- 完整关键反应：
  - 见附录第 `1` 节。

`attentional_v2`

- 关键负证据非常直接：
  - `anchor_hit = 0/3`
  - `matched_reactions = 0`
- 这不是“读到了但解释得不够好”，而是 judge 几乎看不到它在这条线上形成可见的跨章阅读轨迹。

`iterator_v1`

- 它在 `EARLY / MID / LATE` 三个锚点都有可见反应。
- 最决定胜负的是 `LATE` 的 `retrospect` move：
  - 它明确把第三种方式读成对前文集中营问题的回答：即使事业未成、使命未竟，人仍然可以靠对苦难采取某种态度活下去。
- 它同时把 `MID` 的“责任”读成追问者与被追问者位置对调，因此整条线不是“意义清单”，而是“前面的问题 -> 中间的责任结构 -> 后面的回答框架”。

本题结论：

- 这是 `iterator_v1` 赢得最扎实的一题之一。
- `attentional_v2` 的问题不在局部句子理解，而在后文出现明确处方时，没有把前文问题重新抬回台面。

### 5.2 《活出生命的意义》probe 2

- Probe ID: `huochu_shengming_de_yiyi_private_zh__13_16__probe_2`
- Case payload：
  - [huochu probe 2](../../../eval/runs/attentional_v2/attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407/shards/main/cases/huochu_shengming_de_yiyi_private_zh__13_16__probe_2.json)
- 这题真正要看什么：
  - 它考的是一条更抽象的逻辑链：
  - “健康需要张力” -> “失去张力后会进入虚无和厌倦” -> “所以意义不能只在心里找，而要在世界中发现”。
- 完整 probe 题面：
  - `EARLY (13)`：因此，我们可以看到，精神健康有赖于一定程度的紧张——即已完成的和有待完成的任务之间的紧张，或者是当下状态与理想状态之间的差距。
  - `MID (14)`：存在之虚无的主要表现是厌倦。现在我们能够理解叔本华的话了：人注定要徘徊在焦虑和厌倦这两极之间。
  - `LATE (16)`：我们说人要担负起责任，要实现生命的潜在意义，是想强调生命的真正意义要在世界当中而不是内心去发现，因为它不是一个封闭的系统。
- 结果：
  - `coherent_accumulation = iterator_v1`
  - `insight_and_clarification = iterator_v1`
- 完整关键反应：
  - 见附录第 `2` 节。

`attentional_v2`

- 这一题不是完全没有经过痕迹：
  - `anchor_hit = 1/3`
  - 但 `matched_reactions = 0`
- 也就是说，它留下了一些结构性经过痕迹，却没有形成可以直接附着在锚点上的 substantive reaction。

`iterator_v1`

- 它最强的 accumulation 证据主要出现在 `MID`：
  - 它把“维持张力”明确读成避免跌入“虚无/厌倦”的机制。
- `LATE` 则说明 reader 仍然在审查“意义为什么要在世界中发现”这条论证。
- 但这题也要收得克制一点：
  - 它不是像 `probe 1` 那样非常漂亮的三段闭合。
  - 更准确地说，这是 `iterator_v1` 的相对胜出，而不是特别强、特别完整的 accumulation showcase。

本题结论：

- `iterator_v1` 至少留下了真实的跨段承接。
- `attentional_v2` 则连这种有限但真实的承接都没有外显出来。

### 5.3 《史蒂夫·乔布斯》probe 1

- Probe ID: `steve_jobs_private_en__17__probe_1`
- Case payload：
  - [steve_jobs probe 1](../../../eval/runs/attentional_v2/attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407/shards/main/cases/steve_jobs_private_en__17__probe_1.json)
- 这题真正要看什么：
  - 它要看 reader 能不能把 GUI / bitmapping 的技术突破、Jobs 的大众化产品愿景，以及 Lisa 团队后面的冲突放在同一条主线上。
- 完整 probe 题面：
  - `EARLY (17)`：This graphical user interface—or GUI, pronounced “gooey”—was facilitated by another concept pioneered at Xerox PARC: bitmapping…
  - `MID (17)`：“We’ve got to do it!” It was the breakthrough he had been looking for: bringing computers to the people, with the cheerful but affordable design of an Eichler home and the ease of use of a sleek kitchen appliance. “How long would this take to implement?”
  - `LATE (17)`：Atkinson and Jobs became best friends for a while… But John Couch and the other professional engineers on his Lisa team… resented Jobs’s meddling… There was also a clash of visions.
- 结果：
  - `coherent_accumulation = attentional_v2`
  - `insight_and_clarification = attentional_v2`
- 完整关键反应：
  - 见附录第 `3` 节。

`attentional_v2`

- 这题的 strongest direct evidence 在 `MID`：
  - 它明确抓住了 `cheerful but affordable` 的审美张力。
  - 也抓住了 `How long would this take to implement?` 里从愿景转入现实约束的动作。
- 但这一题也不能写得过强：
  - formal `EARLY` 对应的是 `17.15`，不是之前容易误写成的 `17.14`。
  - formal `LATE / 17.39` 上也没有 clean emitted matched reaction。
- 所以这题更准确的理解是：
  - `attentional_v2` 至少一直留在了正确主线上，留下了比 `iterator_v1` 更可信的 chapter-window continuity。
  - 但它并没有把这条链讲得非常漂亮，更像是一个 `medium-confidence relative win`。

`iterator_v1`

- 它确实在 `MID` 留下了对 implementation question 的反应。
- 但它没有把这条线稳定带到 `LATE` 的 Lisa 团队冲突上。
- 所以它的问题不是完全没读到，而是关键冲突线没有闭合。

本题结论：

- `attentional_v2` 赢在“没有读丢主线”，不是赢在“已经把整条链讲透了”。
- 这也是为什么这题适合写成相对胜出，而不适合写成 V2 的代表性 showcase。

### 5.4 `Supremacy` probe 1

- Probe ID: `supremacy_private_en__13__probe_1`
- Case payload：
  - [supremacy probe 1](../../../eval/runs/attentional_v2/attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407/shards/main/cases/supremacy_private_en__13__probe_1.json)
- 这题真正要看什么：
  - 它考的是 DeepMind autonomy / governance 这条线：
  - 从前面的自治承诺，到中间的 board / trustees 折中，再到最后 licensing arrangement 的重包装。
- 完整 probe 题面：
  - `EARLY (13)`：Instead of being an “autonomous unit,” DeepMind could become an “Alphabet company”…
  - `MID (13)`：DeepMind could do a kind of partial spinout and have its own board of trustees…
  - `LATE (13)`：Instead of being a financial asset of Google, DeepMind would enter an exclusive licensing agreement with the company instead…
- 结果：
  - `coherent_accumulation = attentional_v2`
  - `insight_and_clarification = attentional_v2`
- 完整关键反应：
  - 见附录第 `4` 节。

`attentional_v2`

- 这题里它最强的地方，是从头到尾守住了 DeepMind autonomy thread。
- `EARLY` 的 direct reaction 很清楚：
  - 它把 “autonomous unit” 和 “Alphabet company” 之间的转写读成软自治和硬 accountability 的切换。
- `LATE` 的 direct reaction 也很扎实：
  - 它把 licensing arrangement 读成 dependency 的重新包装，而不是独立。
- `MID` 的 strongest evidence 主要是 supporting evidence：
  - board 描述里三位 Alphabet 高管与三位匿名独立董事之间的不对称，帮助它把中段治理结构读清楚。

`iterator_v1`

- 这一题里它并不是完全没有阅读价值。
- 它对 Nadella、Altman、OpenAI、Microsoft 等 actor/company 的捕捉，确实对整本书理解有帮助。
- 但对这道 probe 来说，这反而构成负证据：
  - 因为它把阅读主线带到了 Altman/Nadella/OpenAI 叙事，而不是 DeepMind autonomy thread。

本题结论：

- 这是一道 `attentional_v2` 赢得比 `5.3` 更干净的题。
- 它赢在强 thread discipline，而 `iterator_v1` 输在 thread drift。

### 5.5 《The Value of Others》probe 1

- Probe ID: `value_of_others_private_en__8_10__probe_1`
- Case payload：
  - [value_of_others probe 1](../../../eval/runs/attentional_v2/attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407/shards/main/cases/value_of_others_private_en__8_10__probe_1.json)
- 这题真正要看什么：
  - 它要看前面的 captain/passenger 框架，是否能经过 chapter `9` 的 negotiation logic，一直带到 chapter `10` 的 marketplace-principles claim。
- 完整 probe 题面：
  - `EARLY (8)`：there are more passengers than captains…
  - `MID (9)`：each party… tries to secure the best possible outcome for itself…
  - `LATE (10)`：the principles that govern the commercial marketplace remain just as true when applied to the sexual marketplace.
- 结果：
  - `coherent_accumulation = iterator_v1`
  - `insight_and_clarification = iterator_v1`
- 完整关键反应：
  - 见附录第 `5` 节。

`attentional_v2`

- 它在 `EARLY` 其实读得不差：
  - 能把 passenger/captain 对比读成压缩因果和结构性区分。
- 但这题真正 decisive 的负证据在 `LATE`：
  - formal `LATE / 10` 是 `0 matched reactions`
  - formal `LATE / 10` 也是 `0 matched attention events`
- 这说明它没有把前面的模型带到最后一跳。

`iterator_v1`

- 这里要特别注意证据层级：
  - formal `LATE` 题面本身是 marketplace-principles 那句总结句。
  - 但 V1 最有力的 late evidence，不是直接附着在 formal `LATE` 本句上的 exact hit，而是同一节 `10.10` 里的 supporting bridge。
- 这些 supporting reactions 之所以足够有力，是因为它们明确说出了两件事：
  - `the economic model is being extended here`
  - `This connects back to the 'adjust your expectations' advice from earlier chapters`

本题结论：

- `attentional_v2` 输在 formal `LATE` 完全空白。
- `iterator_v1` 赢在：虽然它的 late evidence 更像 same-section supporting bridge，而不是 formal `LATE` 的 clean direct hit，但它确实把 chapter `10` 继续读成了前面模型的延伸。

### 5.6 《悉达多》probe 1

- Probe ID: `xidaduo_private_zh__13_15__probe_1`
- Case payload：
  - [xidaduo probe 1](../../../eval/runs/attentional_v2/attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407/shards/main/cases/xidaduo_private_zh__13_15__probe_1.json)
- 这题真正要看什么：
  - 它不是泛泛问“最后有没有接受世界”。
  - 它要看的是：后面的平静之所以重要，是不是因为前面的伤口、依恋和痛苦已经被读得足够具体。
- 完整 probe 题面：
  - `EARLY (13)`：可是自从儿子出现，他悉达多却成了完全的世人。苦恋着，在爱中迷失；因为爱，而成为愚人。
  - `MID (14)`：他坦白最狼狈的事，无所顾忌地暴露伤口。他说他今天如何被灼痛击败……
  - `LATE (15)`：我不再将这个世界与我所期待的，塑造的圆满世界比照，而是接受这个世界，爱它，属于它。
- 结果：
  - `coherent_accumulation = iterator_v1`
  - `insight_and_clarification = tie`
- 完整关键反应：
  - 见附录第 `6` 节。

`attentional_v2`

- 它这题的 strongest evidence 主要集中在 `EARLY` 周边的 same-chapter supporting evidence。
- 例如它对“用爱束缚”“过失”“不作为的伦理边界”这些局部压力读得很准。
- 但 judge 认为它没有把这些 wound-bearing 反应稳定带到 `MID / LATE`。

`iterator_v1`

- 它的优势不在局部措辞锋利，而在人物弧线闭合。
- `EARLY` 它明确把“我成了愚人”读成身份翻转。
- `LATE` 它又把“停止比照、接受世界”读成对 earlier suffering 的 closure。
- 但为什么 `insight_and_clarification` 只打平：
  - 因为 judge 认为两边都还差最后一层解释：
  - 前面的伤口为什么不是单纯 precede，而是后面接受世界的必要条件。

本题结论：

- `coherent_accumulation` 上，V1 的人物弧线闭合更完整。
- `insight_and_clarification` 上，两边都没有把最深的因果链彻底说透，所以最后只打成 `tie`。

### 5.7 《悉达多》probe 2

- Probe ID: `xidaduo_private_zh__13_15__probe_2`
- Case payload：
  - [xidaduo probe 2](../../../eval/runs/attentional_v2/attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407/shards/main/cases/xidaduo_private_zh__13_15__probe_2.json)
- 这题真正要看什么：
  - 这题比上一题更强调道德学习和经验学习。
  - 它要看的是：前面的“独自行过生命、犯错、受苦、理解世人”，有没有真正汇入后面的“接受这个世界，爱它，属于它”。
- 完整 probe 题面：
  - `EARLY (13)`：人独自行过生命，蒙受玷污，承担罪过，痛饮苦酒，寻觅出路。
  - `MID (14)`：他在他们的每种激情、每种作为中看到生命、生机，看到坚不可摧之物和梵天。他在他们盲目的忠诚、盲目的强悍和坚韧中看到可爱和可敬之处。
  - `LATE (15)`：我不再将这个世界与我所期待的，塑造的圆满世界比照，而是接受这个世界，爱它，属于它。
- 结果：
  - `coherent_accumulation = iterator_v1`
  - `insight_and_clarification = iterator_v1`
- 完整关键反应：
  - 见附录第 `7` 节。

`attentional_v2`

- 这题的 formal `EARLY` 其实有 direct evidence：
  - 它明确抓住了“谁能免于罪孽、贪婪和愚昧”这一哲学反问。
- 但它更强的部分仍主要集中在 `EARLY` 周边。
- judge 点名它的问题是：
  - 中段只留下了一个比较简略的 bridge 痕迹。
  - 到 `LATE` 时，没有把 earlier suffering-and-error arc 明确带进“接受世界”的段落。

`iterator_v1`

- 真正决定胜负的，是它在 `LATE` 的 retrospective move：
  - 它把“年轻时逃离一切传统”与后来“去经历罪孽”读成同一条 moral-learning arc 的前后两端。
- 它同时把“停止比照”解释成“比较本身才是苦的根源”，于是 `LATE` 不再是悬空格言，而是 earlier experience 的 closure。

本题结论：

- `attentional_v2` 在这题并不缺早段细读。
- 它缺的是把这些 earlier pressure 收束成一条长线的稳定动作。
- `iterator_v1` 则明确完成了这一步，所以两个 target 都判给了它。

## 6. 跨题结论

### 6.1 `attentional_v2` 的真实长项

这轮结果里，`attentional_v2` 的优势主要集中在三件事：

- 更不容易跑到错误主线
  - `Supremacy` 是最明显的例子。
- 更擅长局部措辞和结构压力
  - 比如《悉达多》里的“用爱束缚”“过失”，以及《史蒂夫·乔布斯》里的 `cheerful but affordable`。
- 在单章长线题里更稳
  - 只要题目更强调“别跑题、别换主线”，V2 的表现会明显更好。

### 6.2 `iterator_v1` 的真实长项

这轮结果里，`iterator_v1` 的优势也非常集中：

- 更会 retrospective bridging
  - 更常明确说出“这在回应前面的什么”。
- 更会把窗口尾部重新挂回窗口前部
  - `The Value of Others` 是最明确的例子。
- 更会把人物弧线或概念弧线闭合
  - 《活出生命的意义》和《悉达多》的几道题都体现得很明显。

### 6.3 哪些题最能代表这轮结果

- 最能代表 `iterator_v1` long-span 优势的题：
  - `5.1《活出生命的意义》probe 1`
  - `5.5《The Value of Others》probe 1`
- 最能代表 `attentional_v2` 主线约束优势的题：
  - `5.4 Supremacy probe 1`
- 需要克制解读的题：
  - `5.3《史蒂夫·乔布斯》probe 1`
  - 它更像一个 `medium-confidence relative win`，不是 probe 对齐非常干净的 showcase。

## 7. 这轮评测支持什么结论

这轮结果支持的不是“V2 不应该继续做”，而是更具体的三条判断：

1. `attentional_v2` 目前还没有在 bounded long-span accumulation 上超过 `iterator_v1`。
2. `attentional_v2` 的产品价值仍然成立，因为它在主线约束、局部精度和少跑偏上确实更好。
3. V2 现在最该补的，不是“更会写漂亮句子”，而是：
   - late-anchor persistence
   - retrospective bridge emission
   - window-end closure

## 8. 后续动作建议

- 不要再用旧思路去“补丁式修报告”。
  - 后续所有评估报告，都应该继续沿用这版的证据分层写法。
- 不要因为这轮 long-span 结果就回退默认机制。
  - 这轮结果说明的是“V2 的 long-span 还有明确改进点”，不是“默认切换方向错误”。
- 机制改进应继续聚焦 long-span 的三类缺口：
  - 关键后段锚点的持续可见性
  - 把后文明确读成前文回答 / 延伸 / 反转的稳定外显动作
  - 不让窗口尾部总结段落变成悬空金句

如果你要继续逐条审计证据，请直接进入：

- [关键反应附录](./attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407_score_impact_reaction_appendix.md)

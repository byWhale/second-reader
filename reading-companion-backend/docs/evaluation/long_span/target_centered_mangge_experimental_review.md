# 芒格之道 Target-Centered Experimental Review

Note: this file is now a source-specific companion. For the current unified review pass, prefer:
- `reading-companion-backend/docs/evaluation/long_span/target_centered_candidate_review.md`
- see the `Experimental Appendix` section there for the live combined review entry.

Status: `experimental_review` only. This document is outside the active v2 main batch and does not change the active draft case dataset or manifest.

Purpose: record a **new-method, target-centered** pass over `mangge_zhi_dao_private_zh__segment_1` so future review does not have to fall back to the older substrate memo.

Discovery rule: every candidate below was mined directly from the active正文窗口原文 (`segment_sources/mangge_zhi_dao_private_zh__segment_1.txt`). `note cases`, `excerpt cases`, and historical probes were excluded from discovery.

## Overview

| Book | Window | Candidate count | Status | Notes |
| --- | --- | ---: | --- | --- |
| 《芒格之道》 | `mangge_zhi_dao_private_zh__segment_1` | 3 | experimental only | Repeated bottom-philosophy signals across 1987-1990 talks; promising, but weaker and more repetition-dependent than the current main batch. |

Thread-type mix in this experimental pass:
- `概念/区分澄清线`: `2`
- `论证型论证线`: `1`

## Candidate 1

### `mangge_seg1_exp_tc01_competence_circle_to_safety_margin`

- `candidate_id`: `mangge_seg1_exp_tc01_competence_circle_to_safety_margin`
- `book / window`: `《芒格之道》` / `mangge_zhi_dao_private_zh__segment_1`
- `thread_type`: `概念/区分澄清线`
- `one-line thread`: 从“不预测未来、如履薄冰”到“清楚自己能力的大小”，再到小能力圈与“不赚最后一个铜板”的安全边际纪律。
- `target_span`:
```text
目前，商业票据还没造成太大的损失，但是，不排除商业票据出现集中违约的可能性。赚尽最后一个铜板，这是银行和储贷机构犯过的错误。如今，货币市场基金重蹈覆辙，也想赚钱赚到尽。

在伯克希尔的不同时期，我们制定过管理闲置资金的各种规定。为了防范风险，我们制定的规矩，恰恰是不赚最后一个铜板。例如，我们会规定：参照高信用等级的标准收益率，如果某品种的收益率高出0.125%，则禁止投资。一笔投资，利率超出了正常水平，我们绝对不碰。另外，对于发行人，我们也有限制条件，只投资符合条件的发行人的品种。
```
- `upstream_nodes`:
  - `u1` 早期的不预测与不安:
```text
我要是真知道如何复制过去的成功，那可好了。其实，大多数时候，我们什么都不做。我们出手的时候很少。即使是出手的时候，我们也是如履薄冰，对可能承担的风险感到不安。以前的投资机会让我们感到踏实，现在我们觉得不踏实。
```
  - `u2` “谦卑”被重写成清楚能力与限制:
```text
用“谦卑”这个词也许不太恰当，可能用“务实”这个词更合适。我们能取得今时今日的成就，不是因为我们的能力比别人高出多少，而是我们比别人更清楚自己能力的大小。清楚自己能力的大小，这个品质应该不能说是“谦卑”。

充分认清客观条件的限制，充分认识自身能力的限制，谨小慎微地在限制范围内活动，这是赚钱的诀窍。这个诀窍，与其说是“谦卑”，不如说是“有克制的贪婪”。
```
  - `u3` 能力圈的小圆圈:
```text
好在本·格雷厄姆是个天才，在我们遇到的人中，很少有像他那么聪明的。另外，我们很清楚自己的不足，很清楚有很多事我们做不到，所以我们谨小慎微地留在我们的“能力圈”之中。“能力圈”是沃伦提出的概念。沃伦和我都认为，我们的“能力圈”是一个非常小的圆圈。

我年轻时，有个朋友说：“芒格只研究自己生意里的那点事，和他的生意无关的事，他一概不知。”在自己的已知与未知之间，我们画出明确的界线，我们只在已知的圆圈内活动。
```
- `expected_integration`: target 处应把“不赚最后一个铜板”读成前面整条认知边界哲学的晚期制度化落点，而不是一条孤立的风险偏好格言。
- `why_it_is_long_range`: 从 1987 年的“不预测未来”一直跨到 1990 年的“安全边际/不赚最后一个铜板”，横跨多个讲话年份与不同场景。
- `span_audit`: paragraphs `62 -> 624` (span `562`)
- `distinct_from_neighbors`: 这条测的是风险边界如何逐步定型；不是一般“要保守”。
- `risk_notes`: 容易被回答者压扁成单一“能力圈”名词；好的反应应把“不预测未来 -> 清楚限制 -> 小能力圈 -> 不赚最后一个铜板”串起来。

## Candidate 2

### `mangge_seg1_exp_tc02_self_interest_distorts_advice`

- `candidate_id`: `mangge_seg1_exp_tc02_self_interest_distorts_advice`
- `book / window`: `《芒格之道》` / `mangge_zhi_dao_private_zh__segment_1`
- `thread_type`: `概念/区分澄清线`
- `one-line thread`: 从鱼钩故事与“别问理发师”，到投行卖方信息，再到商学院对大公司的结构性失明，同一条“利益扭曲判断”底层哲学不断再显影。
- `target_span`:
```text
商学院需要大公司的捐赠，商学院的毕业生需要到大公司就业。所以说，从自己的利益出发，商学院不可能谴责大公司的不良行为，除非一家大公司已经遭到全社会的谴责，那商学院倒是可以跟着进行批判。即使是在商学院的象牙塔中，受利益驱使，也不能完全保持客观公正。

本·富兰克林说过：“结婚之前，擦亮双眼。结婚之后，睁一只眼闭一只眼。”商学院就是这么做的。它们已经嫁给了大公司，有些事情，只能睁一只眼闭一只眼。
```
- `upstream_nodes`:
  - `u1` 鱼钩故事与“别问理发师”:
```text
多年以前，我在帕萨迪纳市有个朋友，是做渔具生意的。他出售的鱼钩五颜六色的。我以前从没见过色彩这么丰富的鱼钩。我问他：“你这鱼钩五颜六色的，鱼是不是更容易上钩啊？”

他回答道：“查理，我这鱼钩又不是卖给鱼的。”

你们笑归笑，所有人都有这个倾向。所有人的潜意识里都有这样的偏见：给别人提建议时，以为是在为别人考虑，其实是从自己的利益出发。

自己用不用理发，别问理发师。从自己利益出发的，不仅仅是券商。
```
  - `u2` 卖方信息天然带利益:
```text
监管人员：您讲的话切中要害，这里的风险很难排查。在检查时，我们看到的信息都是投行提供的，而投行是证券化产品的卖方，它们在里面有自己的利益。
```
- `expected_integration`: target 处应把对商学院的批评读成同一条“利益结构使人无法保持客观”的再显影，而不是一段脱离前文的新吐槽。
- `why_it_is_long_range`: 1988 年已经用鱼钩故事明确提出原则，1990 年才把这原则推到制度与知识共同体层面。
- `span_audit`: paragraphs `99 -> 578` (span `479`)
- `distinct_from_neighbors`: 这条测的是“利益如何扭曲判断”；不是资本配置或风险边界那条主线。
- `risk_notes`: 例子非常生动，回答者容易停在鱼钩故事或商学院批评本身，而漏掉“同一底层哲学重复显影”的目标。

## Candidate 3

### `mangge_seg1_exp_tc03_waiting_against_dealmaking`

- `candidate_id`: `mangge_seg1_exp_tc03_waiting_against_dealmaking`
- `book / window`: `《芒格之道》` / `mangge_zhi_dao_private_zh__segment_1`
- `thread_type`: `论证型论证线`
- `one-line thread`: 好机会稀缺时宁愿守势、等待、做好眼前的事，最后落实为反对为做交易而做交易，也反对像打牌一样轻率买卖公司。
- `target_span`:
```text
现在要想买到好公司、价格还合适，非常难，用现金收购更难。如果自己公司的股票是高估的，用自己公司的股票收购同行，倒也不吃亏。至于像我们这样用现金收购的，那就难了。特别是最近一段时间，非常难。

现在人们热衷于收购。刷厕所、搬砖头，这些脏活累活没人干。收购多潇洒，大家都抢着干。管理层喜欢四处收购。再说花的又不是自己的钱，为了把收购做成，管理层总能编出很多理由。

西科不会随意卖出子公司。伯克希尔不会因为旗下的子公司遇到了困境，就一卖了之。只有当子公司出现我们根本无法解决的问题时，我们才会卖出。一家子公司，管理层诚实正直，在行业中表现中规中矩，但盈利能力不让人满意。遇到这样的情况，我们就吸取教训，以后不做类似的投资了。但是，我们不会把它卖掉。我们不会像打牌一样，抓一张、扔一张。
```
- `upstream_nodes`:
  - `u1` 早期收购哲学就是等待:
```text
有的人做收购，请来一群投行员工，以为听他们的建议，就能做成一笔又一笔完美的收购。对于这种做法，我实在不敢苟同。即使是投资机会很多的时候，我们辛辛苦苦地研究和跟踪各个机会，一年也只能做成一笔收购。

有些人钱多得烫手，四处收购，一笔接一笔的。这种收购方法，我不认同，很难有好结果。真正做收购是好事多磨，要熬过辛苦的等待，经历反复的波折。

以前，收购难做，我们还有别的出路。股市有好的投资机会，我们可以先投资股票。在等待收购某家公司的过程中，我们可以把资金先用于投资股票。我们西科以前一直是这么做的。我们在股市里投资过通用食品（General Foods）和埃克森（Exxon）这样的大公司，也投资过许多名不见经传的小公司。现在股市里好的投资机会没了，收购也很难做，两条路都不好走了，我们只能采取守势。
```
  - `u2` 中段把“等待”接成经营方式:
```text
我们始终把眼前所有的投资机会进行比较，力求找到当下最合理的投资逻辑，这才是重中之重。找到了最合理的投资逻辑之后，无论周期波动如何剧烈，是顺境还是逆境，我们都泰然自若。这就是我们的投资之道。我们不去做各种短期预测，我们追求的是长期的良好结果。

威廉·奥斯勒爵士（Sir William Osler）一砖一瓦地建成了世界著名的约翰斯·霍普金斯大学医学院（The Johns Hopkins University School of Medicine）。威廉·奥斯勒爵士信奉托马斯·卡莱尔（Thomas Carlyle）的一句名言：“与其为朦胧的未来而烦恼忧虑，不如脚踏实地，做好眼前的事。”这同样是伯克希尔的经营哲学。

手握大量现金，我们向威廉·奥斯勒爵士学习。脚踏实地，做好眼前的事，让公司顺其自然地长期发展。我们是一家特立独行的公司。
```
- `expected_integration`: target 处应把对收购热和“不随意卖子公司”的判断，读成同一条“不要为了做交易而做交易”的长期哲学，而不是几段分散的经营感想。
- `why_it_is_long_range`: 这条线从 1987 年的守势与等待，跨到 1989 年的“做好眼前的事”，再到 1990 年对收购热和随手卖公司的批评。
- `span_audit`: paragraphs `38 -> 645` (span `607`)
- `distinct_from_neighbors`: 这条强调等待与反交易冲动；不同于“能力圈/安全边际”那条认知边界线。
- `risk_notes`: 后段更像经营风格的重复显影，不如前两条那样凝聚，因此更适合作为 `secondary` 实验候选而不是优先保留项。

## Current Recommendation

- `Candidate 1` 和 `Candidate 2` 值得继续保留为新方法下的《芒格之道》实验候选。
- `Candidate 3` 可以保留为次级实验项，但如果后续需要进一步收缩，我会优先保留前两条。
- 这份文档只提供 **target-centered experimental review**，不自动进入 active draft case dataset。

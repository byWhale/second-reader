# Gap 检查（Step 3）

- 目的：基于 Step 1 和 Step 2，补齐“还没讲到的亮点”“设计与实现的缺口”“简历还缺哪些证据”
- 范围：当前仓库源码、评测工件、提交历史、前两步分析报告
- 结论先行：
  - 代码里确实还有几处没被充分提炼的工程亮点，尤其是多格式输入、多语言输出、LLM 容错解析和历史输出兼容。
  - 设计文档里缺失的部分，有一部分是 MVP 阶段很合理的裁剪，有一部分则已经开始影响产品闭环和简历完整度。
  - 如果目标是“让简历更强”，最缺的不是更多形容词，而是更硬的证据：量化 eval、真实使用反馈、多书 benchmark。

## 1. 代码中存在但尚未提炼的亮点

下面这些点，Step 2 没有展开，但其实很适合放进简历或面试故事里。

### 1.1 多格式电子书解析，而不是只做 EPUB Demo

- 代码位置：
  - `src/parsers/ebook_parser.py:28-52`
  - `src/parsers/ebook_parser.py:55-196`
  - `src/parsers/ebook_parser.py:247-363`
- 亮点：
  - 当前解析器支持 `EPUB / PDF / MOBI/AZW / TXT`
  - 不是简单按格式分流，还针对不同格式做了不同 fallback：
    - EPUB 优先读 TOC，拿不到 TOC 就回退到逐 HTML item
    - PDF 优先读 outline，拿不到就按页块分组
    - MOBI 优先读 Kindle 元数据和 NCX，失败时再从解包 HTML 兜底
- 为什么值得写：
  - 这会让项目从“一个 Prompt Demo”升级成“有输入异构性处理能力的文档 Agent”

### 1.2 多语言支持已经落地，不只是中文 Prompt

- 代码位置：
  - `src/iterator_reader/language.py:52-102`
  - `main.py:99-105`, `main.py:117-123`
- 亮点：
  - 书籍语言会先读 EPUB metadata，失败后再根据文本做启发式检测
  - 输出语言支持 `auto / zh / en`
  - Markdown 标签、搜索标签、reaction 标签都有中英文映射
- 为什么值得写：
  - 这是很典型的“产品化细节”，面试里会比单纯说“支持中英文”更有说服力

### 1.3 LLM 输出容错做得比一般原型更扎实

- 代码位置：
  - `src/iterator_reader/llm_utils.py:14-61`
  - `src/analyzer/chapter.py:35-74`
  - `src/agents/generate_then_verify.py:75-125`
- 亮点：
  - 不是假设模型一定返回干净 JSON
  - 同时兼容：
    - 普通字符串
    - content list
    - fenced json block
    - 夹杂说明文字的 JSON 片段
- 为什么值得写：
  - 这是 Agent 工程里很实在的可靠性工作，能体现“我知道模型不会老老实实按格式输出”

### 1.4 历史输出兼容和文件迁移

- 代码位置：
  - `src/iterator_reader/parse.py:395-416`
  - `src/iterator_reader/parse.py:419-461`
- 亮点：
  - `ensure_structure_for_book()` 不只是“有就加载、没有就新建”
  - 还会：
    - 回填章节编号 metadata
    - 识别旧版输出文件名
    - 自动迁移 legacy 文件到新命名规则
- 为什么值得写：
  - 这体现的是“在做演进中的工具，而不是一次性脚本”

### 1.5 用户可见编号和文件命名做了归一化

- 代码位置：
  - `src/iterator_reader/storage.py:19-67`
  - `tests/test_iterator_selection.py:9-62`
- 亮点：
  - 从原始章节标题里推断人类自然理解的章节号
  - 输出文件名用 `ch10_deep_read.md` 而不是内部 id
  - 展示 segment id 时也把内部 `16.3` 映射成用户看到的 `10.3`
- 为什么值得写：
  - 这是很容易被忽略、但很能体现“我在做产品体验而不是只跑通代码”的细节

### 1.6 Eval 不是单一路径匹配，而是分层匹配

- 代码位置：
  - `eval/compare_highlights.py:533-611`
  - `eval/compare_highlights.py:691-761`
  - `tests/test_compare_highlights.py:128-141`
- 亮点：
  - 高亮对比不是简单字符串相等
  - 实际分成 3 层：
    - 直接包含匹配
    - 模糊匹配
    - LLM 概念级匹配
- 为什么值得写：
  - 这个细节比“我写了 eval”更高级，因为它说明你知道文本任务里“同一句话换个说法”不该直接算 miss

### 1.7 搜索验证不是“搜一下”，而是做了质量排序

- 代码位置：
  - `src/agents/generate_then_verify.py:140-196`
  - `src/tools/search.py:19-52`
- 亮点：
  - 搜索结果会按域名质量打分
  - 过滤 Quora、Medium、LinkedIn、Reddit、博客类低质量来源
  - 优先 `.edu`、`.gov`、Wikipedia、Stanford、JSTOR 等来源
- 为什么值得写：
  - 这部分已经不只是工具调用，而是“搜索结果治理”

### 1.8 Step 2 最值得补写进简历的遗漏 Top 5

1. 多格式文档解析与 fallback 处理。
2. 多语言检测与双语输出能力。
3. LLM JSON 容错解析。
4. 历史输出兼容与自动迁移。
5. Direct/Fuzzy/Semantic 三层 eval 匹配。

## 2. 设计文档中有但代码中没有的部分

这里把缺口分成两类：`MVP 刻意不做` 和 `应该做但还没做`。

### 2.1 属于 MVP 刻意不做的合理取舍

#### A. 完整的 Plan-and-Execute 外层图没有真正接进主流程

- 设计里有：
  - 全书规划
  - 动态 re-plan
  - 跨章聚合
- 当前代码：
  - `src/graph/main.py:22-37` 仍是原型
  - `src/graph/outer.py` 里 `replan` 节点没有接入主执行链
  - 主入口已经转向 `iterator_reader`
- 判断：
  - 这是合理取舍
- 原因：
  - 对长文本产品来说，先把 parse/read 跑稳、checkpoint 做实、输出质量评测做起来，通常比先把“全图编排”做完更重要

#### B. LangSmith Trace / 线上可观测性未接入

- 设计里有：LangSmith Eval / Trace
- 当前代码：
  - 环境里装了 `langsmith`
  - 仓库代码没有任何显式接入
- 判断：
  - 这是合理取舍
- 原因：
  - 在单人/早期项目里，先用本地评测脚本和 Markdown 报告迭代，投入产出比更高

#### C. Segment 级 checkpoint 和跨重启记忆恢复未实现

- 设计里强调更强的 state / 容错
- 当前代码：
  - 只有章节级状态持久化
  - 运行中的 `ReaderMemory` 不会在进程间恢复
- 判断：
  - 这是合理取舍
- 原因：
  - 章节级 checkpoint 已经覆盖大部分失败恢复需求；segment 级恢复复杂度明显更高

### 2.2 属于“应该做但还没做”的 Gap

#### A. 金句扩展网络和背景补充没有进入当前 CLI 主链路

- 设计里有：
  - 三个核心模块之一就是“金句扩展网络”
  - 另一个是“背景补充”
- 当前代码：
  - `src/agents/generate_then_verify.py` 已经实现
  - `src/analyzer/chapter.py`、`src/graph/inner.py` 也会调用
  - 但 `main.py -> src/iterator_reader/*` 主流程没有接入
- 判断：
  - 这是明确的产品 Gap
- 原因：
  - 如果它们不进主流程，产品核心价值仍停留在“逐段共读反应”，而不是“带外部知识增量的阅读伴侣”

#### B. 整书透视 / 最终共读笔记组装没有进入当前主入口

- 设计里有：
  - 跨章聚合
  - 思想结构图
  - 组装最终输出
- 当前代码：
  - `src/graph/outer.py:261-302` 有 `aggregate_node`
  - `src/analyzer/holistic.py` 有整书分析
  - 但当前 CLI 只输出 `structure.md` 和章节级 `deep_read.md`
- 判断：
  - 这是最核心的未闭环 Gap
- 原因：
  - 产品定位写的是“输入一本书，输出一份共读笔记”，而当前主线更像“输出多份章节笔记”

#### C. 双架构并存但未收敛

- 当前仓库同时保留：
  - `graph/* + analyzer/*`
  - `iterator_reader/*`
- 判断：
  - 这是工程 debt，不只是风格问题
- 原因：
  - 对维护者来说，很难一眼判断哪条链是主路径、哪条是遗留原型
  - 这会拉高后续补功能时的认知成本

#### D. 没有真正的多书 benchmark / 规模证明

- 设计层面强调“整书级处理”
- 当前仓库里可验证的稳定样本主要还是 1 本书
- 判断：
  - 这是简历和产品都需要补的 Gap
- 原因：
  - 没有多书、多类型输入、多规模 benchmark，很难证明方案具备普适性

#### E. Eval 覆盖了 blind-spot，但缺少 quote-expansion 的实际跑分结果

- `eval/judge.py` 已实现
- 但仓库没有保存 attribution/fidelity/relevance 的正式结果
- 判断：
  - 这是评测证据缺口
- 原因：
  - 对简历来说，“实现了 Judge”不如“Judge 跑出了什么结果”有说服力

## 3. 简历写作所需但代码无法提供的信息

这部分必须靠你手动补，因为代码只保留了最终态，保不住“为什么这么做”。

### 3.1 迭代决策的动机和背景

代码能看出你改了什么，但看不出：

- 为什么从 `graph/*` 转向 `iterator_reader/*`
- 为什么当时觉得“先做章节级 Reader，比先做整书聚合更重要”
- 为什么会把 Prompt 从任务式改成角色式
- 为什么开始做 `compare_highlights` 这套 blind-spot eval

这些信息是面试里最值钱的部分，需要你自己补成故事。

### 3.2 Eval 的量化结果数据

目前仓库里有：

- 高亮对比命中/遗漏报告
- Prompt 调优前后部分对比

但还缺：

- 金句扩展的 `attribution_accuracy / quote_fidelity / relevance` 跑分结果
- 多章、多书、不同 Prompt 版本的统一对比表
- 是否有 `reflection on/off`、`semantic split vs hard split` 之类 ablation

### 3.3 Prompt 历史版本的清晰对比

目前仓库里能靠 `git diff` 和部分输出工件推断 Prompt 迭代，但还缺：

- 每一版 Prompt 的版本号或命名
- 每版针对什么失败模式做修改
- 修改后带来了什么变化

如果你要在简历或面试里讲 Prompt 工程，这部分最好补一张对照表。

### 3.4 用户测试或真实使用反馈

代码无法告诉别人：

- 有没有真实用户或自己长期使用
- 他们最认可什么
- 他们最不满意什么
- 输出是否真的帮助阅读理解，而不是看起来“写得很像”

### 3.5 运行时成本和效率数据

代码中没有稳定记录：

- 一本书 parse 需要多久
- 一章/一段平均耗时
- 单本书大致 token / API 成本
- `read --continue` 在失败恢复场景下节省了多少时间

这些数据对“工程化能力”加分很大。

### 3.6 规模和适用范围

仓库目前不能直接回答：

- 总共处理过多少本书
- 最长一本书有多大
- 中英文之外是否试过别的语言
- PDF/MOBI 实际效果是否达到可用级别

如果你要把它写成“长文本阅读 Agent”，这些边界最好手动补清楚。

## 4. 建议优先补齐的 Top 3

如果只补 3 样东西，让简历显著变强，我建议按下面顺序来。

### Top 1：补一份正式的 Eval 总表

- 最好包含：
  - 3-5 章高亮对比结果
  - Prompt 调优前后对比
  - `semantic split vs hard split`
  - `reflection on vs off`
  - 金句扩展 Judge 三维评分
- 为什么排第一：
  - 这是最容易把“我做了一个 Agent”升级成“我系统评估过它”的证据

### Top 2：把“最终共读笔记”主链路真正打通

- 具体指：
  - 在当前 `parse/read` 主线里接入跨章聚合
  - 把金句扩展网络和背景补充接进最终输出
  - 让用户真正得到“一份整书共读笔记”，而不是若干章节 Markdown
- 为什么排第二：
  - 这是从“一个很强的中间件/研究原型”走向“完整产品闭环”的关键一步

### Top 3：补真实使用证据

- 至少补下面 3 类中的 1-2 类：
  - 多书 benchmark
  - 真实用户/自己持续使用反馈
  - 单本书耗时、成本、恢复收益
- 为什么排第三：
  - 面试官和简历读者最容易追问的就是“你真的用它了吗？效果怎样？”

## 5. 最后判断

### 5.1 当前最适合写进简历的真实定位

当前最稳妥的写法不是：

> 做了一个完整的阅读伴侣产品

而是：

> 设计并实现了一个面向整本电子书的 `Iterator-Reader` 长文本 Agent 原型，支持 LLM 语义分段、逐段 Reader 循环、章节级 checkpoint、断点续读、blind-spot eval 和搜索验证模块。

### 5.2 当前最该避免的过度表述

在没有补证据前，最好避免直接写：

- “已实现完整 Plan-and-Execute + ReAct 双层系统”
- “已实现最终整书共读笔记产品闭环”
- “已显著提升引用归因准确率”  
  原因：仓库里还没有对应的闭环证据或正式跑分

### 5.3 一句话建议

你的代码基础已经足够支撑一份很强的 Agent/LLM 工程简历；现在最缺的不是新功能本身，而是把已有能力补成“更完整的主链路”和“更硬的量化证据”。

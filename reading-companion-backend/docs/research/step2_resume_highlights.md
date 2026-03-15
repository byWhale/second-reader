# 技术亮点提炼（Step 2：面向简历的萃取）

- 基础依据：`docs/research/step1_project_health_report.md`、当前源码、`git log`、`docs/evaluation/*.md`、`output/*`
- 目标：把“项目做了什么”翻译成“简历上能讲什么、面试里能怎么讲”
- 重要说明：
  - 以下内容只使用仓库中可验证的事实。
  - 没有落盘数据的地方会明确写“仓库内未保留量化结果”。
  - 这个项目的最佳叙事不是“已经完美闭环”，而是“从理想化 Agent 架构出发，逐步收敛到可跑、可测、可恢复、可诊断的长文本 Reader 系统”。

## A. Agent 架构设计

### 1. 实际做了什么

- 做了两层职责拆分，但它经历过一次架构落地方式的转向：
  - 原型层：`src/graph/outer.py`、`src/graph/inner.py`、`src/graph/state.py`、`src/graph/main.py`
  - 当前主链路：`main.py`、`src/iterator_reader/parse.py`、`src/iterator_reader/iterator.py`、`src/iterator_reader/reader.py`、`src/iterator_reader/models.py`
- 当前真正生效的双层职责分离是：
  - 外层 `Iterator`：章节选择、进度推进、checkpoint、输出落盘、断点续读
  - 内层 `Reader`：`read -> think -> express -> search_if_curious -> fuse_curious_results -> reflect`
- 状态管理使用了 LangGraph 的状态机建模能力，但运行时采取了“StateGraph 设计 + 手工节点执行”的折中方案：
  - `src/iterator_reader/reader.py` 里定义了 `build_reader_graph()`
  - 真正执行时走的是 `run_reader_segment()` 手工串联节点
- 容错机制落在章节级 checkpoint：
  - `src/iterator_reader/iterator.py` 在章节开始时把 `status` 写成 `in_progress`
  - 成功后写成 `done`
  - 异常时回滚成 `pending`
  - `structure.json` 作为恢复点保存在输出目录

### 2. 怎么做的

- 架构上先把“纯工程遍历”和“高不确定性的 LLM 推理”拆开：外层不关心提示词和推理细节，只负责把一本书可靠地推进下去；内层只关心单个语义单元的阅读质量。
- LangGraph 具体用到的是 `StateGraph`、`TypedDict` 状态定义、`END`、条件边和编译执行模型；但为了可观察性和可 debug 性，当前主路径没有强依赖图运行器，而是复用了同一批 node 函数手工驱动循环。
- 容错不是抽象“重试机制”，而是可恢复的文件化状态机：`structure.json` 既保存章节/语义段结构，也保存章节状态和输出文件名，`--continue` 直接基于这个状态恢复。

### 3. 效果或数据

- 仓库里可验证的完整样本书为 1 本：
  - `The Value of Others...`
  - 已解析为 `15` 个章节、`153` 个语义段、约 `114,572` 词、约 `694,701` 字符
- 样本输出中可看到中途恢复状态：
  - `structure.json` 当前记录 `6/15` 章已完成
  - 说明系统支持“跑一部分后中断，再继续跑”
- Reflection 作为内层质量闸门不是摆设：
  - 在已完成的 6 章里，共 `63` 个语义段
  - 最终保留 `58` 段，跳过 `5` 段
  - 整体跳过率约 `7.9%`
- 当前回归测试：`python3 -m pytest`，`26 passed`

### 4. 最佳故事点

我把一套理想化的双层 LangGraph Agent，收敛成了“外层可恢复遍历器 + 内层可反思 Reader”的工程化长文本系统，重点不是把图画漂亮，而是让它真的能跑完整本书、出问题能继续。

## B. Prompt 工程

### 1. 实际做了什么

- 可从仓库和提交历史里明确识别出 `3` 次大版本 Prompt 演进：
  - `0369b41`：初始双层 Agent Prompt 脚手架，偏任务指令式
  - `2fde8fe`：修正“金句扩展/章节分析”质量，强调真实引文、来源过滤、共读者写法
  - `4cdb45f`：重构为 `Iterator-Reader` Prompt 体系，加入语义分段、六工具箱、反思修订、搜索融合
- Prompt 中台集中在 `src/prompts/templates.py`
- Prompt 不是“写完就算”，而是被测试锁住了关键 guardrails：
  - `tests/test_iterator_prompts.py`
- 仓库里还保留了多轮输出工件，能看见调优轨迹：
  - `output/chapter1_analysis.md`
  - `output/chapter1_analysis_v2.md`
  - `output/chapter1_v3.md`
  - `output/.../ch03_deep_read_before_prompt_tuning.md`
  - `output/.../ch03_deep_read.md`

### 2. 怎么做的

- 第一阶段的 Prompt 更像“任务说明书”：告诉模型抽取、扩展、聚合，但对语气、节奏、选择性控制不够细。
- 第二阶段开始补“反幻觉”与“输出体感”：
  - 扩展金句必须是真实引文
  - 背景搜索过滤低质量来源
  - 章节洞见改成 3-5 段共读者风格
- 第三阶段的核心改进不是多加几条要求，而是把 Prompt 从“做任务”改成“扮演一个克制但有判断力的共读者”，同时用显式 JSON、反例、revision 指令把角色感收回来，避免变成散文生成器。
- 这一轮最有代表性的 Prompt 策略有 4 个：
  - `SEMANTIC_SEGMENTATION_*`：把“概念首次提出 + 紧接展开”强行视为同一语义单元
  - `READER_EXPRESS_*`：明确禁止 checklist 式一段一套模板
  - `READER_CURIOSITY_FUSE_*`：要求把搜索结果“消化”进表达，而不是贴链接
  - `READER_REFLECT_*`：让模型给自己判 `pass/revise/skip`

### 3. 效果或数据

- 仓库内有 1 组明确的 Prompt 调优前后对比数据：Chapter 3
  - `before_prompt_tuning`：
    - Agent 笔记数 `38`
    - 命中 `18`
    - 遗漏 `38`
    - Agent 独有 `24`
    - 输出字符数 `28,183`
  - 当前版：
    - Agent 笔记数 `57`
    - 命中 `19`
    - 遗漏 `37`
    - Agent 独有 `43`
    - 输出字符数 `46,023`
- 换算后：
  - 笔记数 `+50.0%`
  - 输出字符数 `+63.3%`
  - 命中 `+5.6%`
  - 遗漏 `-2.6%`
  - Agent 独有发现 `+79.2%`
- 反应类型也从更单一的三类为主，扩展成更完整的六工具箱表达：
  - 调优前 Chapter 3 可见 `💡 19 / 🔍 12 / ✍️ 7`
  - 调优后新增 `⚡ 16 / 🔗 11`
- 但要诚实说明：
  - 仓库里没有“只改 persona、不改别的”的纯单变量实验
  - 现有 A/B 更像“整套 Reader Prompt 升级”的前后对比，不是严格实验室条件

### 4. 最佳故事点

我把 Prompt 调优从“写得更文艺”变成了“角色感 + 结构感 + 负面约束 + 自我修订”的组合工程，最终提升最明显的不是命中率本身，而是输出覆盖度、认知增量和反应多样性。

## C. 幻觉治理与 Eval

### 1. 实际做了什么

- 做了两类质量控制：
  - 生成过程内质量控制：`Reflection`
  - 生成后评测：`Eval / Judge`
- Reflection 主逻辑在：
  - `src/iterator_reader/reader.py` 的 `reflect_node()`、`_normalize_reflection()`、`should_continue_reader()`
- 幻觉治理主逻辑在：
  - `src/agents/generate_then_verify.py`
  - 先 `generate` 候选，再调用 `search_web` 验证归因和背景事实
- Eval 主体有两套：
  - `eval/compare_highlights.py`：评估 Agent 对人类高亮的命中、遗漏、独有发现
  - `eval/judge.py`：对金句扩展做 LLM-as-Judge 三维评分

### 2. 怎么做的

- Reflection 的机制不是“让模型说说自己表现如何”，而是结构化评分：
  - 评 5 个维度：选择性、联想质量、归因合理性、贴文程度、深度
  - 输出 `pass / revise / skip`
  - `revise` 时必须给出具体 `revision_instruction`
  - 超过最大修改轮数自动降为 `skip`
- Generate-then-Verify 的机制是：
  - 先要求模型只凭参数记忆给出候选
  - 再通过 Tavily 定向检索
  - 过滤低质量域名
  - 最后让验证 Prompt 输出 `verified / model_knowledge / disputed`
- `compare_highlights.py` 的 judge 链路更像一套“感知盲区诊断”：
  - 先做直接文本匹配
  - 再做模糊匹配
  - 再让 LLM 做“概念级命中”判断
  - 对未命中项再让 LLM 诊断是 `parse 分段问题 / 感知密度不足 / 角色盲区 / 上下文依赖 / 其他`
- `eval/judge.py` 的 LLM-as-Judge 则是更传统的 rubric 评分：
  - `attribution_accuracy`
  - `quote_fidelity`
  - `relevance`
  - 每项 `1-5`

### 3. 效果或数据

- Reflection 的直接效果可以从样本输出看到：
  - 已完成 6 章共 `63` 个语义段
  - 保留 `58`
  - 跳过 `5`
  - 说明系统没有把每段都强行写出来
- `compare_highlights` 的已提交数据覆盖 Chapter 1-3：
  - 人类高亮总数 `185`
  - Agent 笔记总数 `208`
  - 命中 `77`
  - 遗漏 `108`
  - Agent 独有发现 `147`
  - 按人类高亮口径粗看，命中率约 `41.6%`
- 三份对比报告的主导遗漏原因一致：
  - Chapter 1：`感知密度不足` 占主导（`18/27`）
  - Chapter 2：`感知密度不足` 占主导（`27/44`）
  - Chapter 3：`感知密度不足` 占主导（`29/37`）
- 关于“归因准确性 / 引文保真度 / 关联性”的三维跑分：
  - `eval/judge.py` 已实现评分器
  - 但仓库内没有保留实际跑分结果文件
  - 所以这一项只能说“评测框架已做”，不能说“已拿到稳定分数”

### 4. 最佳故事点

我没有把“减少幻觉”停留在 Prompt 层，而是做成了三层质量闸门：生成时自评、生成后搜索验证、离线再用 Judge 和 blind-spot eval 看系统到底漏了什么。

## D. 长文本处理

### 1. 实际做了什么

- 把长文本处理拆成两步：
  - Parse 阶段：`src/iterator_reader/parse.py`
  - Read 阶段：`src/iterator_reader/iterator.py` + `src/iterator_reader/reader.py`
- Parse 阶段不是硬切分：
  - 先 `extract_plain_text`
  - 再按段落编号
  - 再用 `segment_chapter_semantically()` 让 LLM 决定语义边界
  - 最后 `_compact_segments()` 做后处理和平衡
- Read 阶段不是整书一次性塞模型：
  - 以语义段为最小单元推进
  - 同时维护 `ReaderMemory`
  - 逐章落盘输出

### 2. 怎么做的

- 这套方案的关键是“先把长文本压成可控的语义单元，再做单元级推理”，这样模型每次只面对一个具有上下文边界的片段，而不是一整章甚至整本书。
- 语义分段 Prompt 里专门加了一条很关键的规则：如果一个概念刚被定义，紧接着的展开、举例、论证不要拆开，这实际上是在保护论证连续性。
- 模型分段后，还会做工程兜底：
  - 单段过长时按 chunk fallback
  - 低价值段落摘要会被裁剪
  - 太碎的小段会自动并回相邻段

### 3. 效果或数据

- 仓库内可验证的整书样本规模：
  - 书籍：`The Value of Others...`
  - 输入文件大小：约 `1.73 MB` EPUB
  - 解析后：`15` 章、`153` 个语义段
  - 文本量：约 `114,572` 词
- 当前仓库内已经完成的章节输出：
  - `Prologue`
  - `Chapter 1`
  - `Chapter 2`
  - `Chapter 3`
  - `Chapter 4`
  - `Chapter 10`
- 单章输出规模：
  - `ch01_deep_read.md` 约 `57,792` 字符 / `647` 行
  - `ch03_deep_read.md` 约 `46,023` 字符 / `507` 行
- 关于“LLM 语义分段 vs 硬切分”的直接对照数据：
  - 仓库内没有保存硬切分 baseline
  - 因此不能声称“已量化优于硬切分”
  - 目前只能给出间接证据：
    - `SEMANTIC_SEGMENTATION_SYSTEM` 明确防止“概念定义与展开被拆散”
    - `tests/test_iterator_prompts.py` 专门为这一 guardrail 写了回归测试
    - `docs/evaluation/highlight_comparison_*.md` 里也能看到 parse 分段问题被单独识别为遗漏原因
- 关于耗时：
  - 仓库内未记录 parse/read 的稳定 benchmark 耗时
  - 因此这一项不能写成简历数字，只能写成“支持整书分阶段处理”

### 4. 最佳故事点

我不是让模型“硬扛长文本”，而是先把整本书压成语义段，再用段级 Agent 循环去做深读，这让整书处理从一次性生成问题，变成了可恢复、可诊断的流水线问题。

## E. 工程化能力

### 1. 实际做了什么

- Checkpoint 机制：
  - `src/iterator_reader/iterator.py`
  - `src/iterator_reader/storage.py`
  - `src/iterator_reader/parse.py`
- 断点续读：
  - `main.py` 的 `read --continue`
  - `iterator.py` 的 `_chapter_selection()`
- 配置化设计：
  - `src/config.py`
  - `.env.example`
  - `src/tools/search.py`

### 2. 怎么做的

- Checkpoint 的粒度不是进程内内存，而是文件级持久化：
  - 每进入一章就立刻写 `structure.json`
  - 每章完成后再写一次
  - 输出文件名也回写到结构文件
- 断点续读的判断逻辑很直白，但足够稳：
  - `status == done` 的章节直接跳过
  - 当前章异常时回滚为 `pending`
  - 下次 `--continue` 时继续从未完成章节开始
- 配置层做到了“Anthropic-compatible provider swappability”：
  - 用的是 `ChatAnthropic`
  - 但 `base_url`、`api_key`、`model` 全来自环境变量
  - 所以只要接口兼容 Anthropic message format，就能切 provider
- 还有一个很实用的工程细节：
  - `parse.py` 中 `_upgrade_structure_metadata()` 会迁移旧文件名和补齐章节元数据
  - 说明作者考虑过历史输出兼容，而不是每次重跑

### 3. 效果或数据

- 样本 `structure.json` 当前显示 `6/15` 章已完成，说明中途状态真实落盘而不是仅存在内存里。
- 章节级断点恢复的输出目录中，同时保留了：
  - `structure.json`
  - `structure.md`
  - 已完成章节的 `chXX_deep_read.md`
- 测试层面：
  - 章节选择、输出命名、segment id 显示等工程细节都有测试
  - 全量 `26` 个测试通过
- 需要保守表述的一点：
  - 当前的 provider-agnostic 还不是“真正 SDK 无关”
  - 它更准确地说是“Anthropic-compatible endpoint 可切换”

### 4. 最佳故事点

这个项目最有工程含量的地方不是“接了一个大模型”，而是把一本书的处理过程做成了可持久化、可继续、可迁移历史输出的状态机。

## F. 关键决策转折

### 1. 实际做了什么

- 从提交历史能清楚看出 4 个关键转折：
  - `0369b41`：先搭了理想化的 LangGraph 双层骨架
  - `5519e33`：做成“章节分析 + holistic”的 CLI
  - `2fde8fe`：修正扩展金句和章节分析的质量问题
  - `4cdb45f`：大幅转向 `Iterator-Reader`，同时补上 eval 和 tests
- 当前仓库保留了大量“走过弯路后留下的痕迹”：
  - `src/graph/*` 还在，但不是当前主入口
  - `src/analyzer/*` 还在，但不在当前 CLI 主链路
  - `src/graph/main.py` 里仍有明显的“inner graph TODO/未真正接线”痕迹
  - `5519e33` 版本的 `main.py` 还有 `--overview / --chapter / --holistic`，现在已经被 `parse/read` 双命令替代

### 2. 怎么做的

- 第一条弯路：一开始是“先把双层 Agent 图搭出来”，但很快暴露出原型和真实生产链路之间的落差。
- 第二条弯路：曾尝试直接做章节分析和跨章聚合，但后来发现更难的问题不是“最后汇总怎么写”，而是“逐段感知到底抓没抓准”。
- 第三条关键修正：从“直接生成扩展内容”转向“真实引文 + 搜索验证 + 来源过滤”，说明团队意识到输出质量瓶颈不是文风，而是可信度。
- 第四条关键修正：从“做一个看起来完整的 Agent”转向“做一个可观测、可评测、可恢复的 Reader 系统”，于是 `iterator_reader/`、`compare_highlights.py`、完整测试集一起落地。

### 3. 效果或数据

- `4cdb45f` 这次重构是最强的简历证据：
  - 一次提交新增 `26` 个文件
  - `+6811 / -564`
  - 同时引入：
    - `iterator_reader/` 全套实现
    - `compare_highlights.py`
    - 4 份评测报告
    - 6 组测试文件
- `2fde8fe` 也是一个很好的“修正幻觉”证据：
  - 提交信息明确写了：
    - 要求真实 quotes
    - 过滤 Quora/Medium 等低质量源
    - 优先 JSTOR/Sage/APA 等学术源
    - 重写章节洞见为共读者口吻
- 从输出工件也能看到“迭代不是纸上谈兵”：
  - `chapter1_analysis.md -> chapter1_analysis_v2.md -> chapter1_v3.md`
  - `ch03_deep_read_before_prompt_tuning.md -> ch03_deep_read.md`

### 4. 最佳故事点

最值得讲的不是“我从零写了一个 Agent”，而是“我发现早期那套漂亮的全图架构解决不了真实质量问题，于是我重构成了 Iterator-Reader，并用 blind-spot eval 把 Prompt 调优从主观感觉变成可诊断迭代”。

## 一句话版简历素材

- 做了一个面向整本电子书的 `Iterator-Reader` 共读 Agent：先用 LLM 做语义分段，再逐段执行 `Think/Express/Search/Reflect`，支持章节级 checkpoint、断点续读和 Markdown 持久化输出。
- 通过 `compare_highlights` 评测链路把“模型写得像不像”转成“Agent 漏掉了什么、为什么漏”，将 Prompt 调优从主观修改升级为可诊断的 blind-spot 迭代。
- 针对引用扩展和背景补充实现了 `Generate-then-Verify`：先生成候选，再用 Tavily 搜索验证并标注置信度，同时过滤低质量来源，控制归因幻觉。

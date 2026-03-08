"""Regression tests for Reader and parse prompt guardrails."""

from __future__ import annotations

from src.prompts.templates import (
    BOOK_ANALYSIS_QUERY_PROMPT,
    BOOK_ANALYSIS_SKIM_PROMPT,
    BOOK_ANALYSIS_SYNTHESIS_PROMPT,
    READER_CHAPTER_REFLECT_PROMPT,
    READER_CHAPTER_REFLECT_SYSTEM,
    READER_CURIOSITY_FUSE_SYSTEM,
    READER_CURIOSITY_FUSE_PROMPT,
    READER_EXPRESS_PROMPT,
    READER_EXPRESS_SYSTEM,
    READER_REFLECT_PROMPT,
    READER_THINK_PROMPT,
    READER_REFLECT_SYSTEM,
    SEMANTIC_SEGMENTATION_SYSTEM,
)


def test_reader_express_system_breaks_checklist_pattern():
    """Express system prompt should explicitly reject one-of-each output."""
    assert "不要把这四种工具当作 checklist" in READER_EXPRESS_SYSTEM
    assert "你不需要每种都用，也不需要每种只用一次" in READER_EXPRESS_SYSTEM
    assert "同一种 `type` 可以连续出现多次" in READER_EXPRESS_SYSTEM


def test_reader_express_prompt_demonstrates_free_reaction_list():
    """Express prompt example should allow repeated reaction types."""
    assert "反例（不要模仿这种机械 checklist）" in READER_EXPRESS_PROMPT
    assert "每段固定输出 1 条 `highlight` + 1 条 `association` + 1 条 `curious`" in READER_EXPRESS_PROMPT
    assert READER_EXPRESS_PROMPT.count('"type": "highlight"') >= 2
    assert READER_EXPRESS_PROMPT.count('"type": "curious"') >= 2
    assert "不需要凑齐四种 `type`" in READER_EXPRESS_PROMPT


def test_reader_express_system_mentions_structural_nodes_and_rhetoric():
    """Reader system prompt should raise sensitivity to structural nodes."""
    assert "作者搭建论证骨架的关键节点" in READER_EXPRESS_SYSTEM
    assert "第一次给概念命名或下定义的句子" in READER_EXPRESS_SYSTEM
    assert "总起句与总结句" in READER_EXPRESS_SYSTEM
    assert "转折句" in READER_EXPRESS_SYSTEM
    assert "因果链锚点" in READER_EXPRESS_SYSTEM
    assert "隐喻、俗语、引用锚点" in READER_EXPRESS_SYSTEM
    assert "这些位置同样可能触发 💡、✍️、🔍、⚡、🔗 或 🤫" in READER_EXPRESS_SYSTEM


def test_reader_express_system_mentions_discern_and_connect_back():
    """Reader system prompt should expose the expanded six-tool toolbox."""
    assert "⚡ 审辩" in READER_EXPRESS_SYSTEM
    assert "🔗 回溯" in READER_EXPRESS_SYSTEM
    assert "只能是 `highlight` / `association` / `curious` / `discern` / `connect_back` / `silent`" in READER_EXPRESS_SYSTEM
    assert "审辩不是找茬" in READER_EXPRESS_SYSTEM
    assert "`connect_back` 必须点出前文的具体位置或内容" in READER_EXPRESS_SYSTEM


def test_reader_curiosity_fuse_system_requires_digested_search_output():
    """Post-search curiosity prompt should integrate findings into the note."""
    assert "不要把搜索结果当附录贴出来" in READER_CURIOSITY_FUSE_SYSTEM
    assert "写成“查过之后你的阅读随想”" in READER_CURIOSITY_FUSE_SYSTEM
    assert "不要逐条复述链接" in READER_CURIOSITY_FUSE_SYSTEM


def test_reader_reflect_prompt_requires_reason_codes_and_targets():
    """Reflect prompt should request structured revise diagnostics."""
    assert "reason_codes" in READER_REFLECT_PROMPT
    assert "target_reaction_indexes" in READER_REFLECT_PROMPT
    assert "LOW_SELECTIVITY" in READER_REFLECT_SYSTEM


def test_reader_chapter_reflect_prompt_mentions_scoped_repairs():
    """Chapter reflection prompt should require segment/reaction scoped repairs."""
    assert "segment_repairs" in READER_CHAPTER_REFLECT_PROMPT
    assert "reaction_repairs" in READER_CHAPTER_REFLECT_PROMPT
    assert "segment_quality_flags" in READER_CHAPTER_REFLECT_PROMPT
    assert "strong" in READER_CHAPTER_REFLECT_SYSTEM
    assert "skipped" in READER_CHAPTER_REFLECT_SYSTEM


def test_reader_prompts_require_self_contained_clause_quotes():
    """Reader prompts should bias quotes toward readable source-grounded clauses."""
    assert "最小可独立理解的 clause" in READER_THINK_PROMPT
    assert "最小可独立理解的 clause" in READER_EXPRESS_PROMPT
    assert "只剩从句/补语" in READER_THINK_PROMPT
    assert "只剩从句/补语" in READER_EXPRESS_PROMPT
    assert "冒号或分号后的右半句" in READER_THINK_PROMPT
    assert "悬空 `it/they/this/that` 指代" in READER_EXPRESS_PROMPT
    assert "坏例子：`there is no culture in which it doesn't exist`" in READER_THINK_PROMPT
    assert "好例子：`This tendency is universal: there is no culture in which it doesn’t exist.`" in READER_EXPRESS_PROMPT
    assert "不要重新创造更短的残句引用" in READER_CHAPTER_REFLECT_PROMPT


def test_language_contract_preserves_quotes_and_search_hits():
    """Core generation prompts should include the language contract for quote/search handling."""
    prompts = [
        READER_THINK_PROMPT,
        READER_EXPRESS_PROMPT,
        READER_CURIOSITY_FUSE_PROMPT,
        READER_REFLECT_PROMPT,
        READER_CHAPTER_REFLECT_PROMPT,
        BOOK_ANALYSIS_SKIM_PROMPT,
        BOOK_ANALYSIS_SYNTHESIS_PROMPT,
    ]
    for prompt in prompts:
        assert "输出语言契约" in prompt
        assert "原文引用字段（如 anchor_quote、书中直接引文）保持原文语言，不翻译" in prompt
        assert "搜索命中字段（title/snippet/url）保持原样，不翻译、不改写" in prompt


def test_book_analysis_prompts_use_neutral_placeholders_and_query_language_policy():
    """Skim/query templates should avoid fixed-language examples while keeping retrieval flexibility."""
    assert "<skim_summary_1_to_3_sentences>" in BOOK_ANALYSIS_SKIM_PROMPT
    assert "<claim_1>" in BOOK_ANALYSIS_SKIM_PROMPT
    assert "<deep_read_reason>" in BOOK_ANALYSIS_SKIM_PROMPT
    assert "检索词语言策略" in BOOK_ANALYSIS_QUERY_PROMPT
    assert "不受输出语言硬约束" in BOOK_ANALYSIS_QUERY_PROMPT


def test_semantic_segmentation_keeps_definition_with_expansion():
    """Segmentation prompt should preserve concept-definition continuity."""
    assert "概念首次提出" in SEMANTIC_SEGMENTATION_SYSTEM
    assert "紧接着的段落是在展开、举例或论证这个定义时，应合并成同一个语义单元" in SEMANTIC_SEGMENTATION_SYSTEM

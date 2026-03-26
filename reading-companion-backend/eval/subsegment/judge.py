"""LLM-as-judge helpers for subsegment benchmark comparisons."""

from __future__ import annotations

import json
from typing import Any

from src.iterator_reader.llm_utils import LLMTraceContext, ReaderLLMError, invoke_json, llm_invocation_scope
from src.reading_runtime.llm_registry import DEFAULT_EVAL_JUDGE_PROFILE_ID


PLAN_JUDGE_SYSTEM = """你在做离线 reader eval，不是运行时共读。

任务：比较两个 subsegment 切分方案，判断哪个更符合“最少但自洽的局部阅读单元”。

判定标准：
- `self_containedness`：每个 unit 单独看是否像一个完整的局部阅读对象
- `minimal_sufficiency`：是否只切到必要处，没有把一个 reading move 切碎，也没有把两个独立 move 糊在一起
- `reading_move_purity`：每个 unit 是否主要承载一个主阅读动作
- 不要把“切得更多”当成自动优势
- 不要把“更像人类眼动”当成自动优势

输出 JSON。"""


PLAN_JUDGE_PROMPT = """原始 section：
{segment_text}

Section 摘要：
{segment_summary}

候选 A（{left_label}）：
{left_units_json}

候选 B（{right_label}）：
{right_units_json}

请输出 JSON：
{{
  "winner": "{left_label}|{right_label}|tie",
  "dimension_winners": {{
    "self_containedness": "{left_label}|{right_label}|tie",
    "minimal_sufficiency": "{left_label}|{right_label}|tie",
    "reading_move_purity": "{left_label}|{right_label}|tie"
  }},
  "scores": {{
    "{left_label}": {{
      "self_containedness": 1,
      "minimal_sufficiency": 1,
      "reading_move_purity": 1
    }},
    "{right_label}": {{
      "self_containedness": 1,
      "minimal_sufficiency": 1,
      "reading_move_purity": 1
    }}
  }},
  "reason": "2-4句，说明谁更好以及为什么"
}}"""


DOWNSTREAM_JUDGE_SYSTEM = """你在做离线 reader eval，不是运行时共读。

任务：比较同一 section 在两种 subsegment 策略下生成的 section-level 阅读结果，判断哪个更好。

判定标准：
- `reaction_focus`：反应是否围绕清晰点展开
- `source_anchor_quality`：anchor 是否完整、可读、贴住原文
- `coverage_of_meaningful_points`：是否更少漏掉定义、转折、因果点、callback
- `coherence_after_merge`：多 unit 合并回 section 后是否仍像一条自然阅读轨迹

不要把“反应更多”当成自动优势。输出 JSON。"""


DOWNSTREAM_JUDGE_PROMPT = """原始 section：
{segment_text}

Section 摘要：
{segment_summary}

候选 A（{left_label}）：
{left_rendered_json}

候选 B（{right_label}）：
{right_rendered_json}

请输出 JSON：
{{
  "winner": "{left_label}|{right_label}|tie",
  "dimension_winners": {{
    "reaction_focus": "{left_label}|{right_label}|tie",
    "source_anchor_quality": "{left_label}|{right_label}|tie",
    "coverage_of_meaningful_points": "{left_label}|{right_label}|tie",
    "coherence_after_merge": "{left_label}|{right_label}|tie"
  }},
  "scores": {{
    "{left_label}": {{
      "reaction_focus": 1,
      "source_anchor_quality": 1,
      "coverage_of_meaningful_points": 1,
      "coherence_after_merge": 1
    }},
    "{right_label}": {{
      "reaction_focus": 1,
      "source_anchor_quality": 1,
      "coverage_of_meaningful_points": 1,
      "coherence_after_merge": 1
    }}
  }},
  "reason": "2-4句，说明谁更好以及为什么"
}}"""


def _default_plan_judgment(left_label: str, right_label: str) -> dict[str, Any]:
    return {
        "winner": "tie",
        "dimension_winners": {
            "self_containedness": "tie",
            "minimal_sufficiency": "tie",
            "reading_move_purity": "tie",
        },
        "scores": {
            left_label: {
                "self_containedness": 0,
                "minimal_sufficiency": 0,
                "reading_move_purity": 0,
            },
            right_label: {
                "self_containedness": 0,
                "minimal_sufficiency": 0,
                "reading_move_purity": 0,
            },
        },
        "reason": "judge_unavailable",
    }


def _default_downstream_judgment(left_label: str, right_label: str) -> dict[str, Any]:
    return {
        "winner": "tie",
        "dimension_winners": {
            "reaction_focus": "tie",
            "source_anchor_quality": "tie",
            "coverage_of_meaningful_points": "tie",
            "coherence_after_merge": "tie",
        },
        "scores": {
            left_label: {
                "reaction_focus": 0,
                "source_anchor_quality": 0,
                "coverage_of_meaningful_points": 0,
                "coherence_after_merge": 0,
            },
            right_label: {
                "reaction_focus": 0,
                "source_anchor_quality": 0,
                "coverage_of_meaningful_points": 0,
                "coherence_after_merge": 0,
            },
        },
        "reason": "judge_unavailable",
    }


def _invoke_or_default(system_prompt: str, user_prompt: str, default: dict[str, Any]) -> dict[str, Any]:
    try:
        with llm_invocation_scope(
            profile_id=DEFAULT_EVAL_JUDGE_PROFILE_ID,
            trace_context=LLMTraceContext(stage="subsegment_eval", node="judge"),
        ):
            payload = invoke_json(system_prompt, user_prompt, default)
    except ReaderLLMError:
        return default
    except Exception:
        return default
    return payload if isinstance(payload, dict) else default


def judge_plan_pairwise(
    *,
    segment_text: str,
    segment_summary: str,
    left_label: str,
    left_units: list[dict[str, Any]],
    right_label: str,
    right_units: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare two subsegment plans under the fixed plan-level rubric."""
    return _invoke_or_default(
        PLAN_JUDGE_SYSTEM,
        PLAN_JUDGE_PROMPT.format(
            segment_text=segment_text[:8000],
            segment_summary=segment_summary,
            left_label=left_label,
            right_label=right_label,
            left_units_json=json.dumps(left_units, ensure_ascii=False, indent=2),
            right_units_json=json.dumps(right_units, ensure_ascii=False, indent=2),
        ),
        _default_plan_judgment(left_label, right_label),
    )


def judge_downstream_pairwise(
    *,
    segment_text: str,
    segment_summary: str,
    left_label: str,
    left_rendered: dict[str, Any],
    right_label: str,
    right_rendered: dict[str, Any],
) -> dict[str, Any]:
    """Compare two section-level reader outputs under the downstream rubric."""
    return _invoke_or_default(
        DOWNSTREAM_JUDGE_SYSTEM,
        DOWNSTREAM_JUDGE_PROMPT.format(
            segment_text=segment_text[:8000],
            segment_summary=segment_summary,
            left_label=left_label,
            right_label=right_label,
            left_rendered_json=json.dumps(left_rendered, ensure_ascii=False, indent=2),
            right_rendered_json=json.dumps(right_rendered, ensure_ascii=False, indent=2),
        ),
        _default_downstream_judgment(left_label, right_label),
    )

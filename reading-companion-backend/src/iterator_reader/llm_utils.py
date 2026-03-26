"""Compatibility wrapper over the shared backend LLM gateway."""

from __future__ import annotations

from typing import Any

from src.reading_runtime.llm_gateway import (
    LLMInvocationOverrides,
    LLMTraceContext,
    ReaderLLMError,
    current_llm_scope,
    eval_trace_context,
    invoke_json as _invoke_json,
    invoke_text as _invoke_text,
    llm_invocation_scope,
    parse_json_payload,
    response_text,
    runtime_trace_context,
)


def invoke_json(system_prompt: str, user_prompt: str, default: Any, *, profile_id: str | None = None) -> Any:
    """Invoke the shared backend LLM gateway and parse a JSON payload."""

    return _invoke_json(system_prompt, user_prompt, default, profile_id=profile_id)


def invoke_text(system_prompt: str, user_prompt: str, default: str = "", *, profile_id: str | None = None) -> str:
    """Invoke the shared backend LLM gateway and return plain text."""

    return _invoke_text(system_prompt, user_prompt, default, profile_id=profile_id)


__all__ = [
    "LLMInvocationOverrides",
    "LLMTraceContext",
    "ReaderLLMError",
    "current_llm_scope",
    "eval_trace_context",
    "invoke_json",
    "invoke_text",
    "llm_invocation_scope",
    "parse_json_payload",
    "response_text",
    "runtime_trace_context",
]

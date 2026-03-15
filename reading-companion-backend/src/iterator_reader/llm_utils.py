"""Local LLM helper functions for Iterator-Reader."""

from __future__ import annotations

import json
import re
import threading
import time
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_anthropic import ChatAnthropic

from src.config import get_llm_config, get_llm_max_concurrency, get_llm_retry_attempts
from .models import CurrentReadingProblemCode


_LLM_SEMAPHORE = threading.BoundedSemaphore(get_llm_max_concurrency())


class ReaderLLMError(RuntimeError):
    """Typed LLM invocation failure surfaced to the runtime activity tracker."""

    def __init__(self, message: str, *, problem_code: CurrentReadingProblemCode):
        super().__init__(message)
        self.problem_code = problem_code


def _classify_llm_problem(exc: Exception) -> CurrentReadingProblemCode:
    """Map provider/network failures into one stable runtime problem code."""
    message = str(exc).lower()
    if any(token in message for token in ("timed out", "timeout", "read timeout", "deadline exceeded")):
        return "llm_timeout"
    if any(token in message for token in ("authentication", "unauthorized", "forbidden", "invalid api key", "invalid x-api-key")):
        return "llm_auth"
    if any(token in message for token in ("quota", "insufficient", "billing", "credit balance", "rate limit", "429")):
        return "llm_quota"
    return "network_blocked"


def get_reader_llm() -> ChatAnthropic:
    """Create the LLM used by the Iterator-Reader workflow."""
    config = get_llm_config()
    return ChatAnthropic(
        base_url=config["base_url"],
        api_key=config["api_key"],
        model=config["model"],
        temperature=0.2,
        max_tokens=4096,
        timeout=120,
    )


def response_text(response: Any) -> str:
    """Normalize LangChain responses to plain text."""
    if hasattr(response, "content"):
        content = response.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            chunks = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    chunks.append(item.get("text", ""))
                elif not isinstance(item, dict):
                    chunks.append(str(item))
            return "\n".join(chunk for chunk in chunks if chunk)
        return str(content)
    return str(response)


def parse_json_payload(text: str, default: Any) -> Any:
    """Parse the most likely JSON object or array from model output."""
    stripped = text.strip()

    fenced_match = re.search(
        r"```json\s*(\{[\s\S]*?\}|\[[\s\S]*?\])\s*```",
        stripped,
    )
    if fenced_match:
        try:
            return json.loads(fenced_match.group(1))
        except json.JSONDecodeError:
            pass

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    for left, right in (("{", "}"), ("[", "]")):
        start = stripped.find(left)
        end = stripped.rfind(right)
        if start == -1 or end == -1 or end <= start:
            continue
        try:
            return json.loads(stripped[start : end + 1])
        except json.JSONDecodeError:
            continue

    return default


def invoke_json(system_prompt: str, user_prompt: str, default: Any) -> Any:
    """Invoke the configured LLM and parse a JSON payload."""
    response = _invoke_with_limits(system_prompt, user_prompt)
    return parse_json_payload(response_text(response), default)


def invoke_text(system_prompt: str, user_prompt: str, default: str = "") -> str:
    """Invoke the configured LLM and return plain text output."""
    response = _invoke_with_limits(system_prompt, user_prompt)
    text = response_text(response).strip()
    return text or default


def _invoke_with_limits(system_prompt: str, user_prompt: str) -> Any:
    """Invoke the configured LLM behind a shared concurrency gate with basic retries."""
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]
    max_attempts = max(1, get_llm_retry_attempts())
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            with _LLM_SEMAPHORE:
                llm = get_reader_llm()
                return llm.invoke(messages)
        except Exception as exc:  # pragma: no cover - exercised in integration/runtime behavior
            classified = _classify_llm_problem(exc)
            last_error = ReaderLLMError(str(exc), problem_code=classified)
            non_retryable = classified in {"llm_auth", "llm_quota"}
            if attempt >= max_attempts or non_retryable:
                raise last_error
            time.sleep(min(4.0, 0.5 * (2 ** (attempt - 1))))
    if last_error is not None:  # pragma: no cover - defensive fallback
        raise last_error
    raise RuntimeError("LLM invocation failed without raising an exception.")

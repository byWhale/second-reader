"""Local LLM helper functions for Iterator-Reader."""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_anthropic import ChatAnthropic

from src.config import get_llm_config


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
    llm = get_reader_llm()
    response = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
    )
    return parse_json_payload(response_text(response), default)


def invoke_text(system_prompt: str, user_prompt: str, default: str = "") -> str:
    """Invoke the configured LLM and return plain text output."""
    llm = get_reader_llm()
    response = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
    )
    text = response_text(response).strip()
    return text or default

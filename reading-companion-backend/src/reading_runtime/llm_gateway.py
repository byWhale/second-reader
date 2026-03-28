"""Universal provider gateway and trace helpers for project-owned LLM calls."""

from __future__ import annotations

import contextlib
import contextvars
import hashlib
import importlib
import json
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Protocol

from langchain_core.messages import HumanMessage, SystemMessage

from src.reading_core.runtime_contracts import CurrentReadingProblemCode
from src.reading_runtime import artifacts as runtime_artifacts

from .llm_registry import (
    DEFAULT_RUNTIME_PROFILE_ID,
    LLMProfileConfig,
    LLMProviderConfig,
    LLMRegistryError,
    get_llm_profile,
    get_llm_registry,
)


class ReaderLLMError(RuntimeError):
    """Typed LLM invocation failure surfaced to runtime/eval callers."""

    def __init__(self, message: str, *, problem_code: CurrentReadingProblemCode):
        super().__init__(message)
        self.problem_code = problem_code


class JsonlTraceSink:
    """Append-only JSONL sink used by runtime and eval traces."""

    _LOCKS_GUARD = threading.Lock()
    _PATH_LOCKS: dict[str, threading.Lock] = {}

    def __init__(self, path: Path):
        self.path = path
        key = str(path.resolve())
        with self._LOCKS_GUARD:
            self._lock = self._PATH_LOCKS.setdefault(key, threading.Lock())

    def write(self, payload: Mapping[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(dict(payload), ensure_ascii=False))
                handle.write("\n")


class LLMContractAdapter(Protocol):
    """Provider-contract adapter interface."""

    def invoke(
        self,
        messages: list[Any],
        *,
        provider: LLMProviderConfig,
        profile: LLMProfileConfig,
        api_key: str,
        timeout_seconds: int,
    ) -> Any:
        """Invoke the provider client and return a LangChain-style response."""


@dataclass(frozen=True)
class LLMTraceContext:
    """Trace sink and metadata passed through one invocation scope."""

    standard_sink: JsonlTraceSink | None = None
    debug_sink: JsonlTraceSink | None = None
    mechanism_key: str | None = None
    eval_target: str | None = None
    stage: str | None = None
    node: str | None = None
    debug_enabled: bool = False
    extra: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class LLMInvocationOverrides:
    """Optional per-scope overrides layered over a profile."""

    temperature: float | None = None
    max_tokens: int | None = None
    timeout_seconds: int | None = None
    retry_attempts: int | None = None
    max_concurrency: int | None = None


@dataclass(frozen=True)
class LLMInvocationScopeState:
    """Current scope state inherited by nested project-owned LLM calls."""

    profile_id: str | None = None
    trace_context: LLMTraceContext | None = None
    overrides: LLMInvocationOverrides | None = None


_CURRENT_SCOPE: contextvars.ContextVar[LLMInvocationScopeState | None] = contextvars.ContextVar(
    "reading_companion_llm_scope",
    default=None,
)
_SEMAPHORES_LOCK = threading.Lock()
_PROFILE_SEMAPHORES: dict[tuple[str, int], threading.BoundedSemaphore] = {}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _prompt_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _excerpt(text: str, limit: int = 600) -> str:
    stripped = text.strip()
    if len(stripped) <= limit:
        return stripped
    return stripped[: limit - 3].rstrip() + "..."


def _classify_llm_problem(exc: Exception) -> CurrentReadingProblemCode:
    """Map provider/network failures into one stable runtime problem code."""

    message = str(exc).lower()
    if any(token in message for token in ("timed out", "timeout", "read timeout", "deadline exceeded")):
        return "llm_timeout"
    if any(token in message for token in ("authentication", "unauthorized", "forbidden", "invalid api key", "invalid x-api-key", "missing api key")):
        return "llm_auth"
    if any(token in message for token in ("quota", "insufficient", "billing", "credit balance", "rate limit", "429")):
        return "llm_quota"
    return "network_blocked"


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


class AnthropicContractAdapter:
    """Anthropic-compatible LangChain adapter."""

    def invoke(
        self,
        messages: list[Any],
        *,
        provider: LLMProviderConfig,
        profile: LLMProfileConfig,
        api_key: str,
        timeout_seconds: int,
    ) -> Any:
        try:
            module = importlib.import_module("langchain_anthropic")
        except ModuleNotFoundError as exc:
            raise LLMRegistryError("langchain-anthropic is not installed for anthropic contract usage.") from exc
        client = module.ChatAnthropic(
            base_url=provider.base_url,
            api_key=api_key,
            model=profile.model,
            temperature=profile.temperature,
            max_tokens=profile.max_tokens,
            timeout=timeout_seconds,
        )
        return client.invoke(messages)


class OpenAICompatibleContractAdapter:
    """OpenAI-compatible LangChain adapter."""

    def invoke(
        self,
        messages: list[Any],
        *,
        provider: LLMProviderConfig,
        profile: LLMProfileConfig,
        api_key: str,
        timeout_seconds: int,
    ) -> Any:
        try:
            module = importlib.import_module("langchain_openai")
        except ModuleNotFoundError as exc:
            raise LLMRegistryError("langchain-openai is not installed for openai_compatible contract usage.") from exc
        client = module.ChatOpenAI(
            base_url=provider.base_url,
            api_key=api_key,
            model=profile.model,
            temperature=profile.temperature,
            max_tokens=profile.max_tokens,
            timeout=timeout_seconds,
        )
        return client.invoke(messages)


class GoogleGenAIContractAdapter:
    """Google Generative AI LangChain adapter."""

    def invoke(
        self,
        messages: list[Any],
        *,
        provider: LLMProviderConfig,
        profile: LLMProfileConfig,
        api_key: str,
        timeout_seconds: int,
    ) -> Any:
        try:
            module = importlib.import_module("langchain_google_genai")
        except ModuleNotFoundError as exc:
            raise LLMRegistryError("langchain-google-genai is not installed for google_genai contract usage.") from exc
        client = module.ChatGoogleGenerativeAI(
            model=profile.model,
            google_api_key=api_key,
            temperature=profile.temperature,
            max_output_tokens=profile.max_tokens,
            timeout=timeout_seconds,
        )
        return client.invoke(messages)


CONTRACT_ADAPTERS: dict[str, LLMContractAdapter] = {
    "anthropic": AnthropicContractAdapter(),
    "google_genai": GoogleGenAIContractAdapter(),
    "openai_compatible": OpenAICompatibleContractAdapter(),
}


def _merge_trace_context(base: LLMTraceContext | None, overlay: LLMTraceContext | None) -> LLMTraceContext | None:
    if base is None:
        return overlay
    if overlay is None:
        return base
    return LLMTraceContext(
        standard_sink=overlay.standard_sink or base.standard_sink,
        debug_sink=overlay.debug_sink or base.debug_sink,
        mechanism_key=overlay.mechanism_key or base.mechanism_key,
        eval_target=overlay.eval_target or base.eval_target,
        stage=overlay.stage or base.stage,
        node=overlay.node or base.node,
        debug_enabled=overlay.debug_enabled or base.debug_enabled,
        extra={**base.extra, **overlay.extra},
    )


def _merge_overrides(base: LLMInvocationOverrides | None, overlay: LLMInvocationOverrides | None) -> LLMInvocationOverrides | None:
    if base is None:
        return overlay
    if overlay is None:
        return base
    return LLMInvocationOverrides(
        temperature=overlay.temperature if overlay.temperature is not None else base.temperature,
        max_tokens=overlay.max_tokens if overlay.max_tokens is not None else base.max_tokens,
        timeout_seconds=overlay.timeout_seconds if overlay.timeout_seconds is not None else base.timeout_seconds,
        retry_attempts=overlay.retry_attempts if overlay.retry_attempts is not None else base.retry_attempts,
        max_concurrency=overlay.max_concurrency if overlay.max_concurrency is not None else base.max_concurrency,
    )


@contextlib.contextmanager
def llm_invocation_scope(
    *,
    profile_id: str | None = None,
    trace_context: LLMTraceContext | None = None,
    overrides: LLMInvocationOverrides | None = None,
) -> Any:
    """Layer one shared LLM invocation scope over the current thread/task context."""

    current = _CURRENT_SCOPE.get()
    next_scope = LLMInvocationScopeState(
        profile_id=profile_id or (current.profile_id if current else None),
        trace_context=_merge_trace_context(current.trace_context if current else None, trace_context),
        overrides=_merge_overrides(current.overrides if current else None, overrides),
    )
    token = _CURRENT_SCOPE.set(next_scope)
    try:
        yield next_scope
    finally:
        _CURRENT_SCOPE.reset(token)


def current_llm_scope() -> LLMInvocationScopeState | None:
    """Expose the current invocation scope for tests or thin wrappers."""

    return _CURRENT_SCOPE.get()


def runtime_trace_context(
    output_dir: Path,
    *,
    mechanism_key: str,
    stage: str | None = None,
    node: str | None = None,
    debug_enabled: bool = False,
    extra: Mapping[str, object] | None = None,
) -> LLMTraceContext:
    """Build one runtime-scoped trace context."""

    return LLMTraceContext(
        standard_sink=JsonlTraceSink(runtime_artifacts.llm_standard_trace_file(output_dir)),
        debug_sink=JsonlTraceSink(runtime_artifacts.llm_debug_trace_file(output_dir, mechanism_key)),
        mechanism_key=mechanism_key,
        stage=stage,
        node=node,
        debug_enabled=debug_enabled,
        extra=dict(extra or {}),
    )


def eval_trace_context(
    run_dir: Path,
    *,
    eval_target: str,
    stage: str | None = None,
    node: str | None = None,
    debug_enabled: bool = False,
    extra: Mapping[str, object] | None = None,
) -> LLMTraceContext:
    """Build one eval-run-scoped trace context."""

    trace_dir = run_dir / "llm_traces"
    return LLMTraceContext(
        standard_sink=JsonlTraceSink(trace_dir / "standard.jsonl"),
        debug_sink=JsonlTraceSink(trace_dir / "debug.jsonl"),
        eval_target=eval_target,
        stage=stage,
        node=node,
        debug_enabled=debug_enabled,
        extra=dict(extra or {}),
    )


def _effective_profile(scope: LLMInvocationScopeState | None, explicit_profile_id: str | None) -> LLMProfileConfig:
    profile_id = explicit_profile_id or (scope.profile_id if scope else None) or DEFAULT_RUNTIME_PROFILE_ID
    profile = get_llm_profile(profile_id)
    overrides = scope.overrides if scope else None
    if overrides is None:
        return profile
    return LLMProfileConfig(
        profile_id=profile.profile_id,
        provider_id=profile.provider_id,
        fallback_provider_ids=profile.fallback_provider_ids,
        allow_cross_provider_failover=profile.allow_cross_provider_failover,
        model=profile.model,
        temperature=overrides.temperature if overrides.temperature is not None else profile.temperature,
        max_tokens=overrides.max_tokens if overrides.max_tokens is not None else profile.max_tokens,
        timeout_seconds=overrides.timeout_seconds if overrides.timeout_seconds is not None else profile.timeout_seconds,
        retry_attempts=overrides.retry_attempts if overrides.retry_attempts is not None else profile.retry_attempts,
        max_concurrency=overrides.max_concurrency if overrides.max_concurrency is not None else profile.max_concurrency,
    )


def _resolve_provider_sequence(profile: LLMProfileConfig) -> list[LLMProviderConfig]:
    registry_provider_ids = [profile.provider_id]
    if profile.allow_cross_provider_failover:
        registry_provider_ids.extend(
            provider_id for provider_id in profile.fallback_provider_ids if provider_id not in registry_provider_ids
        )
    providers: list[LLMProviderConfig] = []
    registry = get_llm_registry()
    for provider_id in registry_provider_ids:
        provider = registry.get_provider(provider_id)
        if "*" not in provider.supported_models and profile.model not in provider.supported_models:
            raise LLMRegistryError(
                f"Profile {profile.profile_id} cannot use fallback provider {provider_id} with model {profile.model}."
            )
        providers.append(provider)
    return providers


def _semaphore_for(profile: LLMProfileConfig) -> threading.BoundedSemaphore:
    key = (profile.profile_id, profile.max_concurrency)
    with _SEMAPHORES_LOCK:
        semaphore = _PROFILE_SEMAPHORES.get(key)
        if semaphore is None:
            semaphore = threading.BoundedSemaphore(profile.max_concurrency)
            _PROFILE_SEMAPHORES[key] = semaphore
        return semaphore


def _write_standard_trace(
    trace_context: LLMTraceContext | None,
    payload: Mapping[str, Any],
) -> None:
    if trace_context is not None and trace_context.standard_sink is not None:
        trace_context.standard_sink.write(payload)


def _write_debug_trace(
    trace_context: LLMTraceContext | None,
    payload: Mapping[str, Any],
) -> None:
    if trace_context is not None and trace_context.debug_enabled and trace_context.debug_sink is not None:
        trace_context.debug_sink.write(payload)


def _invoke_response(
    system_prompt: str,
    user_prompt: str,
    *,
    explicit_profile_id: str | None = None,
) -> Any:
    scope = current_llm_scope()
    trace_context = scope.trace_context if scope else None
    profile = _effective_profile(scope, explicit_profile_id)
    providers = _resolve_provider_sequence(profile)
    if not providers:
        raise ReaderLLMError("No providers resolved for LLM invocation.", problem_code="network_blocked")

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]
    call_id = uuid.uuid4().hex
    started_at = _utc_now()
    started_perf = time.perf_counter()
    attempts: list[dict[str, Any]] = []
    final_provider_id = ""
    final_contract = ""
    final_slot_id = ""
    final_problem_code = ""
    last_error: Exception | None = None
    response: Any | None = None

    for round_index in range(1, max(1, profile.retry_attempts) + 1):
        for provider in providers:
            key_slots = provider.resolved_key_pool()
            if not key_slots:
                raise ReaderLLMError(
                    f"Provider {provider.provider_id} has no resolved API keys.",
                    problem_code="llm_auth",
                )
            for key_index, key_slot in enumerate(key_slots, start=1):
                attempt_started = _utc_now()
                attempt_perf = time.perf_counter()
                final_provider_id = provider.provider_id
                final_contract = provider.contract
                final_slot_id = key_slot["slot_id"]
                try:
                    adapter = CONTRACT_ADAPTERS[provider.contract]
                    with _semaphore_for(profile):
                        response = adapter.invoke(
                            messages,
                            provider=provider,
                            profile=profile,
                            api_key=key_slot["api_key"],
                            timeout_seconds=profile.timeout_seconds,
                        )
                    attempt = {
                        "attempt": len(attempts) + 1,
                        "round": round_index,
                        "provider_id": provider.provider_id,
                        "contract": provider.contract,
                        "key_slot_id": key_slot["slot_id"],
                        "status": "ok",
                        "started_at": attempt_started,
                        "completed_at": _utc_now(),
                        "duration_ms": int((time.perf_counter() - attempt_perf) * 1000),
                        "problem_code": "",
                        "error_type": "",
                        "error_message": "",
                    }
                    attempts.append(attempt)
                    duration_ms = int((time.perf_counter() - started_perf) * 1000)
                    standard_payload = {
                        "call_id": call_id,
                        "profile_id": profile.profile_id,
                        "provider_id": provider.provider_id,
                        "contract": provider.contract,
                        "model": profile.model,
                        "mechanism_key": trace_context.mechanism_key if trace_context else "",
                        "eval_target": trace_context.eval_target if trace_context else "",
                        "stage": trace_context.stage if trace_context else "",
                        "node": trace_context.node if trace_context else "",
                        "attempt_count": len(attempts),
                        "key_slot_id": key_slot["slot_id"],
                        "started_at": started_at,
                        "completed_at": attempt["completed_at"],
                        "duration_ms": duration_ms,
                        "status": "ok",
                        "problem_code": "",
                        "fallback": {
                            "used_failover": len(attempts) > 1,
                            "providers_tried": [item["provider_id"] for item in attempts],
                            "key_slots_tried": [item["key_slot_id"] for item in attempts],
                        },
                        **(trace_context.extra if trace_context else {}),
                    }
                    _write_standard_trace(trace_context, standard_payload)
                    _write_debug_trace(
                        trace_context,
                        {
                            **standard_payload,
                            "system_prompt_hash": _prompt_hash(system_prompt),
                            "user_prompt_hash": _prompt_hash(user_prompt),
                            "system_prompt_excerpt": _excerpt(system_prompt),
                            "user_prompt_excerpt": _excerpt(user_prompt),
                            "response_excerpt": _excerpt(response_text(response)),
                            "attempts": attempts,
                        },
                    )
                    return response
                except Exception as exc:  # pragma: no cover - runtime/provider behavior
                    classified = _classify_llm_problem(exc)
                    final_problem_code = classified
                    last_error = exc
                    attempts.append(
                        {
                            "attempt": len(attempts) + 1,
                            "round": round_index,
                            "provider_id": provider.provider_id,
                            "contract": provider.contract,
                            "key_slot_id": key_slot["slot_id"],
                            "status": "error",
                            "started_at": attempt_started,
                            "completed_at": _utc_now(),
                            "duration_ms": int((time.perf_counter() - attempt_perf) * 1000),
                            "problem_code": classified,
                            "error_type": exc.__class__.__name__,
                            "error_message": str(exc),
                        }
                    )
                    if classified in {"llm_auth", "llm_quota"}:
                        continue
                    if round_index >= profile.retry_attempts and key_index >= len(key_slots) and provider is providers[-1]:
                        break
                    time.sleep(min(4.0, 0.5 * (2 ** (round_index - 1))))

    completed_at = _utc_now()
    duration_ms = int((time.perf_counter() - started_perf) * 1000)
    standard_payload = {
        "call_id": call_id,
        "profile_id": profile.profile_id,
        "provider_id": final_provider_id,
        "contract": final_contract,
        "model": profile.model,
        "mechanism_key": trace_context.mechanism_key if trace_context else "",
        "eval_target": trace_context.eval_target if trace_context else "",
        "stage": trace_context.stage if trace_context else "",
        "node": trace_context.node if trace_context else "",
        "attempt_count": len(attempts),
        "key_slot_id": final_slot_id,
        "started_at": started_at,
        "completed_at": completed_at,
        "duration_ms": duration_ms,
        "status": "error",
        "problem_code": final_problem_code or "network_blocked",
        "fallback": {
            "used_failover": len(attempts) > 1,
            "providers_tried": [item["provider_id"] for item in attempts],
            "key_slots_tried": [item["key_slot_id"] for item in attempts],
        },
        **(trace_context.extra if trace_context else {}),
    }
    _write_standard_trace(trace_context, standard_payload)
    _write_debug_trace(
        trace_context,
        {
            **standard_payload,
            "system_prompt_hash": _prompt_hash(system_prompt),
            "user_prompt_hash": _prompt_hash(user_prompt),
            "system_prompt_excerpt": _excerpt(system_prompt),
            "user_prompt_excerpt": _excerpt(user_prompt),
            "attempts": attempts,
        },
    )
    if isinstance(last_error, ReaderLLMError):
        raise last_error
    raise ReaderLLMError(str(last_error or "LLM invocation failed."), problem_code=final_problem_code or "network_blocked")


def invoke_json(system_prompt: str, user_prompt: str, default: Any, *, profile_id: str | None = None) -> Any:
    """Invoke the configured LLM and parse a JSON payload."""

    response = _invoke_response(system_prompt, user_prompt, explicit_profile_id=profile_id)
    return parse_json_payload(response_text(response), default)


def invoke_text(system_prompt: str, user_prompt: str, default: str = "", *, profile_id: str | None = None) -> str:
    """Invoke the configured LLM and return plain text output."""

    response = _invoke_response(system_prompt, user_prompt, explicit_profile_id=profile_id)
    text = response_text(response).strip()
    return text or default


__all__ = [
    "CONTRACT_ADAPTERS",
    "JsonlTraceSink",
    "LLMContractAdapter",
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

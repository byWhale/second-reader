"""Universal provider gateway and trace helpers for project-owned LLM calls."""

from __future__ import annotations

import contextlib
import contextvars
import hashlib
import importlib
import json
import ast
from json import JSONDecodeError
import re
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

from langchain_core.messages import HumanMessage, SystemMessage

from src.config import (
    get_backend_runtime_root,
    get_llm_force_target_id,
    get_llm_force_tier_id,
)
from src.reading_core.runtime_contracts import CurrentReadingProblemCode
from src.reading_runtime import artifacts as runtime_artifacts

from .llm_registry import (
    DEFAULT_RUNTIME_PROFILE_ID,
    LLMProfileConfig,
    LLMProviderConfig,
    LLMRegistryError,
    LLMTargetTierConfig,
    apply_process_profile_concurrency_caps,
    get_llm_profile,
    get_llm_registry,
)

try:  # pragma: no cover - platform import guard
    import fcntl
except ModuleNotFoundError:  # pragma: no cover - non-posix fallback
    fcntl = None


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
    max_output_tokens: int | None = None
    timeout_seconds: int | None = None
    retry_attempts: int | None = None
    max_concurrency: int | None = None


@dataclass(frozen=True)
class LLMInvocationScopeState:
    """Current scope state inherited by nested project-owned LLM calls."""

    profile_id: str | None = None
    trace_context: LLMTraceContext | None = None
    overrides: LLMInvocationOverrides | None = None
    required_stable_concurrency: int | None = None
    pinned_target_id: str | None = None
    pinned_tier_id: str | None = None
    selection_reason: str | None = None
    selection_override_source: str | None = None
    dispatch_reservation: "_TierDispatchReservation | None" = None


_CURRENT_SCOPE: contextvars.ContextVar[LLMInvocationScopeState | None] = contextvars.ContextVar(
    "reading_companion_llm_scope",
    default=None,
)
_SEMAPHORES_LOCK = threading.Lock()
_PROFILE_GATES: dict[tuple[str, str, int], "_DynamicProfileGate"] = {}
_PROVIDER_CONTROLLERS: dict[str, "_AdaptiveProviderController"] = {}
_TIER_DISPATCHERS: dict[tuple[str, str], "_TierDispatchController"] = {}
_QUOTA_STATE_VERSION = 1


@dataclass(frozen=True)
class _QuotaCooldownState:
    provider_id: str
    cooldown_until_epoch: float
    cooldown_seconds: int
    strike_count: int
    updated_at_epoch: float

    @property
    def remaining_seconds(self) -> float:
        return max(0.0, self.cooldown_until_epoch - time.time())


@dataclass(frozen=True)
class _TierDispatchReservation:
    profile_id: str
    tier_id: str
    target_id: str


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
    if any(
        token in message
        for token in (
            "not support model",
            "not support current model",
            "unsupported model",
            "model is not available",
            "model not found",
            "unknown model",
            "authentication",
            "unauthorized",
            "forbidden",
            "invalid api key",
            "invalid x-api-key",
            "missing api key",
            "access denied",
            "permission denied",
            "unsupported model",
            "model_not_found",
            "not support model",
            "does not support model",
            "not supported on your current plan",
            "not available for your account",
            "you do not have access",
            "you don't have access",
            "do not have access",
            "does not have access",
            "doesn't have access",
            "not enabled for your account",
        )
    ):
        return "llm_auth"
    if any(token in message for token in ("quota", "insufficient_quota", "billing", "credit balance", "rate limit", "429")):
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

    stripped = text.strip().lstrip("\ufeff")
    if not stripped:
        return default

    for candidate in _json_parse_candidates(stripped):
        parsed = _parse_json_candidate(candidate)
        if parsed is not _JSON_MALFORMED:
            return parsed

    return default


def _json_parse_candidates(text: str) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()

    def _add(candidate: str) -> None:
        cleaned = candidate.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            candidates.append(cleaned)

    _add(text)
    for match in re.finditer(r"```(?:json)?\s*([\s\S]*?)```", text, flags=re.IGNORECASE):
        _add(match.group(1))
    for candidate in _iter_balanced_json_candidates(text):
        _add(candidate)
    for marker in ("{", "["):
        start = text.find(marker)
        if start != -1:
            _add(text[start:])
    return candidates


def _parse_json_candidate(candidate: str) -> Any:
    decoder = json.JSONDecoder()
    attempts = _json_candidate_variants(candidate)

    for attempt in attempts:
        try:
            return json.loads(attempt)
        except JSONDecodeError:
            pass

        for offset, char in enumerate(attempt):
            if char not in "{[":
                continue
            try:
                parsed, _end = decoder.raw_decode(attempt[offset:])
                return parsed
            except JSONDecodeError:
                continue
        try:
            return ast.literal_eval(_pythonize_json_literals(attempt))
        except (SyntaxError, ValueError):
            continue

    return _JSON_MALFORMED


def _iter_balanced_json_candidates(text: str) -> list[str]:
    candidates: list[str] = []
    for start, char in enumerate(text):
        if char not in "{[":
            continue
        stack = [char]
        quote: str | None = None
        escaped = False
        for end in range(start + 1, len(text)):
            current = text[end]
            if quote is not None:
                if escaped:
                    escaped = False
                elif current == "\\":
                    escaped = True
                elif current == quote:
                    quote = None
                continue
            if current in {'"', "'"}:
                quote = current
                continue
            if current in "{[":
                stack.append(current)
                continue
            if current not in "}]":
                continue
            opener = stack[-1]
            if (opener, current) not in {("{", "}"), ("[", "]")}:
                break
            stack.pop()
            if not stack:
                candidates.append(text[start : end + 1].strip())
                break
    return candidates


def _json_candidate_variants(candidate: str) -> list[str]:
    stripped = candidate.strip().lstrip("\ufeff")
    if stripped.lower().startswith("json"):
        stripped = stripped[4:].lstrip(" \t\r\n:-")

    variants: list[str] = []
    seen: set[str] = set()

    def _add(value: str) -> None:
        cleaned = value.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            variants.append(cleaned)

    _add(stripped)
    _add(_strip_json_trailing_commas(stripped))
    escaped_controls = _escape_controls_in_quoted_strings(stripped)
    _add(escaped_controls)
    _add(_strip_json_trailing_commas(escaped_controls))
    return variants


def _strip_json_trailing_commas(text: str) -> str:
    chars: list[str] = []
    in_string = False
    escaped = False
    index = 0

    while index < len(text):
        char = text[index]
        if in_string:
            chars.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue

        if char == '"':
            in_string = True
            chars.append(char)
            index += 1
            continue

        if char == ",":
            lookahead = index + 1
            while lookahead < len(text) and text[lookahead].isspace():
                lookahead += 1
            if lookahead < len(text) and text[lookahead] in "}]":
                index += 1
                continue

        chars.append(char)
        index += 1

    return "".join(chars)


def _escape_controls_in_quoted_strings(text: str) -> str:
    chars: list[str] = []
    quote: str | None = None
    escaped = False

    for char in text:
        if quote is None:
            if char in {'"', "'"}:
                quote = char
            chars.append(char)
            continue
        if escaped:
            chars.append(char)
            escaped = False
            continue
        if char == "\\":
            chars.append(char)
            escaped = True
            continue
        if char == quote:
            chars.append(char)
            quote = None
            continue
        if char == "\n":
            chars.append("\\n")
            continue
        if char == "\r":
            chars.append("\\r")
            continue
        if char == "\t":
            chars.append("\\t")
            continue
        chars.append(char)

    return "".join(chars)


def _pythonize_json_literals(text: str) -> str:
    replacements = {"true": "True", "false": "False", "null": "None"}
    chars: list[str] = []
    quote: str | None = None
    escaped = False
    index = 0

    while index < len(text):
        char = text[index]
        if quote is not None:
            chars.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            index += 1
            continue
        if char in {'"', "'"}:
            quote = char
            chars.append(char)
            index += 1
            continue
        matched = False
        for source, replacement in replacements.items():
            if text.startswith(source, index):
                left_ok = index == 0 or not (text[index - 1].isalnum() or text[index - 1] == "_")
                right_index = index + len(source)
                right_ok = right_index >= len(text) or not (
                    text[right_index].isalnum() or text[right_index] == "_"
                )
                if left_ok and right_ok:
                    chars.append(replacement)
                    index = right_index
                    matched = True
                    break
        if matched:
            continue
        chars.append(char)
        index += 1

    return "".join(chars)


def _quota_state_dir() -> Path:
    return get_backend_runtime_root() / "state" / "llm_gateway" / "providers"


def _quota_state_path(provider: LLMProviderConfig) -> Path:
    return _quota_state_dir() / f"{provider.provider_id}.json"


def _quota_lock_path(provider: LLMProviderConfig) -> Path:
    return _quota_state_dir() / f"{provider.provider_id}.lock"


@contextlib.contextmanager
def _quota_state_lock(provider: LLMProviderConfig) -> Any:
    lock_path = _quota_lock_path(provider)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _clear_quota_state_locked(provider: LLMProviderConfig) -> None:
    with contextlib.suppress(FileNotFoundError):
        _quota_state_path(provider).unlink()


def _read_quota_state_locked(provider: LLMProviderConfig) -> _QuotaCooldownState | None:
    path = _quota_state_path(provider)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _clear_quota_state_locked(provider)
        return None
    if not isinstance(payload, dict):
        _clear_quota_state_locked(provider)
        return None
    updated_at_epoch = float(payload.get("updated_at_epoch", 0.0) or 0.0)
    if updated_at_epoch <= 0:
        _clear_quota_state_locked(provider)
        return None
    if time.time() - updated_at_epoch > float(provider.quota_state_ttl_seconds):
        _clear_quota_state_locked(provider)
        return None
    try:
        return _QuotaCooldownState(
            provider_id=str(payload.get("provider_id", "") or provider.provider_id),
            cooldown_until_epoch=float(payload.get("cooldown_until_epoch", 0.0) or 0.0),
            cooldown_seconds=max(0, int(payload.get("cooldown_seconds", 0) or 0)),
            strike_count=max(0, int(payload.get("strike_count", 0) or 0)),
            updated_at_epoch=updated_at_epoch,
        )
    except (TypeError, ValueError):
        _clear_quota_state_locked(provider)
        return None


def _write_quota_state_locked(provider: LLMProviderConfig, state: _QuotaCooldownState) -> None:
    path = _quota_state_path(provider)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": _QUOTA_STATE_VERSION,
        "provider_id": state.provider_id,
        "cooldown_until_epoch": state.cooldown_until_epoch,
        "cooldown_seconds": state.cooldown_seconds,
        "strike_count": state.strike_count,
        "updated_at_epoch": state.updated_at_epoch,
        "updated_at": datetime.fromtimestamp(state.updated_at_epoch, timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp_path.replace(path)


def _current_quota_state(provider: LLMProviderConfig) -> _QuotaCooldownState | None:
    with _quota_state_lock(provider):
        return _read_quota_state_locked(provider)


def _quota_wait_seconds(provider: LLMProviderConfig) -> float:
    state = _current_quota_state(provider)
    if state is None:
        return 0.0
    return state.remaining_seconds


def _record_quota_pressure(provider: LLMProviderConfig) -> _QuotaCooldownState:
    now = time.time()
    with _quota_state_lock(provider):
        previous = _read_quota_state_locked(provider)
        previous_strikes = previous.strike_count if previous is not None else 0
        if previous is not None and previous.remaining_seconds > 0:
            strike_count = previous_strikes + 1
        else:
            strike_count = max(1, previous_strikes + 1)
        cooldown_seconds = min(
            provider.quota_cooldown_max_seconds,
            provider.quota_cooldown_base_seconds * (2 ** max(0, strike_count - 1)),
        )
        state = _QuotaCooldownState(
            provider_id=provider.provider_id,
            cooldown_until_epoch=now + float(cooldown_seconds),
            cooldown_seconds=int(cooldown_seconds),
            strike_count=strike_count,
            updated_at_epoch=now,
        )
        _write_quota_state_locked(provider, state)
        return state


def _clear_quota_pressure_if_recovered(provider: LLMProviderConfig) -> None:
    with _quota_state_lock(provider):
        state = _read_quota_state_locked(provider)
        if state is None:
            return
        if state.remaining_seconds <= 0:
            _clear_quota_state_locked(provider)


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
            max_tokens=profile.max_output_tokens,
            timeout=timeout_seconds,
            max_retries=0,
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
            max_tokens=profile.max_output_tokens,
            timeout=timeout_seconds,
            max_retries=0,
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
            max_output_tokens=profile.max_output_tokens,
            timeout=timeout_seconds,
        )
        return client.invoke(messages)


CONTRACT_ADAPTERS: dict[str, LLMContractAdapter] = {
    "anthropic": AnthropicContractAdapter(),
    "google_genai": GoogleGenAIContractAdapter(),
    "openai_compatible": OpenAICompatibleContractAdapter(),
}


class _AdaptiveProviderController:
    """Adaptive provider-wide concurrency controller for same-key parallelism."""

    def __init__(self, provider: LLMProviderConfig):
        self.provider = provider
        self._condition = threading.Condition()
        self._active = 0
        self._current_limit = max(
            provider.min_stable_concurrency,
            min(provider.initial_max_concurrency, provider.probe_max_concurrency),
        )
        self._last_adjustment_at = 0.0
        self._last_pressure_at = 0.0
        self._pressure_events: deque[float] = deque()
        self._key_cursor = 0

    @property
    def current_limit(self) -> int:
        with self._condition:
            return self._current_limit

    def ordered_key_slots(self, key_slots: list[dict[str, str]]) -> list[dict[str, str]]:
        if len(key_slots) <= 1:
            return key_slots
        with self._condition:
            start = self._key_cursor % len(key_slots)
            self._key_cursor += 1
        return key_slots[start:] + key_slots[:start]

    def acquire(self) -> None:
        with self._condition:
            while self._active >= self._current_limit:
                self._condition.wait(timeout=0.25)
            self._active += 1

    def release(self) -> None:
        with self._condition:
            self._active = max(0, self._active - 1)
            self._condition.notify_all()

    def report_success(self) -> None:
        now = time.monotonic()
        with self._condition:
            self._prune_pressure_locked(now)
            if self._current_limit >= self.provider.probe_max_concurrency:
                return
            if now - max(self._last_pressure_at, self._last_adjustment_at) < self.provider.recover_window_seconds:
                return
            self._current_limit = min(self.provider.probe_max_concurrency, self._current_limit + 1)
            self._last_adjustment_at = now
            self._condition.notify_all()

    def report_pressure(self) -> None:
        now = time.monotonic()
        with self._condition:
            self._prune_pressure_locked(now)
            self._pressure_events.append(now)
            should_backoff = len(self._pressure_events) >= 2 or self._current_limit > self.provider.initial_max_concurrency
            if not should_backoff:
                return
            new_limit = max(self.provider.min_stable_concurrency, self._current_limit - 1)
            if new_limit == self._current_limit:
                self._last_pressure_at = now
                return
            self._current_limit = new_limit
            self._last_pressure_at = now
            self._last_adjustment_at = now
            self._pressure_events.clear()
            self._condition.notify_all()

    def _prune_pressure_locked(self, now: float) -> None:
        window = float(self.provider.backoff_window_seconds)
        while self._pressure_events and now - self._pressure_events[0] > window:
            self._pressure_events.popleft()


class _DynamicProfileGate:
    """Profile-specific gate that follows the provider's adaptive stable limit."""

    def __init__(self, profile: LLMProfileConfig, provider_controller: _AdaptiveProviderController):
        self.profile = profile
        self.provider_controller = provider_controller
        self._condition = threading.Condition()
        self._active = 0

    @property
    def current_limit(self) -> int:
        return max(1, min(self.profile.max_concurrency, self.provider_controller.current_limit))

    def acquire(self) -> None:
        with self._condition:
            while self._active >= self.current_limit:
                self._condition.wait(timeout=0.25)
            self._active += 1

    def release(self) -> None:
        with self._condition:
            self._active = max(0, self._active - 1)
            self._condition.notify_all()


class _TierDispatchController:
    """Coordinate reservations across same-tier targets for one profile."""

    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._reservations: dict[str, int] = {}
        self._next_index = 0

    def ordered_target_ids(self, target_ids: tuple[str, ...]) -> tuple[str, ...]:
        if len(target_ids) <= 1:
            return target_ids
        with self._condition:
            start = self._next_index % len(target_ids)
        return target_ids[start:] + target_ids[:start]

    def reserve_target(
        self,
        target_ids: tuple[str, ...],
        *,
        stable_limit_for: Callable[[str], int],
        should_wait: Callable[[], bool],
    ) -> str | None:
        if not target_ids:
            return None
        with self._condition:
            while True:
                start = self._next_index % len(target_ids)
                for offset in range(len(target_ids)):
                    target_id = target_ids[(start + offset) % len(target_ids)]
                    stable_limit = max(0, int(stable_limit_for(target_id)))
                    reserved_count = self._reservations.get(target_id, 0)
                    if stable_limit > reserved_count:
                        self._reservations[target_id] = reserved_count + 1
                        self._next_index = (start + offset + 1) % len(target_ids)
                        return target_id
                if not should_wait():
                    return None
                self._condition.wait(timeout=0.25)

    def release_target(self, target_id: str) -> None:
        with self._condition:
            current = self._reservations.get(target_id, 0)
            if current <= 1:
                self._reservations.pop(target_id, None)
            else:
                self._reservations[target_id] = current - 1
            self._condition.notify_all()


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
        max_output_tokens=(
            overlay.max_output_tokens if overlay.max_output_tokens is not None else base.max_output_tokens
        ),
        timeout_seconds=overlay.timeout_seconds if overlay.timeout_seconds is not None else base.timeout_seconds,
        retry_attempts=overlay.retry_attempts if overlay.retry_attempts is not None else base.retry_attempts,
        max_concurrency=overlay.max_concurrency if overlay.max_concurrency is not None else base.max_concurrency,
    )


def _effective_required_stable_concurrency(*values: int | None) -> int:
    normalized = [max(1, int(value)) for value in values if value is not None]
    return max(normalized) if normalized else 1


def _selected_model_for_provider(profile: LLMProfileConfig, provider: LLMProviderConfig) -> str:
    if profile.model_source == "profile":
        if "*" not in provider.supported_models and profile.model not in provider.supported_models:
            raise LLMRegistryError(
                f"Profile {profile.profile_id} cannot use provider {provider.provider_id} with model {profile.model}."
            )
        return profile.model
    if profile.model and profile.model in provider.supported_models:
        return profile.model
    if "*" in provider.supported_models:
        return profile.model
    if len(provider.supported_models) == 1:
        return provider.supported_models[0]
    raise LLMRegistryError(
        f"Profile {profile.profile_id} cannot resolve one model from provider {provider.provider_id}."
    )


def _pinned_profile_for_target(
    profile: LLMProfileConfig,
    provider: LLMProviderConfig,
    tier: LLMTargetTierConfig,
    *,
    selection_reason: str,
    selection_override_source: str | None = None,
) -> LLMProfileConfig:
    return replace(
        profile,
        provider_id=provider.provider_id,
        fallback_provider_ids=(),
        allow_cross_provider_failover=False,
        model=_selected_model_for_provider(profile, provider),
        selected_target_id=provider.provider_id,
        selected_tier_id=tier.tier_id,
        selection_reason=selection_reason,
        selection_override_source=selection_override_source,
    )


def _resolve_tier(profile: LLMProfileConfig, tier_id: str) -> LLMTargetTierConfig:
    for tier in profile.target_tiers:
        if tier.tier_id == tier_id:
            return tier
    raise LLMRegistryError(f"Profile {profile.profile_id} does not define tier {tier_id}.")


def _resolve_target_membership(profile: LLMProfileConfig, target_id: str) -> tuple[LLMTargetTierConfig, int]:
    for tier in profile.target_tiers:
        if target_id in tier.target_ids:
            return tier, tier.target_ids.index(target_id)
    raise LLMRegistryError(f"Profile {profile.profile_id} does not define target {target_id}.")


def _target_is_reachable(provider: LLMProviderConfig) -> bool:
    return bool(provider.resolved_key_pool())


def _tier_dispatch_controller_for(profile_id: str, tier_id: str) -> _TierDispatchController:
    key = (profile_id, tier_id)
    with _SEMAPHORES_LOCK:
        controller = _TIER_DISPATCHERS.get(key)
        if controller is None:
            controller = _TierDispatchController()
            _TIER_DISPATCHERS[key] = controller
        return controller


def _target_stable_capacity(provider: LLMProviderConfig, *, include_quota_blocked: bool = False) -> int:
    if not _target_is_reachable(provider):
        return 0
    if not include_quota_blocked and _quota_wait_seconds(provider) > 0:
        return 0
    return _provider_controller_for(provider).current_limit


def _tier_target_ids_in_order(profile: LLMProfileConfig, tier: LLMTargetTierConfig) -> tuple[str, ...]:
    if len(tier.target_ids) <= 1:
        return tier.target_ids
    return _tier_dispatch_controller_for(profile.profile_id, tier.tier_id).ordered_target_ids(tier.target_ids)


def _tier_stable_capacity(
    profile: LLMProfileConfig,
    tier: LLMTargetTierConfig,
    *,
    include_quota_blocked: bool = False,
) -> int:
    registry = get_llm_registry()
    return sum(
        _target_stable_capacity(
            registry.get_provider(target_id),
            include_quota_blocked=include_quota_blocked,
        )
        for target_id in tier.target_ids
    )


def _scope_pinned_target_is_usable(profile_id: str | None, pinned_target_id: str | None) -> bool:
    if not profile_id or not pinned_target_id:
        return False
    registry = get_llm_registry()
    try:
        provider = registry.get_provider(pinned_target_id)
    except LLMRegistryError:
        return False
    return _target_is_reachable(provider) and _quota_wait_seconds(provider) <= 0


def _target_meets_threshold(provider: LLMProviderConfig, *, required_stable_concurrency: int) -> bool:
    if _quota_wait_seconds(provider) > 0:
        return False
    return _provider_controller_for(provider).current_limit >= required_stable_concurrency


def _select_target_within_tier(
    profile: LLMProfileConfig,
    tier: LLMTargetTierConfig,
    *,
    required_stable_concurrency: int,
    selection_reason: str,
    selection_override_source: str | None = None,
    allow_threshold_relaxation: bool = False,
    include_quota_blocked: bool = False,
) -> LLMProfileConfig | None:
    registry = get_llm_registry()
    tier_target_ids = _tier_target_ids_in_order(profile, tier)
    tier_capacity = _tier_stable_capacity(profile, tier, include_quota_blocked=include_quota_blocked)
    reachable_profile: LLMProfileConfig | None = None
    for target_id in tier_target_ids:
        provider = registry.get_provider(target_id)
        if not _target_is_reachable(provider):
            continue
        pinned = _pinned_profile_for_target(
            profile,
            provider,
            tier,
            selection_reason=selection_reason,
            selection_override_source=selection_override_source,
        )
        if (
            tier_capacity >= required_stable_concurrency
            and _target_stable_capacity(provider, include_quota_blocked=include_quota_blocked) > 0
        ):
            return pinned
        if (
            allow_threshold_relaxation
            and reachable_profile is None
            and _target_stable_capacity(provider, include_quota_blocked=include_quota_blocked) > 0
        ):
            reachable_profile = pinned
    return reachable_profile


def _reserve_target_within_tier(
    profile: LLMProfileConfig,
    tier: LLMTargetTierConfig,
    *,
    required_stable_concurrency: int,
    selection_reason: str,
    selection_override_source: str | None = None,
) -> tuple[LLMProfileConfig, _TierDispatchReservation] | None:
    if len(tier.target_ids) <= 1:
        return None

    controller = _tier_dispatch_controller_for(profile.profile_id, tier.tier_id)
    registry = get_llm_registry()

    def _stable_limit_for(target_id: str) -> int:
        provider = registry.get_provider(target_id)
        return _target_stable_capacity(provider)

    def _should_wait() -> bool:
        return _tier_stable_capacity(profile, tier) >= required_stable_concurrency

    selected_target_id = controller.reserve_target(
        tier.target_ids,
        stable_limit_for=_stable_limit_for,
        should_wait=_should_wait,
    )
    if selected_target_id is None:
        return None

    provider = registry.get_provider(selected_target_id)
    return (
        _pinned_profile_for_target(
            profile,
            provider,
            tier,
            selection_reason=selection_reason,
            selection_override_source=selection_override_source,
        ),
        _TierDispatchReservation(
            profile_id=profile.profile_id,
            tier_id=tier.tier_id,
            target_id=selected_target_id,
        ),
    )


def _select_profile_target(
    profile: LLMProfileConfig,
    *,
    required_stable_concurrency: int | None = None,
    pinned_target_id: str | None = None,
    pinned_tier_id: str | None = None,
) -> LLMProfileConfig:
    target_override = _clean_text(pinned_target_id)
    tier_override = _clean_text(pinned_tier_id)
    if not target_override and not tier_override:
        target_override = _clean_text(get_llm_force_target_id())
        tier_override = _clean_text(get_llm_force_tier_id())
        override_source = "env" if target_override or tier_override else None
    else:
        override_source = "scope"

    if target_override or tier_override:
        if target_override:
            tier, _ = _resolve_target_membership(profile, target_override)
            if tier_override and tier.tier_id != tier_override:
                raise LLMRegistryError(
                    f"Profile {profile.profile_id} target {target_override} is not in tier {tier_override}."
                )
        else:
            tier = _resolve_tier(profile, tier_override)
            target_override = tier.target_ids[0]
        effective_threshold = _effective_required_stable_concurrency(
            required_stable_concurrency,
            tier.min_required_stable_concurrency,
        )
        selected = _select_target_within_tier(
            profile,
            tier,
            required_stable_concurrency=effective_threshold,
            selection_reason="manual_override",
            selection_override_source=override_source,
            allow_threshold_relaxation=True,
        )
        if selected is None or selected.selected_target_id != target_override:
            registry = get_llm_registry()
            provider = registry.get_provider(target_override)
            if not _target_is_reachable(provider):
                raise LLMRegistryError(
                    f"Profile {profile.profile_id} forced target {target_override} has no resolved credentials."
                )
            selected = _pinned_profile_for_target(
                profile,
                provider,
                tier,
                selection_reason="manual_override",
                selection_override_source=override_source,
            )
        return selected

    reachable_profile: LLMProfileConfig | None = None
    quota_blocked_profile: LLMProfileConfig | None = None
    for tier in profile.target_tiers:
        effective_threshold = _effective_required_stable_concurrency(
            required_stable_concurrency,
            tier.min_required_stable_concurrency,
        )
        selected = _select_target_within_tier(
            profile,
            tier,
            required_stable_concurrency=effective_threshold,
            selection_reason="healthy_tier_selection",
        )
        if selected is not None:
            return selected
        if reachable_profile is None:
            reachable_profile = _select_target_within_tier(
                profile,
                tier,
                required_stable_concurrency=effective_threshold,
                selection_reason="reachable_fallback_selection",
                allow_threshold_relaxation=True,
            )
        if quota_blocked_profile is None:
            quota_blocked_profile = _select_target_within_tier(
                profile,
                tier,
                required_stable_concurrency=effective_threshold,
                selection_reason="quota_cooldown_wait_selection",
                allow_threshold_relaxation=True,
                include_quota_blocked=True,
            )

    if reachable_profile is not None:
        return reachable_profile
    if quota_blocked_profile is not None:
        return quota_blocked_profile
    raise LLMRegistryError(f"Profile {profile.profile_id} has no reachable targets with resolved credentials.")


def _select_scope_profile_target(
    profile: LLMProfileConfig,
    *,
    required_stable_concurrency: int | None = None,
    pinned_target_id: str | None = None,
    pinned_tier_id: str | None = None,
) -> tuple[LLMProfileConfig, _TierDispatchReservation | None]:
    target_override = _clean_text(pinned_target_id)
    tier_override = _clean_text(pinned_tier_id)
    if not target_override and not tier_override:
        target_override = _clean_text(get_llm_force_target_id())
        tier_override = _clean_text(get_llm_force_tier_id())
        override_source = "env" if target_override or tier_override else None
    else:
        override_source = "scope"

    if target_override or tier_override:
        if target_override:
            tier, _ = _resolve_target_membership(profile, target_override)
            if tier_override and tier.tier_id != tier_override:
                raise LLMRegistryError(
                    f"Profile {profile.profile_id} target {target_override} is not in tier {tier_override}."
                )
        else:
            tier = _resolve_tier(profile, tier_override)
            effective_threshold = _effective_required_stable_concurrency(
                required_stable_concurrency,
                tier.min_required_stable_concurrency,
            )
            reserved = _reserve_target_within_tier(
                profile,
                tier,
                required_stable_concurrency=effective_threshold,
                selection_reason="manual_override",
                selection_override_source=override_source,
            )
            if reserved is not None:
                return reserved
            target_override = tier.target_ids[0]

        effective_threshold = _effective_required_stable_concurrency(
            required_stable_concurrency,
            tier.min_required_stable_concurrency,
        )
        selected = _select_target_within_tier(
            profile,
            tier,
            required_stable_concurrency=effective_threshold,
            selection_reason="manual_override",
            selection_override_source=override_source,
            allow_threshold_relaxation=True,
        )
        if selected is None or selected.selected_target_id != target_override:
            registry = get_llm_registry()
            provider = registry.get_provider(target_override)
            if not _target_is_reachable(provider):
                raise LLMRegistryError(
                    f"Profile {profile.profile_id} forced target {target_override} has no resolved credentials."
                )
            selected = _pinned_profile_for_target(
                profile,
                provider,
                tier,
                selection_reason="manual_override",
                selection_override_source=override_source,
            )
        return selected, None

    reachable_profile: LLMProfileConfig | None = None
    quota_blocked_profile: LLMProfileConfig | None = None
    for tier in profile.target_tiers:
        effective_threshold = _effective_required_stable_concurrency(
            required_stable_concurrency,
            tier.min_required_stable_concurrency,
        )
        reserved = _reserve_target_within_tier(
            profile,
            tier,
            required_stable_concurrency=effective_threshold,
            selection_reason="healthy_tier_selection",
        )
        if reserved is not None:
            return reserved
        if len(tier.target_ids) <= 1:
            selected = _select_target_within_tier(
                profile,
                tier,
                required_stable_concurrency=effective_threshold,
                selection_reason="healthy_tier_selection",
            )
            if selected is not None:
                return selected, None
        if reachable_profile is None:
            reachable_profile = _select_target_within_tier(
                profile,
                tier,
                required_stable_concurrency=effective_threshold,
                selection_reason="reachable_fallback_selection",
                allow_threshold_relaxation=True,
            )
        if quota_blocked_profile is None:
            quota_blocked_profile = _select_target_within_tier(
                profile,
                tier,
                required_stable_concurrency=effective_threshold,
                selection_reason="quota_cooldown_wait_selection",
                allow_threshold_relaxation=True,
                include_quota_blocked=True,
            )

    if reachable_profile is not None:
        return reachable_profile, None
    if quota_blocked_profile is not None:
        return quota_blocked_profile, None
    raise LLMRegistryError(f"Profile {profile.profile_id} has no reachable targets with resolved credentials.")


def _apply_profile_overrides(
    profile: LLMProfileConfig,
    overrides: LLMInvocationOverrides | None,
) -> LLMProfileConfig:
    if overrides is None:
        return profile
    return apply_process_profile_concurrency_caps(
        replace(
            profile,
            temperature=overrides.temperature if overrides.temperature is not None else profile.temperature,
            max_output_tokens=(
                overrides.max_output_tokens if overrides.max_output_tokens is not None else profile.max_output_tokens
            ),
            timeout_seconds=overrides.timeout_seconds if overrides.timeout_seconds is not None else profile.timeout_seconds,
            retry_attempts=overrides.retry_attempts if overrides.retry_attempts is not None else profile.retry_attempts,
            max_concurrency=overrides.max_concurrency if overrides.max_concurrency is not None else profile.max_concurrency,
        )
    )


@contextlib.contextmanager
def llm_invocation_scope(
    *,
    profile_id: str | None = None,
    trace_context: LLMTraceContext | None = None,
    overrides: LLMInvocationOverrides | None = None,
    required_stable_concurrency: int | None = None,
    pinned_target_id: str | None = None,
    pinned_tier_id: str | None = None,
) -> Any:
    """Layer one shared LLM invocation scope over the current thread/task context."""

    current = _CURRENT_SCOPE.get()
    next_profile_id = profile_id or (current.profile_id if current else None)
    current_pin_is_usable = _scope_pinned_target_is_usable(
        next_profile_id,
        current.pinned_target_id if current else None,
    )
    inherited_selection = (
        current is not None
        and current.profile_id == next_profile_id
        and current.pinned_target_id is not None
        and current_pin_is_usable
        and pinned_target_id is None
        and pinned_tier_id is None
    )
    next_required_stable_concurrency = _effective_required_stable_concurrency(
        current.required_stable_concurrency if current else None,
        required_stable_concurrency,
    )
    next_scope = LLMInvocationScopeState(
        profile_id=next_profile_id,
        trace_context=_merge_trace_context(current.trace_context if current else None, trace_context),
        overrides=_merge_overrides(current.overrides if current else None, overrides),
        required_stable_concurrency=next_required_stable_concurrency,
        pinned_target_id=current.pinned_target_id if inherited_selection else None,
        pinned_tier_id=current.pinned_tier_id if inherited_selection else None,
        selection_reason=current.selection_reason if inherited_selection else None,
        selection_override_source=current.selection_override_source if inherited_selection else None,
    )
    if next_scope.profile_id and not inherited_selection:
        selected_profile, reservation = _select_scope_profile_target(
            get_llm_profile(next_scope.profile_id),
            required_stable_concurrency=next_required_stable_concurrency,
            pinned_target_id=pinned_target_id,
            pinned_tier_id=pinned_tier_id,
        )
        next_scope = replace(
            next_scope,
            pinned_target_id=selected_profile.selected_target_id,
            pinned_tier_id=selected_profile.selected_tier_id,
            selection_reason=selected_profile.selection_reason,
            selection_override_source=selected_profile.selection_override_source,
            dispatch_reservation=reservation,
        )
    token = _CURRENT_SCOPE.set(next_scope)
    try:
        yield next_scope
    finally:
        _CURRENT_SCOPE.reset(token)
        reservation = next_scope.dispatch_reservation
        if reservation is not None:
            _tier_dispatch_controller_for(reservation.profile_id, reservation.tier_id).release_target(
                reservation.target_id
            )


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
    base_profile = get_llm_profile(profile_id)
    scope_pin_usable = _scope_pinned_target_is_usable(
        profile_id,
        scope.pinned_target_id if scope and scope.profile_id == profile_id else None,
    )
    if scope and scope.profile_id == profile_id and scope.pinned_target_id and scope_pin_usable:
        registry = get_llm_registry()
        provider = registry.get_provider(scope.pinned_target_id)
        if scope.pinned_tier_id:
            tier = _resolve_tier(base_profile, scope.pinned_tier_id)
        else:
            tier, _ = _resolve_target_membership(base_profile, scope.pinned_target_id)
        selected_profile = _pinned_profile_for_target(
            base_profile,
            provider,
            tier,
            selection_reason=scope.selection_reason or "scope_pin",
            selection_override_source=scope.selection_override_source,
        )
    else:
        selected_profile = _select_profile_target(
            base_profile,
            required_stable_concurrency=scope.required_stable_concurrency if scope else None,
            pinned_target_id=(
                scope.pinned_target_id
                if scope and scope.profile_id == profile_id and scope_pin_usable
                else None
            ),
            pinned_tier_id=(
                scope.pinned_tier_id
                if scope and scope.profile_id == profile_id and scope_pin_usable
                else None
            ),
        )
    return _apply_profile_overrides(selected_profile, scope.overrides if scope else None)


def _resolve_provider_sequence(profile: LLMProfileConfig) -> list[LLMProviderConfig]:
    registry = get_llm_registry()
    if profile.selected_target_id:
        provider = registry.get_provider(profile.selected_target_id)
        if provider.provider_id != profile.provider_id:
            raise LLMRegistryError(
                f"Profile {profile.profile_id} pinned target {profile.selected_target_id} does not match provider_id {profile.provider_id}."
            )
        return [provider]
    provider = registry.get_provider(profile.provider_id)
    if "*" not in provider.supported_models and profile.model not in provider.supported_models:
        raise LLMRegistryError(
            f"Profile {profile.profile_id} cannot use provider {profile.provider_id} with model {profile.model}."
        )
    return [provider]


def _selected_provider_for_profile(
    profile_id: str,
    *,
    required_stable_concurrency: int | None = None,
) -> tuple[LLMProfileConfig, LLMProviderConfig]:
    profile = _select_profile_target(
        get_llm_profile(profile_id),
        required_stable_concurrency=required_stable_concurrency,
    )
    registry = get_llm_registry()
    return profile, registry.get_provider(profile.provider_id)


def _provider_controller_for(provider: LLMProviderConfig) -> _AdaptiveProviderController:
    with _SEMAPHORES_LOCK:
        controller = _PROVIDER_CONTROLLERS.get(provider.provider_id)
        if controller is None:
            controller = _AdaptiveProviderController(provider)
            _PROVIDER_CONTROLLERS[provider.provider_id] = controller
        return controller


def _profile_gate_for(profile: LLMProfileConfig, provider_controller: _AdaptiveProviderController) -> _DynamicProfileGate:
    key = (profile.profile_id, provider_controller.provider.provider_id, profile.max_concurrency)
    with _SEMAPHORES_LOCK:
        gate = _PROFILE_GATES.get(key)
        if gate is None:
            gate = _DynamicProfileGate(profile, provider_controller)
            _PROFILE_GATES[key] = gate
        return gate


def get_llm_provider_stable_concurrency(provider_id: str) -> int:
    """Return the current adaptive stable concurrency for one provider."""

    provider = get_llm_registry().get_provider(provider_id)
    return _provider_controller_for(provider).current_limit


def get_llm_profile_stable_concurrency(profile_id: str = DEFAULT_RUNTIME_PROFILE_ID) -> int:
    """Return the current effective stable concurrency for one profile."""

    profile = get_llm_profile(profile_id)
    reachable_capacity = 0
    for tier in profile.target_tiers:
        effective_threshold = _effective_required_stable_concurrency(
            None,
            tier.min_required_stable_concurrency,
        )
        tier_capacity = _tier_stable_capacity(profile, tier)
        if tier_capacity >= effective_threshold and tier_capacity > 0:
            return max(1, min(profile.max_concurrency, tier_capacity))
        if reachable_capacity == 0:
            reachable_capacity = _tier_stable_capacity(profile, tier, include_quota_blocked=True)
    if reachable_capacity > 0:
        return max(1, min(profile.max_concurrency, reachable_capacity))
    return 1


def clear_llm_gateway_runtime_state() -> None:
    """Clear adaptive concurrency runtime state for tests."""

    with _SEMAPHORES_LOCK:
        _PROFILE_GATES.clear()
        _PROVIDER_CONTROLLERS.clear()
        _TIER_DISPATCHERS.clear()
    quota_dir = _quota_state_dir()
    if quota_dir.exists():
        for path in quota_dir.glob("*"):
            with contextlib.suppress(OSError):
                path.unlink()
        with contextlib.suppress(OSError):
            quota_dir.rmdir()


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


_JSON_MALFORMED = object()


def _invoke_response(
    system_prompt: str,
    user_prompt: str,
    *,
    explicit_profile_id: str | None = None,
    expect_json: bool = False,
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
    quota_retry_attempt_count = 0
    quota_wait_budget_remaining_seconds = float(profile.quota_wait_budget_seconds)
    quota_wait_ms_total = 0
    max_rounds = max(1, profile.retry_attempts, profile.quota_retry_attempts + 1)

    def _attempt_payload(
        *,
        round_index: int,
        provider: LLMProviderConfig,
        key_slot_id: str,
        status: str,
        started_at: str,
        started_perf: float,
        problem_code: str = "",
        error_type: str = "",
        error_message: str = "",
        quota_wait_ms_before_attempt: int = 0,
        shared_quota_cooldown_honored: bool = False,
        provider_gate_wait_ms: int = 0,
        profile_gate_wait_ms: int = 0,
    ) -> dict[str, Any]:
        return {
            "attempt": len(attempts) + 1,
            "round": round_index,
            "provider_id": provider.provider_id,
            "contract": provider.contract,
            "key_slot_id": key_slot_id,
            "status": status,
            "started_at": started_at,
            "completed_at": _utc_now(),
            "duration_ms": int((time.perf_counter() - started_perf) * 1000),
            "problem_code": problem_code,
            "error_type": error_type,
            "error_message": error_message,
            "quota_wait_ms_before_attempt": quota_wait_ms_before_attempt,
            "shared_quota_cooldown_honored": shared_quota_cooldown_honored,
            "provider_gate_wait_ms": provider_gate_wait_ms,
            "profile_gate_wait_ms": profile_gate_wait_ms,
        }

    for round_index in range(1, max_rounds + 1):
        if round_index > profile.retry_attempts and quota_retry_attempt_count == 0:
            break
        round_attempted_provider_call = False
        for provider in providers:
            key_slots = provider.resolved_key_pool()
            if not key_slots:
                raise ReaderLLMError(
                    f"Provider {provider.provider_id} has no resolved API keys.",
                    problem_code="llm_auth",
                )
            provider_controller = _provider_controller_for(provider)
            profile_gate = _profile_gate_for(profile, provider_controller)
            ordered_key_slots = provider_controller.ordered_key_slots(key_slots)
            provider_skipped_for_quota = False
            for key_index, key_slot in enumerate(ordered_key_slots, start=1):
                attempt_started = _utc_now()
                attempt_perf = time.perf_counter()
                final_provider_id = provider.provider_id
                final_contract = provider.contract
                final_slot_id = key_slot["slot_id"]
                quota_wait_ms_before_attempt = 0
                shared_quota_cooldown_honored = False
                provider_gate_wait_ms = 0
                profile_gate_wait_ms = 0
                shared_quota_wait_seconds = _quota_wait_seconds(provider)
                if shared_quota_wait_seconds > 0:
                    if quota_retry_attempt_count >= profile.quota_retry_attempts:
                        reason = (
                            f"Provider {provider.provider_id} quota cooldown remains active for "
                            f"{shared_quota_wait_seconds:.1f}s but the quota retry budget is exhausted."
                        )
                        last_error = ReaderLLMError(reason, problem_code="llm_quota")
                        final_problem_code = "llm_quota"
                        attempts.append(
                            _attempt_payload(
                                round_index=round_index,
                                provider=provider,
                                key_slot_id=key_slot["slot_id"],
                                status="error",
                                started_at=attempt_started,
                                started_perf=attempt_perf,
                                problem_code="llm_quota",
                                error_type=last_error.__class__.__name__,
                                error_message=str(last_error),
                            )
                        )
                        provider_skipped_for_quota = True
                        break
                    if shared_quota_wait_seconds > quota_wait_budget_remaining_seconds:
                        reason = (
                            f"Provider {provider.provider_id} quota cooldown remains active for "
                            f"{shared_quota_wait_seconds:.1f}s but only "
                            f"{quota_wait_budget_remaining_seconds:.1f}s of quota wait budget remain."
                        )
                        last_error = ReaderLLMError(reason, problem_code="llm_quota")
                        final_problem_code = "llm_quota"
                        attempts.append(
                            _attempt_payload(
                                round_index=round_index,
                                provider=provider,
                                key_slot_id=key_slot["slot_id"],
                                status="error",
                                started_at=attempt_started,
                                started_perf=attempt_perf,
                                problem_code="llm_quota",
                                error_type=last_error.__class__.__name__,
                                error_message=str(last_error),
                            )
                        )
                        provider_skipped_for_quota = True
                        break
                    time.sleep(shared_quota_wait_seconds)
                    quota_wait_budget_remaining_seconds = max(
                        0.0,
                        quota_wait_budget_remaining_seconds - shared_quota_wait_seconds,
                    )
                    quota_wait_ms_before_attempt = int(round(shared_quota_wait_seconds * 1000))
                    quota_wait_ms_total += quota_wait_ms_before_attempt
                    shared_quota_cooldown_honored = True
                try:
                    round_attempted_provider_call = True
                    adapter = CONTRACT_ADAPTERS[provider.contract]
                    provider_gate_wait_started = time.perf_counter()
                    provider_controller.acquire()
                    provider_gate_wait_ms = int(round((time.perf_counter() - provider_gate_wait_started) * 1000))
                    profile_gate_wait_started = time.perf_counter()
                    profile_gate.acquire()
                    profile_gate_wait_ms = int(round((time.perf_counter() - profile_gate_wait_started) * 1000))
                    try:
                        response = adapter.invoke(
                            messages,
                            provider=provider,
                            profile=profile,
                            api_key=key_slot["api_key"],
                            timeout_seconds=profile.timeout_seconds,
                        )
                    finally:
                        profile_gate.release()
                        provider_controller.release()
                    if expect_json:
                        parsed = parse_json_payload(response_text(response), _JSON_MALFORMED)
                        if parsed is _JSON_MALFORMED:
                            raise RuntimeError("malformed json payload")
                    provider_controller.report_success()
                    _clear_quota_pressure_if_recovered(provider)
                    attempt = _attempt_payload(
                        round_index=round_index,
                        provider=provider,
                        key_slot_id=key_slot["slot_id"],
                        status="ok",
                        started_at=attempt_started,
                        started_perf=attempt_perf,
                        quota_wait_ms_before_attempt=quota_wait_ms_before_attempt,
                        shared_quota_cooldown_honored=shared_quota_cooldown_honored,
                        provider_gate_wait_ms=provider_gate_wait_ms,
                        profile_gate_wait_ms=profile_gate_wait_ms,
                    )
                    attempts.append(attempt)
                    duration_ms = int((time.perf_counter() - started_perf) * 1000)
                    standard_payload = {
                        "call_id": call_id,
                        "profile_id": profile.profile_id,
                        "provider_id": provider.provider_id,
                        "selected_target_id": profile.selected_target_id or provider.provider_id,
                        "selected_tier_id": profile.selected_tier_id or "",
                        "selection_reason": profile.selection_reason or "",
                        "selection_override_source": profile.selection_override_source or "",
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
                        "quota_wait_ms_total": quota_wait_ms_total,
                        "quota_retry_attempt_count": quota_retry_attempt_count,
                        "provider_gate_wait_ms": provider_gate_wait_ms,
                        "profile_gate_wait_ms": profile_gate_wait_ms,
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
                    message = str(exc).lower()
                    if classified in {"llm_timeout", "llm_quota"} or "malformed json payload" in message:
                        provider_controller.report_pressure()
                    if classified == "llm_quota":
                        quota_retry_attempt_count += 1
                        _record_quota_pressure(provider)
                    attempts.append(
                        _attempt_payload(
                            round_index=round_index,
                            provider=provider,
                            key_slot_id=key_slot["slot_id"],
                            status="error",
                            started_at=attempt_started,
                            started_perf=attempt_perf,
                            problem_code=classified,
                            error_type=exc.__class__.__name__,
                            error_message=str(exc),
                            quota_wait_ms_before_attempt=quota_wait_ms_before_attempt,
                            shared_quota_cooldown_honored=shared_quota_cooldown_honored,
                            provider_gate_wait_ms=provider_gate_wait_ms,
                            profile_gate_wait_ms=profile_gate_wait_ms,
                        )
                    )
                    if classified in {"llm_auth", "llm_quota"}:
                        continue
                    if round_index >= profile.retry_attempts and key_index >= len(key_slots) and provider is providers[-1]:
                        break
                    time.sleep(min(4.0, 0.5 * (2 ** (round_index - 1))))
            if provider_skipped_for_quota:
                continue
        if not round_attempted_provider_call and isinstance(last_error, ReaderLLMError) and last_error.problem_code == "llm_quota":
            break
        if round_index >= profile.retry_attempts and final_problem_code not in {"", "llm_quota"}:
            break

    completed_at = _utc_now()
    duration_ms = int((time.perf_counter() - started_perf) * 1000)
    standard_payload = {
        "call_id": call_id,
        "profile_id": profile.profile_id,
        "provider_id": final_provider_id,
        "selected_target_id": profile.selected_target_id or final_provider_id,
        "selected_tier_id": profile.selected_tier_id or "",
        "selection_reason": profile.selection_reason or "",
        "selection_override_source": profile.selection_override_source or "",
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
        "quota_wait_ms_total": quota_wait_ms_total,
        "quota_retry_attempt_count": quota_retry_attempt_count,
        "provider_gate_wait_ms": sum(int(item.get("provider_gate_wait_ms", 0) or 0) for item in attempts),
        "profile_gate_wait_ms": sum(int(item.get("profile_gate_wait_ms", 0) or 0) for item in attempts),
        "error_type": last_error.__class__.__name__ if last_error is not None else "",
        "error_message": str(last_error or ""),
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

    response = _invoke_response(system_prompt, user_prompt, explicit_profile_id=profile_id, expect_json=True)
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
    "clear_llm_gateway_runtime_state",
    "current_llm_scope",
    "eval_trace_context",
    "get_llm_profile_stable_concurrency",
    "get_llm_provider_stable_concurrency",
    "invoke_json",
    "invoke_text",
    "llm_invocation_scope",
    "parse_json_payload",
    "response_text",
    "runtime_trace_context",
]

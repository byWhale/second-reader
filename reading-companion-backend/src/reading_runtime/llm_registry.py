"""Structured provider/profile registry for shared backend LLM invocation."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from src.config import (
    get_llm_config,
    get_llm_max_concurrency,
    get_llm_provider_contract,
    get_llm_registry_json,
    get_llm_registry_path,
    get_llm_retry_attempts,
)


LLMProviderContract = Literal["anthropic", "google_genai", "openai_compatible"]

DEFAULT_RUNTIME_PROFILE_ID = "runtime_reader_default"
DEFAULT_DATASET_REVIEW_PROFILE_ID = "dataset_review_high_trust"
DEFAULT_EVAL_JUDGE_PROFILE_ID = "eval_judge_high_trust"

_ALLOWED_CONTRACTS = {"anthropic", "google_genai", "openai_compatible"}


class LLMRegistryError(RuntimeError):
    """Raised when provider/profile registry configuration is invalid."""


@dataclass(frozen=True)
class LLMProviderConfig:
    """Resolved provider entry from the structured registry."""

    provider_id: str
    contract: LLMProviderContract
    base_url: str | None
    api_key_env: str | None
    key_pool_envs: tuple[str, ...]
    supported_models: tuple[str, ...]
    timeout_seconds: int
    retry_attempts: int
    max_concurrency: int

    def resolved_key_pool(self) -> list[dict[str, str]]:
        """Return the configured key slots that currently resolve to non-empty env values."""

        slots: list[dict[str, str]] = []
        ordered_envs: list[str] = []
        if self.api_key_env:
            ordered_envs.append(self.api_key_env)
        ordered_envs.extend(env for env in self.key_pool_envs if env and env not in ordered_envs)
        for env_name in ordered_envs:
            value = os.getenv(env_name, "").strip()
            if value:
                slots.append({"slot_id": env_name, "api_key": value})
        return slots


@dataclass(frozen=True)
class LLMProfileConfig:
    """Resolved task-level model profile."""

    profile_id: str
    provider_id: str
    fallback_provider_ids: tuple[str, ...]
    allow_cross_provider_failover: bool
    model: str
    temperature: float
    max_tokens: int
    timeout_seconds: int
    retry_attempts: int
    max_concurrency: int


@dataclass(frozen=True)
class LLMRegistry:
    """Resolved provider and profile registry."""

    providers: dict[str, LLMProviderConfig]
    profiles: dict[str, LLMProfileConfig]
    source: str

    def get_provider(self, provider_id: str) -> LLMProviderConfig:
        """Return one provider entry or raise a typed config error."""

        try:
            return self.providers[provider_id]
        except KeyError as exc:
            raise LLMRegistryError(f"Unknown LLM provider id: {provider_id}") from exc

    def get_profile(self, profile_id: str) -> LLMProfileConfig:
        """Return one profile entry or raise a typed config error."""

        try:
            return self.profiles[profile_id]
        except KeyError as exc:
            raise LLMRegistryError(f"Unknown LLM profile id: {profile_id}") from exc


def _env_int(name: str, default: int, *, minimum: int = 1) -> int:
    raw = os.getenv(name, "").strip()
    if raw.lstrip("-").isdigit():
        return max(minimum, int(raw))
    return max(minimum, int(default))


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    try:
        return float(raw)
    except ValueError:
        return float(default)


def _clean_str(value: object) -> str:
    return str(value or "").strip()


def _resolve_model(entry: dict[str, Any], *, env_fallbacks: tuple[str, ...] = ()) -> str:
    model = _clean_str(entry.get("model"))
    if model:
        return model
    model_env = _clean_str(entry.get("model_env"))
    if model_env:
        value = _clean_str(os.getenv(model_env))
        if value:
            return value
    for env_name in env_fallbacks:
        value = _clean_str(os.getenv(env_name))
        if value:
            return value
    raise LLMRegistryError("Profile is missing a configured model or model_env.")


def _load_registry_payload() -> tuple[dict[str, Any], str]:
    raw_json = get_llm_registry_json()
    if raw_json:
        return json.loads(raw_json), "env:LLM_REGISTRY_JSON"

    raw_path = get_llm_registry_path()
    if raw_path:
        path = Path(raw_path).expanduser().resolve()
        if not path.exists():
            raise LLMRegistryError(f"LLM registry path does not exist: {path}")
        return json.loads(path.read_text(encoding="utf-8")), str(path)

    return _legacy_registry_payload(), "legacy_env"


def _legacy_registry_payload() -> dict[str, Any]:
    """Build a backward-compatible registry from the legacy single-provider env shape."""

    legacy = get_llm_config()
    provider_contract = get_llm_provider_contract()
    if provider_contract not in _ALLOWED_CONTRACTS:
        raise LLMRegistryError(f"Unsupported legacy LLM provider contract: {provider_contract}")

    provider = {
        "provider_id": "legacy_default",
        "contract": provider_contract,
        "base_url": legacy["base_url"],
        "api_key_env": "LLM_API_KEY",
        "supported_models": ["*"],
        "timeout_seconds": 120,
        "retry_attempts": get_llm_retry_attempts(),
        "max_concurrency": get_llm_max_concurrency(),
    }
    return {
        "providers": [provider],
        "profiles": [
            {
                "profile_id": DEFAULT_RUNTIME_PROFILE_ID,
                "provider_id": "legacy_default",
                "model_env": "LLM_MODEL",
                "temperature": _env_float("LLM_RUNTIME_TEMPERATURE", 0.2),
                "max_tokens": _env_int("LLM_RUNTIME_MAX_TOKENS", 4096),
                "timeout_seconds": _env_int("LLM_RUNTIME_TIMEOUT_SECONDS", 120),
                "retry_attempts": get_llm_retry_attempts(),
                "max_concurrency": get_llm_max_concurrency(),
            },
            {
                "profile_id": DEFAULT_DATASET_REVIEW_PROFILE_ID,
                "provider_id": "legacy_default",
                "model_env": "LLM_DATASET_REVIEW_MODEL",
                "temperature": _env_float("LLM_DATASET_REVIEW_TEMPERATURE", 0.2),
                "max_tokens": _env_int("LLM_DATASET_REVIEW_MAX_TOKENS", 4096),
                "timeout_seconds": _env_int("LLM_DATASET_REVIEW_TIMEOUT_SECONDS", 120),
                "retry_attempts": _env_int("LLM_DATASET_REVIEW_RETRY_ATTEMPTS", get_llm_retry_attempts()),
                "max_concurrency": _env_int("LLM_DATASET_REVIEW_MAX_CONCURRENCY", get_llm_max_concurrency()),
            },
            {
                "profile_id": DEFAULT_EVAL_JUDGE_PROFILE_ID,
                "provider_id": "legacy_default",
                "model_env": "LLM_EVAL_JUDGE_MODEL",
                "temperature": _env_float("LLM_EVAL_JUDGE_TEMPERATURE", 0.2),
                "max_tokens": _env_int("LLM_EVAL_JUDGE_MAX_TOKENS", 4096),
                "timeout_seconds": _env_int("LLM_EVAL_JUDGE_TIMEOUT_SECONDS", 120),
                "retry_attempts": _env_int("LLM_EVAL_JUDGE_RETRY_ATTEMPTS", get_llm_retry_attempts()),
                "max_concurrency": _env_int("LLM_EVAL_JUDGE_MAX_CONCURRENCY", get_llm_max_concurrency()),
            },
        ],
    }


def _parse_provider(entry: Any) -> LLMProviderConfig:
    if not isinstance(entry, dict):
        raise LLMRegistryError("Provider entry must be an object.")
    provider_id = _clean_str(entry.get("provider_id"))
    if not provider_id:
        raise LLMRegistryError("Provider entry is missing provider_id.")
    contract = _clean_str(entry.get("contract")).lower()
    if contract not in _ALLOWED_CONTRACTS:
        raise LLMRegistryError(f"Provider {provider_id} has unsupported contract: {contract}")
    key_pool_envs = tuple(
        env_name
        for env_name in (_clean_str(item) for item in entry.get("key_pool_envs", []))
        if env_name
    )
    supported_models = tuple(
        item for item in (_clean_str(item) for item in entry.get("supported_models", [])) if item
    ) or ("*",)
    return LLMProviderConfig(
        provider_id=provider_id,
        contract=contract,  # type: ignore[arg-type]
        base_url=_clean_str(entry.get("base_url")) or None,
        api_key_env=_clean_str(entry.get("api_key_env")) or None,
        key_pool_envs=key_pool_envs,
        supported_models=supported_models,
        timeout_seconds=max(1, int(entry.get("timeout_seconds", 120) or 120)),
        retry_attempts=max(1, int(entry.get("retry_attempts", get_llm_retry_attempts()) or get_llm_retry_attempts())),
        max_concurrency=max(1, int(entry.get("max_concurrency", get_llm_max_concurrency()) or get_llm_max_concurrency())),
    )


def _parse_profile(entry: Any, providers: dict[str, LLMProviderConfig]) -> LLMProfileConfig:
    if not isinstance(entry, dict):
        raise LLMRegistryError("Profile entry must be an object.")
    profile_id = _clean_str(entry.get("profile_id"))
    provider_id = _clean_str(entry.get("provider_id"))
    if not profile_id:
        raise LLMRegistryError("Profile entry is missing profile_id.")
    if not provider_id:
        raise LLMRegistryError(f"Profile {profile_id} is missing provider_id.")
    provider = providers.get(provider_id)
    if provider is None:
        raise LLMRegistryError(f"Profile {profile_id} refers to unknown provider {provider_id}.")

    env_fallbacks: tuple[str, ...]
    if profile_id == DEFAULT_DATASET_REVIEW_PROFILE_ID:
        env_fallbacks = ("LLM_DATASET_REVIEW_MODEL", "LLM_MODEL")
    elif profile_id == DEFAULT_EVAL_JUDGE_PROFILE_ID:
        env_fallbacks = ("LLM_EVAL_JUDGE_MODEL", "LLM_MODEL")
    else:
        env_fallbacks = ("LLM_MODEL",)

    model = _resolve_model(entry, env_fallbacks=env_fallbacks)
    if "*" not in provider.supported_models and model not in provider.supported_models:
        raise LLMRegistryError(
            f"Profile {profile_id} requests model {model}, which is not listed in provider {provider_id} supported_models."
        )

    fallback_provider_ids = tuple(
        item for item in (_clean_str(item) for item in entry.get("fallback_provider_ids", [])) if item
    )
    for fallback_provider_id in fallback_provider_ids:
        if fallback_provider_id not in providers:
            raise LLMRegistryError(
                f"Profile {profile_id} refers to unknown fallback provider {fallback_provider_id}."
            )

    return LLMProfileConfig(
        profile_id=profile_id,
        provider_id=provider_id,
        fallback_provider_ids=fallback_provider_ids,
        allow_cross_provider_failover=bool(entry.get("allow_cross_provider_failover", False)),
        model=model,
        temperature=float(entry.get("temperature", 0.2) or 0.2),
        max_tokens=max(1, int(entry.get("max_tokens", 4096) or 4096)),
        timeout_seconds=max(1, int(entry.get("timeout_seconds", provider.timeout_seconds) or provider.timeout_seconds)),
        retry_attempts=max(1, int(entry.get("retry_attempts", provider.retry_attempts) or provider.retry_attempts)),
        max_concurrency=max(1, int(entry.get("max_concurrency", provider.max_concurrency) or provider.max_concurrency)),
    )


@lru_cache()
def get_llm_registry() -> LLMRegistry:
    """Return the resolved provider/profile registry."""

    payload, source = _load_registry_payload()
    if not isinstance(payload, dict):
        raise LLMRegistryError("LLM registry payload must be a JSON object.")

    provider_entries = payload.get("providers", [])
    if not isinstance(provider_entries, list) or not provider_entries:
        raise LLMRegistryError("LLM registry must define at least one provider.")
    providers: dict[str, LLMProviderConfig] = {}
    for entry in provider_entries:
        provider = _parse_provider(entry)
        providers[provider.provider_id] = provider

    profile_entries = payload.get("profiles", [])
    if not isinstance(profile_entries, list) or not profile_entries:
        raise LLMRegistryError("LLM registry must define at least one profile.")
    profiles: dict[str, LLMProfileConfig] = {}
    for entry in profile_entries:
        profile = _parse_profile(entry, providers)
        profiles[profile.profile_id] = profile

    for required_profile in (
        DEFAULT_RUNTIME_PROFILE_ID,
        DEFAULT_DATASET_REVIEW_PROFILE_ID,
        DEFAULT_EVAL_JUDGE_PROFILE_ID,
    ):
        if required_profile not in profiles:
            raise LLMRegistryError(f"LLM registry is missing required profile: {required_profile}")

    return LLMRegistry(providers=providers, profiles=profiles, source=source)


def get_llm_profile(profile_id: str = DEFAULT_RUNTIME_PROFILE_ID) -> LLMProfileConfig:
    """Return one resolved profile."""

    return get_llm_registry().get_profile(profile_id)


def get_llm_profile_max_concurrency(profile_id: str = DEFAULT_RUNTIME_PROFILE_ID) -> int:
    """Return the bounded in-flight limit for one profile."""

    return get_llm_profile(profile_id).max_concurrency


def clear_llm_registry_cache() -> None:
    """Clear cached registry state for tests or dynamic env reloading."""

    get_llm_registry.cache_clear()


__all__ = [
    "DEFAULT_DATASET_REVIEW_PROFILE_ID",
    "DEFAULT_EVAL_JUDGE_PROFILE_ID",
    "DEFAULT_RUNTIME_PROFILE_ID",
    "LLMProfileConfig",
    "LLMProviderConfig",
    "LLMProviderContract",
    "LLMRegistry",
    "LLMRegistryError",
    "clear_llm_registry_cache",
    "get_llm_profile",
    "get_llm_profile_max_concurrency",
    "get_llm_registry",
]

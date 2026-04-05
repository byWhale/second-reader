"""Structured provider/profile registry for shared backend LLM invocation."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from src.config import (
    get_llm_config,
    get_llm_max_concurrency,
    get_llm_profile_bindings_json,
    get_llm_profile_bindings_path,
    get_llm_provider_contract,
    get_llm_registry_json,
    get_llm_registry_path,
    get_llm_retry_attempts,
    get_llm_targets_json,
    get_llm_targets_path,
)


LLMProviderContract = Literal["anthropic", "google_genai", "openai_compatible"]
LLMProfileModelSource = Literal["profile", "selected_target"]

DEFAULT_RUNTIME_PROFILE_ID = "runtime_reader_default"
DEFAULT_DATASET_REVIEW_PROFILE_ID = "dataset_review_high_trust"
DEFAULT_EVAL_JUDGE_PROFILE_ID = "eval_judge_high_trust"
BACKEND_ROOT = Path(__file__).resolve().parents[2]

_ALLOWED_CONTRACTS = {"anthropic", "google_genai", "openai_compatible"}
_TARGET_PROVIDER_OPTIONAL_FIELDS = (
    "timeout_seconds",
    "retry_attempts",
    "max_concurrency",
    "initial_max_concurrency",
    "probe_max_concurrency",
    "min_stable_concurrency",
    "backoff_window_seconds",
    "recover_window_seconds",
    "quota_cooldown_base_seconds",
    "quota_cooldown_max_seconds",
    "quota_state_ttl_seconds",
)
_PROFILE_OPTIONAL_FIELDS = (
    "temperature",
    "max_output_tokens",
    "timeout_seconds",
    "retry_attempts",
    "max_concurrency",
    "default_burst_concurrency",
    "quota_retry_attempts",
    "quota_wait_budget_seconds",
)
_ALLOWED_PROFILE_MODEL_SOURCES = {"profile", "selected_target"}
_PROCESS_PROFILE_CONCURRENCY_CAP_ENV_BY_PROFILE = {
    DEFAULT_RUNTIME_PROFILE_ID: "LLM_PROCESS_RUNTIME_PROFILE_MAX_CONCURRENCY",
    DEFAULT_DATASET_REVIEW_PROFILE_ID: "LLM_PROCESS_DATASET_REVIEW_PROFILE_MAX_CONCURRENCY",
    DEFAULT_EVAL_JUDGE_PROFILE_ID: "LLM_PROCESS_EVAL_JUDGE_PROFILE_MAX_CONCURRENCY",
}


class LLMRegistryError(RuntimeError):
    """Raised when provider/profile registry configuration is invalid."""


@dataclass(frozen=True)
class LLMKeySlot:
    """One resolved-or-resolvable API-key slot within a provider pool."""

    slot_id: str
    api_key: str | None = None
    api_key_env: str | None = None

    def resolve_api_key(self) -> str | None:
        """Return the direct or env-backed API key when one is available."""

        direct_value = (self.api_key or "").strip()
        if direct_value:
            return direct_value
        env_name = (self.api_key_env or "").strip()
        if not env_name:
            return None
        env_value = os.getenv(env_name, "").strip()
        return env_value or None


@dataclass(frozen=True)
class LLMProviderConfig:
    """Resolved provider entry from the structured registry."""

    provider_id: str
    contract: LLMProviderContract
    base_url: str | None
    key_slots: tuple[LLMKeySlot, ...]
    supported_models: tuple[str, ...]
    timeout_seconds: int
    retry_attempts: int
    max_concurrency: int
    initial_max_concurrency: int
    probe_max_concurrency: int
    min_stable_concurrency: int
    backoff_window_seconds: int
    recover_window_seconds: int
    quota_cooldown_base_seconds: int
    quota_cooldown_max_seconds: int
    quota_state_ttl_seconds: int

    def resolved_key_pool(self) -> list[dict[str, str]]:
        """Return the configured key slots that currently resolve to non-empty values."""

        slots: list[dict[str, str]] = []
        for slot in self.key_slots:
            api_key = slot.resolve_api_key()
            if api_key:
                slots.append({"slot_id": slot.slot_id, "api_key": api_key})
        return slots


@dataclass(frozen=True)
class LLMProfileConfig:
    """Resolved task-level model profile."""

    profile_id: str
    provider_id: str
    fallback_provider_ids: tuple[str, ...]
    allow_cross_provider_failover: bool
    model_source: LLMProfileModelSource
    target_tiers: tuple["LLMTargetTierConfig", ...]
    model: str
    temperature: float
    max_output_tokens: int
    timeout_seconds: int
    retry_attempts: int
    max_concurrency: int
    default_burst_concurrency: int
    quota_retry_attempts: int
    quota_wait_budget_seconds: int
    selected_target_id: str | None = None
    selected_tier_id: str | None = None
    selection_reason: str | None = None
    selection_override_source: str | None = None


@dataclass(frozen=True)
class LLMTargetTierConfig:
    """Ordered target tier used to select one concrete provider/model at scope start."""

    tier_id: str
    target_ids: tuple[str, ...]
    min_required_stable_concurrency: int = 1


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


def _optional_env_int(name: str) -> int | None:
    raw = os.getenv(name, "").strip()
    if not raw:
        return None
    try:
        return max(1, int(raw))
    except ValueError:
        return None


def _clean_str(value: object) -> str:
    return str(value or "").strip()


def _require_text(entry: dict[str, Any], key: str, *, context: str) -> str:
    value = _clean_str(entry.get(key))
    if not value:
        raise LLMRegistryError(f"{context} is missing {key}.")
    return value


def _copy_present_fields(source: dict[str, Any], field_names: tuple[str, ...]) -> dict[str, Any]:
    copied: dict[str, Any] = {}
    for field_name in field_names:
        value = source.get(field_name)
        if value is not None:
            copied[field_name] = value
    return copied


def _clean_str_list(value: Any, *, context: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise LLMRegistryError(f"{context} must be a list.")
    return [item for item in (_clean_str(item) for item in value) if item]


def _require_int(
    entry: dict[str, Any],
    key: str,
    *,
    context: str,
    default: int | None = None,
    minimum: int = 1,
) -> int:
    raw_value = entry.get(key, default)
    if raw_value is None:
        raise LLMRegistryError(f"{context} is missing {key}.")
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise LLMRegistryError(f"{context} has invalid integer {key}: {raw_value!r}.") from exc
    return max(minimum, value)


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


def _default_quota_retry_attempts(profile_id: str) -> int:
    if profile_id == DEFAULT_RUNTIME_PROFILE_ID:
        return 2
    if profile_id in {DEFAULT_DATASET_REVIEW_PROFILE_ID, DEFAULT_EVAL_JUDGE_PROFILE_ID}:
        return 6
    return 3


def _default_quota_wait_budget_seconds(profile_id: str) -> int:
    if profile_id == DEFAULT_RUNTIME_PROFILE_ID:
        return 25
    if profile_id in {DEFAULT_DATASET_REVIEW_PROFILE_ID, DEFAULT_EVAL_JUDGE_PROFILE_ID}:
        return 180
    return 60


def _load_json_env(raw_json: str, *, env_name: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise LLMRegistryError(f"{env_name} does not contain valid JSON.") from exc
    if not isinstance(payload, dict):
        raise LLMRegistryError(f"{env_name} must contain a JSON object.")
    return payload


def _load_json_path(raw_path: str, *, env_name: str) -> tuple[dict[str, Any], Path]:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = (BACKEND_ROOT / path).resolve()
    else:
        path = path.resolve()
    if not path.exists():
        raise LLMRegistryError(f"{env_name} path does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LLMRegistryError(f"{env_name} path does not contain valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise LLMRegistryError(f"{env_name} path must contain a JSON object: {path}")
    return payload, path


def _compile_target_key_slot(entry: Any, *, target_id: str) -> dict[str, str]:
    if not isinstance(entry, dict):
        raise LLMRegistryError(f"Target {target_id} credential entry must be an object.")
    credential_id = _require_text(entry, "credential_id", context=f"Target {target_id} credential")
    api_key = _clean_str(entry.get("api_key"))
    api_key_env = _clean_str(entry.get("api_key_env"))
    if bool(api_key) == bool(api_key_env):
        raise LLMRegistryError(
            f"Target {target_id} credential {credential_id} must define exactly one of api_key or api_key_env."
        )
    compiled = {"slot_id": credential_id}
    if api_key:
        compiled["api_key"] = api_key
    else:
        compiled["api_key_env"] = api_key_env
    return compiled


def _compile_target_entry(entry: Any) -> dict[str, Any]:
    if not isinstance(entry, dict):
        raise LLMRegistryError("Target entry must be an object.")
    target_id = _require_text(entry, "target_id", context="Target entry")
    contract = _require_text(entry, "contract", context=f"Target {target_id}").lower()
    if contract not in _ALLOWED_CONTRACTS:
        raise LLMRegistryError(f"Target {target_id} has unsupported contract: {contract}")
    base_url = _require_text(entry, "base_url", context=f"Target {target_id}")
    model = _require_text(entry, "model", context=f"Target {target_id}")
    raw_credentials = entry.get("credentials", [])
    if not isinstance(raw_credentials, list) or not raw_credentials:
        raise LLMRegistryError(f"Target {target_id} must define at least one credential.")

    key_slots: list[dict[str, str]] = []
    seen_credential_ids: set[str] = set()
    for raw_credential in raw_credentials:
        key_slot = _compile_target_key_slot(raw_credential, target_id=target_id)
        slot_id = key_slot["slot_id"]
        if slot_id in seen_credential_ids:
            raise LLMRegistryError(f"Target {target_id} reuses credential_id {slot_id}.")
        seen_credential_ids.add(slot_id)
        key_slots.append(key_slot)

    provider_entry: dict[str, Any] = {
        "provider_id": target_id,
        "contract": contract,
        "base_url": base_url,
        "key_slots": key_slots,
        "supported_models": [model],
    }
    provider_entry.update(_copy_present_fields(entry, _TARGET_PROVIDER_OPTIONAL_FIELDS))
    return {
        "target_id": target_id,
        "enabled": bool(entry.get("enabled", True)),
        "model": model,
        "provider_entry": provider_entry,
    }


def _compile_profile_binding_tiers(
    entry: dict[str, Any],
    *,
    profile_id: str,
    compiled_targets: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], str]:
    raw_target_tiers = entry.get("target_tiers")
    if raw_target_tiers is not None:
        if "target_id" in entry or "fallback_target_ids" in entry:
            raise LLMRegistryError(
                f"Profile {profile_id} cannot mix target_tiers with target_id or fallback_target_ids."
            )
        if not isinstance(raw_target_tiers, list) or not raw_target_tiers:
            raise LLMRegistryError(f"Profile {profile_id} target_tiers must be a non-empty list.")
        compiled_tiers: list[dict[str, Any]] = []
        seen_tier_ids: set[str] = set()
        seen_target_ids: set[str] = set()
        for raw_tier in raw_target_tiers:
            if not isinstance(raw_tier, dict):
                raise LLMRegistryError(f"Profile {profile_id} target tier entry must be an object.")
            tier_id = _require_text(raw_tier, "tier_id", context=f"Profile {profile_id} tier")
            if tier_id in seen_tier_ids:
                raise LLMRegistryError(f"Profile {profile_id} reuses tier_id {tier_id}.")
            seen_tier_ids.add(tier_id)
            target_ids = _clean_str_list(
                raw_tier.get("target_ids"),
                context=f"Profile {profile_id} tier {tier_id} target_ids",
            )
            if not target_ids:
                raise LLMRegistryError(
                    f"Profile {profile_id} tier {tier_id} must define at least one target_id."
                )
            ordered_target_ids: list[str] = []
            tier_seen_ids: set[str] = set()
            for target_id in target_ids:
                if target_id in tier_seen_ids:
                    raise LLMRegistryError(
                        f"Profile {profile_id} tier {tier_id} reuses target_id {target_id}."
                    )
                if target_id in seen_target_ids:
                    raise LLMRegistryError(
                        f"Profile {profile_id} reuses target_id {target_id} across multiple tiers."
                    )
                tier_seen_ids.add(target_id)
                seen_target_ids.add(target_id)
                target = compiled_targets.get(target_id)
                if target is None:
                    raise LLMRegistryError(
                        f"Profile {profile_id} refers to unknown target_id {target_id} in tier {tier_id}."
                    )
                if not target["enabled"]:
                    raise LLMRegistryError(
                        f"Profile {profile_id} refers to disabled target_id {target_id} in tier {tier_id}."
                    )
                ordered_target_ids.append(target_id)
            compiled_tiers.append(
                {
                    "tier_id": tier_id,
                    "target_ids": ordered_target_ids,
                    "min_required_stable_concurrency": _require_int(
                        raw_tier,
                        "min_required_stable_concurrency",
                        context=f"Profile {profile_id} tier {tier_id}",
                        default=1,
                        minimum=1,
                    ),
                }
            )
        primary_target_id = compiled_tiers[0]["target_ids"][0]
        return compiled_tiers, primary_target_id

    target_id = _require_text(entry, "target_id", context=f"Profile {profile_id}")
    target = compiled_targets.get(target_id)
    if target is None:
        raise LLMRegistryError(f"Profile {profile_id} refers to unknown target_id {target_id}.")
    if not target["enabled"]:
        raise LLMRegistryError(f"Profile {profile_id} refers to disabled target_id {target_id}.")

    raw_fallback_target_ids = _clean_str_list(
        entry.get("fallback_target_ids"),
        context=f"Profile {profile_id} fallback_target_ids",
    )
    fallback_target_ids: list[str] = []
    seen_fallback_ids: set[str] = set()
    for fallback_target_id in raw_fallback_target_ids:
        if fallback_target_id == target_id or fallback_target_id in seen_fallback_ids:
            continue
        fallback_target = compiled_targets.get(fallback_target_id)
        if fallback_target is None:
            raise LLMRegistryError(
                f"Profile {profile_id} refers to unknown fallback target_id {fallback_target_id}."
            )
        if not fallback_target["enabled"]:
            raise LLMRegistryError(
                f"Profile {profile_id} refers to disabled fallback target_id {fallback_target_id}."
            )
        seen_fallback_ids.add(fallback_target_id)
        fallback_target_ids.append(fallback_target_id)

    compiled_tiers = [{"tier_id": "primary", "target_ids": [target_id], "min_required_stable_concurrency": 1}]
    if fallback_target_ids:
        compiled_tiers.append(
            {
                "tier_id": "fallback",
                "target_ids": fallback_target_ids,
                "min_required_stable_concurrency": 1,
            }
        )
    return compiled_tiers, target_id


def _compile_profile_binding_entry(entry: Any, *, compiled_targets: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(entry, dict):
        raise LLMRegistryError("Profile binding entry must be an object.")
    profile_id = _require_text(entry, "profile_id", context="Profile binding")
    if "max" "_tokens" in entry:
        raise LLMRegistryError(
            f"Profile {profile_id} uses the retired output-limit field; use max_output_tokens."
        )
    compiled_tiers, primary_target_id = _compile_profile_binding_tiers(
        entry,
        profile_id=profile_id,
        compiled_targets=compiled_targets,
    )
    primary_target = compiled_targets[primary_target_id]

    compiled_profile: dict[str, Any] = {
        "profile_id": profile_id,
        "provider_id": primary_target_id,
        "model": primary_target["model"],
        "model_source": "selected_target",
        "target_tiers": compiled_tiers,
    }
    compiled_profile.update(_copy_present_fields(entry, _PROFILE_OPTIONAL_FIELDS))
    return compiled_profile


def _compile_target_bindings_payload(
    targets_payload: dict[str, Any],
    bindings_payload: dict[str, Any],
) -> dict[str, Any]:
    raw_targets = targets_payload.get("targets", [])
    if not isinstance(raw_targets, list) or not raw_targets:
        raise LLMRegistryError("LLM targets payload must define at least one target.")

    compiled_targets: dict[str, dict[str, Any]] = {}
    providers: list[dict[str, Any]] = []
    for raw_target in raw_targets:
        compiled_target = _compile_target_entry(raw_target)
        target_id = compiled_target["target_id"]
        if target_id in compiled_targets:
            raise LLMRegistryError(f"LLM targets payload reuses target_id {target_id}.")
        compiled_targets[target_id] = compiled_target
        if compiled_target["enabled"]:
            providers.append(compiled_target["provider_entry"])

    if not providers:
        raise LLMRegistryError("LLM targets payload must define at least one enabled target.")

    raw_profiles = bindings_payload.get("profiles", [])
    if not isinstance(raw_profiles, list) or not raw_profiles:
        raise LLMRegistryError("LLM profile bindings payload must define at least one profile.")

    profiles: list[dict[str, Any]] = []
    seen_profile_ids: set[str] = set()
    for raw_profile in raw_profiles:
        compiled_profile = _compile_profile_binding_entry(raw_profile, compiled_targets=compiled_targets)
        profile_id = compiled_profile["profile_id"]
        if profile_id in seen_profile_ids:
            raise LLMRegistryError(f"LLM profile bindings payload reuses profile_id {profile_id}.")
        seen_profile_ids.add(profile_id)
        profiles.append(compiled_profile)

    return {"providers": providers, "profiles": profiles}


def _load_registry_payload() -> tuple[dict[str, Any], str]:
    raw_targets_json = get_llm_targets_json()
    raw_bindings_json = get_llm_profile_bindings_json()
    if raw_targets_json or raw_bindings_json:
        if not raw_targets_json or not raw_bindings_json:
            raise LLMRegistryError(
                "LLM_TARGETS_JSON and LLM_PROFILE_BINDINGS_JSON must be set together."
            )
        targets_payload = _load_json_env(raw_targets_json, env_name="LLM_TARGETS_JSON")
        bindings_payload = _load_json_env(raw_bindings_json, env_name="LLM_PROFILE_BINDINGS_JSON")
        return (
            _compile_target_bindings_payload(targets_payload, bindings_payload),
            "env:LLM_TARGETS_JSON+LLM_PROFILE_BINDINGS_JSON",
        )

    raw_targets_path = get_llm_targets_path()
    raw_bindings_path = get_llm_profile_bindings_path()
    if raw_targets_path or raw_bindings_path:
        if not raw_targets_path or not raw_bindings_path:
            raise LLMRegistryError(
                "LLM_TARGETS_PATH and LLM_PROFILE_BINDINGS_PATH must be set together."
            )
        targets_payload, targets_path = _load_json_path(raw_targets_path, env_name="LLM_TARGETS_PATH")
        bindings_payload, bindings_path = _load_json_path(
            raw_bindings_path,
            env_name="LLM_PROFILE_BINDINGS_PATH",
        )
        return (
            _compile_target_bindings_payload(targets_payload, bindings_payload),
            f"{targets_path} + {bindings_path}",
        )

    raw_json = get_llm_registry_json()
    if raw_json:
        return _load_json_env(raw_json, env_name="LLM_REGISTRY_JSON"), "env:LLM_REGISTRY_JSON"

    raw_path = get_llm_registry_path()
    if raw_path:
        payload, path = _load_json_path(raw_path, env_name="LLM_REGISTRY_PATH")
        return payload, str(path)

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
        "initial_max_concurrency": _env_int("LLM_INITIAL_MAX_CONCURRENCY", 6),
        "probe_max_concurrency": _env_int("LLM_PROBE_MAX_CONCURRENCY", get_llm_max_concurrency()),
        "min_stable_concurrency": _env_int("LLM_MIN_STABLE_CONCURRENCY", 2),
        "backoff_window_seconds": _env_int("LLM_BACKOFF_WINDOW_SECONDS", 10),
        "recover_window_seconds": _env_int("LLM_RECOVER_WINDOW_SECONDS", 20),
        "quota_cooldown_base_seconds": _env_int("LLM_QUOTA_COOLDOWN_BASE_SECONDS", 10),
        "quota_cooldown_max_seconds": _env_int("LLM_QUOTA_COOLDOWN_MAX_SECONDS", 60),
        "quota_state_ttl_seconds": _env_int("LLM_QUOTA_STATE_TTL_SECONDS", 120),
    }
    return {
        "providers": [provider],
        "profiles": [
            {
                "profile_id": DEFAULT_RUNTIME_PROFILE_ID,
                "provider_id": "legacy_default",
                "model_env": "LLM_MODEL",
                "temperature": _env_float("LLM_RUNTIME_TEMPERATURE", 0.2),
                "max_output_tokens": _env_int("LLM_RUNTIME_MAX_OUTPUT_TOKENS", 4096),
                "timeout_seconds": _env_int("LLM_RUNTIME_TIMEOUT_SECONDS", 120),
                "retry_attempts": get_llm_retry_attempts(),
                "max_concurrency": get_llm_max_concurrency(),
                "default_burst_concurrency": _env_int("LLM_RUNTIME_DEFAULT_BURST_CONCURRENCY", 6),
                "quota_retry_attempts": _env_int(
                    "LLM_RUNTIME_QUOTA_RETRY_ATTEMPTS",
                    _default_quota_retry_attempts(DEFAULT_RUNTIME_PROFILE_ID),
                ),
                "quota_wait_budget_seconds": _env_int(
                    "LLM_RUNTIME_QUOTA_WAIT_BUDGET_SECONDS",
                    _default_quota_wait_budget_seconds(DEFAULT_RUNTIME_PROFILE_ID),
                    minimum=0,
                ),
            },
            {
                "profile_id": DEFAULT_DATASET_REVIEW_PROFILE_ID,
                "provider_id": "legacy_default",
                "model_env": "LLM_DATASET_REVIEW_MODEL",
                "temperature": _env_float("LLM_DATASET_REVIEW_TEMPERATURE", 0.2),
                "max_output_tokens": _env_int("LLM_DATASET_REVIEW_MAX_OUTPUT_TOKENS", 4096),
                "timeout_seconds": _env_int("LLM_DATASET_REVIEW_TIMEOUT_SECONDS", 120),
                "retry_attempts": _env_int("LLM_DATASET_REVIEW_RETRY_ATTEMPTS", get_llm_retry_attempts()),
                "max_concurrency": _env_int("LLM_DATASET_REVIEW_MAX_CONCURRENCY", get_llm_max_concurrency()),
                "default_burst_concurrency": _env_int("LLM_DATASET_REVIEW_DEFAULT_BURST_CONCURRENCY", 6),
                "quota_retry_attempts": _env_int(
                    "LLM_DATASET_REVIEW_QUOTA_RETRY_ATTEMPTS",
                    _default_quota_retry_attempts(DEFAULT_DATASET_REVIEW_PROFILE_ID),
                ),
                "quota_wait_budget_seconds": _env_int(
                    "LLM_DATASET_REVIEW_QUOTA_WAIT_BUDGET_SECONDS",
                    _default_quota_wait_budget_seconds(DEFAULT_DATASET_REVIEW_PROFILE_ID),
                    minimum=0,
                ),
            },
            {
                "profile_id": DEFAULT_EVAL_JUDGE_PROFILE_ID,
                "provider_id": "legacy_default",
                "model_env": "LLM_EVAL_JUDGE_MODEL",
                "temperature": _env_float("LLM_EVAL_JUDGE_TEMPERATURE", 0.2),
                "max_output_tokens": _env_int("LLM_EVAL_JUDGE_MAX_OUTPUT_TOKENS", 4096),
                "timeout_seconds": _env_int("LLM_EVAL_JUDGE_TIMEOUT_SECONDS", 120),
                "retry_attempts": _env_int("LLM_EVAL_JUDGE_RETRY_ATTEMPTS", get_llm_retry_attempts()),
                "max_concurrency": _env_int("LLM_EVAL_JUDGE_MAX_CONCURRENCY", get_llm_max_concurrency()),
                "default_burst_concurrency": _env_int("LLM_EVAL_JUDGE_DEFAULT_BURST_CONCURRENCY", 6),
                "quota_retry_attempts": _env_int(
                    "LLM_EVAL_JUDGE_QUOTA_RETRY_ATTEMPTS",
                    _default_quota_retry_attempts(DEFAULT_EVAL_JUDGE_PROFILE_ID),
                ),
                "quota_wait_budget_seconds": _env_int(
                    "LLM_EVAL_JUDGE_QUOTA_WAIT_BUDGET_SECONDS",
                    _default_quota_wait_budget_seconds(DEFAULT_EVAL_JUDGE_PROFILE_ID),
                    minimum=0,
                ),
            },
        ],
    }


def _parse_key_slot(entry: Any, *, provider_id: str) -> LLMKeySlot:
    if not isinstance(entry, dict):
        raise LLMRegistryError(f"Provider {provider_id} key slot entry must be an object.")
    slot_id = _clean_str(entry.get("slot_id") or entry.get("credential_id"))
    if not slot_id:
        raise LLMRegistryError(f"Provider {provider_id} key slot entry is missing slot_id.")
    api_key = _clean_str(entry.get("api_key"))
    api_key_env = _clean_str(entry.get("api_key_env"))
    if bool(api_key) == bool(api_key_env):
        raise LLMRegistryError(
            f"Provider {provider_id} key slot {slot_id} must define exactly one of api_key or api_key_env."
        )
    return LLMKeySlot(
        slot_id=slot_id,
        api_key=api_key or None,
        api_key_env=api_key_env or None,
    )


def _parse_provider_key_slots(entry: dict[str, Any], *, provider_id: str) -> tuple[LLMKeySlot, ...]:
    raw_key_slots = entry.get("key_slots")
    normalized_entries: list[dict[str, str]] = []
    if raw_key_slots is not None:
        if not isinstance(raw_key_slots, list):
            raise LLMRegistryError(f"Provider {provider_id} key_slots must be a list.")
        normalized_entries = [item for item in raw_key_slots if item]
    else:
        primary_env = _clean_str(entry.get("api_key_env"))
        if primary_env:
            normalized_entries.append({"slot_id": primary_env, "api_key_env": primary_env})
        raw_key_pool_envs = entry.get("key_pool_envs", [])
        if raw_key_pool_envs is None:
            raw_key_pool_envs = []
        if not isinstance(raw_key_pool_envs, list):
            raise LLMRegistryError(f"Provider {provider_id} key_pool_envs must be a list.")
        for raw_env_name in raw_key_pool_envs:
            env_name = _clean_str(raw_env_name)
            if env_name:
                normalized_entries.append({"slot_id": env_name, "api_key_env": env_name})

    key_slots: list[LLMKeySlot] = []
    seen_slot_ids: set[str] = set()
    for normalized_entry in normalized_entries:
        key_slot = _parse_key_slot(normalized_entry, provider_id=provider_id)
        if key_slot.slot_id in seen_slot_ids:
            raise LLMRegistryError(f"Provider {provider_id} reuses key slot {key_slot.slot_id}.")
        seen_slot_ids.add(key_slot.slot_id)
        key_slots.append(key_slot)
    return tuple(key_slots)


def _parse_provider(entry: Any) -> LLMProviderConfig:
    if not isinstance(entry, dict):
        raise LLMRegistryError("Provider entry must be an object.")
    provider_id = _clean_str(entry.get("provider_id"))
    if not provider_id:
        raise LLMRegistryError("Provider entry is missing provider_id.")
    contract = _clean_str(entry.get("contract")).lower()
    if contract not in _ALLOWED_CONTRACTS:
        raise LLMRegistryError(f"Provider {provider_id} has unsupported contract: {contract}")

    raw_supported_models = entry.get("supported_models", [])
    if raw_supported_models is None:
        raw_supported_models = []
    if not isinstance(raw_supported_models, list):
        raise LLMRegistryError(f"Provider {provider_id} supported_models must be a list.")
    supported_models = tuple(
        item for item in (_clean_str(item) for item in raw_supported_models) if item
    ) or ("*",)

    key_slots = _parse_provider_key_slots(entry, provider_id=provider_id)
    max_concurrency = max(
        1,
        int(entry.get("max_concurrency", get_llm_max_concurrency()) or get_llm_max_concurrency()),
    )
    probe_max_concurrency = max(
        1,
        int(entry.get("probe_max_concurrency", max_concurrency) or max_concurrency),
    )
    min_stable_concurrency = max(1, int(entry.get("min_stable_concurrency", 2) or 2))
    initial_default = min(6, probe_max_concurrency)
    initial_max_concurrency = max(
        min_stable_concurrency,
        min(
            probe_max_concurrency,
            int(entry.get("initial_max_concurrency", initial_default) or initial_default),
        ),
    )
    return LLMProviderConfig(
        provider_id=provider_id,
        contract=contract,  # type: ignore[arg-type]
        base_url=_clean_str(entry.get("base_url")) or None,
        key_slots=key_slots,
        supported_models=supported_models,
        timeout_seconds=max(1, int(entry.get("timeout_seconds", 120) or 120)),
        retry_attempts=max(
            1,
            int(entry.get("retry_attempts", get_llm_retry_attempts()) or get_llm_retry_attempts()),
        ),
        max_concurrency=max(max_concurrency, probe_max_concurrency),
        initial_max_concurrency=initial_max_concurrency,
        probe_max_concurrency=max(probe_max_concurrency, min_stable_concurrency),
        min_stable_concurrency=min_stable_concurrency,
        backoff_window_seconds=max(1, int(entry.get("backoff_window_seconds", 10) or 10)),
        recover_window_seconds=max(1, int(entry.get("recover_window_seconds", 20) or 20)),
        quota_cooldown_base_seconds=max(1, int(entry.get("quota_cooldown_base_seconds", 10) or 10)),
        quota_cooldown_max_seconds=max(
            max(1, int(entry.get("quota_cooldown_base_seconds", 10) or 10)),
            int(entry.get("quota_cooldown_max_seconds", 60) or 60),
        ),
        quota_state_ttl_seconds=max(1, int(entry.get("quota_state_ttl_seconds", 120) or 120)),
    )


def _resolve_profile_model_for_provider(
    provider: LLMProviderConfig,
    *,
    requested_model: str,
    model_source: LLMProfileModelSource,
    context: str,
) -> str:
    if model_source == "profile":
        if "*" not in provider.supported_models and requested_model not in provider.supported_models:
            raise LLMRegistryError(
                f"{context} requests model {requested_model}, which is not listed in provider {provider.provider_id} supported_models."
            )
        return requested_model

    if requested_model and requested_model in provider.supported_models:
        return requested_model
    if "*" in provider.supported_models:
        return requested_model
    if len(provider.supported_models) == 1:
        return provider.supported_models[0]
    raise LLMRegistryError(
        f"{context} cannot resolve one model from provider {provider.provider_id} supported_models."
    )


def _parse_target_tiers(
    entry: dict[str, Any],
    *,
    profile_id: str,
    providers: dict[str, LLMProviderConfig],
    provider_id: str,
    fallback_provider_ids: tuple[str, ...],
    requested_model: str,
    model_source: LLMProfileModelSource,
) -> tuple[LLMTargetTierConfig, ...]:
    raw_target_tiers = entry.get("target_tiers")
    if raw_target_tiers is not None:
        if fallback_provider_ids:
            raise LLMRegistryError(
                f"Profile {profile_id} cannot mix target_tiers with fallback_provider_ids."
            )
        if not isinstance(raw_target_tiers, list) or not raw_target_tiers:
            raise LLMRegistryError(f"Profile {profile_id} target_tiers must be a non-empty list.")
        tiers: list[LLMTargetTierConfig] = []
        seen_tier_ids: set[str] = set()
        seen_target_ids: set[str] = set()
        for raw_tier in raw_target_tiers:
            if not isinstance(raw_tier, dict):
                raise LLMRegistryError(f"Profile {profile_id} target tier entry must be an object.")
            tier_id = _require_text(raw_tier, "tier_id", context=f"Profile {profile_id} tier")
            if tier_id in seen_tier_ids:
                raise LLMRegistryError(f"Profile {profile_id} reuses tier_id {tier_id}.")
            seen_tier_ids.add(tier_id)
            target_ids = _clean_str_list(
                raw_tier.get("target_ids"),
                context=f"Profile {profile_id} tier {tier_id} target_ids",
            )
            if not target_ids:
                raise LLMRegistryError(
                    f"Profile {profile_id} tier {tier_id} must define at least one target_id."
                )
            ordered_target_ids: list[str] = []
            tier_seen_ids: set[str] = set()
            for target_id in target_ids:
                if target_id in tier_seen_ids:
                    raise LLMRegistryError(
                        f"Profile {profile_id} tier {tier_id} reuses target_id {target_id}."
                    )
                if target_id in seen_target_ids:
                    raise LLMRegistryError(
                        f"Profile {profile_id} reuses target_id {target_id} across multiple tiers."
                    )
                provider = providers.get(target_id)
                if provider is None:
                    raise LLMRegistryError(
                        f"Profile {profile_id} refers to unknown target/provider {target_id} in tier {tier_id}."
                    )
                _resolve_profile_model_for_provider(
                    provider,
                    requested_model=requested_model,
                    model_source=model_source,
                    context=f"Profile {profile_id} tier {tier_id}",
                )
                tier_seen_ids.add(target_id)
                seen_target_ids.add(target_id)
                ordered_target_ids.append(target_id)
            tiers.append(
                LLMTargetTierConfig(
                    tier_id=tier_id,
                    target_ids=tuple(ordered_target_ids),
                    min_required_stable_concurrency=_require_int(
                        raw_tier,
                        "min_required_stable_concurrency",
                        context=f"Profile {profile_id} tier {tier_id}",
                        default=1,
                        minimum=1,
                    ),
                )
            )
        if tiers[0].target_ids[0] != provider_id:
            raise LLMRegistryError(
                f"Profile {profile_id} provider_id must match the first target in the first tier."
            )
        return tuple(tiers)

    target_ids = [provider_id, *fallback_provider_ids]
    unique_target_ids: list[str] = []
    seen_target_ids: set[str] = set()
    for target_id in target_ids:
        if target_id in seen_target_ids:
            continue
        provider = providers.get(target_id)
        if provider is None:
            raise LLMRegistryError(f"Profile {profile_id} refers to unknown provider {target_id}.")
        _resolve_profile_model_for_provider(
            provider,
            requested_model=requested_model,
            model_source=model_source,
            context=f"Profile {profile_id}",
        )
        seen_target_ids.add(target_id)
        unique_target_ids.append(target_id)
    primary_tier = LLMTargetTierConfig(
        tier_id="primary",
        target_ids=(provider_id,),
        min_required_stable_concurrency=1,
    )
    if len(unique_target_ids) == 1:
        return (primary_tier,)
    return (
        primary_tier,
        LLMTargetTierConfig(
            tier_id="fallback",
            target_ids=tuple(unique_target_ids[1:]),
            min_required_stable_concurrency=1,
        ),
    )


def _parse_profile(entry: Any, providers: dict[str, LLMProviderConfig]) -> LLMProfileConfig:
    if not isinstance(entry, dict):
        raise LLMRegistryError("Profile entry must be an object.")
    profile_id = _clean_str(entry.get("profile_id"))
    if "max" "_tokens" in entry:
        raise LLMRegistryError(
            f"Profile {profile_id or '<unknown>'} uses the retired output-limit field; use max_output_tokens."
        )
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
    raw_model_source = _clean_str(entry.get("model_source")).lower() or "profile"
    if raw_model_source not in _ALLOWED_PROFILE_MODEL_SOURCES:
        raise LLMRegistryError(f"Profile {profile_id} has unsupported model_source: {raw_model_source}")
    model_source: LLMProfileModelSource = raw_model_source  # type: ignore[assignment]
    _resolve_profile_model_for_provider(
        provider,
        requested_model=model,
        model_source=model_source,
        context=f"Profile {profile_id}",
    )

    fallback_provider_ids = tuple(
        _clean_str_list(entry.get("fallback_provider_ids"), context=f"Profile {profile_id} fallback_provider_ids")
    )
    for fallback_provider_id in fallback_provider_ids:
        if fallback_provider_id not in providers:
            raise LLMRegistryError(
                f"Profile {profile_id} refers to unknown fallback provider {fallback_provider_id}."
            )

    target_tiers = _parse_target_tiers(
        entry,
        profile_id=profile_id,
        providers=providers,
        provider_id=provider_id,
        fallback_provider_ids=fallback_provider_ids,
        requested_model=model,
        model_source=model_source,
    )
    flattened_target_ids: list[str] = []
    for tier in target_tiers:
        for target_id in tier.target_ids:
            if target_id != provider_id and target_id not in flattened_target_ids:
                flattened_target_ids.append(target_id)

    quota_retry_attempts_default = _default_quota_retry_attempts(profile_id)
    quota_wait_budget_seconds_default = _default_quota_wait_budget_seconds(profile_id)
    raw_quota_retry_attempts = entry.get("quota_retry_attempts")
    raw_quota_wait_budget_seconds = entry.get("quota_wait_budget_seconds")

    return LLMProfileConfig(
        profile_id=profile_id,
        provider_id=provider_id,
        fallback_provider_ids=tuple(flattened_target_ids),
        allow_cross_provider_failover=bool(entry.get("allow_cross_provider_failover", bool(flattened_target_ids))),
        model_source=model_source,
        target_tiers=target_tiers,
        model=model,
        temperature=float(entry.get("temperature", 0.2) or 0.2),
        max_output_tokens=max(1, int(entry.get("max_output_tokens", 4096) or 4096)),
        timeout_seconds=max(1, int(entry.get("timeout_seconds", provider.timeout_seconds) or provider.timeout_seconds)),
        retry_attempts=max(1, int(entry.get("retry_attempts", provider.retry_attempts) or provider.retry_attempts)),
        max_concurrency=max(1, int(entry.get("max_concurrency", provider.max_concurrency) or provider.max_concurrency)),
        default_burst_concurrency=max(
            1,
            int(
                entry.get(
                    "default_burst_concurrency",
                    min(provider.initial_max_concurrency, provider.max_concurrency),
                )
                or min(provider.initial_max_concurrency, provider.max_concurrency)
            ),
        ),
        quota_retry_attempts=max(
            1,
            int(quota_retry_attempts_default if raw_quota_retry_attempts is None else raw_quota_retry_attempts),
        ),
        quota_wait_budget_seconds=max(
            0,
            int(
                quota_wait_budget_seconds_default
                if raw_quota_wait_budget_seconds is None
                else raw_quota_wait_budget_seconds
            ),
        ),
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
        if provider.provider_id in providers:
            raise LLMRegistryError(f"LLM registry reuses provider_id {provider.provider_id}.")
        providers[provider.provider_id] = provider

    profile_entries = payload.get("profiles", [])
    if not isinstance(profile_entries, list) or not profile_entries:
        raise LLMRegistryError("LLM registry must define at least one profile.")
    profiles: dict[str, LLMProfileConfig] = {}
    for entry in profile_entries:
        profile = _parse_profile(entry, providers)
        if profile.profile_id in profiles:
            raise LLMRegistryError(f"LLM registry reuses profile_id {profile.profile_id}.")
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

    return apply_process_profile_concurrency_caps(get_llm_registry().get_profile(profile_id))


def get_llm_process_profile_max_concurrency(profile_id: str = DEFAULT_RUNTIME_PROFILE_ID) -> int | None:
    """Return the optional per-process hard cap for one profile."""

    env_name = _PROCESS_PROFILE_CONCURRENCY_CAP_ENV_BY_PROFILE.get(profile_id)
    if not env_name:
        return None
    return _optional_env_int(env_name)


def apply_process_profile_concurrency_caps(profile: LLMProfileConfig) -> LLMProfileConfig:
    """Clamp one profile to the current process-local concurrency ceiling when configured."""

    cap = get_llm_process_profile_max_concurrency(profile.profile_id)
    if cap is None:
        return profile
    capped_max = max(1, min(int(profile.max_concurrency), int(cap)))
    capped_burst = max(1, min(int(profile.default_burst_concurrency), capped_max))
    if capped_max == profile.max_concurrency and capped_burst == profile.default_burst_concurrency:
        return profile
    return replace(
        profile,
        max_concurrency=capped_max,
        default_burst_concurrency=capped_burst,
    )


def get_llm_profile_max_concurrency(profile_id: str = DEFAULT_RUNTIME_PROFILE_ID) -> int:
    """Return the bounded in-flight limit for one profile."""

    return get_llm_profile(profile_id).max_concurrency


def get_llm_profile_default_burst_concurrency(profile_id: str = DEFAULT_RUNTIME_PROFILE_ID) -> int:
    """Return the preferred default burst width for one profile."""

    return get_llm_profile(profile_id).default_burst_concurrency


def clear_llm_registry_cache() -> None:
    """Clear cached registry state for tests or dynamic env reloading."""

    get_llm_registry.cache_clear()
    get_llm_config.cache_clear()


__all__ = [
    "DEFAULT_DATASET_REVIEW_PROFILE_ID",
    "DEFAULT_EVAL_JUDGE_PROFILE_ID",
    "DEFAULT_RUNTIME_PROFILE_ID",
    "LLMKeySlot",
    "LLMProfileConfig",
    "LLMTargetTierConfig",
    "LLMProviderConfig",
    "LLMProviderContract",
    "LLMRegistry",
    "LLMRegistryError",
    "clear_llm_registry_cache",
    "apply_process_profile_concurrency_caps",
    "get_llm_profile",
    "get_llm_profile_default_burst_concurrency",
    "get_llm_profile_max_concurrency",
    "get_llm_process_profile_max_concurrency",
    "get_llm_registry",
]

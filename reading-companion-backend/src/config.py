"""Centralized configuration for LLM and API settings."""

import os
import uuid
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


READER_RESUME_COMPAT_VERSION = 1
_BACKEND_BOOT_ID = uuid.uuid4().hex


def _backend_root() -> Path:
    """Return the backend project root directory."""
    return Path(__file__).resolve().parents[1]


@lru_cache()
def get_llm_config() -> dict:
    """Get LLM configuration from environment variables.

    Returns:
        Dictionary with base_url, api_key, model
    """
    return {
        "base_url": os.getenv("LLM_BASE_URL", "https://api.minimaxi.chat/v1"),
        "api_key": os.getenv("LLM_API_KEY", ""),
        "model": os.getenv("LLM_MODEL", "default-model"),
    }


def get_llm_provider_contract() -> str:
    """Return the legacy provider contract for fallback registry generation."""

    return os.getenv("LLM_PROVIDER_CONTRACT", "anthropic").strip().lower() or "anthropic"


def get_llm_registry_path() -> str:
    """Return the optional structured LLM registry config path."""

    return os.getenv("LLM_REGISTRY_PATH", "").strip()


def get_llm_registry_json() -> str:
    """Return the optional inline structured LLM registry payload."""

    return os.getenv("LLM_REGISTRY_JSON", "").strip()


def _env_int(name: str, default: int, *, minimum: int = 1) -> int:
    """Parse one integer env var with a lower bound fallback."""
    raw = os.getenv(name, "").strip()
    if raw.lstrip("-").isdigit():
        return max(minimum, int(raw))
    return max(minimum, int(default))


def get_llm_max_concurrency() -> int:
    """Return the global in-flight LLM call limit."""
    return _env_int("LLM_MAX_CONCURRENCY", 4)


def get_llm_retry_attempts() -> int:
    """Return the retry count for transient LLM failures."""
    return _env_int("LLM_RETRY_ATTEMPTS", 3)


def get_pipeline_segment_workers() -> int:
    """Return the default background chapter-segmentation worker count."""
    return _env_int("PIPELINE_SEGMENT_WORKERS", 3)


def get_pipeline_segment_workers_when_reader_blocked() -> int:
    """Return the boosted segmentation worker count while the reader waits."""
    return _env_int("PIPELINE_SEGMENT_WORKERS_WHEN_READER_BLOCKED", 4)


def get_pipeline_prefetch_window() -> int:
    """Return how many future unread chapters should be prefetched."""
    return _env_int("PIPELINE_PREFETCH_WINDOW", 3)


def get_tavily_api_key() -> str:
    """Get Tavily API key from environment variables.

    Returns:
        Tavily API key
    """
    return os.getenv("TAVILY_API_KEY", "")
def get_upload_max_bytes() -> int:
    """Return the maximum accepted EPUB upload size in bytes."""
    raw = os.getenv("UPLOAD_MAX_BYTES", "").strip()
    if raw.isdigit():
        return max(1, int(raw))
    return 100 * 1024 * 1024


def get_backend_runtime_root() -> Path:
    """Return the root directory used for runtime state and output."""
    raw = os.getenv("BACKEND_RUNTIME_ROOT", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return _backend_root()


def get_backend_cors_origins() -> list[str]:
    """Return allowed frontend origins for local API access."""
    raw = os.getenv(
        "BACKEND_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).strip()
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def get_backend_host() -> str:
    """Return the API bind host."""
    return os.getenv("BACKEND_HOST", "0.0.0.0").strip() or "0.0.0.0"


def get_backend_port() -> int:
    """Return the API bind port."""
    raw = os.getenv("BACKEND_PORT", "8000").strip()
    if raw.isdigit():
        return int(raw)
    return 8000


def get_backend_run_mode() -> str:
    """Return the backend launcher mode used for logs and health reporting."""
    mode = os.getenv("BACKEND_RUN_MODE", "dev").strip().lower()
    if mode in {"dev", "demo", "prod"}:
        return mode
    return "dev"


def get_backend_boot_id() -> str:
    """Return the current backend-process boot identifier."""
    return _BACKEND_BOOT_ID


def get_reader_resume_compat_version() -> int:
    """Return the persisted compatibility marker used for resume decisions."""
    return READER_RESUME_COMPAT_VERSION


def get_backend_version() -> str | None:
    """Return a deploy/version identifier when one is available."""
    for name in ("APP_VERSION", "RAILWAY_GIT_COMMIT_SHA", "GIT_COMMIT", "COMMIT_SHA"):
        value = os.getenv(name, "").strip()
        if value:
            return value
    return None


def get_backend_reading_mechanism_key() -> str | None:
    """Return the internally selected backend reading mechanism, if overridden."""

    raw = os.getenv("BACKEND_READING_MECHANISM", "").strip().lower()
    if not raw or raw == "iterator_v1":
        return None
    if raw == "attentional_v2":
        return raw
    return None


def get_backend_test_mode() -> bool:
    """Return whether backend fixture mode is enabled."""
    raw = os.getenv("BACKEND_TEST_MODE", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def get_backend_test_fixture_profile() -> str:
    """Return the active backend test fixture profile."""
    return os.getenv("BACKEND_TEST_FIXTURE_PROFILE", "").strip().lower()

"""Centralized configuration for LLM and API settings."""

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


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


def get_tavily_api_key() -> str:
    """Get Tavily API key from environment variables.

    Returns:
        Tavily API key
    """
    return os.getenv("TAVILY_API_KEY", "")


def get_sample_book_id() -> str:
    """Return the configured sample book id for landing/sample endpoints."""
    return os.getenv("SAMPLE_BOOK_ID", "").strip()


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

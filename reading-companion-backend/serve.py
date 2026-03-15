"""Stable server entrypoint for demo and production-style runs."""

from __future__ import annotations

import sys

import uvicorn

from src.config import get_backend_host, get_backend_port, get_backend_run_mode, get_backend_runtime_root

MIN_SUPPORTED_PYTHON = (3, 11)


def _require_supported_python() -> None:
    """Abort the stable server when the interpreter is unsupported."""
    if sys.version_info >= MIN_SUPPORTED_PYTHON:
        return
    print(
        "Error: Reading Companion backend requires Python "
        f"{MIN_SUPPORTED_PYTHON[0]}.{MIN_SUPPORTED_PYTHON[1]}+ but received "
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} "
        f"({sys.executable}).",
        flush=True,
    )
    raise SystemExit(1)


if __name__ == "__main__":
    _require_supported_python()
    mode = get_backend_run_mode()
    host = get_backend_host()
    port = get_backend_port()
    runtime_root = get_backend_runtime_root()
    print(f"[backend] mode={mode} host={host} port={port} runtime_root={runtime_root}", flush=True)
    uvicorn.run(
        "src.api.app:app",
        host=host,
        port=port,
        reload=False,
    )

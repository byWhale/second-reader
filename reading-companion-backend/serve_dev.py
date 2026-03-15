"""Development server entrypoint with autoreload enabled."""

from __future__ import annotations

import uvicorn

from src.config import get_backend_host, get_backend_port, get_backend_run_mode, get_backend_runtime_root


if __name__ == "__main__":
    mode = get_backend_run_mode()
    host = get_backend_host()
    port = get_backend_port()
    runtime_root = get_backend_runtime_root()
    print(f"[backend] mode={mode} host={host} port={port} runtime_root={runtime_root}", flush=True)
    uvicorn.run(
        "src.api.app:app",
        host=host,
        port=port,
        reload=True,
    )

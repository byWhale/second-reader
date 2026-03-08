"""Development server entrypoint for the Reading Companion API."""

from __future__ import annotations

import uvicorn

from src.config import get_backend_host, get_backend_port


if __name__ == "__main__":
    uvicorn.run(
        "src.api.app:app",
        host=get_backend_host(),
        port=get_backend_port(),
        reload=True,
    )

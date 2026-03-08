#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/common.sh"

require_backend_python
require_backend_venv
BACKEND_PYTHON="$BACKEND_DIR/.venv/bin/python"

export BACKEND_RUNTIME_ROOT="$DEFAULT_BACKEND_RUNTIME_ROOT"
export BACKEND_CORS_ORIGINS="$DEFAULT_BACKEND_CORS_ORIGINS"
export BACKEND_HOST="$DEFAULT_BACKEND_HOST"
export BACKEND_PORT="$DEFAULT_BACKEND_PORT"

cd "$BACKEND_DIR"
"$BACKEND_PYTHON" scripts/backfill_legacy_outputs.py --root "$BACKEND_RUNTIME_ROOT"
exec "$BACKEND_PYTHON" serve.py

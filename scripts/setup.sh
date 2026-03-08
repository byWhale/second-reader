#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/common.sh"

echo "Installing frontend dependencies..."
(cd "$FRONTEND_DIR" && npm install)

require_backend_python
BACKEND_PYTHON="$(backend_python)"

echo "Creating backend virtualenv..."
"$BACKEND_PYTHON" -m venv "$BACKEND_DIR/.venv"

echo "Installing backend dependencies..."
(cd "$BACKEND_DIR" && .venv/bin/python -m pip install --upgrade pip && .venv/bin/python -m pip install -e ".[dev]")

echo "Backfilling legacy backend artifacts..."
(cd "$BACKEND_DIR" && .venv/bin/python scripts/backfill_legacy_outputs.py --root "$DEFAULT_BACKEND_RUNTIME_ROOT")

echo "Setup complete."

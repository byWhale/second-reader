#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/common.sh"

if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  echo "error: frontend dependencies missing. Run 'make setup' first."
  exit 1
fi

if [[ ! -x "$BACKEND_DIR/.venv/bin/python" ]]; then
  echo "error: backend virtualenv missing. Run 'make setup' first."
  exit 1
fi

echo "Running backend tests..."
(cd "$BACKEND_DIR" && .venv/bin/python -m pytest)

echo "Running frontend smoke build..."
(cd "$FRONTEND_DIR" && npm run build)

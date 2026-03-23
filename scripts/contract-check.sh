#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/common.sh"

if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  echo "error: frontend dependencies missing. Run 'make setup' first."
  exit 1
fi

require_backend_venv
BACKEND_PYTHON="$BACKEND_DIR/.venv/bin/python"

echo "Checking docs/backend/frontend contract constants..."
"$BACKEND_PYTHON" "$ROOT_DIR/scripts/check-contract-doc.py"

echo "Checking frontend integration doc appendix..."
"$BACKEND_PYTHON" "$ROOT_DIR/scripts/check-integration-doc.py"

echo "Checking current default reading mechanism doc appendix..."
"$BACKEND_PYTHON" "$ROOT_DIR/scripts/check-reading-mechanism-doc.py"

echo "Checking decision-history reminder..."
"$BACKEND_PYTHON" "$ROOT_DIR/scripts/check-history-update.py"

echo "Checking backend OpenAPI snapshot..."
(cd "$BACKEND_DIR" && .venv/bin/python scripts/export_openapi.py --check)

echo "Checking frontend static contract rules..."
(cd "$FRONTEND_DIR" && npm run contract-check)

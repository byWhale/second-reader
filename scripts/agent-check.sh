#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/common.sh"

require_backend_venv

echo "Running existing contract and documentation checks..."
"$ROOT_DIR/scripts/contract-check.sh"

echo "Checking agent-switching traceability..."
"$BACKEND_DIR/.venv/bin/python" "$ROOT_DIR/scripts/check-agent-traceability.py"

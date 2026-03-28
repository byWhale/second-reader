#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/common.sh"

require_backend_python
BACKEND_PYTHON="$(backend_python)"

"$BACKEND_PYTHON" "$ROOT_DIR/scripts/print-agent-context.py"

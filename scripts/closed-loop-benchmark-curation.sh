#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/common.sh"

require_backend_python
require_backend_venv
BACKEND_PYTHON="$BACKEND_DIR/.venv/bin/python"

cd "$BACKEND_DIR"
exec "$BACKEND_PYTHON" -m eval.attentional_v2.run_closed_loop_benchmark_curation "$@"

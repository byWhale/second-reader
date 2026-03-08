#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/common.sh"

"$ROOT_DIR/scripts/doctor.sh"

"$ROOT_DIR/scripts/dev-backend.sh" &
BACKEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" >/dev/null 2>&1 || true
}

trap cleanup EXIT INT TERM

"$ROOT_DIR/scripts/dev-frontend.sh"

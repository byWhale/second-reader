#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/common.sh"

if ! command -v npm >/dev/null 2>&1; then
  echo "error: npm is required."
  exit 1
fi

export VITE_API_BASE_URL="$DEFAULT_API_BASE_URL"
export VITE_WS_BASE_URL="$DEFAULT_WS_BASE_URL"

cd "$FRONTEND_DIR"
exec npm run dev -- --host 0.0.0.0 --port "$DEFAULT_FRONTEND_PORT"

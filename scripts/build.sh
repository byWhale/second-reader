#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/common.sh"

if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  echo "error: frontend dependencies missing. Run 'make setup' first."
  exit 1
fi

export VITE_API_BASE_URL="$DEFAULT_API_BASE_URL"
export VITE_WS_BASE_URL="$DEFAULT_WS_BASE_URL"

cd "$FRONTEND_DIR"
exec npm run build

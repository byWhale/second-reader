#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/reading-companion-backend"
FRONTEND_DIR="$ROOT_DIR/reading-companion-frontend"

DEFAULT_BACKEND_PORT="${BACKEND_PORT:-8000}"
DEFAULT_FRONTEND_PORT="${FRONTEND_PORT:-5173}"
DEFAULT_BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
DEFAULT_API_BASE_URL="${VITE_API_BASE_URL:-http://localhost:${DEFAULT_BACKEND_PORT}}"
DEFAULT_WS_BASE_URL="${VITE_WS_BASE_URL:-ws://localhost:${DEFAULT_BACKEND_PORT}}"
DEFAULT_BACKEND_RUNTIME_ROOT="${BACKEND_RUNTIME_ROOT:-$BACKEND_DIR}"
DEFAULT_BACKEND_CORS_ORIGINS="${BACKEND_CORS_ORIGINS:-http://localhost:${DEFAULT_FRONTEND_PORT},http://127.0.0.1:${DEFAULT_FRONTEND_PORT}}"

backend_python() {
  if [[ -x "$BACKEND_DIR/.venv/bin/python" ]]; then
    printf '%s\n' "$BACKEND_DIR/.venv/bin/python"
    return 0
  fi

  if command -v python3.11 >/dev/null 2>&1; then
    command -v python3.11
    return 0
  fi

  return 1
}

require_backend_python() {
  if ! backend_python >/dev/null 2>&1; then
    echo "error: Python 3.11+ is required for the backend."
    echo "Install python3.11, then rerun 'make setup'."
    exit 1
  fi
}

require_backend_venv() {
  if [[ ! -x "$BACKEND_DIR/.venv/bin/python" ]]; then
    echo "error: backend virtualenv missing. Run 'make setup' first."
    exit 1
  fi
}

port_in_use() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
    return $?
  fi
  return 1
}

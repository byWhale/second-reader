#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/common.sh"

echo "Workspace root: $ROOT_DIR"
echo "Backend dir: $BACKEND_DIR"
echo "Frontend dir: $FRONTEND_DIR"
echo

failed=0

if command -v npm >/dev/null 2>&1; then
  echo "npm: $(npm --version)"
else
  echo "error: npm is required."
  failed=1
fi

if backend_python >/dev/null 2>&1; then
  echo "backend python: $(backend_python) ($("$(backend_python)" --version 2>&1))"
else
  echo "error: python3.11+ is required but was not found."
  failed=1
fi

if [[ -f "$BACKEND_DIR/.env" ]]; then
  echo "backend env: present"
else
  echo "warning: backend .env missing at $BACKEND_DIR/.env"
fi

if [[ -f "$FRONTEND_DIR/.env.local" || -f "$FRONTEND_DIR/.env" ]]; then
  echo "frontend env: present"
else
  echo "frontend env: optional, using script defaults"
fi

if port_in_use "$DEFAULT_BACKEND_PORT"; then
  echo "warning: backend port $DEFAULT_BACKEND_PORT already in use"
else
  echo "backend port $DEFAULT_BACKEND_PORT: free"
fi

if port_in_use "$DEFAULT_FRONTEND_PORT"; then
  echo "warning: frontend port $DEFAULT_FRONTEND_PORT already in use"
else
  echo "frontend port $DEFAULT_FRONTEND_PORT: free"
fi

exit "$failed"

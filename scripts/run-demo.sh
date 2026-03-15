#!/usr/bin/env bash
set -euo pipefail

source "$(cd "$(dirname "$0")" && pwd)/common.sh"

"$ROOT_DIR/scripts/doctor.sh"

SUPERVISOR_PID=""
FRONTEND_PID=""

restart_backend_forever() {
  while true; do
    local started_at
    started_at="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "[demo] starting stable backend at $started_at" >&2
    set +e
    "$ROOT_DIR/scripts/run-backend-stable.sh" demo
    local exit_code=$?
    set -e
    local stopped_at
    stopped_at="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "[demo] backend exited with code $exit_code at $stopped_at; restarting in 1s" >&2
    sleep 1
  done
}

cleanup() {
  if [[ -n "$SUPERVISOR_PID" ]]; then
    kill "$SUPERVISOR_PID" >/dev/null 2>&1 || true
    wait "$SUPERVISOR_PID" 2>/dev/null || true
  fi
  if [[ -n "$FRONTEND_PID" ]]; then
    kill "$FRONTEND_PID" >/dev/null 2>&1 || true
    wait "$FRONTEND_PID" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

restart_backend_forever &
SUPERVISOR_PID=$!

"$ROOT_DIR/scripts/dev-frontend.sh" &
FRONTEND_PID=$!

wait "$FRONTEND_PID"

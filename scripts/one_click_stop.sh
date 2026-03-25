#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$ROOT_DIR/.redeemer.pid"

if [ ! -f "$PID_FILE" ]; then
  echo "[INFO] No PID file found. Bot may already be stopped."
  exit 0
fi

PID="$(cat "$PID_FILE" || true)"
if [ -z "$PID" ]; then
  rm -f "$PID_FILE"
  echo "[INFO] Empty PID file removed."
  exit 0
fi

if kill -0 "$PID" >/dev/null 2>&1; then
  kill "$PID"
  for _ in {1..10}; do
    if kill -0 "$PID" >/dev/null 2>&1; then
      sleep 1
    else
      break
    fi
  done

  if kill -0 "$PID" >/dev/null 2>&1; then
    echo "[WARN] Process still alive, sending SIGKILL..."
    kill -9 "$PID" >/dev/null 2>&1 || true
  fi

  echo "[OK] Auto redeemer stopped (PID: $PID)."
else
  echo "[INFO] Process $PID is not running."
fi

rm -f "$PID_FILE"

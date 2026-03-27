#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$ROOT_DIR/.redeemer.pid"
GLOBAL_CMD="${GLOBAL_CMD:-polymarket-redeemer}"
START_CMD="$GLOBAL_CMD start"
START_CMD_FALLBACK="bash \"$ROOT_DIR/scripts/one_click_start.sh\""

if [ ! -f "$PID_FILE" ]; then
  echo "[INFO] No PID file found. Bot may already be stopped."
  echo "[INFO] Start command: $START_CMD"
  echo "[INFO] Fallback: $START_CMD_FALLBACK"
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
  echo "[INFO] Start command: $START_CMD"
  echo "[INFO] Fallback: $START_CMD_FALLBACK"
else
  echo "[INFO] Process $PID is not running."
  echo "[INFO] Start command: $START_CMD"
  echo "[INFO] Fallback: $START_CMD_FALLBACK"
fi

rm -f "$PID_FILE"

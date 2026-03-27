#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_FILE="$ROOT_DIR/config_redeem.json"
TEMPLATE_FILE="$ROOT_DIR/config_redeem.example.json"
EDITOR_BIN="${EDITOR:-nano}"
GLOBAL_CMD="${GLOBAL_CMD:-polymarket-redeemer}"
START_CMD="$GLOBAL_CMD start"
START_CMD_FALLBACK="bash \"$ROOT_DIR/scripts/one_click_start.sh\""

if [ ! -f "$CONFIG_FILE" ]; then
  cp "$TEMPLATE_FILE" "$CONFIG_FILE"
  echo "[INFO] Created $CONFIG_FILE from template."
fi

if command -v "$EDITOR_BIN" >/dev/null 2>&1; then
  echo "[INFO] Opening config with $EDITOR_BIN"
  "$EDITOR_BIN" "$CONFIG_FILE"
else
  echo "[WARN] Editor '$EDITOR_BIN' not found."
  echo "[INFO] Please edit manually: $CONFIG_FILE"
fi

echo "[INFO] After editing, you can start with: $START_CMD"
echo "[INFO] Fallback: $START_CMD_FALLBACK"

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$ROOT_DIR/.redeemer.pid"
LOG_FILE="$ROOT_DIR/redeemer.runtime.log"
PYTHON_BIN="${PYTHON_BIN:-python3}"

cd "$ROOT_DIR"

if [ -f "$PID_FILE" ]; then
  OLD_PID="$(cat "$PID_FILE" || true)"
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" >/dev/null 2>&1; then
    echo "[INFO] Auto redeemer is already running (PID: $OLD_PID)."
    echo "[INFO] Stop it first: bash scripts/one_click_stop.sh"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "[ERROR] $PYTHON_BIN is required."
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "[INFO] Creating .venv"
  "$PYTHON_BIN" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install --upgrade pip >/dev/null
pip install -r requirements.txt >/dev/null

if [ ! -f "config_redeem.json" ]; then
  cp config_redeem.example.json config_redeem.json
  echo "[WARN] config_redeem.json was missing, created from template."
  echo "[WARN] Please edit config_redeem.json with your keys before production use."
  echo "[INFO] Run: bash scripts/edit_config.sh"
  exit 1
fi

python - <<'PYCONF'
import json
import sys
from pathlib import Path

cfg = Path("config_redeem.json")
try:
    data = json.loads(cfg.read_text())
except Exception:
    print("[ERROR] config_redeem.json is not valid JSON. Please fix it first.")
    sys.exit(1)

bad = False
for i, acc in enumerate(data.get("accounts", []), start=1):
    pk = str(acc.get("private_key", ""))
    fa = str(acc.get("funder_address", ""))
    if not pk or pk in {"0x", "0xYOUR_PRIVATE_KEY"}:
        print(f"[ERROR] account #{i} has placeholder private_key.")
        bad = True
    if not fa or fa in {"0x", "0xYOUR_FUNDER_ADDRESS"}:
        print(f"[ERROR] account #{i} has placeholder funder_address.")
        bad = True
if bad:
    print("[INFO] Run: bash scripts/edit_config.sh")
    sys.exit(1)
PYCONF

nohup python auto_redeem.py >> "$LOG_FILE" 2>&1 &
NEW_PID=$!
echo "$NEW_PID" > "$PID_FILE"

echo "[OK] Auto redeemer started in background."
echo "[OK] PID: $NEW_PID"
echo "[OK] Runtime log: $LOG_FILE"
echo "[OK] Stop command: bash scripts/one_click_stop.sh"

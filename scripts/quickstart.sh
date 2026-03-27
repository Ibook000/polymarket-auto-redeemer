#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/Ibook000/polymarket-auto-redeemer.git}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/polymarket-auto-redeemer}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v git >/dev/null 2>&1; then
  echo "[ERROR] git is required."
  exit 1
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "[ERROR] $PYTHON_BIN is required."
  exit 1
fi

if [ -d "$INSTALL_DIR/.git" ]; then
  echo "[INFO] Updating existing repo: $INSTALL_DIR"
  git -C "$INSTALL_DIR" pull --ff-only
else
  echo "[INFO] Cloning repo to: $INSTALL_DIR"
  git clone "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

if [ ! -d ".venv" ]; then
  if ! "$PYTHON_BIN" -c "import venv" >/dev/null 2>&1; then
    echo "[ERROR] Python module 'venv' is missing for interpreter: $PYTHON_BIN"
    echo "[ERROR] This is a missing system dependency, not a runtime error in this repository."
    if [ -r /etc/os-release ]; then
      # shellcheck disable=SC1091
      . /etc/os-release
      if [ "${ID:-}" = "debian" ] || [ "${ID:-}" = "ubuntu" ] || [[ "${ID_LIKE:-}" == *"debian"* ]]; then
        echo "[HINT] Debian/Ubuntu install command:"
        echo "       sudo apt update && sudo apt install -y python3-venv"
        python_version="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)"
        if [[ "$python_version" =~ ^[0-9]+\.[0-9]+$ ]]; then
          echo "[HINT] Version-specific option for this interpreter:"
          echo "       sudo apt update && sudo apt install -y python${python_version}-venv"
        fi
      fi
    fi
    exit 1
  fi

  echo "[INFO] Creating virtual environment"
  "$PYTHON_BIN" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f "config_redeem.json" ]; then
  cp config_redeem.example.json config_redeem.json
  echo "[INFO] Created config_redeem.json from template"
fi

EDITOR_BIN="${EDITOR:-nano}"
if command -v "$EDITOR_BIN" >/dev/null 2>&1; then
  echo "[INFO] Opening config_redeem.json with $EDITOR_BIN"
  "$EDITOR_BIN" config_redeem.json
else
  echo "[WARN] Editor '$EDITOR_BIN' not found. Please edit: $INSTALL_DIR/config_redeem.json"
fi

echo "[INFO] Starting auto redeemer..."
python auto_redeem.py

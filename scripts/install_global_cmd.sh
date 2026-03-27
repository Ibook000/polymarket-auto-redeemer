#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"
CMD_NAME="${CMD_NAME:-polymarket-redeemer}"
TARGET="$BIN_DIR/$CMD_NAME"

mkdir -p "$BIN_DIR"

cat > "$TARGET" <<EOF
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$ROOT_DIR"

if [ \$# -lt 1 ]; then
  echo "Usage: $CMD_NAME {quickstart|start|stop|edit-config}"
  exit 1
fi

case "\$1" in
  quickstart)
    exec bash "\$ROOT_DIR/scripts/quickstart.sh"
    ;;
  start)
    exec bash "\$ROOT_DIR/scripts/one_click_start.sh"
    ;;
  stop)
    exec bash "\$ROOT_DIR/scripts/one_click_stop.sh"
    ;;
  edit-config)
    exec bash "\$ROOT_DIR/scripts/edit_config.sh"
    ;;
  *)
    echo "Unknown subcommand: \$1"
    echo "Usage: $CMD_NAME {quickstart|start|stop|edit-config}"
    exit 1
    ;;
esac
EOF

chmod +x "$TARGET"

echo "[INFO] Installed global command: $CMD_NAME -> $TARGET"
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
  echo "[WARN] $BIN_DIR is not in PATH for current shell."
  echo "[WARN] Add it with: export PATH=\"$BIN_DIR:\$PATH\""
fi

#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$ROOT/.venv"

echo "==> HÚSVIT PyQt — Raspberry Pi setup"
sudo apt-get update -qq
sudo apt-get install -y python3-venv python3-pyqt5 || true

if [[ ! -d "$VENV" ]]; then
    python3 -m venv "$VENV"
fi
source "$VENV/bin/activate"
pip install --upgrade pip
pip install -r "$ROOT/requirements.txt"

echo ""
echo "Run on the Pi display:"
echo "  $ROOT/scripts/run.sh --fullscreen"

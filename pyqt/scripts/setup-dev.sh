#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$ROOT/.venv"

echo "==> HÚSVIT PyQt — dev setup"
python3 -m venv "$VENV"
source "$VENV/bin/activate"
pip install --upgrade pip
pip install -r "$ROOT/requirements.txt"
echo ""
echo "Run: $ROOT/scripts/run.sh"

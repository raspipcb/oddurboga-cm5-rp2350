#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> HÚSVIT PyQt - Raspberry Pi setup"
sudo apt-get update -qq
# Debian trixie on CM5: prefer apt packages (externally-managed Python).
sudo apt-get install -y \
    python3-pyqt5 \
    python3-pyqt5.qtsvg \
    python3-serial \
    python3-venv

if [[ "${USE_VENV:-0}" == "1" ]]; then
    VENV="$ROOT/.venv"
    if [[ ! -d "$VENV" ]]; then
        python3 -m venv "$VENV"
    fi
    source "$VENV/bin/activate"
    pip install --upgrade pip
    pip install -r "$ROOT/requirements.txt"
    echo "Dev venv installed at $VENV"
else
    echo "Using system packages: python3-pyqt5, python3-serial"
fi

echo ""
echo "UART on CM5 is usually /dev/ttyAMA0 (see doc/oddurboga-bringup-report-1.pdf)."
echo "Run on the Pi display:"
echo "  $ROOT/scripts/run.sh --fullscreen --port /dev/ttyAMA0"

#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/src"

if [[ -f "$ROOT/.venv/bin/activate" ]]; then
    source "$ROOT/.venv/bin/activate"
    PYTHON=python
else
    PYTHON=python3
fi

# CM5 carrier: UART to RP2350 is typically ttyAMA0, not serial0.
if [[ $# -eq 0 ]] && [[ -z "${IPS_PORT:-}" ]] && [[ -e /dev/ttyAMA0 ]]; then
    exec "$PYTHON" main.py --port /dev/ttyAMA0 "$@"
fi

exec "$PYTHON" main.py "$@"

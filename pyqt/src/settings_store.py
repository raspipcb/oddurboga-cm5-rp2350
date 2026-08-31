"""Load and save user-adjustable settings to config.json."""

from __future__ import annotations

import json
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"

PERSISTED_KEYS = frozenset({
    "set_temp",
    "threshold",
    "extra_heat",
    "flow_mode",
})

DEFAULTS = {
    "set_temp": 36,
    "threshold": 2,
    "extra_heat": 3,
    "flow_mode": 1,
}


def read_config() -> dict:
    try:
        if CONFIG_PATH.is_file():
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def write_config(updates: dict) -> None:
    data = read_config()
    data.update(updates)
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def load_persisted() -> dict:
    """Return saved user settings merged over defaults."""
    data = read_config()
    result = DEFAULTS.copy()
    for key in PERSISTED_KEYS:
        if key in data:
            result[key] = data[key]
    return result


def save_persisted(**kwargs) -> None:
    """Persist one or more user settings (silently ignores unknown keys)."""
    filtered = {k: v for k, v in kwargs.items() if k in PERSISTED_KEYS}
    if filtered:
        write_config(filtered)

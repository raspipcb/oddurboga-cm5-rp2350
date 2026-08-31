"""Logging for CM5 <-> RP2350 API traffic.

Writes to pyqt/logs/api.log with rotation, and mirrors to stderr. If the log
directory cannot be created or written (read-only rootfs, full disk), file
logging is skipped rather than raising - losing the log must never take the
controller UI down with it.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIR / "api.log"
MAX_BYTES = 512_000
BACKUPS = 3

_LOGGER_NAME = "ips.api"
_configured = False

# Prefixes keep the log skimmable: request, reply, failure, stray line.
TX = "->"
RX = "<-"
FAIL = "!!"
STRAY = "~~"


def _add_file_handler(logger: logging.Logger, formatter: logging.Formatter) -> bool:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            LOG_FILE, maxBytes=MAX_BYTES, backupCount=BACKUPS, encoding="utf-8"
        )
    except (OSError, PermissionError) as exc:
        logger.warning("file logging disabled (%s): %s", LOG_FILE, exc)
        return False
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return True


def get_logger() -> logging.Logger:
    """Return the shared API logger, configuring handlers once."""
    global _configured
    logger = logging.getLogger(_LOGGER_NAME)
    if _configured:
        return logger

    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03d %(levelname)-7s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formatter)
    console.setLevel(logging.INFO)
    logger.addHandler(console)

    _add_file_handler(logger, formatter)
    _configured = True
    return logger


log = get_logger()

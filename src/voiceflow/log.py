"""Logging — rotating file log at ~/Library/Logs/VoiceFlow/voiceflow.log."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_DIR = Path.home() / "Library" / "Logs" / "VoiceFlow"
_LOG_FILE = _LOG_DIR / "voiceflow.log"


def get_log_path() -> Path:
    return _LOG_FILE


def setup_logging() -> None:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        _LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=3,
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)-8s %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root = logging.getLogger("voiceflow")
    root.setLevel(logging.DEBUG)
    root.addHandler(handler)


logger = logging.getLogger("voiceflow")

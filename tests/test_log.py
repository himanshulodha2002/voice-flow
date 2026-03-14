"""Tests for logging setup."""

from __future__ import annotations

import logging
from pathlib import Path

from voiceflow.log import get_log_path, logger, setup_logging


def test_get_log_path():
    p = get_log_path()
    assert isinstance(p, Path)
    assert p.name == "voiceflow.log"
    assert "VoiceFlow" in str(p)


def test_logger_name():
    assert logger.name == "voiceflow"


def test_setup_logging_adds_handler():
    setup_logging()
    root = logging.getLogger("voiceflow")
    assert root.level == logging.DEBUG
    handler_types = [type(h).__name__ for h in root.handlers]
    assert "RotatingFileHandler" in handler_types


def test_log_dir_created():
    setup_logging()
    assert get_log_path().parent.is_dir()

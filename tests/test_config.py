"""Tests for config loading."""

from __future__ import annotations

import textwrap
from pathlib import Path

from voiceflow.config import (
    Config,
    HotkeyConfig,
    PasteConfig,
    ToggleHotkeyConfig,
    load_config,
)


def test_defaults():
    cfg = Config()
    assert cfg.hotkey == HotkeyConfig()
    assert cfg.hotkey_toggle == ToggleHotkeyConfig()
    assert cfg.paste == PasteConfig()
    assert cfg.hotkey_toggle.key == ""
    assert cfg.hotkey_toggle.modifier == ""
    assert cfg.paste.clipboard_restore_delay == 0.5


def test_load_missing_file_returns_defaults(tmp_path: Path):
    cfg = load_config(tmp_path / "nonexistent.toml")
    assert cfg == Config()


def test_load_toggle_section(tmp_path: Path):
    toml = tmp_path / "config.toml"
    toml.write_text(textwrap.dedent("""\
        [hotkey_toggle]
        key = "Key.f6"
        modifier = "Key.ctrl"
    """))
    cfg = load_config(toml)
    assert cfg.hotkey_toggle.key == "Key.f6"
    assert cfg.hotkey_toggle.modifier == "Key.ctrl"


def test_load_paste_restore_delay(tmp_path: Path):
    toml = tmp_path / "config.toml"
    toml.write_text(textwrap.dedent("""\
        [paste]
        clipboard_restore_delay = 1.5
    """))
    cfg = load_config(toml)
    assert cfg.paste.clipboard_restore_delay == 1.5


def test_load_ignores_unknown_keys(tmp_path: Path):
    toml = tmp_path / "config.toml"
    toml.write_text(textwrap.dedent("""\
        [hotkey_toggle]
        key = "Key.f6"
        unknown_field = true
    """))
    cfg = load_config(toml)
    assert cfg.hotkey_toggle.key == "Key.f6"


def test_load_spoken_commands(tmp_path: Path):
    toml = tmp_path / "config.toml"
    toml.write_text(textwrap.dedent("""\
        [spoken_commands]
        "new line" = "\\n"
    """))
    cfg = load_config(toml)
    assert cfg.spoken_commands == {"new line": "\n"}


def test_full_config_loads(tmp_path: Path):
    """The real config.toml should load without error."""
    real = Path(__file__).resolve().parent.parent / "config.toml"
    if real.exists():
        cfg = load_config(real)
        assert cfg.hotkey.key
        assert cfg.paste.clipboard_restore_delay > 0

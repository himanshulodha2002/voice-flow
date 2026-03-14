"""Tests for SystemInterface — hotkey logic (no real keyboard/clipboard)."""

from __future__ import annotations

from unittest.mock import MagicMock

from voiceflow.config import HotkeyConfig, PasteConfig, ToggleHotkeyConfig
from voiceflow.system import SystemInterface


def _make_si(
    hotkey="Key.cmd",
    modifier="Key.ctrl",
    toggle_key="",
    toggle_modifier="",
) -> tuple[SystemInterface, MagicMock, MagicMock]:
    on_press = MagicMock()
    on_release = MagicMock()
    si = SystemInterface(
        hotkey_cfg=HotkeyConfig(key=hotkey, modifier=modifier),
        toggle_cfg=ToggleHotkeyConfig(key=toggle_key, modifier=toggle_modifier),
        paste_cfg=PasteConfig(),
        on_press=on_press,
        on_release=on_release,
    )
    return si, on_press, on_release


class FakeKey:
    """Mimics a pynput Key object whose str() returns the given name."""

    def __init__(self, name: str):
        self._name = name

    def __str__(self):
        return self._name


# --- PTT (push-to-talk) mode tests ---

class TestPTT:
    def test_press_with_modifier(self):
        si, on_press, _ = _make_si(hotkey="Key.cmd", modifier="Key.ctrl")
        si._on_key_press(FakeKey("Key.ctrl_l"))  # modifier
        si._on_key_press(FakeKey("Key.cmd"))      # hotkey
        on_press.assert_called_once()

    def test_press_without_modifier_held(self):
        si, on_press, _ = _make_si(hotkey="Key.cmd", modifier="Key.ctrl")
        si._on_key_press(FakeKey("Key.cmd"))
        on_press.assert_not_called()

    def test_release_modifier_triggers_release(self):
        si, on_press, on_release = _make_si(hotkey="Key.cmd", modifier="Key.ctrl")
        si._on_key_press(FakeKey("Key.ctrl_l"))
        si._on_key_press(FakeKey("Key.cmd"))
        si._on_key_release(FakeKey("Key.ctrl_l"))
        on_release.assert_called_once()

    def test_release_hotkey_triggers_release(self):
        si, _, on_release = _make_si(hotkey="Key.cmd", modifier="Key.ctrl")
        si._on_key_press(FakeKey("Key.ctrl_l"))
        si._on_key_press(FakeKey("Key.cmd"))
        si._on_key_release(FakeKey("Key.cmd"))
        on_release.assert_called_once()

    def test_no_modifier_mode(self):
        si, on_press, on_release = _make_si(hotkey="Key.f5", modifier="")
        si._on_key_press(FakeKey("Key.f5"))
        on_press.assert_called_once()
        si._on_key_release(FakeKey("Key.f5"))
        on_release.assert_called_once()

    def test_pasting_suppresses_keys(self):
        si, on_press, on_release = _make_si(hotkey="Key.f5", modifier="")
        si._pasting = True
        si._on_key_press(FakeKey("Key.f5"))
        si._on_key_release(FakeKey("Key.f5"))
        on_press.assert_not_called()
        on_release.assert_not_called()


# --- Toggle mode tests ---

class TestToggle:
    def test_toggle_on_calls_press(self):
        si, on_press, _ = _make_si(toggle_key="Key.f6", toggle_modifier="")
        si._on_key_press(FakeKey("Key.f6"))
        on_press.assert_called_once()
        assert si._toggle_active is True

    def test_toggle_off_calls_release(self):
        si, _, on_release = _make_si(toggle_key="Key.f6", toggle_modifier="")
        si._on_key_press(FakeKey("Key.f6"))  # on
        si._on_key_press(FakeKey("Key.f6"))  # off
        on_release.assert_called_once()
        assert si._toggle_active is False

    def test_toggle_with_modifier(self):
        si, on_press, _ = _make_si(
            toggle_key="Key.f6", toggle_modifier="Key.ctrl",
        )
        si._on_key_press(FakeKey("Key.ctrl_l"))  # toggle modifier
        si._on_key_press(FakeKey("Key.f6"))       # toggle key
        on_press.assert_called_once()
        assert si._toggle_active is True

    def test_toggle_without_modifier_held_no_toggle(self):
        si, on_press, _ = _make_si(
            toggle_key="Key.f6", toggle_modifier="Key.ctrl",
        )
        # Press toggle key without modifier held — should NOT toggle
        si._on_key_press(FakeKey("Key.f6"))
        on_press.assert_not_called()
        assert si._toggle_active is False

    def test_ptt_disabled_while_toggle_active(self):
        si, on_press, _ = _make_si(
            hotkey="Key.cmd", modifier="Key.ctrl",
            toggle_key="Key.f6", toggle_modifier="",
        )
        si._on_key_press(FakeKey("Key.f6"))  # toggle on
        on_press.assert_called_once()
        on_press.reset_mock()
        # Now try PTT — should be suppressed
        si._on_key_press(FakeKey("Key.ctrl_l"))
        si._on_key_press(FakeKey("Key.cmd"))
        on_press.assert_not_called()


# --- Modifier matching ---

class TestModifierMatches:
    def test_exact_match(self):
        si, _, _ = _make_si()
        assert si._modifier_matches(FakeKey("Key.ctrl"), "Key.ctrl")

    def test_left_variant(self):
        si, _, _ = _make_si()
        assert si._modifier_matches(FakeKey("Key.ctrl_l"), "Key.ctrl")

    def test_right_variant(self):
        si, _, _ = _make_si()
        assert si._modifier_matches(FakeKey("Key.ctrl_r"), "Key.ctrl")

    def test_no_match(self):
        si, _, _ = _make_si()
        assert not si._modifier_matches(FakeKey("Key.alt"), "Key.ctrl")

    def test_empty_modifier(self):
        si, _, _ = _make_si()
        assert not si._modifier_matches(FakeKey("Key.ctrl"), "")

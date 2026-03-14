"""System interface — hotkey listener and clipboard paste."""

from __future__ import annotations

import subprocess
import threading
import time
from collections.abc import Callable

from voiceflow.config import HotkeyConfig, PasteConfig, ToggleHotkeyConfig
from voiceflow.log import logger


class SystemInterface:
    """Handles hotkey listening and clipboard paste."""

    def __init__(
        self,
        hotkey_cfg: HotkeyConfig,
        toggle_cfg: ToggleHotkeyConfig,
        paste_cfg: PasteConfig,
        on_press: Callable[[], None],
        on_release: Callable[[], None],
    ) -> None:
        self._hotkey = hotkey_cfg.key
        self._modifier = hotkey_cfg.modifier
        self._paste_cfg = paste_cfg
        self._on_press_cb = on_press
        self._on_release_cb = on_release
        self._listener = None
        self._modifier_held = False
        self._pasting = False

        # Toggle mode
        self._toggle_key = toggle_cfg.key if toggle_cfg.key else None
        self._toggle_modifier = toggle_cfg.modifier if toggle_cfg.modifier else None
        self._toggle_modifier_held = False
        self._toggle_active = False

    def _key_str(self, key) -> str:
        return str(key)

    def _modifier_matches(self, key, modifier: str) -> bool:
        if not modifier:
            return False
        s = self._key_str(key)
        return s == modifier or s in (modifier + "_l", modifier + "_r")

    def _on_key_press(self, key):
        if self._pasting:
            return

        ks = self._key_str(key)

        # --- Toggle hotkey handling ---
        if self._toggle_key:
            if self._toggle_modifier and self._modifier_matches(key, self._toggle_modifier):
                self._toggle_modifier_held = True
            elif self._toggle_modifier:
                if ks == self._toggle_key and self._toggle_modifier_held:
                    self._handle_toggle()
                    return
            else:
                if ks == self._toggle_key:
                    self._handle_toggle()
                    return

        # --- PTT hotkey handling ---
        if self._toggle_active:
            return  # PTT disabled while toggle is active
        if self._modifier:
            if self._modifier_matches(key, self._modifier):
                self._modifier_held = True
                return
            if ks == self._hotkey and self._modifier_held:
                self._on_press_cb()
        else:
            if ks == self._hotkey:
                self._on_press_cb()

    def _on_key_release(self, key):
        if self._pasting:
            return

        ks = self._key_str(key)

        # --- Toggle modifier release ---
        if self._toggle_modifier and self._modifier_matches(key, self._toggle_modifier):
            self._toggle_modifier_held = False

        # --- PTT handling ---
        if self._toggle_active:
            return
        if self._modifier:
            if self._modifier_matches(key, self._modifier):
                self._modifier_held = False
                self._on_release_cb()
                return
            if ks == self._hotkey:
                self._on_release_cb()
        else:
            if ks == self._hotkey:
                self._on_release_cb()

    def _handle_toggle(self) -> None:
        self._toggle_active = not self._toggle_active
        if self._toggle_active:
            logger.info("Toggle recording ON")
            self._on_press_cb()
        else:
            logger.info("Toggle recording OFF")
            self._on_release_cb()

    def start_listener(self) -> None:
        """Start the keyboard listener. Returns immediately (daemon thread)."""
        from pynput.keyboard import Listener

        self._listener = Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
        )
        self._listener.start()

    def stop_listener(self) -> None:
        if self._listener:
            self._listener.stop()

    def paste_text(self, text: str) -> None:
        """Copy text to clipboard via pbcopy, simulate Cmd+V, then restore original clipboard."""
        # Save current clipboard
        original = None
        try:
            result = subprocess.run(
                ["pbpaste"], capture_output=True, timeout=2,
            )
            if result.returncode == 0:
                original = result.stdout
        except Exception:
            pass

        subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
        time.sleep(0.05)
        self._pasting = True
        try:
            subprocess.run(
                [
                    "osascript", "-e",
                    'tell application "System Events" to keystroke "v" using command down',
                ],
                check=True,
                timeout=3,
            )
            time.sleep(0.05)
        finally:
            self._pasting = False

        # Restore original clipboard after a short delay
        if original is not None:
            threading.Timer(
                self._paste_cfg.clipboard_restore_delay,
                _restore_clipboard,
                args=(original,),
            ).start()
        else:
            threading.Timer(
                self._paste_cfg.clipboard_restore_delay,
                _clear_clipboard,
            ).start()


def _restore_clipboard(data: bytes) -> None:
    try:
        subprocess.run(["pbcopy"], input=data, check=True)
    except Exception:
        pass


def _clear_clipboard() -> None:
    try:
        subprocess.run(["pbcopy"], input=b"", check=True)
    except Exception:
        pass

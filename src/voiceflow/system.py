"""System interface — hotkey listener and clipboard paste."""

from __future__ import annotations

import subprocess
import threading
import time
from collections.abc import Callable

from voiceflow.config import HotkeyConfig, PasteConfig


class SystemInterface:
    """Handles hotkey listening and clipboard paste."""

    def __init__(
        self,
        hotkey_cfg: HotkeyConfig,
        paste_cfg: PasteConfig,
        on_press: Callable[[], None],
        on_release: Callable[[], None],
    ) -> None:
        self._hotkey = hotkey_cfg.key
        self._modifier = hotkey_cfg.modifier  # e.g. "Key.alt" — empty means no modifier
        self._paste_cfg = paste_cfg
        self._on_press_cb = on_press
        self._on_release_cb = on_release
        self._listener = None
        self._modifier_held = False
        self._pasting = False

    def _key_str(self, key) -> str:
        return str(key)

    def _modifier_matches(self, key) -> bool:
        if not self._modifier:
            return False
        s = self._key_str(key)
        # Match either side (e.g. Key.alt matches Key.alt_l and Key.alt_r too)
        return s == self._modifier or s in (self._modifier + "_l", self._modifier + "_r")

    def _on_key_press(self, key):
        if self._pasting:
            return
        if self._modifier:
            if self._modifier_matches(key):
                self._modifier_held = True
                return
            if self._key_str(key) == self._hotkey and self._modifier_held:
                self._on_press_cb()
        else:
            if self._key_str(key) == self._hotkey:
                self._on_press_cb()

    def _on_key_release(self, key):
        if self._pasting:
            return
        if self._modifier:
            if self._modifier_matches(key):
                self._modifier_held = False
                # Releasing the modifier also stops recording
                self._on_release_cb()
                return
            if self._key_str(key) == self._hotkey:
                self._on_release_cb()
        else:
            if self._key_str(key) == self._hotkey:
                self._on_release_cb()

    def start_listener(self) -> None:
        """Start the keyboard listener. Blocks the calling thread."""
        from pynput.keyboard import Listener

        self._listener = Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
        )
        self._listener.start()
        self._listener.join()

    def stop_listener(self) -> None:
        if self._listener:
            self._listener.stop()

    def paste_text(self, text: str) -> None:
        """Copy text to clipboard via pbcopy, then simulate Cmd+V, then clear clipboard."""
        subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
        time.sleep(0.05)
        from pynput.keyboard import Controller, Key

        kb = Controller()
        self._pasting = True
        try:
            kb.press(Key.cmd)
            kb.press("v")
            kb.release("v")
            kb.release(Key.cmd)
        finally:
            self._pasting = False
        # Clear clipboard after a short delay so dictated text doesn't linger
        threading.Timer(self._paste_cfg.clipboard_clear_delay, _clear_clipboard).start()


def _clear_clipboard() -> None:
    try:
        subprocess.run(["pbcopy"], input=b"", check=True)
    except Exception:
        pass

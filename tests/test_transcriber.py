"""Tests for SpeechTranscriber — load/unload lifecycle (no real Whisper)."""

from __future__ import annotations

from voiceflow.config import WhisperConfig
from voiceflow.transcriber import SpeechTranscriber


class TestIsLoaded:
    def test_not_loaded_initially(self):
        t = SpeechTranscriber(WhisperConfig())
        assert not t.is_loaded

    def test_loaded_after_setting_module(self):
        t = SpeechTranscriber(WhisperConfig())
        t._mlx_whisper = "fake"
        assert t.is_loaded


class TestUnload:
    def test_unload_clears_module(self):
        t = SpeechTranscriber(WhisperConfig())
        t._mlx_whisper = "fake"
        t.unload()
        assert t._mlx_whisper is None
        assert not t.is_loaded

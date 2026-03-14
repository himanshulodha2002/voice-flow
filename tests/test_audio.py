"""Tests for AudioRecorder — basic start/stop logic."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np

from voiceflow.config import AudioConfig
from voiceflow.audio import AudioRecorder


class TestAudioRecorder:
    def test_stop_without_start_returns_none(self):
        r = AudioRecorder(AudioConfig())
        assert r.stop() is None

    def test_stop_with_no_chunks_returns_none(self):
        r = AudioRecorder(AudioConfig())
        r._stream = MagicMock()
        r._chunks = []
        result = r.stop()
        assert result is None

    def test_stop_short_recording_returns_none(self):
        cfg = AudioConfig(min_record_seconds=0.3, sample_rate=16_000)
        r = AudioRecorder(cfg)
        r._stream = MagicMock()
        # Less than 0.3s at 16kHz = 4800 samples
        r._chunks = [np.zeros(100, dtype=np.float32)]
        result = r.stop()
        assert result is None

    def test_stop_silence_returns_none(self):
        cfg = AudioConfig(silence_rms_threshold=0.003, sample_rate=16_000)
        r = AudioRecorder(cfg)
        r._stream = MagicMock()
        r._chunks = [np.zeros(16_000, dtype=np.float32)]  # pure silence
        result = r.stop()
        assert result is None

    def test_stop_valid_audio_returns_array(self):
        cfg = AudioConfig(
            sample_rate=16_000,
            min_record_seconds=0.1,
            silence_rms_threshold=0.001,
            max_record_seconds=30.0,
        )
        r = AudioRecorder(cfg)
        r._stream = MagicMock()
        # 1 second of non-silent audio
        r._chunks = [np.full(16_000, 0.1, dtype=np.float32)]
        result = r.stop()
        assert result is not None
        assert len(result) == 16_000

    def test_stop_truncates_to_max(self):
        cfg = AudioConfig(
            sample_rate=16_000,
            min_record_seconds=0.1,
            silence_rms_threshold=0.001,
            max_record_seconds=1.0,
        )
        r = AudioRecorder(cfg)
        r._stream = MagicMock()
        # 2 seconds of audio, should be truncated to 1s
        r._chunks = [np.full(32_000, 0.1, dtype=np.float32)]
        result = r.stop()
        assert result is not None
        assert len(result) == 16_000

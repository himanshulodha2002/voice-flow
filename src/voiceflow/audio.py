"""Audio recording via sounddevice."""

from __future__ import annotations

import numpy as np
import sounddevice as sd

from voiceflow.config import AudioConfig


class AudioRecorder:
    """Records audio from the default mic as 16kHz mono float32 numpy arrays."""

    def __init__(self, cfg: AudioConfig) -> None:
        self._cfg = cfg
        self._stream: sd.InputStream | None = None
        self._chunks: list[np.ndarray] = []

    def _callback(self, indata, frames, time_info, status):
        self._chunks.append(indata[:, 0].copy())

    def start(self) -> None:
        self._chunks = []
        self._stream = sd.InputStream(
            samplerate=self._cfg.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=self._cfg.block_size,
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> np.ndarray | None:
        """Stop recording. Returns 1D float32 array, or None if silence/too short."""
        if self._stream is None:
            return None
        self._stream.stop()
        self._stream.close()
        self._stream = None

        if not self._chunks:
            return None

        audio = np.concatenate(self._chunks)
        duration = len(audio) / self._cfg.sample_rate

        if duration < self._cfg.min_record_seconds:
            return None

        rms = float(np.sqrt(np.mean(audio**2)))
        if rms < self._cfg.silence_rms_threshold:
            return None

        max_samples = int(self._cfg.max_record_seconds * self._cfg.sample_rate)
        return audio[:max_samples]

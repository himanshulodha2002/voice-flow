"""Whisper speech-to-text via mlx-whisper."""

from __future__ import annotations

import numpy as np

from voiceflow.config import WhisperConfig


class SpeechTranscriber:
    """Whisper speech-to-text via mlx-whisper."""

    def __init__(self, cfg: WhisperConfig) -> None:
        self._cfg = cfg

    def warmup(self) -> None:
        import mlx_whisper

        print(f"  Warming up Whisper ({self._cfg.model})...")
        silence = np.zeros(16_000, dtype=np.float32)
        mlx_whisper.transcribe(
            silence,
            path_or_hf_repo=self._cfg.model,
            language=self._cfg.language,
        )

    def transcribe(self, audio: np.ndarray) -> str:
        import mlx_whisper

        kwargs: dict = dict(
            path_or_hf_repo=self._cfg.model,
            language=self._cfg.language,
            condition_on_previous_text=False,
        )
        if self._cfg.revision:
            kwargs["revision"] = self._cfg.revision

        result = mlx_whisper.transcribe(audio, **kwargs)
        return result.get("text", "").strip()

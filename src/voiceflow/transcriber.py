"""Whisper speech-to-text via mlx-whisper."""

from __future__ import annotations

from types import ModuleType

import numpy as np

from voiceflow.config import WhisperConfig


class SpeechTranscriber:
    """Whisper speech-to-text via mlx-whisper."""

    def __init__(self, cfg: WhisperConfig) -> None:
        self._cfg = cfg
        self._mlx_whisper: ModuleType | None = None

    def warmup(self) -> None:
        import mlx_whisper
        self._mlx_whisper = mlx_whisper

        print(f"  Loading Whisper ({self._cfg.model})...", flush=True)
        silence = np.zeros(16_000, dtype=np.float32)
        self._transcribe(silence)
        print("  Whisper ready.", flush=True)

    def transcribe(self, audio: np.ndarray) -> str:
        return self._transcribe(audio)

    def _transcribe(self, audio: np.ndarray) -> str:
        kwargs: dict = {}
        if self._cfg.revision:
            kwargs["revision"] = self._cfg.revision
        result = self._mlx_whisper.transcribe(
            audio,
            path_or_hf_repo=self._cfg.model,
            language=self._cfg.language,
            condition_on_previous_text=False,
            **kwargs,
        )
        return result.get("text", "").strip()

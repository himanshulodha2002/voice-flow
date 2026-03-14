"""Whisper speech-to-text via mlx-whisper."""

from __future__ import annotations

from types import ModuleType

import numpy as np

from voiceflow.config import WhisperConfig
from voiceflow.log import logger


class SpeechTranscriber:
    """Whisper speech-to-text via mlx-whisper."""

    def __init__(self, cfg: WhisperConfig) -> None:
        self._cfg = cfg
        self._mlx_whisper: ModuleType | None = None
        self._resolved_path: str = cfg.model

    @property
    def is_loaded(self) -> bool:
        return self._mlx_whisper is not None

    def warmup(self) -> None:
        import mlx_whisper
        self._mlx_whisper = mlx_whisper

        # Pin to a specific revision by resolving the HF repo to a local snapshot
        if self._cfg.revision:
            from huggingface_hub import snapshot_download
            self._resolved_path = snapshot_download(
                self._cfg.model, revision=self._cfg.revision,
            )
        else:
            self._resolved_path = self._cfg.model

        logger.info("Loading Whisper (%s)...", self._cfg.model)
        silence = np.zeros(16_000, dtype=np.float32)
        self._transcribe(silence)
        logger.info("Whisper ready.")

    def unload(self) -> None:
        try:
            from mlx_whisper.transcribe import ModelHolder
            ModelHolder.model = None
            ModelHolder.model_path = None
        except Exception:
            pass
        self._mlx_whisper = None
        logger.info("Whisper model unloaded.")

    def transcribe(self, audio: np.ndarray) -> str:
        return self._transcribe(audio)

    def _transcribe(self, audio: np.ndarray) -> str:
        result = self._mlx_whisper.transcribe(
            audio,
            path_or_hf_repo=self._resolved_path,
            language=self._cfg.language,
            condition_on_previous_text=False,
        )
        return result.get("text", "").strip()

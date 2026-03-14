"""Pipeline — orchestrates hotkey → record → transcribe → rewrite → paste."""

from __future__ import annotations

import enum
import gc
import queue
import threading
import time
from collections.abc import Callable

import numpy as np

from voiceflow.audio import AudioRecorder
from voiceflow.config import Config
from voiceflow.log import logger
from voiceflow.rewriter import TextRewriter
from voiceflow.system import SystemInterface
from voiceflow.transcriber import SpeechTranscriber

_QUEUE_MAX = 4  # max pending recordings; oldest dropped if exceeded


class PipelineState(enum.Enum):
    IDLE = "idle"
    RECORDING = "recording"
    PROCESSING = "processing"
    MODELS_LOADING = "models_loading"
    MODELS_UNLOADED = "models_unloaded"


class VoiceTypePipeline:
    """Orchestrates: hotkey → record → transcribe → rewrite → paste."""

    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg
        self._recorder = AudioRecorder(cfg.audio)
        self._transcriber = SpeechTranscriber(cfg.whisper)
        self._rewriter = TextRewriter(cfg.rewriter)
        self._system = SystemInterface(
            hotkey_cfg=cfg.hotkey,
            toggle_cfg=cfg.hotkey_toggle,
            paste_cfg=cfg.paste,
            on_press=self._on_hotkey_press,
            on_release=self._on_hotkey_release,
        )
        self._is_recording = False
        self._record_timeout: threading.Timer | None = None
        self._audio_queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=_QUEUE_MAX)
        self._ready = threading.Event()
        self._state = PipelineState.MODELS_UNLOADED
        self._state_cb: Callable[[PipelineState], None] | None = None

    def set_state_callback(self, cb: Callable[[PipelineState], None]) -> None:
        self._state_cb = cb

    def _set_state(self, state: PipelineState) -> None:
        self._state = state
        logger.debug("State → %s", state.value)
        if self._state_cb:
            try:
                self._state_cb(state)
            except Exception:
                pass

    @property
    def state(self) -> PipelineState:
        return self._state

    def run(self) -> None:
        """Start listener + worker + warmup. Returns immediately (non-blocking)."""
        logger.info("VoiceFlow starting up")
        threading.Thread(target=self._worker, daemon=True).start()
        self._system.start_listener()
        self.load_models()

    def stop(self) -> None:
        self._system.stop_listener()

    def load_models(self) -> None:
        """Load models in a background thread."""
        self._set_state(PipelineState.MODELS_LOADING)

        def _warmup() -> None:
            try:
                self._transcriber.warmup()
                self._rewriter.warmup()
                self._ready.set()
                self._set_state(PipelineState.IDLE)
                logger.info("Models loaded — ready for dictation.")
            except Exception as e:
                logger.error("Model loading failed: %s", e)
                self._set_state(PipelineState.MODELS_UNLOADED)

        threading.Thread(target=_warmup, daemon=True).start()

    def unload_models(self) -> None:
        """Unload models and free GPU memory."""
        self._ready.clear()
        self._transcriber.unload()
        self._rewriter.unload()
        gc.collect()
        try:
            import mlx.core as mx
            mx.metal.clear_cache()
        except Exception:
            pass
        self._set_state(PipelineState.MODELS_UNLOADED)
        logger.info("Models unloaded, GPU memory freed.")

    def _on_hotkey_press(self) -> None:
        if self._is_recording:
            return
        if not self._ready.is_set():
            logger.warning("Models not ready, ignoring hotkey.")
            return
        self._is_recording = True
        self._recorder.start()
        self._set_state(PipelineState.RECORDING)
        logger.info("Recording started")
        self._record_timeout = threading.Timer(
            self._cfg.audio.max_record_seconds, self._on_hotkey_release
        )
        self._record_timeout.daemon = True
        self._record_timeout.start()

    def _on_hotkey_release(self) -> None:
        if not self._is_recording:
            return
        self._is_recording = False
        if self._record_timeout is not None:
            self._record_timeout.cancel()
            self._record_timeout = None
        audio = self._recorder.stop()
        if audio is None:
            logger.info("No speech detected")
            self._set_state(PipelineState.IDLE)
            return
        try:
            self._audio_queue.put_nowait(audio)
            queued = self._audio_queue.qsize()
            if queued > 1:
                logger.info("Queued — %d pending", queued)
        except queue.Full:
            logger.warning("Queue full, oldest dropped")
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                pass
            self._audio_queue.put_nowait(audio)

    def _worker(self) -> None:
        """Single background thread — processes queued audio clips in order."""
        while True:
            audio = self._audio_queue.get()
            try:
                self._set_state(PipelineState.PROCESSING)
                self._process_pipeline(audio)
            finally:
                self._audio_queue.task_done()
                if self._ready.is_set():
                    self._set_state(PipelineState.IDLE)

    def _process_pipeline(self, audio: np.ndarray) -> None:
        try:
            t0 = time.perf_counter()

            duration = len(audio) / self._cfg.audio.sample_rate
            logger.info("Audio: %.1fs", duration)

            t1 = time.perf_counter()
            raw_text = self._transcriber.transcribe(audio)
            t2 = time.perf_counter()

            if not raw_text.strip():
                logger.info("Empty transcription")
                return

            logger.info("Raw:     %s", raw_text)

            cleaned = self._rewriter.rewrite(raw_text)
            t3 = time.perf_counter()

            cleaned = _apply_spoken_commands(cleaned, self._cfg.spoken_commands)

            logger.info("Cleaned: %s", cleaned)

            self._system.paste_text(cleaned)
            t4 = time.perf_counter()

            logger.info(
                "whisper:%dms rewrite:%dms paste:%dms total:%dms",
                (t2 - t1) * 1000, (t3 - t2) * 1000,
                (t4 - t3) * 1000, (t4 - t0) * 1000,
            )
        except Exception as e:
            logger.error("Pipeline error: %s", e)


def _apply_spoken_commands(text: str, commands: dict[str, str]) -> str:
    for phrase, replacement in commands.items():
        lower = text.lower()
        idx = lower.find(phrase)
        while idx != -1:
            text = text[:idx] + replacement + text[idx + len(phrase) :]
            lower = text.lower()
            idx = lower.find(phrase, idx + len(replacement))
    return text.strip()

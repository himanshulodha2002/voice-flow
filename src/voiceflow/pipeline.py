"""Pipeline — orchestrates hotkey → record → transcribe → rewrite → paste."""

from __future__ import annotations

import queue
import threading
import time

import numpy as np

from voiceflow.audio import AudioRecorder
from voiceflow.config import Config
from voiceflow.rewriter import TextRewriter
from voiceflow.system import SystemInterface
from voiceflow.transcriber import SpeechTranscriber

_QUEUE_MAX = 4  # max pending recordings; oldest dropped if exceeded


class VoiceTypePipeline:
    """Orchestrates: hotkey → record → transcribe → rewrite → paste."""

    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg
        self._recorder = AudioRecorder(cfg.audio)
        self._transcriber = SpeechTranscriber(cfg.whisper)
        self._rewriter = TextRewriter(cfg.rewriter)
        self._system = SystemInterface(
            hotkey_cfg=cfg.hotkey,
            paste_cfg=cfg.paste,
            on_press=self._on_hotkey_press,
            on_release=self._on_hotkey_release,
        )
        self._is_recording = False
        self._record_timeout: threading.Timer | None = None
        self._audio_queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=_QUEUE_MAX)
        self._ready = threading.Event()

    def run(self) -> None:
        print("VoiceFlow — Local Voice Typing")
        print("=" * 40)
        print("Warming up models in background (first run downloads ~1GB)...")
        print("Hotkey is active — dictation will begin once models are ready.")
        print("=" * 40)

        def _warmup() -> None:
            self._transcriber.warmup()
            self._rewriter.warmup()
            self._ready.set()
            print("Ready! Hold Control+Command (⌃⌘) to dictate.", flush=True)
            print("Press Ctrl+C to quit.\n", flush=True)

        threading.Thread(target=_warmup, daemon=True).start()
        threading.Thread(target=self._worker, daemon=True).start()

        # Blocks until stop() is called or process exits
        self._system.start_listener()

    def stop(self) -> None:
        self._system.stop_listener()

    def _on_hotkey_press(self) -> None:
        if self._is_recording:
            return
        if not self._ready.is_set():
            print("  [still warming up, please wait...]", flush=True)
            return
        self._is_recording = True
        self._recorder.start()
        print("● Recording...", flush=True)
        # Safety net: auto-release if the key-up event is missed (e.g. system busy)
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
            print("  [no speech detected]")
            return
        try:
            self._audio_queue.put_nowait(audio)
            queued = self._audio_queue.qsize()
            if queued > 1:
                print(f"  [queued — {queued} pending]", flush=True)
        except queue.Full:
            print("  [queue full, oldest dropped]", flush=True)
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
                self._process_pipeline(audio)
            finally:
                self._audio_queue.task_done()

    def _process_pipeline(self, audio: np.ndarray) -> None:
        try:
            t0 = time.perf_counter()

            duration = len(audio) / self._cfg.audio.sample_rate
            print(f"  Audio: {duration:.1f}s", flush=True)

            t1 = time.perf_counter()
            raw_text = self._transcriber.transcribe(audio)
            t2 = time.perf_counter()

            if not raw_text.strip():
                print("  [empty transcription]")
                return

            print(f"  Raw:     {raw_text}")

            cleaned = self._rewriter.rewrite(raw_text)
            t3 = time.perf_counter()

            cleaned = _apply_spoken_commands(cleaned, self._cfg.spoken_commands)

            print(f"  Cleaned: {cleaned}")

            self._system.paste_text(cleaned)
            t4 = time.perf_counter()

            print(
                f"  [whisper:{(t2 - t1) * 1000:.0f}ms "
                f"rewrite:{(t3 - t2) * 1000:.0f}ms "
                f"paste:{(t4 - t3) * 1000:.0f}ms "
                f"total:{(t4 - t0) * 1000:.0f}ms]"
            )
        except Exception as e:
            print(f"  [error: {e}]")


def _apply_spoken_commands(text: str, commands: dict[str, str]) -> str:
    for phrase, replacement in commands.items():
        lower = text.lower()
        idx = lower.find(phrase)
        while idx != -1:
            text = text[:idx] + replacement + text[idx + len(phrase) :]
            lower = text.lower()
            idx = lower.find(phrase, idx + len(replacement))
    return text.strip()

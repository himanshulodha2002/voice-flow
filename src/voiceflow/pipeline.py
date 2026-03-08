"""Pipeline — orchestrates hotkey → record → transcribe → rewrite → paste."""

from __future__ import annotations

import threading
import time

from voiceflow.audio import AudioRecorder
from voiceflow.config import Config
from voiceflow.rewriter import TextRewriter
from voiceflow.system import SystemInterface
from voiceflow.transcriber import SpeechTranscriber


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
        self._process_lock = threading.Lock()

    def run(self) -> None:
        print("VoiceFlow — Local Voice Typing")
        print("=" * 40)
        print("Warming up models (first run downloads ~1GB)...")
        self._transcriber.warmup()
        self._rewriter.warmup()
        print("=" * 40)
        print(f"Ready! Hold {self._cfg.hotkey.key} to dictate.")
        print("Press Ctrl+C to quit.\n")
        self._system.start_listener()

    def stop(self) -> None:
        self._system.stop_listener()

    def _on_hotkey_press(self) -> None:
        if self._is_recording:
            return
        self._is_recording = True
        self._recorder.start()
        print("● Recording...", flush=True)

    def _on_hotkey_release(self) -> None:
        if not self._is_recording:
            return
        self._is_recording = False
        t = threading.Thread(target=self._process_pipeline, daemon=True)
        t.start()

    def _process_pipeline(self) -> None:
        if not self._process_lock.acquire(blocking=False):
            self._recorder.stop()
            print("  [busy, skipped]")
            return

        try:
            t0 = time.perf_counter()

            audio = self._recorder.stop()
            if audio is None:
                print("  [no speech detected]")
                return

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
        finally:
            self._process_lock.release()


def _apply_spoken_commands(text: str, commands: dict[str, str]) -> str:
    for phrase, replacement in commands.items():
        lower = text.lower()
        idx = lower.find(phrase)
        while idx != -1:
            text = text[:idx] + replacement + text[idx + len(phrase) :]
            lower = text.lower()
            idx = lower.find(phrase, idx + len(replacement))
    return text.strip()

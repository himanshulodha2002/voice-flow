"""Tests for pipeline state management and spoken commands."""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

import numpy as np

from voiceflow.config import Config
from voiceflow.pipeline import PipelineState, VoiceTypePipeline, _apply_spoken_commands


# --- PipelineState enum ---

class TestPipelineState:
    def test_all_states_exist(self):
        names = {s.name for s in PipelineState}
        assert names == {"IDLE", "RECORDING", "PROCESSING", "MODELS_LOADING", "MODELS_UNLOADED"}

    def test_values(self):
        assert PipelineState.IDLE.value == "idle"
        assert PipelineState.MODELS_UNLOADED.value == "models_unloaded"


# --- State callback ---

class TestStateCallback:
    def _make_pipeline(self) -> VoiceTypePipeline:
        with patch("voiceflow.pipeline.AudioRecorder"), \
             patch("voiceflow.pipeline.SpeechTranscriber"), \
             patch("voiceflow.pipeline.TextRewriter"), \
             patch("voiceflow.pipeline.SystemInterface"):
            return VoiceTypePipeline(Config())

    def test_initial_state_is_unloaded(self):
        p = self._make_pipeline()
        assert p.state == PipelineState.MODELS_UNLOADED

    def test_set_state_callback_fires(self):
        p = self._make_pipeline()
        cb = MagicMock()
        p.set_state_callback(cb)
        p._set_state(PipelineState.IDLE)
        cb.assert_called_once_with(PipelineState.IDLE)

    def test_set_state_updates_property(self):
        p = self._make_pipeline()
        p._set_state(PipelineState.RECORDING)
        assert p.state == PipelineState.RECORDING

    def test_callback_exception_does_not_crash(self):
        p = self._make_pipeline()
        p.set_state_callback(MagicMock(side_effect=RuntimeError("boom")))
        # Should not raise
        p._set_state(PipelineState.IDLE)
        assert p.state == PipelineState.IDLE

    def test_no_callback_is_fine(self):
        p = self._make_pipeline()
        p._set_state(PipelineState.RECORDING)  # should not raise


# --- Hotkey handlers ---

class TestHotkeyHandlers:
    def _make_pipeline(self) -> VoiceTypePipeline:
        with patch("voiceflow.pipeline.AudioRecorder") as mock_rec, \
             patch("voiceflow.pipeline.SpeechTranscriber"), \
             patch("voiceflow.pipeline.TextRewriter"), \
             patch("voiceflow.pipeline.SystemInterface"):
            p = VoiceTypePipeline(Config())
            p._recorder = mock_rec.return_value
            return p

    def test_press_ignored_when_not_ready(self):
        p = self._make_pipeline()
        states = []
        p.set_state_callback(lambda s: states.append(s))
        p._on_hotkey_press()
        assert PipelineState.RECORDING not in states
        assert not p._is_recording

    def test_press_starts_recording_when_ready(self):
        p = self._make_pipeline()
        p._ready.set()
        p._on_hotkey_press()
        assert p._is_recording
        assert p.state == PipelineState.RECORDING
        p._recorder.start.assert_called_once()

    def test_press_ignored_if_already_recording(self):
        p = self._make_pipeline()
        p._ready.set()
        p._on_hotkey_press()
        p._recorder.start.reset_mock()
        p._on_hotkey_press()  # second press
        p._recorder.start.assert_not_called()

    def test_release_stops_recording(self):
        p = self._make_pipeline()
        p._ready.set()
        p._recorder.stop.return_value = None
        p._on_hotkey_press()
        p._on_hotkey_release()
        assert not p._is_recording
        p._recorder.stop.assert_called_once()

    def test_release_ignored_if_not_recording(self):
        p = self._make_pipeline()
        p._on_hotkey_release()
        p._recorder.stop.assert_not_called()

    def test_release_queues_audio(self):
        p = self._make_pipeline()
        p._ready.set()
        audio = np.zeros(16000, dtype=np.float32)
        p._recorder.stop.return_value = audio
        p._on_hotkey_press()
        p._on_hotkey_release()
        assert not p._audio_queue.empty()


# --- Model load/unload ---

class TestModelLifecycle:
    def _make_pipeline(self) -> VoiceTypePipeline:
        with patch("voiceflow.pipeline.AudioRecorder"), \
             patch("voiceflow.pipeline.SpeechTranscriber") as mock_t, \
             patch("voiceflow.pipeline.TextRewriter") as mock_r, \
             patch("voiceflow.pipeline.SystemInterface"):
            p = VoiceTypePipeline(Config())
            p._transcriber = mock_t.return_value
            p._rewriter = mock_r.return_value
            return p

    def test_unload_models(self):
        p = self._make_pipeline()
        p._ready.set()
        p.unload_models()
        p._transcriber.unload.assert_called_once()
        p._rewriter.unload.assert_called_once()
        assert not p._ready.is_set()
        assert p.state == PipelineState.MODELS_UNLOADED

    def test_load_models_sets_loading_state(self):
        p = self._make_pipeline()
        states = []
        p.set_state_callback(lambda s: states.append(s))
        p.load_models()
        assert PipelineState.MODELS_LOADING in states


# --- Spoken commands ---

class TestSpokenCommands:
    def test_single_replacement(self):
        # Surrounding spaces are preserved; only the phrase itself is replaced
        assert _apply_spoken_commands("hello new line world", {"new line": "\n"}) == "hello \n world"

    def test_multiple_replacements(self):
        result = _apply_spoken_commands("hi period bye period", {"period": "."})
        assert result == "hi . bye ."

    def test_case_insensitive(self):
        assert _apply_spoken_commands("Hello New Line world", {"new line": "\n"}) == "Hello \n world"

    def test_no_match(self):
        assert _apply_spoken_commands("hello world", {"goodbye": "bye"}) == "hello world"

    def test_empty_commands(self):
        assert _apply_spoken_commands("hello world", {}) == "hello world"

    def test_new_paragraph(self):
        result = _apply_spoken_commands("first new paragraph second", {"new paragraph": "\n\n"})
        assert result == "first \n\n second"

    def test_strips_result(self):
        assert _apply_spoken_commands("  hello  ", {}) == "hello"

    def test_adjacent_phrase(self):
        # When phrase is at start/end, no extra spaces
        result = _apply_spoken_commands("period", {"period": "."})
        assert result == "."

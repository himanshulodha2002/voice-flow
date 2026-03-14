"""Tests for VoiceFlowApp — title mapping and menu state (no real NSRunLoop)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from voiceflow.pipeline import PipelineState


class TestTitleMapping:
    def test_all_states_have_titles(self):
        from voiceflow.app import _TITLES
        for state in PipelineState:
            assert state in _TITLES

    def test_idle_title(self):
        from voiceflow.app import _TITLES
        assert _TITLES[PipelineState.IDLE] == "VF"

    def test_recording_title(self):
        from voiceflow.app import _TITLES
        assert _TITLES[PipelineState.RECORDING] == "VF ●"

    def test_processing_title(self):
        from voiceflow.app import _TITLES
        assert _TITLES[PipelineState.PROCESSING] == "VF ⟳"

    def test_loading_title(self):
        from voiceflow.app import _TITLES
        assert _TITLES[PipelineState.MODELS_LOADING] == "VF ↓"

    def test_unloaded_title(self):
        from voiceflow.app import _TITLES
        assert _TITLES[PipelineState.MODELS_UNLOADED] == "VF ○"


class TestMenuState:
    def _make_app(self):
        from voiceflow.app import VoiceFlowApp
        pipeline = MagicMock()
        app = VoiceFlowApp(pipeline)
        return app, pipeline

    def test_initial_title_is_loading(self):
        app, _ = self._make_app()
        assert app.title == "VF ↓"

    def test_update_to_idle(self):
        app, _ = self._make_app()
        app._update_menu(PipelineState.IDLE)
        assert app.title == "VF"

    def test_update_to_recording(self):
        app, _ = self._make_app()
        app._update_menu(PipelineState.RECORDING)
        assert app.title == "VF ●"

    def test_load_item_disabled_when_loaded(self):
        app, _ = self._make_app()
        app._update_menu(PipelineState.IDLE)
        # When models are loaded, Load should have no callback (grayed out)
        assert app._load_item.callback is None

    def test_unload_item_enabled_when_loaded(self):
        app, _ = self._make_app()
        app._update_menu(PipelineState.IDLE)
        assert app._unload_item.callback is not None

    def test_load_item_enabled_when_unloaded(self):
        app, _ = self._make_app()
        app._update_menu(PipelineState.MODELS_UNLOADED)
        assert app._load_item.callback is not None

    def test_unload_item_disabled_when_unloaded(self):
        app, _ = self._make_app()
        app._update_menu(PipelineState.MODELS_UNLOADED)
        assert app._unload_item.callback is None

    def test_on_load_calls_pipeline(self):
        app, pipeline = self._make_app()
        app._on_load(None)
        pipeline.load_models.assert_called_once()

    def test_on_unload_calls_pipeline(self):
        app, pipeline = self._make_app()
        app._on_unload(None)
        pipeline.unload_models.assert_called_once()

    def test_on_quit_stops_pipeline(self):
        app, pipeline = self._make_app()
        with patch("voiceflow.app.rumps") as mock_rumps:
            app._on_quit(None)
            pipeline.stop.assert_called_once()
            mock_rumps.quit_application.assert_called_once()

    def test_state_callback_registered(self):
        _, pipeline = self._make_app()
        pipeline.set_state_callback.assert_called_once()

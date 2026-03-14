"""macOS menubar app using rumps."""

from __future__ import annotations

import subprocess

import rumps

from voiceflow.log import get_log_path
from voiceflow.pipeline import PipelineState, VoiceTypePipeline

_TITLES = {
    PipelineState.IDLE: "VF",
    PipelineState.RECORDING: "VF ●",
    PipelineState.PROCESSING: "VF ⟳",
    PipelineState.MODELS_LOADING: "VF ↓",
    PipelineState.MODELS_UNLOADED: "VF ○",
}


class VoiceFlowApp(rumps.App):
    def __init__(self, pipeline: VoiceTypePipeline) -> None:
        super().__init__("VF ↓", quit_button=None)
        self._pipeline = pipeline

        self._load_item = rumps.MenuItem("Load Models", callback=self._on_load)
        self._unload_item = rumps.MenuItem("Unload Models", callback=self._on_unload)
        self._logs_item = rumps.MenuItem("Show Logs", callback=self._on_show_logs)
        self._quit_item = rumps.MenuItem("Quit", callback=self._on_quit)

        self.menu = [
            self._load_item,
            self._unload_item,
            None,  # separator
            self._logs_item,
            None,  # separator
            self._quit_item,
        ]

        pipeline.set_state_callback(self._on_state_change)
        self._update_menu(PipelineState.MODELS_LOADING)

    def _on_state_change(self, state: PipelineState) -> None:
        # rumps title/menu property updates are thread-safe via PyObjC
        self._update_menu(state)

    def _update_menu(self, state: PipelineState) -> None:
        self.title = _TITLES.get(state, "VF")
        models_loaded = state not in (
            PipelineState.MODELS_UNLOADED,
            PipelineState.MODELS_LOADING,
        )
        self._load_item.set_callback(None if models_loaded else self._on_load)
        self._unload_item.set_callback(self._on_unload if models_loaded else None)

    def _on_load(self, _) -> None:
        self._pipeline.load_models()

    def _on_unload(self, _) -> None:
        self._pipeline.unload_models()

    def _on_show_logs(self, _) -> None:
        log_path = get_log_path()
        subprocess.Popen(["open", "-a", "Console", str(log_path)])

    def _on_quit(self, _) -> None:
        self._pipeline.stop()
        rumps.quit_application()

"""Configuration loader — reads config.toml and exposes typed values."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config.toml"


@dataclass(frozen=True, slots=True)
class AudioConfig:
    sample_rate: int = 16_000
    block_size: int = 1024
    max_record_seconds: float = 30.0
    min_record_seconds: float = 0.3
    silence_rms_threshold: float = 0.003


@dataclass(frozen=True, slots=True)
class WhisperConfig:
    model: str = "mlx-community/whisper-small.en-mlx"
    revision: str = ""
    language: str = "en"


@dataclass(frozen=True, slots=True)
class RewriterConfig:
    model: str = "mlx-community/Qwen3.5-0.8B-4bit"
    revision: str = ""
    max_tokens: int = 150
    system_prompt: str = (
        "You are a dictation cleanup assistant. "
        "Fix the transcribed speech: remove filler words (um, uh, like, you know, so, basically), "
        "add proper punctuation and capitalization, fix obvious grammar errors. "
        "Keep the original meaning and wording. Do NOT add, explain, or comment. "
        "Output ONLY the cleaned text, nothing else."
    )
    max_length_ratio: float = 2.0
    min_word_overlap: float = 0.2


@dataclass(frozen=True, slots=True)
class HotkeyConfig:
    key: str = "Key.alt_r"
    modifier: str = ""


@dataclass(frozen=True, slots=True)
class ToggleHotkeyConfig:
    key: str = ""
    modifier: str = ""


@dataclass(frozen=True, slots=True)
class PasteConfig:
    clipboard_restore_delay: float = 0.5


@dataclass(frozen=True, slots=True)
class Config:
    audio: AudioConfig = field(default_factory=AudioConfig)
    whisper: WhisperConfig = field(default_factory=WhisperConfig)
    rewriter: RewriterConfig = field(default_factory=RewriterConfig)
    hotkey: HotkeyConfig = field(default_factory=HotkeyConfig)
    hotkey_toggle: ToggleHotkeyConfig = field(default_factory=ToggleHotkeyConfig)
    paste: PasteConfig = field(default_factory=PasteConfig)
    spoken_commands: dict[str, str] = field(default_factory=dict)


def load_config(path: Path | None = None) -> Config:
    """Load config from a TOML file, falling back to defaults for missing keys."""
    config_path = path or _DEFAULT_CONFIG_PATH
    if not config_path.exists():
        return Config()

    with open(config_path, "rb") as f:
        raw = tomllib.load(f)

    def _load(cls, section: str):
        valid = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in raw.get(section, {}).items() if k in valid})

    return Config(
        audio=_load(AudioConfig, "audio"),
        whisper=_load(WhisperConfig, "whisper"),
        rewriter=_load(RewriterConfig, "rewriter"),
        hotkey=_load(HotkeyConfig, "hotkey"),
        hotkey_toggle=_load(ToggleHotkeyConfig, "hotkey_toggle"),
        paste=_load(PasteConfig, "paste"),
        spoken_commands=raw.get("spoken_commands", {}),
    )

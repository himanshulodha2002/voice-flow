"""Configuration loader — reads config.toml and exposes typed values."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
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


@dataclass(frozen=True, slots=True)
class PasteConfig:
    clipboard_clear_delay: float = 2.0


@dataclass(frozen=True, slots=True)
class Config:
    audio: AudioConfig = field(default_factory=AudioConfig)
    whisper: WhisperConfig = field(default_factory=WhisperConfig)
    rewriter: RewriterConfig = field(default_factory=RewriterConfig)
    hotkey: HotkeyConfig = field(default_factory=HotkeyConfig)
    paste: PasteConfig = field(default_factory=PasteConfig)
    spoken_commands: dict[str, str] = field(default_factory=dict)


def load_config(path: Path | None = None) -> Config:
    """Load config from a TOML file, falling back to defaults for missing keys."""
    config_path = path or _DEFAULT_CONFIG_PATH
    if not config_path.exists():
        return Config()

    with open(config_path, "rb") as f:
        raw = tomllib.load(f)

    return Config(
        audio=AudioConfig(**{k: v for k, v in raw.get("audio", {}).items() if k in AudioConfig.__dataclass_fields__}),
        whisper=WhisperConfig(**{k: v for k, v in raw.get("whisper", {}).items() if k in WhisperConfig.__dataclass_fields__}),
        rewriter=RewriterConfig(**{k: v for k, v in raw.get("rewriter", {}).items() if k in RewriterConfig.__dataclass_fields__}),
        hotkey=HotkeyConfig(**{k: v for k, v in raw.get("hotkey", {}).items() if k in HotkeyConfig.__dataclass_fields__}),
        paste=PasteConfig(**{k: v for k, v in raw.get("paste", {}).items() if k in PasteConfig.__dataclass_fields__}),
        spoken_commands=raw.get("spoken_commands", {}),
    )

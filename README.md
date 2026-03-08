# VoiceFlow

Push-to-talk voice typing for macOS Apple Silicon. Hold a hotkey, speak, release — cleaned text is pasted wherever your cursor is. Everything runs 100% on-device.

**Pipeline:** hotkey → mic → Whisper (transcription) → Qwen LLM (cleanup) → paste

> **RAM:** ~700 MB while running (models resident in GPU memory via MLX).

## Requirements

- macOS, Apple Silicon (M1+)
- Python 3.13+
- [`uv`](https://github.com/astral-sh/uv): `curl -LsSf https://astral.sh/uv/install.sh | sh`

## Setup

```bash
./setup.sh
```

Installs dependencies and registers a LaunchAgent that auto-starts VoiceFlow on login.

Grant permissions when prompted: **Accessibility** and **Microphone** in System Settings → Privacy & Security.

## Run manually

```bash
uv run python -m voiceflow
```

First run downloads models (~1 GB) and caches them locally.

## Usage

| Action | Result |
|---|---|
| Hold **⌥⌘** (Option + Command) | Start recording |
| Release | Transcribe, clean, and paste |
| **Ctrl+C** | Quit |

You can also say punctuation aloud:

| Say | Inserts |
|---|---|
| "new paragraph" | blank line |
| "period" / "comma" / "question mark" | `. , ?` |

## Configuration

Edit [config.toml](config.toml) — no code changes needed.

| Section | What it controls |
|---|---|
| `[audio]` | recording limits, silence threshold |
| `[whisper]` | transcription model |
| `[rewriter]` | cleanup LLM, system prompt, max tokens |
| `[hotkey]` | trigger key |
| `[paste]` | clipboard clear delay |

## LaunchAgent

```bash
# Logs
tail -f ~/personal/voice-flow/voiceflow.log

# Stop
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.voiceflow.voicetype.plist

# Restart
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.voiceflow.voicetype.plist

# Uninstall
rm ~/Library/LaunchAgents/com.voiceflow.voicetype.plist
```

## Models

| Role | Model |
|---|---|
| Transcription | `mlx-community/whisper-small.en-mlx` |
| Cleanup | `mlx-community/Qwen3.5-0.8B-4bit` |

No internet required after the initial download.

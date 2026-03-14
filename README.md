# VoiceFlow

macOS menubar app for push-to-talk voice typing on Apple Silicon. Hold a hotkey, speak, release — cleaned text is pasted wherever your cursor is. Everything runs 100% on-device.

**Pipeline:** hotkey → mic → Whisper (transcription) → Qwen LLM (cleanup) → paste

> **RAM:** ~700 MB while models are loaded. Use **Unload Models** from the menubar to free GPU memory when not in use.

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

First run downloads models (~1 GB) and caches them locally. A **VF** icon appears in the menubar.

## Menubar

| Icon | State |
|---|---|
| **VF** | Idle — ready for dictation |
| **VF ●** | Recording |
| **VF ⟳** | Processing (transcribe + rewrite) |
| **VF ↓** | Loading models |
| **VF ○** | Models unloaded |

Menu items: **Load Models** / **Unload Models** / **Show Logs** / **Quit**

## Usage

| Action | Result |
|---|---|
| Hold **⌃⌘** (Control + Command) | Start recording |
| Release | Transcribe, clean, and paste |

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
| `[hotkey]` | push-to-talk trigger key |
| `[hotkey_toggle]` | toggle mode key (press once to start/stop) |
| `[paste]` | clipboard restore delay |

## Logs

Logs are written to `~/Library/Logs/VoiceFlow/voiceflow.log` (rotating, 2 MB max). Open via the menubar **Show Logs** item, or:

```bash
tail -f ~/Library/Logs/VoiceFlow/voiceflow.log
```

## LaunchAgent

```bash
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

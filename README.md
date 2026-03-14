# VoiceFlow

Push-to-talk voice typing for macOS Apple Silicon. Runs 100% on-device via MLX.

Hold **⌃⌘** → speak → release → text is pasted at your cursor.

## Setup

```bash
./setup.sh
```

Grant **Accessibility** and **Microphone** permissions when prompted.

Starts automatically on login via LaunchAgent. Restarts on crash.

## Run manually

```bash
uv run python -m voiceflow
```

First run downloads models (~1 GB).

## Menubar

**VF** = ready, **VF ●** = recording, **VF ⟳** = processing, **VF ↓** = loading, **VF ○** = unloaded

Menu: Load Models / Unload Models / Show Logs / Quit

## Config

Edit [`config.toml`](config.toml) — hotkey, models, audio settings, spoken commands.

## Logs

`~/Library/Logs/VoiceFlow/voiceflow.log`

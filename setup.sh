#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_NAME="com.voiceflow.voicetype"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"

echo "=== VoiceFlow Setup ==="

# ── Platform checks ──────────────────────────────────────────────────────────

if [[ "$(uname)" != "Darwin" ]]; then
    echo "Error: VoiceFlow requires macOS with Apple Silicon."
    exit 1
fi

if [[ "$(uname -m)" != "arm64" ]]; then
    echo "Error: VoiceFlow requires Apple Silicon (M-series chip)."
    exit 1
fi

if ! command -v uv &>/dev/null; then
    echo "Error: uv not found. Install it: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# ── Install dependencies via uv ─────────────────────────────────────────────

echo "Syncing project dependencies..."
cd "$PROJECT_DIR"
uv sync

echo "Dependencies installed."

# ── Install LaunchAgent for auto-start on login ─────────────────────────────

echo "Installing LaunchAgent for auto-start..."
mkdir -p "$HOME/Library/LaunchAgents"

cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_NAME}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${PROJECT_DIR}/.venv/bin/python</string>
        <string>-m</string>
        <string>voiceflow</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${PROJECT_DIR}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>StandardOutPath</key>
    <string>${PROJECT_DIR}/voiceflow.log</string>
    <key>StandardErrorPath</key>
    <string>${PROJECT_DIR}/voiceflow.log</string>
    <key>ProcessType</key>
    <string>Interactive</string>
</dict>
</plist>
PLIST

# Load the agent (unload first if already loaded)
launchctl bootout "gui/$(id -u)" "$PLIST_PATH" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"

echo "LaunchAgent installed. VoiceFlow will start on login."

# ── Done ─────────────────────────────────────────────────────────────────────

echo ""
echo "=== Setup complete ==="
echo ""
echo "Before first run, enable these macOS permissions:"
echo "  1. Accessibility: System Settings → Privacy & Security → Accessibility → toggle ON for your terminal"
echo "  2. Microphone:    System Settings → Privacy & Security → Microphone → toggle ON for your terminal"
echo ""
echo "Usage:"
echo "  Run now:    uv run python -m voiceflow"
echo "  View logs:  tail -f ${PROJECT_DIR}/voiceflow.log"
echo "  Stop:       launchctl bootout gui/\$(id -u) ${PLIST_PATH}"
echo "  Uninstall:  rm ${PLIST_PATH}"

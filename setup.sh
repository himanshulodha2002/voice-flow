#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_NAME="com.voiceflow.voicetype"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"
LOG_DIR="$HOME/Library/Logs/VoiceFlow"

if [[ "$EUID" -eq 0 ]]; then
    echo "Error: Do not run with sudo." && exit 1
fi
if [[ "$(uname)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
    echo "Error: Requires macOS Apple Silicon." && exit 1
fi
if ! command -v uv &>/dev/null; then
    echo "Error: uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh" && exit 1
fi

echo "Installing dependencies..."
cd "$PROJECT_DIR"
uv sync

echo "Installing LaunchAgent..."
mkdir -p "$HOME/Library/LaunchAgents" "$LOG_DIR"

NEW_PLIST=$(cat <<PLIST
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
    <key>ProcessType</key>
    <string>Interactive</string>
</dict>
</plist>
PLIST
)

EXISTING_PLIST=""
[[ -f "$PLIST_PATH" ]] && EXISTING_PLIST=$(cat "$PLIST_PATH")

SERVICE_LABEL="gui/$(id -u)/${PLIST_NAME}"

if [[ "$NEW_PLIST" != "$EXISTING_PLIST" ]]; then
    echo "$NEW_PLIST" > "$PLIST_PATH"
    chmod 644 "$PLIST_PATH"
    if ! launchctl kickstart -k "$SERVICE_LABEL" 2>/dev/null; then
        launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH" 2>/dev/null || true
    fi
else
    launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH" 2>&1 || true
fi

PYTHON_BIN="$(cd "$PROJECT_DIR" && .venv/bin/python -c 'import sys; print(sys.executable)' 2>/dev/null || echo "${PROJECT_DIR}/.venv/bin/python")"

echo ""
echo "Done. Grant these permissions in System Settings → Privacy & Security:"
echo "  Accessibility: add ${PYTHON_BIN}"
echo "  Microphone:    allow when prompted"
echo ""
echo "VoiceFlow will start on login. Logs: ~/Library/Logs/VoiceFlow/voiceflow.log"

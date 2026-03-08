#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_NAME="com.voiceflow.voicetype"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"

echo "=== VoiceFlow Setup ==="

# ── Guard: must not run as root ───────────────────────────────────────────────

if [[ "$EUID" -eq 0 ]]; then
    echo "Error: Do not run this script with sudo."
    echo "LaunchAgents are per-user and must be installed as yourself."
    exit 1
fi

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
        <string>-u</string>
        <string>-m</string>
        <string>voiceflow</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONUNBUFFERED</key>
        <string>1</string>
    </dict>
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
)

EXISTING_PLIST=""
[[ -f "$PLIST_PATH" ]] && EXISTING_PLIST=$(cat "$PLIST_PATH")

SERVICE_LABEL="gui/$(id -u)/${PLIST_NAME}"

# Write plist if changed
if [[ "$NEW_PLIST" != "$EXISTING_PLIST" ]]; then
    echo "$NEW_PLIST" > "$PLIST_PATH"
    chmod 644 "$PLIST_PATH"
    # Reload: kickstart if registered, else bootstrap
    if ! launchctl kickstart -k "$SERVICE_LABEL" 2>/dev/null; then
        launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH" 2>/dev/null || true
    fi
    echo "LaunchAgent updated."
else
    # Plist unchanged — ensure it's registered (bootstrap is a no-op if already loaded)
    bootstrap_out=$(launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH" 2>&1) && \
        echo "LaunchAgent registered." || {
        # Exit code 5 (EIO) = already loaded, which is fine
        if echo "$bootstrap_out" | /usr/bin/grep -qF "Bootstrap failed: 5"; then
            echo "LaunchAgent already running — no changes made."
        else
            echo "Warning: $bootstrap_out"
        fi
    }
fi

# ── Request microphone permission (only if not already granted) ───────────────

echo ""
MIC_STATUS=$(uv run python -c "
import sounddevice as sd, time
try:
    with sd.InputStream(samplerate=16000, channels=1, dtype='float32', blocksize=1024):
        time.sleep(0.3)
    print('granted')
except Exception:
    print('denied')
" 2>/dev/null)

if [[ "$MIC_STATUS" == "granted" ]]; then
    echo "Microphone permission: already granted."
else
    echo "Microphone permission not yet granted — macOS dialog may appear on first use."
    echo "  Grant access: System Settings → Privacy & Security → Microphone"
fi

# ── Done ─────────────────────────────────────────────────────────────────────

echo ""
PYTHON_BIN="$(cd "$PROJECT_DIR" && .venv/bin/python -c 'import sys; print(sys.executable)' 2>/dev/null || echo "${PROJECT_DIR}/.venv/bin/python")"

echo "=== Setup complete ==="
echo ""
echo "ACTION REQUIRED — Accessibility permission for hotkey support:"
echo "  1. Open: System Settings → Privacy & Security → Accessibility"
echo "  2. Click '+' and add this binary:"
echo "     ${PYTHON_BIN}"
echo "  (This is needed because VoiceFlow runs as a background agent, not from your terminal)"
echo ""
echo "Usage:"
echo "  Run now:    uv run python -m voiceflow"
echo "  View logs:  tail -f ${PROJECT_DIR}/voiceflow.log"
echo "  Stop:       launchctl bootout gui/\$(id -u) ${PLIST_PATH}"
echo "  Uninstall:  rm ${PLIST_PATH}"

#!/bin/bash
# =============================================================================
# setup_scheduler_mac.sh
# =============================================================================
# Sets up automatic daily MF NAV fetching on macOS using launchd.
# Runs every day at 9:30 PM IST (21:30) — after AMFI updates NAVs (~7 PM IST).
#
# Usage:
#   chmod +x setup_scheduler_mac.sh
#   ./setup_scheduler_mac.sh
#
# To stop the scheduler:
#   launchctl unload ~/Library/LaunchAgents/com.mfnav.updater.plist
#
# To check status:
#   launchctl list | grep mfnav
#
# To view logs:
#   cat /tmp/mfnav_updater.log
# =============================================================================

set -e

# ── Detect Python path ────────────────────────────────────────────────────────
PYTHON_PATH=$(which python3)
if [ -z "$PYTHON_PATH" ]; then
    echo "❌ python3 not found in PATH. Install Python 3 first."
    exit 1
fi
echo "✅ Python: $PYTHON_PATH"

# ── Get absolute script directory ─────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPDATER_SCRIPT="$SCRIPT_DIR/scripts/03_incremental_update.py"
LOG_FILE="/tmp/mfnav_updater.log"
PLIST_LABEL="com.mfnav.updater"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_LABEL}.plist"

echo "📁 Project dir : $SCRIPT_DIR"
echo "📜 Script      : $UPDATER_SCRIPT"
echo "📋 Plist       : $PLIST_PATH"

# ── Install Python deps ────────────────────────────────────────────────────────
echo ""
echo "📦 Installing Python dependencies..."
$PYTHON_PATH -m pip install --quiet --upgrade requests pandas tqdm

# ── Write launchd plist ────────────────────────────────────────────────────────
mkdir -p "$HOME/Library/LaunchAgents"

cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_LABEL}</string>

    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON_PATH}</string>
        <string>${UPDATER_SCRIPT}</string>
        <string>--notify</string>
    </array>

    <!-- Run every day at 21:30 (9:30 PM) local time -->
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>21</integer>
        <key>Minute</key>
        <integer>30</integer>
    </dict>

    <key>StandardOutPath</key>
    <string>${LOG_FILE}</string>
    <key>StandardErrorPath</key>
    <string>${LOG_FILE}</string>

    <!-- Run even if the scheduled time was missed (e.g. Mac was asleep) -->
    <key>RunAtLoad</key>
    <false/>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
EOF

# ── Load the plist ─────────────────────────────────────────────────────────────
# Unload first if already exists
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"

echo ""
echo "🎉 Scheduler installed and active!"
echo ""
echo "   Schedule    : Every day at 9:30 PM"
echo "   Log file    : $LOG_FILE"
echo "   Config      : $PLIST_PATH"
echo ""
echo "   Useful commands:"
echo "   ─────────────────────────────────────────────────────"
echo "   View logs   : tail -f $LOG_FILE"
echo "   Run now     : python3 $UPDATER_SCRIPT --notify"
echo "   Stop        : launchctl unload $PLIST_PATH"
echo "   Check status: launchctl list | grep mfnav"
echo "   ─────────────────────────────────────────────────────"

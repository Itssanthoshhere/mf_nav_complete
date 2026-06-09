#!/bin/bash
# =============================================================================
# setup_cron.sh  — Linux / Mac (cron alternative)
# =============================================================================
# Adds a cron job that runs the MF NAV updater every day at 9:30 PM.
#
# Usage:
#   chmod +x setup_cron.sh
#   ./setup_cron.sh
#
# To remove later:
#   crontab -e   →  delete the mfnav line
# =============================================================================

PYTHON_PATH=$(which python3)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPDATER="$SCRIPT_DIR/scripts/03_incremental_update.py"
LOG="/tmp/mfnav_cron.log"

CRON_LINE="30 21 * * * $PYTHON_PATH $UPDATER --notify >> $LOG 2>&1"

# Check if already exists
if crontab -l 2>/dev/null | grep -q "mfnav\|03_incremental_update"; then
    echo "⚠️  Cron job already exists. Edit with: crontab -e"
    crontab -l | grep "incremental_update"
    exit 0
fi

# Add to crontab
(crontab -l 2>/dev/null; echo "# MF NAV daily updater — runs at 9:30 PM"; echo "$CRON_LINE") | crontab -

echo "✅ Cron job added:"
echo "   $CRON_LINE"
echo ""
echo "   View logs : tail -f $LOG"
echo "   Edit/remove: crontab -e"
echo "   List all  : crontab -l"

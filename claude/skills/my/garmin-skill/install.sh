#!/usr/bin/env bash
# Garmin Skill Installation Script
#
# Sets up virtual environment, installs dependencies, initializes database,
# tests authentication, and provides cron setup instructions.

set -e

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_DIR="$HOME/.garmin-skill"
VENV_DIR="$SKILL_DIR/.venv"

echo "=== Garmin Skill Installation ==="
echo ""

# 1. Check Python
echo "Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not found."
    echo "Install Python 3.10+ and try again."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Found Python $PYTHON_VERSION"

# 2. Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
echo "Virtual environment created at $VENV_DIR"

# 3. Install dependencies
echo ""
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r "$SKILL_DIR/scripts/requirements.txt"
echo "Dependencies installed"

# 4. Create data directory
echo ""
echo "Creating data directory..."
mkdir -p "$DATA_DIR"
echo "Data directory: $DATA_DIR"

# 5. Initialize database
echo ""
echo "Initializing database..."
python3 -c "
import sys
sys.path.insert(0, '$SKILL_DIR/scripts')
from db import init_db
from pathlib import Path
init_db(Path('$DATA_DIR/garmin.db'))
print('Database initialized at $DATA_DIR/garmin.db')
"

# 6. Test Garmin authentication
echo ""
echo "=== Garmin Authentication ==="
echo ""
echo "Testing Garmin Connect authentication..."
echo "The library will try:"
echo "  1. Existing tokens in ~/.garminconnect/"
echo "  2. GARMIN_USERNAME/GARMIN_PASSWORD environment variables"
echo ""

AUTH_OK=0
python3 -c "
from garminconnect import Garmin
try:
    g = Garmin()
    g.login()
    print('Authentication successful! (using saved tokens)')
    exit(0)
except Exception:
    pass

import os
u = os.environ.get('GARMIN_USERNAME')
p = os.environ.get('GARMIN_PASSWORD')
if u and p:
    try:
        g = Garmin(u, p)
        g.login()
        print('Authentication successful! (using env vars)')
        exit(0)
    except Exception as e:
        print(f'Authentication failed: {e}')
        exit(1)
else:
    print('No credentials found.')
    print('')
    print('Set environment variables:')
    print('  export GARMIN_USERNAME=\"your@email.com\"')
    print('  export GARMIN_PASSWORD=\"your_password\"')
    print('')
    print('Then re-run this script.')
    exit(1)
" && AUTH_OK=1

if [ "$AUTH_OK" -eq 0 ]; then
    echo ""
    echo "Skipping initial sync due to authentication issue."
    echo "Fix credentials and run: python $SKILL_DIR/scripts/garmin_sync.py --backfill 30"
else
    # 7. Run initial sync
    echo ""
    echo "=== Initial Sync ==="
    echo "Running initial sync (backfilling 7 days)..."
    echo "This may take a moment..."
    echo ""
    python3 "$SKILL_DIR/scripts/garmin_sync.py" --backfill 7
fi

# 8. Cron setup instructions
echo ""
echo "=== Cron Setup (Optional) ==="
echo ""
echo "To sync automatically every morning at 6 AM, add this to your crontab:"
echo ""
echo "  crontab -e"
echo ""
echo "Add this line:"
echo ""
echo "  0 6 * * * cd $SKILL_DIR && $VENV_DIR/bin/python scripts/garmin_sync.py >> $DATA_DIR/sync.log 2>&1"
echo ""

# 9. Register with Claude Code
echo "=== Claude Code Registration ==="
PLUGINS_DIR="$HOME/.claude/plugins"
if [ -d "$PLUGINS_DIR" ]; then
    ln -sf "$SKILL_DIR" "$PLUGINS_DIR/garmin-skill" 2>/dev/null || true
    echo "Skill linked at $PLUGINS_DIR/garmin-skill"
else
    echo "Note: ~/.claude/plugins/ not found."
    echo "If using Claude Code, manually create a symlink:"
    echo "  mkdir -p $PLUGINS_DIR"
    echo "  ln -s $SKILL_DIR $PLUGINS_DIR/garmin-skill"
fi

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Test the skill:"
echo "  cd $SKILL_DIR"
echo "  source .venv/bin/activate"
echo "  python scripts/garmin_query.py summary"
echo "  python scripts/garmin_query.py --help"
echo ""

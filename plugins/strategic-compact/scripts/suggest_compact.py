#!/usr/bin/env python3
"""
PreToolUse hook: suggest /compact at strategic intervals.

Counts tool calls per session. At COMPACT_THRESHOLD (default 50),
suggests compaction. Repeats every COMPACT_INTERVAL (default 25) calls after.
"""

import os
import sys
import tempfile
from pathlib import Path

THRESHOLD = int(os.environ.get("COMPACT_THRESHOLD", "50"))
INTERVAL = int(os.environ.get("COMPACT_INTERVAL", "25"))

# Session-specific counter file
session_id = os.environ.get("CLAUDE_SESSION_ID", str(os.getppid()))
counter_file = Path(tempfile.gettempdir()) / f"claude-tool-count-{session_id}"


def main():
    # Read current count
    count = 0
    try:
        count = int(counter_file.read_text().strip())
    except (FileNotFoundError, ValueError):
        pass

    count += 1
    counter_file.write_text(str(count))

    # Check if we should suggest compaction
    if count == THRESHOLD:
        print(
            f"[StrategicCompact] {count} tool calls reached "
            f"— consider /compact if transitioning between phases"
        )
    elif count > THRESHOLD and (count - THRESHOLD) % INTERVAL == 0:
        print(
            f"[StrategicCompact] {count} tool calls "
            f"— good checkpoint for /compact if context is stale"
        )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # Never block the session
    sys.exit(0)

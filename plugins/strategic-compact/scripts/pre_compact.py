#!/usr/bin/env python3
"""
PreCompact hook: log compaction events.

Appends a timestamped entry to .claude/compact-log.jsonl whenever
context compaction is triggered.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG_FILE = Path(".claude") / "compact-log.jsonl"


def main():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": "compaction",
        "session_id": os.environ.get("CLAUDE_SESSION_ID", "unknown"),
    }

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # Never block compaction
    sys.exit(0)

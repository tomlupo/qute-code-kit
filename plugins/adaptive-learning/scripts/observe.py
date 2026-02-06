#!/usr/bin/env python3
"""
PostToolUse hook: capture tool events to observations JSONL.

Reads tool data from stdin, appends a compact record to
~/.claude/adaptive-learning/observations.jsonl.
Silent on stdout — never blocks the session.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Resolve relative to this script so plugin root is found correctly
sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import get_config, get_storage_dir, truncate_str, rotate_if_needed


def main():
    raw = sys.stdin.read().strip()
    if not raw:
        return

    try:
        hook_input = json.loads(raw)
    except json.JSONDecodeError:
        return

    tool_name = hook_input.get("tool_name", "unknown")

    cfg = get_config()
    exclude = cfg.get("exclude_tools", [])
    if tool_name in exclude:
        return

    storage = get_storage_dir()
    obs_file = storage / "observations.jsonl"

    max_chars = cfg.get("max_io_chars", 5000)
    tool_input = hook_input.get("tool_input", {})
    tool_output = hook_input.get("tool_output", "")

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": "tool_complete",
        "tool": tool_name,
        "session": os.environ.get("CLAUDE_SESSION_ID", "unknown"),
        "project": Path.cwd().name,
        "input": truncate_str(json.dumps(tool_input) if isinstance(tool_input, dict) else str(tool_input), max_chars),
        "output": truncate_str(str(tool_output), max_chars),
    }

    with open(obs_file, "a") as f:
        f.write(json.dumps(entry) + "\n")

    rotate_if_needed(
        obs_file,
        max_mb=cfg.get("max_observation_size_mb", 10),
        archive_count=cfg.get("archive_count", 3),
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # Never block the session
    sys.exit(0)

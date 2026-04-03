#!/usr/bin/env python3
"""
PostToolUse hook (filtered to Skill|Agent): log skill and agent invocations.

Reads tool input from stdin (JSON) and appends a JSONL entry to
.claude/skill-use-log.jsonl.

Entry shape:
  Skill → {"timestamp", "type": "skill", "skill", "args", "session_id", "project"}
  Agent → {"timestamp", "type": "agent", "subagent_type", "description", "session_id", "project"}
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG_FILE = Path(".claude") / "skill-use-log.jsonl"


def build_entry(hook_input: dict) -> dict | None:
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    base = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": os.environ.get("CLAUDE_SESSION_ID", "unknown"),
        "project": Path.cwd().name,
    }

    if tool_name == "Skill":
        return {
            **base,
            "type": "skill",
            "skill": tool_input.get("skill", "unknown"),
            "args": tool_input.get("args", ""),
        }

    if tool_name == "Agent":
        return {
            **base,
            "type": "agent",
            "subagent_type": tool_input.get("subagent_type", "general-purpose"),
            "description": tool_input.get("description", ""),
        }

    return None


def main():
    raw = sys.stdin.read().strip()
    if not raw:
        return

    try:
        hook_input = json.loads(raw)
    except json.JSONDecodeError:
        return

    entry = build_entry(hook_input)
    if entry is None:
        return

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # Never block the session
    sys.exit(0)

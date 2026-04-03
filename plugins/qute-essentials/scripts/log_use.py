#!/usr/bin/env python3
"""
Hook logger: captures Skill, Agent tool calls (PostToolUse) and native subagent
invocations (SubagentStart). Appends JSONL entries to .claude/skill-use-log.jsonl.

Entry shapes:
  Skill        → {"timestamp", "type": "skill", "skill", "args", "session_id", "project"}
  Agent tool   → {"timestamp", "type": "agent", "subagent_type", "description", "session_id", "project"}
  SubagentStart→ {"timestamp", "type": "subagent", "agent_id", "agent_type", "session_id", "project"}
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG_FILE = Path(".claude") / "skill-use-log.jsonl"


def build_entry(hook_input: dict) -> dict | None:
    base = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": os.environ.get("CLAUDE_SESSION_ID", "unknown"),
        "project": Path.cwd().name,
    }

    # PostToolUse: Skill or Agent tool calls
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

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

    # SubagentStart: native .claude/agents/ invocations
    if "agent_id" in hook_input:
        return {
            **base,
            "type": "subagent",
            "agent_id": hook_input.get("agent_id", ""),
            "agent_type": hook_input.get("agent_type", ""),
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

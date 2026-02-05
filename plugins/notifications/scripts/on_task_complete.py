#!/usr/bin/env python3
"""
PostToolUse hook for task completion notifications.

This script is called after Bash tool usage to detect long-running
commands and send notifications when they complete.
"""

import json
import os
import sys
import time
from pathlib import Path

# Add parent to path for notify module
sys.path.insert(0, str(Path(__file__).parent))

from notify import get_config, notify_task_complete


def parse_hook_input() -> dict:
    """Parse hook input from stdin."""
    try:
        input_data = sys.stdin.read()
        if input_data:
            return json.loads(input_data)
    except json.JSONDecodeError:
        pass
    return {}


def should_notify(command: str, config: dict) -> bool:
    """Check if this command should trigger notifications."""
    filters = config.get("filters", {})
    monitored_commands = filters.get("commands", [])

    if not monitored_commands:
        return True

    # Check if command starts with any monitored command
    for cmd in monitored_commands:
        if command.strip().startswith(cmd):
            return True

    return False


def main():
    """Main hook handler."""
    hook_data = parse_hook_input()

    # Extract tool use information
    tool_name = hook_data.get("tool_name", "")
    tool_input = hook_data.get("tool_input", {})
    tool_output = hook_data.get("tool_output", {})

    # Only process Bash tool
    if tool_name != "Bash":
        return

    command = tool_input.get("command", "")
    if not command:
        return

    config = get_config()

    # Check if this command should trigger notifications
    if not should_notify(command, config):
        return

    # Determine success/failure
    # This is a simplified check - actual implementation might need more logic
    output = tool_output.get("output", "")
    exit_code = tool_output.get("exit_code", 0)
    success = exit_code == 0

    # Get duration if available (from tool metadata)
    duration = tool_output.get("duration_ms", 0) / 1000.0

    # Check minimum duration filter
    min_duration = config.get("filters", {}).get("min_duration_seconds", 30)
    if duration < min_duration:
        return

    # Send notification
    notify_task_complete(command, duration, success)


if __name__ == "__main__":
    main()

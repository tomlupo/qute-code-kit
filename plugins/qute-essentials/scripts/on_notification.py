#!/usr/bin/env python3
"""
Notification hook - fires when Claude sends a message and is waiting for user input.
Sends a push notification so the user doesn't have to stare at the terminal.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from notify import send_notification


def parse_hook_input() -> dict:
    """Parse hook input from stdin."""
    try:
        input_data = sys.stdin.read()
        if input_data:
            return json.loads(input_data)
    except json.JSONDecodeError:
        pass
    return {}


def main():
    hook_data = parse_hook_input()
    message = hook_data.get("message", "Claude needs your attention")

    # Truncate long messages for the notification
    if len(message) > 200:
        message = message[:197] + "..."

    hostname = platform.node().split(".")[0]
    send_notification(
        message,
        title=f"Claude Code [{hostname}]",
        priority="default",
        tags=["robot", "speech_balloon"],
    )


if __name__ == "__main__":
    main()

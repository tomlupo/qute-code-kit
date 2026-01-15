#!/usr/bin/env python3
"""
Enforce deterministic council script execution.

This PreToolUse hook blocks Bash commands that look like SDK improvisation,
ensuring Claude uses the pre-built council scripts instead of writing custom code.
"""
import json
import re
import sys
from pathlib import Path

# Marker file to indicate council command is active
COUNCIL_MARKER = Path("/tmp/.council_active")

def main():
    # Read tool input from stdin
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)  # Can't parse, allow

    command = data.get("tool_input", {}).get("command", "")

    # Always allow council scripts (python or uv run python)
    COUNCIL_SCRIPTS = [
        r"(uv\s+run\s+)?python3?\s+.*council_(ask|debate|decide|brainstorm)\.py",
        r"(uv\s+run\s+)?python3?\s+.*scripts/council_(ask|debate|decide|brainstorm)\.py",
    ]

    if any(re.search(p, command) for p in COUNCIL_SCRIPTS):
        sys.exit(0)  # Allow council scripts

    # Block SDK improvisation patterns (inline Python with imports)
    BLOCKED_PATTERNS = [
        r'(uv\s+run\s+)?python3?\s+-c\s+',  # Any inline python -c (including uv run)
        r'cat\s*<<.*\|\s*.*python',          # Heredoc piped to python
        r"<<\s*['\"]?EOF",                   # Heredoc syntax
        r'\|\s*python3?',                    # Pipe to python
        r'python3?\s*<',                     # Redirect to python
    ]

    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE | re.DOTALL):
            response = {
                "decision": "block",
                "reason": (
                    "BLOCKED: Do not write inline Python code. "
                    "Use the council script: python council_<command>.py \"<topic>\" "
                    "The script handles CLI-first + API fallback automatically."
                )
            }
            print(json.dumps(response))
            sys.exit(2)

    # Allow other commands (ls, grep, etc.)
    sys.exit(0)

if __name__ == "__main__":
    main()

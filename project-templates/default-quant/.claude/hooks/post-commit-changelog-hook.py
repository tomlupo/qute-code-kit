#!/usr/bin/env python3
"""
PostToolUse hook that reminds Claude to update CHANGELOG.md
after commits on the main branch.
"""

import json
import subprocess
import sys


def get_current_branch():
    """Get the current git branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except:
        return None


def main():
    # Read hook input from stdin
    try:
        hook_input = json.load(sys.stdin)
    except:
        sys.exit(0)  # No input, skip

    # Get the command that was executed
    command = hook_input.get("tool_input", {}).get("command", "")

    # Check if this was a git commit
    if not command.startswith("git commit"):
        sys.exit(0)

    # Check if we're on main branch
    branch = get_current_branch()
    if branch != "main":
        sys.exit(0)

    # Output reminder for Claude
    reminder = """
CHANGELOG REMINDER: You just committed to the main branch.

Please offer to update CHANGELOG.md with user-facing changes:
- New features
- Bug fixes
- Breaking changes

Skip internal changes (refactors, dev tooling, docs).

Format: `## [Date] - Brief description`
"""
    print(reminder)
    sys.exit(0)


if __name__ == "__main__":
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    main()

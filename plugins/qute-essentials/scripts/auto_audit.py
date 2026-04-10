"""PostToolUse hook: run /audit after commands that mutate Python dependencies.

Triggers on `uv add`, `uv remove`, `uv sync`, `uv lock`, and `pip install`.
Runs audit.py and pipes a short summary back to Claude via stderr (or
directly prints vulnerability details if any are found). Non-blocking:
always exits 0 so it doesn't interfere with the main command.

Toggle via config/guards.json {"audit": {"enabled": true/false}}.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GUARDS_CONFIG = Path(__file__).parent.parent / "config" / "guards.json"
AUDIT_SCRIPT = Path(__file__).parent / "audit.py"

# Commands that change the resolved dependency set
TRIGGER = re.compile(
    r"\b(?:uv\s+(?:add|remove|sync|lock)|pip\s+install|pip\s+uninstall)\b"
)


def is_enabled() -> bool:
    if os.environ.get("CLAUDE_SKIP_GUARDS") == "1":
        return False
    if os.environ.get("CLAUDE_GUARD_AUDIT") == "0":
        return False
    try:
        with open(GUARDS_CONFIG) as f:
            config = json.load(f)
        return config.get("audit", {}).get("enabled", True)
    except (FileNotFoundError, json.JSONDecodeError):
        return True


def main() -> int:
    if not is_enabled():
        return 0

    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    if payload.get("tool_name") != "Bash":
        return 0

    cmd = (payload.get("tool_input") or {}).get("command", "")
    if not cmd or not TRIGGER.search(cmd):
        return 0

    # Only run if we're inside a Python project
    cwd = Path.cwd()
    if not (cwd / "pyproject.toml").exists():
        return 0

    print("audit: running dependency vulnerability scan...", file=sys.stderr)
    try:
        result = subprocess.run(
            [sys.executable, str(AUDIT_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=180,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        print(f"audit: skipped ({exc})", file=sys.stderr)
        return 0

    # Exit 0: clean, 1: vulns found, 2: error
    if result.returncode == 0:
        # Print the short "scanned N packages, no vulnerabilities" line only
        tail = result.stdout.strip().splitlines()[-2:]
        for line in tail:
            print(line, file=sys.stderr)
        return 0

    # Vulnerabilities or error: forward full output so Claude surfaces it
    if result.stdout:
        print(result.stdout, file=sys.stderr)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    # Still exit 0 — auto-audit is informational, not blocking
    return 0


if __name__ == "__main__":
    sys.exit(main())

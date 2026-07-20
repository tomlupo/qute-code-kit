"""PostToolUse hook: run /audit after commands that mutate Python dependencies.

Triggers on `uv add`, `uv remove`, `uv sync`, `uv lock`, and `pip install`.
Runs audit.py and pipes a short summary back to Claude via stderr (or
directly prints vulnerability details if any are found). Non-blocking:
always exits 0 so it doesn't interfere with the main command.

Toggle with `/guard <name> on/off` (persists to ~/.claude/qute-guards.json).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AUDIT_SCRIPT = Path(__file__).parent / "audit.py"

# Commands that change the resolved dependency set
TRIGGER = re.compile(
    r"\b(?:uv\s+(?:add|remove|sync|lock)|pip\s+install|pip\s+uninstall)\b"
)


sys.path.insert(0, str(Path(__file__).resolve().parent))
from guard_config import guard_enabled  # noqa: E402


def is_enabled() -> bool:
    """Whether the dependency-audit guard is enabled (local guard: fails open)."""
    return guard_enabled("audit")


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

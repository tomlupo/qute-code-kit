#!/usr/bin/env python3
"""
PostToolUse hook (filtered to Edit, Write): auto-format Python files with ruff.

Runs ruff format and ruff check --fix after Python file edits. Silently skips
if ruff is not available or file is not Python.
"""

import json
import subprocess
import sys
from pathlib import Path


def find_ruff():
    """Find ruff executable. Try direct, then uvx (standalone), then uv run (project)."""
    for cmd in [["ruff"], ["uvx", "ruff"], ["uv", "run", "ruff"]]:
        try:
            result = subprocess.run(
                cmd + ["--version"], capture_output=True, timeout=10
            )
            if result.returncode == 0:
                return cmd
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


def main():
    raw = sys.stdin.read().strip()
    if not raw:
        return

    try:
        hook_input = json.loads(raw)
    except json.JSONDecodeError:
        return

    file_path = hook_input.get("tool_input", {}).get("file_path", "")
    if not file_path or not file_path.endswith(".py"):
        return

    if not Path(file_path).exists():
        return

    ruff_cmd = find_ruff()
    if not ruff_cmd:
        return

    # Format
    subprocess.run(
        ruff_cmd + ["format", "--quiet", file_path],
        capture_output=True, timeout=10,
    )

    # Auto-fix safe lint issues
    subprocess.run(
        ruff_cmd + ["check", "--fix", "--quiet", file_path],
        capture_output=True, timeout=10,
    )

    print(f"[RuffFormatter] Formatted {Path(file_path).name}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # Never block the session
    sys.exit(0)

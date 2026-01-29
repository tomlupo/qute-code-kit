#!/usr/bin/env python3
"""Load TASKS.md and active session context on startup."""
import os
import sys
import json
from pathlib import Path

# Fix Windows encoding issues
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))

    output = []

    # Read TASKS.md Now section
    tasks_file = project_dir / "TASKS.md"
    if tasks_file.exists():
        content = tasks_file.read_text(encoding="utf-8")
        # Extract Now section
        lines = content.split("\n")
        in_now = False
        now_section = []
        for line in lines:
            if line.startswith("## Now"):
                in_now = True
                now_section.append(line)
            elif line.startswith("## ") and in_now:
                break
            elif in_now:
                now_section.append(line)
        if now_section:
            output.append("## Current Tasks (from TASKS.md)")
            output.extend(now_section[1:])  # Skip header

    # Check for active session
    active_file = project_dir / ".claude/sessions/.active-sessions"
    if active_file.exists():
        try:
            data = json.loads(active_file.read_text(encoding="utf-8"))
            if data.get("sessions"):
                output.append("\n## Active Sessions")
                for s in data["sessions"]:
                    output.append(f"- {s}")
        except Exception:
            pass

    if output:
        print("\n".join(output))


if __name__ == "__main__":
    main()

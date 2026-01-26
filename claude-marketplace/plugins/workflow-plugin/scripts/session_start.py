#!/usr/bin/env python3
"""Load ledger, handoffs, and active session context on startup."""
import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

# Fix Windows encoding issues
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


def get_latest_handoff(handoffs_dir: Path, max_age_hours: int = 24) -> str | None:
    """Get the most recent handoff if within max_age_hours."""
    if not handoffs_dir.exists():
        return None

    handoff_files = sorted(handoffs_dir.glob("*.md"), reverse=True)
    if not handoff_files:
        return None

    latest = handoff_files[0]
    # Check age based on filename (YYYY-MM-DD-HHMM.md)
    try:
        name = latest.stem  # e.g., "2025-12-29-1530"
        handoff_time = datetime.strptime(name, "%Y-%m-%d-%H%M")
        if datetime.now() - handoff_time < timedelta(hours=max_age_hours):
            return latest.read_text(encoding="utf-8")
    except (ValueError, Exception):
        pass

    return None


def main():
    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
    output = []

    # 1. Check for recent handoff (priority)
    handoffs_dir = project_dir / ".claude" / "handoffs"
    handoff = get_latest_handoff(handoffs_dir)
    if handoff:
        output.append("## Resuming from Handoff")
        output.append(handoff)
        output.append("")

    # 2. Read ledger.md (replaces context.md)
    ledger_file = project_dir / ".claude" / "memory" / "ledger.md"
    if ledger_file.exists():
        try:
            content = ledger_file.read_text(encoding="utf-8")
            output.append("## Session Ledger")
            output.append(content)
        except Exception:
            pass
    else:
        # Fallback to old context.md
        context_file = project_dir / ".claude" / "memory" / "context.md"
        if context_file.exists():
            try:
                content = context_file.read_text(encoding="utf-8")
                output.append("## Context (from .claude/memory/context.md)")
                output.append(content)
            except Exception:
                pass

    # 3. Read TASKS.md Now section
    tasks_file = project_dir / "TASKS.md"
    if tasks_file.exists():
        content = tasks_file.read_text(encoding="utf-8")
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
            output.append("\n## Current Tasks")
            output.extend(now_section[1:])

    # 4. Check for active sessions
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
        print("\n---")
        print("INSTRUCTION: On first message, summarize current focus and propose 2-3 actions.")


if __name__ == "__main__":
    main()

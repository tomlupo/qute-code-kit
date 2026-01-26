#!/usr/bin/env python3
"""UserPromptSubmit hook - injects session context on every message to survive compaction."""
import json
import os
from pathlib import Path


def main():
    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
    sessions_dir = project_dir / ".claude" / "sessions"
    active_file = sessions_dir / ".active-sessions"

    if not active_file.exists():
        return

    try:
        data = json.loads(active_file.read_text(encoding="utf-8"))
        sessions = data.get("sessions", [])
    except Exception:
        return

    if not sessions:
        return

    session_name = sessions[0]

    # Find session file and extract task
    session_files = list(sessions_dir.glob(f"*-{session_name}.md"))
    task = "No task linked"

    if session_files:
        try:
            content = session_files[0].read_text(encoding="utf-8", errors="ignore")
            for line in content.split("\n"):
                if line.startswith("**Task:**") or line.startswith("Task:"):
                    task = line.replace("**Task:**", "").replace("Task:", "").strip()
                    break
        except Exception:
            pass

    # Compact session info for injection
    session_info = {"name": session_name, "task": task}

    # Also extract current goal from ledger if available
    ledger_file = project_dir / ".claude" / "memory" / "ledger.md"
    if ledger_file.exists():
        try:
            content = ledger_file.read_text(encoding="utf-8")
            for line in content.split("\n"):
                if line.startswith("## Current Goal"):
                    # Get next non-empty line
                    idx = content.split("\n").index(line)
                    for next_line in content.split("\n")[idx + 1 :]:
                        if next_line.strip() and not next_line.startswith("#"):
                            session_info["goal"] = next_line.strip()
                            break
                    break
        except Exception:
            pass

    # Output reminder
    print(f"[Session: {session_info}] Task: {task}")


if __name__ == "__main__":
    main()

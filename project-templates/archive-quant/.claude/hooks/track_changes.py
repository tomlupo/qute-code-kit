#!/usr/bin/env python3
"""Track file changes during session and auto-log to active session file."""
import os
import sys
import json
from datetime import datetime
from pathlib import Path


def get_project_dir() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))


def log_to_changes_file(project_dir: Path, action: str, file_path: str):
    """Log change to changes.log file."""
    log_file = project_dir / ".claude/hooks/changes.log"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} | {action} | {file_path}\n")


def append_to_session(project_dir: Path, action: str, file_path: str):
    """Auto-append file change to active session file."""
    active_file = project_dir / ".claude" / "sessions" / ".active-sessions"

    if not active_file.exists():
        return

    try:
        data = json.loads(active_file.read_text(encoding="utf-8"))
        sessions = data.get("sessions", [])

        if not sessions:
            return

        # Find session file for first active session
        session_name = sessions[0]
        session_files = list((project_dir / ".claude" / "sessions").glob(f"*-{session_name}.md"))

        if session_files:
            # Make path relative for cleaner output
            try:
                rel_path = Path(file_path).relative_to(project_dir)
            except ValueError:
                rel_path = file_path

            with open(session_files[0], "a", encoding="utf-8") as f:
                f.write(f"\n- {action}: `{rel_path}`")
    except Exception:
        pass


def main():
    # Read input from stdin
    try:
        input_data = json.load(sys.stdin)
    except Exception:
        return

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Only track Write and Edit
    if tool_name not in ("Write", "Edit"):
        return

    file_path = tool_input.get("file_path", "unknown")
    action = "created" if tool_name == "Write" else "modified"

    project_dir = get_project_dir()

    # Log to changes.log
    log_to_changes_file(project_dir, action, file_path)

    # Auto-append to active session file
    append_to_session(project_dir, action, file_path)


if __name__ == "__main__":
    main()

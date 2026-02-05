#!/usr/bin/env python3
"""
Stop hook: save session state to ~/.claude/sessions/.

Reads session context from stdin (JSON), writes a structured markdown
file capturing completed items, in-progress work, and notes.
"""

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

SESSIONS_DIR = Path.home() / ".claude" / "sessions"


def short_id(session_id):
    """Derive a short 6-char ID from session ID or fallback."""
    return hashlib.sha256(session_id.encode()).hexdigest()[:6]


def extract_session_data(hook_input):
    """Extract useful fields from the Stop hook input."""
    # The Stop hook receives the conversation transcript summary
    # We extract what we can and write a template for the rest
    transcript = hook_input.get("transcript_summary", "")
    session_id = os.environ.get("CLAUDE_SESSION_ID", "")
    project = Path.cwd().name

    return {
        "transcript": transcript,
        "session_id": session_id,
        "project": project,
    }


def build_session_markdown(data):
    """Build the structured markdown session file."""
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M UTC")
    project = data.get("project", "unknown")
    transcript = data.get("transcript", "")

    lines = [
        f"# Session: {project}",
        f"**Date:** {date_str}",
        f"**Time:** {time_str}",
        f"**Project:** {project}",
        "",
        "### Completed",
        "- [ ] (fill in completed tasks)",
        "",
        "### In Progress",
        "- [ ] (fill in current tasks)",
        "",
        "### Notes for Next Session",
        "- (add notes here)",
        "",
        "### Context to Load",
        "- (list key files to load next session)",
        "",
    ]

    if transcript:
        lines.extend([
            "### Session Summary",
            transcript,
            "",
        ])

    return "\n".join(lines)


def main():
    # Read hook input from stdin
    raw = sys.stdin.read().strip()

    hook_input = {}
    if raw:
        try:
            hook_input = json.loads(raw)
        except json.JSONDecodeError:
            pass

    data = extract_session_data(hook_input)

    # Create sessions directory
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    # Generate filename
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    sid = data.get("session_id") or str(os.getpid())
    tag = short_id(sid)
    filename = f"{date_str}-{tag}-session.tmp"
    filepath = SESSIONS_DIR / filename

    # Write session file
    content = build_session_markdown(data)
    filepath.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # Never block the session
    sys.exit(0)

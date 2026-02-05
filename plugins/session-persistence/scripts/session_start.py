#!/usr/bin/env python3
"""
SessionStart hook: report recent sessions with unfinished work.

Scans ~/.claude/sessions/ for .tmp files from the last 7 days,
parses each for title, date, in-progress items, and notes.
Outputs a brief summary if sessions are found, stays silent otherwise.
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

SESSIONS_DIR = Path.home() / ".claude" / "sessions"
MAX_AGE_DAYS = 7
MAX_DISPLAY = 3


def parse_session(path):
    """Extract metadata from a session .tmp file."""
    title = None
    date = None
    in_progress = 0
    notes = []

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    in_notes_section = False
    in_progress_section = False

    for line in text.splitlines():
        stripped = line.strip()

        # Title from first H1
        if stripped.startswith("# Session:") and title is None:
            title = stripped[len("# Session:"):].strip()

        # Date from **Date:** field
        if stripped.startswith("**Date:**"):
            date = stripped[len("**Date:**"):].strip()

        # Track which section we're in
        if stripped.startswith("### In Progress"):
            in_progress_section = True
            in_notes_section = False
            continue
        elif stripped.startswith("### Notes"):
            in_notes_section = True
            in_progress_section = False
            continue
        elif stripped.startswith("### "):
            in_progress_section = False
            in_notes_section = False
            continue

        # Count in-progress items
        if in_progress_section and stripped.startswith("- [ ]"):
            in_progress += 1

        # Collect notes (first 2 lines)
        if in_notes_section and stripped.startswith("- ") and len(notes) < 2:
            notes.append(stripped[2:])

    if not title and not date:
        return None

    return {
        "path": path,
        "title": title or path.stem,
        "date": date or "unknown",
        "in_progress": in_progress,
        "notes": notes,
        "mtime": path.stat().st_mtime,
    }


def main():
    if not SESSIONS_DIR.exists():
        return

    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    cutoff_ts = cutoff.timestamp()

    sessions = []
    for f in SESSIONS_DIR.glob("*.tmp"):
        try:
            if f.stat().st_mtime < cutoff_ts:
                continue
        except OSError:
            continue

        info = parse_session(f)
        if info:
            sessions.append(info)

    if not sessions:
        return

    # Sort by modification time, most recent first
    sessions.sort(key=lambda s: s["mtime"], reverse=True)

    # Build summary
    total = len(sessions)
    shown = sessions[:MAX_DISPLAY]

    parts = [f"[SessionPersistence] Found {total} recent session(s):"]
    for s in shown:
        line = f"  - {s['title']} ({s['date']}"
        if s["in_progress"] > 0:
            line += f", {s['in_progress']} item(s) in progress"
        line += ")"
        if s["notes"]:
            line += f" — {s['notes'][0]}"
        parts.append(line)

    if total > MAX_DISPLAY:
        parts.append(f"  ... and {total - MAX_DISPLAY} more (use /session-persistence:list to see all)")

    parts.append("")
    parts.append("Use /session-persistence:load to resume a previous session.")

    print("\n".join(parts))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # Never block the session
    sys.exit(0)

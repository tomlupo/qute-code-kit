#!/usr/bin/env python3
"""
PostToolUse hook (filtered to Edit, Write): track code vs doc file edits.

Maintains per-session state of modified code and doc files. When code files
accumulate without corresponding doc edits, prints a reminder.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

THRESHOLD = int(os.environ.get("DOC_ENFORCER_THRESHOLD", "3"))

CODE_EXTENSIONS = {".py", ".sh", ".go", ".js", ".ts", ".jsx", ".tsx", ".rs", ".java", ".c", ".cpp", ".h"}
DOC_EXTENSIONS = {".md", ".rst", ".txt"}

session_id = os.environ.get("CLAUDE_SESSION_ID", str(os.getppid()))
state_file = Path(tempfile.gettempdir()) / f"doc-enforcer-{session_id}.json"


def load_state():
    try:
        return json.loads(state_file.read_text())
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        return {"code_files": [], "doc_files": [], "last_reminded_at": 0}


def save_state(state):
    state_file.write_text(json.dumps(state))


def is_doc_file(path):
    p = Path(path)
    if p.suffix in DOC_EXTENSIONS:
        return True
    # Anything under a docs/ directory counts as documentation
    parts = p.parts
    return "docs" in parts or "doc" in parts


def is_code_file(path):
    return Path(path).suffix in CODE_EXTENSIONS


def main():
    raw = sys.stdin.read().strip()
    if not raw:
        return

    try:
        hook_input = json.loads(raw)
    except json.JSONDecodeError:
        return

    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    if not file_path:
        return

    state = load_state()

    if is_doc_file(file_path):
        if file_path not in state["doc_files"]:
            state["doc_files"].append(file_path)
        # Reset reminder counter when a doc file is edited
        state["last_reminded_at"] = len(state["code_files"])
        save_state(state)
        return

    if is_code_file(file_path):
        if file_path not in state["code_files"]:
            state["code_files"].append(file_path)
        save_state(state)

        code_count = len(state["code_files"])
        since_last = code_count - state["last_reminded_at"]

        if since_last >= THRESHOLD:
            doc_count = len(state["doc_files"])
            print(
                f"[DocEnforcer] {code_count} code file(s) modified, "
                f"{doc_count} doc file(s) touched "
                f"— check if docs/ or README need updating"
            )
            state["last_reminded_at"] = code_count
            save_state(state)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # Never block the session
    sys.exit(0)

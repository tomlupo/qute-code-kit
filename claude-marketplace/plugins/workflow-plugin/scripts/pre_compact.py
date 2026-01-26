#!/usr/bin/env python3
"""
PreCompact hook - Auto-generate handoff before context clears.

This is the key innovation from Continuous-Claude: instead of allowing
context to degrade through compaction (summaries of summaries), we
generate a structured handoff and block manual compaction.

The handoff captures:
- Current goal
- Active files with descriptions
- Recent uncommitted changes
- Recent decisions
- Next steps

On session resume, session_start.py loads the latest handoff automatically.
"""
import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path

# Fix Windows encoding issues
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

MAX_HANDOFFS = 5  # Keep only this many most recent handoffs


def get_project_dir() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))


def get_uncommitted_changes(project_dir: Path) -> list[str]:
    """Get list of uncommitted file changes."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            changes = []
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    status = line[:2].strip()
                    filepath = line[3:].strip()
                    if status == "M":
                        changes.append(f"- Modified: `{filepath}`")
                    elif status == "A":
                        changes.append(f"- Added: `{filepath}`")
                    elif status == "D":
                        changes.append(f"- Deleted: `{filepath}`")
                    elif status == "??":
                        changes.append(f"- Untracked: `{filepath}`")
            return changes
    except Exception:
        pass
    return []


def get_recent_changes(project_dir: Path) -> list[str]:
    """Get recent changes from changes.log."""
    log_file = project_dir / ".claude" / "hooks" / "changes.log"
    if not log_file.exists():
        return []

    try:
        lines = log_file.read_text(encoding="utf-8").strip().split("\n")
        # Get last 10 changes
        return [f"- {line}" for line in lines[-10:] if line.strip()]
    except Exception:
        return []


def extract_from_ledger(project_dir: Path) -> dict:
    """Extract current goal, active files, decisions from ledger."""
    ledger_file = project_dir / ".claude" / "memory" / "ledger.md"
    result = {"goal": "", "active_files": [], "decisions": [], "constraints": []}

    if not ledger_file.exists():
        # Try old context.md
        context_file = project_dir / ".claude" / "memory" / "context.md"
        if context_file.exists():
            try:
                content = context_file.read_text(encoding="utf-8")
                # Extract key decisions
                in_decisions = False
                for line in content.split("\n"):
                    if "Key Decisions" in line or "## Decisions" in line:
                        in_decisions = True
                    elif line.startswith("##") and in_decisions:
                        break
                    elif in_decisions and line.strip().startswith("-"):
                        result["decisions"].append(line.strip())
            except Exception:
                pass
        return result

    try:
        content = ledger_file.read_text(encoding="utf-8")
        lines = content.split("\n")
        current_section = None

        for i, line in enumerate(lines):
            if line.startswith("## Current Goal"):
                current_section = "goal"
            elif line.startswith("## Active Files"):
                current_section = "files"
            elif line.startswith("## Recent Decisions"):
                current_section = "decisions"
            elif line.startswith("## Constraints"):
                current_section = "constraints"
            elif line.startswith("##"):
                current_section = None
            elif current_section and line.strip():
                if current_section == "goal" and not line.startswith("["):
                    result["goal"] = line.strip()
                    current_section = None
                elif current_section == "files" and line.strip().startswith("-"):
                    result["active_files"].append(line.strip())
                elif current_section == "decisions" and line.strip().startswith("-"):
                    result["decisions"].append(line.strip())
                elif current_section == "constraints" and line.strip().startswith("-"):
                    result["constraints"].append(line.strip())
    except Exception:
        pass

    return result


def get_active_session(project_dir: Path) -> str | None:
    """Get active session name."""
    active_file = project_dir / ".claude" / "sessions" / ".active-sessions"
    if not active_file.exists():
        return None

    try:
        data = json.loads(active_file.read_text(encoding="utf-8"))
        sessions = data.get("sessions", [])
        return sessions[0] if sessions else None
    except Exception:
        return None


def cleanup_old_handoffs(handoffs_dir: Path):
    """Keep only MAX_HANDOFFS most recent handoffs."""
    if not handoffs_dir.exists():
        return

    handoff_files = sorted(handoffs_dir.glob("*.md"), reverse=True)
    for old_file in handoff_files[MAX_HANDOFFS:]:
        try:
            old_file.unlink()
        except Exception:
            pass


def generate_handoff(project_dir: Path) -> str:
    """Generate handoff document content."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    ledger = extract_from_ledger(project_dir)
    uncommitted = get_uncommitted_changes(project_dir)
    recent = get_recent_changes(project_dir)
    session = get_active_session(project_dir)

    lines = [
        f"# Handoff: {timestamp}",
        "",
    ]

    if session:
        lines.extend([f"**Session:** {session}", ""])

    lines.extend(["## Current Goal"])
    if ledger["goal"]:
        lines.append(ledger["goal"])
    else:
        lines.append("[No goal set in ledger]")
    lines.append("")

    if ledger["active_files"]:
        lines.extend(["## Active Files"])
        lines.extend(ledger["active_files"])
        lines.append("")

    if uncommitted:
        lines.extend(["## Uncommitted Changes"])
        lines.extend(uncommitted)
        lines.append("")

    if recent:
        lines.extend(["## Recent Session Changes"])
        lines.extend(recent[-5:])  # Last 5 only
        lines.append("")

    if ledger["decisions"]:
        lines.extend(["## Recent Decisions"])
        lines.extend(ledger["decisions"][:5])  # Top 5 only
        lines.append("")

    lines.extend(
        [
            "## Next Steps",
            "1. [ ] [Continue from above context]",
            "2. [ ] [Review uncommitted changes]",
            "",
            "---",
            "*Auto-generated handoff. Use `/workflow:session` to resume.*",
        ]
    )

    return "\n".join(lines)


def main():
    project_dir = get_project_dir()
    handoffs_dir = project_dir / ".claude" / "handoffs"
    handoffs_dir.mkdir(parents=True, exist_ok=True)

    # Generate handoff
    handoff_content = generate_handoff(project_dir)

    # Save handoff
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    handoff_file = handoffs_dir / f"{timestamp}.md"
    handoff_file.write_text(handoff_content, encoding="utf-8")

    # Cleanup old handoffs
    cleanup_old_handoffs(handoffs_dir)

    # Block compaction and notify
    print(f"Handoff created: {handoff_file.relative_to(project_dir)}")
    print("")
    print("Context preserved. To continue with fresh context:")
    print("1. Use /clear (not /compact)")
    print("2. Handoff will auto-load on restart")
    print("")
    print("--- Handoff Preview ---")
    print(handoff_content[:500] + "..." if len(handoff_content) > 500 else handoff_content)

    # Return blocking response to prevent compaction
    # Note: The actual blocking depends on Claude Code's hook behavior
    # This output signals the user to use /clear instead
    sys.exit(0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
PreToolUse hook: block destructive commands before execution.

Catches git destruction, filesystem destruction, database drops,
and custom project-specific protections. Context-aware to avoid
false positives (won't block grep/echo containing patterns).

Toggle on/off via config/guards.json {"destructive": {"enabled": true/false}}.
"""

import json
import os
import re
import sys
from pathlib import Path

GUARDS_CONFIG = Path(__file__).parent.parent / "config" / "guards.json"


def is_enabled() -> bool:
    if os.environ.get("CLAUDE_SKIP_GUARDS") == "1":
        return False
    if os.environ.get("CLAUDE_GUARD_DESTRUCTIVE") == "0":
        return False
    try:
        with open(GUARDS_CONFIG) as f:
            config = json.load(f)
        return config.get("destructive", {}).get("enabled", True)
    except (FileNotFoundError, json.JSONDecodeError):
        return True


# ─── Pattern definitions ──────────────────────────────────────
# Each pattern: (compiled regex, description, severity)
# Severity: "block" = hard deny, "warn" = deny with explanation

GIT_PATTERNS = [
    (
        re.compile(r"\bgit\s+reset\s+--hard\b"),
        "git reset --hard destroys uncommitted changes",
        "block",
    ),
    (
        re.compile(r"\bgit\s+clean\s+-[a-zA-Z]*f"),
        "git clean -f permanently deletes untracked files",
        "block",
    ),
    (
        re.compile(r"\bgit\s+push\s+[^|]*--force\b"),
        "git push --force overwrites remote history",
        "block",
    ),
    (
        re.compile(r"\bgit\s+push\s+-f\b"),
        "git push -f overwrites remote history",
        "block",
    ),
    (
        re.compile(r"\bgit\s+stash\s+(clear|drop)\b"),
        "git stash clear/drop permanently deletes stashed work",
        "block",
    ),
    (
        re.compile(r"\bgit\s+checkout\s+--\s+\."),
        "git checkout -- . discards all working changes",
        "block",
    ),
    (
        re.compile(r"\bgit\s+restore\s+(?!--staged)[^|]*\.\s*$"),
        "git restore . discards all working changes",
        "block",
    ),
    (
        re.compile(r"\bgit\s+branch\s+-D\b"),
        "git branch -D force-deletes branch without merge check",
        "warn",
    ),
    (
        re.compile(r"\bgit\s+rebase\s+.*--force\b"),
        "forced rebase rewrites history",
        "block",
    ),
]

FILESYSTEM_PATTERNS = [
    # Unix
    (
        re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+/(?!tmp|var/tmp)"),
        "rm -rf on non-tmp root path",
        "block",
    ),
    (
        re.compile(r"\brm\s+-[a-zA-Z]*f[a-zA-Z]*r[a-zA-Z]*\s+/(?!tmp|var/tmp)"),
        "rm -fr on non-tmp root path",
        "block",
    ),
    (
        re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+~/"),
        "rm -rf in home directory",
        "block",
    ),
    (
        re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+\.\s*$"),
        "rm -rf . deletes current directory",
        "block",
    ),
    (
        re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+\.\./"),
        "rm -rf with parent traversal",
        "block",
    ),
    (
        re.compile(r"\bfind\s+.*-delete\b"),
        "find -delete permanently removes matched files",
        "warn",
    ),
    (
        re.compile(r"\bfind\s+.*-exec\s+rm\b"),
        "find -exec rm removes matched files",
        "warn",
    ),
    (re.compile(r"\b>\s*/etc/"), "overwriting system config file", "block"),
    (re.compile(r"\bmkfs\b"), "mkfs formats a filesystem", "block"),
    (re.compile(r"\bdd\s+.*of=/dev/"), "dd writing to device", "block"),
    # Windows
    (
        re.compile(r"\brmdir\s+/s", re.I),
        "rmdir /s recursively deletes directory",
        "block",
    ),
    (re.compile(r"\bdel\s+/s", re.I), "del /s recursively deletes files", "block"),
    (re.compile(r"\brd\s+/s", re.I), "rd /s recursively deletes directory", "block"),
    (
        re.compile(r"\bRemove-Item\s+.*-Recurse", re.I),
        "Remove-Item -Recurse deletes directory tree",
        "block",
    ),
    (
        re.compile(r"\bRemove-Item\s+.*-Force", re.I),
        "Remove-Item -Force bypasses safety checks",
        "warn",
    ),
    (re.compile(r"\bformat\s+[A-Z]:", re.I), "format drive command", "block"),
]

DATABASE_PATTERNS = [
    (
        re.compile(r"\bDROP\s+(DATABASE|TABLE|SCHEMA)\b", re.I),
        "DROP destroys database objects",
        "block",
    ),
    (
        re.compile(r"\bTRUNCATE\s+TABLE\b", re.I),
        "TRUNCATE deletes all rows without logging",
        "block",
    ),
    (
        re.compile(r"\bDELETE\s+FROM\s+\w+\s*;", re.I),
        "DELETE without WHERE clause deletes all rows",
        "warn",
    ),
    (re.compile(r"\bdropdb\b"), "dropdb removes entire database", "block"),
    (re.compile(r"\bdropuser\b"), "dropuser removes database user", "block"),
]

DOCKER_PATTERNS = [
    (
        re.compile(r"\bdocker\s+system\s+prune\s+-a"),
        "docker system prune -a removes all unused data",
        "block",
    ),
    (
        re.compile(r"\bdocker\s+volume\s+prune\b"),
        "docker volume prune deletes all unused volumes",
        "warn",
    ),
    (
        re.compile(r"\bdocker\s+rm\s+-f\s+\$\(docker\s+ps"),
        "mass-removing running containers",
        "block",
    ),
]

SYSTEM_PATTERNS = [
    # Unix
    (re.compile(r"\bsudo\s+rm\s+-rf\b"), "sudo rm -rf as root", "block"),
    (
        re.compile(r"\bchmod\s+-R\s+777\b"),
        "chmod -R 777 makes everything world-writable",
        "block",
    ),
    (re.compile(r"\bchown\s+-R\s+.*\s+/\s*$"), "chown -R on root filesystem", "block"),
    (re.compile(r"\bkillall\b"), "killall terminates all matching processes", "warn"),
    (
        re.compile(r"\bpkill\s+-9\s+-u\b"),
        "pkill -9 -u kills all user processes",
        "block",
    ),
    # Windows
    (
        re.compile(r"\btaskkill\s+/f\s+/im\s+\*", re.I),
        "taskkill mass-killing all processes",
        "block",
    ),
    (
        re.compile(r"\bStop-Process\s+.*-Force", re.I),
        "Stop-Process -Force kills processes",
        "warn",
    ),
    (
        re.compile(r"\bnet\s+stop\b", re.I),
        "net stop disables a Windows service",
        "warn",
    ),
    (
        re.compile(r"\bsc\s+delete\b", re.I),
        "sc delete removes a Windows service",
        "block",
    ),
    (
        re.compile(r"\breg\s+delete\s+.*\\\\.*\s+/f", re.I),
        "reg delete /f force-deletes registry keys",
        "block",
    ),
]

# ─── Custom protections for this VPS ──────────────────────────

CUSTOM_PATTERNS = [
    # Trading crons are live (07:00 quantlab = real Binance trades)
    (
        re.compile(r"\bcrontab\s+-r\b"),
        "crontab -r removes ALL cron jobs including live trading",
        "block",
    ),
    (
        re.compile(r"\bcrontab\s+/dev/null\b"),
        "crontab /dev/null wipes all cron jobs",
        "block",
    ),
    # Obsidian vaults
    (
        re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f?[a-zA-Z]*\s+/srv/obsidian\b"),
        "removing Obsidian vault data",
        "block",
    ),
    # Syncthing config
    (
        re.compile(r"\brm\s+.*\.stfolder\b"),
        "removing Syncthing folder marker breaks sync",
        "block",
    ),
    # Production quantlab
    (
        re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f?[a-zA-Z]*\s+.*/prod/quantlab\b"),
        "removing production trading code",
        "block",
    ),
]

ALL_PATTERNS = (
    GIT_PATTERNS
    + FILESYSTEM_PATTERNS
    + DATABASE_PATTERNS
    + DOCKER_PATTERNS
    + SYSTEM_PATTERNS
    + CUSTOM_PATTERNS
)


# ─── Context detection (avoid false positives) ────────────────


def is_safe_context(command: str) -> bool:
    """Commands that mention destructive patterns but aren't destructive."""
    stripped = command.strip()

    # grep/rg searching for patterns
    if re.match(r"^(grep|rg|ag|ack)\s+", stripped):
        return True

    # echo/printf just printing text
    if re.match(r"^(echo|printf)\s+", stripped):
        return True

    # Comments
    if stripped.startswith("#"):
        return True

    # Variable assignment (not execution)
    if re.match(r"^[A-Z_]+=", stripped):
        return True

    # man/help pages
    if re.match(r"^(man|help|\w+\s+--help)\b", stripped):
        return True

    # Dry run flags
    if re.search(r"--dry-run|--dryrun|-n\b|--check\b|--whatif\b", stripped):
        return True

    return False


# ─── Main hook ────────────────────────────────────────────────


def main():
    if not is_enabled():
        print("{}")
        return

    try:
        input_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        print("{}")
        return

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Only screen Bash commands
    if tool_name != "Bash":
        print("{}")
        return

    command = tool_input.get("command", "")
    if not command:
        print("{}")
        return

    # Skip safe contexts
    if is_safe_context(command):
        print("{}")
        return

    # Check all patterns
    for pattern, description, severity in ALL_PATTERNS:
        if pattern.search(command):
            reason = f"🛑 BLOCKED: {description}\nCommand: {command[:200]}"

            # Log the block
            log_dir = Path.home() / ".claude" / "permission-audit"
            log_dir.mkdir(parents=True, exist_ok=True)
            import time

            entry = {
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "type": "destructive_guard",
                "severity": severity,
                "description": description,
                "command": command[:500],
            }
            with open(log_dir / "destructive-blocks.jsonl", "a") as f:
                f.write(json.dumps(entry) + "\n")

            # Send ntfy alert for blocks
            if severity == "block":
                try:
                    from urllib.request import Request, urlopen

                    ntfy_req = Request(
                        "https://ntfy.sh/core-tom-claude",
                        data=f"🛑 Destructive command blocked\n{description}\n{command[:100]}".encode(),
                        headers={
                            "Title": "Destructive Command Blocked",
                            "Priority": "high",
                            "Tags": "octagonal_sign,warning",
                        },
                        method="POST",
                    )
                    urlopen(ntfy_req, timeout=3)
                except Exception:
                    pass

            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "PreToolUse",
                            "permissionDecision": "deny",
                            "permissionDecisionReason": reason,
                        }
                    }
                )
            )
            return

    # No match — allow
    print("{}")


if __name__ == "__main__":
    main()

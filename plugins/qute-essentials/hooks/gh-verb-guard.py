#!/usr/bin/env python3
"""
PreToolUse(Bash) hook: steer raw `gh issue create` / `gh label create` back to
the sanctioned verbs (obsidian-vaults#177).

Repo issue operations should flow through the `task` verb (pulse.sh) and board
operations through `gh-track`. Raw `gh issue create` / `gh label create` bypass
two things #177 relies on: the TYPE+STRUCTURE label taxonomy applied by the
`task` verb, and the `[agent:<name>]` comment-prefix enforcement.

This is a WARN, not a deny: these verbs legitimately shell out to `gh` under the
hood, so blocking would break the sanctioned path. When the command is itself
issued by pulse.sh / gh-track, the guard SUPPRESSES entirely (allows silently).

Toggleable via the shared guard framework as guard name "gh-verbs" (see
config/guards.json). It is a LOCAL deterministic guard: it fails OPEN — any
error or missing config allows the command.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from guard_config import guard_enabled  # noqa: E402

GUARD_NAME = "gh-verbs"

# Commands that ARE the sanctioned path — if the raw gh call is issued by one of
# these, it's legitimate; suppress the guard entirely.
_SANCTIONED = ("pulse.sh", "gh-track", "bin-extras/gh-track")


def _emit_allow() -> None:
    print("{}")


def _emit_deny(reason: str) -> None:
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


def _emit_warn(msg: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": msg,
                }
            }
        )
    )


# Match `gh issue create` / `gh label create` only when `gh` STARTS a command —
# at string start or after a shell separator (; & | newline ( ), optionally with
# an env-var prefix like FOO=bar) — so an incidental mention inside a quoted
# string or another argument does NOT trip it.
_CMD_START = r"(?:^|[\n;&|(])\s*(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)*"
_ISSUE_CREATE_RE = re.compile(_CMD_START + r"gh\s+issue\s+create\b")
_LABEL_CREATE_RE = re.compile(_CMD_START + r"gh\s+label\s+create\b")

_WARN_MSG = (
    "⚠️ gh-verbs guard (#177): prefer the sanctioned verbs over raw gh. "
    "Repo issue operations go through the `task` verb (pulse.sh) — which applies the "
    "TYPE+STRUCTURE label taxonomy and the [agent:<name>] comment prefix — and board "
    "operations go through `gh-track`. Raw `gh issue create` / `gh label create` bypass "
    "that label taxonomy and the [agent:] prefix enforcement. Use `/task` for issues and "
    "`gh-track` for board fields; only fall back to raw gh if neither can express what you need."
)


def main() -> None:
    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        _emit_allow()
        return

    if data.get("tool_name") != "Bash":
        _emit_allow()
        return

    # LOCAL deterministic guard -> fail OPEN. Only act when explicitly enabled.
    # guard_config derives its env override from the guard name upper-cased
    # ("GH-VERBS", with a hyphen); also honour the underscore spelling
    # CLAUDE_GUARD_GH_VERBS so the env toggle is usable from a shell.
    if os.environ.get("CLAUDE_GUARD_GH_VERBS") == "0":
        _emit_allow()
        return
    try:
        if not guard_enabled(GUARD_NAME):
            _emit_allow()
            return
    except Exception:
        _emit_allow()
        return

    command = data.get("tool_input", {}).get("command", "") or ""

    # Suppress when the sanctioned verbs are the ones issuing gh.
    if any(tok in command for tok in _SANCTIONED):
        _emit_allow()
        return

    if _ISSUE_CREATE_RE.search(command) or _LABEL_CREATE_RE.search(command):
        _emit_warn(_WARN_MSG)
        return

    _emit_allow()


if __name__ == "__main__":
    main()

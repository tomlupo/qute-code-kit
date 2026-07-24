#!/usr/bin/env python3
"""PreToolUse hook: stamp an identity tag on every automated write to a shared record.

Per ADR-0006 §6/§7 the provenance rule is ONE resolution, followed by every lane:

    QUTE_AGENT_NAME set  ->  [agent: $QUTE_AGENT_NAME]
    otherwise            ->  [session: <name-or-cwd-basename>]

This hook closes the one lane server-side stamping can't reach: **direct MCP
writes** to Linear (`save_issue`/`save_comment`/`save_document`/`save_status_update`,
under either linear MCP server-name variant) and local `gh pr (review|comment|create)`
Bash commands.

Behavior — **idempotent auto-inject, never a hard block**:

- If a valid leading `[agent: …]` / `[session: …]` tag is already present on the
  write's body, this NO-OPS.
- Otherwise it prepends the resolved tag. The primary mechanism is an in-place
  edit of the tool input (`hookSpecificOutput.updatedInput`). Because not every
  harness applies `updatedInput`, the injecting path ALSO emits a non-blocking
  `systemMessage` reminder (ADR-0006 §7 fail-safe: "fall back to
  allow-with-a-reminder message, do NOT hard-block writes").
- Fail-safe: on unresolved identity we inject `[session: <cwd-basename>]` rather
  than block. Malformed input, an un-mutatable Bash body, etc. all degrade to a
  reminder — the write is NEVER denied.

Toggle with `/guard provenance on|off` (persists to ~/.claude/qute-guards.json).
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


def is_enabled() -> bool:
    """Whether the provenance guard is enabled (local guard: fails open)."""
    return guard_enabled("provenance")


# A valid leading identity tag: [agent: NAME] or [session: NAME] at the very
# start of the body (optionally after leading whitespace).
LEADING_TAG_RE = re.compile(r"^\s*\[(?:agent|session):\s*[^\]]+\]")

# Linear MCP write verbs we stamp. Matched against the *suffix* of the tool
# name so both server-name variants (mcp__linear__… and the UUID variant) hit.
MCP_WRITE_SUFFIXES = (
    "save_issue",
    "save_comment",
    "save_document",
    "save_status_update",
)

# Ordered candidate body fields for the MCP write verbs. save_comment /
# save_status_update carry `body`; save_issue carries `description`;
# save_document carries `content`. We only mutate a field that is already
# present in the tool input (authoring that text) — never fabricate one.
MCP_BODY_FIELDS = ("body", "description", "content")

# gh commands that write to a shared record (a PR).
GH_WRITE_RE = re.compile(r"\bgh\s+pr\s+(?:review|comment|create)\b")

# A quoted --body / -b value we can inject into (best-effort for Bash).
GH_BODY_RE = re.compile(r"(--body|-b)(\s+|=)([\"'])(.*?)(\3)", re.DOTALL)


def resolve_tag(payload: dict) -> str:
    """Resolve the identity tag per ADR-0006 §6's one rule (fail-safe to session)."""
    agent = (os.environ.get("QUTE_AGENT_NAME") or "").strip()
    if agent:
        return f"[agent: {agent}]"
    # Session lane: prefer an explicit session name, else a dispatcher-supplied
    # one, else the cwd basename. This order MUST match qute-platform's
    # agent-kit/bin/_identity.sh so the two implementations of ADR-0006 §6's one
    # rule agree by construction (the whole point of pinning the rule once).
    name = (
        os.environ.get("QUTE_SESSION_NAME")
        or os.environ.get("DISPATCHER_SESSION_NAME")
        or ""
    ).strip()
    if not name:
        cwd = payload.get("cwd") or os.getcwd()
        name = Path(cwd).name or "session"
    return f"[session: {name}]"


def has_leading_tag(text: str) -> bool:
    return bool(LEADING_TAG_RE.match(text or ""))


def emit_noop() -> None:
    print("{}")


def emit_update(updated_input: dict, message: str) -> None:
    """Emit an input mutation plus a non-blocking reminder. Never denies."""
    print(
        json.dumps(
            {
                "systemMessage": message,
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "updatedInput": updated_input,
                },
            }
        )
    )


def emit_reminder(message: str) -> None:
    """Allow-with-a-reminder: surface a nudge, mutate nothing, block nothing."""
    print(json.dumps({"systemMessage": message}))


def handle_mcp(payload: dict, tool_input: dict, tag: str) -> None:
    for field in MCP_BODY_FIELDS:
        if field in tool_input:
            current = tool_input.get(field) or ""
            if has_leading_tag(current):
                emit_noop()
                return
            updated = dict(tool_input)
            updated[field] = f"{tag}\n{current}" if current else tag
            emit_update(
                updated,
                f"provenance: tagged this write with {tag}. "
                f"If it did not apply, prepend {tag!r} to the `{field}` field.",
            )
            return
    # No authorable body field present (e.g. a status-only issue update) — nudge
    # only; we never fabricate a field, and we never block.
    emit_reminder(
        f"provenance: this write has no body field to auto-tag — "
        f"start the record body with {tag} if it authors shared content."
    )


def handle_bash(tool_input: dict, tag: str) -> None:
    command = tool_input.get("command") or ""
    if not GH_WRITE_RE.search(command):
        emit_noop()
        return

    m = GH_BODY_RE.search(command)
    if m:
        body = m.group(4)
        if has_leading_tag(body):
            emit_noop()
            return
        new_body = f"{tag}\\n{body}" if body else tag
        new_command = (
            command[: m.start()]
            + f"{m.group(1)}{m.group(2)}{m.group(3)}{new_body}{m.group(5)}"
            + command[m.end() :]
        )
        updated = dict(tool_input)
        updated["command"] = new_command
        emit_update(
            updated,
            f"provenance: prefixed the PR body with {tag}. "
            f"If it did not apply, ensure the --body starts with {tag}.",
        )
        return

    # --body-file / --fill / heredoc / -F: can't safely rewrite the body — nudge.
    emit_reminder(
        f"provenance: could not auto-tag this `gh pr` write — "
        f"ensure the PR body starts with {tag} (author != reviewer marker)."
    )


def main() -> int:
    if not is_enabled():
        emit_noop()
        return 0

    try:
        payload = json.load(sys.stdin)
    except Exception:
        emit_noop()  # never block on malformed input
        return 0

    tool_name = payload.get("tool_name", "") or ""
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        emit_noop()
        return 0

    tag = resolve_tag(payload)

    if tool_name == "Bash":
        handle_bash(tool_input, tag)
    elif tool_name.startswith("mcp__") and any(
        tool_name.endswith(sfx) for sfx in MCP_WRITE_SUFFIXES
    ):
        handle_mcp(payload, tool_input, tag)
    else:
        emit_noop()
    return 0


if __name__ == "__main__":
    sys.exit(main())

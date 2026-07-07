#!/usr/bin/env python3
"""
PreToolUse(Bash) hook: enforce the qute-coder → qute-reviewer PR flow.

OPT-IN, DEFAULT OFF. Inert unless the current repo sets
``"quteEnforcePrReview": true`` in .claude/settings.json (see pr_flow_config.py).
A repo that merely has qute-essentials installed but has NOT opted in gets
exactly the prior behaviour — no block, no warning, no failure.

When a repo HAS opted in, it:
  1. blocks ``gh pr create`` → tells the user to use /qute-coder (so the PR is
     authored by qute-coder[bot] and review independence holds by construction);
  2. blocks ``gh pr merge`` unless a native review object authored by
     qute-review[bot] already exists on the target PR.

Fail-open on ambiguity: if enforcement is on but the PR/repo can't be resolved
for a merge, it WARNS (additionalContext) rather than blocking, so it never
wedges a legitimate merge on a detection failure. It only DENIES a merge when it
positively fetched the reviews and found none by qute-review[bot].
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from pr_flow_config import enforcement_enabled  # noqa: E402

REVIEW_BOT = "qute-review[bot]"


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


# Match `gh pr <sub>` only when `gh` STARTS a command — at string start or after a
# shell separator (; & | newline ( ), optionally with an env-var prefix like FOO=bar) —
# so an incidental mention inside a quoted string or another argument
# (e.g. `printf %s gh pr create`, `git commit -m "gh pr create"`) does NOT trip it.
_CMD_START = r"(?:^|[\n;&|(])\s*(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s+)*"
_CREATE_RE = re.compile(_CMD_START + r"gh\s+pr\s+create\b")
_MERGE_RE = re.compile(_CMD_START + r"gh\s+pr\s+merge\b")


def _run(args: list[str], cwd: str | None) -> tuple[int, str]:
    try:
        p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=8)
        return p.returncode, (p.stdout or "").strip()
    except Exception:
        return 1, ""


def _resolve_pr(command: str, cwd: str | None) -> tuple[str | None, str | None]:
    """Return (repo 'owner/name', pr_number) for a `gh pr merge` command, best-effort."""
    # explicit --repo
    repo = None
    m = re.search(r"--repo(?:=|\s+)(\S+)", command)
    if m:
        repo = m.group(1)
    # explicit PR number or URL as a positional arg
    pr = None
    m = re.search(r"github\.com/[^/]+/[^/]+/pull/(\d+)", command)
    if m:
        pr = m.group(1)
    else:
        # a bare number token after `merge`
        m = re.search(r"\bgh\s+pr\s+merge\s+(?:--\S+\s+)*?(\d+)\b", command)
        if m:
            pr = m.group(1)
    if repo and pr:
        return repo, pr
    # fall back to the current branch's PR via gh
    rc, out = _run(
        [
            "gh",
            "pr",
            "view",
            "--json",
            "number,headRepositoryOwner,headRepository,baseRepository",
        ],
        cwd,
    )
    if rc == 0 and out:
        try:
            d = json.loads(out)
            pr = pr or (str(d["number"]) if d.get("number") else None)
        except (ValueError, KeyError):
            pass
    if repo is None:
        rc, out = _run(
            ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
            cwd,
        )
        if rc == 0 and out:
            repo = out
    return repo, pr


def _has_bot_review(repo: str, pr: str, cwd: str | None) -> bool | None:
    """True/False if we could fetch reviews; None if the fetch failed (ambiguous)."""
    rc, out = _run(
        [
            "gh",
            "api",
            f"repos/{repo}/pulls/{pr}/reviews",
            "--paginate",
            "--jq",
            f'[.[] | select(.user.login=="{REVIEW_BOT}")] | length',
        ],
        cwd,
    )
    if rc != 0 or not out:
        return None
    try:
        return int(out.strip().splitlines()[-1]) > 0
    except (ValueError, IndexError):
        return None


def main() -> None:
    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        _emit_allow()
        return

    if data.get("tool_name") != "Bash":
        _emit_allow()
        return

    command = data.get("tool_input", {}).get("command", "") or ""
    cwd = data.get("cwd")

    # DEFAULT OFF — inert unless this repo opted in.
    if not enforcement_enabled(cwd):
        _emit_allow()
        return

    if _CREATE_RE.search(command):
        _emit_deny(
            "🛑 PR-flow enforcement (this repo opted in via quteEnforcePrReview): "
            "`gh pr create` is blocked. Use `/qute-coder` instead so the PR is authored by "
            "qute-coder[bot] — that makes the independent-reviewer gate pass by construction "
            "(author != reviewer). Same args as `gh pr create`."
        )
        return

    if _MERGE_RE.search(command):
        repo, pr = _resolve_pr(command, cwd)
        if not repo or not pr:
            _emit_warn(
                "⚠️ PR-flow enforcement is ON for this repo but the PR could not be resolved for "
                "this `gh pr merge`. Allowing the merge, but confirm a qute-review[bot] review "
                "exists first (run /qute-reviewer)."
            )
            return
        has = _has_bot_review(repo, pr, cwd)
        if has is None:
            _emit_warn(
                f"⚠️ PR-flow enforcement is ON but could not fetch reviews for {repo}#{pr}. "
                "Allowing the merge — verify a qute-review[bot] verdict exists (run /qute-reviewer)."
            )
            return
        if not has:
            _emit_deny(
                f"🛑 PR-flow enforcement: merging {repo}#{pr} is blocked — no independent "
                f"review by {REVIEW_BOT} exists yet. Run `/qute-reviewer {repo} {pr}` to post the "
                "independent verdict (satisfies the review-gate), then merge."
            )
            return
        _emit_allow()
        return

    _emit_allow()


if __name__ == "__main__":
    main()

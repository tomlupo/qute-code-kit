"""Tests for gh-verb-guard.py — steer raw gh issue/label create to the verbs (#177).

Verifies:
- WARN (additionalContext, not deny) on `gh issue create` and `gh label create`;
- SUPPRESS (allow) when the sanctioned verbs (pulse.sh / gh-track) issue gh;
- allow unrelated commands and incidental quoted mentions;
- respects the guard disable via CLAUDE_GUARD_GH_VERBS=0.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "hooks" / "gh-verb-guard.py"


def _run(command: str, env: dict | None = None) -> dict:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    r = subprocess.run(
        ["python3", str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )
    return json.loads(r.stdout or "{}")


def _warned(out: dict) -> bool:
    return "additionalContext" in out.get("hookSpecificOutput", {})


def _decision(out: dict) -> str | None:
    return out.get("hookSpecificOutput", {}).get("permissionDecision")


def test_warns_on_issue_create():
    assert _warned(_run("gh issue create --title x"))


def test_warns_on_label_create():
    assert _warned(_run("gh label create bug --color ff0000"))


def test_never_denies():
    # It steers, it does not block.
    assert _decision(_run("gh issue create --title x")) != "deny"


def test_suppressed_when_pulse_issues_gh():
    assert (
        _run('bash pulse.sh add --type feature "x" && gh issue create --title x') == {}
    )


def test_suppressed_when_gh_track():
    assert _run("gh-track set-field status Done && gh issue create --title x") == {}


def test_allows_unrelated():
    assert _run("ls -la") == {}
    assert _run("gh pr create --title x") == {}


def test_no_false_positive_in_quoted_string():
    assert _run('git commit -m "run gh issue create instead"') == {}
    assert _run("echo see the gh label create docs") == {}


def test_respects_env_disable():
    env = dict(os.environ, CLAUDE_GUARD_GH_VERBS="0")
    assert _run("gh issue create --title x", env=env) == {}

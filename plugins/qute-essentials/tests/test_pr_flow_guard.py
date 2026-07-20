"""Tests for pr-flow-guard.py — opt-in, default-OFF PR-flow enforcement hook.

Verifies:
- inert (allow) by default: no marker, marker=false, and outside a repo;
- active only when the repo sets quteEnforcePrReview:true — blocks `gh pr create`;
- command-boundary matching: an incidental `gh pr create` inside a quoted string or
  another argument is NOT blocked (the SHIP-WITH-NITS follow-up).

The merge path calls real `gh`; it's exercised via the create path + config unit here,
with full merge deny/allow proven separately (mocked gh) — this file focuses on gating
and the false-positive fix, which need no network.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "hooks" / "pr-flow-guard.py"


def _run(cwd: Path, command: str) -> dict:
    payload = json.dumps(
        {"tool_name": "Bash", "cwd": str(cwd), "tool_input": {"command": command}}
    )
    r = subprocess.run(
        ["python3", str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return json.loads(r.stdout or "{}")


def _decision(out: dict) -> str | None:
    return out.get("hookSpecificOutput", {}).get("permissionDecision")


def _repo(tmp_path: Path, marker) -> Path:
    root = tmp_path / "repo"
    (root / ".claude").mkdir(parents=True)
    (root / ".git").mkdir()
    cfg = {} if marker is None else {"quteEnforcePrReview": marker}
    (root / ".claude" / "settings.json").write_text(json.dumps(cfg))
    return root


def test_inert_without_marker(tmp_path):
    root = _repo(tmp_path, None)
    assert _run(root, "gh pr create --title x") == {}


def test_inert_with_marker_false(tmp_path):
    root = _repo(tmp_path, False)
    assert _run(root, "gh pr create --title x") == {}


def test_inert_outside_repo(tmp_path):
    outside = tmp_path / "plain"
    outside.mkdir()
    assert _run(outside, "gh pr create --title x") == {}


def test_active_blocks_create(tmp_path):
    root = _repo(tmp_path, True)
    assert _decision(_run(root, "gh pr create --title x")) == "deny"


def test_active_allows_unrelated(tmp_path):
    root = _repo(tmp_path, True)
    assert _run(root, "ls -la") == {}


def test_active_allows_env_prefixed_create(tmp_path):
    # a legit command with an env-var prefix is still a real invocation -> blocked
    root = _repo(tmp_path, True)
    assert _decision(_run(root, "FOO=1 gh pr create --title x")) == "deny"
    # and chained after a separator
    assert _decision(_run(root, "cd x && gh pr create --title x")) == "deny"


def test_no_false_positive_in_quoted_string(tmp_path):
    root = _repo(tmp_path, True)
    # incidental mention, not a real invocation -> must NOT block
    assert _run(root, 'git commit -m "use gh pr create instead"') == {}
    assert _run(root, "printf %s gh pr create") == {}
    assert _run(root, "echo see the gh pr create docs") == {}


# ── merge gate: allowAgentSelfMerge (config via .github/qute-pr.yml) ───────
import os  # noqa: E402


def _yml_repo(tmp_path: Path, body: str) -> Path:
    root = tmp_path / "repo"
    (root / ".github").mkdir(parents=True)
    (root / ".git").mkdir()
    (root / ".github" / "qute-pr.yml").write_text(body)
    return root


def _run_env(cwd: Path, command: str, env: dict) -> dict:
    payload = json.dumps(
        {"tool_name": "Bash", "cwd": str(cwd), "tool_input": {"command": command}}
    )
    r = subprocess.run(
        ["python3", str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )
    return json.loads(r.stdout or "{}")


def _gh_stub(tmp_path: Path, review_count: int) -> str:
    """A bin/ dir whose `gh` stub returns `review_count` for the reviews query."""
    bind = tmp_path / "bin"
    bind.mkdir()
    gh = bind / "gh"
    gh.write_text(
        "#!/usr/bin/env bash\n"
        'for a in "$@"; do case "$a" in */reviews) echo %d; exit 0;; esac; done\n'
        "# repo view / pr view resolution\n"
        'case "$*" in\n'
        '  *"repo view"*) echo o/r; exit 0;;\n'
        '  *"pr view"*) echo \'{"number": 7}\'; exit 0;;\n'
        "esac\n"
        "exit 0\n" % review_count
    )
    gh.chmod(0o755)
    return str(bind)


def test_merge_denied_when_self_merge_off(tmp_path):
    # default allowAgentSelfMerge=false + enforce=true -> merge blocked, no gh needed
    root = _yml_repo(tmp_path, "enforce: true\nallowAgentSelfMerge: false\n")
    out = _run(root, "gh pr merge 7 --repo o/r --squash")
    assert _decision(out) == "deny"
    assert (
        "self-merge is DISABLED"
        in out["hookSpecificOutput"]["permissionDecisionReason"]
    )


def test_merge_allowed_when_self_merge_on_and_review_exists(tmp_path):
    root = _yml_repo(tmp_path, "enforce: true\nallowAgentSelfMerge: true\n")
    env = dict(os.environ, PATH=_gh_stub(tmp_path, 1) + os.pathsep + os.environ["PATH"])
    out = _run_env(root, "gh pr merge 7 --repo o/r --squash", env)
    assert out == {}  # allowed


def test_merge_denied_when_self_merge_on_but_no_review(tmp_path):
    root = _yml_repo(tmp_path, "enforce: true\nallowAgentSelfMerge: true\n")
    env = dict(os.environ, PATH=_gh_stub(tmp_path, 0) + os.pathsep + os.environ["PATH"])
    out = _run_env(root, "gh pr merge 7 --repo o/r --squash", env)
    assert _decision(out) == "deny"
    assert "no independent" in out["hookSpecificOutput"]["permissionDecisionReason"]


def test_create_blocked_via_qute_pr_yml_enforce(tmp_path):
    root = _yml_repo(tmp_path, "enforce: true\n")
    assert _decision(_run(root, "gh pr create --title x")) == "deny"

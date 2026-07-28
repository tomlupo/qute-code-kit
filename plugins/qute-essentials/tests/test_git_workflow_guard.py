"""Tests for the branch-workflow guard (hooks/git-workflow-guard.py).

Every test builds real throwaway git repos in a tmpdir and invokes the hook as
a subprocess exactly as Claude Code does — JSON payload on stdin — then asserts
the allow/deny decision. HOME is redirected to a tmpdir so the developer's own
``~/.claude/qute-guards.json`` can never flip a test.

Two properties are load-bearing and are asserted explicitly:

* the guard NEVER returns ``ask`` (an interactive prompt stalls a backgrounded
  agent session at waiting/blocked until a human attaches);
* per-repo scoping — a git command aimed at another repo (``git -C``, ``cd``)
  is evaluated against THAT repo's branch and config, not the session's.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parent.parent / "hooks" / "git-workflow-guard.py"

STD_CFG = {
    "protected_branch": "main",
    "integration_branch": "dev",
    "release_tool": "commitizen (/ship)",
}


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True
    )


def _make_repo(
    root: Path,
    branch: str = "main",
    guard_cfg: dict | None = None,
    *,
    origin_dev: bool = False,
    detached: bool = False,
) -> Path:
    """A throwaway repo on `branch`, optionally opted into the guard.

    ``guard_cfg=None`` writes NO ``.claude/git-guard.json`` — i.e. the repo is
    not opted in. ``origin_dev`` fakes a remote-tracking ``origin/dev`` ref so
    the integration-branch default can be exercised without a real remote.
    """
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@t.t")
    _git(root, "config", "user.name", "t")
    _git(root, "checkout", "-q", "-b", "main")
    (root / "f.txt").write_text("x")
    _git(root, "add", "f.txt")
    _git(root, "commit", "-q", "-m", "init")
    if branch != "main":
        _git(root, "checkout", "-q", "-b", branch)
    if origin_dev:
        _git(root, "update-ref", "refs/remotes/origin/dev", "HEAD")
    if detached:
        _git(root, "checkout", "-q", "--detach", "HEAD")
    if guard_cfg is not None:
        cdir = root / ".claude"
        cdir.mkdir(exist_ok=True)
        (cdir / "git-guard.json").write_text(json.dumps(guard_cfg))
    return root


def _write_raw_cfg(root: Path, text: str) -> None:
    cdir = root / ".claude"
    cdir.mkdir(exist_ok=True)
    (cdir / "git-guard.json").write_text(text)


@pytest.fixture()
def home(tmp_path: Path) -> Path:
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    return h


def _run(
    command: str,
    cwd: Path,
    home: Path,
    *,
    tool_name: str = "Bash",
    extra_env: dict | None = None,
) -> tuple[str, dict]:
    """Invoke the hook; return (decision, hookSpecificOutput)."""
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "tool_input": {"command": command},
        "cwd": str(cwd),
        "permission_mode": "auto",
    }
    env = dict(os.environ, HOME=str(home))
    env.pop("CLAUDE_PROJECT_DIR", None)
    env.pop("CLAUDE_SKIP_GUARDS", None)
    env.pop("CLAUDE_GUARD_GIT_WORKFLOW", None)
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout.strip()
    assert out, f"hook produced no stdout (stderr: {proc.stderr})"
    data = json.loads(out)
    hso = data.get("hookSpecificOutput") or {}
    decision = hso.get("permissionDecision", "allow")
    # The guard must never prompt: a prompt stalls a backgrounded agent.
    assert decision != "ask"
    return decision, hso


# ─── protected branch ─────────────────────────────────────────


def test_commit_on_protected_denied(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, hso = _run("git commit -m x", repo, home)
    assert decision == "deny"
    assert "main" in hso["permissionDecisionReason"]


def test_push_of_current_protected_branch_denied(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run("git push origin", repo, home)
    assert decision == "deny"


def test_push_explicit_refspec_to_protected_denied(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, _ = _run("git push origin main", repo, home)
    assert decision == "deny"


def test_force_push_refspec_to_protected_denied(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, _ = _run("git push origin +refs/heads/main", repo, home)
    assert decision == "deny"


# ─── integration branch ───────────────────────────────────────


def test_commit_on_integration_denied(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "dev", STD_CFG)
    decision, hso = _run("git commit -m x", repo, home)
    assert decision == "deny"
    assert "dev" in hso["permissionDecisionReason"]


def test_push_to_integration_denied(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, _ = _run("git push origin dev", repo, home)
    assert decision == "deny"


def test_push_of_current_integration_branch_denied(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "dev", STD_CFG)
    decision, _ = _run("git push", repo, home)
    assert decision == "deny"


def test_explicit_null_integration_allows_commit_on_dev(tmp_path, home):
    """An explicit null means "this repo genuinely has no integration branch"
    and must not be overridden by the `dev` default — even when origin/dev
    exists."""
    repo = _make_repo(
        tmp_path / "r",
        "dev",
        {"protected_branch": "main", "integration_branch": None},
        origin_dev=True,
    )
    decision, _ = _run("git commit -m x", repo, home)
    assert decision == "allow"


def test_integration_defaults_to_dev_when_origin_dev_exists(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "dev", {}, origin_dev=True)
    decision, hso = _run("git commit -m x", repo, home)
    assert decision == "deny"
    assert "integration branch 'dev'" in hso["permissionDecisionReason"]


def test_no_integration_default_without_origin_dev(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "dev", {})
    decision, _ = _run("git commit -m x", repo, home)
    assert decision == "allow"


def test_empty_config_still_protects_main(tmp_path, home):
    """`{}` is a valid opt-in: house defaults apply."""
    repo = _make_repo(tmp_path / "r", "main", {})
    decision, _ = _run("git commit -m x", repo, home)
    assert decision == "deny"


# ─── allowed traffic ──────────────────────────────────────────


def test_commit_on_feature_branch_allowed(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, _ = _run("git commit -m x", repo, home)
    assert decision == "allow"


def test_push_of_feature_branch_allowed(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, _ = _run("git push -u origin feat/x", repo, home)
    assert decision == "allow"


def test_tag_push_allowed_from_protected_branch(tmp_path, home):
    """`/ship` pushes a tag refspec, not a branch — never blocked."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run("git push origin v1.2.3", repo, home)
    assert decision == "allow"


def test_non_mutating_git_allowed_on_protected(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    for cmd in ("git status", "git log --oneline -5", "git diff"):
        decision, _ = _run(cmd, repo, home)
        assert decision == "allow", cmd


def test_detached_head_allowed(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "main", STD_CFG, detached=True)
    decision, _ = _run("git commit -m x", repo, home)
    assert decision == "allow"


def test_non_bash_tool_allowed(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run("git commit -m x", repo, home, tool_name="Write")
    assert decision == "allow"


# ─── opt-in / fail-open ───────────────────────────────────────


def test_repo_without_config_is_a_noop(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "main", None)
    decision, _ = _run("git commit -m x", repo, home)
    assert decision == "allow"


def test_malformed_config_fails_open(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "main", None)
    _write_raw_cfg(repo, "{not json")
    decision, _ = _run("git commit -m x", repo, home)
    assert decision == "allow"


def test_non_git_directory_allowed(tmp_path, home):
    plain = tmp_path / "plain"
    plain.mkdir()
    decision, _ = _run("git commit -m x", plain, home)
    assert decision == "allow"


def test_guard_toggled_off_allows_everything(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    (home / ".claude" / "qute-guards.json").write_text(
        json.dumps({"git-workflow": {"enabled": False}})
    )
    decision, _ = _run("git commit -m x", repo, home)
    assert decision == "allow"


def test_env_override_disables_guard(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run(
        "git commit -m x", repo, home, extra_env={"CLAUDE_GUARD_GIT_WORKFLOW": "0"}
    )
    assert decision == "allow"


def test_skip_all_guards_disables_guard(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run(
        "git commit -m x", repo, home, extra_env={"CLAUDE_SKIP_GUARDS": "1"}
    )
    assert decision == "allow"


# ─── per-repo scoping ─────────────────────────────────────────


def test_sibling_repo_on_feature_branch_allowed(tmp_path, home):
    """Session sits on protected `main`; the command targets a SIBLING repo
    standing on a feature branch. Evaluated against the sibling -> allow."""
    session = _make_repo(tmp_path / "lab", "main", STD_CFG)
    sibling = _make_repo(tmp_path / "datasets", "feat/data", STD_CFG)
    decision, _ = _run(f"git -C {sibling} commit -m x", session, home)
    assert decision == "allow"


def test_sibling_repo_via_cd_allowed(tmp_path, home):
    session = _make_repo(tmp_path / "lab", "main", STD_CFG)
    sibling = _make_repo(tmp_path / "datasets", "feat/data", STD_CFG)
    decision, _ = _run(f"cd {sibling} && git commit -m x", session, home)
    assert decision == "allow"


def test_sibling_repo_on_protected_branch_denied(tmp_path, home):
    """Mirror image: session on a feature branch, sibling on its protected
    branch -> the sibling's violation is still caught."""
    session = _make_repo(tmp_path / "lab", "feat/work", STD_CFG)
    sibling = _make_repo(tmp_path / "other", "main", STD_CFG)
    decision, _ = _run(f"git -C {sibling} commit -m x", session, home)
    assert decision == "deny"


def test_sibling_repo_without_config_allowed(tmp_path, home):
    session = _make_repo(tmp_path / "lab", "feat/work", STD_CFG)
    sibling = _make_repo(tmp_path / "scratch", "main", None)
    decision, _ = _run(f"git -C {sibling} commit -m x", session, home)
    assert decision == "allow"


def test_sibling_uses_its_own_config_not_the_sessions(tmp_path, home):
    """The sibling protects `trunk`, not `main`; standing on `trunk` there must
    be denied even though the session repo has no such branch."""
    session = _make_repo(tmp_path / "lab", "feat/work", STD_CFG)
    sibling = tmp_path / "other"
    _make_repo(
        sibling, "trunk", {"protected_branch": "trunk", "integration_branch": None}
    )
    decision, hso = _run(f"git -C {sibling} commit -m x", session, home)
    assert decision == "deny"
    assert "trunk" in hso["permissionDecisionReason"]


def test_git_dir_option_scopes_to_target_repo(tmp_path, home):
    session = _make_repo(tmp_path / "lab", "feat/work", STD_CFG)
    sibling = _make_repo(tmp_path / "other", "main", STD_CFG)
    decision, _ = _run(f"git --git-dir={sibling}/.git commit -m x", session, home)
    assert decision == "deny"


def test_chained_command_denied_on_the_offending_segment(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run("git add -A && git commit -m x && echo done", repo, home)
    assert decision == "deny"


# ─── guidance text ────────────────────────────────────────────


def test_denial_names_the_route_and_the_override(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    _, hso = _run("git commit -m x", repo, home)
    guidance = hso["additionalContext"]
    assert "pull request" in guidance
    assert "git switch -c" in guidance
    assert "/guard git-workflow off" in guidance
    assert "commitizen (/ship)" in guidance


def test_denial_guidance_without_integration_branch(tmp_path, home):
    repo = _make_repo(
        tmp_path / "r", "main", {"integration_branch": None, "release_tool": None}
    )
    _, hso = _run("git commit -m x", repo, home)
    guidance = hso["additionalContext"]
    assert "'main' is the protected branch" in guidance
    assert "/guard git-workflow off" in guidance


# ─── push destination resolution ──────────────────────────────
#
# The regression class the original guard missed entirely: it compared the
# refspec text against the branch name, so `git push origin HEAD` — the shape
# an agent reaches for most naturally — was read as destination "HEAD", never
# equal to "main", and sailed through on the protected branch. These tests pin
# every refspec shape that resolves to a guarded branch, on BOTH a guarded
# branch and a feature branch, so the same hole cannot be reopened.

# Shapes that must be DENIED while standing on the guarded branch itself,
# because they all resolve to the current (guarded) branch.
CURRENT_BRANCH_PUSHES = [
    "git push origin HEAD",
    "git push origin @",
    "git push origin +HEAD",
    "git push origin +@",
    "git push --force-with-lease origin HEAD",
    "git push -u origin HEAD",
    "git push -o ci.skip origin HEAD",
]

# Shapes that name a guarded branch outright and must be denied from ANY
# branch, feature branches included.
EXPLICIT_MAIN_PUSHES = [
    "git push origin main",
    "git push origin +main",
    "git push origin refs/heads/main",
    "git push origin +refs/heads/main",
    "git push origin HEAD:main",
    "git push origin @:main",
    "git push origin HEAD:refs/heads/main",
    "git push origin +HEAD:refs/heads/main",
    "git push origin feat/x:main",
    "git push origin :main",
]

# Destinations the guard cannot resolve. Fail CLOSED: they may target a
# guarded branch, and a check that cannot verify must not report success.
UNRESOLVABLE_PUSHES = [
    "git push origin $BRANCH",
    "git push origin refs/heads/*:refs/heads/*",
    "git push origin @{-1}",
    "git push origin HEAD~1",
    "git push origin main^",
    "git push origin main:",
]


@pytest.mark.parametrize("cmd", CURRENT_BRANCH_PUSHES)
def test_current_branch_push_shapes_denied_on_protected(cmd, tmp_path, home):
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, hso = _run(cmd, repo, home)
    assert decision == "deny", cmd
    assert "main" in hso["permissionDecisionReason"]


@pytest.mark.parametrize("cmd", CURRENT_BRANCH_PUSHES)
def test_current_branch_push_shapes_denied_on_integration(cmd, tmp_path, home):
    repo = _make_repo(tmp_path / "r", "dev", STD_CFG)
    decision, hso = _run(cmd, repo, home)
    assert decision == "deny", cmd
    assert "dev" in hso["permissionDecisionReason"]


@pytest.mark.parametrize("cmd", CURRENT_BRANCH_PUSHES)
def test_current_branch_push_shapes_allowed_on_feature_branch(cmd, tmp_path, home):
    """Same shapes, standing on a feature branch: they resolve to `feat/x`,
    which is not guarded, so they must sail through."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, _ = _run(cmd, repo, home)
    assert decision == "allow", cmd


@pytest.mark.parametrize("cmd", EXPLICIT_MAIN_PUSHES)
def test_explicit_protected_destination_denied_from_feature_branch(cmd, tmp_path, home):
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, hso = _run(cmd, repo, home)
    assert decision == "deny", cmd
    assert "main" in hso["permissionDecisionReason"]


@pytest.mark.parametrize("cmd", EXPLICIT_MAIN_PUSHES)
def test_explicit_protected_destination_denied_from_protected_branch(
    cmd, tmp_path, home
):
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run(cmd, repo, home)
    assert decision == "deny", cmd


@pytest.mark.parametrize(
    "cmd",
    [
        "git push origin dev",
        "git push origin refs/heads/dev",
        "git push origin +refs/heads/dev",
        "git push origin HEAD:dev",
        "git push origin @:refs/heads/dev",
    ],
)
def test_explicit_integration_destination_denied_from_feature_branch(
    cmd, tmp_path, home
):
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, hso = _run(cmd, repo, home)
    assert decision == "deny", cmd
    assert "dev" in hso["permissionDecisionReason"]


@pytest.mark.parametrize("cmd", UNRESOLVABLE_PUSHES)
def test_unresolvable_destination_denied_on_protected(cmd, tmp_path, home):
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, hso = _run(cmd, repo, home)
    assert decision == "deny", cmd
    assert "cannot resolve" in hso["permissionDecisionReason"], cmd


@pytest.mark.parametrize("cmd", UNRESOLVABLE_PUSHES)
def test_unresolvable_destination_denied_on_feature_branch(cmd, tmp_path, home):
    """Fail-closed applies everywhere: `refs/heads/*:refs/heads/*` from a
    feature branch still writes to `main`."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, hso = _run(cmd, repo, home)
    assert decision == "deny", cmd
    assert "cannot resolve" in hso["permissionDecisionReason"], cmd


def test_head_push_on_detached_head_is_unresolvable(tmp_path, home):
    """Detached HEAD has no branch name, so `HEAD` cannot be resolved — deny
    rather than guess. (git itself rejects this push; denying costs nothing.)"""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG, detached=True)
    decision, hso = _run("git push origin HEAD", repo, home)
    assert decision == "deny"
    assert "cannot resolve" in hso["permissionDecisionReason"]


def test_unresolvable_push_is_a_noop_in_a_repo_without_config(tmp_path, home):
    """Fail-CLOSED on unresolvable destinations must not leak into repos that
    never opted in — those stay a total no-op."""
    repo = _make_repo(tmp_path / "r", "main", None)
    decision, _ = _run("git push origin $BRANCH", repo, home)
    assert decision == "allow"


@pytest.mark.parametrize(
    "cmd",
    [
        "git push origin feat/x",
        "git push origin main:feat/x",  # only the dst half counts
        "git push origin HEAD:feat/x",
        "git push origin refs/tags/v1.2.3",
        "git push origin v1.2.3",
    ],
)
def test_unguarded_destinations_allowed_from_protected_branch(cmd, tmp_path, home):
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run(cmd, repo, home)
    assert decision == "allow", cmd


@pytest.mark.parametrize("cmd", ["git push", "git push origin", "git push -u origin"])
def test_bare_push_fallback_not_regressed(cmd, tmp_path, home):
    """The no-refspec fallback (push the current branch) predates this fix and
    must keep working: denied on guarded branches, allowed on feature ones."""
    for branch, expected in (("main", "deny"), ("dev", "deny"), ("feat/x", "allow")):
        repo = _make_repo(tmp_path / branch.replace("/", "_"), branch, STD_CFG)
        decision, _ = _run(cmd, repo, home)
        assert decision == expected, f"{cmd} on {branch}"


def test_sibling_repo_head_push_scoped_to_sibling(tmp_path, home):
    """`HEAD` resolves against the TARGET repo's branch, not the session's."""
    session = _make_repo(tmp_path / "lab", "feat/work", STD_CFG)
    sibling = _make_repo(tmp_path / "other", "main", STD_CFG)
    decision, _ = _run(f"git -C {sibling} push origin HEAD", session, home)
    assert decision == "deny"

    session2 = _make_repo(tmp_path / "lab2", "main", STD_CFG)
    sibling2 = _make_repo(tmp_path / "other2", "feat/data", STD_CFG)
    decision, _ = _run(f"git -C {sibling2} push origin HEAD", session2, home)
    assert decision == "allow"

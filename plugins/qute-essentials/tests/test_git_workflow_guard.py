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


def _set_alias(root: Path, name: str, expansion: str) -> None:
    _git(root, "config", f"alias.{name}", expansion)


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


# ─── `--all` / `--mirror` push every local branch ─────────────
#
# Defect 20, and the last of the old "documented gaps". `git push --all origin`
# from a feature branch is an ordinary invocation, and verified against real
# git it writes `main -> main` when a local `main` exists — so by this guard's
# own criterion it was a defect, not a deliberate omission. The destination set
# is the LOCAL BRANCH LIST; nothing on the command line names it, and these
# flags override `push.default` too.

PUSH_ALL_FORMS = [
    "git push --all origin",
    "git push --branches origin",
    "git push --mirror origin",
    "git push origin --all",
    "git push --all",
    "git push --all --force-with-lease origin",
]


@pytest.mark.parametrize("cmd", PUSH_ALL_FORMS)
def test_push_all_denied_from_a_feature_branch_when_guarded_exists(cmd, tmp_path, home):
    """The whole point: standing on `feat/x` is no protection, because `main`
    is in the local branch list and gets written."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)  # `main` exists locally
    decision, hso = _run(cmd, repo, home)
    assert decision == "deny", cmd
    assert "main" in hso["permissionDecisionReason"], cmd


@pytest.mark.parametrize("cmd", PUSH_ALL_FORMS)
def test_push_all_denied_from_the_guarded_branch_too(cmd, tmp_path, home):
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run(cmd, repo, home)
    assert decision == "deny", cmd


def test_push_all_names_the_integration_branch_when_that_is_what_exists(tmp_path, home):
    repo = _make_repo(
        tmp_path / "r",
        "dev",
        {"protected_branch": "trunk", "integration_branch": "dev"},
    )
    decision, hso = _run("git push --all origin", repo, home)
    assert decision == "deny"
    assert "dev" in hso["permissionDecisionReason"]


def test_push_all_allowed_when_no_guarded_branch_exists_locally(tmp_path, home):
    """Not fail-closed guesswork: if the local branch list holds nothing
    guarded, `--all` writes nothing guarded and must be allowed."""
    repo = _make_repo(
        tmp_path / "r",
        "feat/x",
        {"protected_branch": "release", "integration_branch": None},
    )
    decision, _ = _run("git push --all origin", repo, home)
    assert decision == "allow"


def test_push_all_is_a_noop_in_a_repo_without_config(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "feat/x", None)
    decision, _ = _run("git push --all origin", repo, home)
    assert decision == "allow"


def test_push_all_is_scoped_to_the_target_repo(tmp_path, home):
    session = _make_repo(tmp_path / "lab", "feat/work", STD_CFG)
    sibling = _make_repo(
        tmp_path / "other",
        "feat/y",
        {"protected_branch": "release", "integration_branch": None},
    )
    decision, _ = _run(f"git -C {sibling} push --all origin", session, home)
    assert decision == "allow", "the sibling has no local `release` branch"


def test_push_all_overrides_push_default(tmp_path, home):
    """`--all` ignores push.default, so `nothing` must not make it look safe."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    _git(repo, "config", "push.default", "nothing")
    decision, _ = _run("git push --all origin", repo, home)
    assert decision == "deny"


def test_tags_flag_is_not_an_all_branches_push(tmp_path, home):
    """`--tags` pushes tags in addition to the refspec — no branch dst, so it
    must not be swept up with `--all`."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, _ = _run("git push --tags origin feat/x", repo, home)
    assert decision == "allow"


# ─── redirections are not arguments ───────────────────────────
#
# Defect 28, parsing axis. Bash allows a redirection ANYWHERE in a simple
# command, including in front of the command word — verified: `>/tmp/out echo
# hi` runs `echo`, and `echo hi >main` writes a FILE called `main`.

LEADING_REDIRECTIONS = [
    ">/tmp/guard-test.out",
    ">> /tmp/guard-test.out",
    "2>/tmp/guard-test.out",
    "&>/tmp/guard-test.out",
    "> /tmp/guard-test.out",
    "2>&1 >/tmp/guard-test.out",
    "</dev/null",
]


@pytest.mark.parametrize("redir", LEADING_REDIRECTIONS)
def test_leading_redirection_does_not_hide_a_commit(redir, tmp_path, home):
    """The redirection was left as token 0, so the segment stopped looking like
    a git command at all."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, hso = _run(f"{redir} git commit -m x", repo, home)
    assert decision == "deny", redir
    assert "main" in hso["permissionDecisionReason"], redir


@pytest.mark.parametrize("redir", LEADING_REDIRECTIONS)
def test_leading_redirection_does_not_hide_a_push(redir, tmp_path, home):
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, hso = _run(f"{redir} git push origin main", repo, home)
    assert decision == "deny", redir
    assert "main" in hso["permissionDecisionReason"], redir


@pytest.mark.parametrize("redir", LEADING_REDIRECTIONS)
def test_leading_redirection_does_not_manufacture_a_denial(redir, tmp_path, home):
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, _ = _run(f"{redir} git commit -m x", repo, home)
    assert decision == "allow", redir


def test_a_redirect_target_is_not_a_refspec(tmp_path, home):
    """`git push origin >main` pushes the CURRENT branch and writes a file
    called `main`. Counting `>main` as an explicit refspec suppressed the
    current-branch fallback and allowed a push of `main` itself."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, hso = _run("git push origin >main", repo, home)
    assert decision == "deny"
    assert "current branch" in hso["permissionDecisionReason"]


def test_a_redirect_target_is_not_a_branch_destination(tmp_path, home):
    """Mirror: the file name must not be read as a guarded destination
    either — from a feature branch this pushes nothing guarded."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, _ = _run("git push origin feat/x >main", repo, home)
    assert decision == "allow"


def test_trailing_redirections_do_not_disturb_a_normal_command(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    for cmd in (
        "git commit -m x >>log 2>&1",
        "git commit -m x >/dev/null",
        "git push origin main 2>&1 | tee log",
    ):
        decision, _ = _run(cmd, repo, home)
        assert decision == "deny", cmd


def test_a_redirection_does_not_hide_a_cd(tmp_path, home):
    session = _make_repo(tmp_path / "lab", "feat/work", STD_CFG)
    other = _make_repo(tmp_path / "other", "main", STD_CFG)
    decision, _ = _run(f">/dev/null cd {other} && git commit -m x", session, home)
    assert decision == "deny"


# ─── here-doc bodies are data ─────────────────────────────────
#
# Defect 30, an over-denial. `cat <<EOF … EOF` feeds its body to stdin; bash
# never runs those lines. Splitting on newlines turned each one into a command,
# so a `git commit` line inside a here-doc could be blocked — in a guard whose
# docs call false blocks defects.


@pytest.mark.parametrize(
    "cmd",
    [
        "cat <<EOF\ngit commit -m x\nEOF",
        "cat <<'EOF'\ngit push origin main\nEOF",
        'cat <<"EOF"\ngit commit -m x\nEOF',
        "cat <<- END\n\tgit commit -m x\n\tEND",
        "cat <<EOF > script.sh\ngit commit -m x\ngit push origin main\nEOF",
    ],
)
def test_heredoc_body_is_not_executed(cmd, tmp_path, home):
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run(cmd, repo, home)
    assert decision == "allow", cmd


def test_a_real_command_after_a_heredoc_is_still_seen(tmp_path, home):
    """The body ends at its terminator — everything after it is live code."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, hso = _run(
        "cat <<EOF > script.sh\ngit commit -m fake\nEOF\ngit commit -m real",
        repo,
        home,
    )
    assert decision == "deny"
    assert "main" in hso["permissionDecisionReason"]


def test_a_heredoc_terminator_must_match_to_end_the_body(tmp_path, home):
    """A `<<-` body allows leading tabs on its terminator; a plain `<<` does
    not, so an indented `EOF` does not close it."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run("cat <<-END\n\tgit commit -m x\n\tEND", repo, home)
    assert decision == "allow"


@pytest.mark.parametrize("near_miss", [" EOF", "EOF ", "\tEOF", "EOFX", "eof"])
def test_a_near_miss_terminator_does_not_close_a_heredoc(near_miss, tmp_path, home):
    """Defect 31. Bash needs the terminator line to match EXACTLY — verified:
    an indented ` EOF` leaves the body open. Matching a stripped line closed it
    early and handed the remaining DATA lines back to the parser as commands."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run(
        f"cat <<EOF\nline1\n{near_miss}\ngit commit -m x\nEOF", repo, home
    )
    assert decision == "allow", near_miss


def test_an_exact_terminator_does_close_the_heredoc(tmp_path, home):
    """The control: once it matches exactly, what follows is live code."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run("cat <<EOF\nline1\nEOF\ngit commit -m x", repo, home)
    assert decision == "deny"


def test_a_dash_heredoc_terminator_strips_only_tabs(tmp_path, home):
    """`<<-` strips leading TABS, not spaces — a space-indented terminator
    leaves the body open."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run("cat <<-END\nline1\n END\ngit commit -m x\nEND", repo, home)
    assert decision == "allow"

    decision, _ = _run("cat <<-END\nline1\n\tEND\ngit commit -m x", repo, home)
    assert decision == "deny", "a tab-indented terminator DOES close a <<- body"


@pytest.mark.parametrize(
    "delim",
    ["EOF", "\\EOF", "'EOF'", '"EOF"', 'E"OF"', "E'OF'", "EO\\F"],
)
def test_a_quoted_heredoc_delimiter_still_terminates(delim, tmp_path, home):
    """Defect 34. Bash applies quote REMOVAL to the here-doc word, so
    `<<\\EOF`, `<<E"OF"` and `<<'EOF'` are all closed by a plain `EOF` —
    verified. Storing the delimiter with its quoting meant it never matched,
    so the body ran to the end of the script and swallowed the real command
    after the terminator."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, hso = _run(f"cat <<{delim}\nbody line\nEOF\ngit commit -m x", repo, home)
    assert decision == "deny", delim
    assert "main" in hso["permissionDecisionReason"], delim


@pytest.mark.parametrize("delim", ["EOF", "\\EOF", "'EOF'", 'E"OF"'])
def test_a_quoted_heredoc_delimiter_still_protects_its_body(delim, tmp_path, home):
    """The other half: the body is still data whichever way it is quoted."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run(f"cat <<{delim}\ngit commit -m x\nEOF", repo, home)
    assert decision == "allow", delim


def test_a_here_string_is_not_a_heredoc(tmp_path, home):
    """`<<<` is a here-STRING — one word, no body — so the command carrying it
    is still a real command."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run("git commit -m x <<<hi", repo, home)
    assert decision == "deny"


# ─── dry runs write nothing ───────────────────────────────────
#
# Defect 27, an over-denial like 24. The criterion is "will this command WRITE
# to a guarded branch?", and a dry run does not. Verified: `git commit
# --dry-run` leaves HEAD where it was. The `-n` spelling is where care is
# needed — for `git push` it IS `--dry-run`, but for `git commit` it is
# `--no-verify`, which really commits (HEAD moves), so it must stay blocked.


@pytest.mark.parametrize("branch", ["main", "dev", "feat/x"])
def test_commit_dry_run_is_allowed(branch, tmp_path, home):
    repo = _make_repo(tmp_path / branch.replace("/", "_"), branch, STD_CFG)
    for cmd in (
        "git commit --dry-run",
        "git commit --dry-run -m x",
        "git commit -a --dry-run",
    ):
        decision, _ = _run(cmd, repo, home)
        assert decision == "allow", f"{cmd} on {branch}"


def test_commit_dash_n_is_no_verify_and_still_blocked(tmp_path, home):
    """`git commit -n` skips hooks but really commits — HEAD moves. Reading it
    as a dry run would turn the guard's main case into an allow."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    for cmd in ("git commit -n -m x", "git commit --no-verify -m x"):
        decision, _ = _run(cmd, repo, home)
        assert decision == "deny", cmd


def test_a_dry_run_option_value_is_not_a_dry_run(tmp_path, home):
    """`git commit -m --dry-run` is a real commit whose MESSAGE is
    `--dry-run`; option values must not be read as flags, or the fix for a
    false positive becomes a bypass."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    for cmd in (
        "git commit -m --dry-run",
        "git commit --message --dry-run",
        "git commit -F --dry-run",
        "git commit --author --dry-run -m x",
    ):
        decision, _ = _run(cmd, repo, home)
        assert decision == "deny", cmd


def test_commit_dry_run_after_a_double_dash_is_a_pathspec(tmp_path, home):
    """After `--` everything is a path, so a file called `--dry-run` must not
    disarm the guard."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run("git commit -m x -- --dry-run", repo, home)
    assert decision == "deny"


@pytest.mark.parametrize("branch", ["main", "dev", "feat/x"])
@pytest.mark.parametrize(
    "cmd",
    [
        "git push --dry-run",
        "git push -n",
        "git push --dry-run origin main",
        "git push -n origin main",
        "git push --all --dry-run origin",
        "git push --mirror -n origin",
        "git push --dry-run origin $BRANCH",
    ],
)
def test_push_dry_run_is_allowed(cmd, branch, tmp_path, home):
    """Nothing is sent, so nothing is blocked — including the shapes that
    would otherwise deny on an unresolvable destination or `--all`."""
    repo = _make_repo(tmp_path / branch.replace("/", "_"), branch, STD_CFG)
    decision, _ = _run(cmd, repo, home)
    assert decision == "allow", f"{cmd} on {branch}"


def test_push_dry_run_as_an_option_value_is_not_a_dry_run(tmp_path, home):
    """`-o` consumes its value, so `git push -o --dry-run origin main` really
    pushes."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, _ = _run("git push -o --dry-run origin main", repo, home)
    assert decision == "deny"


# ─── tag pushes are never branch pushes ───────────────────────
#
# Defect 24, parsing axis, and an OVER-denial rather than a bypass — which
# still makes it a defect, and one that falsified a documented claim: the docs
# have always said tag pushes are never blocked, and `/ship` relies on it.
# Verified against real git: from `main` with the branch AHEAD of the remote,
# `git push --tags origin --dry-run` reports the tag alone and no branch
# update, and `git push origin tag main` in a repo holding a TAG called `main`
# reports `[new tag] main -> main`.


@pytest.mark.parametrize(
    "cmd",
    [
        "git push --tags origin",
        "git push origin --tags",
        "git push --tags",
        "git push --tags --dry-run origin",
    ],
)
@pytest.mark.parametrize("branch", ["main", "dev", "feat/x"])
def test_tags_only_push_is_allowed_from_every_branch(cmd, branch, tmp_path, home):
    """`--tags` with no refspec sends tags and no branch, so the
    current-branch fallback must not fire."""
    repo = _make_repo(tmp_path / branch.replace("/", "_"), branch, STD_CFG)
    decision, _ = _run(cmd, repo, home)
    assert decision == "allow", f"{cmd} on {branch}"


@pytest.mark.parametrize("branch", ["main", "dev", "feat/x"])
def test_follow_tags_still_pushes_the_branch(branch, tmp_path, home):
    """`--follow-tags` is the opposite of `--tags`: a normal branch push PLUS
    reachable tags, so the fallback must stay armed."""
    expected = "allow" if branch == "feat/x" else "deny"
    repo = _make_repo(tmp_path / branch.replace("/", "_"), branch, STD_CFG)
    decision, _ = _run("git push --follow-tags origin", repo, home)
    assert decision == expected, branch


def test_tags_with_an_explicit_refspec_still_reads_the_refspec(tmp_path, home):
    """`--tags` alongside a refspec pushes both, so a guarded destination on
    the command line is still caught."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, hso = _run("git push --tags origin main", repo, home)
    assert decision == "deny"
    assert "main" in hso["permissionDecisionReason"]


@pytest.mark.parametrize("branch", ["main", "dev", "feat/x"])
def test_tag_shorthand_is_not_a_branch_destination(branch, tmp_path, home):
    """`git push origin tag <name>` is `refs/tags/<name>` — even when the tag
    is called `main`, which is the shape that was wrongly blocked."""
    repo = _make_repo(tmp_path / branch.replace("/", "_"), branch, STD_CFG)
    for cmd in (
        "git push origin tag main",
        "git push origin tag dev",
        "git push origin tag v1.2.3",
    ):
        decision, _ = _run(cmd, repo, home)
        assert decision == "allow", f"{cmd} on {branch}"


def test_tag_shorthand_does_not_swallow_a_following_branch_refspec(tmp_path, home):
    """Only the word right after `tag` is a tag; a later refspec is read
    normally."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, hso = _run("git push origin tag v1.0 main", repo, home)
    assert decision == "deny"
    assert "main" in hso["permissionDecisionReason"]


def test_tag_shorthand_suppresses_the_current_branch_fallback(tmp_path, home):
    """`git push origin tag v1` pushes only that tag — verified — so standing
    on a guarded branch must not deny it."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run("git push origin tag v1.0", repo, home)
    assert decision == "allow"


def test_a_trailing_bare_tag_word_is_still_read_as_a_refspec(tmp_path, home):
    """With nothing after it, `tag` is not the shorthand (git errors), so it
    keeps its ordinary reading as a refspec — and `main` after a remote is
    still a branch."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, _ = _run("git push origin main tag", repo, home)
    assert decision == "deny"


# ─── where a refspec-less push actually goes ──────────────────
#
# Defect 17, environment axis. "No refspec" was read as "pushes the current
# branch", but git consults config first — and two ordinary settings redirect
# it. Verified against real git: from `feat/x` with an upstream of
# `origin/main`, `git push --dry-run` reports `feat/x -> main` under BOTH
# `push.default=upstream` and a configured `remote.origin.push`.


def _set_upstream(repo: Path, branch: str, remote: str, merge: str) -> None:
    _git(repo, "config", f"branch.{branch}.remote", remote)
    _git(repo, "config", f"branch.{branch}.merge", merge)


@pytest.mark.parametrize("mode", ["upstream", "tracking"])
def test_push_default_upstream_follows_the_configured_upstream(mode, tmp_path, home):
    """`push.default=upstream` sends a bare push to `branch.<cur>.merge` — for
    a branch made with `git checkout -b feat/x origin/main`, that is `main`."""
    repo = _make_repo(tmp_path / f"r{mode}", "feat/x", STD_CFG)
    _set_upstream(repo, "feat/x", "origin", "refs/heads/main")
    _git(repo, "config", "push.default", mode)
    decision, hso = _run("git push", repo, home)
    assert decision == "deny"
    assert "main" in hso["permissionDecisionReason"]
    assert "no refspec" in hso["permissionDecisionReason"]


def test_push_default_upstream_to_an_unguarded_branch_allowed(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    _set_upstream(repo, "feat/x", "origin", "refs/heads/feat/upstream")
    _git(repo, "config", "push.default", "upstream")
    decision, _ = _run("git push", repo, home)
    assert decision == "allow"


def test_push_default_upstream_pointing_at_integration_denied(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    _set_upstream(repo, "feat/x", "origin", "refs/heads/dev")
    _git(repo, "config", "push.default", "upstream")
    decision, hso = _run("git push", repo, home)
    assert decision == "deny"
    assert "dev" in hso["permissionDecisionReason"]


def test_push_default_upstream_without_an_upstream_pushes_nothing(tmp_path, home):
    """Git errors out rather than pushing, so there is nothing to guard."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    _git(repo, "config", "push.default", "upstream")
    decision, _ = _run("git push", repo, home)
    assert decision == "allow"


def test_remote_push_refspec_is_honoured(tmp_path, home):
    """`remote.<name>.push` supplies refspecs and takes precedence over
    push.default."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    _git(repo, "config", "remote.origin.push", "refs/heads/feat/x:refs/heads/main")
    decision, hso = _run("git push", repo, home)
    assert decision == "deny"
    assert "main" in hso["permissionDecisionReason"]

    repo2 = _make_repo(tmp_path / "r2", "feat/x", STD_CFG)
    _git(repo2, "config", "remote.origin.push", "refs/heads/feat/x:refs/heads/feat/y")
    decision, _ = _run("git push", repo2, home)
    assert decision == "allow"


def test_remote_push_refspec_is_read_for_the_named_remote(tmp_path, home):
    """The refspec is looked up under the remote actually being pushed to."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    _git(repo, "config", "remote.upstream.push", "refs/heads/feat/x:refs/heads/main")
    decision, _ = _run("git push upstream", repo, home)
    assert decision == "deny"
    # A different remote has no such refspec, so the default applies.
    decision, _ = _run("git push origin", repo, home)
    assert decision == "allow"


@pytest.mark.parametrize("spelling", ["--repo upstream", "--repo=upstream"])
def test_repo_option_names_the_remote_for_the_config_lookup(spelling, tmp_path, home):
    """Defect 19: the separate-token `--repo <r>` form dropped its value, so
    the no-refspec fallback read the DEFAULT remote's push refspec instead of
    `<r>`'s. Both spellings must reach `remote.upstream.push`."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    _git(repo, "config", "remote.upstream.push", "refs/heads/feat/x:refs/heads/main")
    decision, hso = _run(f"git push {spelling}", repo, home)
    assert decision == "deny", spelling
    assert "main" in hso["permissionDecisionReason"], spelling


def test_repo_option_ambiguity_checks_both_candidate_remotes(tmp_path, home):
    """Defect 21. With `--repo=origin upstream` git IGNORES `--repo` and treats
    `upstream` as the repository — so the config lookup has to cover that
    reading too, exactly as the positional-vs-refspec union already does. A
    `remote.upstream.push` aimed at the protected branch was slipping through
    because only `remote.origin.push` was consulted."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    _git(repo, "config", "remote.upstream.push", "refs/heads/feat/x:refs/heads/main")
    decision, hso = _run("git push --repo=origin upstream", repo, home)
    assert decision == "deny"
    assert "main" in hso["permissionDecisionReason"]


def test_repo_option_ambiguity_also_checks_the_option_remote(tmp_path, home):
    """The mirror reading: the guarded refspec hangs off the `--repo` remote."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    _git(repo, "config", "remote.origin.push", "refs/heads/feat/x:refs/heads/main")
    decision, hso = _run("git push --repo=origin upstream", repo, home)
    assert decision == "deny"
    assert "main" in hso["permissionDecisionReason"]


def test_repo_option_ambiguity_allows_when_neither_remote_is_guarded(tmp_path, home):
    """The union must not become a blanket denial — with no guarded push
    refspec on either candidate, a feature branch stays allowed."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    _git(repo, "config", "remote.origin.push", "refs/heads/feat/x:refs/heads/feat/a")
    _git(repo, "config", "remote.upstream.push", "refs/heads/feat/x:refs/heads/feat/b")
    decision, _ = _run("git push --repo=origin upstream", repo, home)
    assert decision == "allow"


def test_two_positionals_settle_the_repo_ambiguity_for_config_too(tmp_path, home):
    """With a second positional git definitively reads the first as the remote,
    so only that one's config applies."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    _git(repo, "config", "remote.origin.push", "refs/heads/feat/x:refs/heads/main")
    decision, _ = _run("git push --repo=origin upstream feat/y", repo, home)
    assert decision == "allow"


@pytest.mark.parametrize("spelling", ["--repo other", "--repo=other"])
def test_repo_option_remote_without_a_push_refspec_is_unaffected(
    spelling, tmp_path, home
):
    """The control: naming a remote that has no configured refspec falls back
    to push.default, so a feature branch stays allowed."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    _git(repo, "config", "remote.upstream.push", "refs/heads/feat/x:refs/heads/main")
    decision, _ = _run(f"git push {spelling}", repo, home)
    assert decision == "allow", spelling


def test_push_remote_precedence_is_followed(tmp_path, home):
    """With no remote on the command line, `branch.<cur>.pushRemote` wins over
    `remote.pushDefault`, which wins over `branch.<cur>.remote`."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    _git(repo, "config", "branch.feat/x.remote", "c")
    _git(repo, "config", "remote.pushDefault", "b")
    _git(repo, "config", "branch.feat/x.pushRemote", "a")
    _git(repo, "config", "remote.a.push", "refs/heads/feat/x:refs/heads/main")
    _git(repo, "config", "remote.b.push", "refs/heads/feat/x:refs/heads/feat/b")
    _git(repo, "config", "remote.c.push", "refs/heads/feat/x:refs/heads/feat/c")
    decision, _ = _run("git push", repo, home)
    assert decision == "deny"


def test_glob_push_refspec_in_config_fails_closed(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    _git(repo, "config", "remote.origin.push", "refs/heads/*:refs/heads/*")
    decision, hso = _run("git push", repo, home)
    assert decision == "deny"
    assert "cannot resolve" in hso["permissionDecisionReason"]


def test_push_default_matching_fails_closed(tmp_path, home):
    """`matching` pushes every branch that exists on both sides, which includes
    the guarded ones — and nothing on the command line names them."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    _git(repo, "config", "push.default", "matching")
    decision, hso = _run("git push", repo, home)
    assert decision == "deny"
    assert "cannot resolve" in hso["permissionDecisionReason"]


def test_push_default_nothing_pushes_nothing(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    _git(repo, "config", "push.default", "nothing")
    decision, _ = _run("git push", repo, home)
    assert decision == "allow"


@pytest.mark.parametrize("mode", ["simple", "current"])
def test_push_default_same_name_modes_keep_the_current_branch_reading(
    mode, tmp_path, home
):
    for branch, expected in (("main", "deny"), ("dev", "deny"), ("feat/x", "allow")):
        repo = _make_repo(
            tmp_path / f"{branch.replace('/', '_')}-{mode}", branch, STD_CFG
        )
        _git(repo, "config", "push.default", mode)
        decision, _ = _run("git push", repo, home)
        assert decision == expected, f"{mode} on {branch}"


def test_explicit_refspec_still_overrides_config(tmp_path, home):
    """Config only applies when the command line gives no refspec."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    _set_upstream(repo, "feat/x", "origin", "refs/heads/main")
    _git(repo, "config", "push.default", "upstream")
    decision, _ = _run("git push origin feat/x", repo, home)
    assert decision == "allow", "an explicit unguarded refspec wins"


def test_implicit_push_config_is_read_from_the_target_repo(tmp_path, home):
    session = _make_repo(tmp_path / "lab", "feat/work", STD_CFG)
    sibling = _make_repo(tmp_path / "other", "feat/x", STD_CFG)
    _set_upstream(sibling, "feat/x", "origin", "refs/heads/main")
    _git(sibling, "config", "push.default", "upstream")
    decision, _ = _run(f"git -C {sibling} push", session, home)
    assert decision == "deny"


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


# ─── `--repo` supplies the remote ─────────────────────────────
#
# Third parsing bypass found by review: `--repo <r>` / `--repo=<r>` names the
# remote, so positional #0 is a REFSPEC, not the remote. The old parser
# discarded it as "the remote", concluded there was no refspec at all, and let
# `git push --repo=origin main` through from a feature branch.

REPO_OPT_PROTECTED_PUSHES = [
    "git push --repo origin main",
    "git push --repo=origin main",
    "git push --repo origin refs/heads/main",
    "git push --repo=origin +main",
    "git push --repo=origin HEAD:main",
    "git push --repo=origin :main",
]


@pytest.mark.parametrize("cmd", REPO_OPT_PROTECTED_PUSHES)
def test_repo_option_protected_destination_denied_from_feature_branch(
    cmd, tmp_path, home
):
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, hso = _run(cmd, repo, home)
    assert decision == "deny", cmd
    assert "main" in hso["permissionDecisionReason"]


@pytest.mark.parametrize("cmd", REPO_OPT_PROTECTED_PUSHES)
def test_repo_option_protected_destination_denied_from_protected_branch(
    cmd, tmp_path, home
):
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run(cmd, repo, home)
    assert decision == "deny", cmd


@pytest.mark.parametrize(
    "cmd", ["git push --repo origin dev", "git push --repo=origin dev"]
)
def test_repo_option_integration_destination_denied(cmd, tmp_path, home):
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, hso = _run(cmd, repo, home)
    assert decision == "deny", cmd
    assert "dev" in hso["permissionDecisionReason"]


@pytest.mark.parametrize(
    "cmd", ["git push --repo origin HEAD", "git push --repo=origin @"]
)
def test_repo_option_head_resolves_to_current_branch(cmd, tmp_path, home):
    for branch, expected in (("main", "deny"), ("dev", "deny"), ("feat/x", "allow")):
        repo = _make_repo(
            tmp_path / f"{branch.replace('/', '_')}-{hash(cmd)}", branch, STD_CFG
        )
        decision, _ = _run(cmd, repo, home)
        assert decision == expected, f"{cmd} on {branch}"


@pytest.mark.parametrize(
    "cmd", ["git push --repo origin feat/y", "git push --repo=origin feat/y"]
)
def test_repo_option_unguarded_destination_allowed(cmd, tmp_path, home):
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, _ = _run(cmd, repo, home)
    assert decision == "allow", cmd


@pytest.mark.parametrize("cmd", ["git push --repo origin", "git push --repo=origin"])
def test_repo_option_without_refspec_falls_back_to_current_branch(cmd, tmp_path, home):
    for branch, expected in (("main", "deny"), ("dev", "deny"), ("feat/x", "allow")):
        repo = _make_repo(
            tmp_path / f"{branch.replace('/', '_')}-{len(cmd)}", branch, STD_CFG
        )
        decision, _ = _run(cmd, repo, home)
        assert decision == expected, f"{cmd} on {branch}"


def test_repo_option_with_positional_remote_is_read_fail_closed(tmp_path, home):
    """Git IGNORES `--repo` when a positional repository is also given, and we
    cannot tell the two readings apart without knowing the repo's remotes. So
    both are honoured: every positional is checked as a refspec, AND the
    current-branch fallback stays alive until a second positional proves the
    first one was the remote."""
    # git's reading: push current branch `main` to remote `upstream` -> denied
    # by the fallback, even though `upstream` looks like a harmless refspec.
    on_main = _make_repo(tmp_path / "m", "main", STD_CFG)
    decision, _ = _run("git push --repo=origin upstream", on_main, home)
    assert decision == "deny"

    # Same shape from a feature branch is genuinely harmless under both
    # readings -> allowed.
    on_feat = _make_repo(tmp_path / "f", "feat/x", STD_CFG)
    decision, _ = _run("git push --repo=origin upstream", on_feat, home)
    assert decision == "allow"

    # Two positionals: git reads `upstream` as the remote and `main` as the
    # refspec. Denied under either reading.
    on_feat2 = _make_repo(tmp_path / "f2", "feat/x", STD_CFG)
    decision, _ = _run("git push --repo=origin upstream main", on_feat2, home)
    assert decision == "deny"


def test_url_as_remote_keeps_positional_slots(tmp_path, home):
    """A URL still occupies the remote slot — positional #0 is the remote."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, _ = _run("git push https://example.invalid/x.git main", repo, home)
    assert decision == "deny"
    decision, _ = _run("git push https://example.invalid/x.git feat/x", repo, home)
    assert decision == "allow"


def test_deletion_flag_refspec_is_read_as_a_destination(tmp_path, home):
    """With the deletion flag the ref names a DESTINATION to remove — the same
    reading a bare refspec already gets, so no special case is needed."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, _ = _run("git push --de" + "lete origin main", repo, home)
    assert decision == "deny"


# ─── a remote whose NAME collides with a guarded branch ───────
#
# `--repo <r>` consumes its value, so the remote NAME never reaches the target
# list: a remote called `main` or `dev` must behave exactly like one called
# `origin`. Round-3 review asserted the opposite — that the option value was
# appended to the positionals and could block a harmless feature-branch push
# on the strength of the remote name alone. It does not reproduce. These tests
# pin the behaviour, including the `origin` control that shows the remote name
# is not what any decision turns on.


@pytest.mark.parametrize("remote", ["main", "dev", "origin"])
@pytest.mark.parametrize("spelling", ["--repo {r}", "--repo={r}"])
def test_colliding_remote_name_allows_feature_push_from_feature_branch(
    remote, spelling, tmp_path, home
):
    """The exact shape round-3 review claimed was broken."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    cmd = f"git push {spelling.format(r=remote)} feat/x"
    decision, _ = _run(cmd, repo, home)
    assert decision == "allow", cmd


@pytest.mark.parametrize("remote", ["main", "dev", "origin"])
@pytest.mark.parametrize("spelling", ["--repo {r}", "--repo={r}"])
@pytest.mark.parametrize("branch", ["main", "dev"])
def test_colliding_remote_name_is_not_what_denies_on_a_guarded_branch(
    remote, spelling, branch, tmp_path, home
):
    """From a GUARDED branch the same command is denied — but by the
    fail-closed union rule, not by the remote's name. With a single positional
    git may still be reading it as the remote and pushing the current branch,
    so the current-branch fallback stays alive. Parametrising `origin`
    alongside `main`/`dev` is the control: all three behave identically, which
    is what proves the remote name plays no part."""
    repo = _make_repo(tmp_path / "r", branch, STD_CFG)
    cmd = f"git push {spelling.format(r=remote)} feat/x"
    decision, hso = _run(cmd, repo, home)
    assert decision == "deny", cmd
    assert "current branch" in hso["permissionDecisionReason"], cmd


@pytest.mark.parametrize("remote", ["main", "dev", "origin"])
@pytest.mark.parametrize("spelling", ["--repo {r}", "--repo={r}"])
@pytest.mark.parametrize("dst", ["main", "dev"])
def test_guarded_destination_denied_through_a_colliding_remote(
    remote, spelling, dst, tmp_path, home
):
    """Mirror image: when the POSITIONAL genuinely is a guarded branch the push
    is denied on that destination — a remote named `main` neither masks it nor
    manufactures it."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    cmd = f"git push {spelling.format(r=remote)} {dst}"
    decision, hso = _run(cmd, repo, home)
    assert decision == "deny", cmd
    assert dst in hso["permissionDecisionReason"], cmd


@pytest.mark.parametrize("spelling", ["--repo main", "--repo=main"])
def test_repo_option_value_never_becomes_a_target(spelling, tmp_path, home):
    """Two positionals settle the ambiguity: git reads `upstream` as the remote
    and `feat/y` as the refspec, so nothing guarded is in play and the remote
    named `main` must not conjure a denial."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, _ = _run(f"git push {spelling} upstream feat/y", repo, home)
    assert decision == "allow"


# ─── the `env` wrapper ────────────────────────────────────────
#
# Fourth parsing bypass found by review. The parser skipped INLINE assignments
# (`FOO=1 git push`) but not the `env` COMMAND, so `env GIT_AUTHOR_NAME=x git
# commit` and bare `env git push origin main` never reached the `git` check at
# all and sailed through on a guarded branch.

ENV_WRAPPED_COMMITS = [
    "env VAR=x git commit -m y",
    "env GIT_AUTHOR_NAME=x GIT_AUTHOR_EMAIL=y@z git commit -m w",
    "env git commit -m y",
    "/usr/bin/env git commit -m y",
    "env -i git commit -m y",
    "env - git commit -m y",
    "env -u SOMEVAR git commit -m y",
    "env -uSOMEVAR git commit -m y",
    "env --unset=SOMEVAR git commit -m y",
    "env --ignore-environment VAR=x git commit -m y",
    "env -iu SOMEVAR VAR=x git commit -m y",
    "FOO=1 env BAR=2 git commit -m y",
]


@pytest.mark.parametrize("cmd", ENV_WRAPPED_COMMITS)
def test_env_wrapped_commit_denied_on_protected(cmd, tmp_path, home):
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, hso = _run(cmd, repo, home)
    assert decision == "deny", cmd
    assert "main" in hso["permissionDecisionReason"], cmd


@pytest.mark.parametrize("cmd", ENV_WRAPPED_COMMITS)
def test_env_wrapped_commit_denied_on_integration(cmd, tmp_path, home):
    repo = _make_repo(tmp_path / "r", "dev", STD_CFG)
    decision, hso = _run(cmd, repo, home)
    assert decision == "deny", cmd
    assert "dev" in hso["permissionDecisionReason"], cmd


@pytest.mark.parametrize("cmd", ENV_WRAPPED_COMMITS)
def test_env_wrapped_commit_allowed_on_feature_branch(cmd, tmp_path, home):
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, _ = _run(cmd, repo, home)
    assert decision == "allow", cmd


ENV_WRAPPED_PUSHES = [
    "env git push origin main",
    "env VAR=x git push origin main",
    "/usr/bin/env git push origin main",
    "env -i git push origin refs/heads/main",
    "env -u SOMEVAR git push origin +main",
    "env git push --repo=origin main",
    "env git push origin HEAD:main",
]


@pytest.mark.parametrize("cmd", ENV_WRAPPED_PUSHES)
def test_env_wrapped_push_to_protected_denied_from_feature_branch(cmd, tmp_path, home):
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, hso = _run(cmd, repo, home)
    assert decision == "deny", cmd
    assert "main" in hso["permissionDecisionReason"], cmd


@pytest.mark.parametrize(
    "cmd", ["env git push", "env VAR=x git push origin", "env -i git push origin HEAD"]
)
def test_env_wrapped_bare_push_follows_the_current_branch(cmd, tmp_path, home):
    for branch, expected in (("main", "deny"), ("dev", "deny"), ("feat/x", "allow")):
        repo = _make_repo(
            tmp_path / f"{branch.replace('/', '_')}-{len(cmd)}", branch, STD_CFG
        )
        decision, _ = _run(cmd, repo, home)
        assert decision == expected, f"{cmd} on {branch}"


def test_env_wrapped_push_of_unguarded_branch_allowed(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, _ = _run("env VAR=x git push -u origin feat/x", repo, home)
    assert decision == "allow"


def test_env_chdir_scopes_to_the_target_repo(tmp_path, home):
    """`env -C dir` moves git before it starts, exactly like git's own `-C`."""
    session = _make_repo(tmp_path / "lab", "feat/work", STD_CFG)
    sibling = _make_repo(tmp_path / "other", "main", STD_CFG)
    for spelling in (f"-C {sibling}", f"--chdir={sibling}"):
        decision, _ = _run(f"env {spelling} git commit -m x", session, home)
        assert decision == "deny", spelling

    session2 = _make_repo(tmp_path / "lab2", "main", STD_CFG)
    sibling2 = _make_repo(tmp_path / "other2", "feat/data", STD_CFG)
    decision, _ = _run(f"env -C {sibling2} git commit -m x", session2, home)
    assert decision == "allow"


# `env` shapes whose command cannot be determined. Fail CLOSED, consistent with
# unresolvable refspecs: a check that cannot verify must not report success.
UNRESOLVABLE_ENV = [
    "env -S 'git commit -m x'",
    "env --split-string='git push origin main'",
    "env -Sgit\\ push",
    "env --argv0 sneaky git push origin main",
    "env -z git commit -m x",
]


@pytest.mark.parametrize("cmd", UNRESOLVABLE_ENV)
def test_unresolvable_env_wrapper_denied(cmd, tmp_path, home):
    for branch in ("main", "dev", "feat/x"):
        repo = _make_repo(
            tmp_path / f"{branch.replace('/', '_')}-{len(cmd)}", branch, STD_CFG
        )
        decision, hso = _run(cmd, repo, home)
        assert decision == "deny", f"{cmd} on {branch}"
        assert "`env ...`" in hso["permissionDecisionReason"], cmd


def test_unresolvable_env_wrapper_is_a_noop_without_config(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "main", None)
    decision, _ = _run("env -S 'git commit -m x'", repo, home)
    assert decision == "allow"


def test_unresolvable_env_without_git_does_not_block_the_chain(tmp_path, home):
    """An unparseable `env` segment that has nothing to do with git must not
    take the whole command down — only the `git` mention makes it worth a deny.
    (`git status` is in the same chain, so the hook is definitely running.)"""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run("env -S 'echo hi' && git status", repo, home)
    assert decision == "allow"


# ─── git aliases ──────────────────────────────────────────────
#
# Fifth parsing bypass found by review: only the literal `commit` and `push`
# were recognised, so `git ci` and `git publish` — the exact shorthands a repo
# defines to make those two verbs easier to type — walked straight past. An
# unrecognised subcommand is now resolved ONE level through
# `git config --get alias.<name>` in the TARGET repo.


def test_alias_to_commit_denied_on_guarded_branches(tmp_path, home):
    for branch, expected in (("main", "deny"), ("dev", "deny"), ("feat/x", "allow")):
        repo = _make_repo(tmp_path / branch.replace("/", "_"), branch, STD_CFG)
        _set_alias(repo, "ci", "commit -s")
        decision, _ = _run("git ci -m x", repo, home)
        assert decision == expected, f"git ci on {branch}"


def test_alias_to_push_with_refspec_denied_from_feature_branch(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    _set_alias(repo, "publish", "push origin main")
    decision, hso = _run("git publish", repo, home)
    assert decision == "deny"
    assert "main" in hso["permissionDecisionReason"]


def test_alias_to_push_head_resolves_against_the_current_branch(tmp_path, home):
    """`publish = push origin HEAD` follows the branch you are standing on."""
    for branch, expected in (("main", "deny"), ("dev", "deny"), ("feat/x", "allow")):
        repo = _make_repo(tmp_path / branch.replace("/", "_"), branch, STD_CFG)
        _set_alias(repo, "publish", "push origin HEAD")
        decision, _ = _run("git publish", repo, home)
        assert decision == expected, f"git publish on {branch}"


def test_alias_args_are_prepended_to_the_command_line(tmp_path, home):
    """`p = push` + `git p origin main` must read as `git push origin main`."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    _set_alias(repo, "p", "push")
    decision, hso = _run("git p origin main", repo, home)
    assert decision == "deny"
    assert "main" in hso["permissionDecisionReason"]

    _set_alias(repo, "po", "push origin")
    decision, _ = _run("git po feat/x", repo, home)
    assert decision == "allow"


def test_alias_to_a_harmless_builtin_allowed(tmp_path, home):
    """`lg = log --graph` expands to a builtin that is neither commit nor push
    — resolvable, and plainly not a guarded verb, so it sails through even on
    the protected branch."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    for name, expansion in (
        ("lg", "log --oneline --graph"),
        ("st", "status -sb"),
        ("co", "checkout"),
    ):
        _set_alias(repo, name, expansion)
        decision, _ = _run(f"git {name}", repo, home)
        assert decision == "allow", name


def test_alias_to_alias_is_unresolvable_and_denied(tmp_path, home):
    """Resolution is deliberately ONE level: an alias pointing at another alias
    is not chased, it is guarded."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    _set_alias(repo, "ci", "commit")
    _set_alias(repo, "c", "ci")
    decision, hso = _run("git c -m x", repo, home)
    assert decision == "deny"
    assert "'c'" in hso["permissionDecisionReason"]
    assert "another alias" in hso["permissionDecisionReason"]


def test_shell_alias_is_unresolvable_and_denied(tmp_path, home):
    """A `!shell` alias is arbitrary shell — it can chain, pipe and re-enter git
    through further aliases — so it is guarded rather than parsed."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    _set_alias(repo, "yolo", "!git commit -am wip && git push origin main")
    decision, hso = _run("git yolo", repo, home)
    assert decision == "deny"
    assert "'yolo'" in hso["permissionDecisionReason"]


def test_unresolvable_alias_denied_from_every_branch(tmp_path, home):
    for branch in ("main", "dev", "feat/x"):
        repo = _make_repo(tmp_path / branch.replace("/", "_"), branch, STD_CFG)
        _set_alias(repo, "sh", "!git status")
        decision, _ = _run("git sh", repo, home)
        assert decision == "deny", branch


def test_unknown_subcommand_without_an_alias_is_allowed(tmp_path, home):
    """No alias of that name -> git itself would error; nothing to guard."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run("git nosuchthing --flag", repo, home)
    assert decision == "allow"


def test_aliases_are_a_noop_in_a_repo_without_config(tmp_path, home):
    """Opt-in gates the alias lookup too: an un-opted-in repo stays a total
    no-op, `!shell` aliases included."""
    repo = _make_repo(tmp_path / "r", "main", None)
    _set_alias(repo, "ci", "commit")
    _set_alias(repo, "sh", "!git push origin main")
    for cmd in ("git ci -m x", "git sh"):
        decision, _ = _run(cmd, repo, home)
        assert decision == "allow", cmd


def test_alias_is_resolved_in_the_target_repo_not_the_session(tmp_path, home):
    """`git -C <other> ci` must read `<other>`'s alias table, not this repo's."""
    session = _make_repo(tmp_path / "lab", "feat/work", STD_CFG)
    sibling = _make_repo(tmp_path / "other", "main", STD_CFG)
    _set_alias(sibling, "ci", "commit")
    decision, _ = _run(f"git -C {sibling} ci -m x", session, home)
    assert decision == "deny"

    # The session repo has no such alias, so the same word there is a no-op.
    on_main = _make_repo(tmp_path / "solo", "main", STD_CFG)
    decision, _ = _run("git ci -m x", on_main, home)
    assert decision == "allow"


def test_env_and_alias_compose(tmp_path, home):
    """The two bypasses stack: `env VAR=x git ci` has to survive both peels."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    _set_alias(repo, "ci", "commit")
    decision, _ = _run("env VAR=x git ci -m y", repo, home)
    assert decision == "deny"


# ─── how git is invoked ───────────────────────────────────────
#
# Eighth shape found by review, and the one that was a hole in the MIDDLE
# rather than an edge: the parser only ever matched `tokens[0] == "git"`, so an
# absolute path to git — an ordinary form that scripts and cron entries use
# constantly — was not a git command as far as the guard was concerned. Nor was
# the `command` / `builtin` / `exec` prefix. Git is now matched on the BASENAME
# of the executable, with those prefixes peeled first.

GIT_INVOCATION_FORMS = [
    "/usr/bin/git",
    "/usr/local/bin/git",
    "command git",
    "command -p git",
    "exec git",
    "exec -c git",
    "command -- git",
    "env VAR=x command git",
    "command env VAR=x git",
]


@pytest.mark.parametrize("form", GIT_INVOCATION_FORMS)
def test_invocation_form_commit_denied_on_protected(form, tmp_path, home):
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, hso = _run(f"{form} commit -m x", repo, home)
    assert decision == "deny", form
    assert "main" in hso["permissionDecisionReason"], form


@pytest.mark.parametrize("form", GIT_INVOCATION_FORMS)
def test_invocation_form_commit_denied_on_integration(form, tmp_path, home):
    repo = _make_repo(tmp_path / "r", "dev", STD_CFG)
    decision, hso = _run(f"{form} commit -m x", repo, home)
    assert decision == "deny", form
    assert "dev" in hso["permissionDecisionReason"], form


@pytest.mark.parametrize("form", GIT_INVOCATION_FORMS)
def test_invocation_form_commit_allowed_on_feature_branch(form, tmp_path, home):
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, _ = _run(f"{form} commit -m x", repo, home)
    assert decision == "allow", form


@pytest.mark.parametrize("form", GIT_INVOCATION_FORMS)
def test_invocation_form_push_to_protected_denied_from_feature_branch(
    form, tmp_path, home
):
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, hso = _run(f"{form} push origin main", repo, home)
    assert decision == "deny", form
    assert "main" in hso["permissionDecisionReason"], form


@pytest.mark.parametrize("form", GIT_INVOCATION_FORMS)
def test_invocation_form_push_of_unguarded_branch_allowed(form, tmp_path, home):
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, _ = _run(f"{form} push -u origin feat/x", repo, home)
    assert decision == "allow", form


@pytest.mark.parametrize("form", ["/usr/bin/git", "command git", "exec git"])
def test_invocation_form_bare_push_follows_the_current_branch(form, tmp_path, home):
    for branch, expected in (("main", "deny"), ("dev", "deny"), ("feat/x", "allow")):
        repo = _make_repo(
            tmp_path / f"{branch.replace('/', '_')}-{len(form)}", branch, STD_CFG
        )
        decision, _ = _run(f"{form} push", repo, home)
        assert decision == expected, f"{form} push on {branch}"


@pytest.mark.parametrize("form", ["/usr/bin/git", "command git"])
def test_invocation_form_scoping_options_still_apply(form, tmp_path, home):
    """`-C` and the alias lookup must survive the new executable matching."""
    session = _make_repo(tmp_path / "lab", "feat/work", STD_CFG)
    sibling = _make_repo(tmp_path / f"other{len(form)}", "main", STD_CFG)
    _set_alias(sibling, "ci", "commit")
    decision, _ = _run(f"{form} -C {sibling} ci -m x", session, home)
    assert decision == "deny", form


@pytest.mark.parametrize(
    "cmd",
    [
        "git-foo commit -m x",  # a different program entirely
        "gitk commit -m x",
        "/usr/bin/git-secret commit -m x",
        "mygit commit -m x",
        "gitk.exe commit -m x",
        "git-secret.exe commit -m x",
    ],
)
def test_lookalike_executables_are_not_git(cmd, tmp_path, home):
    """Basename matching must not swallow neighbouring programs."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run(cmd, repo, home)
    assert decision == "allow", cmd


# Defect 15, parsing axis: Git Bash and Windows spell it `git.exe`, and a
# case-insensitive filesystem means the spelling isn't even stable — so
# `git.exe commit` and `/mingw64/bin/git.exe push origin main` were not
# recognised as git at all.

WINDOWS_GIT_FORMS = [
    "git.exe",
    "GIT.EXE",
    "Git.exe",
    "/mingw64/bin/git.exe",
    "/c/Git/bin/git.exe",
    '"/c/Program Files/Git/bin/git.exe"',
    "env.exe VAR=x git.exe",
    "command git.exe",
]


@pytest.mark.parametrize("form", WINDOWS_GIT_FORMS)
def test_windows_git_spelling_commit_denied_on_protected(form, tmp_path, home):
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, hso = _run(f"{form} commit -m x", repo, home)
    assert decision == "deny", form
    assert "main" in hso["permissionDecisionReason"], form


@pytest.mark.parametrize("form", WINDOWS_GIT_FORMS)
def test_windows_git_spelling_commit_allowed_on_feature_branch(form, tmp_path, home):
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, _ = _run(f"{form} commit -m x", repo, home)
    assert decision == "allow", form


@pytest.mark.parametrize("form", WINDOWS_GIT_FORMS)
def test_windows_git_spelling_push_to_protected_denied(form, tmp_path, home):
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, hso = _run(f"{form} push origin main", repo, home)
    assert decision == "deny", form
    assert "main" in hso["permissionDecisionReason"], form


def test_windows_git_spelling_keeps_scoping_and_aliases(tmp_path, home):
    """`.exe` normalisation must not disturb anything downstream of it."""
    session = _make_repo(tmp_path / "lab", "feat/work", STD_CFG)
    sibling = _make_repo(tmp_path / "other", "main", STD_CFG)
    _set_alias(sibling, "ci", "commit")
    decision, _ = _run(f"git.exe -C {sibling} ci -m x", session, home)
    assert decision == "deny"

    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run("git.exe -c alias.ci=commit ci -m x", repo, home)
    assert decision == "deny"


def test_exec_dash_a_consumes_its_value(tmp_path, home):
    """`exec -a NAME CMD` runs CMD under argv[0]=NAME. So `exec -a mygit git
    commit` IS a git commit, while `exec -a git commit` runs a program called
    `commit` and is not git at all — the arity has to be modelled to tell the
    two apart."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run("exec -a mygit git commit -m x", repo, home)
    assert decision == "deny"
    decision, _ = _run("exec -a git commit -m x", repo, home)
    assert decision == "allow"


@pytest.mark.parametrize("cmd", ["command -X git commit -m x", "exec -Z git push"])
def test_unresolvable_run_wrapper_denied(cmd, tmp_path, home):
    """Same fail-closed stance as `env`: a wrapper option we do not know may
    swallow the command token, so it is guarded, not allowed."""
    for branch in ("main", "dev", "feat/x"):
        repo = _make_repo(
            tmp_path / f"{branch.replace('/', '_')}-{len(cmd)}", branch, STD_CFG
        )
        decision, hso = _run(cmd, repo, home)
        assert decision == "deny", f"{cmd} on {branch}"
        assert "invocation runs" in hso["permissionDecisionReason"], cmd


def test_unresolvable_run_wrapper_is_a_noop_without_config(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "main", None)
    decision, _ = _run("command -X git commit -m x", repo, home)
    assert decision == "allow"


@pytest.mark.parametrize(
    "cmd",
    [
        "command -v git",
        "command -v git commit",
        "command -V git commit",
        "command -v git push origin main",
    ],
)
def test_command_v_is_a_lookup_not_an_invocation(cmd, tmp_path, home):
    """Defect 32. `command -v`/`-V` only look a name up and print it — verified,
    `command -v git commit` prints `/usr/bin/git` and commits nothing. Skipping
    the flag and reading the rest as a real invocation was an over-denial."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run(cmd, repo, home)
    assert decision == "allow", cmd


def test_command_without_a_lookup_flag_still_runs_git(tmp_path, home):
    """The control: `command git commit` and `command -p git commit` really do
    execute git."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    for cmd in ("command git commit -m x", "command -p git commit -m x"):
        decision, _ = _run(cmd, repo, home)
        assert decision == "deny", cmd


def test_wrapper_options_are_per_wrapper(tmp_path, home):
    """`-c`/`-a` belong to `exec`, `-p`/`-v` to `command`; using one on the
    other is an unknown option and fails closed rather than being waved
    through."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    for cmd in ("exec -c git commit -m x", "exec -a name git commit -m x"):
        decision, _ = _run(cmd, repo, home)
        assert decision == "deny", cmd
    for cmd in ("command -c git commit -m x", "exec -v git commit -m x"):
        decision, hso = _run(cmd, repo, home)
        assert decision == "deny", cmd
        assert "invocation runs" in hso["permissionDecisionReason"], cmd


def test_builtin_cannot_run_git(tmp_path, home):
    """Defect 29. `builtin` runs ONLY shell builtins, so `builtin git commit`
    dies with "git: not a shell builtin" and git never runs — verified. The
    asymmetry with `builtin cd`, which really does move the shell, is the
    point: a wrapper belongs in a list only where it can run that command."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    for cmd in ("builtin git commit -m x", "builtin git push origin main"):
        decision, _ = _run(cmd, repo, home)
        assert decision == "allow", cmd

    # …while `builtin cd` is still followed.
    session = _make_repo(tmp_path / "lab", "feat/work", STD_CFG)
    other = _make_repo(tmp_path / "other", "main", STD_CFG)
    decision, _ = _run(f"builtin cd {other} && git commit -m x", session, home)
    assert decision == "deny"


# ─── `-c alias.<name>=…` on the command line ──────────────────
#
# Ninth shape: `_git_subcommand` parsed and discarded `-c key=val`, while
# `_expand_alias` only read repo config — so an alias defined for that one
# invocation was invisible, and the docs claimed aliases were handled.


@pytest.mark.parametrize(
    "cmd",
    [
        "git -c alias.ci=commit ci -m x",
        "git -c alias.ci='commit -s' ci -m x",
        "git -c alias.CI=commit ci -m x",  # config names are case-insensitive
        "git -c user.name=t -c alias.ci=commit ci -m x",
        "/usr/bin/git -c alias.ci=commit ci -m x",
        "env VAR=x git -c alias.ci=commit ci -m x",
    ],
)
def test_cli_alias_to_commit_denied_on_protected(cmd, tmp_path, home):
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, hso = _run(cmd, repo, home)
    assert decision == "deny", cmd
    assert "main" in hso["permissionDecisionReason"], cmd


@pytest.mark.parametrize(
    "cmd",
    [
        "git -c alias.ci=commit ci -m x",
        "git -c alias.CI=commit ci -m x",
    ],
)
def test_cli_alias_to_commit_allowed_on_feature_branch(cmd, tmp_path, home):
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, _ = _run(cmd, repo, home)
    assert decision == "allow", cmd


def test_cli_alias_to_push_resolves_its_refspec(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, hso = _run("git -c alias.pub='push origin main' pub", repo, home)
    assert decision == "deny"
    assert "main" in hso["permissionDecisionReason"]

    decision, _ = _run("git -c alias.pub='push origin feat/x' pub", repo, home)
    assert decision == "allow"


def test_cli_alias_to_push_head_follows_the_current_branch(tmp_path, home):
    for branch, expected in (("main", "deny"), ("dev", "deny"), ("feat/x", "allow")):
        repo = _make_repo(tmp_path / branch.replace("/", "_"), branch, STD_CFG)
        decision, _ = _run("git -c alias.pub='push origin HEAD' pub", repo, home)
        assert decision == expected, branch


def test_cli_alias_overrides_the_repo_alias(tmp_path, home):
    """git prefers `-c` over config, and so must the guard — in both
    directions, so the override is honoured rather than merely unioned."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    _set_alias(repo, "x", "status")  # harmless in config …
    decision, _ = _run("git -c alias.x=commit x -m y", repo, home)
    assert decision == "deny"  # … but `commit` on the command line

    repo2 = _make_repo(tmp_path / "r2", "main", STD_CFG)
    _set_alias(repo2, "x", "commit")  # guarded in config …
    decision, _ = _run("git -c alias.x=status x", repo2, home)
    assert decision == "allow"  # … but harmless on the command line


@pytest.mark.parametrize(
    "cmd",
    [
        "git -c alias.a=b a",  # alias to another alias
        "git -c alias.sh='!git push origin main' sh",  # shell alias
    ],
)
def test_unresolvable_cli_alias_denied(cmd, tmp_path, home):
    """Same one-level, non-recursive rule as repo aliases."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, hso = _run(cmd, repo, home)
    assert decision == "deny", cmd
    assert "alias" in hso["permissionDecisionReason"], cmd


def test_cli_alias_to_a_builtin_allowed(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run("git -c alias.lg='log --graph' lg", repo, home)
    assert decision == "allow"


def test_cli_alias_is_a_noop_without_config(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "main", None)
    decision, _ = _run("git -c alias.ci=commit ci -m x", repo, home)
    assert decision == "allow"


def test_non_alias_dash_c_is_not_mistaken_for_one(tmp_path, home):
    """`-c` carrying anything but an alias must not disturb parsing."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run("git -c core.hooksPath=/dev/null status", repo, home)
    assert decision == "allow"
    decision, _ = _run("git -c user.name=t commit -m x", repo, home)
    assert decision == "deny"


# ─── option arity ─────────────────────────────────────────────
#
# Shapes 6 and 7: an option whose value sits in the NEXT token shifts every
# positional after it. `git push --recurse-submodules on-demand origin` read
# `on-demand` as the remote and `origin` as an explicit harmless refspec, so a
# push of the guarded current branch looked safe; `git --namespace foo commit`
# read `foo` as the subcommand and never saw the commit. Both are ordinary
# invocation forms, so both are defects rather than tail.


@pytest.mark.parametrize(
    "cmd",
    [
        "git push --recurse-submodules on-demand origin",
        "git push --recurse-submodules check origin",
        "git push --recurse-submodules=on-demand origin",
    ],
)
def test_push_option_arity_keeps_the_current_branch_fallback(cmd, tmp_path, home):
    """With the arity known, `origin` is the remote and there is no refspec —
    so this is a push of the current branch."""
    for branch, expected in (("main", "deny"), ("dev", "deny"), ("feat/x", "allow")):
        repo = _make_repo(
            tmp_path / f"{branch.replace('/', '_')}-{len(cmd)}", branch, STD_CFG
        )
        decision, _ = _run(cmd, repo, home)
        assert decision == expected, f"{cmd} on {branch}"


def test_push_option_arity_keeps_explicit_refspecs_readable(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, hso = _run(
        "git push --recurse-submodules on-demand origin main", repo, home
    )
    assert decision == "deny"
    assert "main" in hso["permissionDecisionReason"]

    decision, _ = _run(
        "git push --recurse-submodules on-demand origin feat/x", repo, home
    )
    assert decision == "allow"


@pytest.mark.parametrize(
    "cmd",
    [
        "git --namespace foo commit -m x",
        "git --namespace=foo commit -m x",
        "git --attr-source HEAD commit -m x",
        "git --config-env=user.name=N commit -m x",
    ],
)
def test_global_option_arity_still_finds_the_subcommand(cmd, tmp_path, home):
    for branch, expected in (("main", "deny"), ("feat/x", "allow")):
        repo = _make_repo(
            tmp_path / f"{branch.replace('/', '_')}-{len(cmd)}", branch, STD_CFG
        )
        decision, _ = _run(cmd, repo, home)
        assert decision == expected, f"{cmd} on {branch}"


@pytest.mark.parametrize(
    "cmd",
    [
        "git --literal-pathspecs commit -m x",
        "git --no-optional-locks commit -m x",
        "git -p commit -m x",
        "git --bare commit -m x",
    ],
)
def test_value_less_globals_do_not_shift_the_subcommand(cmd, tmp_path, home):
    """A global we do not model but that takes NO value must still land on the
    real subcommand — the unknown-arity backstop must not fire here."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, hso = _run(cmd, repo, home)
    assert decision == "deny", cmd
    assert "protected branch 'main'" in hso["permissionDecisionReason"], cmd


@pytest.mark.parametrize(
    "cmd", ["git --literal-pathspecs status", "git -p log", "git --no-advice diff"]
)
def test_value_less_globals_before_harmless_builtins_allowed(cmd, tmp_path, home):
    """The backstop only fires on an UNIDENTIFIABLE subcommand, so ordinary
    read-only traffic behind an unmodelled global is untouched."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run(cmd, repo, home)
    assert decision == "allow", cmd


def test_unknown_global_hiding_the_subcommand_is_denied(tmp_path, home):
    """The backstop: a global whose arity we do not know may have eaten a token
    we then read as the subcommand. Only fires when that token is neither a
    builtin nor an alias — i.e. when we already know we are lost."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, hso = _run("git --future-option value commit -m x", repo, home)
    assert decision == "deny"
    assert "unknown arity" in hso["permissionDecisionReason"]


def test_unknown_global_backstop_is_a_noop_without_config(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "main", None)
    decision, _ = _run("git --future-option value commit -m x", repo, home)
    assert decision == "allow"


def test_unknown_subcommand_alone_is_still_allowed(tmp_path, home):
    """No unknown global in play -> an unrecognised word is just a typo git
    itself will reject, and must not be denied."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run("git nosuchthing --flag", repo, home)
    assert decision == "allow"


# ─── the environment axis ─────────────────────────────────────
#
# Defects 10 and 11, and the first two found on an axis other than parsing.
# Neither is about how the command is WRITTEN — `git commit -m x` parses
# perfectly in both — but about whether the guard's model of the world matches
# the shell's and git's. Both ended with the guard evaluating a different repo
# than git was about to write to, and allowing a direct commit on `main`.


@pytest.mark.parametrize("sep", [";", "||"])
def test_failing_cd_leaves_the_guard_where_the_shell_stays(sep, tmp_path, home):
    """A `cd` to a directory that does not exist FAILS, so the shell never
    moves and the commit runs in the original — protected — repo. Following the
    dead path landed the guard in a non-repo, which it read as "nothing to
    guard". Checking that the directory exists is the shell's semantics, which
    is why `;` and `||` both come out right with no separator modelling.

    `&&` is NOT in this list any more: bash short-circuits past the commit
    entirely, so there is nothing to block. It used to be a deliberate
    over-deny; defect 25 made the short-circuit explicit and the over-deny
    went away with it — see the test below.
    """
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, hso = _run(f"cd /does/not/exist {sep} git commit -m x", repo, home)
    assert decision == "deny", sep
    assert "main" in hso["permissionDecisionReason"], sep


def test_failing_cd_does_not_manufacture_a_denial_on_a_feature_branch(tmp_path, home):
    """The control: staying put must mean staying put, not denying blindly."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, _ = _run("cd /does/not/exist ; git commit -m x", repo, home)
    assert decision == "allow"


def test_successful_cd_is_still_followed(tmp_path, home):
    """The control that already passed and must keep passing: a `cd` to a real
    directory moves the shell, so the guard has to move with it."""
    session = _make_repo(tmp_path / "lab", "main", STD_CFG)
    sibling = _make_repo(tmp_path / "datasets", "feat/data", STD_CFG)
    decision, _ = _run(f"cd {sibling} && git commit -m x", session, home)
    assert decision == "allow"

    session2 = _make_repo(tmp_path / "lab2", "feat/work", STD_CFG)
    sibling2 = _make_repo(tmp_path / "other2", "main", STD_CFG)
    decision, hso = _run(f"cd {sibling2} && git commit -m x", session2, home)
    assert decision == "deny"
    assert "main" in hso["permissionDecisionReason"]


def test_relative_cd_that_exists_is_followed(tmp_path, home):
    session = _make_repo(tmp_path / "lab", "main", STD_CFG)
    _make_repo(tmp_path / "lab" / "nested", "feat/x", STD_CFG)
    decision, _ = _run("cd nested && git commit -m x", session, home)
    assert decision == "allow"


def test_relative_cd_that_does_not_exist_is_not_followed(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run("cd nope ; git commit -m x", repo, home)
    assert decision == "deny"


# Defect 16, environment axis: a `cd` operand we never expanded is neither
# "resolved" nor "failed" — it is UNKNOWN. Treating it as a failed `cd` meant
# that from an unguarded repo the guard kept evaluating THIS repo while bash
# expanded the variable and committed somewhere else entirely.

UNEXPANDABLE_CD = [
    'cd "$MAIN_REPO"',
    "cd $MAIN_REPO",
    "cd ${MAIN_REPO}",
    "cd $(cat path.txt)",
    "cd `cat path.txt`",
    "cd repo-*",
    "cd ../repo?",
    "cd ~nosuchuser/x",
]


@pytest.mark.parametrize("cd", UNEXPANDABLE_CD)
@pytest.mark.parametrize("branch", ["main", "dev", "feat/x"])
def test_unexpandable_cd_fails_closed_for_guarded_verbs(cd, branch, tmp_path, home):
    """Denied from EVERY branch, including a feature branch: the point is that
    we do not know which repo the commit lands in."""
    repo = _make_repo(tmp_path / branch.replace("/", "_"), branch, STD_CFG)
    decision, hso = _run(f"{cd} && git commit -m x", repo, home)
    assert decision == "deny", f"{cd} on {branch}"
    assert "cannot determine which repo" in hso["permissionDecisionReason"], cd


@pytest.mark.parametrize("cd", UNEXPANDABLE_CD)
def test_unexpandable_cd_does_not_block_read_only_git(cd, tmp_path, home):
    """Only the guarded verbs fail closed — an unknown cwd is no reason to
    refuse `git status`."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run(f"{cd} && git status", repo, home)
    assert decision == "allow", cd


def test_unexpandable_cd_is_a_noop_without_config(tmp_path, home):
    """A DOCUMENTED LIMIT, not an oversight: the fail-closed deny is gated on
    the last known directory being opted in, so starting from a repo that never
    opted in this stays a no-op — even though `$MAIN_REPO` might expand into a
    guarded repo. Closing it would mean denying on every unexpandable `cd` in
    every repo on the machine, which ends the opt-in contract that keeps this
    hook out of scratch repos and third-party clones. See the module
    docstring's structural limits; `pre-push` is installed in the guarded repo
    and so is reached by definition."""
    repo = _make_repo(tmp_path / "r", "main", None)
    decision, _ = _run('cd "$MAIN_REPO" && git commit -m x', repo, home)
    assert decision == "allow"


def test_unexpandable_cd_is_escaped_by_an_absolute_scoping_option(tmp_path, home):
    """If the git command pins its own repo absolutely, the unknown cwd is
    irrelevant and must not manufacture a denial."""
    session = _make_repo(tmp_path / "lab", "main", STD_CFG)
    other = _make_repo(tmp_path / "other", "feat/data", STD_CFG)
    decision, _ = _run(f'cd "$D" && git -C {other} commit -m x', session, home)
    assert decision == "allow"

    on_main = _make_repo(tmp_path / "onmain", "main", STD_CFG)
    decision, _ = _run(f'cd "$D" && git -C {on_main} commit -m x', session, home)
    assert decision == "deny"


# Defect 22, environment axis: the same unexpanded-operand failure as 16, one
# operand over. `git -C "$MAIN_REPO" commit` was read as a LITERAL directory
# called `$MAIN_REPO`, found not to be a repo, and allowed — while bash
# expanded the variable and git committed in the guarded repo it named.

UNEXPANDABLE_SCOPING = [
    'git -C "$MAIN_REPO"',
    "git -C $MAIN_REPO",
    "git -C ${MAIN_REPO}",
    "git -C $(cat path.txt)",
    "git -C repo-*",
    'git --git-dir="$MAIN_REPO/.git"',
    "git --git-dir $MAIN_REPO/.git",
    'git --work-tree=/tmp --git-dir="$D/.git"',
    'env -C "$MAIN_REPO" git',
    "git -C ~nosuchuser/x",
]


@pytest.mark.parametrize("prefix", UNEXPANDABLE_SCOPING)
@pytest.mark.parametrize("branch", ["main", "feat/x"])
def test_unexpandable_scoping_operand_fails_closed(prefix, branch, tmp_path, home):
    """Denied from every branch — the point is that the target repo is
    unknowable, not that this one is guarded."""
    repo = _make_repo(tmp_path / branch.replace("/", "_"), branch, STD_CFG)
    decision, hso = _run(f"{prefix} commit -m x", repo, home)
    assert decision == "deny", f"{prefix} on {branch}"
    assert "cannot determine which repo" in hso["permissionDecisionReason"], prefix


@pytest.mark.parametrize("prefix", UNEXPANDABLE_SCOPING)
def test_unexpandable_scoping_operand_allows_read_only_git(prefix, tmp_path, home):
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run(f"{prefix} status", repo, home)
    assert decision == "allow", prefix


def test_unexpandable_scoping_operand_is_a_noop_without_config(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "main", None)
    decision, _ = _run('git -C "$MAIN_REPO" commit -m x', repo, home)
    assert decision == "allow"


def test_a_later_absolute_scoping_operand_re_anchors_the_target(tmp_path, home):
    """An absolute literal operand pins the repo no matter what came before, so
    it must clear the unknown rather than be swamped by it."""
    session = _make_repo(tmp_path / "lab", "main", STD_CFG)
    other = _make_repo(tmp_path / "other", "feat/data", STD_CFG)
    decision, _ = _run(f'git -C "$D" -C {other} commit -m x', session, home)
    assert decision == "allow"

    on_main = _make_repo(tmp_path / "onmain", "main", STD_CFG)
    decision, _ = _run(f'git -C "$D" -C {on_main} commit -m x', session, home)
    assert decision == "deny"

    decision, _ = _run(f'git -C "$D" --git-dir={other}/.git commit -m x', session, home)
    assert decision == "allow"


def test_literal_scoping_operands_are_unaffected(tmp_path, home):
    """The control: a `-C` that holds no expansion still resolves exactly as
    before, including a relative one that is not a repo."""
    session = _make_repo(tmp_path / "lab", "feat/work", STD_CFG)
    other = _make_repo(tmp_path / "other", "main", STD_CFG)
    decision, _ = _run(f"git -C {other} commit -m x", session, home)
    assert decision == "deny"
    decision, _ = _run("git -C nowhere commit -m x", session, home)
    assert decision == "allow"


def test_unknown_cwd_is_sticky_until_an_absolute_cd(tmp_path, home):
    session = _make_repo(tmp_path / "lab", "main", STD_CFG)
    other = _make_repo(tmp_path / "other", "feat/data", STD_CFG)
    # A relative cd from an unknown location is still unknown.
    decision, _ = _run('cd "$D" ; cd sub ; git commit -m x', session, home)
    assert decision == "deny"
    # An absolute cd re-anchors us, so we know again.
    decision, _ = _run(f'cd "$D" ; cd {other} ; git commit -m x', session, home)
    assert decision == "allow"


def test_an_absolute_cd_gated_on_an_unknown_status_keeps_both_places(tmp_path, home):
    """With `&&` rather than `;`, the re-anchoring `cd` only runs if the first
    one succeeded — which we cannot know. One of the two possible locations is
    unknowable, so the guarded verb fails closed."""
    session = _make_repo(tmp_path / "lab", "main", STD_CFG)
    other = _make_repo(tmp_path / "other", "feat/data", STD_CFG)
    decision, hso = _run(f'cd "$D" && cd {other} && git commit -m x', session, home)
    assert decision == "deny"
    assert "cannot determine which repo" in hso["permissionDecisionReason"]


def test_unknown_cwd_dies_with_the_subshell(tmp_path, home):
    """`(cd "$D" && …)` leaves the outer shell where it was, so a command after
    the `)` is knowable again."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, _ = _run('(cd "$D" && git status) && git commit -m x', repo, home)
    assert decision == "allow"


def test_tilde_is_expanded_rather_than_called_unknown(tmp_path, home):
    """`cd ~/proj` is extremely ordinary and the expansion is deterministic, so
    it must resolve rather than fail closed."""
    fake_home = tmp_path / "home2"
    _make_repo(fake_home / "proj", "feat/x", STD_CFG)
    session = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run(
        "cd ~/proj && git commit -m x",
        session,
        home,
        extra_env={"HOME": str(fake_home)},
    )
    assert decision == "allow"


def test_bare_cd_goes_home(tmp_path, home):
    fake_home = tmp_path / "home2"
    _make_repo(fake_home, "feat/x", STD_CFG)
    session = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run(
        "cd && git commit -m x", session, home, extra_env={"HOME": str(fake_home)}
    )
    assert decision == "allow"


def test_cd_dash_returns_to_the_previous_directory(tmp_path, home):
    """`cd -` goes back, so a commit after it lands in the ORIGINAL repo."""
    session = _make_repo(tmp_path / "lab", "main", STD_CFG)
    other = _make_repo(tmp_path / "other", "feat/data", STD_CFG)
    decision, hso = _run(f"cd {other} && cd - && git commit -m x", session, home)
    assert decision == "deny"
    assert "main" in hso["permissionDecisionReason"]


def test_cd_dash_without_a_known_previous_directory_fails_closed(tmp_path, home):
    """With no `cd` seen first, `$OLDPWD` is the shell's, which we never saw."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, hso = _run("cd - && git commit -m x", repo, home)
    assert decision == "deny"
    assert "cannot determine which repo" in hso["permissionDecisionReason"]


# Defect 26, environment axis: a `cd` can hide behind an assignment prefix or
# a `command`/`builtin` wrapper and still move the shell. Verified in bash —
# `FOO=1 cd sub`, `command cd sub` and `builtin cd sub` all end up in `sub`,
# while `env cd sub` and `exec cd sub` FAIL (no `cd` binary exists) and move
# nothing, so those two must not be stripped.


@pytest.mark.parametrize(
    "prefix", ["FOO=1", "FOO=1 BAR=2", "command", "builtin", "FOO=1 command"]
)
def test_a_wrapped_cd_still_moves_the_guard(prefix, tmp_path, home):
    session = _make_repo(tmp_path / "lab", "feat/work", STD_CFG)
    other = _make_repo(tmp_path / f"other{len(prefix)}", "main", STD_CFG)
    decision, hso = _run(f"{prefix} cd {other} && git commit -m x", session, home)
    assert decision == "deny", prefix
    assert "main" in hso["permissionDecisionReason"], prefix


@pytest.mark.parametrize("prefix", ["FOO=1", "command", "builtin"])
def test_a_wrapped_cd_does_not_manufacture_a_denial(prefix, tmp_path, home):
    session = _make_repo(tmp_path / "lab", "main", STD_CFG)
    other = _make_repo(tmp_path / f"other{len(prefix)}", "feat/data", STD_CFG)
    decision, _ = _run(f"{prefix} cd {other} && git commit -m x", session, home)
    assert decision == "allow", prefix


@pytest.mark.parametrize("prefix", ["env", "exec"])
def test_env_and_exec_cannot_run_cd_so_the_shell_stays(prefix, tmp_path, home):
    """`env cd sub` and `exec cd sub` look up an external `cd` that does not
    exist — they fail and move nothing, so the commit stays in this repo."""
    session = _make_repo(tmp_path / "lab", "main", STD_CFG)
    other = _make_repo(tmp_path / f"other{len(prefix)}", "feat/data", STD_CFG)
    decision, hso = _run(f"{prefix} cd {other} ; git commit -m x", session, home)
    assert decision == "deny", prefix
    assert "main" in hso["permissionDecisionReason"], prefix


def test_cd_options_do_not_hide_the_target(tmp_path, home):
    """`cd -P <path>` is the same `cd` — the flag must not be read as the
    operand, or the directory change would be missed entirely."""
    session = _make_repo(tmp_path / "lab", "feat/work", STD_CFG)
    other = _make_repo(tmp_path / "other", "main", STD_CFG)
    for flag in ("-P", "-L", "--"):
        decision, _ = _run(f"cd {flag} {other} && git commit -m x", session, home)
        assert decision == "deny", flag


def test_work_tree_alone_does_not_move_the_repo(tmp_path, home):
    """Git identifies a repo by its GIT DIR. With `--work-tree` and no
    `--git-dir` it still discovers `.git` upward from the current directory, so
    `git --work-tree ../scratch commit` commits HERE — on the protected branch
    — using `../scratch`'s files."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    scratch = _make_repo(tmp_path / "scratch", "feat/data", STD_CFG)
    for spelling in (f"--work-tree {scratch}", f"--work-tree={scratch}"):
        decision, hso = _run(f"git {spelling} commit -m x", repo, home)
        assert decision == "deny", spelling
        assert "main" in hso["permissionDecisionReason"], spelling


def test_work_tree_alone_from_a_feature_branch_is_allowed(tmp_path, home):
    """Mirror image: the repo we are standing in is what counts, so an
    unguarded branch here stays allowed even when the work tree is a repo
    sitting on `main`."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    other = _make_repo(tmp_path / "other", "main", STD_CFG)
    decision, _ = _run(f"git --work-tree {other} commit -m x", repo, home)
    assert decision == "allow"


def test_work_tree_alone_does_not_consume_the_subcommand(tmp_path, home):
    """`--work-tree` is still parsed as taking a value — dropping it from repo
    identity must not drop it from the arity table."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    other = _make_repo(tmp_path / "other", "feat/x", STD_CFG)
    decision, _ = _run(f"git --work-tree {other} status", repo, home)
    assert decision == "allow"
    decision, _ = _run(f"git --work-tree {other} push origin main", repo, home)
    assert decision == "deny"


def test_git_dir_with_work_tree_targets_the_git_dirs_repo(tmp_path, home):
    """When both are given the repo genuinely IS the other one — `--git-dir`
    names it, and that is what the guard must evaluate."""
    session = _make_repo(tmp_path / "lab", "feat/work", STD_CFG)
    other = _make_repo(tmp_path / "other", "main", STD_CFG)
    decision, hso = _run(
        f"git --git-dir={other}/.git --work-tree={other} commit -m x", session, home
    )
    assert decision == "deny"
    assert "main" in hso["permissionDecisionReason"]

    # And the mirror: session on `main`, the named repo on a feature branch.
    session2 = _make_repo(tmp_path / "lab2", "main", STD_CFG)
    other2 = _make_repo(tmp_path / "other2", "feat/data", STD_CFG)
    decision, _ = _run(
        f"git --git-dir={other2}/.git --work-tree={other2} commit -m x", session2, home
    )
    assert decision == "allow"


def test_dash_c_alone_selects_the_repo(tmp_path, home):
    session = _make_repo(tmp_path / "lab", "feat/work", STD_CFG)
    other = _make_repo(tmp_path / "other", "main", STD_CFG)
    decision, _ = _run(f"git -C {other} commit -m x", session, home)
    assert decision == "deny"


# ─── `-C` and `--git-dir` compose ─────────────────────────────
#
# Defect 13, environment axis. `-C` was treated as OVERRIDING `--git-dir`, but
# git applies `-C` to the process cwd and still lets `--git-dir` choose the
# repository — so `git -C ../feature --git-dir=<on-main>/.git commit` was
# evaluated against `../feature` while git committed to the repo on `main`.


@pytest.mark.parametrize("order", ["-C {c} --git-dir={g}", "--git-dir={g} -C {c}"])
def test_git_dir_wins_over_dash_c_for_repo_identity(order, tmp_path, home):
    """Git applies `-C` first whatever the order on the command line, then
    `--git-dir` names the repo."""
    session = _make_repo(tmp_path / "lab", "feat/work", STD_CFG)
    feature = _make_repo(tmp_path / "feature", "feat/x", STD_CFG)
    on_main = _make_repo(tmp_path / "onmain", "main", STD_CFG)
    cmd = "git " + order.format(c=feature, g=f"{on_main}/.git") + " commit -m x"
    decision, hso = _run(cmd, session, home)
    assert decision == "deny", cmd
    assert "main" in hso["permissionDecisionReason"], cmd


def test_git_dir_wins_over_dash_c_in_the_safe_direction_too(tmp_path, home):
    """The mirror: `-C` points at a repo on `main`, but `--git-dir` names an
    unguarded one — git commits there, so this must be allowed."""
    session = _make_repo(tmp_path / "lab", "main", STD_CFG)
    on_main = _make_repo(tmp_path / "onmain", "main", STD_CFG)
    feature = _make_repo(tmp_path / "feature", "feat/x", STD_CFG)
    decision, _ = _run(
        f"git -C {on_main} --git-dir={feature}/.git commit -m x", session, home
    )
    assert decision == "allow"


def test_relative_git_dir_resolves_against_the_dash_c_directory(tmp_path, home):
    """A relative `--git-dir` is interpreted relative to the directory `-C`
    produced, not to the session's cwd."""
    session = _make_repo(tmp_path / "lab", "feat/work", STD_CFG)
    outer = _make_repo(tmp_path / "outer", "feat/x", STD_CFG)
    _make_repo(tmp_path / "outer" / "nested", "main", STD_CFG)
    decision, hso = _run(
        f"git -C {outer} --git-dir=nested/.git commit -m x", session, home
    )
    assert decision == "deny"
    assert "main" in hso["permissionDecisionReason"]


def test_cumulative_dash_c_then_relative_git_dir(tmp_path, home):
    session = _make_repo(tmp_path / "lab", "feat/work", STD_CFG)
    _make_repo(tmp_path / "a", "feat/a", STD_CFG)
    _make_repo(tmp_path / "a" / "b", "feat/b", STD_CFG)
    _make_repo(tmp_path / "a" / "b" / "c", "main", STD_CFG)
    decision, _ = _run(
        f"git -C {tmp_path / 'a'} -C b --git-dir=c/.git commit -m x", session, home
    )
    assert decision == "deny"


def test_dash_c_with_work_tree_only_still_uses_the_dash_c_repo(tmp_path, home):
    """`--work-tree` names no repo, so with `-C` present the `-C` directory is
    still what git discovers `.git` from."""
    session = _make_repo(tmp_path / "lab", "feat/work", STD_CFG)
    on_main = _make_repo(tmp_path / "onmain", "main", STD_CFG)
    scratch = _make_repo(tmp_path / "scratch", "feat/x", STD_CFG)
    decision, _ = _run(
        f"git -C {on_main} --work-tree={scratch} commit -m x", session, home
    )
    assert decision == "deny"


# ─── subshells scope the working directory ────────────────────
#
# Defect 12, environment axis again. The old regex split dropped `(` and `)`
# entirely, so `(cd ../other && git commit)` was evaluated against the ORIGINAL
# repo — and a naive fix that merely stripped the parens would have made the
# opposite error, leaking the subshell's `cd` onto every later command. Both
# directions are pinned here.


def test_subshell_cd_scopes_the_commit_to_the_inner_repo(tmp_path, home):
    session = _make_repo(tmp_path / "lab", "feat/work", STD_CFG)
    other = _make_repo(tmp_path / "other", "main", STD_CFG)
    decision, hso = _run(f"(cd {other} && git commit -m x)", session, home)
    assert decision == "deny"
    assert "main" in hso["permissionDecisionReason"]


def test_subshell_cd_to_an_unguarded_repo_is_allowed(tmp_path, home):
    session = _make_repo(tmp_path / "lab", "main", STD_CFG)
    other = _make_repo(tmp_path / "other", "feat/data", STD_CFG)
    decision, _ = _run(f"(cd {other} && git commit -m x)", session, home)
    assert decision == "allow"


def test_subshell_cd_does_not_leak_past_the_closing_paren(tmp_path, home):
    """The other half: after `)` the shell is back where it started, so a later
    command must be evaluated against the ORIGINAL repo."""
    session = _make_repo(tmp_path / "lab", "main", STD_CFG)
    other = _make_repo(tmp_path / "other", "feat/data", STD_CFG)
    decision, hso = _run(
        f"(cd {other} && git status) && git commit -m x", session, home
    )
    assert decision == "deny"
    assert "main" in hso["permissionDecisionReason"]


def test_subshell_push_refspec_is_not_mangled_by_the_paren(tmp_path, home):
    """`(… git push origin main)` — the `)` must not end up glued to the
    refspec, or `main)` would never match the guarded branch."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, hso = _run(f"(cd {repo} && git push origin main)", repo, home)
    assert decision == "deny"
    assert "main" in hso["permissionDecisionReason"]


def test_nested_subshells_restore_one_level_at_a_time(tmp_path, home):
    outer = _make_repo(tmp_path / "outer", "main", STD_CFG)
    mid = _make_repo(tmp_path / "mid", "feat/mid", STD_CFG)
    inner = _make_repo(tmp_path / "inner", "dev", STD_CFG)
    decision, hso = _run(f"(cd {mid} && (cd {inner} && git commit -m x))", outer, home)
    assert decision == "deny"
    assert "dev" in hso["permissionDecisionReason"]

    # Back out of the inner subshell only: `mid` is unguarded, so allowed.
    decision, _ = _run(
        f"(cd {mid} && (cd {inner} && git status) && git commit -m x)", outer, home
    )
    assert decision == "allow"


def test_subshell_cd_to_a_missing_directory_still_stays_put(tmp_path, home):
    """Both environment fixes at once: the `cd` fails, so the subshell runs the
    commit in the original repo."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run("(cd /does/not/exist ; git commit -m x)", repo, home)
    assert decision == "deny"


def test_brace_group_cd_still_applies_afterwards(tmp_path, home):
    """A brace group runs in the CURRENT shell, so unlike a subshell its `cd`
    persists — and the `{`/`}` tokens must not hide the commands."""
    session = _make_repo(tmp_path / "lab", "feat/work", STD_CFG)
    other = _make_repo(tmp_path / "other", "main", STD_CFG)
    decision, hso = _run(f"{{ cd {other}; git commit -m x; }}", session, home)
    assert decision == "deny"
    assert "main" in hso["permissionDecisionReason"]

    session2 = _make_repo(tmp_path / "lab2", "feat/work", STD_CFG)
    other2 = _make_repo(tmp_path / "other2", "main", STD_CFG)
    decision, _ = _run(
        f"{{ cd {other2}; git status; }}; git commit -m x", session2, home
    )
    assert decision == "deny", "a brace-group cd persists after the group"


@pytest.mark.parametrize(
    "cmd",
    [
        'git commit -m "done)"',
        "git commit -m 'wrap (up)'",
        'git commit -m "a ; b && c"',
    ],
)
def test_parens_and_separators_inside_quotes_are_text(cmd, tmp_path, home):
    """The scan is quote-aware: punctuation inside a commit message is not
    shell syntax, and must neither split the command nor pop a scope."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run(cmd, repo, home)
    assert decision == "deny", cmd

    repo2 = _make_repo(tmp_path / "r2", "feat/x", STD_CFG)
    decision, _ = _run(cmd, repo2, home)
    assert decision == "allow", cmd


def test_unmatched_closing_paren_is_harmless(tmp_path, home):
    """A `case` arm's `)` has no scope to restore and must not disturb the
    command that follows."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run("case $x in a) echo hi;; esac; git commit -m x", repo, home)
    assert decision == "deny"


# Defect 18, environment axis: bash runs every pipeline element, and any
# command ended by `&`, in its own process — verified, `cd sub | pwd` and
# `cd sub & wait; pwd` both print the ORIGINAL directory while `cd sub && pwd`
# prints `sub`. Treating `|` like `;` let a `cd` leak across a boundary the
# shell never crosses.


@pytest.mark.parametrize("sep", ["|", "|&", "&"])
def test_cd_does_not_cross_a_subshell_separator(sep, tmp_path, home):
    """The commit runs in the ORIGINAL repo, so a guarded branch there is
    caught even though the `cd` names an unguarded repo."""
    session = _make_repo(tmp_path / "lab", "main", STD_CFG)
    other = _make_repo(tmp_path / "other", "feat/data", STD_CFG)
    decision, hso = _run(f"cd {other} {sep} git commit -m x", session, home)
    assert decision == "deny", sep
    assert "main" in hso["permissionDecisionReason"], sep


@pytest.mark.parametrize("sep", ["|", "&"])
def test_subshell_separator_does_not_manufacture_a_denial(sep, tmp_path, home):
    """Mirror: staying put must mean staying put, not denying blindly."""
    session = _make_repo(tmp_path / "lab", "feat/work", STD_CFG)
    other = _make_repo(tmp_path / "other", "main", STD_CFG)
    decision, _ = _run(f"cd {other} {sep} git commit -m x", session, home)
    assert decision == "allow", sep


def test_cd_in_a_later_pipeline_element_also_dies(tmp_path, home):
    """The LAST element of a pipeline is a subshell too, so its `cd` must not
    reach a command after the pipeline ends."""
    session = _make_repo(tmp_path / "lab", "main", STD_CFG)
    other = _make_repo(tmp_path / "other", "feat/data", STD_CFG)
    decision, hso = _run(f"echo hi | cd {other} ; git commit -m x", session, home)
    assert decision == "deny"
    assert "main" in hso["permissionDecisionReason"]


@pytest.mark.parametrize("sep", [";", "&&"])
def test_cd_still_propagates_across_non_subshell_separators(sep, tmp_path, home):
    """`;`, `&&` and `||` keep the shell in one process — the control that
    must not regress. (`||` is excluded because a SUCCEEDING `cd` makes bash
    skip what follows it; that is defect 25's territory, tested below.)"""
    session = _make_repo(tmp_path / "lab", "feat/work", STD_CFG)
    other = _make_repo(tmp_path / f"other{len(sep)}", "main", STD_CFG)
    decision, _ = _run(f"cd {other} {sep} git commit -m x", session, home)
    assert decision == "deny", sep


# ─── `&&` / `||` short-circuit ────────────────────────────────
#
# Defect 25, environment axis. A `cd` is the one command whose exit status the
# guard can compute, and bash uses that status to decide whether the NEXT
# command runs at all. Applying a skipped `cd` moved the guard somewhere the
# shell never went. All four behaviours below were verified against bash first.


def test_a_skipped_cd_does_not_move_the_guard(tmp_path, home):
    """The reported shape: the first `cd` fails, so bash never runs the second
    — and the commit happens in the ORIGINAL, guarded repo."""
    session = _make_repo(tmp_path / "lab", "main", STD_CFG)
    other = _make_repo(tmp_path / "other", "feat/data", STD_CFG)
    decision, hso = _run(
        f"cd /does/not/exist && cd {other} ; git commit -m x", session, home
    )
    assert decision == "deny"
    assert "main" in hso["permissionDecisionReason"]


def test_a_failed_cd_short_circuits_the_commit_itself(tmp_path, home):
    """`cd /gone && git commit` never reaches the commit, so there is nothing
    to block — the over-deny this used to produce is gone."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run("cd /does/not/exist && git commit -m x", repo, home)
    assert decision == "allow"


def test_a_succeeding_cd_short_circuits_an_or(tmp_path, home):
    """`cd <exists> || git commit` skips the commit."""
    session = _make_repo(tmp_path / "lab", "main", STD_CFG)
    other = _make_repo(tmp_path / "other", "feat/data", STD_CFG)
    decision, _ = _run(f"cd {other} || git commit -m x", session, home)
    assert decision == "allow"


def test_a_failed_cd_lets_an_or_branch_run(tmp_path, home):
    """The mirror: `cd /gone || cd <other>` DOES run the second `cd`."""
    session = _make_repo(tmp_path / "lab", "feat/work", STD_CFG)
    other = _make_repo(tmp_path / "other", "main", STD_CFG)
    decision, hso = _run(
        f"cd /does/not/exist || cd {other} ; git commit -m x", session, home
    )
    assert decision == "deny"
    assert "main" in hso["permissionDecisionReason"]


def test_short_circuit_propagates_along_an_and_chain(tmp_path, home):
    """`a && b && c` skips BOTH b and c when a fails."""
    session = _make_repo(tmp_path / "lab", "main", STD_CFG)
    other = _make_repo(tmp_path / "other", "feat/data", STD_CFG)
    decision, _ = _run(
        f"cd /does/not/exist && cd {other} && git commit -m x", session, home
    )
    assert decision == "allow", "the commit is skipped too"


def test_short_circuit_still_reaches_an_or_after_a_skipped_and(tmp_path, home):
    """`a && b || c` runs c when a fails — the status carries through the
    skipped b rather than being reset."""
    session = _make_repo(tmp_path / "lab", "feat/work", STD_CFG)
    other = _make_repo(tmp_path / "other", "main", STD_CFG)
    decision, _ = _run(
        f"cd /does/not/exist && cd /also/gone || cd {other} ; git commit -m x",
        session,
        home,
    )
    assert decision == "deny"


def test_a_skipped_subshell_is_not_entered(tmp_path, home):
    """`cd /gone && ( … )` skips the whole group — verified in bash."""
    session = _make_repo(tmp_path / "lab", "main", STD_CFG)
    other = _make_repo(tmp_path / "other", "feat/data", STD_CFG)
    decision, _ = _run(
        f"cd /does/not/exist && (cd {other} && git commit -m x)", session, home
    )
    assert decision == "allow", "nothing in the subshell runs"

    # And the commit after it is back in the original repo.
    decision, hso = _run(
        f"cd /does/not/exist && (cd {other} && git status) ; git commit -m x",
        session,
        home,
    )
    assert decision == "deny"
    assert "main" in hso["permissionDecisionReason"]


def test_a_cd_gated_on_an_unknown_status_is_checked_both_ways(tmp_path, home):
    """Defect 33. `test -d /missing && cd ../feature ; git commit` — bash
    skips the `cd`, so the commit lands on the guarded branch, but "might run"
    was treated as "did run" and the guard moved to `../feature`. Both
    candidate directories are now checked, and the guarded one denies."""
    session = _make_repo(tmp_path / "lab", "main", STD_CFG)
    other = _make_repo(tmp_path / "other", "feat/data", STD_CFG)
    decision, hso = _run(
        f"test -d /missing && cd {other} ; git commit -m x", session, home
    )
    assert decision == "deny"
    assert "main" in hso["permissionDecisionReason"]


def test_the_other_candidate_is_checked_too(tmp_path, home):
    """Mirror: the repo we might have moved INTO is guarded, and that must
    deny even though the one we started in is not."""
    session = _make_repo(tmp_path / "lab", "feat/work", STD_CFG)
    other = _make_repo(tmp_path / "other", "main", STD_CFG)
    decision, hso = _run(f"test -d /x && cd {other} ; git commit -m x", session, home)
    assert decision == "deny"
    assert "main" in hso["permissionDecisionReason"]


def test_a_conditional_cd_does_not_deny_when_no_candidate_is_guarded(tmp_path, home):
    """The reason this is checked per-candidate rather than failed closed:
    when neither possibility is guarded there is nothing to report."""
    session = _make_repo(tmp_path / "lab", "feat/work", STD_CFG)
    other = _make_repo(tmp_path / "other", "feat/data", STD_CFG)
    decision, _ = _run(f"test -d /x && cd {other} ; git commit -m x", session, home)
    assert decision == "allow"


def test_a_conditional_cd_within_one_repo_is_not_noise(tmp_path, home):
    """The common shape — `git add -A && cd subdir && git commit` — has both
    candidates inside the SAME repo, so a blanket fail-closed would have been
    pure noise. On a feature branch it stays allowed."""
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    (repo / "subdir").mkdir()
    decision, _ = _run("git add -A && cd subdir && git commit -m x", repo, home)
    assert decision == "allow"

    guarded = _make_repo(tmp_path / "g", "main", STD_CFG)
    (guarded / "subdir").mkdir()
    decision, _ = _run("git add -A && cd subdir && git commit -m x", guarded, home)
    assert decision == "deny", "…and on a guarded branch both candidates deny"


def test_a_certain_cd_replaces_rather_than_adds(tmp_path, home):
    """After `;` the `cd` definitely ran, so the old location is NOT a
    candidate any more — otherwise every chain would accumulate ghosts."""
    session = _make_repo(tmp_path / "lab", "main", STD_CFG)
    other = _make_repo(tmp_path / "other", "feat/data", STD_CFG)
    decision, _ = _run(f"cd {other} ; git commit -m x", session, home)
    assert decision == "allow"


def test_an_unknown_status_leaves_both_branches_live(tmp_path, home):
    """A `cd` we could not resolve, or any non-`cd` command, has an unknown
    status — so the guard must keep evaluating what follows rather than
    assuming it is skipped."""
    session = _make_repo(tmp_path / "lab", "feat/work", STD_CFG)
    other = _make_repo(tmp_path / "other", "main", STD_CFG)
    decision, _ = _run(f"git add -A && cd {other} && git commit -m x", session, home)
    assert decision == "deny"

    decision, _ = _run(f'cd "$D" || cd {other} ; git commit -m x', session, home)
    assert decision == "deny"


def test_pipeline_inside_a_chain_only_rolls_back_its_own_elements(tmp_path, home):
    """A `cd` before the pipeline still applies after it."""
    session = _make_repo(tmp_path / "lab", "feat/work", STD_CFG)
    other = _make_repo(tmp_path / "other", "main", STD_CFG)
    decision, hso = _run(
        f"cd {other} && git status | cat && git commit -m x", session, home
    )
    assert decision == "deny"
    assert "main" in hso["permissionDecisionReason"]


def test_command_substitution_does_not_disturb_the_base_dir(tmp_path, home):
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    other = _make_repo(tmp_path / "other", "feat/x", STD_CFG)
    decision, _ = _run(f"echo $(cd {other} && pwd) && git commit -m x", repo, home)
    assert decision == "deny"


# ─── shell control flow ───────────────────────────────────────
#
# Defect 14, parsing axis. Reserved words sit in FRONT of the command they
# introduce, and the segment splitter leaves them glued to it — so `then git
# commit` tokenized as `["then", "git", …]` and the parser, which only ever
# looked for `git` at position 0 (after wrappers and assignments), did not see
# a git command at all. `if …; then git commit; fi` is about as ordinary a Bash
# form as exists.

CONTROL_FLOW_COMMITS = [
    "if true; then git commit -m x; fi",
    "if false; then echo no; else git commit -m x; fi",
    "if false; then echo no; elif true; then git commit -m x; fi",
    "while true; do git commit -m x; done",
    "until false; do git commit -m x; done",
    "for f in a b; do git commit -m x; done",
    "! git commit -m x",
    "time git commit -m x",
    "if true; then { git commit -m x; }; fi",
]


@pytest.mark.parametrize("cmd", CONTROL_FLOW_COMMITS)
def test_control_flow_commit_denied_on_protected(cmd, tmp_path, home):
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, hso = _run(cmd, repo, home)
    assert decision == "deny", cmd
    assert "main" in hso["permissionDecisionReason"], cmd


@pytest.mark.parametrize("cmd", CONTROL_FLOW_COMMITS)
def test_control_flow_commit_allowed_on_feature_branch(cmd, tmp_path, home):
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, _ = _run(cmd, repo, home)
    assert decision == "allow", cmd


@pytest.mark.parametrize(
    "cmd",
    [
        "while true; do git push origin main; done",
        "if true; then git push origin main; fi",
        "for f in a; do git push origin main; done",
        "while git push origin main; do echo again; done",
    ],
)
def test_control_flow_push_to_protected_denied_from_feature_branch(cmd, tmp_path, home):
    repo = _make_repo(tmp_path / "r", "feat/x", STD_CFG)
    decision, hso = _run(cmd, repo, home)
    assert decision == "deny", cmd
    assert "main" in hso["permissionDecisionReason"], cmd


def test_control_flow_condition_is_read_too(tmp_path, home):
    """`if git …` / `while git …` put a real git command in the condition."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run("if git diff --quiet; then echo clean; fi", repo, home)
    assert decision == "allow", "a read-only condition must not be blocked"
    decision, _ = _run("if git commit -m x; then echo done; fi", repo, home)
    assert decision == "deny"


def test_control_flow_cd_is_followed(tmp_path, home):
    """A `cd` behind a reserved word must move the guard as well."""
    session = _make_repo(tmp_path / "lab", "feat/work", STD_CFG)
    other = _make_repo(tmp_path / "other", "main", STD_CFG)
    decision, hso = _run(
        f"if true; then cd {other}; git commit -m x; fi", session, home
    )
    assert decision == "deny"
    assert "main" in hso["permissionDecisionReason"]


def test_control_flow_terminators_are_not_commands(tmp_path, home):
    """`fi` / `done` / `esac` land in segments of their own and must stay
    inert — no denial, no crash."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    decision, _ = _run("if true; then echo hi; fi; git status", repo, home)
    assert decision == "allow"


def test_control_flow_wrappers_compose(tmp_path, home):
    """The reserved word peels first, then the `env` / path handling."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    for cmd in (
        "if true; then env VAR=x git commit -m y; fi",
        "while true; do /usr/bin/git commit -m y; done",
        "if true; then command git commit -m y; fi",
    ):
        decision, _ = _run(cmd, repo, home)
        assert decision == "deny", cmd


# ─── the guard describes itself honestly ──────────────────────


def test_guidance_states_the_coverage_criterion(tmp_path, home):
    """Eleven defects in, the denial text must not imply completeness — but nor
    should it be a bare "best effort" with no criterion. It has to name BOTH
    axes it can be wrong on, state the line (ordinary invocation forms in,
    constructed evasion out), name the tool-call-only scope, and point at
    `pre-push` as the layer that holds."""
    repo = _make_repo(tmp_path / "r", "main", STD_CFG)
    _, hso = _run("git commit -m x", repo, home)
    guidance = hso["additionalContext"]
    assert "not enforcement" in guidance
    assert "ordinary invocation forms" in guidance
    assert "evasion" in guidance
    assert "Claude tool calls only" in guidance
    # both axes, not just parsing
    assert "the command" in guidance
    assert "the environment" in guidance
    assert "pre-push" in guidance
    assert "TOM-348" in guidance

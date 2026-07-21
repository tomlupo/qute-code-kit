"""Tests for qute_coder_flow.sh — the /qute-coder verb-contract chain.

Verifies the Jimek verb contract WITHOUT changing human-invocation defaults:
- default invocation still opens → reviews → assigns (to tomlupo) — regression guard;
- chain-control flags parameterize policy: --no-review, --no-assign, --assign-to;
- --json emits ONE structured object a conductor can branch on;
- idempotency: an existing OPEN PR for the branch is REUSED (no second PR);
- ADR-0005: a leftover `.github/qute-pr.yml` has NO effect (policy file is dead).

All externals (gh, gh-app-token minter, codex, curl) are shell stubs on PATH.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "qute_coder_flow.sh"
PR_URL = "https://github.com/o/r/pull/7"


def _write(path: Path, body: str) -> None:
    path.write_text("#!/usr/bin/env bash\n" + body)
    path.chmod(0o755)


@pytest.fixture
def env(tmp_path: Path):
    bind = tmp_path / "bin"
    bind.mkdir()
    ghapps = tmp_path / "ghapps"
    ghapps.mkdir()
    # both apps' creds (coder opens the PR; review posts the verdict)
    (ghapps / "coding.env").write_text("CODING_APP_ID=4172326\n")
    (ghapps / "coding.pem").write_text("dummy\n")
    (ghapps / "review.env").write_text("REVIEW_APP_ID=4172333\n")
    (ghapps / "review.pem").write_text("dummy\n")
    _write(ghapps / "gh-app-token", 'echo "tok-$1"')

    marker = tmp_path / "reviews.count"  # native review objects posted
    calls = tmp_path / "calls.log"  # every gh invocation
    existing = tmp_path / "existing.url"  # if present, `pr list` returns it

    _write(
        bind / "gh",
        f'''
echo "gh $*" >> "{calls}"
args="$*"
case "$args" in
  "pr list"*)
    if [ -f "{existing}" ]; then cat "{existing}"; fi; exit 0 ;;
  "pr create"*) echo "{PR_URL}"; exit 0 ;;
  "pr diff"*) echo "diff --git a/x b/x"; echo "+changed"; exit 0 ;;
  "pr edit"*) exit 0 ;;
  "repo view"*) echo "o/r"; exit 0 ;;
  *"pulls/"*"/reviews"*)
    if [[ "$args" == *"-X POST"* ]]; then
      n=0; [ -f "{marker}" ] && n=$(cat "{marker}"); echo $((n+1)) > "{marker}"
      echo created; exit 0
    elif [[ "$args" == *".body"* ]]; then
      echo "VERDICT: SHIP-WITH-NITS"; exit 0     # latest_bot_verdict body query
    else
      n=0; [ -f "{marker}" ] && n=$(cat "{marker}"); echo "$n"; exit 0
    fi ;;
  *"pulls/7"*) echo "beef7"; exit 0 ;;
  *"assignees"*|*"requested_reviewers"*) exit 0 ;;
  *) exit 0 ;;
esac
''',
    )
    _write(
        bind / "codex", 'cat >/dev/null\necho "VERDICT: SHIP-WITH-NITS"\necho "- nit"'
    )
    _write(bind / "curl", 'printf "000"; exit 0')  # dispatcher unreachable
    _write(bind / "git", "echo feature")  # rev-parse --abbrev-ref -> feature

    import os

    base = dict(os.environ)
    base["PATH"] = f"{bind}:{base['PATH']}"
    base["QUTE_GH_APPS_DIR"] = str(ghapps)
    base["HOME"] = str(tmp_path)
    base["QUTE_REVIEW_MODE"] = "local"  # avoid the dispatcher probe in the sub-verb
    return {
        "path_env": base,
        "bin": bind,
        "marker": marker,
        "calls": calls,
        "existing": existing,
        "cwd": tmp_path,
    }


def _run(env, args, cwd=None, extra_env=None):
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env={**env["path_env"], **(extra_env or {})},
        cwd=str(cwd or env["cwd"]),
        timeout=60,
    )


def _last_json(stdout: str) -> dict:
    line = [x for x in stdout.splitlines() if x.strip().startswith("{")][-1]
    return json.loads(line)


BASE_ARGS = [
    "--json",
    "--repo",
    "o/r",
    "--head",
    "feature",
    "--title",
    "T",
    "--body",
    "B",
]


def test_defaults_regression_open_review_assign(env):
    """Default human invocation: open + independent review + assign to tomlupo."""
    r = _run(env, BASE_ARGS)
    assert r.returncode == 0, r.stderr
    j = _last_json(r.stdout)
    assert j["verb"] == "qute-coder"
    assert j["ok"] is True
    assert j["pr_url"] == PR_URL and j["pr_number"] == 7
    assert j["created"] is True
    assert j["review"]["ran"] is True and j["review"]["ok"] is True
    assert j["review"]["verdict"] == "SHIP-WITH-NITS"
    assert j["assign"]["ran"] is True and j["assign"]["to"] == "tomlupo"
    # a native review object was actually posted
    assert env["marker"].read_text().strip() == "1"
    calls = env["calls"].read_text()
    assert "pr create" in calls
    assert "add-assignee tomlupo" in calls or "assignees" in calls


def test_no_review_no_assign_flags(env):
    r = _run(env, [*BASE_ARGS, "--no-review", "--no-assign"])
    assert r.returncode == 0, r.stderr
    j = _last_json(r.stdout)
    assert j["review"]["ran"] is False
    assert j["assign"]["ran"] is False
    assert not env["marker"].exists()  # no review posted
    assert "add-assignee" not in env["calls"].read_text()


def test_passthrough_value_not_mistaken_for_chain_flag(env):
    """A gh value that looks like a chain flag (--body '--no-review') must NOT be
    consumed as the chain flag — review must still run."""
    r = _run(
        env,
        [
            "--json",
            "--repo",
            "o/r",
            "--head",
            "feature",
            "--title",
            "T",
            "--body",
            "--no-review",
        ],
    )
    assert r.returncode == 0, r.stderr
    j = _last_json(r.stdout)
    assert j["review"]["ran"] is True  # --no-review was a body VALUE, not a flag
    assert j["assign"]["ran"] is True
    # the literal value reached gh pr create
    assert "--body --no-review" in env["calls"].read_text()


def test_short_title_flag_value_not_stolen(env):
    """gh's short `-t` (title) value that looks like a chain flag stays a value."""
    r = _run(
        env,
        [
            "--json",
            "--repo",
            "o/r",
            "--head",
            "feature",
            "-t",
            "--no-assign",
            "--body",
            "B",
        ],
    )
    assert r.returncode == 0, r.stderr
    j = _last_json(r.stdout)
    assert j["assign"]["ran"] is True  # --no-assign was the -t title VALUE
    assert "-t --no-assign" in env["calls"].read_text()


def test_assign_to_override(env):
    r = _run(env, [*BASE_ARGS, "--assign-to", "alice"])
    assert r.returncode == 0, r.stderr
    j = _last_json(r.stdout)
    assert j["assign"]["to"] == "alice"
    assert "add-assignee alice" in env["calls"].read_text()


def test_idempotent_reuses_existing_pr(env):
    env["existing"].write_text(PR_URL + "\n")  # `pr list` finds an open PR
    r = _run(env, BASE_ARGS)
    assert r.returncode == 0, r.stderr
    j = _last_json(r.stdout)
    assert j["created"] is False  # reused, not re-opened
    assert j["pr_url"] == PR_URL
    assert "pr create" not in env["calls"].read_text()  # no second PR opened
    # review + assign still run against the existing PR
    assert j["review"]["ran"] is True
    assert j["assign"]["ran"] is True


def test_qute_pr_yml_is_ignored(env, tmp_path):
    """ADR-0005: `.github/qute-pr.yml` is dead — a leftover file must have NO effect."""
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    (repo / ".github").mkdir()
    (repo / ".github" / "qute-pr.yml").write_text("baseBranch: dev\n")
    r = _run(
        env,
        ["--json", "--repo", "o/r", "--head", "feature", "--title", "T", "--body", "B"],
        cwd=repo,
    )
    assert r.returncode == 0, r.stderr
    j = _last_json(r.stdout)
    assert j["base"] is None  # gh default — the leftover policy file changed nothing
    assert "--base dev" not in env["calls"].read_text()


def test_env_assign_to_default(env):
    """QUTE_ASSIGN_TO env sets the default assignee; --assign-to still wins."""
    r = _run(env, BASE_ARGS, extra_env={"QUTE_ASSIGN_TO": "bob"})
    assert r.returncode == 0, r.stderr
    j = _last_json(r.stdout)
    assert j["assign"]["to"] == "bob"

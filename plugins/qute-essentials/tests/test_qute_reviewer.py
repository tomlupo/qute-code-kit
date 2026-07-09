"""Tests for qute_reviewer_post.sh — portable two-mode independent review poster.

Verifies:
- auto mode picks LOCAL when the dispatcher is unreachable, and DISPATCHER when it is;
- explicit QUTE_REVIEW_MODE overrides the probe;
- LOCAL mode generates the verdict in a SEPARATE PROCESS (codex) — never an in-process
  subagent — and posts a native review OBJECT via `gh api .../pulls/N/reviews`;
- the codex->claude fallback fires when codex is absent;
- success is confirmed by a qute-review[bot] review object appearing.

All externals (gh, curl, codex, claude, gh-app-token) are mocked as shell stubs on PATH.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "qute_reviewer_post.sh"


def _write(path: Path, body: str) -> None:
    path.write_text("#!/usr/bin/env bash\n" + body)
    path.chmod(0o755)


@pytest.fixture
def env(tmp_path: Path):
    """A mock host: bin/ stubs for every external, plus gh-apps creds.

    The gh stub records calls to reviews-POST via a marker file so the reviews-GET
    count reflects whether a review object was 'created'.
    """
    bind = tmp_path / "bin"
    bind.mkdir()
    ghapps = tmp_path / "ghapps"
    ghapps.mkdir()
    (ghapps / "review.env").write_text("REVIEW_APP_ID=4172333\n")
    (ghapps / "review.pem").write_text("dummy-pem\n")
    marker = tmp_path / "posted.count"
    calls = tmp_path / "calls.log"

    # gh stub: emulate `gh api .../reviews` (GET count + POST create) and `gh pr diff`.
    _write(
        bind / "gh",
        f'''
echo "gh $*" >> "{calls}"
args="$*"
case "$args" in
  *"pulls/"*"/reviews"*)
    # a POST carries -X POST; a GET does not.
    if [[ "$args" == *"-X POST"* || "$args" == *"--method POST"* ]]; then
      n=0; [ -f "{marker}" ] && n=$(cat "{marker}"); echo $((n+1)) > "{marker}"
      echo "created"; exit 0
    else
      n=0; [ -f "{marker}" ] && n=$(cat "{marker}"); echo "$n"; exit 0
    fi ;;
  "pr diff"*) echo "diff --git a/x b/x"; echo "+changed"; exit 0 ;;
  *) exit 0 ;;
esac
''',
    )
    # the minter is resolved from the gh-apps dir ($GHAPPS/gh-app-token), not PATH
    _write(
        ghapps / "gh-app-token",
        f'echo "gh-app-token $*" >> "{calls}"\necho "tok-review-123"',
    )

    base = dict(os.environ)
    base["PATH"] = f"{bind}:{base['PATH']}"
    base["QUTE_GH_APPS_DIR"] = str(ghapps)
    base["HOME"] = str(tmp_path)
    return {
        "path_env": base,
        "bin": bind,
        "ghapps": ghapps,
        "marker": marker,
        "calls": calls,
        "write": _write,
    }


def _run(env, extra=None):
    e = dict(env["path_env"])
    if extra:
        e.update(extra)
    return subprocess.run(
        ["bash", str(SCRIPT), "o/r", "42"],
        capture_output=True,
        text=True,
        env=e,
        timeout=30,
    )


def _add_curl(env, health_code: str):
    """Add a curl stub whose /health returns the given HTTP code."""
    env["write"](
        env["bin"] / "curl",
        f'if [[ "$*" == *"/health"* ]]; then printf "{health_code}"; exit 0; fi\n'
        'if [[ "$*" == *"/review"* ]]; then echo "{}"; exit 0; fi\nexit 0\n',
    )


def _add_codex(env, ok: bool = True):
    if ok:
        env["write"](
            env["bin"] / "codex",
            'cat >/dev/null\necho "VERDICT: SHIP-WITH-NITS"\necho "- nit"',
        )
    # if not ok, simply don't create the stub -> command -v codex fails


def _add_claude(env):
    env["write"](
        env["bin"] / "claude", 'cat >/dev/null\necho "VERDICT: SHIP"\necho "- ok"'
    )


def test_auto_selects_local_when_dispatcher_down(env):
    _add_curl(env, "000")  # unreachable
    _add_codex(env)
    r = _run(env)
    assert r.returncode == 0, r.stderr
    assert "mode=local" in r.stderr
    # posted a review object via the app token + gh api
    assert int(env["marker"].read_text()) == 1
    calls = env["calls"].read_text()
    assert "gh-app-token 4172333" in calls
    assert "-X POST" in calls  # native review object create


def test_auto_selects_dispatcher_when_up(env):
    _add_curl(env, "200")  # reachable
    # pre-seed one existing bot review so the confirm passes without a local post
    env["marker"].write_text("1")
    r = _run(env)
    assert r.returncode == 0, r.stderr
    assert "mode=dispatcher" in r.stderr
    # dispatcher mode must NOT mint the app token / post via gh api itself
    assert "gh-app-token" not in env["calls"].read_text()


def test_explicit_local_overrides_probe(env):
    _add_curl(env, "200")  # dispatcher IS up, but override forces local
    _add_codex(env)
    r = _run(env, {"QUTE_REVIEW_MODE": "local"})
    assert r.returncode == 0, r.stderr
    assert "mode=local" in r.stderr
    assert int(env["marker"].read_text()) == 1


def test_local_uses_separate_process_codex(env):
    _add_curl(env, "000")
    _add_codex(env)
    r = _run(env, {"QUTE_REVIEW_MODE": "local"})
    assert r.returncode == 0, r.stderr
    # verdict generated by the codex separate process (not an in-process subagent)
    assert "codex exec (cross-model" in r.stderr


def test_local_falls_back_to_claude_when_no_codex(env):
    _add_curl(env, "000")
    _add_claude(env)  # codex stub intentionally absent
    r = _run(env, {"QUTE_REVIEW_MODE": "local"})
    assert r.returncode == 0, r.stderr
    assert "fresh 'claude -p'" in r.stderr
    assert int(env["marker"].read_text()) == 1


def test_invalid_mode_errors(env):
    _add_curl(env, "000")
    r = _run(env, {"QUTE_REVIEW_MODE": "bogus"})
    assert r.returncode != 0
    assert "invalid QUTE_REVIEW_MODE" in r.stderr


# ── verb contract: --json structured return + head-SHA idempotency ───────
import json as _json  # noqa: E402


def _run_args(env, args, extra=None):
    e = dict(env["path_env"])
    if extra:
        e.update(extra)
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=e,
        timeout=30,
    )


def _last_json(stdout: str) -> dict:
    line = [x for x in stdout.splitlines() if x.strip().startswith("{")][-1]
    return _json.loads(line)


def _add_head_sha(env, sha: str = "deadbeef"):
    """Augment the gh stub so `gh api repos/o/r/pulls/42` (no /reviews) returns a
    head SHA — required to exercise the idempotency path. Reviews endpoints keep
    returning the marker count (so at-head count == marker)."""
    marker = env["marker"]
    calls = env["calls"]
    env["write"](
        env["bin"] / "gh",
        f'''
echo "gh $*" >> "{calls}"
args="$*"
case "$args" in
  *"pulls/"*"/reviews"*)
    if [[ "$args" == *"-X POST"* || "$args" == *"--method POST"* ]]; then
      n=0; [ -f "{marker}" ] && n=$(cat "{marker}"); echo $((n+1)) > "{marker}"
      echo "created"; exit 0
    else
      n=0; [ -f "{marker}" ] && n=$(cat "{marker}"); echo "$n"; exit 0
    fi ;;
  *"pulls/42"*) echo "{sha}"; exit 0 ;;
  "pr diff"*) echo "diff --git a/x b/x"; echo "+changed"; exit 0 ;;
  *) exit 0 ;;
esac
''',
    )


def test_json_output_on_success(env):
    _add_curl(env, "000")
    _add_codex(env)
    r = _run_args(env, ["--json", "o/r", "42"], {"QUTE_REVIEW_MODE": "local"})
    assert r.returncode == 0, r.stderr
    j = _last_json(r.stdout)
    assert j["verb"] == "qute-reviewer"
    assert j["ok"] is True
    assert j["posted"] is True
    assert j["idempotent_skip"] is False
    assert j["repo"] == "o/r" and j["pr"] == 42


def test_idempotent_skip_when_review_exists(env):
    _add_curl(env, "000")
    _add_codex(env)
    _add_head_sha(env)
    env["marker"].write_text("1")  # a bot review already exists at head SHA
    r = _run_args(env, ["--json", "o/r", "42"], {"QUTE_REVIEW_MODE": "local"})
    assert r.returncode == 0, r.stderr
    assert "idempotent" in r.stderr
    j = _last_json(r.stdout)
    assert j["idempotent_skip"] is True
    assert j["posted"] is False
    # no NEW review object posted (marker unchanged)
    assert env["marker"].read_text().strip() == "1"
    assert "-X POST" not in env["calls"].read_text()


def test_force_posts_even_when_review_exists(env):
    _add_curl(env, "000")
    _add_codex(env)
    _add_head_sha(env)
    env["marker"].write_text("1")
    r = _run_args(env, ["--force", "o/r", "42"], {"QUTE_REVIEW_MODE": "local"})
    assert r.returncode == 0, r.stderr
    # --force bypasses idempotency and posts anyway (marker incremented)
    assert env["marker"].read_text().strip() == "2"

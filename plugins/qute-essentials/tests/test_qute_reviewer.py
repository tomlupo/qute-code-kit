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
    calls = tmp_path / "calls.log"
    # Faithful model: `reviews` holds one head-SHA per posted qute-review[bot]
    # review object; `headsha` is the PR's current head SHA. The stub honors the
    # `commit_id==<sha>` jq filter so head-SHA idempotency/confirmation is really
    # exercised (a stale review on a different SHA does NOT count as current).
    reviews = tmp_path / "reviews.shas"
    reviews.write_text("")
    headsha = tmp_path / "head.sha"
    headsha.write_text("H1")

    _write(
        bind / "gh",
        f'''
echo "gh $*" >> "{calls}"
args="$*"
case "$args" in
  *"pulls/"*"/reviews"*)
    if [[ "$args" == *"-X POST"* || "$args" == *"--method POST"* ]]; then
      cat "{headsha}" >> "{reviews}"; echo "created"; exit 0
    elif [[ "$args" == *'commit_id=="'* ]]; then
      want="${{args#*commit_id==\\"}}"; want="${{want%%\\"*}}"
      awk -v w="$want" '$0==w{{n++}} END{{print n+0}}' "{reviews}"; exit 0
    else
      awk 'END{{print NR+0}}' "{reviews}"; exit 0
    fi ;;
  *"pulls/42"*) cat "{headsha}"; exit 0 ;;
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
        "reviews": reviews,
        "headsha": headsha,
        "calls": calls,
        "write": _write,
    }


def _review_count(env) -> int:
    return len([x for x in env["reviews"].read_text().splitlines() if x.strip()])


def _run(env, extra=None, args=("o/r", "42")):
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


def _add_curl(env, health_code: str):
    """curl stub: /health returns the code; a reachable dispatcher /review POST
    simulates the dispatcher creating a review at the current head SHA."""
    env["write"](
        env["bin"] / "curl",
        f'if [[ "$*" == *"/health"* ]]; then printf "{health_code}"; exit 0; fi\n'
        f'if [[ "$*" == *"/review"* ]]; then cat "{env["headsha"]}" >> "{env["reviews"]}"; echo "{{}}"; exit 0; fi\n'
        "exit 0\n",
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
    assert _review_count(env) == 1
    calls = env["calls"].read_text()
    assert "gh-app-token 4172333" in calls
    assert "-X POST" in calls  # native review object create


def test_auto_selects_dispatcher_when_up(env):
    _add_curl(env, "200")  # reachable — the /review POST simulates the dispatcher post
    r = _run(env)
    assert r.returncode == 0, r.stderr
    assert "mode=dispatcher" in r.stderr
    # dispatcher mode must NOT mint the app token / post via gh api itself
    assert "gh-app-token" not in env["calls"].read_text()
    assert _review_count(env) == 1  # the dispatcher created exactly one


def test_explicit_local_overrides_probe(env):
    _add_curl(env, "200")  # dispatcher IS up, but override forces local
    _add_codex(env)
    r = _run(env, {"QUTE_REVIEW_MODE": "local"})
    assert r.returncode == 0, r.stderr
    assert "mode=local" in r.stderr
    assert _review_count(env) == 1


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
    assert _review_count(env) == 1


def test_invalid_mode_errors(env):
    _add_curl(env, "000")
    r = _run(env, {"QUTE_REVIEW_MODE": "bogus"})
    assert r.returncode != 0
    assert "invalid QUTE_REVIEW_MODE" in r.stderr


# ── verb contract: --json structured return + head-SHA idempotency ───────
import json as _json  # noqa: E402


def _last_json(stdout: str) -> dict:
    line = [x for x in stdout.splitlines() if x.strip().startswith("{")][-1]
    return _json.loads(line)


def test_json_output_on_success(env):
    _add_curl(env, "000")
    _add_codex(env)
    r = _run(env, {"QUTE_REVIEW_MODE": "local"}, args=("--json", "o/r", "42"))
    assert r.returncode == 0, r.stderr
    j = _last_json(r.stdout)
    assert j["verb"] == "qute-reviewer"
    assert j["ok"] is True
    assert j["posted"] is True
    assert j["idempotent_skip"] is False
    assert j["repo"] == "o/r" and j["pr"] == 42


def test_idempotent_skip_when_review_at_head_exists(env):
    _add_curl(env, "000")
    _add_codex(env)
    env["reviews"].write_text("H1\n")  # a bot review already exists at head SHA H1
    r = _run(env, {"QUTE_REVIEW_MODE": "local"}, args=("--json", "o/r", "42"))
    assert r.returncode == 0, r.stderr
    assert "idempotent" in r.stderr
    j = _last_json(r.stdout)
    assert j["idempotent_skip"] is True
    assert j["posted"] is False
    assert _review_count(env) == 1  # no NEW review posted
    assert "-X POST" not in env["calls"].read_text()


def test_stale_review_on_old_sha_does_not_skip(env):
    """A review on an OLDER head SHA must NOT count as current — re-review posts."""
    _add_curl(env, "000")
    _add_codex(env)
    env["reviews"].write_text("OLDSHA\n")  # stale review, PR head is H1
    r = _run(env, {"QUTE_REVIEW_MODE": "local"}, args=("--json", "o/r", "42"))
    assert r.returncode == 0, r.stderr
    assert "idempotent" not in r.stderr  # did NOT skip
    j = _last_json(r.stdout)
    assert j["idempotent_skip"] is False
    assert j["posted"] is True
    # posted a fresh review at the current head SHA H1 (2 total now: OLDSHA + H1)
    assert _review_count(env) == 2


def test_force_posts_even_when_review_at_head_exists(env):
    _add_curl(env, "000")
    _add_codex(env)
    env["reviews"].write_text("H1\n")
    r = _run(env, {"QUTE_REVIEW_MODE": "local"}, args=("--force", "o/r", "42"))
    assert r.returncode == 0, r.stderr
    assert _review_count(env) == 2  # --force bypasses idempotency and posts anyway

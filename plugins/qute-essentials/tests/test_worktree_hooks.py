"""Tests for the worktree lifecycle hooks (worktree_create.py / worktree_remove.py).

The remove hook deletes directories, so most of this file is the refusal
matrix: traversal names, symlinked venvs, non-venv directories, in-use venvs,
and empty/degenerate names must all refuse and leave the filesystem intact.
The create hook's setup path is tested for both the happy paths and the
fail-loud paths (missing uv, failing uv sync, failing post-worktree.sh).

Hooks are exercised as subprocesses with HOME pointed at a tmp dir, so the
real ~/.venvs is never touched.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parent.parent / "hooks"
REMOVE = HOOKS / "worktree_remove.py"
CREATE = HOOKS / "worktree_create.py"


def _env(home: Path, extra_path: Path | None = None) -> dict:
    env = dict(os.environ, HOME=str(home))
    if extra_path is not None:
        env["PATH"] = f"{extra_path}:{env['PATH']}"
    return env


def _reap(home: Path, worktree_path: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(REMOVE), "--reap", worktree_path],
        capture_output=True,
        text=True,
        env=_env(home),
    )


def _mk_venv(home: Path, name: str) -> Path:
    venv = home / ".venvs" / name
    venv.mkdir(parents=True)
    (venv / "pyvenv.cfg").write_text("home = /usr\n")
    (venv / "lib").mkdir()
    return venv


def _log(home: Path) -> str:
    log = home / ".claude" / "qute-worktree-reap.log"
    return log.read_text() if log.is_file() else ""


# ── worktree_remove: happy path ──────────────────────────────────────────────


def test_reap_deletes_matching_venv(tmp_path):
    venv = _mk_venv(tmp_path, "wt-a")
    proc = _reap(tmp_path, "/somewhere/worktrees/wt-a")
    assert proc.returncode == 0
    assert not venv.exists()
    assert (tmp_path / ".venvs").is_dir()  # root itself untouched
    assert "reaped" in _log(tmp_path)


def test_reap_hook_mode_exits_zero_and_deletes(tmp_path):
    venv = _mk_venv(tmp_path, "wt-b")
    proc = subprocess.run(
        [sys.executable, str(REMOVE)],
        input=json.dumps({"worktree_path": "/x/wt-b", "branch_name": "b"}),
        capture_output=True,
        text=True,
        env=_env(tmp_path),
    )
    assert proc.returncode == 0
    assert not venv.exists()


def test_missing_venv_is_skip_not_error(tmp_path):
    (tmp_path / ".venvs").mkdir()
    proc = _reap(tmp_path, "/x/no-such-venv")
    assert proc.returncode == 1  # --reap signals "nothing deleted"
    assert "skip: no venv" in _log(tmp_path)


# ── worktree_remove: refusal matrix ──────────────────────────────────────────


def test_refuses_traversal_basename(tmp_path):
    _mk_venv(tmp_path, "victim")
    proc = _reap(tmp_path, "/x/..")
    assert proc.returncode == 1
    assert (tmp_path / ".venvs" / "victim").exists()
    assert "REFUSED: invalid worktree basename" in _log(tmp_path)


def test_refuses_empty_name(tmp_path):
    _mk_venv(tmp_path, "victim")
    for bad in ("", "/", "."):
        assert _reap(tmp_path, bad).returncode == 1
    assert (tmp_path / ".venvs" / "victim").exists()


def test_refuses_symlinked_venv(tmp_path):
    outside = tmp_path / "outside-data"
    outside.mkdir()
    (outside / "pyvenv.cfg").write_text("home = /usr\n")
    (tmp_path / ".venvs").mkdir()
    (tmp_path / ".venvs" / "wt-link").symlink_to(outside)
    proc = _reap(tmp_path, "/x/wt-link")
    assert proc.returncode == 1
    assert outside.exists()
    assert (outside / "pyvenv.cfg").exists()
    assert "REFUSED" in _log(tmp_path) and "symlink" in _log(tmp_path)


def test_refuses_non_venv_directory(tmp_path):
    """Name collision with a directory that isn't a venv must not delete it."""
    imposter = tmp_path / ".venvs" / "wt-c"
    imposter.mkdir(parents=True)
    (imposter / "important.txt").write_text("data")
    proc = _reap(tmp_path, "/x/wt-c")
    assert proc.returncode == 1
    assert (imposter / "important.txt").exists()
    assert "no pyvenv.cfg" in _log(tmp_path)


@pytest.mark.skipif(not Path("/proc").is_dir(), reason="needs /proc")
def test_refuses_venv_held_by_live_process(tmp_path):
    venv = _mk_venv(tmp_path, "wt-busy")
    holder = subprocess.Popen(["sleep", "30"], cwd=venv, stdout=subprocess.DEVNULL)
    try:
        proc = _reap(tmp_path, "/x/wt-busy")
        assert proc.returncode == 1
        assert venv.exists()
        assert "held by a live process" in _log(tmp_path)
    finally:
        holder.kill()
        holder.wait()
    # once released, the same reap succeeds
    assert _reap(tmp_path, "/x/wt-busy").returncode == 0
    assert not venv.exists()


def test_garbage_hook_input_soft_exits_zero(tmp_path):
    proc = subprocess.run(
        [sys.executable, str(REMOVE)],
        input="not json",
        capture_output=True,
        text=True,
        env=_env(tmp_path),
    )
    assert proc.returncode == 0
    assert "REFUSED: invalid hook input" in _log(tmp_path)


# ── worktree_create: setup ───────────────────────────────────────────────────


def _mk_project(tmp_path: Path, config: dict | None) -> tuple[Path, Path]:
    base = tmp_path / "main"
    wt = tmp_path / "wt" / "proj-feat-x"
    (base / ".claude").mkdir(parents=True)
    wt.mkdir(parents=True)
    if config is not None:
        (base / ".claude" / "worktree.json").write_text(json.dumps(config))
    return base, wt


def _setup(home: Path, wt: Path, base: Path, path_dir: Path | None = None):
    return subprocess.run(
        [sys.executable, str(CREATE), "--setup", str(wt), "--base", str(base)],
        capture_output=True,
        text=True,
        env=_env(home, path_dir),
    )


def _stub_uv(tmp_path: Path, exit_code: int = 0) -> Path:
    bin_dir = tmp_path / "stubbin"
    bin_dir.mkdir(exist_ok=True)
    uv = bin_dir / "uv"
    uv.write_text(
        "#!/bin/sh\n"
        f'[ {exit_code} -ne 0 ] && {{ echo "stub uv failure" >&2; exit {exit_code}; }}\n'
        'mkdir -p "$UV_PROJECT_ENVIRONMENT"\n'
        'touch "$UV_PROJECT_ENVIRONMENT/pyvenv.cfg"\n'
    )
    uv.chmod(0o755)
    return bin_dir


def test_setup_no_config_is_noop(tmp_path):
    base, wt = _mk_project(tmp_path, None)
    proc = _setup(tmp_path, wt, base)
    assert proc.returncode == 0
    assert "setup OK" in proc.stdout


def test_setup_shared_dirs_and_copy_files(tmp_path):
    base, wt = _mk_project(
        tmp_path, {"shared_dirs": ["data"], "copy_files": ["local.toml"]}
    )
    (base / "data").mkdir()
    (base / "data" / "big.bin").write_text("x")
    (base / "local.toml").write_text("[cfg]")
    proc = _setup(tmp_path, wt, base)
    assert proc.returncode == 0
    assert (wt / "data").is_symlink()
    assert (wt / "data" / "big.bin").read_text() == "x"
    assert (wt / "local.toml").read_text() == "[cfg]"


def test_setup_uv_writes_envrc_and_syncs(tmp_path):
    base, wt = _mk_project(tmp_path, {"venv_setup": "uv"})
    proc = _setup(tmp_path, wt, base, _stub_uv(tmp_path))
    assert proc.returncode == 0, proc.stderr
    envrc = (wt / ".envrc").read_text()
    assert 'UV_PROJECT_ENVIRONMENT="$HOME/.venvs/${PWD##*/}"' in envrc
    assert (tmp_path / ".venvs" / wt.name / "pyvenv.cfg").exists()


def test_setup_uv_missing_binary_fails_loudly(tmp_path):
    base, wt = _mk_project(tmp_path, {"venv_setup": "uv"})
    env = _env(tmp_path)
    env["PATH"] = str(tmp_path / "emptybin")  # no uv anywhere
    (tmp_path / "emptybin").mkdir()
    proc = subprocess.run(
        [sys.executable, str(CREATE), "--setup", str(wt), "--base", str(base)],
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 1
    assert "`uv` not found" in proc.stderr


def test_setup_uv_sync_failure_fails_loudly(tmp_path):
    base, wt = _mk_project(tmp_path, {"venv_setup": "uv"})
    proc = _setup(tmp_path, wt, base, _stub_uv(tmp_path, exit_code=3))
    assert proc.returncode == 1
    assert "uv sync" in proc.stderr and "exited 3" in proc.stderr


def test_setup_unknown_venv_setup_fails(tmp_path):
    base, wt = _mk_project(tmp_path, {"venv_setup": "conda"})
    proc = _setup(tmp_path, wt, base)
    assert proc.returncode == 1
    assert "unknown value" in proc.stderr


def test_setup_post_worktree_failure_is_error(tmp_path):
    base, wt = _mk_project(tmp_path, None)
    hook = base / ".claude" / "post-worktree.sh"
    hook.write_text("#!/bin/sh\necho boom >&2\nexit 7\n")
    hook.chmod(0o755)
    proc = _setup(tmp_path, wt, base)
    assert proc.returncode == 1
    assert "post-worktree.sh" in proc.stderr and "exited 7" in proc.stderr


def test_hook_mode_creates_worktree_and_prints_path(tmp_path):
    """End-to-end WorktreeCreate contract against a throwaway git repo."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=t",
            "commit",
            "--allow-empty",
            "-q",
            "-m",
            "init",
        ],
        cwd=repo,
        check=True,
    )
    wt_path = tmp_path / "wts" / "repo-feat-y"
    payload = json.dumps(
        {
            "worktree_path": str(wt_path),
            "branch_name": "feat/y",
            "base_path": str(repo),
        }
    )
    proc = subprocess.run(
        [sys.executable, str(CREATE)],
        input=payload,
        capture_output=True,
        text=True,
        env=_env(tmp_path),
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == str(wt_path)
    assert (wt_path / ".git").exists()


def test_hook_mode_missing_fields_fail_creation(tmp_path):
    proc = subprocess.run(
        [sys.executable, str(CREATE)],
        input=json.dumps({"worktree_path": "/x"}),
        capture_output=True,
        text=True,
        env=_env(tmp_path),
    )
    assert proc.returncode == 1
    assert "missing worktree_path/branch_name/base_path" in proc.stderr

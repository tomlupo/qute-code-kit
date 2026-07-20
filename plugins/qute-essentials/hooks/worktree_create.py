#!/usr/bin/env python3
"""WorktreeCreate hook + shared worktree setup for the worktrees skill.

Two entry points, one implementation:

1. Hook mode (no args): Claude Code's native WorktreeCreate hook. Reads
   {worktree_path, branch_name, base_path} JSON on stdin, creates the git
   worktree itself (the hook contract replaces built-in creation), runs the
   .claude/worktree.json setup, prints the final worktree path to stdout and
   exits 0. Any failure exits non-zero, which makes Claude Code fail the
   worktree creation — setup problems are never silent.

2. `--setup <worktree_path> --base <main_checkout>`: run ONLY the setup steps
   on an already-created worktree. This is what the worktrees skill invokes
   after `git worktree add`, so the skill path and the native path share one
   code path.

Setup contract (mirrors skills/worktrees/SKILL.md steps 4-5):
- shared_dirs: symlink each existing dir from the main checkout (ln -sf).
- copy_files: copy each existing file from the main checkout.
- venv_setup == "uv": write .envrc exporting
  UV_PROJECT_ENVIRONMENT="$HOME/.venvs/<worktree-basename>", direnv allow
  (best effort), uv sync (mandatory — failure aborts).
- venv_setup == "pip": python -m venv .venv && .venv/bin/pip install -e .
- venv_setup absent/"none": skip venv, still apply shared_dirs/copy_files.
- .claude/post-worktree.sh (executable): run inside the worktree; non-zero
  exit is a hard failure.

Every step is verified after it runs (e.g. .envrc must exist, uv sync must
exit 0) so the "config says uv but the worktree silently ended up bare"
failure class cannot recur.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


class SetupError(RuntimeError):
    pass


def _run(cmd: list[str], cwd: Path, step: str) -> None:
    """Run a required command; raise SetupError with full output on failure."""
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise SetupError(f"{step}: command not found: {cmd[0]} ({exc})") from exc
    if proc.returncode != 0:
        raise SetupError(
            f"{step}: `{' '.join(cmd)}` exited {proc.returncode}\n"
            f"stdout: {proc.stdout.strip()}\nstderr: {proc.stderr.strip()}"
        )


def load_config(base_path: Path) -> dict:
    cfg_file = base_path / ".claude" / "worktree.json"
    if not cfg_file.is_file():
        return {}
    try:
        cfg = json.loads(cfg_file.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SetupError(f"unreadable/invalid {cfg_file}: {exc}") from exc
    if not isinstance(cfg, dict):
        raise SetupError(f"{cfg_file} must contain a JSON object")
    return cfg


MARKER_NAME = ".qute-worktree.json"


def _safe_rel_name(name: object, kind: str) -> str:
    """Validate a shared_dirs/copy_files entry as a safe relative subpath.

    Rejects absolute paths, `..` components, and empty names so a hostile or
    typo'd worktree.json can never make setup touch anything outside the
    worktree / main checkout.
    """
    if not isinstance(name, str) or not name.strip():
        raise SetupError(f"{kind}: invalid entry {name!r}")
    p = Path(name)
    if p.is_absolute() or ".." in p.parts or not p.parts:
        raise SetupError(f"{kind}: entry {name!r} must be a relative path without '..'")
    return name


def _dst_in_worktree(worktree: Path, name: str, kind: str) -> Path:
    """Return worktree/name after proving it cannot escape the worktree.

    `_safe_rel_name` already rejected absolute/`..`/empty entries; this closes
    the remaining hole — a symlink component inside the worktree (e.g. a
    tracked `link -> /outside` with entry `link/sub`) redirecting the write or
    delete outside. The destination's parent must resolve inside the resolved
    worktree, and an existing destination must itself resolve strictly inside
    (a symlink destination is fine — it is unlinked, never followed).
    """
    dst = worktree / name
    wt_res = worktree.resolve()
    parent_res = dst.parent.resolve()
    if parent_res != wt_res and wt_res not in parent_res.parents:
        raise SetupError(
            f"{kind}: entry {name!r} escapes the worktree via a symlinked "
            f"parent ({parent_res})"
        )
    if dst.exists() and not dst.is_symlink():
        dst_res = dst.resolve()
        if dst_res == wt_res or wt_res not in dst_res.parents:
            raise SetupError(
                f"{kind}: entry {name!r} resolves to {dst_res}, outside or "
                "equal to the worktree — refusing"
            )
    return dst


def setup_worktree(worktree: Path, base: Path) -> list[str]:
    """Apply worktree.json setup + post-worktree.sh. Returns log of actions."""
    actions: list[str] = []
    cfg = load_config(base)

    for name in cfg.get("shared_dirs", []):
        name = _safe_rel_name(name, "shared_dirs")
        src = base / name
        if not src.is_dir():
            actions.append(f"shared_dirs: skip {name} (missing in main checkout)")
            continue
        dst = _dst_in_worktree(worktree, name, "shared_dirs")
        if dst.is_symlink():
            dst.unlink()  # unlink removes the link itself, never the target
        elif dst.is_dir():
            shutil.rmtree(dst)
        elif dst.exists():
            dst.unlink()
        dst.symlink_to(src)
        if not dst.is_symlink():
            raise SetupError(f"shared_dirs: failed to symlink {name}")
        actions.append(f"shared_dirs: {name} -> {src}")

    for name in cfg.get("copy_files", []):
        name = _safe_rel_name(name, "copy_files")
        src = base / name
        if not src.is_file():
            actions.append(f"copy_files: skip {name} (missing in main checkout)")
            continue
        dst = _dst_in_worktree(worktree, name, "copy_files")
        if dst.is_symlink():
            dst.unlink()  # never write through a pre-existing symlink
        shutil.copy2(src, dst)
        if not dst.is_file():
            raise SetupError(f"copy_files: failed to copy {name}")
        actions.append(f"copy_files: {name}")

    venv_setup = cfg.get("venv_setup", "none")
    if venv_setup == "uv":
        envrc = worktree / ".envrc"
        envrc.write_text('export UV_PROJECT_ENVIRONMENT="$HOME/.venvs/${PWD##*/}"\n')
        if not envrc.is_file():
            raise SetupError("venv_setup=uv: .envrc was not written")
        # direnv is optional sugar; uv sync below is the real setup.
        if shutil.which("direnv"):
            subprocess.run(["direnv", "allow"], cwd=worktree, capture_output=True)
        if not shutil.which("uv"):
            raise SetupError("venv_setup=uv: `uv` not found on PATH")
        env_dir = Path.home() / ".venvs" / worktree.name
        env = dict(os.environ, UV_PROJECT_ENVIRONMENT=str(env_dir))
        proc = subprocess.run(
            ["uv", "sync"], cwd=worktree, capture_output=True, text=True, env=env
        )
        if proc.returncode != 0:
            raise SetupError(
                f"venv_setup=uv: `uv sync` exited {proc.returncode}\n"
                f"stderr: {proc.stderr.strip()}"
            )
        if not (env_dir / "pyvenv.cfg").is_file():
            raise SetupError(
                f"venv_setup=uv: uv sync succeeded but {env_dir} is not a venv"
            )
        # Ownership marker: worktree_remove.py only reaps venvs that carry a
        # marker recording the exact worktree they belong to.
        (env_dir / MARKER_NAME).write_text(
            json.dumps({"worktree_path": str(worktree)}) + "\n"
        )
        actions.append(f"venv_setup=uv: synced {env_dir}")
    elif venv_setup == "pip":
        _run([sys.executable, "-m", "venv", ".venv"], worktree, "venv_setup=pip")
        pip = worktree / ".venv" / "bin" / "pip"
        _run([str(pip), "install", "-e", "."], worktree, "venv_setup=pip")
        actions.append("venv_setup=pip: created .venv")
    elif venv_setup not in ("none", None):
        raise SetupError(f"venv_setup: unknown value {venv_setup!r}")

    hook = base / ".claude" / "post-worktree.sh"
    if hook.is_file() and os.access(hook, os.X_OK):
        _run([str(hook)], worktree, "post-worktree.sh")
        actions.append("post-worktree.sh: ok")

    return actions


def hook_main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"WorktreeCreate hook: invalid JSON input: {exc}", file=sys.stderr)
        return 1

    worktree_path = payload.get("worktree_path", "")
    branch_name = payload.get("branch_name", "")
    base_path = payload.get("base_path", "")
    if not worktree_path or not branch_name or not base_path:
        print(
            "WorktreeCreate hook: missing worktree_path/branch_name/base_path "
            f"in input: {json.dumps(payload)[:500]}",
            file=sys.stderr,
        )
        return 1

    base = Path(base_path)
    worktree = Path(worktree_path)
    try:
        # New branch first; fall back to checking out an existing branch.
        new = subprocess.run(
            [
                "git",
                "-C",
                str(base),
                "worktree",
                "add",
                str(worktree),
                "-b",
                branch_name,
            ],
            capture_output=True,
            text=True,
        )
        if new.returncode != 0:
            existing = subprocess.run(
                ["git", "-C", str(base), "worktree", "add", str(worktree), branch_name],
                capture_output=True,
                text=True,
            )
            if existing.returncode != 0:
                print(
                    "WorktreeCreate hook: git worktree add failed.\n"
                    f"-b attempt: {new.stderr.strip()}\n"
                    f"existing-branch attempt: {existing.stderr.strip()}",
                    file=sys.stderr,
                )
                return 1
        actions = setup_worktree(worktree, base)
    except SetupError as exc:
        print(f"WorktreeCreate hook: setup FAILED: {exc}", file=sys.stderr)
        return 1
    for line in actions:
        print(line, file=sys.stderr)
    print(worktree)
    return 0


def cli_main(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--setup", metavar="WORKTREE", required=True)
    parser.add_argument("--base", metavar="MAIN_CHECKOUT", required=True)
    args = parser.parse_args(argv)
    worktree = Path(args.setup).resolve()
    base = Path(args.base).resolve()
    if not worktree.is_dir():
        print(f"setup: worktree {worktree} is not a directory", file=sys.stderr)
        return 1
    try:
        actions = setup_worktree(worktree, base)
    except SetupError as exc:
        print(f"setup FAILED: {exc}", file=sys.stderr)
        return 1
    for line in actions:
        print(line)
    print(f"setup OK: {worktree}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1:
        sys.exit(cli_main(sys.argv[1:]))
    sys.exit(hook_main())

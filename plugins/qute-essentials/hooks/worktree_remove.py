#!/usr/bin/env python3
"""WorktreeRemove hook: reap the per-worktree venv under ~/.venvs.

The worktrees setup (worktree_create.py / the worktrees skill) keys venvs as
$HOME/.venvs/<worktree-dir-basename> via UV_PROJECT_ENVIRONMENT. Nothing ever
deleted them, so removed worktrees leaked venvs (1.7G of orphans found during
a disk incident). This hook reaps the matching venv when the worktree goes.

Entry points:
- Hook mode (no args): reads {worktree_path, ...} JSON on stdin.
- `--reap <worktree_path>`: same logic for manual `git worktree remove` flows
  (invoked by the worktrees skill, step 8).

Safety model — this hook deletes a directory, so every path out of here is
either "provably the right venv" or a refusal:
- The venv name is derived exactly like the create path: the worktree
  directory's basename (${PWD##*/} equivalent). Empty or dot names refused.
- The candidate must be a real directory (not a symlink) directly under
  $HOME/.venvs, and its fully resolved realpath must still be strictly inside
  the resolved $HOME/.venvs — symlink/.. escapes are refused. $HOME/.venvs
  itself can never be the target.
- The candidate must look like a venv (pyvenv.cfg present), so an unrelated
  directory that merely shares the name is refused.
- If any live process holds the venv (exe or cwd inside it, per /proc), refuse.

Failure is soft by contract (WorktreeRemove cannot block removal and its exit
code is ignored) but never silent: every decision is appended to
~/.claude/qute-worktree-reap.log and echoed to stderr (debug log).
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

LOG_FILE = Path.home() / ".claude" / "qute-worktree-reap.log"


def log(msg: str) -> None:
    line = f"worktree-reap: {msg}"
    print(line, file=sys.stderr)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a") as fh:
            fh.write(line + "\n")
    except OSError:
        pass  # stderr already has it; logging must never raise


def venv_in_use(venv: Path) -> bool:
    """True if any live process runs from or inside the venv (Linux /proc)."""
    proc_root = Path("/proc")
    if not proc_root.is_dir():
        return False  # no /proc (non-Linux): no reliable check available
    resolved = str(venv.resolve())
    prefix = resolved + "/"
    for pid_dir in proc_root.iterdir():
        if not pid_dir.name.isdigit():
            continue
        for link in ("exe", "cwd"):
            try:
                target = str((pid_dir / link).resolve())
            except OSError:
                continue
            if target == resolved or target.startswith(prefix):
                return True
    return False


def reap_venv(worktree_path: str, venvs_root: Path | None = None) -> bool:
    """Validate and delete the venv for a removed worktree.

    Returns True if a venv was deleted, False on any refusal (logged).
    `venvs_root` is injectable for tests; defaults to $HOME/.venvs.
    """
    root = venvs_root if venvs_root is not None else Path.home() / ".venvs"

    name = Path(worktree_path).name if worktree_path else ""
    if not name or name in (".", "..") or "/" in name:
        log(f"REFUSED: invalid worktree basename {name!r} from {worktree_path!r}")
        return False

    if not root.is_dir():
        log(f"skip: venvs root {root} does not exist")
        return False

    candidate = root / name
    if not candidate.exists():
        log(f"skip: no venv at {candidate}")
        return False
    if candidate.is_symlink():
        log(f"REFUSED: {candidate} is a symlink, not deleting")
        return False
    if not candidate.is_dir():
        log(f"REFUSED: {candidate} is not a directory")
        return False

    resolved_root = root.resolve()
    resolved = candidate.resolve()
    if resolved == resolved_root or resolved.parent != resolved_root:
        log(f"REFUSED: resolved path {resolved} is not strictly inside {resolved_root}")
        return False

    if not (candidate / "pyvenv.cfg").is_file():
        log(f"REFUSED: {candidate} has no pyvenv.cfg — not a venv, not deleting")
        return False

    if venv_in_use(candidate):
        log(f"REFUSED: {candidate} is held by a live process, not deleting")
        return False

    try:
        shutil.rmtree(candidate)
    except OSError as exc:
        log(f"FAILED: rmtree {candidate}: {exc}")
        return False
    log(f"reaped {candidate} (worktree {worktree_path} removed)")
    return True


def main(argv: list[str]) -> int:
    if argv and argv[0] == "--reap":
        if len(argv) != 2:
            print("usage: worktree_remove.py --reap <worktree_path>", file=sys.stderr)
            return 2
        return 0 if reap_venv(argv[1]) else 1
    try:
        payload = json.load(sys.stdin)
        worktree_path = payload.get("worktree_path", "")
    except (json.JSONDecodeError, AttributeError) as exc:
        log(f"REFUSED: invalid hook input: {exc}")
        return 0  # exit code is ignored by WorktreeRemove; stay soft
    reap_venv(worktree_path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

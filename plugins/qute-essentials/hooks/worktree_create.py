#!/usr/bin/env python3
"""WorktreeCreate hook + shared worktree setup for the worktrees skill.

Two entry points, one implementation:

1. Hook mode (no args): Claude Code's native WorktreeCreate hook. The hook
   contract replaces built-in creation — the hook creates the worktree, runs
   the .claude/worktree.json setup, and prints the final worktree path to
   stdout. Any failure exits non-zero, which makes Claude Code fail the
   worktree creation — setup problems are never silent.

   Two stdin payload shapes are accepted:

   a. `{name}` (+ the standard session_id/cwd/transcript_path envelope) —
      what Claude Code itself sends, for `claude --worktree`, `/worktree` and
      subagent `isolation: "worktree"` alike. `name` is a *suggested slug*
      only; the hook picks the path and branch (from `.claude/worktree.json`
      when present, else `<repo>/.claude/worktrees/<slug>` on branch
      `worktree-<slug>`, matching Claude Code's own built-in convention) and
      resolves the main checkout from `cwd`. Re-running with an existing
      worktree is a resume: setup re-runs in preserve mode (existing
      shared_dirs/copy_files entries are kept, not replaced), the path is
      printed, no error.

   b. `{worktree_path, branch_name, base_path}` — an explicit instruction to
      create exactly that worktree. Not emitted by Claude Code (verified
      against the 2.1.x CLI: `base_path` appears nowhere in it), kept for
      callers that drive the hook directly.

   An unrecognised payload logs and exits 0 rather than erroring.

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
import re
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


ENVRC_EXPORT = 'export UV_PROJECT_ENVIRONMENT="$HOME/.venvs/${PWD##*/}"'


def _read_text_or_empty(path: Path) -> str:
    try:
        return path.read_text()
    except (OSError, UnicodeDecodeError):
        return ""


def _points_at(link: Path, target: Path) -> bool:
    """True if `link` is a symlink already resolving to `target`."""
    try:
        return os.path.realpath(link) == os.path.realpath(target)
    except OSError:
        return False


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


def setup_worktree(
    worktree: Path, base: Path, preserve_existing: bool = False
) -> list[str]:
    """Apply worktree.json setup + post-worktree.sh. Returns log of actions.

    `preserve_existing` is for re-running setup on a worktree that already
    holds work (the resume path). Freshly created worktrees contain only what
    `git worktree add` checked out, so replacing an entry there is safe; a
    live worktree may hold hours of edits under exactly those names, and
    `shared_dirs` deletes what it replaces, `copy_files` overwrites it, and
    `venv_setup: uv` rewrites `.envrc`. With `preserve_existing`, every one of
    those three is left alone when it already exists, and logged instead —
    setup never destroys work it did not create. (Nothing else in here writes
    into the worktree; the only other write is the ownership marker inside the
    venv this hook created.)
    """
    actions: list[str] = []
    cfg = load_config(base)

    for name in cfg.get("shared_dirs", []):
        name = _safe_rel_name(name, "shared_dirs")
        src = base / name
        if not src.is_dir():
            actions.append(f"shared_dirs: skip {name} (missing in main checkout)")
            continue
        dst = _dst_in_worktree(worktree, name, "shared_dirs")
        if preserve_existing and (dst.is_symlink() or dst.exists()):
            if dst.is_symlink() and _points_at(dst, src):
                actions.append(f"shared_dirs: {name} already linked -> {src}")
            else:
                actions.append(
                    f"shared_dirs: KEEP {name} (already exists in the worktree; "
                    "resume does not replace it)"
                )
            continue
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
        if preserve_existing and (dst.is_symlink() or dst.exists()):
            actions.append(
                f"copy_files: KEEP {name} (already in the worktree; resume does "
                "not overwrite it)"
            )
            continue
        if dst.is_symlink():
            dst.unlink()  # never write through a pre-existing symlink
        shutil.copy2(src, dst)
        if not dst.is_file():
            raise SetupError(f"copy_files: failed to copy {name}")
        actions.append(f"copy_files: {name}")

    venv_setup = cfg.get("venv_setup", "none")
    if venv_setup == "uv":
        envrc = worktree / ".envrc"
        # .envrc is generated, but people extend it (extra exports, `use
        # flake`, dotenv). On resume it counts as existing work like anything
        # else — keep it. uv sync below passes UV_PROJECT_ENVIRONMENT
        # explicitly, so the venv lands in the right place either way; only
        # direnv's shell integration depends on the file's contents.
        if preserve_existing and (envrc.is_file() or envrc.is_symlink()):
            if ENVRC_EXPORT in _read_text_or_empty(envrc):
                actions.append("venv_setup=uv: .envrc already configured (kept)")
            else:
                actions.append(
                    "venv_setup=uv: KEEP .envrc (already in the worktree; resume "
                    "does not overwrite it) — it does not export "
                    f"UV_PROJECT_ENVIRONMENT; add `{ENVRC_EXPORT}` if you want "
                    "direnv to key the venv per worktree"
                )
        else:
            if envrc.is_symlink():
                envrc.unlink()  # never write through a pre-existing symlink
            envrc.write_text(ENVRC_EXPORT + "\n")
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


SLUG_RE = re.compile(r"^[A-Za-z0-9_+][A-Za-z0-9._+-]*$")


def slug_from_name(name: object) -> str:
    """Normalise Claude Code's suggested worktree `name` into a safe slug.

    `/` becomes `+` (Claude Code's own spelling for a slash in a worktree
    name). Anything that could escape a directory, be read as a git option, or
    confuse a shell is refused outright rather than sanitised into something
    the caller did not ask for.
    """
    if not isinstance(name, str):
        raise SetupError(f"name: expected a string, got {name!r}")
    slug = name.strip().replace("/", "+")
    if not SLUG_RE.match(slug):
        raise SetupError(
            f"name: {name!r} is not a usable worktree slug "
            "(allowed: letters, digits, . _ + -; must not start with '-' or '.')"
        )
    return slug


def resolve_repo_root(cwd: str) -> Path:
    """Main checkout for a `name`-only payload: the git root containing cwd."""
    if not cwd:
        raise SetupError("cwd missing from payload — cannot locate the repository")
    proc = subprocess.run(
        ["git", "-C", cwd, "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        raise SetupError(
            f"cwd {cwd} is not inside a git repository "
            f"({proc.stderr.strip() or 'no toplevel'})"
        )
    return Path(proc.stdout.strip())


def plan_from_slug(base: Path, slug: str) -> tuple[Path, str]:
    """(worktree_path, branch) for a slug, honouring .claude/worktree.json.

    Defaults mirror Claude Code's built-in convention — `<repo>/.claude/
    worktrees/<slug>` on branch `worktree-<slug>` — so a repo without config
    gets the same layout whether or not this hook is installed.
    """
    cfg = load_config(base)

    template = cfg.get("base_path")
    if isinstance(template, str) and template.strip():
        expanded = template.replace("{project}", base.name).replace("{slug}", slug)
        expanded = os.path.expandvars(os.path.expanduser(expanded))
        worktree = Path(os.path.normpath(expanded))
        if not worktree.is_absolute():
            worktree = Path(os.path.normpath(base / worktree))
    else:
        worktree = base / ".claude" / "worktrees" / slug

    pattern = cfg.get("branch_pattern")
    if isinstance(pattern, str) and pattern.strip():
        wt_type = cfg.get("default_type") or "feat"
        branch = pattern.replace("{type}", str(wt_type)).replace("{slug}", slug)
    else:
        branch = f"worktree-{slug}"
    if not branch.strip() or branch.startswith("-"):
        raise SetupError(f"branch_pattern produced an unusable branch name {branch!r}")
    return worktree, branch


def is_registered_worktree(base: Path, worktree: Path) -> bool:
    """True if `worktree` is already a worktree of the repo at `base`."""
    proc = subprocess.run(
        ["git", "-C", str(base), "worktree", "list", "--porcelain"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return False
    # git records the realpath, so compare realpaths — otherwise a symlinked
    # parent (e.g. /tmp on macOS) makes a resume look like a fresh create.
    target = os.path.realpath(worktree)
    for line in proc.stdout.splitlines():
        if line.startswith("worktree ") and (
            os.path.realpath(line[len("worktree ") :]) == target
        ):
            return True
    return False


def git_worktree_add(base: Path, worktree: Path, branch: str) -> None:
    """Create the worktree: new branch first, else check out the existing one."""
    new = subprocess.run(
        ["git", "-C", str(base), "worktree", "add", str(worktree), "-b", branch],
        capture_output=True,
        text=True,
    )
    if new.returncode == 0:
        return
    existing = subprocess.run(
        ["git", "-C", str(base), "worktree", "add", str(worktree), branch],
        capture_output=True,
        text=True,
    )
    if existing.returncode != 0:
        raise SetupError(
            "git worktree add failed.\n"
            f"-b attempt: {new.stderr.strip()}\n"
            f"existing-branch attempt: {existing.stderr.strip()}"
        )


def unrecognised_payload_report(payload: dict) -> str:
    """Diagnostic for a payload matching no known shape.

    The hook deliberately exits 0 here (see hook_main), so this text is the
    only trace it leaves. It must therefore say what arrived, what would have
    been understood, what was done, and what happens next — a hook that does
    nothing quietly is indistinguishable from a hook that is broken.
    """
    keys = ", ".join(sorted(map(str, payload))) or "(none)"
    return "\n".join(
        [
            "WorktreeCreate hook: unrecognised payload — DID NOTHING (exit 0).",
            f"  received keys: {keys}",
            f"  received event: {payload.get('hook_event_name', '(absent)')!r}",
            "  recognised shapes:",
            "    1. {name, cwd, ...}  — what Claude Code sends (--worktree, "
            "/worktree, agent isolation); the hook picks the path and creates "
            "the worktree",
            "    2. {worktree_path, branch_name, base_path} — an explicit "
            "instruction to create exactly that worktree",
            "  no worktree was created and no setup ran, because neither "
            "shape was present.",
            "  exiting 0 on purpose: failing here would block worktree "
            "creation over a payload this hook simply does not know "
            "(the TOM-358 regression). Claude Code raises its own "
            '"returned no worktree path" error when nothing is printed to '
            "stdout, so the real failure surfaces there rather than being "
            "masked by this hook's exit code.",
            "  if this is a payload shape Claude Code now sends, teach the "
            "hook about it (hooks/worktree_create.py, hook_main).",
            f"  payload: {json.dumps(payload)[:500]}",
        ]
    )


def hook_main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"WorktreeCreate hook: invalid JSON input: {exc}", file=sys.stderr)
        return 1
    if not isinstance(payload, dict):
        print(
            f"WorktreeCreate hook: expected a JSON object, got {type(payload).__name__}"
            " — nothing to do, exiting 0",
            file=sys.stderr,
        )
        return 0

    worktree_path = payload.get("worktree_path", "")
    branch_name = payload.get("branch_name", "")
    base_path = payload.get("base_path", "")
    name = payload.get("name", "")

    if worktree_path and branch_name and base_path:
        # Explicit shape: caller dictates path, branch and main checkout.
        base = Path(base_path)
        worktree = Path(worktree_path)
        resume = False
    elif name:
        # Claude Code's own shape (`--worktree`, `/worktree`, agent isolation):
        # a suggested slug plus the session envelope. We choose path + branch
        # and locate the repository from cwd.
        try:
            slug = slug_from_name(name)
            base = resolve_repo_root(payload.get("cwd", ""))
            worktree, branch_name = plan_from_slug(base, slug)
        except SetupError as exc:
            print(f"WorktreeCreate hook: cannot plan worktree: {exc}", file=sys.stderr)
            return 1
        resume = is_registered_worktree(base, worktree)
        print(
            f"WorktreeCreate hook: name={name!r} -> "
            f"{'resuming' if resume else 'creating'} {worktree} "
            f"(branch {branch_name}, base {base})",
            file=sys.stderr,
        )
    elif worktree_path or branch_name or base_path:
        # A partial explicit payload is a caller bug, not an unknown shape:
        # say exactly what is missing instead of pretending we handled it.
        print(
            "WorktreeCreate hook: missing worktree_path/branch_name/base_path "
            f"in input: {json.dumps(payload)[:500]}",
            file=sys.stderr,
        )
        return 1
    else:
        # Neither shape. Exit 0 — failing closed on a payload we don't
        # understand is the bug this branch exists to prevent (TOM-358) — but
        # say everything a reader needs, because doing nothing quietly is its
        # own failure mode.
        print(unrecognised_payload_report(payload), file=sys.stderr)
        return 0

    try:
        if not resume:
            git_worktree_add(base, worktree, branch_name)
        actions = setup_worktree(worktree, base, preserve_existing=resume)
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
    parser.add_argument(
        "--preserve-existing",
        action="store_true",
        help=(
            "re-running on a worktree that already holds work: leave any "
            "shared_dirs/copy_files entry that already exists in place "
            "instead of replacing it"
        ),
    )
    args = parser.parse_args(argv)
    worktree = Path(args.setup).resolve()
    base = Path(args.base).resolve()
    if not worktree.is_dir():
        print(f"setup: worktree {worktree} is not a directory", file=sys.stderr)
        return 1
    try:
        actions = setup_worktree(
            worktree, base, preserve_existing=args.preserve_existing
        )
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

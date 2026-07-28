#!/usr/bin/env python3
"""
PreToolUse hook (matcher: Bash) — agent-side branch-workflow guard.

The deterministic stand-in for GitHub branch protection, for repos where
protection is unavailable (private repos on the Free plan). It blocks exactly
one class of mistake: a direct `git commit` / `git push` to a branch that work
is supposed to reach through a pull request.

Two branches are protected:

  - `protected_branch` — the release branch (default `main`).
  - `integration_branch` — where feature PRs land first (default `dev`, but
    only when `origin/dev` actually exists in that repo).

The integration branch is guarded for the same reason as the protected one:
that is where the review gate lives. Work reaches it via a PR; a direct commit
opens no PR, so it runs neither review nor CI.

The guard never returns `permissionDecision: "ask"` and never inspects
`permission_mode`. A hook that asks renders an interactive confirmation, and in
a BACKGROUNDED agent session that stalls the worker at `waiting/blocked` until a
human attaches — and the payload cannot distinguish that case from a headless
run that would block cleanly (both report `permission_mode: "auto"`). So the
decision is always allow or deny, and the escape hatch is the visible,
deliberate guard toggle: `/guard git-workflow off`.

It does NOT lint/format (git pre-commit hooks already do that) and it does NOT
touch normal feature-branch work.

Documented gaps (deliberate — these are explicit acts, not the accidental
footgun this guards, and catching them would risk false blocks):
  - `git checkout main && git commit ...` in one line — the hook reads the
    *current* branch, so a switch-then-act chain is not caught.
  - `git push --all` / `git push --mirror` from an unguarded branch — only
    caught when standing on a guarded branch.

Opt-in: `.claude/git-guard.json` in the TARGET repo root. The PRESENCE of that
file is what opts a repo in — no file means a total no-op for that repo, which
is what keeps the guard out of scratch repos and third-party clones. Every
field is optional:

    {
      "protected_branch": "main",       // default "main"
      "integration_branch": "dev",      // default "dev" iff origin/dev exists;
                                        // explicit null = this repo has none
      "release_tool": "commitizen (/ship)"   // guidance text only
    }

A repo that wants the house defaults can commit `{}`.

Toggle with `/guard git-workflow on|off` (persists to ~/.claude/qute-guards.json).

Contract (per Claude Code hook docs):
  - stdin: JSON with `tool_name`, `tool_input.command`, `cwd`
  - block: exit 0 with JSON
        {"hookSpecificOutput": {"hookEventName": "PreToolUse",
          "permissionDecision": "deny", "permissionDecisionReason": "...",
          "additionalContext": "..."}}
  - allow: exit 0 with `{}`
  - any internal error: exit 0, allow (fail-open — a guard bug must never
    wedge the agent's git access)
"""

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from guard_config import guard_enabled  # noqa: E402

GUARD_NAME = "git-workflow"

DEFAULT_PROTECTED = "main"
DEFAULT_INTEGRATION = "dev"


def is_enabled() -> bool:
    """Whether the branch-workflow guard is enabled (local guard: fails open)."""
    return guard_enabled(GUARD_NAME)


def _allow():
    """Emit the empty decision — falls through to the normal permission flow."""
    print("{}")
    sys.exit(0)


def _deny(reason: str, guidance: str):
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                    "additionalContext": guidance,
                }
            }
        )
    )
    sys.exit(0)


def _base_dir(hook_input: dict) -> Path:
    """Directory the Bash command starts in: the payload's cwd when present,
    else the project dir, else this process's cwd."""
    for candidate in (hook_input.get("cwd"), os.environ.get("CLAUDE_PROJECT_DIR")):
        if candidate:
            return Path(candidate)
    return Path.cwd()


def _git(cwd: Path, *args: str):
    """Run a read-only git query in `cwd`; return stdout or None on any failure."""
    try:
        out = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            cwd=str(cwd),
            timeout=5,
        )
    except Exception:
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip()


def _repo_root(cwd: Path):
    """Toplevel of the git repo that `cwd` belongs to, or None."""
    top = _git(cwd, "rev-parse", "--show-toplevel")
    return Path(top) if top else None


def _remote_branch_exists(repo_root: Path, branch: str) -> bool:
    return (
        _git(
            repo_root,
            "rev-parse",
            "--verify",
            "--quiet",
            f"refs/remotes/origin/{branch}",
        )
        is not None
    )


def _load_config(repo_root: Path):
    """Resolved guard config for `repo_root`, or None if the repo isn't opted in.

    Opt-in is the PRESENCE of `.claude/git-guard.json`. Fields are optional and
    fall back to house defaults; an unreadable or malformed file is treated as
    "no config" (fail open) rather than as an error.
    """
    cfg_path = repo_root / ".claude" / "git-guard.json"
    if not cfg_path.is_file():
        return None
    try:
        raw = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(raw, dict):
        return None

    protected = raw.get("protected_branch") or DEFAULT_PROTECTED

    if "integration_branch" in raw:
        # An explicit null means "this repo genuinely has no integration
        # branch" — the default must not resurrect one.
        integration = raw["integration_branch"] or None
    else:
        integration = (
            DEFAULT_INTEGRATION
            if _remote_branch_exists(repo_root, DEFAULT_INTEGRATION)
            else None
        )
    if integration == protected:
        integration = None

    return {
        "protected": protected,
        "integration": integration,
        "release_tool": raw.get("release_tool"),
    }


def _current_branch(cwd: Path):
    branch = _git(cwd, "rev-parse", "--abbrev-ref", "HEAD")
    # Detached HEAD reports "HEAD" — not on a named branch, nothing to guard.
    return branch if branch and branch != "HEAD" else None


# Split a shell line into the individual commands joined by &&, ||, ;, | (and
# newlines). Crude but sufficient: we only need to find git commit/push verbs.
_SEP = re.compile(r"&&|\|\||;|\n|\|")


def _segments(command: str):
    return [s.strip() for s in _SEP.split(command) if s.strip()]


def _tokens(segment: str):
    try:
        return shlex.split(segment)
    except ValueError:
        return segment.split()


def _git_subcommand(tokens):
    """Return (subcommand, args_after_it, global_opts) if this segment is a git
    invocation, else (None, [], {}).

    `global_opts` captures the path-scoping options that decide WHICH repo the
    git command targets: `-C <path>` (repeatable, cumulative), `--git-dir`,
    `--work-tree`. Used to resolve the target repo per-command so the guard
    evaluates the right repo's branch/config instead of the session's.
    """
    empty = (None, [], {})
    if not tokens:
        return empty
    # Skip leading inline env-var assignments (`FOO=1 git push ...`). Note an
    # inline `CLAUDE_GUARD_GIT_WORKFLOW=0 git ...` does NOT override this hook —
    # the hook runs as a separate process and only sees exported env.
    while tokens and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", tokens[0]):
        tokens = tokens[1:]
    if not tokens or tokens[0] != "git":
        return empty
    i = 1
    c_paths = []
    git_dir = None
    work_tree = None
    # Parse global git options like `-C path`, `-c key=val`, `--git-dir[=]...`.
    while i < len(tokens) and tokens[i].startswith("-"):
        tok = tokens[i]
        if tok in ("-C", "-c", "--git-dir", "--work-tree"):
            val = tokens[i + 1] if i + 1 < len(tokens) else None
            if tok == "-C" and val is not None:
                c_paths.append(val)
            elif tok == "--git-dir" and val is not None:
                git_dir = val
            elif tok == "--work-tree" and val is not None:
                work_tree = val
            i += 2
        elif tok.startswith("--git-dir="):
            git_dir = tok.split("=", 1)[1]
            i += 1
        elif tok.startswith("--work-tree="):
            work_tree = tok.split("=", 1)[1]
            i += 1
        else:
            i += 1
    if i >= len(tokens):
        return empty
    opts = {"C": c_paths, "git_dir": git_dir, "work_tree": work_tree}
    return tokens[i], tokens[i + 1 :], opts


def _cd_target(tokens):
    """If a segment is `cd <path>`, return the path, else None. A bare `cd`
    (home) or `cd -` is ignored — we only track explicit relative/absolute
    directory changes that could point git at a sibling repo."""
    if len(tokens) >= 2 and tokens[0] == "cd":
        target = tokens[1]
        if target and target != "-" and not target.startswith("-"):
            return target
        return None
    return None


def _resolve_git_target_dir(base: Path, opts: dict) -> Path:
    """The effective directory the git command operates in, applying `cd` base
    plus git's own path-scoping options. `-C` paths are cumulative and resolved
    relative to the running dir (git's documented behaviour); `--work-tree` and
    `--git-dir` fall back in that order when no `-C` is present."""
    d = base
    for p in opts.get("C") or []:
        pp = Path(p)
        d = pp if pp.is_absolute() else (d / pp)
    if not (opts.get("C")):
        alt = opts.get("work_tree") or opts.get("git_dir")
        if alt:
            ap = Path(alt)
            # A --git-dir of `<repo>/.git` -> the repo root is its parent.
            if opts.get("work_tree") is None and ap.name == ".git":
                ap = ap.parent
            d = ap if ap.is_absolute() else (base / ap)
    return d


def _strip_ref(name: str) -> str:
    # Drop the force-push sigil (`+main`) and the fully-qualified prefix so
    # `+refs/heads/main` and `main` compare equal to the protected name.
    return name.lstrip("+").replace("refs/heads/", "")


def _push_targets(args):
    """
    Destination branch names for a `git push` invocation.
    Returns (targets, had_explicit_refspec).
    """
    positionals = [a for a in args if not a.startswith("-")]
    # First positional is the remote; the rest are refspecs.
    refspecs = positionals[1:] if len(positionals) >= 1 else []
    targets = []
    for ref in refspecs:
        # src:dst -> dst is the destination branch; bare ref -> same name.
        dst = ref.split(":", 1)[1] if ":" in ref else ref
        targets.append(_strip_ref(dst))
    return targets, len(refspecs) > 0


def _guidance(cfg: dict) -> str:
    protected = cfg["protected"]
    integration = cfg["integration"]
    release_tool = cfg["release_tool"]
    if integration:
        route = (
            f"'{protected}' and '{integration}' are guarded branches in this repo: work "
            f"reaches them through a pull request, never a direct commit or push. A direct "
            f"commit opens no PR, so it runs neither review nor CI. "
            f"Route: git switch -c feat/<slug> off '{integration}', commit there, push the "
            f"feature branch, and open a PR into '{integration}'. "
            f"'{integration}' -> '{protected}' goes through the release flow"
            + (f" ({release_tool})" if release_tool else "")
            + "."
        )
    else:
        route = (
            f"'{protected}' is the protected branch in this repo: work reaches it through a "
            f"pull request, never a direct commit or push. A direct commit opens no PR, so it "
            f"runs neither review nor CI. "
            f"Route: git switch -c feat/<slug>, commit there, push the feature branch, and "
            f"open a PR into '{protected}'"
            + (f". Releases go through {release_tool}" if release_tool else "")
            + "."
        )
    return (
        route + " Deliberate override (visible and reversible): run "
        "`/guard git-workflow off`, do the work, then `/guard git-workflow on`."
    )


def main():
    if not is_enabled():
        _allow()

    try:
        hook_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError, ValueError):
        _allow()

    if not isinstance(hook_input, dict) or hook_input.get("tool_name") != "Bash":
        _allow()

    command = (hook_input.get("tool_input") or {}).get("command", "")
    if not command or "git" not in command:
        _allow()

    # Base dir the command runs in. `cd` segments earlier in the same chained
    # command shift this; each git command is then scoped to its OWN target repo
    # (via `cd` and/or `-C`/`--git-dir`), so a sibling-repo op is evaluated
    # against the SIBLING repo's branch + config — not the session's repo.
    base_dir = _base_dir(hook_input)

    # Per-target-repo config cache: repo-root -> cfg (or None). Avoids re-reading
    # config / re-shelling rev-parse for repeated ops on the same repo.
    cfg_cache: dict = {}

    for seg in _segments(command):
        tokens = _tokens(seg)

        # Track `cd` so a subsequent git command in the same chain resolves
        # against the directory the shell actually moved into.
        cd_to = _cd_target(tokens)
        if cd_to is not None:
            p = Path(cd_to)
            base_dir = p if p.is_absolute() else (base_dir / p)
            continue

        sub, args, opts = _git_subcommand(tokens)
        if sub not in ("commit", "push"):
            continue

        # Resolve the repo this specific git command targets, then load THAT
        # repo's guard config and current branch.
        target_dir = _resolve_git_target_dir(base_dir, opts)
        repo_root = _repo_root(target_dir)
        if repo_root is None:
            continue  # not a git repo we can resolve -> nothing to guard
        key = str(repo_root)
        if key not in cfg_cache:
            cfg_cache[key] = _load_config(repo_root)
        cfg = cfg_cache[key]
        if cfg is None:
            continue  # target repo not opted in -> no-op for it

        protected = cfg["protected"]
        integration = cfg["integration"]
        branch = _current_branch(target_dir)
        guidance = _guidance(cfg)

        if sub == "commit":
            if branch == protected:
                _deny(
                    f"Blocked: direct commit on protected branch '{protected}'.",
                    guidance,
                )
            if integration and branch == integration:
                _deny(
                    f"Blocked: direct commit on integration branch '{integration}'.",
                    guidance,
                )

        elif sub == "push":
            targets, had_refspec = _push_targets(args)
            if protected in targets:
                _deny(
                    f"Blocked: push to protected branch '{protected}'.",
                    guidance,
                )
            if integration and integration in targets:
                _deny(
                    f"Blocked: push to integration branch '{integration}'.",
                    guidance,
                )
            # No explicit refspec -> pushes the current branch. If that's a
            # guarded branch, it's a direct push to it.
            if not had_refspec:
                if branch == protected:
                    _deny(
                        f"Blocked: push of current branch '{protected}' (the protected branch).",
                        guidance,
                    )
                if integration and branch == integration:
                    _deny(
                        f"Blocked: push of current branch '{integration}' (the integration branch).",
                        guidance,
                    )

    _allow()


if __name__ == "__main__":
    # Belt-and-suspenders fail-open: an unforeseen error must never wedge git.
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        print("{}")
        sys.exit(0)

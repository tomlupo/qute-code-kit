#!/usr/bin/env python3
"""
PreToolUse hook (matcher: Bash) — agent-side branch-workflow SPEED BUMP.

A best-effort, agent-side nudge for repos where GitHub branch protection is
unavailable (private repos on the Free plan). It aims at exactly one class of
mistake: a direct `git commit` / `git push` to a branch that work is supposed
to reach through a pull request.

It is NOT enforcement, and it is not a stand-in for branch protection. Read
"WHAT THIS IS, AND WHAT IT IS NOT" below before trusting it with anything.

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

Push destinations are resolved, not string-matched: `HEAD` and `@` (bare or on
the source side of a refspec) resolve to the current branch, a `+` force sigil
and a `refs/heads/` prefix are stripped, and only the dst half of `src:dst`
counts. A destination that cannot be resolved confidently is DENIED rather than
allowed — see `_resolve_push_dst` for the exact list of unresolvable shapes.

Git is recognised by the BASENAME of the executable, so `/usr/bin/git` counts,
and the `env` / `command` / `builtin` / `exec` wrappers are peeled first
(`env FOO=1 git push`, `command git commit`). An unrecognised subcommand is
resolved ONE level as an alias — from `-c alias.<name>=<expansion>` on the
command line first, then `git config --get alias.<name>` in the TARGET repo.
All of it fails closed: a wrapper or an alias whose meaning cannot be pinned
down is denied, not allowed. See `_strip_env`, `_strip_run_wrapper`,
`_is_git_executable` and `_expand_alias`.


WHAT THIS COVERS — AND THE LINE THAT DECIDES IT
===============================================

The target is ORDINARY INVOCATION FORMS: what a person or an agent actually
types or scripts. Within that target the guard is meant to be correct, and a
miss is a DEFECT.

It is NOT, and cannot be, resistant to DELIBERATELY CONSTRUCTED EVASION. It
reads a shell string, and git's command-line surface is unbounded; no amount of
parsing closes that. That distinction is the line, and a new finding can be
placed on one side of it without asking anyone:

  IN SCOPE — a shape someone would plausibly write without trying to evade
  anything. `/usr/bin/git commit`, `env VAR=x git commit`, `command git push`,
  a `git ci` alias, `git push origin HEAD`, an option whose arity shifts the
  positionals. These are defects: fix them.

  OUT OF SCOPE — a shape that only occurs when someone is routing around the
  guard on purpose. Anyone doing that also has `--no-verify`, git behind a
  shell variable or a here-doc, a wrapper script, or simply their own terminal.
  Hardening the parser against them buys nothing, and `pre-push` is the layer
  that answers them.

So this is a SPEED BUMP, not enforcement — but with a criterion, not a shrug.

Two limits are structural rather than parsing bugs, and neither has a fix in
this file:

  * It observes CLAUDE TOOL CALLS ONLY. A human typing in their own terminal, a
    Makefile target, a CI job, or any script an agent launches that shells out
    to git internally are all invisible to it — no PreToolUse hook ever sees
    them.

  * Its knowledge of git's option arity is a table, and git's surface grows. A
    FUTURE value-taking `git push` option we do not know about would shift the
    positionals the way `--recurse-submodules` did. `_git_subcommand` carries a
    backstop for the GLOBAL-option case (an unknown global plus an
    unidentifiable subcommand denies); the push-option case has none, because
    the only available backstop — re-arming the current-branch fallback
    whenever an unknown option appears — would false-block ordinary pushes of
    an unguarded refspec from a guarded branch.

Shapes review has found, ALL now handled — kept as evidence the tail is real,
not as a checklist that is now complete:

   1. bare `HEAD` — compared as the literal "HEAD", never equal to "main";
   2. refspecs whose destination could not be resolved were allowed, not denied;
   3. `--repo <remote>` supplies the remote, so every positional is a refspec —
      `git push --repo=origin main` parsed as "no refspec at all";
   4. the `env` wrapper — `env GIT_AUTHOR_NAME=x git commit`, bare
      `env git push origin main`;
   5. git aliases — `git ci`, `git publish`, neither the literal `commit` nor
      the literal `push`;
   6. push-option arity — `git push --recurse-submodules on-demand origin` read
      `on-demand` as the remote and `origin` as a harmless explicit refspec;
   7. global-option arity — `git --namespace foo commit -m x` read `foo` as the
      subcommand;
   8. the executable form — `/usr/bin/git commit`, `command git commit`, which
      only `tokens[0] == "git"` had ever matched;
   9. `-c alias.ci=commit` — an alias defined on the command line, invisible to
      a repo-config lookup.

`pre-push` IS THE ACTUAL ENFORCEMENT LAYER (TOM-348, being built in parallel).
Git invokes `pre-push` with the real local/remote refs it is about to send —
after alias expansion, after `env`, after every shell trick, and regardless of
who or what ran the command. So it needs no command-line parser, none of the
shapes above exist at that layer, and a human's own push is covered too.

The two are COMPLEMENTARY, not redundant. This hook gives an agent IMMEDIATE
FEEDBACK and a message naming the right route before the command ever runs;
`pre-push` is what HOLDS. Anyone tempted to harden this parser against the
out-of-scope side of the line should land TOM-348 instead.

Documented gaps (deliberate — these are explicit acts, not the accidental
footgun this guards, and catching them would risk false blocks):
  - `git checkout main && git commit ...` in one line — the hook reads the
    *current* branch, so a switch-then-act chain is not caught.
  - `git push --all` / `git push --mirror` from an unguarded branch — only
    caught when standing on a guarded branch.
  - anything that reaches git without going through the Bash tool.

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
from pathlib import Path, PurePosixPath

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


_ASSIGN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*")

# Sentinel subcommands for "this segment invokes something we could not pin
# down". Both are NUL-prefixed so they can never collide with a real git
# subcommand or alias name. The caller denies on them when the repo is opted in.
_WRAPPER_UNRESOLVABLE = "\0wrapper-unresolvable"
_ALIAS_UNRESOLVABLE = "\0alias-unresolvable"

# `env` long options that never take a value, or whose value can only ever be
# attached with `=` (so a bare occurrence consumes nothing).
_ENV_LONG_FLAGS = frozenset(
    {
        "--ignore-environment",
        "--null",
        "--debug",
        "--list-signal-handling",
        "--block-signal",
        "--default-signal",
        "--ignore-signal",
    }
)
# `env` long options that take a value, either `--opt=v` or `--opt v`.
_ENV_LONG_WITH_VALUE = frozenset({"--unset", "--chdir"})


def _strip_env(tokens):
    """Consume a leading `env` invocation, returning (rest_tokens, chdirs), or
    None when the wrapper cannot be resolved.

    `env [OPTION]... [-] [NAME=VALUE]... [COMMAND [ARG]...]` — the command we
    care about hides after the options and the assignments, so `env
    GIT_AUTHOR_NAME=x git commit` and bare `env git push origin main` both have
    to be unwrapped before anything can look for `git`. (Bypass #4.)

    Options are handled to the extent they can be:
      `-i` / `--ignore-environment` / `-` / `-v` / `-0`  no effect on WHICH
          command runs — skipped.
      `-u NAME` / `--unset=NAME`  consumes its value — skipped.
      `-C dir` / `--chdir=dir`  changes the directory git runs in, so it is
          returned and applied to the target-repo resolution exactly like git's
          own `-C`.

    Anything else returns None -> the caller treats the segment as GUARDED, not
    allowed. The notable member of that set is `-S` / `--split-string`, which
    re-splits a whole command line out of one string with its own quoting and
    `\\c` escapes; re-implementing that is precisely the unbounded-parser trap
    this guard's docstring warns about. Unknown options land there too, since a
    new option could consume the token we would otherwise read as `git`.
    """
    tokens = tokens[1:]  # drop `env` itself
    chdirs = []
    i, n = 0, len(tokens)
    while i < n:
        tok = tokens[i]
        if tok == "-":  # bare `-` is a synonym for `-i`
            i += 1
            continue
        if not tok.startswith("-"):
            break  # first non-option: assignments or the command itself
        if tok.startswith("--"):
            name, eq, attached = tok.partition("=")
            if name in _ENV_LONG_FLAGS:
                i += 1
            elif name in _ENV_LONG_WITH_VALUE:
                if eq:
                    value, step = attached, 1
                elif i + 1 < n:
                    value, step = tokens[i + 1], 2
                else:
                    return None
                if name == "--chdir":
                    chdirs.append(value)
                i += step
            else:
                return None
            continue
        # Short-option cluster: `-i`, `-iu FOO`, `-uFOO`, `-C dir`.
        j, step = 1, 1
        while j < len(tok):
            c = tok[j]
            if c in "iv0":
                j += 1
                continue
            if c not in "uCS":
                return None  # unknown short option — it may eat the command
            if c == "S":
                return None  # --split-string: see the docstring
            attached = tok[j + 1 :]
            if attached:
                value = attached
            elif i + 1 < n:
                value, step = tokens[i + 1], 2
            else:
                return None
            if c == "C":
                chdirs.append(value)
            break
        i += step
    return tokens[i:], chdirs


# Shell prefixes that mean "run the following command": `command git push`,
# `exec git commit` (both ordinary in scripts), `builtin`. Matched literally —
# unlike `env` these are shell builtins and never appear as a path.
_RUN_WRAPPERS = frozenset({"command", "builtin", "exec"})
# Their value-less options (`command -p`, `exec -c`/`-l`) and the one that takes
# a value (`exec -a NAME`). Anything else is unresolvable -> guarded.
_WRAPPER_FLAGS = frozenset({"-p", "-v", "-V", "-c", "-l"})
_WRAPPER_WITH_VALUE = frozenset({"-a"})


def _strip_run_wrapper(tokens):
    """Consume a leading `command` / `builtin` / `exec` prefix, returning the
    remaining tokens, or None when its options cannot be resolved."""
    tokens = tokens[1:]
    i, n = 0, len(tokens)
    while i < n:
        tok = tokens[i]
        if tok == "--":
            i += 1
            break
        if not tok.startswith("-") or tok == "-":
            break
        if tok in _WRAPPER_FLAGS:
            i += 1
        elif tok in _WRAPPER_WITH_VALUE:
            if i + 1 >= n:
                return None
            i += 2
        else:
            return None  # unknown option — it may swallow the command token
    return tokens[i:]


def _is_git_executable(token: str) -> bool:
    """Whether this token invokes git.

    Matched on the BASENAME, so `/usr/bin/git` and `./git` count. Absolute paths
    to git are ordinary — scripts and cron entries use them constantly — and
    `tokens[0] == "git"` missed every one of them. `git-foo`, `gitk` and the
    like have a different basename and are correctly excluded.
    """
    return PurePosixPath(token).name == "git"


# Git GLOBAL options (before the subcommand) that consume the FOLLOWING token.
# Without the arity the value gets read as the subcommand and the real one
# shifts into the args — `git --namespace foo commit -m x` parsed as subcommand
# `foo`. `--exec-path` is deliberately ABSENT: bare `--exec-path` prints the
# path and exits, so it never takes a separate value.
_GIT_GLOBAL_WITH_VALUE = frozenset(
    {
        "-C",
        "-c",
        "--git-dir",
        "--work-tree",
        "--namespace",
        "--super-prefix",
        "--attr-source",
        "--config-env",
    }
)

# `-c alias.<name>=<expansion>` defines an alias for THIS invocation only.
_CLI_ALIAS_RE = re.compile(r"(?i)^alias\.([^=]+)=(.*)$", re.DOTALL)


def _git_subcommand(tokens):
    """Return (subcommand, args_after_it, global_opts) if this segment is a git
    invocation, else (None, [], {}).

    `global_opts` carries:
      `C` / `git_dir` / `work_tree` — the path-scoping options that decide WHICH
          repo the git command targets, so the guard evaluates that repo's
          branch and config instead of the session's;
      `aliases` — `-c alias.<name>=<expansion>` pairs, which define aliases for
          this invocation only and are therefore invisible to a repo-config
          lookup;
      `unknown_global` — whether an option we do not know the arity of was seen,
          which makes the token we read as the subcommand untrustworthy;
      `wrapper` — set only alongside `_WRAPPER_UNRESOLVABLE`.

    A subcommand of `_WRAPPER_UNRESOLVABLE` means the segment starts with an
    `env` / `command` / `exec` wrapper whose command could not be determined;
    `args` then holds the raw tokens so the caller can decide whether git is
    even in play.
    """
    empty = (None, [], {})
    if not tokens:
        return empty
    original = list(tokens)
    env_chdirs = []
    # Peel inline env-var assignments and run-wrappers, in any order and any
    # number: `FOO=1 git push`, `env FOO=1 git push`, `command git push`,
    # `FOO=1 env BAR=2 exec git push`. Note an inline
    # `CLAUDE_GUARD_GIT_WORKFLOW=0 git ...` does NOT override this hook — the
    # hook runs as a separate process and only sees exported env.
    while tokens:
        while tokens and _ASSIGN_RE.fullmatch(tokens[0]):
            tokens = tokens[1:]
        if not tokens:
            break
        head = tokens[0]
        if PurePosixPath(head).name == "env":
            stripped = _strip_env(tokens)
            if stripped is None:
                return (_WRAPPER_UNRESOLVABLE, original, {"wrapper": "env"})
            tokens, chdirs = stripped
            env_chdirs.extend(chdirs)
            continue
        if head in _RUN_WRAPPERS:
            stripped = _strip_run_wrapper(tokens)
            if stripped is None:
                return (_WRAPPER_UNRESOLVABLE, original, {"wrapper": head})
            tokens = stripped
            continue
        break
    if not tokens or not _is_git_executable(tokens[0]):
        return empty
    i = 1
    c_paths = []
    git_dir = None
    work_tree = None
    cli_aliases = {}
    unknown_global = False
    # Parse global git options like `-C path`, `-c key=val`, `--git-dir[=]...`.
    while i < len(tokens) and tokens[i].startswith("-"):
        tok = tokens[i]
        if tok in _GIT_GLOBAL_WITH_VALUE:
            val = tokens[i + 1] if i + 1 < len(tokens) else None
            if val is not None:
                if tok == "-C":
                    c_paths.append(val)
                elif tok == "--git-dir":
                    git_dir = val
                elif tok == "--work-tree":
                    work_tree = val
                elif tok == "-c":
                    m = _CLI_ALIAS_RE.match(val)
                    if m:
                        # git config variable names are case-insensitive.
                        cli_aliases[m.group(1).lower()] = m.group(2)
            i += 2
        elif tok.startswith("--git-dir="):
            git_dir = tok.split("=", 1)[1]
            i += 1
        elif tok.startswith("--work-tree="):
            work_tree = tok.split("=", 1)[1]
            i += 1
        else:
            # A value-less global (`-p`, `--literal-pathspecs`, `--bare`, …) —
            # or one whose arity we do not know, which would silently shift the
            # subcommand slot. Recorded rather than assumed either way; the
            # caller only acts on it if the subcommand turns out unidentifiable.
            unknown_global = True
            i += 1
    if i >= len(tokens):
        return empty
    # `env -C dir` happens BEFORE git starts, so it precedes git's own `-C`
    # chain in the cumulative resolution.
    opts = {
        "C": env_chdirs + c_paths,
        "git_dir": git_dir,
        "work_tree": work_tree,
        "aliases": cli_aliases,
        "unknown_global": unknown_global,
    }
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


# `git push` options that consume the FOLLOWING token as their value. Without
# this the value would be mistaken for the remote or a refspec and shift every
# positional by one (`git push -o ci.skip origin HEAD` is the live example, and
# `git push --recurse-submodules on-demand origin` is the same bug: `on-demand`
# read as the remote, `origin` read as a harmless refspec, so a push of the
# guarded current branch looked explicit and unguarded).
# `--repo` also consumes a value but is handled separately below, because it
# changes what the REMAINING positionals mean.
# Options whose value can ONLY be attached (`--force-with-lease=<ref>`,
# `--signed=<yes|no|if-asked>`) need no entry — they consume no extra token.
_PUSH_OPTS_WITH_VALUE = frozenset(
    {"-o", "--push-option", "--receive-pack", "--exec", "--recurse-submodules"}
)

# Bounded sweep for siblings of the `--repo` bug — options that change what the
# positionals MEAN (not merely options that take a value). What was found:
#
#   `--repo <r>` / `--repo=<r>`  CHANGES IT. The remote comes from the option,
#       so positional #0 is a refspec, not the remote. Handled below.
#   URL as the remote (`git push https://host/x.git main`)  no change — a URL
#       still occupies the remote slot; positional #0 is still the remote.
#   the deletion flag  no change — positionals keep their slots, and with it
#       the ref names a DESTINATION to remove, which is exactly how a bare
#       refspec is already read, so `origin main` denies today.
#   the all-tags flag  no change — pushes refs/tags IN ADDITION to any
#       refspec; slots untouched, and a tag dst is not a guarded branch.
#   the all-branches / mirror flags  no change to slots (positional #0 is
#       still the remote), but they push guarded branches with no refspec
#       naming them.
#       That is the pre-existing DOCUMENTED gap below, unchanged here: caught
#       only when standing on a guarded branch. It is a coverage hole, not a
#       parsing one, and `pre-push` (TOM-348) closes it for good.
_REPO_OPT = "--repo"
_REPO_OPT_EQ = "--repo="

# `HEAD` and `@` name whatever branch HEAD currently points at; git pushes them
# to that branch, so they must be resolved before comparing against a guarded
# branch name. This is the hole the original guard had: bare `HEAD` compared as
# the literal string "HEAD", which never equals `main`.
_HEAD_ALIASES = frozenset({"HEAD", "@"})

# Characters that mean "this destination is not a literal branch name we can
# resolve": shell expansion we never ran ($VAR, $(cmd), `cmd`), refspec globs
# (`refs/heads/*:refs/heads/*`), and git's ref-navigation syntax (`main^`,
# `HEAD~1`, `@{-1}`, `@{u}`). None of these can appear in a real branch name
# (git check-ref-format forbids `~ ^ ? * [`), so matching them cannot shadow a
# legitimate push.
_UNRESOLVABLE_RE = re.compile(r"[$`*?\[\]~^]|@\{")


def _resolve_push_dst(ref: str, current_branch):
    """The branch a single `git push` refspec would land on, or None if the
    destination cannot be determined confidently.

    Resolved shapes:
      ``main``                      -> ``main``
      ``+main`` / ``refs/heads/main``  -> ``main``   (force sigil, full ref)
      ``HEAD`` / ``@``              -> the current branch
      ``HEAD:topic`` / ``@:topic``  -> ``topic``     (only the dst side counts)
      ``src:refs/heads/main``       -> ``main``
      ``:main``                     -> ``main``      (branch deletion)

    DELIBERATELY treated as unresolvable (-> the caller denies, because a check
    that cannot verify must not report success):
      * anything holding shell/glob/ref-navigation syntax we do not expand —
        ``$BRANCH``, ``$(cmd)``, ``` `cmd` ```, ``refs/heads/*:refs/heads/*``,
        ``@{-1}``, ``HEAD~1``, ``main^``;
      * an empty destination (``main:``);
      * ``HEAD``/``@`` while the repo is on a detached HEAD — there is no
        branch name to compare against.
    """
    spec = ref.lstrip("+")
    dst = (spec.split(":", 1)[1] if ":" in spec else spec).strip()
    if not dst:
        return None
    if _UNRESOLVABLE_RE.search(dst):
        return None
    if dst.startswith("refs/heads/"):
        dst = dst[len("refs/heads/") :]
    if dst in _HEAD_ALIASES:
        # None here == detached HEAD == unresolvable, which is the answer we want.
        return current_branch
    return dst


def _push_targets(args, current_branch):
    """
    Destination branch names for a `git push` invocation.

    Returns (targets, had_explicit_refspec, unresolvable) — `targets` are the
    branch names the push would land on, and `unresolvable` holds the raw
    refspecs whose destination could not be pinned down.
    """
    positionals = []
    remote_from_opt = False
    skip_value = False
    for a in args:
        if skip_value:
            skip_value = False
            continue
        if a.startswith("-"):
            if a == _REPO_OPT:
                remote_from_opt = True
                skip_value = True
            elif a.startswith(_REPO_OPT_EQ):
                remote_from_opt = True
            elif a in _PUSH_OPTS_WITH_VALUE:
                skip_value = True
            continue
        positionals.append(a)

    if remote_from_opt:
        # `--repo` already named the remote, so EVERY positional is a refspec.
        # Git does ignore `--repo` when a positional repository is ALSO given,
        # and we cannot tell those two readings apart without knowing the
        # repo's remotes — so take the fail-closed union of both: treat all
        # positionals as refspecs, AND keep the current-branch fallback alive
        # unless a second positional proves the first one was the remote.
        refspecs = positionals
        had_refspec = len(positionals) > 1
    else:
        # First positional is the remote; the rest are refspecs.
        refspecs = positionals[1:]
        had_refspec = len(refspecs) > 0
    targets = []
    unresolvable = []
    for ref in refspecs:
        dst = _resolve_push_dst(ref, current_branch)
        if dst is None:
            unresolvable.append(ref)
        else:
            targets.append(dst)
    return targets, had_refspec, unresolvable


# Git subcommands that are definitely NOT `commit`/`push`. This list exists
# purely to keep `git config --get alias.<name>` OFF THE HOT PATH: an ordinary
# `git status` / `git log` short-circuits here with no subprocess at all. Git
# ignores any alias that shadows a builtin, so a name in this set can never be
# an alias — and the set being incomplete costs a config lookup, never
# correctness (an unlisted builtin simply resolves to "no such alias").
_GIT_BUILTINS = frozenset(
    """
    add am annotate apply archive bisect blame branch bundle cat-file
    check-ignore check-ref-format checkout cherry cherry-pick clean clone
    column config count-objects describe diff diff-tree difftool fetch
    filter-branch for-each-ref format-patch fsck gc grep help init instaweb
    log ls-files ls-remote ls-tree maintenance merge merge-base mergetool mv
    name-rev notes pack-refs prune pull range-diff rebase reflog remote repack
    replace request-pull rerere reset restore rev-list rev-parse revert rm
    shortlog show show-branch sparse-checkout stash status submodule switch
    symbolic-ref tag update-index update-ref var verify-commit version
    whatchanged worktree
    """.split()
)


def _mentions_git(tokens) -> bool:
    """Whether any token contains `git` at all — used ONLY to decide whether an
    unresolvable `env` segment is worth denying over.

    Deliberately a substring test, not a word-boundary one: in `env -Sgit\\ push`
    the option letter is glued to the command, so `\\bgit\\b` misses it. Erring
    toward "yes" is the correct direction on this path — the alternative is
    letting an env wrapper we admit we cannot parse through unexamined.
    """
    return any("git" in t for t in tokens)


def _expand_alias(target_dir: Path, name: str, cli_aliases: dict):
    """Resolve `git <name>` one level, preferring an alias defined ON THE
    COMMAND LINE (`-c alias.<name>=...`, which overrides and is invisible to a
    config lookup) and otherwise `git config --get alias.<name>` run IN THE
    TARGET REPO. Returns:

      None                      no such alias, or an alias that plainly expands
                                to a harmless builtin (`lg = log --graph`);
      (`commit`|`push`, args)   the alias expands to a guarded verb — the caller
                                re-parses `args + original args` under the
                                normal rules;
      (_ALIAS_UNRESOLVABLE, []) the expansion cannot be pinned down.

    Bypass #5: `git ci` / `git publish` are neither the literal `commit` nor the
    literal `push`, so they sailed straight past a check that only knew those
    two words.

    Resolution is DELIBERATELY ONE LEVEL. An alias that expands to another
    alias, or to a `!shell` command, is not chased: `!` expansions are arbitrary
    shell (they can pipe, chain, and re-invoke git through further aliases), and
    following an alias chain re-opens exactly the unbounded-parser problem this
    guard's docstring warns about. Both are therefore treated as GUARDED rather
    than resolved. That is a deliberate false-positive cost — a `!git status`
    alias in an opted-in repo is denied — and `/guard git-workflow off` is the
    escape hatch.
    """
    raw = cli_aliases.get(name.lower())
    if raw is None:
        raw = _git(target_dir, "config", "--get", f"alias.{name}")
    if not raw:
        return None
    raw = raw.strip()
    if raw.startswith("!"):
        return (_ALIAS_UNRESOLVABLE, [])
    try:
        parts = shlex.split(raw)
    except ValueError:
        return (_ALIAS_UNRESOLVABLE, [])
    if not parts:
        return None
    head = parts[0]
    if head in ("commit", "push"):
        return (head, parts[1:])
    if head in _GIT_BUILTINS:
        return None
    return (_ALIAS_UNRESOLVABLE, [])


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
        "`/guard git-workflow off`, do the work, then `/guard git-workflow on`. "
        "Note this guard is an agent-side speed bump, not enforcement. It "
        "targets ordinary invocation forms — what someone would actually type "
        "— and within those a miss is a defect worth reporting. But it sees "
        "Claude tool calls only (a human's own shell, and any script they run, "
        "are invisible to it) and it reads a command string, so it cannot "
        "resist deliberately constructed evasion. The `pre-push` hook "
        "(TOM-348) is the layer that actually holds; this one is here to tell "
        "you the route early."
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

    def _cfg_for(target_dir: Path):
        """This repo's guard config, or None when it isn't a resolvable repo or
        isn't opted in. Both mean "nothing to guard here"."""
        repo_root = _repo_root(target_dir)
        if repo_root is None:
            return None
        key = str(repo_root)
        if key not in cfg_cache:
            cfg_cache[key] = _load_config(repo_root)
        return cfg_cache[key]

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
        if sub is None:
            continue

        if sub == _WRAPPER_UNRESOLVABLE:
            # An `env`/`command`/`exec` wrapper we could not see through. Only
            # worth denying over if git is plausibly the wrapped command —
            # otherwise a chain like `env -S 'echo hi' && git status` would
            # block on the echo.
            if not _mentions_git(args):
                continue
            cfg = _cfg_for(base_dir)
            if cfg is None:
                continue  # not opted in -> total no-op, as everywhere else
            wrapper = opts.get("wrapper", "env")
            _deny(
                f"Blocked: cannot determine which command this `{wrapper} ...` "
                "invocation runs, and it mentions git — it may be a commit or "
                f"push to '{cfg['protected']}'"
                + (f" or '{cfg['integration']}'" if cfg["integration"] else "")
                + f". Run git directly instead of through `{wrapper}`.",
                _guidance(cfg),
            )
            continue

        if sub not in ("commit", "push") and sub in _GIT_BUILTINS:
            # Hot path: an ordinary git command, resolved with no subprocess and
            # no config read. Git ignores aliases that shadow builtins, so there
            # is nothing further to resolve here.
            continue

        # Resolve the repo this specific git command targets, then load THAT
        # repo's guard config and current branch.
        target_dir = _resolve_git_target_dir(base_dir, opts)
        cfg = _cfg_for(target_dir)
        if cfg is None:
            continue  # not a resolvable repo, or not opted in -> no-op for it

        if sub not in ("commit", "push"):
            # Unrecognised subcommand in an opted-in repo: it may be an alias,
            # defined either on the command line (`-c alias.ci=commit`) or in
            # the target repo's config. The config lookup is gated on BOTH
            # conditions so ordinary traffic never pays for it.
            expanded = _expand_alias(target_dir, sub, opts.get("aliases") or {})
            if expanded is None:
                if opts.get("unknown_global"):
                    # We could not identify this subcommand AND we skipped a
                    # global option of unknown arity — so that option may have
                    # eaten a value we then read as the subcommand, hiding the
                    # real one (`git --namespace foo commit -m x` reads as
                    # subcommand `foo`). Deny rather than guess. Narrow by
                    # construction: an unknown global in front of a subcommand
                    # we DO recognise is unaffected, so `git --literal-pathspecs
                    # status` and `git -p log` still cost nothing.
                    _deny(
                        f"Blocked: '{sub}' is neither a git subcommand nor an "
                        "alias, and a preceding global option of unknown arity "
                        "may have hidden the real one — it may be a commit or "
                        f"push to '{cfg['protected']}'"
                        + (f" or '{cfg['integration']}'" if cfg["integration"] else "")
                        + ". Run the git command without the unrecognised "
                        "global option.",
                        _guidance(cfg),
                    )
                continue  # no alias, or one that expands to a harmless builtin
            alias_name = sub
            sub, alias_args = expanded
            if sub == _ALIAS_UNRESOLVABLE:
                _deny(
                    f"Blocked: the git alias '{alias_name}' expands to a shell "
                    "command or to another alias, which this guard resolves "
                    "one level only — so it cannot rule out a commit or push "
                    f"to '{cfg['protected']}'"
                    + (f" or '{cfg['integration']}'" if cfg["integration"] else "")
                    + ". Run the underlying git command directly.",
                    _guidance(cfg),
                )
            args = alias_args + args

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
            targets, had_refspec, unresolvable = _push_targets(args, branch)
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
            # Fail CLOSED on a destination we could not resolve: it may well be
            # a guarded branch, and a guard that cannot verify must not report
            # success. (Distinct from the fail-OPEN cases above, which are all
            # "this repo is not guarded at all".)
            if unresolvable:
                _deny(
                    "Blocked: cannot resolve the push destination of "
                    + ", ".join(repr(r) for r in unresolvable)
                    + f" — it may target '{protected}'"
                    + (f" or '{integration}'" if integration else "")
                    + ". Push an explicit branch refspec instead.",
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

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

The guard answers one question: WILL THIS COMMAND WRITE TO A GUARDED BRANCH?
It can be wrong about that on two independent axes, and a defect on EITHER is
in scope, because both end the same way — the guard evaluates a context that is
not the one git is about to act in, and says yes.

  THE COMMAND (parsing) — WHAT is being run, and against which destination.
  `/usr/bin/git commit`, `env VAR=x git commit`, `command git push`, a `git ci`
  alias, `git push origin HEAD`, an option whose arity shifts the positionals.

  THE ENVIRONMENT (context) — WHICH repo and branch git will actually act on.
  This has nothing to do with how the command is written; it is about whether
  the guard's model of the world matches the shell's and git's. A `cd` that
  FAILS leaves the shell where it was. `--work-tree` without `--git-dir` leaves
  the REPO where it was. A `cd` inside `( … )` moves the shell only until the
  `)`. A path operand the guard never expanded — `cd "$D"`, `git -C "$D"` —
  points somewhere it cannot name, which is not the same as "nowhere". Each
  looked like an ordinary command, and each let a direct commit on a guarded
  branch through, because the guard went looking somewhere else.

An environment-axis defect is in scope however ordinary the command looks — the
"ordinary invocation forms" line below bounds the FIRST axis only, and is about
the kind of command, not the kind of bug.

On the parsing axis the target is ORDINARY INVOCATION FORMS: what a person or
an agent actually types or scripts. Within that target the guard is meant to be
correct, and a miss is a DEFECT.

It is NOT, and cannot be, resistant to DELIBERATELY CONSTRUCTED EVASION. It
reads a shell string, and git's command-line surface is unbounded; no amount of
parsing closes that. That distinction is the line, and a new finding can be
placed on one side of it without asking anyone:

  IN SCOPE — a shape someone would plausibly write without trying to evade
  anything. All the parsing examples above. These are defects: fix them.

  OUT OF SCOPE — a shape that only occurs when someone is routing around the
  guard on purpose. Anyone doing that also has `--no-verify`, git behind a
  shell variable or a here-doc, a wrapper script, or simply their own terminal.
  Hardening the parser against them buys nothing, and `pre-push` is the layer
  that answers them.

There is no equivalent escape clause on the environment axis. "The command was
weird" never excuses evaluating the wrong repo.

So this is a SPEED BUMP, not enforcement — but with a criterion, not a shrug.

Two limits are structural rather than parsing bugs, and neither has a fix in
this file:

  * It observes CLAUDE TOOL CALLS ONLY. A human typing in their own terminal, a
    Makefile target, a CI job, or any script an agent launches that shells out
    to git internally are all invisible to it — no PreToolUse hook ever sees
    them.

  * Its opt-in gate needs a repo it can NAME. Every decision starts from
    "is THIS repo opted in", and when a `cd` leaves the location unknown
    (defect 16) the fail-closed deny is gated on the LAST KNOWN directory. So
    `cd "$MAIN_REPO" && git commit`, started from a scratch repo that never
    opted in, stays a no-op even if `$MAIN_REPO` expands into a guarded repo.
    The only way to close that is to deny on every unexpandable `cd` in every
    repo on the machine — which ends the opt-in contract (`.claude/
    git-guard.json` present = guarded, absent = TOTAL no-op) that keeps this
    hook out of scratch repos and third-party clones. That trade is not worth
    making here, and it is not a trade `pre-push` has to make at all: it is
    installed IN the guarded repo, so it is reached by definition.

  * Its knowledge of git's option arity is a table, and git's surface grows. A
    FUTURE value-taking `git push` option we do not know about would shift the
    positionals the way `--recurse-submodules` did. `_git_subcommand` carries a
    backstop for the GLOBAL-option case (an unknown global plus an
    unidentifiable subcommand denies); the push-option case has none, because
    the only available backstop — re-arming the current-branch fallback
    whenever an unknown option appears — would false-block ordinary pushes of
    an unguarded refspec from a guarded branch.

Defects review has found, ALL now handled — kept as evidence the tail is real,
not as a checklist that is now complete. 1-9, 14, 15, 19-21, 23, 24, 27-32 and
34-36, 38-41 and 45-48 are parsing; 10-13, 16-18, 22, 25, 26, 33, 37, 42-44, 49 and 50 are the environment axis, and
are the reason that axis is written down at all. Most let something THROUGH;
24, 27, 29-32, 36, 42 and 43 BLOCKED something they should not have, which is a defect on
the same footing — a guard that cries wolf gets turned off:

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
      a repo-config lookup;
  10. a FAILING `cd` — `cd /gone ; git commit` and `cd /gone || git commit` run
      the commit in the original repo, but the guard followed the dead path and
      evaluated a directory that is not a repo at all;
  11. `--work-tree` without `--git-dir` — git still uses the current repo's
      `.git`, but the guard treated the work tree as the repo;
  12. subshell grouping — `(cd ../other && git commit)` was evaluated against
      the ORIGINAL repo, because the segment splitter dropped `(` and `)`
      instead of scoping the working directory to them;
  13. `-C` + `--git-dir` — `-C` was treated as overriding `--git-dir`, but git
      applies `-C` to the cwd and STILL lets `--git-dir` pick the repo, so
      `git -C ../feature --git-dir=/repo-on-main/.git commit` was evaluated
      against `../feature`;
  14. shell control flow (parsing) — reserved words sit in FRONT of the command
      they introduce, so `if …; then git commit; fi` and `while …; do git push
      origin main; done` tokenized as `["then", "git", …]` and never registered
      as git commands at all;
  15. the Windows spelling (parsing) — `git.exe commit`,
      `/mingw64/bin/git.exe push origin main`, and any case variant of them,
      matched neither the executable check nor the `"git" in command` fast
      path;
  16. an UNEXPANDED `cd` operand — `cd "$MAIN_REPO" && git commit` was read as
      a failed `cd` (defect 10's fix, applied where it did not belong), so the
      guard went on evaluating the current repo while bash expanded the
      variable and committed somewhere else. `cd -` and a bare `cd` had the
      same shape;
  17. where a refspec-less push GOES — `git push` with no refspec was read as
      "the current branch", but git consults config first, and both
      `push.default=upstream` and a configured `remote.<name>.push` send it to
      `main` from a feature branch tracking `origin/main`;
  18. pipelines and `&` — bash runs each pipeline element, and any command
      ended by `&`, in its OWN process, so `cd other | git commit` commits in
      the original repo. `|` was treated like `;`, letting the `cd` leak;
  19. `--repo <r>` as two tokens — the value was skipped rather than captured,
      so the no-refspec fallback read the DEFAULT remote's `push` refspec
      instead of `<r>`'s;
  20. `--all` / `--mirror` — they push every LOCAL branch and override
      `push.default`, so `git push --all origin` from a feature branch writes
      the protected branch with nothing on the command line naming it;
  21. the `--repo` ambiguity, half-handled — the positionals were read under
      both meanings, but the CONFIG lookup still used the `--repo` value, so
      `git push --repo=origin upstream` consulted `remote.origin.push` while
      git pushed to `upstream`;
  22. an unexpanded `-C` / `--git-dir` operand — defect 16 one operand over.
      `git -C "$MAIN_REPO" commit` was read as a literal directory of that
      name, found not to be a repo, and allowed;
  23. command substitutions as command boundaries (parsing) — `$( … )` is part
      of a word, but both the segment scanner and `shlex` broke it apart, so
      `git -C $(cat path) commit` stopped being recognised as a git command at
      all;
  24. tag pushes read as branch pushes (parsing) — an OVER-denial, and the
      only one so far. `git push --tags origin` sends tags and no branch, and
      `git push origin tag <name>` is `refs/tags/<name>`; both were read as
      branch destinations, so from a guarded branch they were blocked. That
      falsified a claim the docs had made from the start — that tag pushes are
      never blocked — and would have broken `/ship`;
  25. `&&` / `||` short-circuit — a `cd` bash SKIPS was applied anyway, so
      `cd /missing && cd ../feature ; git commit` evaluated `../feature` while
      the commit really happened in the original, guarded repo;
  26. a wrapped `cd` — `FOO=1 cd /guarded`, `command cd /guarded` and
      `builtin cd /guarded` all move the shell, but only a bare `cd` was
      recognised, so the guard stayed in the previous repo;
  27. dry runs treated as writes (parsing) — the second OVER-denial.
      `git commit --dry-run` and `git push --dry-run`/`-n` write nothing, and
      the criterion is whether the command WRITES to a guarded branch;
  28. redirections (parsing) — bash allows them ANYWHERE in a simple command.
      In front, `>/tmp/out git commit -m x` left the redirection as token 0 and
      the segment stopped looking like git; behind, `git push origin >main`
      counted the FILENAME as an explicit refspec and suppressed the
      current-branch fallback. `2>&1` was split at the `&` on top of that;
  29. `builtin git` (parsing) — an OVER-denial. `builtin` runs only shell
      builtins, so git never runs; it was in the run-wrapper list anyway;
  30. here-doc bodies (parsing) — another OVER-denial. `cat <<EOF … EOF` feeds
      its body to stdin, but newline splitting turned every line of it into a
      command, so a `git commit` line inside one could be blocked;
  31. the here-doc TERMINATOR (parsing) — bash needs an exact match, and `<<-`
      strips only leading tabs. Comparing a stripped line closed the body early
      on an indented ` EOF`, handing the rest of the data back as commands;
  32. `command -v` (parsing) — it LOOKS UP a name and prints it, running
      nothing, but the flag was skipped and `command -v git commit` read as a
      commit;
  33. a `cd` gated on an UNKNOWN status — defect 25 modelled the short-circuit
      only where the outcome was computable. `test -d /missing && cd ../feature
      ; git commit` has an uncomputable condition, and "might run" was applied
      as "did run", so the guard moved to `../feature` while the commit landed
      on the guarded branch. Both candidate directories are now checked;
  34. a QUOTED here-doc delimiter (parsing) — bash quote-removes the word, so
      `<<\\EOF` and `<<E"OF"` are closed by a plain `EOF`. Storing the quoting
      meant the terminator never matched and the body ran to the end of the
      script, swallowing a real `git commit` after it;
  35. `--mirror` read as `--all` — it also DELETES remote refs that are absent
      locally, so the guarded branch is written whether it is present or not.
      Checking the LOCAL branch list answered the wrong question and allowed a
      mirror push from a repo with no local `main`;
  36. function definitions (parsing) — an OVER-denial with a bypass hiding
      behind the obvious fix. `gc() { git commit -m x; }` defines and writes
      nothing, but the body was read as a live command; simply skipping it
      would have lost `gc() { … }; gc`, which really does commit. The body is
      parked at the definition and expanded at the CALL;
  37. a `cd` inside an `if`/loop BODY — defect 33 for control flow rather than
      `&&`. `if false; then cd /feature; fi; git commit` commits in the
      original repo, but the body was applied as if it always ran;
  38. config field TYPES — `{"protected_branch": 123}` is truthy, so 123
      became the guarded branch name, matched nothing, and silently unguarded
      a repo that looked opted in;
  39. an assignment prefix before a function CALL — `FOO=1 gc` still calls
      `gc`, but the lookup used `tokens[0]`, which was the assignment;
  40. function call ARGUMENTS — `g() { git "$@"; }` is an ordinary wrapper,
      and expanding the body without the call's arguments left a subcommand of
      `$@` that matched nothing;
  41. a VARIABLE subcommand — `git $VERB -m x` was allowed outright. The verb
      is exactly as unresolvable as a refspec we cannot expand, and now fails
      closed the same way;
  42. conditional-depth leak — defect 37's own bookkeeping. Counting
      `then`/`else`/`elif`/`do` incremented once per BRANCH but decremented
      once per `fi`, so after an `if … else … fi` the guard still believed it
      was inside a conditional and a later CERTAIN `cd` kept the old repo
      alive as a candidate, denying on it;
  43. …and counting the CONSTRUCT instead over-denied the CONDITION. `if cd
      ../other; then :; fi` really moves the shell, because a condition runs
      unconditionally. The two are now separated: a construct's condition is
      certain, its body is not;
  44. `GIT_DIR` in the environment — it selects the repo exactly as
      `--git-dir` does, but assignment prefixes were dropped, so
      `GIT_DIR=/repo-on-main/.git git commit` was evaluated against the
      session's repo;
  45. quoted parens inside `$( … )` — counting parens without minding quotes
      ended the substitution early on `echo $(printf ')')`, and the stray
      quote then swallowed the rest of the line, including a real
      `; git commit`;
  46. short-option CLUSTERS on `git commit` — git reads `-am` as `-a -m`, so
      `git commit -am --dry-run` makes `--dry-run` the MESSAGE and really
      commits, while the guard read the cluster as an unknown option and let
      it through as a dry run;
  47. `_tokens` masked substitutions with a REGEX while `_segments` used the
      quote-aware scanner, so `git -C $(printf '(') status` came out shredded
      and a READ-ONLY command fell into the unknown-target fail-closed path;
  48. short-option clusters on `git push` — `-vn` is `-v -n`, a dry run that
      writes nothing, but only the exact `-n` was recognised, so it was
      blocked;
  49. `export GIT_DIR=…` — it persists to every LATER command in the shell, so
      a commit after it lands in that repo, but only INLINE assignments were
      read. (A bare `GIT_DIR=…;` is not exported, so git never sees it —
      bash's answer, not an assumption.);
  50. the unresolvable-wrapper deny checked only `states[0]` — after a
      conditional `cd`, an opted-in candidate went unexamined whenever the
      other one was not opted in.

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
  - anything that reaches git without going through the Bash tool.

(`git push --all` / `--mirror` used to sit in this list, "caught only when
standing on a guarded branch". It does not belong: it is an ordinary
invocation that writes the protected branch from anywhere, which the coverage
claim above makes a defect rather than an omission. Closed as defect 20 — the
destinations are the local branch list, which is enumerable, so no guessing
is involved.)

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

    def branch_name(value):
        """A usable branch name, or None. A non-string is not one: a config
        saying `"protected_branch": 123` compared 123 against every branch
        name, matched nothing, and silently unguarded the repo while looking
        opted in (defect 38)."""
        return value.strip() if isinstance(value, str) and value.strip() else None

    # A bad value falls back to the house default rather than disabling the
    # guard: the file's presence says this repo WANTS guarding, so the safe
    # reading of a malformed field is "the default", not "nothing".
    protected = branch_name(raw.get("protected_branch")) or DEFAULT_PROTECTED

    if "integration_branch" in raw and (
        raw["integration_branch"] is None
        or branch_name(raw["integration_branch"]) is not None
    ):
        # An explicit null means "this repo genuinely has no integration
        # branch" — the default must not resurrect one. Any other unusable
        # value falls through to the default detection below.
        integration = branch_name(raw["integration_branch"])
    else:
        integration = (
            DEFAULT_INTEGRATION
            if _remote_branch_exists(repo_root, DEFAULT_INTEGRATION)
            else None
        )
    if integration == protected:
        integration = None

    release_tool = raw.get("release_tool")
    return {
        "protected": protected,
        "integration": integration,
        "release_tool": release_tool if isinstance(release_tool, str) else None,
    }


def _current_branch(cwd: Path):
    branch = _git(cwd, "rev-parse", "--abbrev-ref", "HEAD")
    # Detached HEAD reports "HEAD" — not on a named branch, nothing to guard.
    return branch if branch and branch != "HEAD" else None


# A shell function definition at a command position: `name() { … }` or
# `function name { … }` (parens optional). The body is DEFINED here, not run —
# `gc() { git commit -m x; }` writes nothing — so it must not be read as a live
# command. It must also not simply be DISCARDED: `gc() { … }; gc` really does
# commit, so the body is remembered and expanded at the CALL (defect 36).
_FUNC_DEF_RE = re.compile(
    r"(?:function\s+(?P<n1>[^\s(){}<>&|;]+)\s*(?:\(\s*\)\s*)?"
    r"|(?P<n2>[A-Za-z_][A-Za-z0-9_]*)\s*\(\s*\)\s*)"
)


# `$1`, `${2}`, `$@`, `$*` — a called function's positional parameters.
_POSITIONAL_RE = re.compile(r"\$\{?([1-9][0-9]*|[@*])\}?")


def _expand_positionals(body: str, args) -> str:
    """Substitute a function call's arguments into its body.

    `g() { git "$@"; }` is an ordinary wrapper, and without this `g commit -m
    x` expanded to a subcommand of `$@` — unrecognised, no alias, allowed.
    The quoted `"$@"` / `"$*"` forms are replaced INCLUDING their quotes,
    because they expand to separate words rather than one.
    """
    joined = " ".join(shlex.quote(a) for a in args)
    for quoted in ('"$@"', '"$*"', '"${@}"', '"${*}"'):
        body = body.replace(quoted, joined)

    def replace(match):
        name = match.group(1)
        if name in ("@", "*"):
            return joined
        index = int(name)
        return shlex.quote(args[index - 1]) if index <= len(args) else ""

    return _POSITIONAL_RE.sub(replace, body)


def _skip_group(command: str, pos: int, opener: str, closer: str):
    """Index just past the balanced `opener`…`closer` group starting at `pos`,
    or None if it never closes. Quote-aware, so a brace in a string is text."""
    depth, quote = 0, None
    i, n = pos, len(command)
    while i < n:
        c = command[i]
        if quote:
            if c == "\\" and quote == '"' and i + 1 < n:
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if c == "\\" and i + 1 < n:
            i += 2
            continue
        if c in "'\"":
            quote = c
            i += 1
            continue
        if c == opener:
            depth += 1
        elif c == closer:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return None


def _dequote_word(word: str) -> str:
    """Shell quote removal: drop the quoting, keep what it quoted.

    `\\EOF`, `E"OF"`, `'EOF'` and `"EOF"` all name the same here-doc delimiter
    `EOF`, because bash removes quotes from the word before matching the
    terminator line against it.
    """
    out = []
    i, n = 0, len(word)
    while i < n:
        c = word[i]
        if c == "\\" and i + 1 < n:
            out.append(word[i + 1])
            i += 2
        elif c in "'\"":
            j = i + 1
            while j < n and word[j] != c:
                # Inside double quotes a backslash still escapes.
                j += 2 if c == '"' and word[j] == "\\" and j + 1 < n else 1
            out.append(_dequote_word(word[i + 1 : j]) if c == '"' else word[i + 1 : j])
            i = min(j + 1, n)
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _segments(command: str):
    """Split a shell line into events: the individual commands joined by
    `&&`, `||`, `;`, `|` and newlines, plus the SUBSHELL boundaries between
    them. Yields `("cmd", text)`, `("open", None)` and `("close", None)`.

    Subshells are events rather than noise because `(` and `)` scope the
    working directory, and the guard tracks `cd` to know which repo a later
    command targets. `(cd ../other && git commit)` runs the commit in
    `../other`, and the cwd reverts afterwards — so a regex split that merely
    dropped the parens produced BOTH errors: it evaluated the commit against
    the original repo (missing a direct commit on the other repo's guarded
    branch), and, had the parens been stripped naively, it would have leaked
    the `cd` out past the `)` onto every later command. Environment-axis
    defect, round 6.

    The SEPARATOR is reported too, because not all of them keep the shell in
    one process. Bash runs every element of a pipeline, and any command ended
    by `&`, in a SUBSHELL — verified: `cd sub | pwd` and `cd sub & wait; pwd`
    both print the original directory, while `cd sub && pwd` prints `sub`. So a
    `cd` on either side of a `|` never reaches the next command, and treating
    `|` like `;` let `cd other | git commit` be evaluated against `other` while
    bash committed in the original repo (environment-axis defect, round 9).

    The scan is quote-aware, so a `)` or a separator inside `git commit -m
    "done)"` is text, not syntax. Command substitutions — `$(…)`, `` `…` `` and
    `$((…))` — are consumed WHOLE as opaque text rather than treated as
    boundaries, because they are part of a word, not a command break: splitting
    `git -C $(cat path) commit` at the `(` tore the git command in half and it
    stopped being recognised at all. Their contents are deliberately not
    inspected; an operand containing one is unexpanded, which
    `_literal_path` already reports as unknown. An unmatched `)` (a `case` arm)
    is ignored by the caller.

    HERE-DOC BODIES ARE DATA, not commands. `cat <<EOF` … `EOF` feeds its body
    to stdin, so a `git commit` line inside one is text that bash never runs —
    but splitting on newlines turned every such line into a command and could
    block on it. The body is now skipped to its terminator (honouring `<<-`,
    which allows leading tabs, and a quoted delimiter). `<<<` is a here-STRING,
    a single word rather than a body, and is left alone.

    A FUNCTION DEFINITION yields a `("func", (name, body))` event and its body
    is not emitted as commands — defining is not running. The caller expands
    the body if and when the function is called.
    """
    events = []
    buf = []

    def flush():
        text = "".join(buf).strip()
        buf.clear()
        if text:
            events.append(("cmd", text))

    def skip_heredoc_bodies(pos, pending):
        """Consume the bodies queued by `<<` operators on the line just ended."""
        for delim, strip_tabs in pending:
            while pos < n:
                eol = command.find("\n", pos)
                line_end = n if eol < 0 else eol
                line = command[pos:line_end]
                pos = n if eol < 0 else eol + 1
                # Bash needs the terminator line to match EXACTLY; `<<-` only
                # strips leading TABS. Comparing a `.strip()`ed line closed the
                # body early on an indented ` EOF`, putting real body lines
                # back in front of the parser.
                if (line.lstrip("\t") if strip_tabs else line) == delim:
                    break
        return pos

    pending_heredocs = []
    i, n = 0, len(command)
    in_single = in_double = False
    while i < n:
        c = command[i]
        if not in_single and not in_double and not "".join(buf).strip():
            # At a command position: a function DEFINITION defines, it does not
            # run. Capture the body and skip past it.
            match = _FUNC_DEF_RE.match(command, i)
            if match:
                k = match.end()
                while k < n and command[k] in " \t\n":
                    k += 1
                opener = command[k : k + 1]
                if opener in ("{", "("):
                    end = _skip_group(command, k, opener, "}" if opener == "{" else ")")
                    if end is not None:
                        events.append(
                            (
                                "func",
                                (
                                    match.group("n1") or match.group("n2"),
                                    command[k + 1 : end - 1],
                                ),
                            )
                        )
                        buf.clear()
                        i = end
                        continue
        if in_single:
            buf.append(c)
            in_single = c != "'"
            i += 1
        elif in_double:
            if c == "\\" and i + 1 < n:
                buf.append(c)
                buf.append(command[i + 1])
                i += 2
                continue
            buf.append(c)
            in_double = c != '"'
            i += 1
        elif c == "'":
            in_single = True
            buf.append(c)
            i += 1
        elif c == '"':
            in_double = True
            buf.append(c)
            i += 1
        elif c == "\\" and i + 1 < n:
            buf.append(c)
            buf.append(command[i + 1])
            i += 2
        elif c == "$" and i + 1 < n and command[i + 1] == "(":
            # `$( … )` / `$(( … ))` — opaque, balanced, part of the word.
            # Balanced QUOTE-AWARE: a bare paren counter treated the `)` in
            # `echo $(printf ')')` as the closing one, so the scan ended early,
            # the stray `'` then opened a quote, and everything after it —
            # including a real `; git commit` — was swallowed as text
            # (defect 45).
            j = _skip_group(command, i + 1, "(", ")")
            if j is None:
                j = n  # never closes: a syntax error bash would not run either
            buf.append(command[i:j])
            i = j
        elif c == "`":
            j = command.find("`", i + 1)
            j = n if j < 0 else j + 1
            buf.append(command[i:j])
            i = j
        elif (
            c == "<" and command[i + 1 : i + 2] == "<" and command[i + 2 : i + 3] != "<"
        ):
            # `<<WORD` / `<<-WORD` — queue the body to skip once this line
            # ends. (`<<<` is a here-string; it falls through.)
            #
            # The WORD is read whole and then quote-REMOVED, because bash
            # applies quote removal to it: `<<\EOF`, `<<E"OF"` and `<<'EOF'`
            # are all terminated by a plain `EOF`. Handling only a fully
            # quoted word stored the delimiter as `\EOF`, which never matched,
            # so the rest of the script — including a real `git commit` after
            # the terminator — was swallowed as here-doc data (defect 34).
            j = i + 2
            strip_tabs = command[j : j + 1] == "-"
            if strip_tabs:
                j += 1
            while j < n and command[j] in " \t":
                j += 1
            start, quote = j, None
            while j < n:
                ch = command[j]
                if quote:
                    if ch == quote:
                        quote = None
                    j += 1
                elif ch == "\\" and j + 1 < n:
                    j += 2
                elif ch in "'\"":
                    quote = ch
                    j += 1
                elif ch in " \t\n;&|<>()":
                    break
                else:
                    j += 1
            delim = _dequote_word(command[start:j])
            if delim:
                pending_heredocs.append((delim, strip_tabs))
            buf.append(command[i:j])
            i = j
        elif c in "&|;\n":
            nxt = command[i + 1] if i + 1 < n else ""
            prev = buf[-1] if buf else ""
            # `&` and `|` are ALSO redirection syntax: `2>&1`, `>&2`, `<&0`,
            # `&>log`, `>|file`. Splitting there tore `2>&1 git commit` into a
            # background `2>` and a segment starting `1`, which then did not
            # look like a git command at all.
            if (c == "&" and (prev in (">", "<") or nxt == ">")) or (
                c == "|" and prev == ">"
            ):
                buf.append(c)
                i += 1
                continue
            flush()
            if c in "&|" and nxt == c:  # `&&` / `||`
                sep, width = c * 2, 2
            elif c == "|" and nxt == "&":  # `|&` is `2>&1 |`
                sep, width = "|", 2
            else:
                sep, width = c, 1
            events.append(("sep", sep))
            i += width
            if c == "\n" and pending_heredocs:
                # The line that queued them has ended; its bodies are data.
                i = skip_heredoc_bodies(i, pending_heredocs)
                pending_heredocs = []
        elif c in "()":
            flush()
            events.append(("open" if c == "(" else "close", None))
            i += 1
        else:
            buf.append(c)
            i += 1
    flush()
    return events


# Separators that put the command BEFORE them in its own process, so a `cd` in
# that command dies with it: pipeline elements and background commands.
# `;`, `&&`, `||` and a newline all keep the shell in one process.
_SUBSHELL_SEPARATORS = frozenset({"|", "&"})


# Shell reserved words that SIT IN FRONT OF a command, so the command we care
# about is the next token along: `then git commit`, `do git push origin main`,
# `! git diff --quiet`, `time git push`. The segment splitter leaves them glued
# to the command, and the parser then failed to see `git` at all — an ordinary
# Bash form (`if …; then git commit; fi`) that never reached the guard.
#
# A redirection token: an optional fd number or `&`, one of the redirection
# operators, and optionally the target glued on. Bash allows these ANYWHERE in
# a simple command, including in FRONT of the command word.
_REDIRECT_RE = re.compile(r"^(?:[0-9]+|&)?(?:>>|>\||<>|<<<|<<-?|>&|<&|>|<)(.*)$")


def _strip_redirections(tokens):
    """Drop redirection tokens, and the operands they consume, from anywhere in
    a command.

    Both ends matter. In FRONT of the command word — `>/tmp/out git commit -m
    x`, `2>/tmp/log git push origin main` — the redirection was left as token 0
    and the segment stopped looking like git at all. AFTER it, the operand was
    read as an argument: `git push origin >main` on `main` really pushes the
    current branch to `origin` while writing stdout to a file called `main`,
    but `>main` was counted as an explicit refspec, which SUPPRESSED the
    current-branch fallback and allowed it (defect 28).

    A bare operator takes the next token as its target; an operator with the
    target attached (`2>&1`, `>>log`) takes only itself. No ordinary git
    argument begins with `<` or `>`, so nothing legitimate is caught.
    """
    out = []
    skip_next = False
    for tok in tokens:
        if skip_next:
            skip_next = False
            continue
        match = _REDIRECT_RE.match(tok)
        if match:
            skip_next = not match.group(1)
            continue
        out.append(tok)
    return out


# Brace groups are stripped here rather than scoped like `( … )`: a brace group
# runs in the CURRENT shell, so a `cd` inside it must keep applying afterwards.
#
# Terminators (`fi`, `done`, `esac`) need no entry — a separator always puts
# them in a segment of their own, where they are simply not a git command.
# `for` / `function` need none either: what follows them is a variable or a
# name, never a command.
_LEADING_SHELL_WORDS = frozenset(
    {
        "{",
        "}",
        "!",
        "then",
        "else",
        "elif",
        "do",
        "if",
        "while",
        "until",
        "time",
    }
)
_TRAILING_SHELL_WORDS = frozenset({"}"})

# A `cd` in a body that may not run is conditional, so it adds a candidate
# directory rather than replacing the current one. Tracked as a STACK of
# constructs, each flagged "are we in its body yet" — because the two things a
# plain counter conflated are both real:
#
#   COUNTING BRANCH WORDS leaks. `then`/`else`/`elif`/`do` incremented once per
#   BRANCH while `fi` decremented once per CONSTRUCT, so `if x; then …; else …;
#   fi` never unwound, and a later CERTAIN `cd` kept the old repo alive as a
#   candidate and denied on it (defect 42).
#
#   COUNTING THE CONSTRUCT over-denies the CONDITION. `if cd ../other; then :;
#   fi` really does move the shell — verified — because a condition runs
#   unconditionally; treating it as "maybe" kept the original repo live and
#   blocked the commit after it (defect 43).
#
# So: opening a construct pushes "not in the body yet", a body word flips the
# top entry, the closing word pops, and uncertainty is "are we inside ANY
# construct's body".
_CONSTRUCT_OPEN_WORDS = frozenset({"if", "while", "until"})
_BODY_OPEN_WORDS = frozenset({"then", "do", "else", "elif"})
# `for f in a` is a header, so its body waits for `do`; a `case` has no body
# word at all and its arms are conditional from the start.
_CONSTRUCT_OPEN_HEADS = {"for": False, "case": True}
_CONDITIONAL_END_WORDS = frozenset({"fi", "done", "esac"})


_SUBST_HOLE_RE = re.compile(r"\0S(\d+)\0")


def _mask_substitutions(segment: str):
    """Replace each command substitution with a space-free placeholder,
    returning `(masked_text, originals)`.

    Scanned with the same quote-aware `_skip_group` that `_segments` uses,
    rather than a regex. A regex could not see quoting, so `$(printf '(')`
    ended at the wrong paren and the tokens came out shredded — which then
    made a READ-ONLY `git -C $(printf '(') status` look like an unidentifiable
    subcommand and fail closed, contradicting the promise that read-only
    commands are untouched (defect 47).
    """
    holes = []
    out = []
    i, n = 0, len(segment)
    quote = None
    while i < n:
        c = segment[i]
        if quote:
            if c == quote:
                quote = None
            out.append(c)
            i += 1
        elif c == "\\" and i + 1 < n:
            out.append(segment[i : i + 2])
            i += 2
        elif c in "'\"":
            quote = c
            out.append(c)
            i += 1
        elif c == "$" and segment[i + 1 : i + 2] == "(":
            end = _skip_group(segment, i + 1, "(", ")")
            end = n if end is None else end
            holes.append(segment[i:end])
            out.append(f"\0S{len(holes) - 1}\0")
            i = end
        elif c == "`":
            end = segment.find("`", i + 1)
            end = n if end < 0 else end + 1
            holes.append(segment[i:end])
            out.append(f"\0S{len(holes) - 1}\0")
            i = end
        else:
            out.append(c)
            i += 1
    return "".join(out), holes


def _tokens(segment: str):
    """Split a segment into words, keeping each command substitution WHOLE.

    `shlex` knows nothing about `$( … )`, so `git -C $(cat path.txt) status`
    tokenized as `['git', '-C', '$(cat', 'path.txt)', 'status']` — the `-C`
    operand cut in half and `path.txt)` read as the subcommand. Substitutions
    are therefore masked to a space-free placeholder before splitting and
    restored after, which matches how `_segments` already treats them.
    """
    masked, holes = _mask_substitutions(segment)
    try:
        words = shlex.split(masked)
    except ValueError:
        words = masked.split()
    if not holes:
        return words
    return [
        _SUBST_HOLE_RE.sub(lambda m: holes[int(m.group(1))], word) for word in words
    ]


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
# `exec git commit` — both ordinary in scripts. Matched literally; unlike `env`
# these are shell builtins and never appear as a path.
#
# `builtin` is NOT here, and the asymmetry with `_CD_WRAPPERS` is deliberate:
# `builtin` runs ONLY shell builtins, so `builtin git commit` dies with "git:
# not a shell builtin" and git never runs, while `builtin cd /x` really moves
# the shell. Same reasoning that keeps `env`/`exec` out of `_CD_WRAPPERS` —
# a wrapper belongs in a list only where it can actually run that command.
_RUN_WRAPPERS = frozenset({"command", "exec"})
# Per-wrapper options, because they do not share a set: `command -p` and
# `exec -c`/`-l` take no value, `exec -a NAME` takes one. Anything else is
# unresolvable -> guarded.
_WRAPPER_FLAGS = {"command": frozenset({"-p"}), "exec": frozenset({"-c", "-l"})}
_WRAPPER_WITH_VALUE = {"command": frozenset(), "exec": frozenset({"-a"})}
# `command -v` / `-V` only LOOK UP a name and print it — nothing is executed,
# so `command -v git commit` is not a commit.
_COMMAND_LOOKUP_FLAGS = frozenset({"-v", "-V"})


def _strip_run_wrapper(tokens):
    """Consume a leading `command` / `exec` prefix, returning the remaining
    tokens, `[]` when the wrapper executes nothing at all, or None when its
    options cannot be resolved."""
    name = tokens[0]
    flags = _WRAPPER_FLAGS.get(name, frozenset())
    with_value = _WRAPPER_WITH_VALUE.get(name, frozenset())
    tokens = tokens[1:]
    i, n = 0, len(tokens)
    while i < n:
        tok = tokens[i]
        if tok == "--":
            i += 1
            break
        if not tok.startswith("-") or tok == "-":
            break
        if name == "command" and tok in _COMMAND_LOOKUP_FLAGS:
            return []  # a lookup, not an invocation
        if tok in flags:
            i += 1
        elif tok in with_value:
            if i + 1 >= n:
                return None
            i += 2
        else:
            return None  # unknown option — it may swallow the command token
    return tokens[i:]


def _exe_name(token: str) -> str:
    """The program a token invokes, normalised for comparison: BASENAME,
    lowercased, with a Windows `.exe` suffix removed.

    Basename, because absolute paths to a program are ordinary — scripts and
    cron entries use them constantly — and matching `tokens[0] == "git"` missed
    every one of them.

    Lowercase + `.exe`, because Git Bash and Windows spell it `git.exe`
    (`/mingw64/bin/git.exe push origin main`), and a case-insensitive
    filesystem means the spelling is not even stable. Neither variant was
    recognised, so both sailed past the guard.
    """
    name = PurePosixPath(token).name.lower()
    return name[:-4] if name.endswith(".exe") else name


def _is_git_executable(token: str) -> bool:
    """Whether this token invokes git. `git-foo`, `gitk` and the like have a
    different name and are correctly excluded."""
    return _exe_name(token) == "git"


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
      `C` / `git_dir` / `work_tree` — the path-scoping options, so the guard
          evaluates the targeted repo's branch and config instead of the
          session's. `work_tree` is captured because it CONSUMES A VALUE (which
          would otherwise shift the subcommand slot), not because it selects the
          repo — see `_resolve_git_target_dir` for why it does not;
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
    env_git_dir = None
    # Peel inline env-var assignments and run-wrappers, in any order and any
    # number: `FOO=1 git push`, `env FOO=1 git push`, `command git push`,
    # `FOO=1 env BAR=2 exec git push`. Note an inline
    # `CLAUDE_GUARD_GIT_WORKFLOW=0 git ...` does NOT override this hook — the
    # hook runs as a separate process and only sees exported env.
    while tokens:
        while tokens and _ASSIGN_RE.fullmatch(tokens[0]):
            # `GIT_DIR` selects the repo exactly as `--git-dir` does — verified,
            # `GIT_DIR=../other/.git git rev-parse --abbrev-ref HEAD` reports
            # the OTHER repo's branch. Dropping these assignments evaluated the
            # session's repo instead (defect 44). `GIT_WORK_TREE` is captured
            # for symmetry but selects nothing, the same way `--work-tree`
            # does not (defect 11) — verified alongside it.
            name, _, value = tokens[0].partition("=")
            if name == "GIT_DIR":
                env_git_dir = value
            tokens = tokens[1:]
        if not tokens:
            break
        head = tokens[0]
        if _exe_name(head) == "env":
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
        # A command-line `--git-dir` overrides the environment — verified.
        "git_dir": git_dir or env_git_dir,
        "work_tree": work_tree,
        "aliases": cli_aliases,
        "unknown_global": unknown_global,
    }
    return tokens[i], tokens[i + 1 :], opts


# `cd` options, none of which take a value.
_CD_FLAGS = frozenset({"-L", "-P", "-e", "-@", "--"})

# A path operand holding any of these is one WE NEVER EXPANDED: parameter or
# command substitution, or a glob. Bash resolves it and git acts there; we
# cannot, so the target becomes unknown rather than "a literal path of that
# name". (Same character class as `_UNRESOLVABLE_RE` for refspecs, minus the
# ref-navigation syntax.)
_UNEXPANDED_RE = re.compile(r"[$`*?\[]")


# Prefixes a `cd` can hide behind and STILL move the shell. Verified: `FOO=1
# cd sub`, `command cd sub` and `builtin cd sub` all leave the shell in `sub`.
# `env` and `exec` are deliberately absent — they look up an EXTERNAL program,
# and there is no `cd` binary, so `env cd sub` fails with "No such file or
# directory" and moves nothing. Stripping them would invent a move that never
# happened.
_CD_WRAPPERS = frozenset({"command", "builtin"})


def _cd_argument(tokens):
    """For a `cd` segment return `(True, operand)`, else `(False, None)`.

    `operand` is None for a bare `cd` (i.e. `$HOME`). Options are skipped, so
    `cd -P /x` is the same `cd` as `cd /x`, and leading assignments/wrappers
    are peeled so `FOO=1 cd /x` and `command cd /x` are seen as the directory
    changes they are (defect 26).
    """
    while tokens and (_ASSIGN_RE.fullmatch(tokens[0]) or tokens[0] in _CD_WRAPPERS):
        tokens = tokens[1:]
    if not tokens or tokens[0] != "cd":
        return (False, None)
    for tok in tokens[1:]:
        if tok in _CD_FLAGS:
            continue
        return (True, tok)
    return (True, None)


def _literal_path(operand: str):
    """`Path(operand)` when we can resolve it literally, else None — None means
    the operand holds expansion we never ran, so where it points is UNKNOWN.

    `~` is expanded because that expansion is deterministic; a `~user` that does
    not resolve stays unknown. Shared by every path operand the guard reads —
    `cd`, `-C`, `--git-dir` — because they fail the same way.
    """
    expanded = os.path.expanduser(operand)
    if expanded.startswith("~") or _UNEXPANDED_RE.search(expanded):
        return None
    return Path(expanded)


def _resolve_cd(base: Path, base_unknown: bool, operand: str):
    """Where the shell ends up after `cd <operand>`, as `(dir, unknown, ok)`.

    `ok` is the command's exit status where we can compute it — True, False, or
    None when the operand was never expanded. It is the ONLY status this guard
    can determine for any command, and `&&` / `||` short-circuiting depends on
    it.

    Three outcomes, and telling them apart is the whole point:

      RESOLVED   an existing directory — the shell moves, and so do we.
      FAILED     a literal path that does not exist — `cd` errors and the shell
                 STAYS PUT, so we stay too (defect 10).
      UNKNOWN    an operand we did not expand: `cd "$MAIN_REPO"`, `cd $(…)`,
                 `cd repo-*`. Bash expands it and moves somewhere we cannot
                 name. Treating that as "failed, stay put" was wrong in exactly
                 the direction that matters — from an unguarded repo the guard
                 kept evaluating THIS repo while the commit landed in whatever
                 the variable pointed at (defect 16). Unknown is therefore
                 sticky and the caller fails closed on it.

    `~` IS expanded, because that expansion is deterministic and doing it keeps
    an extremely ordinary `cd ~/proj` out of the UNKNOWN bucket. A `~user` that
    does not resolve stays UNKNOWN.
    """
    p = _literal_path(operand)
    if p is None:
        return (base, True, None)
    if p.is_absolute():
        # An absolute target re-anchors us even from an unknown location.
        return (p, False, True) if p.is_dir() else (base, base_unknown, False)
    if base_unknown:
        return (base, True, None)  # relative to nowhere we can name
    target = base / p
    return (target, False, True) if target.is_dir() else (base, False, False)


def _resolve_git_target_dir(base: Path, base_unknown: bool, opts: dict):
    """The directory to evaluate this git command against — i.e. one that
    belongs to the repo git will actually act on — as `(dir, unknown)`.

    The two options compose, in git's documented order — `-C` FIRST, whatever
    order they appear in on the command line:

      `-C` moves the process's working directory. Paths are cumulative and each
      relative one resolves against the previous.
      `--git-dir` then names the REPO, and a relative one resolves against the
      directory `-C` produced.

    Treating `-C` as overriding `--git-dir` was wrong in exactly the way that
    matters: `git -C ../feature --git-dir=/repo-on-main/.git commit` was
    evaluated against `../feature` while git committed to `/repo-on-main`
    (environment-axis defect, round 7).

    `--work-tree` deliberately names neither: git identifies a repo by its GIT
    DIR, and with `--work-tree` alone it still discovers `.git` upward from the
    current directory. So `git --work-tree ../scratch commit` commits to the
    repo you are standing in, using `../scratch`'s files — the branch and the
    guard config both still come from HERE. Reading the work tree as the repo
    pointed the guard at a different repo than git would write to, and let a
    protected-branch commit through (environment-axis defect, round 5).

    Every operand runs through `_literal_path`, so an UNEXPANDED one —
    `git -C "$MAIN_REPO" commit`, `git --git-dir="$D/.git" commit`,
    `env -C "$D" git commit` — makes the target unknown instead of being read
    as a literal directory of that name. It was read literally, found not to be
    a repo, and allowed, while bash expanded the variable and git committed in
    the guarded repo: the same failure as defect 16, one operand over
    (defect 22). `unknown` is inherited from the shell's own location and
    CLEARED by any later absolute literal operand, which genuinely re-anchors
    the target no matter where the shell is.
    """
    d, unknown = base, base_unknown
    for p in opts.get("C") or []:
        pp = _literal_path(p)
        if pp is None:
            unknown = True
        elif pp.is_absolute():
            d, unknown = pp, False
        elif not unknown:
            d = d / pp
    git_dir = opts.get("git_dir")
    if git_dir:
        ap = _literal_path(git_dir)
        if ap is None:
            unknown = True
        else:
            # A --git-dir of `<repo>/.git` -> the repo root is its parent.
            if ap.name == ".git":
                ap = ap.parent
            if ap.is_absolute():
                d, unknown = ap, False
            elif not unknown:
                # Relative git dirs resolve against the post-`-C` directory.
                d = d / ap
    return d, unknown


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

# The same, as single letters, because short options cluster: in `-vo ci.skip`
# the `o` still takes the next token.
_PUSH_SHORT_OPTS_WITH_VALUE = "o"


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
#   the all-tags flag  slots untouched, but it DOES change what a bare push
#       sends: `--tags` with no refspec pushes ONLY tags. Verified — from
#       `main` with the branch ahead of the remote, `git push --tags origin
#       --dry-run` reports the tag alone and no branch update. So the
#       current-branch fallback must not fire (defect 24). `--follow-tags` is
#       the opposite: a normal branch push PLUS reachable tags, so it keeps it.
#   the all-branches / mirror flags  no change to slots (positional #0 is
#       still the remote), but they push guarded branches with NO refspec
#       naming them, and they override `push.default` too. Handled separately
#       via `_local_branches` — see `_PUSH_ALL_OPTS`.
_REPO_OPT = "--repo"
_REPO_OPT_EQ = "--repo="

# Options that push EVERY local branch, so the destination set is the local
# branch list rather than anything on the command line. Verified: from `feat/x`
# with a local `main`, `git push --all origin --dry-run` reports `main -> main`.
# `--branches` is git's newer spelling of `--all`. These only ADD refs, so
# enumerating the local branches answers the question exactly.
_PUSH_ALL_OPTS = frozenset({"--all", "--branches"})

# `--mirror` is NOT one of them. It makes the remote MATCH the local ref set,
# which means it also DELETES remote refs that are absent locally — verified:
# with a remote `main` and no local `main`, `git push --mirror origin
# --dry-run` reports `- [deleted] main`. So the local branch list is the wrong
# question: the guarded branch is written whether it is present (updated) or
# absent (deleted), and answering "is it on the remote?" would need either the
# network or a remote-tracking ref that may be stale. It fails closed instead.
_MIRROR_OPT = "--mirror"

# `--tags` alone pushes ONLY tags; `--follow-tags` pushes the branch as well.
_TAGS_OPT = "--tags"
_FOLLOW_TAGS_OPT = "--follow-tags"

# `git push <remote> tag <name>` is shorthand for `refs/tags/<name>` — the word
# after `tag` is a TAG, never a branch destination. Reading it as one blocked
# `git push origin tag main` in a repo that has a tag called `main`.
_TAG_SHORTHAND = "tag"

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

    Returns (targets, had_explicit_refspec, unresolvable, remotes, push_all) —
    `targets` are the branch names the push would land on, `unresolvable` holds
    the raw refspecs whose destination could not be pinned down, `remotes` are
    the remotes this push might go to (more than one only for the ambiguous
    `--repo` shape), which the no-refspec fallback needs in order to read
    `remote.<name>.push`, `push_all` marks `--all`, whose destinations are
    every LOCAL branch, `push_mirror` marks `--mirror`, which also DELETES
    remote refs absent locally, and `tags_only` marks a push that sends tags
    and no branch at all.
    """
    positionals = []
    remote_from_opt = None
    skip_value = False
    value_is_repo = False
    push_all = push_mirror = False
    all_tags = follow_tags = False
    dry_run = False
    for a in args:
        if skip_value:
            # `--repo <r>` names the remote in the NEXT token; dropping it left
            # the no-refspec fallback reading `remote.<default>.push` instead of
            # `remote.<r>.push`.
            if value_is_repo:
                remote_from_opt = a
                value_is_repo = False
            skip_value = False
            continue
        if a.startswith("-"):
            if a == _REPO_OPT:
                remote_from_opt = ""  # sentinel until the value arrives
                skip_value = True
                value_is_repo = True
            elif a.startswith(_REPO_OPT_EQ):
                remote_from_opt = a[len(_REPO_OPT_EQ) :]
            elif a in _PUSH_OPTS_WITH_VALUE:
                skip_value = True
            elif a in _PUSH_ALL_OPTS:
                push_all = True
            elif a == _MIRROR_OPT:
                push_mirror = True
            elif a == _TAGS_OPT:
                all_tags = True
            elif a == _FOLLOW_TAGS_OPT:
                follow_tags = True
            elif a == "--dry-run":
                # For `git push`, `-n` IS `--dry-run` (unlike `git commit -n`,
                # which is `--no-verify` and really commits).
                dry_run = True
            elif len(a) > 1 and a[1] != "-":
                # Short options CLUSTER, so `git push -vn origin main` is a
                # dry run and writes nothing — denying it was an over-block
                # (defect 48). Scanning stops at a value-taking letter, whose
                # value is either glued on (`-onci.skip`) or the next token
                # (`-vo ci.skip`): letters after it are that VALUE, not flags,
                # so an `n` there must not be read as `--dry-run`.
                for index, letter in enumerate(a[1:]):
                    if letter in _PUSH_SHORT_OPTS_WITH_VALUE:
                        skip_value = index == len(a) - 2
                        break
                    if letter == "n":
                        dry_run = True
            continue
        positionals.append(a)

    if remote_from_opt is not None:
        # `--repo` already named the remote, so EVERY positional is a refspec.
        # Git does ignore `--repo` when a positional repository is ALSO given,
        # and we cannot tell those two readings apart without knowing the
        # repo's remotes — so take the fail-closed union of both: treat all
        # positionals as refspecs, AND keep the current-branch fallback alive
        # unless a second positional proves the first one was the remote.
        refspecs = positionals
        had_refspec = len(positionals) > 1
        if len(positionals) == 1:
            # The ambiguous shape. The union has to cover the REMOTE reading
            # too, or `git push --repo=origin upstream` consults
            # `remote.origin.push` while git is pushing to `upstream` — and a
            # `remote.upstream.push` aimed at the protected branch slips by.
            remotes = [remote_from_opt, positionals[0]]
        elif positionals:
            remotes = [positionals[0]]  # git ignores --repo once a repo is given
        else:
            remotes = [remote_from_opt]
    else:
        # First positional is the remote; the rest are refspecs.
        refspecs = positionals[1:]
        had_refspec = len(refspecs) > 0
        remotes = [positionals[0] if positionals else None]
    targets = []
    unresolvable = []
    idx = 0
    while idx < len(refspecs):
        ref = refspecs[idx]
        if ref == _TAG_SHORTHAND and idx + 1 < len(refspecs):
            # `tag <name>` -> `refs/tags/<name>`. A tag, never a branch — even
            # when the tag happens to be called `main`.
            idx += 2
            continue
        dst = _resolve_push_dst(ref, current_branch)
        if dst is None:
            unresolvable.append(ref)
        else:
            targets.append(dst)
        idx += 1
    # `--tags` with no refspec sends tags and nothing else, so there is no
    # implicit branch destination to work out. With a refspec, or alongside
    # `--follow-tags`, a branch IS pushed and the normal reading applies.
    tags_only = all_tags and not follow_tags and not had_refspec
    return (
        targets,
        had_refspec,
        unresolvable,
        remotes,
        push_all,
        push_mirror,
        tags_only,
        dry_run,
    )


# `git commit` options that consume the FOLLOWING token. Needed only so a
# value can never be mistaken for the dry-run flag: `git commit -m --dry-run`
# is a REAL commit whose message happens to be `--dry-run`, and reading it as a
# dry run would be a bypass — the opposite of the false positive being fixed.
_COMMIT_OPTS_WITH_VALUE = frozenset(
    {
        "-m",
        "--message",
        "-F",
        "--file",
        "--author",
        "--date",
        "-C",
        "--reuse-message",
        "-c",
        "--reedit-message",
        "--fixup",
        "--squash",
        "--cleanup",
        "-t",
        "--template",
        "--trailer",
        "--pathspec-from-file",
    }
)

# The same options as single letters, which CLUSTER: `-am` is `-a -m`, so the
# `m` still consumes the next token.
_COMMIT_SHORT_OPTS_WITH_VALUE = "mFCct"


def _commit_is_dry_run(args) -> bool:
    """Whether this `git commit` writes nothing.

    ONLY `--dry-run`. `git commit -n` is `--no-verify`, which is a real commit
    that merely skips hooks — verified: HEAD moves. Conflating the two would
    turn the busiest bypass in the file into an allow.

    Short options CLUSTER, and that matters here for the same reason: git
    reads `git commit -am --dry-run` as `-a -m --dry-run`, so `--dry-run` is
    the commit MESSAGE and the commit is real — verified, HEAD moves and the
    subject line is `--dry-run`. A value-taking letter anywhere in a cluster
    consumes the next token unless the cluster already supplies its value
    (`-amwip`) (defect 46).
    """
    skip_value = False
    for a in args:
        if skip_value:
            skip_value = False
            continue
        if a == "--":
            break  # pathspecs from here on
        if a == "--dry-run":
            return True
        if a in _COMMIT_OPTS_WITH_VALUE:
            skip_value = True
        elif len(a) > 1 and a[0] == "-" and a[1] != "-":
            letters = a[1:]
            for index, letter in enumerate(letters):
                if letter in _COMMIT_SHORT_OPTS_WITH_VALUE:
                    skip_value = index == len(letters) - 1
                    break
    return False


def _local_branches(target_dir: Path):
    """Every local branch name, or None if they could not be enumerated (which
    the caller must treat as "cannot verify" rather than "none")."""
    out = _git(target_dir, "for-each-ref", "--format=%(refname:short)", "refs/heads/")
    if out is None:
        return None
    return [line.strip() for line in out.splitlines() if line.strip()]


def _config_map(target_dir: Path) -> dict:
    """The repo's effective git config as `{key: [values]}`, lowercased section
    and variable names (git's own normalisation) with subsection case intact.

    One `git config --list -z` call rather than a handful of `--get`s, and only
    ever made on the no-refspec push path.
    """
    raw = _git(target_dir, "config", "--list", "-z")
    out: dict = {}
    if not raw:
        return out
    for entry in raw.split("\0"):
        if not entry:
            continue
        key, _, value = entry.partition("\n")
        out.setdefault(key, []).append(value)
    return out


def _push_remote(cfg_map: dict, explicit, branch) -> str:
    """The remote a push goes to, in git's precedence order. Only the NAME
    matters here — it is the key for `remote.<name>.push`."""
    if explicit:
        return explicit
    for key in (
        f"branch.{branch}.pushremote",
        "remote.pushdefault",
        f"branch.{branch}.remote",
    ):
        values = cfg_map.get(key)
        if values and values[-1]:
            return values[-1]
    return "origin"


def _implicit_push_refspecs(cfg_map: dict, remote: str, branch):
    """The refspecs a `git push` with NO refspec on the command line actually
    uses, as `(refspecs, unresolvable)`.

    "No refspec" does NOT mean "the current branch": git consults config, and
    two ordinary settings redirect it somewhere else entirely (defect 17).
    Verified against real git — from `feat/x` with an upstream of `origin/main`,
    a bare `git push` reports `feat/x -> main` under both:

      `remote.<name>.push`   configured refspecs, used verbatim and in
                             preference to `push.default`;
      `push.default=upstream` (or the `tracking` alias) — pushes to
                             `branch.<cur>.merge`, which is `refs/heads/main`
                             for any branch made with `git checkout -b … origin/main`.

    The rest resolve without surprises:
      `nothing`            pushes nothing;
      `current` / `simple` the same-name branch. (`simple` additionally REFUSES
                           when the upstream name differs, so reading it as the
                           current branch can only over-deny, never under-.)
      `matching`           pushes every branch that exists on both sides, which
                           includes a guarded one — unresolvable, so fail closed.
    """
    if branch is None:
        return [], []  # detached HEAD: nothing to push by default
    configured = [v for v in cfg_map.get(f"remote.{remote}.push", []) if v]
    if configured:
        return configured, []
    modes = cfg_map.get("push.default") or []
    mode = (modes[-1] if modes else "simple").strip().lower()
    if mode == "nothing":
        return [], []
    if mode in ("upstream", "tracking"):
        merge = [v for v in cfg_map.get(f"branch.{branch}.merge", []) if v]
        # No upstream configured -> git errors out, nothing is pushed.
        return ([merge[-1]] if merge else []), []
    if mode == "matching":
        return [], ["push.default=matching"]
    return [branch], []


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
        "Note this guard is an agent-side speed bump, not enforcement. It has "
        "to be right about both the command (which git verb, which "
        "destination) and the environment (which repo and branch git will "
        "actually act on); it targets ordinary invocation forms, and within "
        "those a miss on either is a defect worth reporting. But it sees "
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
    # Case-insensitive: the whole point of normalising the executable name is
    # that `GIT.EXE` is a real spelling, and a case-sensitive fast path here
    # would throw those commands away before the parser ever ran.
    if not command or "git" not in command.lower():
        _allow()

    # Base dir the command runs in. `cd` segments earlier in the same chained
    # command shift this; each git command is then scoped to its OWN target repo
    # (via `cd` and/or `-C`/`--git-dir`), so a sibling-repo op is evaluated
    # against the SIBLING repo's branch + config — not the session's repo.
    base_dir = _base_dir(hook_input)

    # Per-target-repo config cache: repo-root -> cfg (or None). Avoids re-reading
    # config / re-shelling rev-parse for repeated ops on the same repo.
    cfg_cache: dict = {}
    # Full `git config --list` per repo, read only on the no-refspec push path.
    cfgmap_cache: dict = {}

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

    # EVERY directory the shell might be in, as (dir, unknown) pairs — see
    # `_resolve_cd` for what `unknown` means. Normally one, but a `cd` gated on
    # a condition we cannot evaluate leaves TWO possibilities, and a guarded
    # verb is then checked against both.
    #
    # `test -d /missing && cd ../feature ; git commit` is the shape that forced
    # this: bash skips the `cd`, so the commit lands on the guarded branch, but
    # treating "might run" as "did run" moved the guard to `../feature` and let
    # it through. Blanket fail-closed would have been wrong in the other
    # direction — `git add -A && cd subdir && git commit` has both candidates
    # inside the SAME repo, so denying it would be pure noise. Checking each
    # candidate is exact either way (environment-axis defect, round 15).
    states = [(base_dir, False)]
    prev_dir = None
    # `GIT_DIR` as a shell variable, and the value git actually sees. Only the
    # EXPORTED one reaches a child process.
    shell_git_dir = None
    exported_git_dir = None
    # Above this many possibilities, stop enumerating and fail closed instead.
    max_states = 8

    # Shell state saved by an open subshell, restored when it closes.
    dir_stack: list = []
    # State as it stood before the command segment currently being processed,
    # so a `cd` that turns out to have run in its own process can be undone —
    # and whether the previous separator opened a pipeline, whose LAST element
    # is equally a subshell.
    state_before = None
    after_pipe = False

    # `&&` / `||` SHORT-CIRCUIT. `last_status` is the exit status of the last
    # command we could determine one for — which is only ever a `cd`, since
    # that is the only command whose outcome the guard can compute. Everything
    # else leaves it None (unknown), and an unknown condition means the next
    # command might run, so it is still processed.
    #
    # Without this, `cd /missing && cd ../feature ; git commit` applied the
    # SECOND `cd` even though bash skips it, and the commit — which really
    # happens in the original, guarded repo — was evaluated against
    # `../feature` and allowed (environment-axis defect, round 13).
    #
    # A skipped command leaves `last_status` untouched, which is what makes a
    # chain behave: `a && b && c` skips both b and c when a fails, while
    # `a && b || c` still runs c.
    # `run_uncertain` is the other half: the command runs only if the unknown
    # condition happened to hold, so a `cd` in it ADDS a possibility rather
    # than replacing the current one.
    last_status = None
    run_next = True
    run_uncertain = False
    skip_depth = 0
    # One entry per open `if`/loop/`case`; True once we are inside its BODY,
    # which is the part that may not run. See `_CONSTRUCT_OPEN_WORDS`.
    construct_stack: list = []

    # Shell functions: name -> body. Defining one runs nothing, so the body is
    # parked here and spliced into the event stream at the CALL instead.
    functions: dict = {}
    expansions = 0

    events = _segments(command)
    event_index = 0
    while event_index < len(events):
        kind, seg = events[event_index]
        event_index += 1
        if kind == "func":
            name, body = seg
            if not skip_depth:
                functions[name] = body
            continue
        if skip_depth:
            # Inside a subshell bash never entered.
            if kind == "open":
                skip_depth += 1
            elif kind == "close":
                skip_depth -= 1
            continue
        if kind == "sep":
            # A `cd` inside a pipeline element, or before a `&`, dies with that
            # element's process — so roll the shell back to where that element
            # started. `;`, `&&`, `||` and newlines keep the same shell.
            if state_before is not None and (seg in _SUBSHELL_SEPARATORS or after_pipe):
                states, prev_dir, shell_git_dir, exported_git_dir = state_before
            after_pipe = seg == "|"
            if seg == "&&":
                run_next = last_status is not False
                run_uncertain = last_status is None
            elif seg == "||":
                run_next = last_status is not True
                run_uncertain = last_status is None
            else:
                run_next = True
                run_uncertain = False
            continue
        if kind == "open":
            if not run_next:
                skip_depth = 1
                continue
            dir_stack.append((list(states), prev_dir, shell_git_dir, exported_git_dir))
            continue
        if kind == "close":
            # A subshell's status is its own; we cannot compute it.
            last_status = None
            # A subshell's `cd` dies with the subshell. An unmatched `)` (a
            # `case` arm, say) has nothing to restore and is ignored.
            if dir_stack:
                states, prev_dir, shell_git_dir, exported_git_dir = dir_stack.pop()
            continue

        if not run_next:
            # Bash short-circuits past this command, so it neither moves the
            # shell nor writes anything. `last_status` carries through, which
            # keeps `a && b && c` and `a && b || c` both correct.
            continue

        state_before = (list(states), prev_dir, shell_git_dir, exported_git_dir)

        tokens = _tokens(seg)
        # Redirections can sit anywhere, including before the command word.
        tokens = _strip_redirections(tokens)
        # Peel shell reserved words standing in front of the command, so
        # `then git commit` is read as the `git commit` it is — and note when
        # one of them opens a body that may not run at all. `if false; then cd
        # /feature; fi; git commit` commits in the ORIGINAL repo, so a `cd` in
        # there ADDS a possibility rather than replacing the current one, the
        # same way a `cd` after an unevaluated `&&` does (defect 37).
        while tokens and tokens[0] in _LEADING_SHELL_WORDS:
            if tokens[0] in _CONSTRUCT_OPEN_WORDS:
                construct_stack.append(False)  # in its CONDITION, which runs
            elif tokens[0] in _BODY_OPEN_WORDS and construct_stack:
                construct_stack[-1] = True  # now in a body, which may not
            tokens = tokens[1:]
        while tokens and tokens[-1] in _TRAILING_SHELL_WORDS:
            tokens = tokens[:-1]
        if tokens and tokens[0] in _CONSTRUCT_OPEN_HEADS:
            construct_stack.append(_CONSTRUCT_OPEN_HEADS[tokens[0]])
        if tokens and tokens[0] in _CONDITIONAL_END_WORDS:
            if construct_stack:
                construct_stack.pop()
            continue

        # CALLING a function runs its body — so splice the body's events in
        # here, which is the half that keeps `gc() { git commit; }; gc` caught
        # while the bare definition is not. The cap stops a recursive function
        # (`f() { f; }`) from expanding forever.
        #
        # Assignment prefixes are peeled first: `FOO=1 gc` still calls `gc`
        # (verified). `command gc` deliberately is NOT peeled here — `command`
        # suppresses function lookup, so it runs the external `gc` or nothing
        # ("gc: command not found"), never the function (defect 39).
        call = tokens
        while call and _ASSIGN_RE.fullmatch(call[0]):
            call = call[1:]
        if call and call[0] in functions and expansions < 32:
            expansions += 1
            # The call's arguments are the body's positional parameters, so a
            # wrapper like `g() { git "$@"; }` is expanded with them — without
            # this, `g commit -m x` left a subcommand of `$@` (defect 40).
            body = _expand_positionals(functions[call[0]], call[1:])
            events[event_index:event_index] = _segments(body)
            continue

        # Track `export GIT_DIR=…`, which persists to every LATER command in
        # the same shell — verified: `export GIT_DIR=../lab/.git; git rev-parse
        # --abbrev-ref HEAD` reports the OTHER repo's branch, so a commit after
        # it lands there (defect 49).
        #
        # A BARE `GIT_DIR=…;` does not, and bash was the one to say so: it sets
        # a shell variable that a child process never sees, and the same
        # `rev-parse` reports the current repo. It is tracked only so that a
        # later `export GIT_DIR` (no value) can promote it.
        if tokens and tokens[0] in ("export", "unset"):
            for tok in tokens[1:]:
                name, eq, value = tok.partition("=")
                if name == "-n" or tok == "-n":
                    continue
                if name != "GIT_DIR":
                    continue
                if tokens[0] == "unset":
                    shell_git_dir = exported_git_dir = None
                elif eq:
                    shell_git_dir = exported_git_dir = value
                elif "-n" in tokens[1:]:
                    exported_git_dir = None  # `export -n` un-exports it
                else:
                    exported_git_dir = shell_git_dir
            last_status = None
            continue
        if tokens and all(_ASSIGN_RE.fullmatch(t) for t in tokens):
            for tok in tokens:
                name, _, value = tok.partition("=")
                if name == "GIT_DIR":
                    shell_git_dir = value
                    if exported_git_dir is not None:
                        # Already exported: assigning updates what git sees.
                        exported_git_dir = value
            last_status = None
            continue

        # Track `cd` so a subsequent git command in the same chain resolves
        # against the directory the shell actually moved into — or, when that
        # cannot be determined, is refused rather than guessed at.
        is_cd, operand = _cd_argument(tokens)
        if is_cd:
            was = states[0]
            moved = []
            statuses = set()
            for cur_dir, cur_unknown in states:
                if operand is None:
                    # Bare `cd` goes to $HOME, and the hook runs as the same user.
                    home_dir = Path.home()
                    moved.append((home_dir, False))
                    statuses.add(home_dir.is_dir())
                elif operand == "-":
                    # `cd -` returns to the previous directory. We know it only
                    # if we saw the `cd` that set it.
                    if prev_dir is None:
                        moved.append((cur_dir, True))
                        statuses.add(None)
                    else:
                        moved.append((prev_dir, False))
                        statuses.add(True)
                else:
                    new_dir, new_unknown, ok = _resolve_cd(
                        cur_dir, cur_unknown, operand
                    )
                    moved.append((new_dir, new_unknown))
                    statuses.add(ok)
            # A `cd` bash only MIGHT have run leaves the shell in either
            # place — whether the doubt comes from an unevaluated `&&`/`||`
            # condition or from sitting inside an `if`/loop body.
            uncertain = run_uncertain or any(construct_stack)
            candidates = (list(states) + moved) if uncertain else moved
            deduped = list(dict.fromkeys(candidates))
            if len(deduped) > max_states:
                # Too many branches to enumerate — collapse to "unknown", which
                # the guarded-verb check fails closed on.
                deduped = [(deduped[0][0], True)]
            states = deduped
            # One agreed status, or none at all.
            last_status = statuses.pop() if len(statuses) == 1 else None
            if uncertain:
                last_status = None
            # $OLDPWD only moves when the `cd` actually succeeded.
            if states[0] != was:
                prev_dir = None if was[1] else was[0]
            continue

        # Any other command: we cannot compute its exit status, so a following
        # `&&` / `||` has to assume it might go either way.
        last_status = None

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
            wrapper = opts.get("wrapper", "env")
            # EVERY candidate directory, not just the first: after a
            # conditional `cd` the shell might be in either, and checking only
            # `states[0]` let an opted-in candidate go unexamined whenever the
            # other one was not opted in (defect 50). Same rule as
            # `_check_git_command` already follows for a real git invocation.
            for cand_dir, _cand_unknown in states:
                cfg = _cfg_for(cand_dir)
                if cfg is None:
                    continue  # not opted in -> total no-op, as everywhere else
                _deny(
                    f"Blocked: cannot determine which command this "
                    f"`{wrapper} ...` invocation runs, and it mentions git — "
                    f"it may be a commit or push to '{cfg['protected']}'"
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

        # Check the command against EVERY directory the shell might be in. All
        # but one of these is a singleton loop; the exception is a `cd` gated
        # on a condition we could not evaluate. `_deny` exits, so the first
        # candidate that violates wins.
        if exported_git_dir and not opts.get("git_dir"):
            # An exported `GIT_DIR` selects the repo just like `--git-dir`,
            # which overrides it.
            opts = dict(opts, git_dir=exported_git_dir)
        for _cand_dir, _cand_unknown in states:
            _check_git_command(
                _cand_dir, _cand_unknown, sub, args, opts, _cfg_for, cfgmap_cache
            )
        continue

    _allow()


def _check_git_command(base_dir, base_unknown, sub, args, opts, _cfg_for, cfgmap_cache):
    """Evaluate one `git commit` / `git push` against ONE candidate working
    directory, denying (and exiting) if it would write to a guarded branch."""
    # Resolve the repo this specific git command targets, then load THAT
    # repo's guard config and current branch.
    target_dir, target_unknown = _resolve_git_target_dir(base_dir, base_unknown, opts)

    if target_unknown:
        # Either a preceding `cd`, or one of this command's own path
        # operands, used something we could not expand — so we cannot tell
        # which repo it writes to. Fail closed, as everywhere else a check
        # cannot verify. The gate is the LAST KNOWN directory's opt-in, so
        # a repo that never opted in stays a total no-op (a documented
        # limit — see the module docstring); and read-only subcommands
        # never get here, so `cd "$D" && git status` is fine.
        cfg = _cfg_for(base_dir)
        if cfg is None:
            return
        _deny(
            f"Blocked: cannot determine which repo `git {sub}` runs in — a "
            "preceding `cd`, or a `-C`/`--git-dir` operand, used a path "
            "this guard cannot expand (a variable, a command substitution "
            f"or a glob), so the target may be '{cfg['protected']}'"
            + (f" or '{cfg['integration']}'" if cfg["integration"] else "")
            + ". Use a literal path.",
            _guidance(cfg),
        )

    cfg = _cfg_for(target_dir)
    if cfg is None:
        return  # not a resolvable repo, or not opted in -> no-op for it

    if sub not in ("commit", "push") and _UNEXPANDED_RE.search(sub):
        # The VERB itself is a variable or a substitution we never expanded —
        # `git $VERB -m x`, or a function wrapper whose `$@` had no arguments
        # to expand. We cannot tell whether it is `commit`, `push`, or
        # `status`, so fail closed like every other check that cannot verify.
        _deny(
            f"Blocked: cannot tell which git subcommand `{sub}` is — it is a "
            "variable or a substitution this guard never expanded, so it may "
            f"be a commit or push to '{cfg['protected']}'"
            + (f" or '{cfg['integration']}'" if cfg["integration"] else "")
            + ". Name the subcommand literally.",
            _guidance(cfg),
        )

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
            return  # no alias, or one that expands to a harmless builtin
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
        if _commit_is_dry_run(args):
            return  # writes nothing — see `_commit_is_dry_run`
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
        (
            targets,
            had_refspec,
            unresolvable,
            remotes,
            push_all,
            push_mirror,
            tags_only,
            dry_run,
        ) = _push_targets(args, branch)
        if dry_run:
            # `--dry-run` / `-n` writes nothing, so by the guard's own
            # criterion — will this command WRITE to a guarded branch? —
            # there is nothing to block (defect 27).
            return
        implicit_targets = []
        remote_name = None
        if push_mirror:
            # `--mirror` makes the remote MATCH the local ref set, so it
            # writes the guarded branch whether that branch is present
            # (updated) or absent (DELETED — verified: with a remote `main`
            # and no local one, `--dry-run` reports `- [deleted] main`).
            # Enumerating local branches, which is the right question for
            # `--all`, answers the wrong one here, and the right one needs
            # the remote's actual refs. So it fails closed (defect 35).
            _deny(
                "Blocked: `git push --mirror` makes the remote match this "
                "repo exactly — it would update or DELETE "
                f"'{protected}'"
                + (f" and '{integration}'" if integration else "")
                + " on the remote. Push an explicit branch refspec instead.",
                guidance,
            )
        if push_all:
            # `--all` pushes every LOCAL branch and overrides push.default
            # entirely, so the destinations are the local branch list —
            # nothing on the command line names them. This was the last
            # "documented gap", but `git push --all origin` from a feature
            # branch is an ordinary invocation that writes the protected
            # branch, so by this guard's own criterion it was a defect (20).
            local = _local_branches(target_dir)
            if local is None:
                _deny(
                    "Blocked: `git push --all` pushes every local branch and "
                    "the branch list could not be read, so it may include "
                    f"'{protected}'"
                    + (f" or '{integration}'" if integration else "")
                    + ". Push an explicit branch refspec instead.",
                    guidance,
                )
            for name, label in (
                (protected, "protected"),
                (integration, "integration"),
            ):
                if name and name in local:
                    _deny(
                        "Blocked: `git push --all` pushes every local branch, "
                        f"including the {label} branch '{name}'.",
                        guidance,
                    )
        elif tags_only:
            # `--tags` with no refspec pushes tags and no branch, so there
            # is no implicit destination to resolve. `/ship` depends on
            # this, and the docs have always claimed tag pushes are never
            # blocked — the current-branch fallback was falsifying that
            # from a guarded branch (defect 24).
            pass
        elif not had_refspec:
            # "No refspec" does NOT mean "the current branch": git reads
            # `remote.<name>.push` and `push.default`, and either can send
            # the push to a different branch entirely. `remotes` holds more
            # than one candidate only for the ambiguous `--repo` shape, and
            # then every candidate is checked — the same fail-closed union
            # already applied to that shape's positionals.
            key = str(target_dir)
            if key not in cfgmap_cache:
                cfgmap_cache[key] = _config_map(target_dir)
            cmap = cfgmap_cache[key]
            for candidate in remotes:
                name = _push_remote(cmap, candidate, branch)
                if remote_name is None:
                    remote_name = name
                implicit, unresolvable_modes = _implicit_push_refspecs(
                    cmap, name, branch
                )
                unresolvable = unresolvable + unresolvable_modes
                for ref in implicit:
                    dst = _resolve_push_dst(ref, branch)
                    if dst is None:
                        unresolvable.append(ref)
                    else:
                        implicit_targets.append(dst)

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
        # Destinations git supplies itself when no refspec was given.
        for name, label in ((protected, "protected"), (integration, "integration")):
            if name and name in implicit_targets:
                if name == branch:
                    _deny(
                        f"Blocked: push of current branch '{name}' "
                        f"(the {label} branch).",
                        guidance,
                    )
                _deny(
                    f"Blocked: `git push` with no refspec sends '{branch}' to "
                    f"the {label} branch '{name}' in this repo — git's own "
                    f"config says so (`remote.{remote_name}.push` or "
                    "`push.default`), even though no refspec names it.",
                    guidance,
                )


if __name__ == "__main__":
    # Belt-and-suspenders fail-open: an unforeseen error must never wedge git.
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        print("{}")
        sys.exit(0)

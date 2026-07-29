#!/usr/bin/env python3
"""
PreToolUse hook: block destructive commands before execution.

Catches git destruction, filesystem destruction, database drops,
and custom project-specific protections. Context-aware to avoid
false positives (won't block grep/echo containing patterns), and
matches only against the part of the command the shell will actually
run — see "Execution surface" below.

Toggle with `/guard <name> on/off` (persists to ~/.claude/qute-guards.json).
"""

import ast
import json
import os
import re
import sys
from pathlib import Path

# Ensure unicode (emoji, ✓/✗) prints cleanly on Windows cp1250/cp1252 consoles.
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

NTFY_CONFIG = Path(__file__).parent.parent / "config" / "ntfy.json"


def _ntfy_url() -> str:
    """Resolve the ntfy endpoint: server + topic from config/ntfy.json,
    falling back to https://ntfy.sh/{hostname}-{username}-claude when the
    topic is unset — so one config drives alerts correctly on any machine."""
    server, topic = "https://ntfy.sh", ""
    try:
        cfg = json.loads(NTFY_CONFIG.read_text())
        server = (cfg.get("server") or server).rstrip("/")
        topic = (cfg.get("topic") or "").strip()
    except (OSError, ValueError):
        pass
    if not topic:
        import getpass
        import socket

        host = socket.gethostname().split(".")[0]
        try:
            user = getpass.getuser()
        except Exception:
            user = os.environ.get("USER") or "user"
        topic = f"{host}-{user}-claude"
    return f"{server}/{topic}"


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from guard_config import guard_enabled  # noqa: E402


def is_enabled() -> bool:
    """Whether the destructive-command guard is enabled (local guard: fails open)."""
    return guard_enabled("destructive")


# ─── Why these patterns run against a *surface*, not the raw command ──
#
# TOM-379. These regexes match command TEXT. Text is not execution, and the
# gap between the two was costing real work: an agent writing regression
# tests for the git-workflow guard had two Bash calls denied because the
# script it was writing contained `git push --force-with-lease` as a FIXTURE
# STRING inside a heredoc. It got the write through by assembling the literal
# out of fragments ("--f" + "orce-with-lease"). That is the worst outcome
# available: the guard blocked honest work, and taught the agent an
# obfuscation trick that walks past every pattern below.
#
# Three fixes were on the table. What was chosen, and why the others were not:
#
#   (1) CHOSEN — match only against the *execution surface*: blank out the
#       regions of the command the shell hands to a program as data, then run
#       the patterns unchanged. See `execution_surface()`. Scoped to two
#       region kinds (heredoc bodies into a data sink; `python -c` payloads
#       that cannot shell out), each gated on the surrounding segment being
#       free of pipes and substitutions.
#
#       The stated cost of this option was parser surface — this repo found
#       NINE parser bypasses in the sibling git-workflow guard. That cost is
#       real but it does not transfer, because the failure DIRECTION is
#       inverted. There, a parse miss meant a destructive push sailed through:
#       the parser had to be right to block. Here, `execution_surface()` only
#       ever REMOVES text from the scan, and every uncertainty resolves to
#       "leave the text in". A parse miss therefore yields a false positive —
#       the status quo — never a bypass. Hence: allowlists, never blacklists,
#       for anything that decides a region is data; unknown consumer, unknown
#       shape, or any parse error at all falls back to scanning the whole
#       original command.
#
#   (2) REJECTED — downgrade `git push --force*` from "block" to "warn".
#       Two reasons. First, it does not work: read `main()` — "warn" and
#       "block" both emit permissionDecision "deny" with a "🛑 BLOCKED"
#       reason, and severity only decides whether an ntfy alert fires. A
#       downgrade would have changed nothing that the incident was about.
#       (That warn/block conflation is pre-existing and deliberately left
#       alone here; it is not this ticket.) Second, even a working downgrade
#       is aimed at one pattern, and the bug is not about force-push — a
#       heredoc containing `rm -rf /` or `DROP TABLE` was equally stuck.
#
#       The half of option 2 that IS true: since `pre-push` landed (e6e3b15),
#       force-pushes to a protected branch are caught by git's own resolved
#       refs, for humans and scripts too — so the text match here is no
#       longer load-bearing for that case, and there is no reason to defend
#       its false positives.
#
#   (3) REJECTED — accept the false positive and document the escape. The
#       escape was already documented, by the agent, in the shape of string
#       concatenation. A guard that is routinely worked around is worse than
#       one that is off, because everyone still believes it is on.
#
# WHAT THIS GUARD IS NOT. It is a text matcher over a single Bash tool call.
# It stops the accident, not the adversary: `X="rm -rf"; $X /`, a shell
# variable, an alias, or that same fragment concatenation all defeat it and
# always did. Nothing here changes that, and no amount of parsing would —
# reach for `pre-push`, `.claude/git-guard.json`, or real branch protection
# when the threat model has an actor in it.

# ─── Pattern definitions ──────────────────────────────────────
# Each pattern: (compiled regex, description, severity)
# Severity: "block" = hard deny, "warn" = deny with explanation

GIT_PATTERNS = [
    (
        re.compile(r"\bgit\s+reset\s+--hard\b"),
        "git reset --hard destroys uncommitted changes",
        "block",
    ),
    (
        re.compile(r"\bgit\s+clean\s+-[a-zA-Z]*f"),
        "git clean -f permanently deletes untracked files",
        "block",
    ),
    (
        re.compile(r"\bgit\s+push\s+[^|]*--force\b"),
        "git push --force overwrites remote history",
        "block",
    ),
    (
        re.compile(r"\bgit\s+push\s+-f\b"),
        "git push -f overwrites remote history",
        "block",
    ),
    (
        re.compile(r"\bgit\s+stash\s+(clear|drop)\b"),
        "git stash clear/drop permanently deletes stashed work",
        "block",
    ),
    (
        re.compile(r"\bgit\s+checkout\s+--\s+\."),
        "git checkout -- . discards all working changes",
        "block",
    ),
    (
        re.compile(r"\bgit\s+restore\s+(?!--staged)[^|]*\.\s*$"),
        "git restore . discards all working changes",
        "block",
    ),
    (
        re.compile(r"\bgit\s+branch\s+-D\b"),
        "git branch -D force-deletes branch without merge check",
        "warn",
    ),
    (
        re.compile(r"\bgit\s+rebase\s+.*--force\b"),
        "forced rebase rewrites history",
        "block",
    ),
]

FILESYSTEM_PATTERNS = [
    # Unix
    (
        re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+/(?!tmp|var/tmp)"),
        "rm -rf on non-tmp root path",
        "block",
    ),
    (
        re.compile(r"\brm\s+-[a-zA-Z]*f[a-zA-Z]*r[a-zA-Z]*\s+/(?!tmp|var/tmp)"),
        "rm -fr on non-tmp root path",
        "block",
    ),
    (
        re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+~/"),
        "rm -rf in home directory",
        "block",
    ),
    (
        re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+\.\s*$"),
        "rm -rf . deletes current directory",
        "block",
    ),
    (
        re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+\.\./"),
        "rm -rf with parent traversal",
        "block",
    ),
    (
        re.compile(r"\bfind\s+.*-delete\b"),
        "find -delete permanently removes matched files",
        "warn",
    ),
    (
        re.compile(r"\bfind\s+.*-exec\s+rm\b"),
        "find -exec rm removes matched files",
        "warn",
    ),
    (re.compile(r"\b>\s*/etc/"), "overwriting system config file", "block"),
    (re.compile(r"\bmkfs\b"), "mkfs formats a filesystem", "block"),
    (re.compile(r"\bdd\s+.*of=/dev/"), "dd writing to device", "block"),
    # Windows
    (
        re.compile(r"\brmdir\s+/s", re.I),
        "rmdir /s recursively deletes directory",
        "block",
    ),
    (re.compile(r"\bdel\s+/s", re.I), "del /s recursively deletes files", "block"),
    (re.compile(r"\brd\s+/s", re.I), "rd /s recursively deletes directory", "block"),
    (
        re.compile(r"\bRemove-Item\s+.*-Recurse", re.I),
        "Remove-Item -Recurse deletes directory tree",
        "block",
    ),
    (
        re.compile(r"\bRemove-Item\s+.*-Force", re.I),
        "Remove-Item -Force bypasses safety checks",
        "warn",
    ),
    (re.compile(r"\bformat\s+[A-Z]:", re.I), "format drive command", "block"),
]

DATABASE_PATTERNS = [
    (
        re.compile(r"\bDROP\s+(DATABASE|TABLE|SCHEMA)\b", re.I),
        "DROP destroys database objects",
        "block",
    ),
    (
        re.compile(r"\bTRUNCATE\s+TABLE\b", re.I),
        "TRUNCATE deletes all rows without logging",
        "block",
    ),
    (
        re.compile(r"\bDELETE\s+FROM\s+\w+\s*;", re.I),
        "DELETE without WHERE clause deletes all rows",
        "warn",
    ),
    (re.compile(r"\bdropdb\b"), "dropdb removes entire database", "block"),
    (re.compile(r"\bdropuser\b"), "dropuser removes database user", "block"),
]

DOCKER_PATTERNS = [
    (
        re.compile(r"\bdocker\s+system\s+prune\s+-a"),
        "docker system prune -a removes all unused data",
        "block",
    ),
    (
        re.compile(r"\bdocker\s+volume\s+prune\b"),
        "docker volume prune deletes all unused volumes",
        "warn",
    ),
    (
        re.compile(r"\bdocker\s+rm\s+-f\s+\$\(docker\s+ps"),
        "mass-removing running containers",
        "block",
    ),
]

SYSTEM_PATTERNS = [
    # Unix
    (re.compile(r"\bsudo\s+rm\s+-rf\b"), "sudo rm -rf as root", "block"),
    (
        re.compile(r"\bchmod\s+-R\s+777\b"),
        "chmod -R 777 makes everything world-writable",
        "block",
    ),
    (re.compile(r"\bchown\s+-R\s+.*\s+/\s*$"), "chown -R on root filesystem", "block"),
    (re.compile(r"\bkillall\b"), "killall terminates all matching processes", "warn"),
    (
        re.compile(r"\bpkill\s+-9\s+-u\b"),
        "pkill -9 -u kills all user processes",
        "block",
    ),
    # Windows
    (
        re.compile(r"\btaskkill\s+/f\s+/im\s+\*", re.I),
        "taskkill mass-killing all processes",
        "block",
    ),
    (
        re.compile(r"\bStop-Process\s+.*-Force", re.I),
        "Stop-Process -Force kills processes",
        "warn",
    ),
    (
        re.compile(r"\bnet\s+stop\b", re.I),
        "net stop disables a Windows service",
        "warn",
    ),
    (
        re.compile(r"\bsc\s+delete\b", re.I),
        "sc delete removes a Windows service",
        "block",
    ),
    (
        re.compile(r"\breg\s+delete\s+.*\\\\.*\s+/f", re.I),
        "reg delete /f force-deletes registry keys",
        "block",
    ),
]

# ─── Custom protections for this VPS ──────────────────────────

CUSTOM_PATTERNS = [
    # Trading crons are live (07:00 quantlab = real Binance trades)
    (
        re.compile(r"\bcrontab\s+-r\b"),
        "crontab -r removes ALL cron jobs including live trading",
        "block",
    ),
    (
        re.compile(r"\bcrontab\s+/dev/null\b"),
        "crontab /dev/null wipes all cron jobs",
        "block",
    ),
    # Obsidian vaults
    (
        re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f?[a-zA-Z]*\s+/srv/obsidian\b"),
        "removing Obsidian vault data",
        "block",
    ),
    # Syncthing config
    (
        re.compile(r"\brm\s+.*\.stfolder\b"),
        "removing Syncthing folder marker breaks sync",
        "block",
    ),
    # Production quantlab
    (
        re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f?[a-zA-Z]*\s+.*/prod/quantlab\b"),
        "removing production trading code",
        "block",
    ),
]

ALL_PATTERNS = (
    GIT_PATTERNS
    + FILESYSTEM_PATTERNS
    + DATABASE_PATTERNS
    + DOCKER_PATTERNS
    + SYSTEM_PATTERNS
    + CUSTOM_PATTERNS
)


# ─── Context detection (avoid false positives) ────────────────
#
# `is_safe_context()` lives with the rest of the data-only machinery, below
# `execution_surface()` — see "Data-only stages". It used to live here and
# answer from a PREFIX; TOM-394 replaced that with a per-stage judgement, and
# the two now share one predicate.


# ─── Execution surface ────────────────────────────────────────
#
# `execution_surface(command)` returns a string the SAME LENGTH as `command`
# with data regions overwritten by spaces (newlines preserved, so `^`/`$` and
# line structure behave exactly as they did before). Patterns then run on it
# unchanged — no pattern needs to know this exists.
#
# Only two region kinds are ever blanked, and only inside a segment that
# contains no `|`, no `$(`, no backtick and no process substitution, because
# each of those can turn "data" back into "commands":
#
#   heredoc body → a data sink   `cat > f <<'EOF' … EOF`, `tee f <<EOF … EOF`
#       The sink list is an ALLOWLIST of two commands that cannot execute
#       their stdin. `bash <<EOF`, `ssh host <<EOF`, `psql <<EOF` and every
#       other consumer keep their body scanned — an unlisted consumer is
#       assumed to execute. For an UNQUOTED delimiter (`<<EOF`, not
#       `<<'EOF'`) the shell still runs command substitutions in the body, so
#       a body containing `$(` or a backtick is not exempt at all.
#
#   `python -c <payload>`        …and `python3 - <<'PY' … PY`
#       Exempt only when python is genuinely reading that region AS ITS OWN
#       SOURCE — `-c` as the interpreter's own flag, or stdin when the
#       invocation is `python3 -` / bare `python3`. `python3 runner.py <<EOF`
#       and `python3 runner.py -c '…'` hand the region to an arbitrary script
#       instead, so they stay scanned; so do `-m` and option bundles like
#       `-uc`, which this code will not try to take apart.
#       Exempt only when the payload provably cannot reach a shell, decided
#       by an ALLOWLIST over its parsed AST (`_python_payload_is_inert`): no
#       imports, and every call target a safe builtin or a safe method. A
#       deny-list of names would be defeated by `getattr(os, 'sys' + 'tem')`,
#       which is the fragment trick again. Python is the only interpreter:
#       every other one (`perl -e`, `node -e`, `ruby -e`, and notably
#       `psql -c` / `mysql -e`, whose payloads the DATABASE_PATTERNS are
#       *about*) would need its own shell-out vocabulary, and an incomplete
#       vocabulary is a bypass rather than a false positive.
#
# Third, and cutting across both: a data region is exempt only when NOTHING
# ELSE in the same Bash call can run a program (`INERT_PROGRAMS`). Writing a
# file and executing it are two steps, and they fit in one tool call:
#
#     cat > /tmp/x <<'EOF'
#     rm -rf /srv/data
#     EOF
#     bash /tmp/x
#
# Blanking that body would hide a command the very next line runs. So one
# non-inert segment anywhere voids every exemption in the call.
#
# CASES THIS DELIBERATELY STILL BLOCKS, because they cannot be told apart
# from execution by looking at the text:
#   * `python3 -c "os.system('rm -rf /x')"` — and, unavoidably, any payload
#     that imports anything at all or calls something off the AST allowlist,
#     however innocent its intent.
#   * any interpreter other than python: `perl -e '…'`, `node -e '…'`.
#   * a heredoc into anything but `cat`/`tee`, including `sudo tee`.
#   * anything in the same call as a program that could execute a file —
#     `bash`, `.`, `make`, `./script`, or a name not on the inert allowlist.
#   * any of the above when the segment also pipes or substitutes.
#
# …and two shapes it blocks purely because this code declines to parse them,
# raised in review and left as-is ON PURPOSE. Both fail toward blocking, and
# the fix for each is more shell parsing — which is what produced four separate
# bypasses in review before this landed. Widen them only with tests that prove
# the widening cannot exempt something executable:
#
#     python3 -c "open(f,'w').write(\"…\")"   escaped quotes inside the payload:
#                                             `_dash_c_payload` stops at the
#                                             first raw quote, so the tail of
#                                             the payload stays scanned.
#     python3 -W ignore -c "…"                `_python_source_mode` cannot tell
#                                             an option's VALUE from a script
#                                             name, so `ignore` reads as a
#                                             script and the payload is not
#                                             exempt. `python3 -u -c` works —
#                                             flags that take no value are fine.
#
# The route for any of this is the Write tool (never screened by this guard —
# it only matches Bash) or `/guard destructive off` for the one session.

# stdin consumers that cannot execute what they read.
HEREDOC_DATA_SINKS = frozenset({"cat", "tee"})

# Interpreters whose payload is exempt when it cannot shell out.
_PYTHON_CMD = re.compile(r"\Apython[0-9.]*\Z")

# Programs that cannot run another program, so their presence elsewhere in the
# command does not put a blanked region back into play. An ALLOWLIST: anything
# not named here — `bash`, `.`, `sudo`, `make`, `npm`, `./script`, or simply a
# name this file has never heard of — voids every exemption in the command.
#
# The bar is "no option to this program spawns another one", and it is stricter
# than intuition. Three obvious-looking candidates are deliberately ABSENT:
#
#     git   `git -c alias.x='!bash /tmp/x' x`, and hooks, difftool,
#           mergetool, `-c core.pager=…`, submodule helpers
#     sort  `sort --compress-program=/tmp/x`
#     rg    `rg --pre=/tmp/x`
#
# Each would let a call write a script and run it while every segment still
# looked harmless. `git` costs the most to leave out — `… <<'EOF' … EOF; git add
# f` now loses the exemption — and it goes out anyway, because an allowlist that
# admits one program with an exec escape is not an allowlist.
INERT_PROGRAMS = frozenset(
    {
        "cat", "tee", "echo", "printf", "true", "false", "test", "[",
        "ls", "pwd", "cd", "mkdir", "rmdir", "touch", "mktemp",
        "chmod", "chown", "chgrp", "cp", "mv", "ln", "rm",
        "stat", "file", "wc", "head", "tail", "uniq", "cut", "tr",
        "diff", "cmp", "grep", "egrep", "fgrep",
        "date", "sleep", "basename", "dirname", "realpath", "readlink",
    }
)  # fmt: skip

# Calls a python payload may make and still count as "only writes files and
# shuffles strings". An ALLOWLIST checked against the parsed AST, not the text:
# a deny-list of names (`os.system`, `subprocess`, …) is defeated by one
# `getattr(os, 'sys' + 'tem')`, which is exactly the fragment trick this ticket
# exists to stop rewarding. Anything else — any import at all, any call whose
# target is not one of these, any payload that will not parse — is not exempt.
_PY_SAFE_CALLS = frozenset(
    {"open", "print", "str", "repr", "len", "int", "float", "bool", "list",
     "dict", "tuple", "set", "sorted", "range", "enumerate", "zip", "format"}
)  # fmt: skip
_PY_SAFE_METHODS = frozenset(
    {"write", "writelines", "read", "readlines", "close", "flush",
     "join", "format", "replace", "strip", "lstrip", "rstrip", "split",
     "splitlines", "encode", "decode", "startswith", "endswith", "upper",
     "lower", "title", "append", "extend", "insert", "items", "keys",
     "values", "get", "count", "index", "ljust", "rjust", "zfill"}
)  # fmt: skip


def _python_payload_is_inert(source: str) -> bool:
    """Whether a python program provably cannot reach a shell.

    Allowlist over the AST: no imports, and every call target must be a
    builtin from `_PY_SAFE_CALLS` or a method from `_PY_SAFE_METHODS`. A
    syntax error means "not exempt" — a payload this code cannot parse is a
    payload it cannot vouch for.
    """
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, MemoryError, RecursionError):
        return False
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            return False
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in _PY_SAFE_CALLS:
                continue
            if isinstance(func, ast.Attribute) and func.attr in _PY_SAFE_METHODS:
                continue
            return False
    return True


# Turns a "data" region back into commands, so it disqualifies the segment.
_SEGMENT_DISQUALIFIERS = ("|", "$(", "`", ">(", "<(")

# `<<`, optional `-`, optional whitespace, then the delimiter word — quoted
# ('EOF' / "EOF"), backslash-escaped (\EOF), or bare (EOF).
_HEREDOC_DELIM = re.compile(
    r"""<<-?[ \t]*(?:
          (?P<q>['"])(?P<qword>[^'"]+)(?P=q)
        | (?P<bs>\\)?(?P<word>[A-Za-z_][A-Za-z0-9_]*)
    )""",
    re.VERBOSE,
)

# A token that is a redirection (`>f`, `2>&1`, `<in`) or an env assignment
# (`FOO=bar`) — neither is a command word nor an argument.
_NOT_A_COMMAND_WORD = re.compile(r"\A(?:\d*[<>]|[A-Za-z_][A-Za-z0-9_]*=)")

# A redirection operator standing alone, whose target is the NEXT token.
_REDIR_OP = re.compile(r"\A\d*(?:>>|>&|<&|>|<)\Z")

# `$(...)`/backticks inside an unquoted heredoc body still expand.
# Inside an UNQUOTED heredoc (`<<EOF`, not `<<'EOF'`) the shell still runs
# command substitutions. An earlier version tried to carve the substituted
# SPANS back out of the blanked body with a regex; that regex stopped at the
# first `)`, and `$(printf ')' ; rm -rf /srv/data)` put that `)` inside quotes
# — so the tail of a substitution the shell really executes got blanked.
# Finding the true end of a substitution needs a shell parser. Rather than
# grow one, an unquoted body carrying either marker is simply not exempt.
_SUBSTITUTION_MARKERS = ("$(", "`")


def _split_segments(line: str, base: int = 0):
    """Split one line into command segments on unquoted `;`, `&`, `&&`, `||`.

    `|` is NOT a separator here: a pipe inside a segment disqualifies it from
    every exemption, so it has to stay visible. Returns (start, end) offsets
    relative to `base`.
    """
    segments = []
    start, i, n, quote = 0, 0, len(line), None
    while i < n:
        c = line[i]
        if quote:
            if c == "\\" and quote == '"':
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if c in "'\"":
            quote = c
            i += 1
            continue
        if c == "\\":
            i += 2
            continue
        if line[i : i + 2] in ("&&", "||"):
            segments.append((base + start, base + i))
            i += 2
            start = i
            continue
        if c == "&" and (
            line[i - 1 : i] in ("<", ">", "|") or line[i + 1 : i + 2] == ">"
        ):
            # `2>&1`, `>&2`, `&>log` — fd duplication, NOT a separator. Getting
            # this wrong split the segment before a later `|`, which hid the
            # pipe from `_segment_is_plain` and exempted a payload that a shell
            # then executed: `python3 -c '…' 2>&1 | bash`.
            #
            # `|&` is the same trap wearing a different hat (TOM-394): it is
            # bash's pipe-with-stderr, one operator. Splitting it left the
            # first segment ending in a bare `|`, so the stage after the pipe
            # was the EMPTY STRING — which runs nothing, and therefore did not
            # stop `echo 'rm -rf /srv/data' |& bash` having its echo blanked.
            i += 1
            continue
        if c in ";&":
            segments.append((base + start, base + i))
            i += 1
            start = i
            continue
        i += 1
    segments.append((base + start, base + n))
    return segments


def _heredoc_openers(segment: str):
    """Heredoc delimiters opened in `segment`, left to right.

    Returns [(delimiter_word, delimiter_was_quoted), ...]. Skips `<<` that
    appears inside quotes, and `<<<` (a here-string, which stays scanned).

    The `<<<` skip is belt-and-braces: mutation testing showed removing it
    changes nothing, because `_HEREDOC_DELIM` requires a quote or a word
    character immediately after `<<` and a here-string's third `<` is
    neither. Kept so that loosening that regex later cannot silently start
    treating here-strings as heredocs. Either way a here-string can never be
    exempted — its payload sits on the operator's own line, and this function's
    caller only ever blanks whole *subsequent* lines.
    """
    openers = []
    i, n, quote = 0, len(segment), None
    while i < n:
        c = segment[i]
        if quote:
            if c == "\\" and quote == '"':
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if c in "'\"":
            quote = c
            i += 1
            continue
        if c == "\\":
            i += 2
            continue
        if segment[i : i + 3] == "<<<":
            i += 3
            continue
        if segment[i : i + 2] == "<<":
            m = _HEREDOC_DELIM.match(segment, i)
            if m:
                word = m.group("qword") or m.group("word")
                openers.append((word, bool(m.group("q") or m.group("bs"))))
                i = m.end()
                continue
            i += 2
            continue
        i += 1
    return openers


# Everything accumulated so far is itself part of a redirection operator, so a
# `<`/`>` here CONTINUES it rather than starting a new one: `>>`, `2>&1`, `&>`.
_IS_REDIR_PREFIX = re.compile(r"\A[0-9<>&]*\Z")


def _has_unquoted(text: str, chars: str) -> bool:
    """Whether any of `chars` appears in `text` outside quotes/escapes."""
    i, n, quote = 0, len(text), None
    while i < n:
        c = text[i]
        if quote:
            if c == "\\" and quote == '"':
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if c in "'\"":
            quote = c
            i += 1
            continue
        if c == "\\":
            i += 2
            continue
        if c in chars:
            return True
        i += 1
    return False


def _token_spans(text: str):
    """(start, end) of every whitespace-separated token, respecting quotes.

    `str.split()` does not, in two ways that both cost a bypass.

    QUOTES. It reads `FOO='x cat' bash <<'EOF'` as five words, the second of
    which is `cat'`. `_split_command` then stripped the quote, called the
    program `cat` — a heredoc DATA SINK — and blanked a body that `bash` went
    on to execute. A quoted value must not be able to donate a word.

    REDIRECTIONS, which the shell does not require whitespace around. `echo
    rm -rf /srv/data>/tmp/x` is four words and a redirection to bash; to
    `str.split()` it is `/srv/data>/tmp/x`, one argument, and `_stage_writes_a_file`
    saw no write at all — so route 3 let the text be blanked while the next
    command ran the file. The same mis-parse read `foo>/tmp/cat <<'EOF'` as
    the program `cat`, making an arbitrary program's heredoc look like data.
    Splitting before a glued operator fixes both, and `cat>/tmp/f <<'EOF'` —
    previously a false positive — starts working for the same reason.
    (Review on #91, round 4.)
    """
    spans, i, n = [], 0, len(text)
    while i < n:
        while i < n and text[i].isspace():
            i += 1
        if i >= n:
            break
        start, quote = i, None
        while i < n:
            c = text[i]
            if quote:
                if c == "\\" and quote == '"':
                    i += 2
                    continue
                if c == quote:
                    quote = None
                i += 1
                continue
            if c in "'\"":
                quote = c
                i += 1
                continue
            if c == "\\":
                i += 2
                continue
            if c.isspace():
                break
            if c in "<>" and i > start and not _IS_REDIR_PREFIX.match(text[start:i]):
                break  # a redirection glued to the end of a word: `cat>f`
            i += 1
        spans.append((start, min(i, n)))
    return spans


def _split_command(segment: str):
    """(program, argument tokens) for a segment, or ("", []).

    Leading env assignments and redirections are skipped, and redirections are
    dropped from the argument list — `python3 > out - <<EOF` has to read as
    "python, arg `-`", not "python, arg `out`".
    """
    tokens = [segment[a:b] for a, b in _token_spans(segment)]
    i = 0
    while i < len(tokens) and _NOT_A_COMMAND_WORD.match(tokens[i]):
        if _REDIR_OP.match(tokens[i]):
            i += 1  # bare operator: its target is the next token
        i += 1
    if i >= len(tokens):
        return "", []
    program = tokens[i].strip("'\"").rsplit("/", 1)[-1]
    args, i = [], i + 1
    while i < len(tokens):
        token = tokens[i]
        if token.startswith("<<"):
            i += 1
        elif _REDIR_OP.match(token):
            i += 2  # operator plus its target
        elif _NOT_A_COMMAND_WORD.match(token):
            i += 1  # redirection with the target attached, e.g. `2>&1`
        else:
            args.append(token)
            i += 1
    return program, args


def _command_word(segment: str) -> str:
    """The program a segment runs, basename-only, or "" if undeterminable."""
    return _split_command(segment)[0]


def _python_source_mode(args: list) -> str:
    """Where a python invocation gets its program: stdin / dash_c / file.

    Only `stdin` makes a heredoc body python *source*, and only `dash_c` makes
    the quoted payload python source. `python3 runner.py <<EOF` hands the body
    to an arbitrary script that may do anything with it, so it is `file` — the
    same bucket as `-m`, a script path, or an option bundle like `-uc` that
    this function will not try to take apart.
    """
    for token in args:
        if token == "-":
            return "stdin"
        if token == "--":
            # Option terminator: everything after it is a SCRIPT FILENAME, so
            # `python3 -- -c` runs a file called `-c`, it does not take a `-c`
            # flag. Reading it as the flag would exempt the payload and mark
            # the segment inert while python ran a file the same call wrote.
            return "file"
        if token == "-c":
            return "dash_c"
        if token.startswith("-") and len(token) > 1:
            if "c" in token[1:] or "m" in token[1:]:
                return "file"
            continue  # a benign flag: -u, -E, -B, …
        return "file"  # a script path, a module name, or an option's value
    return "stdin"  # bare `python3 <<EOF`: stdin *is* the program


def _segment_is_plain(segment: str) -> bool:
    """No pipe / substitution — i.e. nothing that re-executes a data region."""
    return not any(token in segment for token in _SEGMENT_DISQUALIFIERS)


def _dash_c_payload(segment: str):
    """(start, end) of a `python -c '<payload>'` body inside `segment`."""
    m = re.search(r"(?:\A|\s)-c[ \t]*(['\"])", segment)
    if not m:
        return None
    start = m.end()
    end = segment.find(m.group(1), start)
    return None if end == -1 else (start, end)


def _heredoc_body_is_data(segment: str, body: str) -> bool:
    program, args = _split_command(segment)
    if program in HEREDOC_DATA_SINKS:
        return True
    if _PYTHON_CMD.match(program) and _python_source_mode(args) == "stdin":
        return _python_payload_is_inert(body)
    return False


def _scan_layout(command: str):
    """(heredocs, segments) for the whole command.

    heredocs: (quoted, seg_start, seg_end, body_start, body_end) per opener.
    segments: char ranges of every command segment, EXCLUDING heredoc body and
    terminator lines — those are data (or a delimiter), not commands.
    """
    lines, offset = [], 0
    for line in command.split("\n"):
        lines.append((offset, line))
        offset += len(line) + 1

    heredocs, segments, idx = [], [], 0
    while idx < len(lines):
        line_start, line = lines[idx]
        pending = []
        for seg_start, seg_end in _split_segments(line, line_start):
            segments.append((seg_start, seg_end))
            for word, quoted in _heredoc_openers(command[seg_start:seg_end]):
                pending.append((word, quoted, seg_start, seg_end))
        idx += 1
        for word, quoted, seg_start, seg_end in pending:
            body_start = lines[idx][0] if idx < len(lines) else len(command)
            body_end = body_start
            while idx < len(lines):
                l_start, l_text = lines[idx]
                if l_text.strip() == word:
                    idx += 1  # consume the terminator line
                    break
                body_end = l_start + len(l_text)
                idx += 1
            heredocs.append((quoted, seg_start, seg_end, body_start, body_end))
    return heredocs, segments


def _segment_can_run_a_program(command: str, seg_range, bodies: dict) -> bool:
    """Whether a segment could execute something — including a file that
    another segment in the same call just wrote.

    This is the answer to "write it, then run it in one Bash call":

        cat > /tmp/x <<'EOF'
        rm -rf /srv/data
        EOF
        bash /tmp/x

    Blanking the body while `bash /tmp/x` sits in the same command would hide
    a command that then runs. So a single non-inert segment anywhere voids
    every exemption in the call. Allowlist, so an unrecognised program counts
    as an executor.
    """
    segment = command[seg_range[0] : seg_range[1]]
    # A pipe or a substitution reaches a program the command word never names:
    # `cat /tmp/x | bash` resolves to `cat`, and runs `bash`. So the metachar
    # check gates the WHOLE call here, not just the segment owning the data.
    if not _segment_is_plain(segment):
        return True
    program, args = _split_command(segment)
    if not program:
        return False
    if program in INERT_PROGRAMS:
        return False
    if _PYTHON_CMD.match(program):
        # Python counts as inert only if the source it is about to run is
        # itself inert — otherwise it is a program that could run `/tmp/x`.
        mode = _python_source_mode(args)
        if mode == "dash_c":
            span = _dash_c_payload(segment)
            return not (span and _python_payload_is_inert(segment[span[0] : span[1]]))
        if mode == "stdin":
            body = bodies.get(seg_range)
            return body is None or not _python_payload_is_inert(body)
    return True


def _blank(chars: list, start: int, end: int) -> None:
    """Overwrite [start, end) with spaces, keeping newlines so `$`/`^` hold."""
    for i in range(start, end):
        if chars[i] != "\n":
            chars[i] = " "


def _blank_heredoc_bodies(command: str, chars: list, heredocs) -> None:
    for quoted, seg_start, seg_end, body_start, body_end in heredocs:
        segment = command[seg_start:seg_end]
        body = command[body_start:body_end]
        if not _segment_is_plain(segment):
            continue
        if not _heredoc_body_is_data(segment, body):
            continue
        if not quoted and any(mark in body for mark in _SUBSTITUTION_MARKERS):
            continue  # the shell will run something in there — scan all of it
        _blank(chars, body_start, body_end)


def _blank_python_c_payloads(command: str, chars: list, segments) -> None:
    for seg_start, seg_end in segments:
        segment = command[seg_start:seg_end]
        if not _segment_is_plain(segment):
            continue
        program, args = _split_command(segment)
        if not _PYTHON_CMD.match(program):
            continue
        # `-c` must be the INTERPRETER's, not an argument that happens to
        # follow a script name (`python3 runner.py -c "…"` hands the string
        # to runner.py, which may do anything with it).
        if _python_source_mode(args) != "dash_c":
            continue
        span = _dash_c_payload(segment)
        if not span:
            continue
        if not _python_payload_is_inert(segment[span[0] : span[1]]):
            continue
        _blank(chars, seg_start + span[0], seg_start + span[1])


def execution_surface(command: str) -> str:
    """The part of `command` the shell will run, with data regions blanked.

    Same length as the input, so every existing pattern (including the
    `$`-anchored ones) keeps its exact meaning. Any failure returns the
    command untouched: falling back to scanning everything reproduces the
    old behaviour, which errs toward blocking.
    """
    try:
        # `_scan_layout` reads PHYSICAL lines, but bash joins a line ending in
        # a backslash with the next one before parsing. `cat <<'EOF' \` +
        # `| bash` is one pipeline to the shell and two lines here — enough to
        # hide the pipe and get the body blanked. Reconstructing logical lines
        # would move every offset this design depends on, so a continuation
        # anywhere simply forfeits every exemption. The cost is a heredoc body
        # whose own line ends in a backslash: also not exempt, also blocked.
        if "\\\n" in command:
            return command
        heredocs, segments = _scan_layout(command)
        bodies = {(s, e): command[bs:be] for _q, s, e, bs, be in heredocs}
        chars = list(command)
        # One executor anywhere in the call voids every exemption in it: it
        # could run a file another segment just wrote.
        if not any(
            _segment_can_run_a_program(command, seg, bodies) for seg in segments
        ):
            _blank_heredoc_bodies(command, chars, heredocs)
            _blank_python_c_payloads(command, chars, segments)
        # Arguments of a data-only stage (`grep …`, `echo …`). Gated per
        # stage rather than per call — see "Data-only stages" below.
        _blank_data_only_stages(command, chars, segments, bodies)
        return "".join(chars)
    except Exception:
        return command


# ─── Data-only stages ─────────────────────────────────────────
#
# TOM-394. `is_safe_context()` used to decide, from a PREFIX, that an ENTIRE
# command was harmless — and every pattern above was then skipped for every
# command chained after that prefix. Six prefixes did it. All six were the
# same bug, and the cheapest of them was `^[A-Z_]+=`:
#
#     FOO=1 rm -rf /srv/data                  ← assignment prefix: exempt
#     echo hi && rm -rf /srv/data             ← echo prefix: exempt
#     grep -r x . ; rm -rf /srv/data          ← grep prefix: exempt
#     # note⏎rm -rf /srv/data                 ← comment prefix: exempt
#     man rm ; rm -rf /srv/data               ← man prefix: exempt
#     rsync --dry-run a b && rm -rf /srv/data ← dry-run prefix: exempt
#
# Each cost nothing to type, needed no knowledge of this file, and failed
# silently — no output, no signal that the guard had been skipped. (A seventh,
# bare `-n`, was removed earlier; its comment is preserved below.)
#
# THE PREFIX WAS NEVER THE POINT. What those rules were reaching for is that
# some programs treat their command line as TEXT: `grep` searches for it,
# `echo` prints it, `man` looks it up. That is a property of one stage, not of
# a line. So the judgement is per stage, and it feeds the same execution
# surface as everything else: a data-only stage has its ARGUMENTS blanked, and
# every other stage in the call stays fully scanned.
#
# Blanking arguments rather than the whole stage is not fussiness. A
# redirection is an ACTION, not data, so the operator and its target survive
# on the surface: `printf 'x' > /etc/passwd` keeps its `> /etc/passwd`, where
# the old `^(echo|printf)` prefix rule exempted the whole line.
#
#   (It is still not BLOCKED, for an unrelated reason: the pattern is
#   `\b>\s*/etc/`, and `\b` before `>` demands a word character immediately
#   to its left — so it matches `foo>/etc/passwd` and misses every ordinary
#   spelling, `> /etc/passwd` included. That is a defect in the pattern, not
#   in this exemption; it predates TOM-394 and is reported separately rather
#   than fixed here. The surface behaviour above is asserted directly, by
#   `TestDataOnlyStagesOnTheSurface`, so it holds whatever the pattern does.)
#
# WHAT STILL EXEMPTS A COMMAND, and why:
#
#   * a data-only PROGRAM (`TEXT_ONLY_PROGRAMS`) — allowlist of text search
#     and print tools — UNLESS the invocation hands it a command to run
#     (`EXEC_OPTIONS`), because then the destructive text can be that option's
#     value: `rg --pre 'rm -rf /srv/data' needle .`.
#   * `<prog> --help` and nothing else — narrower than the old rule's
#     `^\w+\s+--help`, so no other argument can ride along. `rm -rf / --help`
#     is still scanned.
#   * a dry-run flag, but only for a program that HAS one (`DRY_RUN_PROGRAMS`)
#     and only when every argument is a BARE WORD (`_is_a_bare_word`). The old
#     rule searched the flag anywhere in the first segment for any program at
#     all, so `rm -rf /srv/data --dry-run` was exempt — `rm` has no such flag
#     and would have deleted the path. The bare-word half is what stops
#     `git -c alias.x='!rm -rf /srv/data' x --dry-run` and its unquoted
#     sibling `git -c alias.x=!killall x -- --dry-run`: every program with a
#     dry-run flag can also be made to run something, and every spelling of
#     that carries the command in an OPTION VALUE — which needs quoting,
#     whitespace, or an `=`.
#   * a stage that is only assignments and redirections (`FOO=bar`) — nothing
#     runs — but only when nothing in the call can execute, because a shell
#     variable is a channel to a later stage exactly as a file is:
#     `foo='rm -rf /srv/data'; bash -c "$foo"` is scanned, not blanked. A value
#     assembled ACROSS the expansion (`X="rm -rf"; $X /`) remains the
#     documented, unfixable limitation at the top of this file.
#   * a comment stage.
#
# …and the gate over all of it. Blanking a stage hides its text, so it is
# allowed only when that text cannot reach something that RUNS it. There are
# exactly three routes out of a stage, and one condition each:
#
#   1. the stage's own program — it is data-only, so its arguments are text
#      to it by construction. Unless the stage carries `$(…)`, a backtick or
#      a process substitution, which the shell runs before the program ever
#      sees them: `_segment_is_plain`.
#   2. its STDOUT, down the pipeline — so no LATER stage in the pipeline may
#      be able to execute anything. `echo 'rm -rf /srv/data' | bash` is caught
#      here; `rg 'rm -rf /srv' . | wc -l` is not, because `wc` cannot run it.
#   3. a FILE — if the stage, or anything downstream of it in the pipeline,
#      redirects the output or writes it with `tee` (or `cp`/`mv` handed
#      `/dev/stdin`) — and then something else in the call could run that
#      file. So THAT case, and only that case, takes the call-wide gate:
#
#          echo 'rm -rf /srv/data' > /tmp/x ; bash /tmp/x
#
#      the write-then-execute shape the heredoc rules already defend against.
#
# Route 3 is why "can execute" is judged by TOM-379's `_segment_can_run_a_program`
# with NO widening for text tools. `rg --pre=/tmp/x`, `man -P /tmp/x` and
# `ack --pager=/tmp/x` really do run a named file, so they must count as
# executors — and they do, by simply not being on `INERT_PROGRAMS`. That costs
# nothing this exemption was for: those tools are still data-only, so their own
# arguments are still blanked, and `rg 'rm -rf /srv' . | wc -l` still passes
# under route 2. No option denylist is needed anywhere.
#
# `_call_can_execute` differs from the strict gate in one way only: it looks at
# PIPELINE STAGES, so a pipe by itself is not an executor when no stage in it
# can execute.

# Programs whose command line is TEXT: they search it or print it, and never
# execute it. An ALLOWLIST — an unknown program is an executor.
#
# `man`, `info`, `help`, `whatis` and `apropos` were on this list and are
# deliberately OFF it (review on #91, round 3). `man -P CMD`, `-H CMD`,
# `-e CMD` and `-C FILE` all hand man a command to run, and the list bought
# nothing to weigh against that: no realistic `man …` invocation contains text
# any pattern matches, so `man rm` was never allowed BECAUSE of this list.
TEXT_ONLY_PROGRAMS = frozenset(
    {
        "grep", "egrep", "fgrep", "zgrep", "zegrep", "zfgrep",
        "rg", "ag", "ack", "ack-grep",
        "echo", "printf",
    }
)  # fmt: skip

# Options that hand a text tool a COMMAND. A tool carrying one is NOT
# data-only, because the destructive text can BE that option's value:
# `rg --pre 'rm -rf /srv/data' needle .` (review on #91, round 3).
#
# Only the four members of TEXT_ONLY_PROGRAMS that are not also on
# INERT_PROGRAMS need an entry — the grep family, `echo` and `printf` are on
# that allowlist, which already asserts that no option of theirs spawns a
# program. An allowlist of BENIGN options is not available here: `rg` alone has
# well over a hundred. So this is a list of the executing ones, and the failure
# direction is stated rather than hidden — a spelling missing from it leaves
# the stage data-only, which is where the file stood before the list existed;
# an entry present can only ever take an exemption away. The bare-word rule on
# the dry-run exemption below is the second, program-agnostic net.
EXEC_OPTIONS = {
    "rg": ("--pre", "--hostname-bin"),
    "ag": ("--pager",),
    "ack": ("--pager", "--ackrc"),
    "ack-grep": ("--pager", "--ackrc"),
}

# Programs that actually HAVE a dry-run flag, so claiming one means something.
# `rm --dry-run` does not exist; `rm` is not here, and `rm -rf /x --dry-run`
# is scanned like any other `rm -rf`.
DRY_RUN_PROGRAMS = frozenset(
    {
        "git", "rsync", "make", "gmake",
        "docker", "docker-compose", "podman", "kubectl", "helm",
        "terraform", "terragrunt", "ansible", "ansible-playbook",
        "apt", "apt-get", "yum", "dnf", "brew",
        "npm", "pnpm", "yarn", "pip", "pip3", "uv", "poetry", "cargo",
        "gh", "rclone", "restic", "borg",
    }
)  # fmt: skip

# Dry-run flags — LONG FORMS ONLY.
#
# This exemption skips ALL patterns above for the stage, so it has to be
# narrower than what it protects. It used to include bare `-n`, which is a
# dry-run flag for make/rsync/git-clean and something else entirely everywhere
# else: line numbers (grep), numeric sort (sort), a count (head/tail), quiet
# (sed), no-clobber (cp/mv), batch size (xargs). `\b` only needs a non-word
# char after the n, so `head -n 20` disarmed the guard — and because the search
# spanned the whole string, it disarmed it for every command chained alongside:
# `rm -rf /srv/data && tail -n 50 log` was exempt. So was
# `find . -type f | xargs -n 1 rm -rf`.
_DRY_RUN_FLAG = re.compile(r"\A--(?:dry-run|dryrun|check|whatif|just-print)(?:=|\Z)")

_ASSIGNMENT = re.compile(r"\A[A-Za-z_][A-Za-z0-9_]*=")

# Programs that can put their STDIN into a file named in their ARGUMENTS, so a
# pipeline ending in one lands the piped text on disk with no `>` in sight.
# Only members of INERT_PROGRAMS need naming here — anything off that allowlist
# already counts as an executor and gates the call by itself, which is why
# `dd of=…` and `sponge` are absent.
#
# `tee` does it by definition. `cp` and `mv` do it only when handed a path that
# IS stdin, so they are checked for one rather than assumed: reading every
# `cp` as a stdin writer blocked `echo … | cp a b ; bash /tmp/x`, where the
# text goes nowhere near a file (review on #91, round 5).
STDIN_WRITERS = frozenset({"tee"})
STDIN_PATH_WRITERS = frozenset({"cp", "mv"})
_STDIN_PATHS = frozenset({"/dev/stdin", "/dev/fd/0", "/proc/self/fd/0"})

# `2>&1`, `>&2`, `>&-` duplicate or close a descriptor; they do not open a file.
_FD_DUP = re.compile(r"\A(?:\d*|&)>&(?:\d+|-)\Z")
# `>f`, `>>f`, `2>f`, `&>f`, and the bare operators.
_REDIRECTS_OUTPUT = re.compile(r"\A(?:&|\d*)>{1,2}")


def _pipeline_stages(command: str, seg_range):
    """Char ranges of the pipeline stages inside one segment.

    `_split_segments` deliberately leaves `|` inside a segment, because a pipe
    disqualifies that segment from the heredoc/python exemptions. Deciding
    whether a stage's ARGUMENTS are data needs the finer view: in
    `grep 'rm -rf /srv/data' . | wc -l` the pattern is data and `wc` cannot
    execute it, while in `echo 'rm -rf /srv/data' | bash` it plainly can.
    `||` never reaches here — `_split_segments` already split on it — and `>|`
    is a clobber operator, not a pipe.
    """
    start, end = seg_range
    text = command[start:end]
    stages, seg_start, i, n, quote = [], 0, 0, end - start, None
    while i < n:
        c = text[i]
        if quote:
            if c == "\\" and quote == '"':
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if c in "'\"":
            quote = c
            i += 1
            continue
        if c == "\\":
            i += 2
            continue
        if c == "|" and text[i - 1 : i] != ">":
            stages.append((start + seg_start, start + i))
            # `|&` is ONE operator, so the next stage starts after both
            # characters. Consuming only the `|` left the stage reading `&
            # grep x`, whose program parsed as `&` — not on any allowlist, so
            # an inert `… |& grep` looked executable (review on #91, round 7).
            i += 2 if text[i + 1 : i + 2] == "&" else 1
            seg_start = i
            continue
        i += 1
    stages.append((start + seg_start, start + n))
    return stages


def _stage_is_data_only(stage: str) -> bool:
    """Whether this stage treats its command line as text rather than action."""
    stripped = stage.strip()
    if not stripped:
        return True
    if stripped.startswith("#"):
        return True
    program, args = _split_command(stage)
    if not program:
        return True  # assignments and/or redirections only — nothing runs
    if program in TEXT_ONLY_PROGRAMS:
        return not _carries_an_exec_option(program, args)
    if args == ["--help"]:
        return True
    if (
        program in DRY_RUN_PROGRAMS
        and any(_DRY_RUN_FLAG.match(a) for a in args)
        and all(_is_a_bare_word(a) for a in args)
    ):
        return True
    return False


def _carries_an_exec_option(program: str, args: list) -> bool:
    """Whether a text tool was handed a command to run — see `EXEC_OPTIONS`."""
    for option in EXEC_OPTIONS.get(program, ()):
        for arg in args:
            if arg == option or arg.startswith(option + "="):
                return True
            if not option.startswith("--") and arg.startswith(option) and arg != option:
                return True  # a short option with its value attached: `-Pless`
    return False


def _is_a_bare_word(token: str) -> bool:
    """A flag, a subcommand or a path: no quoting, no whitespace, no `=`.

    The dry-run exemption's program-agnostic net, and the reason it needs no
    per-program option table (review on #91, round 3). Every program with a
    dry-run flag can also be made to run something, and every spelling of that
    puts a command into an OPTION VALUE:

        git -c alias.x='!rm -rf /srv/data' x --dry-run
        git -c alias.x=!killall x -- --dry-run
        git -c core.pager=mkfs clean -fd --dry-run
        rsync -e 'rm -rf /srv/data' --dry-run src dst
        make --eval='$(shell rm -rf /srv/data)' --just-print

    Quoting and whitespace catch the multi-word ones. `=` catches the rest: a
    value carried inside a single token needs it, and so do the one-word
    commands that fit in such a token — `mkfs`, `dropdb`, `dropuser`,
    `killall`, the only patterns that match a single word. Round 3 excluded
    only quoting and whitespace, and said so in a comment that the second
    example above contradicts; `=` is the correction (round 6).

    A real dry run needs none of the three: `git clean -fd --dry-run`,
    `rsync --dry-run -a /srv/data /backup/`, `make --just-print clean` and
    `docker system prune -a --dry-run` are bare words end to end.

    Not applied to the text tools, whose whole point is a quoted pattern; they
    have `EXEC_OPTIONS` instead.

    What remains, stated rather than left to be found: an option value passed
    as a SEPARATE bare token, `git --exec-path /tmp/mkfs clean -fd --dry-run`.
    Reaching a destructive command that way needs the file to exist already —
    and if this call wrote it, route 3 catches the write.
    """
    return not any(c.isspace() or c in "'\"`=" for c in token)


def _data_spans(stage: str, variables_are_visible_later: bool = False):
    """Ranges inside a data-only `stage` that are DATA, relative to it.

    The program word stays visible (no pattern matches a bare `grep`), and so
    does every redirection operator and target: `> /etc/passwd` is an action
    whichever program performs it, so it stays on the surface where the old
    `^(echo|printf)` prefix rule removed the whole line from the scan.

    `variables_are_visible_later` is route 3 again, for the fourth channel out
    of a stage. A STANDALONE assignment sets a shell variable that every later
    stage can expand — `foo='rm -rf /srv/data'; bash -c "$foo"` — so its value
    is only data when nothing in the call can execute. A PREFIX assignment
    (`FOO=1 grep …`) is that one command's environment and does not persist,
    so it is data regardless. (Review on #91, round 8. The distinction matters:
    without it `FOO=1 git clean -fd --dry-run` would stop being exempt, `git`
    being an executor.)
    """
    stripped = stage.strip()
    if not stripped:
        return []
    if stripped.startswith("#"):
        return [(0, len(stage))]

    spans = _token_spans(stage)
    tokens = [stage[a:b] for a, b in spans]
    assignments, data, i, n = [], [], 0, len(tokens)

    while i < n and _NOT_A_COMMAND_WORD.match(tokens[i]):
        if _ASSIGNMENT.match(tokens[i]):
            assignments.append(spans[i])  # an assigned value is data…
            i += 1
            continue
        if _REDIR_OP.match(tokens[i]):
            i += 2  # bare operator: its target is the next token, kept
            continue
        i += 1  # redirection with the target attached, e.g. `2>&1`
    if i >= n:
        # …unless it is a standalone assignment and something here can run it.
        return [] if variables_are_visible_later else assignments
    data = assignments

    i += 1  # the program word itself stays on the surface
    while i < n:
        token = tokens[i]
        if token.startswith("<<"):
            i += 1  # a heredoc opener; its body is not this function's to blank
        elif _REDIR_OP.match(token):
            i += 2
        elif _has_unquoted(token, "<>"):
            i += 1  # `>/etc/passwd`, `2>&1` — action, not data
        else:
            data.append(spans[i])
            i += 1
    return data


def _stage_writes_a_file(stage: str) -> bool:
    """Whether the stage sends its output into a file (route 3 above)."""
    for a, b in _token_spans(stage):
        token = stage[a:b]
        if _FD_DUP.match(token):
            continue
        # `_has_unquoted` rather than a match at the token's start: since the
        # tokenizer splits before a glued operator the two agree, and if it
        # ever stops agreeing this one errs toward calling it a write.
        if _REDIRECTS_OUTPUT.match(token) or _has_unquoted(token, ">"):
            return True
    return False


def _stage_writes_stdin_to_a_file(stage: str) -> bool:
    """Whether the stage puts what it reads on stdin into a named file."""
    program, args = _split_command(stage)
    if program in STDIN_WRITERS:
        return True
    if program in STDIN_PATH_WRITERS:
        return any(arg.strip("'\"") in _STDIN_PATHS for arg in args)
    return False


def _stage_can_execute(command: str, stage_range, bodies: dict) -> bool:
    """Whether one pipeline stage could run a program or a file.

    TOM-379's `_segment_can_run_a_program` unchanged — no widening for text
    tools, because `rg --pre=…`, `man -P …` and `ack --pager=…` really do run
    a named file. A comment is the one thing it cannot be asked about: its `#`
    is not a program name, it is the absence of one.
    """
    if command[stage_range[0] : stage_range[1]].strip().startswith("#"):
        return False
    return _segment_can_run_a_program(command, stage_range, bodies)


def _call_can_execute(command: str, segments, bodies: dict) -> bool:
    """Whether ANY stage in the whole call could run a program or a file."""
    return any(
        _stage_can_execute(command, stage, bodies)
        for seg in segments
        for stage in _pipeline_stages(command, seg)
    )


def _blank_data_only_stages(command: str, chars: list, segments, bodies: dict) -> None:
    call_can_execute = _call_can_execute(command, segments, bodies)
    for seg in segments:
        stages = _pipeline_stages(command, seg)
        for index, (start, end) in enumerate(stages):
            stage = command[start:end]
            if not _segment_is_plain(stage):
                continue  # route 1: the shell runs part of this stage itself
            if not _stage_is_data_only(stage):
                continue
            downstream = stages[index + 1 :]
            if any(_stage_can_execute(command, s, bodies) for s in downstream):
                continue  # route 2: stdout reaches something that can run it
            # Route 3 asks where this stage's OUTPUT ends up, so it has to
            # follow the whole pipeline, not just this stage: the redirection
            # in `echo … | cat > /tmp/x` belongs to `cat`, and `cat` is inert,
            # so route 2 lets it through. (Review finding on #91, round 2.)
            onward = [stage] + [command[s[0] : s[1]] for s in downstream]
            if call_can_execute and any(
                _stage_writes_a_file(text) or _stage_writes_stdin_to_a_file(text)
                for text in onward
            ):
                continue  # route 3: written to disk, and something here runs
            for a, b in _data_spans(stage, call_can_execute):
                _blank(chars, start + a, start + b)


def is_safe_context(command: str) -> bool:
    """Whether the WHOLE command is data — nothing in it acts.

    TOM-394. This used to answer that question from a PREFIX, and so exempted
    everything chained after the prefix too; see "Data-only stages" above for
    what that cost. It is now the whole-command case of the same per-stage
    predicate: every stage plain and data-only, nothing written to a file, and
    no stage in the call able to run anything.

    It is a fast path, not a second opinion. Everything it accepts, the
    surface would have blanked to nothing but program words anyway — and that
    is the point: a prefix-shaped shortcut that can DISAGREE with the surface
    is the bug this ticket is about. `TestIsSafeContextIsAStrictSubsetOfTheSurface`
    pins the agreement. TOM-394 asked that the function not simply be deleted;
    it is kept, gated to agree, and the deletion question is left open.

    Only `_stage_is_data_only` is load-bearing today; mutation testing says so
    outright — remove the plainness check, the write check or the executor
    gate and no test moves, because `_call_can_execute` already refuses a
    stage carrying a substitution, and a data-only program cannot put text on
    disk without a redirection. They are belt-and-braces, kept for the same
    reason as the `<<<` skip in `_heredoc_openers`: widening
    `_stage_is_data_only` later must not be able to make this shortcut
    silently disagree with the surface.
    """
    try:
        heredocs, segments = _scan_layout(command)
        bodies = {(s, e): command[bs:be] for _q, s, e, bs, be in heredocs}
        stages = [
            command[start:end]
            for seg in segments
            for start, end in _pipeline_stages(command, seg)
        ]
        if _call_can_execute(command, segments, bodies):
            return False
        return all(
            _segment_is_plain(stage)
            and _stage_is_data_only(stage)
            and not _stage_writes_a_file(stage)
            for stage in stages
        )
    except Exception:
        return False  # unparseable is not safe: scan everything


# ─── Main hook ────────────────────────────────────────────────


def main():
    if not is_enabled():
        print("{}")
        return

    try:
        input_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        print("{}")
        return

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Only screen Bash commands
    if tool_name != "Bash":
        print("{}")
        return

    command = tool_input.get("command", "")
    if not command:
        print("{}")
        return

    # Skip safe contexts
    if is_safe_context(command):
        print("{}")
        return

    # Match against what the shell will RUN, not what the command string
    # merely contains — see "Why these patterns run against a *surface*".
    surface = execution_surface(command)

    # Check all patterns
    for pattern, description, severity in ALL_PATTERNS:
        if pattern.search(surface):
            reason = f"🛑 BLOCKED: {description}\nCommand: {command[:200]}"

            # Log the block
            log_dir = Path.home() / ".claude" / "permission-audit"
            log_dir.mkdir(parents=True, exist_ok=True)
            import time

            entry = {
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "type": "destructive_guard",
                "severity": severity,
                "description": description,
                "command": command[:500],
            }
            with open(log_dir / "destructive-blocks.jsonl", "a") as f:
                f.write(json.dumps(entry) + "\n")

            # Send ntfy alert for blocks
            if severity == "block":
                try:
                    from urllib.request import Request, urlopen

                    ntfy_req = Request(
                        _ntfy_url(),
                        data=f"🛑 Destructive command blocked\n{description}\n{command[:100]}".encode(),
                        headers={
                            "Title": "Destructive Command Blocked",
                            "Priority": "high",
                            "Tags": "octagonal_sign,warning",
                        },
                        method="POST",
                    )
                    urlopen(ntfy_req, timeout=3)
                except Exception:
                    pass

            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "PreToolUse",
                            "permissionDecision": "deny",
                            "permissionDecisionReason": reason,
                        }
                    }
                )
            )
            return

    # No match — allow
    print("{}")


if __name__ == "__main__":
    main()

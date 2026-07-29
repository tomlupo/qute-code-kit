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


def is_safe_context(command: str) -> bool:
    """Commands that mention destructive patterns but aren't destructive."""
    stripped = command.strip()

    # grep/rg searching for patterns
    if re.match(r"^(grep|rg|ag|ack)\s+", stripped):
        return True

    # echo/printf just printing text
    if re.match(r"^(echo|printf)\s+", stripped):
        return True

    # Comments
    if stripped.startswith("#"):
        return True

    # Variable assignment (not execution)
    if re.match(r"^[A-Z_]+=", stripped):
        return True

    # man/help pages
    if re.match(r"^(man|help|\w+\s+--help)\b", stripped):
        return True

    # Dry-run flags — LONG FORMS ONLY, and only on the FIRST command.
    #
    # This exemption skips ALL patterns below, so it has to be narrower than
    # what it protects. It used to include bare `-n`, which is a dry-run flag
    # for make/rsync/git-clean and something else entirely everywhere else:
    # line numbers (grep), numeric sort (sort), a count (head/tail), quiet
    # (sed), no-clobber (cp/mv), batch size (xargs). `\b` only needs a
    # non-word char after the n, so `head -n 20` disarmed the guard — and
    # because the search spanned the whole string, it disarmed it for every
    # command chained alongside: `rm -rf /srv/data && tail -n 50 log` was
    # exempt. So was `find . -type f | xargs -n 1 rm -rf`.
    #
    # Scoping to the first segment matters for the same reason: a dry run
    # later in a pipeline says nothing about the destructive command before it.
    first_segment = re.split(r"[;|]|&&|\|\|", stripped, maxsplit=1)[0]
    if re.search(
        r"--dry-run\b|--dryrun\b|--check\b|--whatif\b|--just-print\b", first_segment
    ):
        return True

    return False


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
        if c == "&" and (line[i - 1 : i] in ("<", ">") or line[i + 1 : i + 2] == ">"):
            # `2>&1`, `>&2`, `&>log` — fd duplication, NOT a separator. Getting
            # this wrong split the segment before a later `|`, which hid the
            # pipe from `_segment_is_plain` and exempted a payload that a shell
            # then executed: `python3 -c '…' 2>&1 | bash`.
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


def _split_command(segment: str):
    """(program, argument tokens) for a segment, or ("", []).

    Leading env assignments and redirections are skipped, and redirections are
    dropped from the argument list — `python3 > out - <<EOF` has to read as
    "python, arg `-`", not "python, arg `out`".
    """
    tokens, i = segment.split(), 0
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
        # One executor anywhere in the call voids every exemption in it: it
        # could run a file another segment just wrote.
        if any(_segment_can_run_a_program(command, seg, bodies) for seg in segments):
            return command
        chars = list(command)
        _blank_heredoc_bodies(command, chars, heredocs)
        _blank_python_c_payloads(command, chars, segments)
        return "".join(chars)
    except Exception:
        return command


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

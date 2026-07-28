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
#       `<<'EOF'`) the shell still expands `$(…)` and backticks inside the
#       body, so those spans are left in the surface.
#
#   `python -c <payload>`        …and `python3 - <<'PY' … PY`
#       Exempt only when the payload contains no way to hand text to a
#       shell (`_PY_SHELLS_OUT`). Python is the only interpreter exempted:
#       every other one (`perl -e`, `node -e`, `ruby -e`, and notably
#       `psql -c` / `mysql -e`, whose payloads the DATABASE_PATTERNS are
#       *about*) would need its own shell-out vocabulary, and an incomplete
#       vocabulary is a bypass rather than a false positive.
#
# CASES THIS DELIBERATELY STILL BLOCKS, because they cannot be told apart
# from execution by looking at the text:
#   * `python3 -c "os.system('rm -rf /x')"` — and so, unavoidably, also
#     `python3 -c "open('f','w').write('rm -rf /x')"` when the same payload
#     happens to mention subprocess/os.system/exec/eval anywhere.
#   * any interpreter other than python: `perl -e '…'`, `node -e '…'`.
#   * a heredoc into anything but `cat`/`tee`, including `sudo tee`.
#   * any of the above when the segment also pipes or substitutes.
# The route for those is the Write tool (never screened by this guard —
# it only matches Bash) or `/guard destructive off` for the one session.

# stdin consumers that cannot execute what they read.
HEREDOC_DATA_SINKS = frozenset({"cat", "tee"})

# Interpreters whose payload is exempt when it cannot shell out.
_PYTHON_CMD = re.compile(r"\Apython[0-9.]*\Z")

# Anything that lets a python payload hand a string to a shell (or build one
# dynamically). Deliberately over-broad: a match means "scan it", which is the
# safe direction.
_PY_SHELLS_OUT = re.compile(
    r"""(?:
          \bos\s*\.\s*(?:system|popen|exec\w*|spawn\w*)
        | \bsubprocess\b
        | \bcommands\s*\.
        | \bpty\s*\.\s*spawn\b
        | \bsystem\s*\(
        | \bpopen\s*\(
        | \b(?:check_output|check_call|getoutput|getstatusoutput)\b
        | \b(?:exec|eval|compile)\s*\(
    )""",
    re.VERBOSE,
)

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

# A leading token that is a redirection (`>f`, `2>&1`, `<in`) or an env
# assignment (`FOO=bar`) — skipped when looking for a segment's command word.
_NOT_A_COMMAND_WORD = re.compile(r"\A(?:\d*[<>]|[A-Za-z_][A-Za-z0-9_]*=)")

# `$(...)`/backticks inside an unquoted heredoc body still expand.
_EXPANSION = re.compile(r"\$\([^)]*\)|`[^`]*`")


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


def _command_word(segment: str) -> str:
    """The program a segment runs, basename-only, or "" if undeterminable."""
    for token in segment.split():
        if _NOT_A_COMMAND_WORD.match(token):
            continue
        return token.strip("'\"").rsplit("/", 1)[-1]
    return ""


def _segment_is_plain(segment: str) -> bool:
    """No pipe / substitution — i.e. nothing that re-executes a data region."""
    return not any(token in segment for token in _SEGMENT_DISQUALIFIERS)


def _heredoc_body_is_data(command_word: str, body: str) -> bool:
    if command_word in HEREDOC_DATA_SINKS:
        return True
    if _PYTHON_CMD.match(command_word):
        return not _PY_SHELLS_OUT.search(body)
    return False


def _blank(chars: list, start: int, end: int) -> None:
    """Overwrite [start, end) with spaces, keeping newlines so `$`/`^` hold."""
    for i in range(start, end):
        if chars[i] != "\n":
            chars[i] = " "


def _blank_heredoc_bodies(command: str, chars: list) -> None:
    lines, offset = [], 0
    for line in command.split("\n"):
        lines.append((offset, line))
        offset += len(line) + 1

    idx = 0
    while idx < len(lines):
        line_start, line = lines[idx]
        pending = []
        for seg_start, seg_end in _split_segments(line, line_start):
            segment = command[seg_start:seg_end]
            for word, quoted in _heredoc_openers(segment):
                pending.append((word, quoted, segment))
        idx += 1
        for word, quoted, segment in pending:
            body_start = lines[idx][0] if idx < len(lines) else len(command)
            body_end = body_start
            while idx < len(lines):
                l_start, l_text = lines[idx]
                if l_text.strip() == word:
                    idx += 1  # consume the terminator line
                    break
                body_end = l_start + len(l_text)
                idx += 1
            body = command[body_start:body_end]
            if not _segment_is_plain(segment):
                continue
            if not _heredoc_body_is_data(_command_word(segment), body):
                continue
            _blank(chars, body_start, body_end)
            if not quoted:
                # The shell still expands these inside an unquoted heredoc.
                for m in _EXPANSION.finditer(body):
                    chars[body_start + m.start() : body_start + m.end()] = list(
                        m.group(0)
                    )


def _blank_python_c_payloads(command: str, chars: list) -> None:
    offset = 0
    for line in command.split("\n"):
        for seg_start, seg_end in _split_segments(line, offset):
            segment = command[seg_start:seg_end]
            if not _segment_is_plain(segment):
                continue
            if not _PYTHON_CMD.match(_command_word(segment)):
                continue
            for m in re.finditer(r"(?:\A|\s)-c[ \t]*(['\"])", segment):
                quote = m.group(1)
                body_start = m.end()
                body_end = segment.find(quote, body_start)
                if body_end == -1:
                    continue
                payload = segment[body_start:body_end]
                if _PY_SHELLS_OUT.search(payload):
                    continue
                _blank(chars, seg_start + body_start, seg_start + body_end)
        offset += len(line) + 1


def execution_surface(command: str) -> str:
    """The part of `command` the shell will run, with data regions blanked.

    Same length as the input, so every existing pattern (including the
    `$`-anchored ones) keeps its exact meaning. Any failure returns the
    command untouched: falling back to scanning everything reproduces the
    old behaviour, which errs toward blocking.
    """
    try:
        chars = list(command)
        _blank_heredoc_bodies(command, chars)
        _blank_python_c_payloads(command, chars)
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

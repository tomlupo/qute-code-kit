"""Tests for the destructive-command guard: TOM-379 and TOM-394.

Two layers:

  * **Integration** — the real hook, driven as a subprocess with real
    `PreToolUse` payloads. This is the layer that matters: the bug being
    fixed was about what the deployed hook decides, so a test that only
    poked at helper functions would be testing the wrong half.
  * **Unit** — `execution_surface()` directly, where the blanked region can
    be asserted character-for-character rather than inferred from a verdict.

Every allow-assertion checks that stdout is *exactly* `{}` — no
`hookSpecificOutput` at all — and every deny-assertion checks the specific
pattern description that fired, not merely that the word "BLOCKED" appears
somewhere. A substring assertion against the reason text would pass for the
wrong pattern, which is precisely the class of test that measures nothing.

DO NOT remove the sandboxing in `_HOOK_ENV`. Every "block" the hook decides
has two live side effects: it appends to `~/.claude/permission-audit/` and it
POSTs a high-priority ntfy alert. This file provokes ~90 blocks per run, so an
unsandboxed run pages a real phone ninety times. `HOME` is redirected to a temp
dir and the proxy vars point at a closed port so `urlopen` is refused locally
and instantly.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / "hooks" / "destructive-guard.py"

_SANDBOX_HOME = tempfile.mkdtemp(prefix="qute-destructive-guard-")
_DEAD_PROXY = "http://127.0.0.1:9"  # discard port: refused, never routed

_HOOK_ENV = {
    "PATH": "/usr/bin:/bin",
    "HOME": _SANDBOX_HOME,
    "USERPROFILE": _SANDBOX_HOME,
    # Pin the toggle so the suite does not depend on the developer's
    # ~/.claude/qute-guards.json state.
    "CLAUDE_GUARD_DESTRUCTIVE": "1",
    "http_proxy": _DEAD_PROXY,
    "https_proxy": _DEAD_PROXY,
    "HTTP_PROXY": _DEAD_PROXY,
    "HTTPS_PROXY": _DEAD_PROXY,
}

_spec = importlib.util.spec_from_file_location("qute_destructive_guard", str(HOOK))
guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guard)


def decide(command: str, tool_name: str = "Bash"):
    """Run the real hook and return (decision, reason).

    decision is "allow" when the hook emits a bare `{}`.
    """
    payload = json.dumps(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": tool_name,
            "tool_input": {"command": command},
        }
    )
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=30,
        env=_HOOK_ENV,
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    hso = out.get("hookSpecificOutput")
    if hso is None:
        assert out == {}, f"expected a bare allow, got {out!r}"
        return "allow", ""
    return hso["permissionDecision"], hso["permissionDecisionReason"]


def assert_allowed(command: str) -> None:
    decision, reason = decide(command)
    assert decision == "allow", f"unexpectedly denied: {reason}"


def assert_denied(command: str, description: str) -> None:
    """Deny, *and* for the stated reason — the description identifies which
    pattern fired, so a different pattern matching by accident still fails."""
    decision, reason = decide(command)
    assert decision == "deny", f"expected a deny for: {command!r}"
    assert reason.startswith(f"🛑 BLOCKED: {description}\n"), reason


# Descriptions, copied from the pattern table. Kept as constants so a typo
# fails loudly instead of silently weakening an assertion.
RESET_HARD = "git reset --hard destroys uncommitted changes"
PUSH_FORCE = "git push --force overwrites remote history"
RM_ROOT = "rm -rf on non-tmp root path"
DROP = "DROP destroys database objects"
VAULT = "removing Obsidian vault data"
CLEAN = "git clean -f permanently deletes untracked files"
PRUNE = "docker system prune -a removes all unused data"
KILLALL = "killall terminates all matching processes"
MKFS = "mkfs formats a filesystem"
DROPDB = "dropdb removes entire database"


# ------------------------------------------------------- TOM-379: literals


class TestWritingAFileIsNotExecutingIt:
    """The incident: fixture strings inside a heredoc were denied, and the
    agent got its write through by concatenating the literal from fragments."""

    def test_heredoc_into_cat_redirect(self):
        assert_allowed(
            "cat > /tmp/patch.sh <<'EOF'\n"
            "#!/bin/bash\n"
            "git push --force-with-lease origin feat/x\n"
            "EOF"
        )

    def test_heredoc_into_tee(self):
        assert_allowed("tee /tmp/fixture.txt <<'EOF'\ngit reset --hard HEAD~1\nEOF")

    def test_heredoc_with_unquoted_delimiter(self):
        assert_allowed("cat > /tmp/f <<EOF\nrm -rf /srv/data\nEOF")

    def test_heredoc_with_tab_stripping_operator(self):
        assert_allowed("cat > /tmp/f <<-EOF\n\tgit reset --hard HEAD~1\n\tEOF")

    def test_python_dash_c_writing_a_file(self):
        assert_allowed(
            "python3 -c \"open('/tmp/f','w').write('git push --force-with-lease')\""
        )

    def test_python_stdin_heredoc_writing_a_file(self):
        assert_allowed(
            "python3 - <<'PY'\n"
            "open('/tmp/f','w').write('git push --force-with-lease')\n"
            "PY"
        )

    def test_the_fragment_trick_is_now_pointless(self):
        """Both the honest literal and the obfuscated one are allowed, so
        there is nothing left to obfuscate around."""
        honest = "cat > /tmp/f <<'EOF'\ngit push --force-with-lease\nEOF"
        obfuscated = (
            "python3 -c \"open('/tmp/f','w').write('git push ' + '--f' + "
            "'orce-with-lease')\""
        )
        assert_allowed(honest)
        assert_allowed(obfuscated)


class TestExecutionIsStillBlocked:
    def test_real_force_with_lease_push(self):
        assert_denied("git push --force-with-lease origin main", PUSH_FORCE)

    def test_real_force_push(self):
        assert_denied("git push --force origin main", PUSH_FORCE)

    def test_real_reset_hard(self):
        assert_denied("git reset --hard HEAD~3", RESET_HARD)

    def test_real_rm_rf_root_path(self):
        assert_denied("rm -rf /srv/data", RM_ROOT)

    def test_real_vault_removal(self):
        # `-r` without `-f`: only the vault-specific pattern can catch this,
        # so the assertion pins that pattern rather than the generic rm rule.
        assert_denied("rm -r /srv/obsidian", VAULT)


class TestHeredocConsumersThatActuallyExecute:
    """The data-sink list is an allowlist; everything else keeps its body
    scanned, because an unlisted consumer is assumed to execute stdin."""

    @pytest.mark.parametrize(
        "consumer", ["bash", "sh", "zsh", "ssh host", "sudo tee /tmp/f", "xargs -0"]
    )
    def test_unlisted_consumer_keeps_its_body_scanned(self, consumer):
        assert_denied(f"{consumer} <<'EOF'\nrm -rf /srv/data\nEOF", RM_ROOT)

    def test_psql_heredoc_really_runs_the_sql(self):
        assert_denied("psql mydb <<'EOF'\nDROP TABLE users;\nEOF", DROP)

    def test_python_heredoc_that_shells_out(self):
        assert_denied(
            "python3 - <<'PY'\nimport os\nos.system('rm -rf /srv/data')\nPY", RM_ROOT
        )

    def test_python_dash_c_that_shells_out(self):
        assert_denied(
            "python3 -c \"import os; os.system('rm -rf /srv/data')\"", RM_ROOT
        )

    def test_python_dash_c_shelling_out_via_dunder_import(self):
        assert_denied(
            "python3 -c \"__import__('os').system('rm -rf /srv/data')\"", RM_ROOT
        )

    # The payloads below are deliberately VALID, inert python. A body like a
    # bare `rm -rf …` fails `ast.parse` and would be denied for that reason
    # alone, so it would prove nothing about how the invocation was read.

    def test_python_running_a_script_does_not_own_its_stdin(self):
        """Review finding on #90: the exemption is for python reading its own
        SOURCE from stdin. `python3 runner.py <<EOF` feeds the body to an
        arbitrary script, which may interpret or execute it."""
        assert_denied(
            "python3 runner.py <<'EOF'\ndata = 'rm -rf /srv/data'\nEOF", RM_ROOT
        )

    def test_python_module_invocation_does_not_own_its_stdin(self):
        assert_denied(
            "python3 -m runner <<'EOF'\ndata = 'rm -rf /srv/data'\nEOF", RM_ROOT
        )

    def test_dash_c_after_a_script_name_is_not_the_interpreters(self):
        assert_denied("python3 runner.py -c \"data = 'rm -rf /srv/data'\"", RM_ROOT)

    def test_a_heredoc_feeding_a_dash_c_one_liner_is_data_for_it_not_source(self):
        # `python3 -c '<code>' <<EOF` — the -c payload is the program, so the
        # heredoc is that program's INPUT. Only `python3 -`/bare `python3`
        # make a heredoc body python source.
        assert_denied(
            "python3 -c \"data = 'x'\" <<'EOF'\ndata = 'rm -rf /srv/data'\nEOF",
            RM_ROOT,
        )

    def test_a_dash_c_that_is_an_argument_to_the_stdin_program_is_not_pythons(self):
        # `python3 - -c "…"`: python's program comes from stdin, so this `-c`
        # is argv for that program, not an interpreter flag.
        assert_denied(
            "python3 - -c \"data = 'rm -rf /srv/data'\" <<'PY'\nx = 1\nPY",
            RM_ROOT,
        )

    def test_the_option_terminator_makes_dash_c_a_filename(self):
        """Review finding on #90 round 5: after `--`, CPython reads `-c` as a
        SCRIPT NAME. Treating it as the flag exempted the payload and marked
        the segment inert, while python ran a file the same call had written."""
        assert_denied("python3 -- -c \"data = 'rm -rf /srv/data'\"", RM_ROOT)

    def test_the_option_terminator_also_voids_a_neighbours_exemption(self):
        assert_denied(
            "cat > /tmp/x <<'EOF'\nrm -rf /srv/data\nEOF\npython3 -- -c \"data = 'x'\"",
            RM_ROOT,
        )

    def test_option_bundles_are_not_taken_apart(self):
        # A bundle containing `c` or `m` means the invocation is doing
        # something this code refuses to guess at, so the body stays scanned.
        assert_denied("python3 -uc <<'PY'\ndata = 'rm -rf /srv/data'\nPY", RM_ROOT)

    def test_bare_python_reading_stdin_as_source_is_still_exempt(self):
        assert_allowed(
            "python3 <<'PY'\nopen('/tmp/f','w').write('rm -rf /srv/data')\nPY"
        )

    def test_benign_flags_before_the_stdin_dash_are_tolerated(self):
        assert_allowed(
            "python3 -u - <<'PY'\nopen('/tmp/f','w').write('rm -rf /srv/data')\nPY"
        )

    def test_a_redirection_target_is_not_mistaken_for_a_script_name(self):
        # `> /tmp/out` is two tokens; counting `/tmp/out` as an argument would
        # read this as "python running a script" and stop exempting it.
        assert_allowed(
            "python3 > /tmp/out - <<'PY'\n"
            "open('/tmp/f','w').write('rm -rf /srv/data')\n"
            "PY"
        )

    def test_other_interpreters_are_not_exempt(self):
        """Documented limitation: only python is exempted, because every
        other interpreter needs its own shell-out vocabulary."""
        assert_denied("perl -e 'print \"rm -rf /srv/data\"'", RM_ROOT)
        assert_denied("node -e 'console.log(\"rm -rf /srv/data\")'", RM_ROOT)


class TestWriteThenExecuteInOneCall:
    """Review finding on #90: writing a file and running it are two steps and
    they fit in one Bash call. One non-inert segment anywhere in the call
    voids every exemption in it."""

    @pytest.mark.parametrize(
        "runner", ["bash /tmp/x", ". /tmp/x", "source /tmp/x", "./x", "make -f /tmp/x"]
    )
    def test_an_executor_later_in_the_call_voids_the_exemption(self, runner):
        assert_denied(f"cat > /tmp/x <<'EOF'\nrm -rf /srv/data\nEOF\n{runner}", RM_ROOT)

    def test_an_executor_before_the_heredoc_voids_it_too(self):
        assert_denied(
            "bash /tmp/x\ncat > /tmp/y <<'EOF'\nrm -rf /srv/data\nEOF", RM_ROOT
        )

    def test_a_program_nobody_listed_counts_as_an_executor(self):
        # INERT_PROGRAMS is an allowlist: unrecognised means "might run it".
        assert_denied(
            "cat > /tmp/x <<'EOF'\nrm -rf /srv/data\nEOF\nsome-runner /tmp/x", RM_ROOT
        )

    def test_python_shelling_out_later_in_the_call_voids_the_exemption(self):
        assert_denied(
            "cat > /tmp/x <<'EOF'\nrm -rf /srv/data\nEOF\n"
            "python3 -c \"import os; os.system('bash /tmp/x')\"",
            RM_ROOT,
        )

    def test_python_heredoc_shelling_out_later_voids_the_exemption(self):
        assert_denied(
            "cat > /tmp/x <<'A'\nrm -rf /srv/data\nA\n"
            "python3 - <<'B'\nimport os\nos.system('bash /tmp/x')\nB",
            RM_ROOT,
        )

    @pytest.mark.parametrize(
        "runner",
        [
            "cat /tmp/x | bash",
            "echo `bash /tmp/x`",
            "FOO=$(bash /tmp/x)",
            "diff <(bash /tmp/x) /dev/null",
            "tee >(bash) < /tmp/x",
            "cat /tmp/x | xargs -0 sh -c",
        ],
    )
    def test_metacharacters_reach_a_program_the_command_word_never_names(self, runner):
        """Review finding on #90 round 4: `cat /tmp/x | bash` resolves to
        `cat`, which is inert — and runs `bash`. So a pipe or a substitution
        anywhere gates the WHOLE call, not just the segment owning the data."""
        assert_denied(f"cat > /tmp/x <<'EOF'\nrm -rf /srv/data\nEOF\n{runner}", RM_ROOT)

    def test_a_line_continuation_hiding_a_pipe_voids_the_call(self):
        """Review finding on #90 round 7: bash joins a line ending in `\\`
        with the next, so this is the single pipeline `cat <<'EOF' | bash`.
        Read as two physical lines, the pipe was invisible and the body — the
        thing bash pipes into a shell — got blanked."""
        assert_denied("cat <<'EOF' \\\n| bash\nrm -rf /srv/data\nEOF", RM_ROOT)

    def test_a_continuation_inside_a_body_is_the_documented_cost(self):
        # Nothing here is executed; the exemption is forfeited anyway, because
        # rebuilding logical lines would move every offset the surface relies
        # on. Pinned so the trade-off is visible rather than surprising.
        assert_denied(
            "cat > /tmp/f <<'EOF'\nfirst \\\nsecond git reset --hard\nEOF", RESET_HARD
        )

    def test_inert_neighbours_do_not_void_it(self):
        # chmod cannot run anything, so the common write-then-mark-executable
        # shape stays exempt.
        assert_allowed(
            "cat > /tmp/x <<'EOF'\ngit push --force-with-lease\nEOF\nchmod +x /tmp/x"
        )

    def test_several_writes_in_one_call_stay_exempt(self):
        assert_allowed(
            "cat > /tmp/a <<'A'\ngit push --force\nA\n"
            "cat > /tmp/b <<'B'\ngit reset --hard\nB\n"
            "chmod 600 /tmp/a /tmp/b"
        )

    @pytest.mark.parametrize(
        "runner",
        [
            "git -c alias.x='!bash /tmp/x' x",  # alias with a shell escape
            "git add /tmp/x",  # the cost: even benign git voids it
            "sort --compress-program=/tmp/x /tmp/x",
            "rg --pre=/tmp/x pattern /tmp/x",
        ],
    )
    def test_tools_with_an_exec_escape_are_not_inert(self, runner):
        """Review finding on #90 round 3: `git` was on the inert allowlist,
        but `git -c alias.x='!…'` runs anything. `sort --compress-program` and
        `rg --pre` are the same class, so all three are off the list — the bar
        is "no option to this program spawns another one"."""
        assert_denied(f"cat > /tmp/x <<'EOF'\nrm -rf /srv/data\nEOF\n{runner}", RM_ROOT)


class TestPythonPayloadAllowlist:
    """Review finding on #90: the exemption used to key on a deny-list of
    shell-out spellings, which `getattr(os, 'sys' + 'tem')` walks past — the
    same fragment trick this ticket exists to stop rewarding. It is now an
    allowlist over the parsed AST."""

    @pytest.mark.parametrize(
        "payload",
        [
            "import os; getattr(os, 'system')('rm -rf /srv/data')",
            "getattr(__builtins__, 'x')('rm -rf /srv/data')",
            "f = lambda: __import__('os').system('rm -rf /srv/data'); f()",
            "exec('rm -rf /srv/data')",
            "eval(compile('x', 'rm -rf /srv/data', 'exec'))",
        ],
    )
    def test_indirect_shell_out_is_not_exempt(self, payload):
        assert_denied(f'python3 -c "{payload}"', RM_ROOT)

    @pytest.mark.parametrize(
        "command",
        [
            # `_dash_c_payload` stops at the first raw quote.
            "python3 -c \"open('/tmp/f','w').write(\\\"rm -rf /srv/data\\\")\"",
            # `_python_source_mode` reads `ignore` as a script name.
            "python3 -W ignore -c \"data = 'rm -rf /srv/data'\"",
        ],
    )
    def test_shapes_this_code_declines_to_parse_stay_blocked(self, command):
        """Raised as nits in review and kept: both are FALSE POSITIVES, i.e.
        they fail toward blocking, and the fix for each is more shell parsing —
        which is what produced four separate bypasses in earlier rounds. Pinned
        here so a future widening has to change a test on purpose."""
        assert_denied(command, RM_ROOT)

    def test_an_attribute_call_off_the_allowlist_is_not_exempt(self):
        # No import statement here, so the method allowlist is the only thing
        # standing between this payload and a shell.
        assert_denied("python3 -c \"os.system('rm -rf /srv/data')\"", RM_ROOT)

    def test_a_payload_that_will_not_parse_is_not_exempt(self):
        assert_denied("python3 -c \"def (: 'rm -rf /srv/data'\"", RM_ROOT)

    def test_any_import_at_all_forfeits_the_exemption(self):
        # Strict by design: json is harmless, but drawing that line needs a
        # module allowlist, and an incomplete one is a bypass.
        assert_denied(
            "python3 -c \"import json; open('/tmp/f','w').write('rm -rf /srv/data')\"",
            RM_ROOT,
        )

    # Both payloads below carry text that WOULD match a pattern if it were
    # scanned, so the allow verdict can only come from the exemption.

    def test_string_building_and_file_writing_stay_exempt(self):
        assert_allowed(
            "python3 -c \"open('/tmp/f','w').write('rm -rf /srv/data'.upper())\""
        )

    def test_the_allowlist_is_checked_on_the_ast_not_the_text(self):
        # `os.system` appears as data. Nothing calls it, so the AST is inert.
        assert_allowed(
            "python3 -c \"open('/tmp/f','w').write('os.system: rm -rf /srv/data')\""
        )


class TestSegmentsThatReExecuteData:
    """A pipe or a substitution turns a data region back into commands, so it
    disqualifies the segment from every exemption."""

    def test_cat_heredoc_piped_into_a_shell(self):
        assert_denied("cat <<'EOF' | bash\nrm -rf /srv/data\nEOF", RM_ROOT)

    def test_python_dash_c_piped_into_a_shell(self):
        assert_denied("python3 -c \"print('rm -rf /srv/data')\" | bash", RM_ROOT)

    def test_command_substitution_in_an_unquoted_heredoc_still_runs(self):
        assert_denied(
            "cat > /tmp/f <<EOF\nprefix $(rm -rf /srv/data) suffix\nEOF", RM_ROOT
        )

    def test_a_closing_paren_inside_quotes_does_not_end_the_substitution(self):
        """Review finding on #90 round 6: the old span regex stopped at the
        first `)`, which here sits inside quotes — so the tail of a
        substitution bash really runs was blanked away."""
        assert_denied(
            "cat > /tmp/f <<EOF\n$(printf ')' ; rm -rf /srv/data)\nEOF", RM_ROOT
        )

    def test_a_nested_substitution_does_not_end_the_outer_one(self):
        assert_denied(
            "cat > /tmp/f <<EOF\n$(echo $(date) ; rm -rf /srv/data)\nEOF", RM_ROOT
        )

    def test_fd_duplication_does_not_hide_a_later_pipe(self):
        """Review finding on #90: `&` was treated as a command separator, so
        `2>&1` split the segment before the `|` and the pipe went unseen."""
        assert_denied(
            "python3 -c \"print('rm -rf /srv/data')\" 2>&1 | bash",
            RM_ROOT,
        )
        assert_denied("cat <<'EOF' 2>&1 | bash\nrm -rf /srv/data\nEOF", RM_ROOT)

    def test_fd_duplication_without_a_pipe_is_not_a_segment_break(self):
        # `2>&1` sitting between the target and the heredoc operator: splitting
        # on that `&` would strand the opener in a segment whose "program" is
        # the stray `1`, which is not on the inert allowlist, and the whole
        # call would lose its exemption.
        assert_allowed("cat > /tmp/f 2>&1 <<'EOF'\ngit push --force-with-lease\nEOF")

    def test_ampersand_redirect_form_does_not_hide_a_later_pipe(self):
        assert_denied("cat <<'EOF' &>/tmp/log | bash\nrm -rf /srv/data\nEOF", RM_ROOT)

    def test_a_pipe_in_an_unrelated_segment_still_voids_the_call(self):
        # Deliberate false positive. This pipe belongs to `ls | wc -l` and can
        # reach nothing the heredoc wrote — but after the round-4 finding the
        # metachar check gates the whole call, and drawing the line finer would
        # mean deciding which pipes can reach which files. Blocking is cheaper.
        assert_denied(
            "cat > /tmp/f <<'EOF' & ls | wc -l\ngit reset --hard\nEOF", RESET_HARD
        )

    def test_command_substitution_is_inert_under_a_quoted_delimiter(self):
        assert_allowed("cat > /tmp/f <<'EOF'\nprefix $(rm -rf /srv/data) suffix\nEOF")

    def test_backticks_in_an_unquoted_heredoc_still_run(self):
        assert_denied(
            "cat > /tmp/f <<EOF\nprefix `rm -rf /srv/data` suffix\nEOF", RM_ROOT
        )


class TestNeighbouringCommandsAreUnaffected:
    def test_destructive_command_before_a_benign_heredoc(self):
        assert_denied(
            "git reset --hard HEAD~1\ncat > /tmp/f <<'EOF'\nhello\nEOF", RESET_HARD
        )

    def test_destructive_command_after_a_benign_heredoc(self):
        assert_denied(
            "cat > /tmp/f <<'EOF'\nhello\nEOF\ngit reset --hard HEAD~1", RESET_HARD
        )

    def test_two_heredocs_one_line_only_the_sink_is_exempt(self):
        # Bodies arrive in OPENER order: `A` belongs to cat (a sink, blanked),
        # `B` to wc (inert, so it does not void the call, but it is not a sink
        # either, so its body stays scanned). Misattributing them swaps which
        # pattern fires, which is why this asserts RM_ROOT and not merely
        # "denied" — `git reset --hard` would deny too, for the wrong reason.
        assert_denied(
            "cat > /tmp/a <<'A' ; wc -l <<'B'\ngit reset --hard\nA\nrm -rf /srv/data\nB",
            RM_ROOT,
        )

    def test_a_shell_heredoc_voids_the_whole_call(self):
        assert_denied(
            "cat > /tmp/a <<'A' ; bash <<'B'\ngit reset --hard\nA\nrm -rf /srv/data\nB",
            RESET_HARD,
        )

    def test_here_string_is_not_a_heredoc(self):
        assert_denied("cat > /tmp/f <<<'rm -rf /srv/data'", RM_ROOT)


class TestCommandWordResolution:
    """Which program a segment runs decides whether its heredoc is data, so
    the leading-token walk has to survive the usual decorations."""

    def test_absolute_path_to_a_data_sink(self):
        assert_allowed("/bin/cat > /tmp/f <<'EOF'\ngit reset --hard HEAD~1\nEOF")

    def test_env_assignment_prefix_before_a_data_sink(self):
        # Until TOM-394 the first spelling could not be tested here at all: a
        # command *starting* with an uppercase assignment was exempted
        # wholesale by `is_safe_context`, so it never reached the surface —
        # a test measuring nothing. Both spellings now go through the surface.
        assert_allowed("LC_ALL=C cat > /tmp/f <<'EOF'\ngit reset --hard\nEOF")
        assert_allowed("true && FOO=1 cat > /tmp/f <<'EOF'\ngit reset --hard\nEOF")

    def test_leading_redirection_before_a_data_sink(self):
        assert_allowed("2>/dev/null cat > /tmp/f <<'EOF'\ngit reset --hard HEAD~1\nEOF")

    def test_an_absolute_path_to_a_shell_is_still_a_shell(self):
        assert_denied("/bin/bash <<'EOF'\nrm -rf /srv/data\nEOF", RM_ROOT)


# -------------------------------------------------------- TOM-394: prefixes


class TestAnEnvAssignmentPrefixNoLongerDisarmsTheGuard:
    """The hole: `is_safe_context` returned True for the ENTIRE command when
    it started with `^[A-Z_]+=`, so every pattern was skipped. A throwaway
    assignment — no knowledge of this file required — turned the guard off,
    silently."""

    def test_one_assignment(self):
        assert_denied("FOO=1 rm -rf /srv/data", RM_ROOT)

    def test_several_assignments(self):
        assert_denied("FOO=1 BAR=2 BAZ=3 git reset --hard HEAD~1", RESET_HARD)

    def test_a_lowercase_assignment_too(self):
        # The old rule was `^[A-Z_]+=`, so `foo=1` was never exempt. The new
        # parse accepts any valid name, which can only widen what is scanned.
        assert_denied("foo=1 rm -rf /srv/data", RM_ROOT)

    def test_a_quoted_value(self):
        assert_denied("FOO='a b' git push --force origin main", PUSH_FORCE)

    @pytest.mark.parametrize(
        "assignment",
        [
            "FOO='; echo x'",  # a separator inside the value
            'FOO="a|b&&c;d"',  # every separator at once
            "FOO='#'",  # a comment character
            "FOO='<<EOF'",  # a heredoc operator
        ],
    )
    def test_a_value_that_looks_like_shell_syntax(self, assignment):
        assert_denied(f"{assignment} rm -rf /srv/data", RM_ROOT)

    def test_a_value_that_donates_the_name_of_a_data_sink(self):
        """Also a pre-existing TOM-379 bug, reachable without any prefix as
        the `true && …` spelling below: `_split_command` used `str.split()`,
        which reads `FOO='x cat' bash` as the words `FOO='x`, `cat'`, `bash`.
        Stripping the quote made the program `cat` — a heredoc DATA SINK — so
        the body was blanked while `bash` executed it."""
        assert_denied(
            "true && FOO='x cat' bash <<'EOF'\nrm -rf /srv/data\nEOF", RM_ROOT
        )
        assert_denied("FOO='x cat' bash <<'EOF'\nrm -rf /srv/data\nEOF", RM_ROOT)

    def test_a_command_substitution_in_the_value(self):
        assert_denied("FOO=$(echo x) rm -rf /srv/data", RM_ROOT)

    def test_an_assignment_before_a_separator(self):
        assert_denied("FOO=1; rm -rf /srv/data", RM_ROOT)

    def test_a_line_continuation_after_the_assignment(self):
        assert_denied("FOO=1 \\\nrm -rf /srv/data", RM_ROOT)

    def test_an_assignment_on_its_own_is_still_not_a_command(self):
        # Nothing runs, so nothing is blocked.
        assert_allowed("MSG='rm -rf /srv/data is dangerous'")
        assert_allowed("MSG='rm -rf /srv/data' ; echo done")

    @pytest.mark.parametrize(
        "command",
        [
            "foo='rm -rf /srv/data'; bash -c \"$foo\"",
            "FOO='rm -rf /srv/data'; bash -c \"$FOO\"",
            "foo='rm -rf /srv/data'; eval $foo",
            "foo='rm -rf /srv/data'\nsome-runner",
        ],
    )
    def test_a_standalone_assignment_is_data_only_if_nothing_can_run_it(self, command):
        """Review finding on #91 round 8: a shell variable is a channel to a
        later stage exactly as a file is, so the value takes route 3's gate.
        Both cases are listed because widening the assignment parse to any
        case is what put the lowercase one in reach — under `^[A-Z_]+=` it
        was blocked, by accident rather than by design."""
        assert_denied(command, RM_ROOT)

    def test_a_prefix_assignment_does_not_persist_so_it_is_always_data(self):
        # `FOO=1 grep …` is that one command's environment, not a shell
        # variable. Gating it on the call would cost the dry-run exemption
        # every time, `git` being an executor.
        assert_allowed("FOO='rm -rf /srv/data' git clean -fd --dry-run")
        assert_allowed("FOO='rm -rf /srv/data' grep x .")

    def test_the_value_assembled_across_the_expansion_is_still_the_limitation(
        self,
    ):
        # `X="rm -rf"; $X /` — the documented, unfixable case at the top of the
        # hook. No pattern matches the text, with or without any exemption.
        assert_allowed("X='rm -rf'; $X /srv/data")

    def test_an_assignment_before_a_text_search_is_still_fine(self):
        assert_allowed("FOO=1 BAR=2 grep 'rm -rf /srv/data' .")


class TestEveryOtherPrefixThatUsedToExemptTheWholeCommand:
    """`is_safe_context` had six of these and they were all one bug: a prefix
    deciding that everything chained after it was safe too."""

    @pytest.mark.parametrize(
        "command",
        [
            "grep -r pattern . && rm -rf /srv/data",  # grep prefix
            "rg pattern . ; rm -rf /srv/data",  # rg prefix
            "echo starting && rm -rf /srv/data",  # echo prefix
            "printf '%s\\n' starting ; rm -rf /srv/data",  # printf prefix
            "# cleanup step\nrm -rf /srv/data",  # comment prefix
            "man rm ; rm -rf /srv/data",  # man prefix
            "rm --help ; rm -rf /srv/data",  # `<prog> --help` prefix
            "rsync --dry-run -a /srv/data /backup && rm -rf /srv/data",  # dry-run
            "make --just-print all && rm -rf /srv/data",  # dry-run, long form
        ],
    )
    def test_the_prefix_no_longer_covers_what_follows_it(self, command):
        assert_denied(command, RM_ROOT)

    def test_a_comment_covers_only_its_own_line(self):
        assert_denied("# a\n# b\ngit reset --hard HEAD~1", RESET_HARD)

    def test_a_dry_run_flag_on_a_program_that_has_no_such_flag(self):
        """`rm --dry-run` does not exist, so the flag is not a promise — it is
        an unknown argument next to a real recursive delete. The old rule
        searched for the flag anywhere in the first segment, for any program."""
        assert_denied("rm -rf /srv/data --dry-run", RM_ROOT)
        assert_denied("rm -rf /srv/data --check", RM_ROOT)

    def test_a_help_flag_that_is_not_the_first_argument(self):
        # The old rule was `^\w+\s+--help` — `--help` as the FIRST argument.
        # Not widened: widening it is how `--dry-run` went wrong.
        assert_denied("rm -rf /srv/data --help", RM_ROOT)

    def test_help_must_be_the_only_argument(self):
        # NARROWER than the old rule, which asked only that `--help` came
        # first. Nothing may ride along behind it, because what rides along
        # can be a command: git prints help either way, but the exemption
        # would have blanked the alias out of the scan.
        assert_denied("git --help -c alias.x='!rm -rf /srv/data' x", RM_ROOT)
        assert_allowed("git --help")

    def test_a_dry_run_later_in_the_pipeline_says_nothing_about_what_precedes(
        self,
    ):
        assert_denied("rm -rf /srv/data && rsync --dry-run -a x y", RM_ROOT)


class TestTheFalsePositivesThosePrefixesExistedFor:
    """`is_safe_context` was not gratuitous — it suppressed real false
    positives, and every one of them still has to pass. Each command below
    carries text that WOULD match a pattern if it were scanned, so an allow
    verdict can only come from the exemption."""

    @pytest.mark.parametrize(
        "command",
        [
            "grep -r 'rm -rf /srv/data' .",
            "grep -rn 'git reset --hard' . | wc -l",
            "grep 'rm -rf /srv/data' notes.txt > /tmp/out",
            "rg 'rm -rf /srv/data' .",
            "ag 'rm -rf /srv/data' src",
            "ack 'git push --force origin main' src",
            "echo 'rm -rf /srv/data'",
            "printf '%s\\n' 'git push --force origin main'",
            "# rm -rf /srv/data",
            "MSG='rm -rf /srv/data'",
            "man rm",
            "git push --help",
            "git clean -fd --dry-run",
            "git push --dry-run --force origin main",
            "rsync --dry-run -a /srv/data /backup/",
            "make --just-print clean",
            "cat /tmp/notes | grep 'rm -rf /srv/data'",
            "echo hi | grep 'rm -rf /srv/data'",
            "grep -rn 'rm -rf /srv/data' . | head -20",
        ],
    )
    def test_still_not_blocked(self, command):
        assert_allowed(command)


class TestADataOnlyStageMayNotFeedAnExecutor:
    """Blanking a stage hides its text from every pattern, so it is allowed
    only when nothing in the same Bash call could run that text — the same
    write-then-execute rule the heredoc exemptions already follow."""

    def test_piped_straight_into_a_shell(self):
        assert_denied("echo 'rm -rf /srv/data' | bash", RM_ROOT)

    def test_piped_through_a_filter_into_a_shell(self):
        assert_denied("echo 'rm -rf /srv/data' | tee /tmp/x | bash", RM_ROOT)

    def test_written_to_a_file_that_the_same_call_runs(self):
        assert_denied("echo 'rm -rf /srv/data' > /tmp/x ; bash /tmp/x", RM_ROOT)

    def test_a_program_nobody_listed_counts_as_an_executor(self):
        assert_denied("echo 'rm -rf /srv/data' > /tmp/x ; some-runner /tmp/x", RM_ROOT)

    @pytest.mark.parametrize(
        "reader",
        [
            "rg --pre=/tmp/x needle .",
            "rg --pre /tmp/x needle .",
            "man -P /tmp/x rm",
            "ack --pager=/tmp/x needle",
            "ag --pager=/tmp/x needle",
        ],
    )
    def test_a_text_tool_that_can_run_a_file_is_an_executor(self, reader):
        """Review finding on #91: these tools read text, but `--pre`, `-P` and
        `--pager` all RUN a named program, so a text tool is not automatically
        a non-executor. Nothing here special-cases their options — they are
        simply not on `INERT_PROGRAMS`, and that is enough."""
        assert_denied(f"echo 'rm -rf /srv/data' > /tmp/x ; {reader}", RM_ROOT)

    def test_a_plain_invocation_of_the_same_tool_is_unaffected(self):
        """…and the finding costs the exemption nothing when the tool is not
        being handed a command: being an executor stops OTHER stages being
        blanked, and a plain search is still a search."""
        assert_allowed("rg 'rm -rf /srv/data' .")
        assert_allowed("rg --hidden --type=py 'rm -rf /srv/data' .")
        assert_allowed("rg 'rm -rf /srv/data' . | wc -l")


class TestAToolThatCanRunItsOwnOptionValue:
    """Review finding on #91 round 3: a text tool being an executor was used
    only to protect OTHER stages. But the destructive text can BE the option
    value it executes, and that text was blanked before matching."""

    @pytest.mark.parametrize(
        "command",
        [
            "rg --pre 'rm -rf /srv/data' needle .",
            "rg --pre='rm -rf /srv/data' needle .",
            "rg --hostname-bin 'rm -rf /srv/data' .",
            "ag --pager='rm -rf /srv/data' needle",
            "ack --pager 'rm -rf /srv/data' needle",
            "ack --ackrc='rm -rf /srv/data' needle",
        ],
    )
    def test_a_text_tool_handed_a_command_is_not_data_only(self, command):
        assert_denied(command, RM_ROOT)

    @pytest.mark.parametrize(
        "command",
        [
            "man -P 'rm -rf /srv/data' rm",
            "man -H 'rm -rf /srv/data' rm",
            "man -e 'rm -rf /srv/data' rm",
        ],
    )
    def test_man_is_off_the_data_only_list_entirely(self, command):
        """`man -P CMD` runs CMD through a shell, and the list bought nothing
        against that: no realistic `man …` contains text a pattern matches, so
        `man rm` was never allowed BECAUSE of the exemption."""
        assert_denied(command, RM_ROOT)

    def test_man_without_a_command_option_is_still_fine(self):
        assert_allowed("man rm")
        assert_allowed("man git-push")

    @pytest.mark.parametrize(
        "command",
        [
            "git -c alias.x='!rm -rf /srv/data' x --dry-run",
            "git --exec-path='rm -rf /srv/data' clean -fd --dry-run",
            "rsync -e 'rm -rf /srv/data' --dry-run src dst",
            "make --eval='$(shell rm -rf /srv/data)' --just-print",
            "git -c core.pager='rm -rf /srv/data' clean -fd --dry-run",
        ],
    )
    def test_a_dry_run_carrying_a_quoted_option_value_is_not_data_only(self, command):
        """Every program with a dry-run flag can also be made to run something,
        and every spelling of that carries the command in an OPTION VALUE. So
        the dry-run exemption requires bare words end to end — one rule, no
        per-program option table."""
        assert_denied(command, RM_ROOT)

    @pytest.mark.parametrize(
        "command,description",
        [
            ("git -c alias.x=!killall x -- --dry-run", KILLALL),
            ("git -c core.pager=mkfs clean -fd --dry-run", MKFS),
            ("git -c alias.x=!dropdb x mydb --dry-run", DROPDB),
        ],
    )
    def test_an_unquoted_option_value_is_not_a_bare_word_either(
        self, command, description
    ):
        """Review finding on #91 round 6: an unquoted alias value is a single
        token with no whitespace, and git hands it the arguments that follow —
        so quoting and whitespace were not the whole of it. `=` is what these
        have in common, and a real dry run has none of the three.

        These are the four single-word patterns, deliberately: a one-word
        command is exactly what fits in a bare option value, and round 3
        documented that as a residual. It is now closed."""
        assert_denied(command, description)

    def test_the_reported_shape_itself_is_no_longer_data_only(self):
        """The shape as reported. It is asserted at the predicate rather than
        through a verdict because the command contains no text any pattern
        matches — git's alias NAME sits between `!rm` and the later `-rf
        /srv/data`, so `rm -rf /` is never contiguous. The exemption applying
        to it was still wrong, and no longer does."""
        stage = "git -c alias.x=!rm x -rf /srv/data -- --dry-run"
        assert guard._stage_is_data_only(stage) is False
        assert guard.execution_surface(stage) == stage

    @pytest.mark.parametrize(
        "command",
        [
            "git clean -fd --dry-run",
            "git clean --dry-run -fdx",
            "git push --dry-run --force origin main",
        ],
    )
    def test_a_real_dry_run_is_bare_words_end_to_end(self, command):
        assert_allowed(command)

    @pytest.mark.parametrize(
        "command",
        [
            "rsync --dry-run -a /srv/data /backup/",
            "make --just-print clean",
            "npm ci --dry-run",
        ],
    )
    def test_the_programs_dropped_in_round_10_never_needed_the_exemption(self, command):
        """They match no pattern with or without it — which is the criterion
        `DRY_RUN_INVOCATIONS` now uses. Pinned so that shrinking the list is
        seen to have cost nothing."""
        assert_allowed(command)
        assert guard._stage_is_data_only(command) is False

    @pytest.mark.parametrize(
        "command,description",
        [
            # Review finding on #91 round 10: these tools take a COMMAND as
            # bare-word arguments, so a `--dry-run` among them may be the
            # payload's or ignored outright — it says nothing about the tool.
            ("kubectl exec pod -- rm -rf /srv/data --dry-run", RM_ROOT),
            ("docker run --dry-run alpine rm -rf /srv/data", RM_ROOT),
            ("npm exec --dry-run -- rm -rf /srv/data", RM_ROOT),
            ("git bisect run rm -rf /srv/data --dry-run", RM_ROOT),
            ("git submodule foreach rm -rf /srv/data --dry-run", RM_ROOT),
        ],
    )
    def test_a_dry_run_flag_among_a_command_payload_exempts_nothing(
        self, command, description
    ):
        assert_denied(command, description)

    def test_the_flag_must_be_the_tools_not_the_payloads(self):
        # After `--` the arguments belong to whatever the tool invokes, so a
        # dry-run flag there is not the tool's promise to keep.
        assert_denied("git clean -fd -- --dry-run", CLEAN)
        assert_allowed("git clean -fd --dry-run")

    def test_docker_system_prune_is_the_one_deliberate_casualty(self):
        """Docker has no `--dry-run` for `prune`, so this errors today anyway.
        Pinned so that adding `"docker": {"system"}` later is a decision rather
        than a drift."""
        assert_denied("docker system prune -a --dry-run", PRUNE)


class TestWhereADataOnlyStagesOutputEndsUp:
    """Route 3 in detail: the stage's output reaching a FILE that something in
    the same call can then run. Where the write happens, and how it is spelled,
    is not the stage's business — so neither is it this check's."""

    @pytest.mark.parametrize(
        "writer",
        [
            "tee /tmp/x",  # writes a file with no `>` in the command at all
            "cat > /tmp/x",  # the redirection belongs to a LATER stage
            "cat >> /tmp/x",
            "cp /dev/stdin /tmp/x",
            "cp /proc/self/fd/0 /tmp/x",
            "mv /dev/stdin /tmp/x",
        ],
    )
    def test_the_file_can_be_written_by_a_later_stage_of_the_pipeline(self, writer):
        """Review finding on #91 round 2: route 3 asks where this stage's
        OUTPUT ends up, so it has to follow the whole pipeline. `cat` is inert,
        so route 2 waves `echo … | cat > /tmp/x` through, and the redirection
        that puts the text on disk is not on the `echo` stage at all."""
        assert_denied(f"echo 'rm -rf /srv/data' | {writer} ; bash /tmp/x", RM_ROOT)

    def test_writing_it_is_still_fine_when_nothing_runs_it(self):
        assert_allowed("echo 'rm -rf /srv/data' | cat > /tmp/x")
        assert_allowed("echo 'rm -rf /srv/data' | tee /tmp/x")

    @pytest.mark.parametrize("consumer", ["tee", "tee -a", "tee --"])
    def test_tee_with_no_file_operand_writes_nothing(self, consumer):
        """Review nit on #91 round 9: `tee` writes to the files it is GIVEN.
        Bare, or with options only, it is a copy to stdout — so route 3 does
        not apply and a deny here is a false positive."""
        assert_allowed(f"echo 'rm -rf /srv/data' | {consumer} ; bash /tmp/x")

    @pytest.mark.parametrize("consumer", ["tee /tmp/x", "tee -a /tmp/x", "tee -- -x"])
    def test_tee_with_a_file_operand_however_spelled_does_write(self, consumer):
        assert_denied(f"echo 'rm -rf /srv/data' | {consumer} ; bash /tmp/x", RM_ROOT)

    @pytest.mark.parametrize("consumer", ["cp a b", "mv a b", "wc -l", "grep x"])
    def test_a_consumer_that_does_not_write_its_stdin_is_not_route_3(self, consumer):
        """Review finding on #91 round 5: `cp` and `mv` write their STDIN only
        when handed a path that is stdin. Treating every `cp` as a stdin writer
        blocked a pipeline whose text goes nowhere near a file."""
        assert_allowed(f"echo 'rm -rf /srv/data' | {consumer} ; bash /tmp/x")

    @pytest.mark.parametrize("redirection", [">", ">>", ">|", "1>", "&>", ">&", "2>"])
    def test_every_spelling_of_a_write_counts_as_one(self, redirection):
        assert_denied(
            f"echo 'rm -rf /srv/data' {redirection} /tmp/x ; bash /tmp/x", RM_ROOT
        )

    @pytest.mark.parametrize("filter_stage", ["tr a a", "head -1", "cat"])
    def test_a_filter_between_the_stage_and_the_write_changes_nothing(
        self, filter_stage
    ):
        assert_denied(
            f"echo 'rm -rf /srv/data' | {filter_stage} > /tmp/x ; bash /tmp/x", RM_ROOT
        )

    def test_pipe_with_stderr_is_one_operator_not_a_separator(self):
        """`|&` used to be split at the `&`, leaving the first segment ending
        in a bare `|` — so the stage after the pipe was the empty string, which
        runs nothing and did not stop the echo being blanked."""
        assert_denied("echo 'rm -rf /srv/data' |& bash", RM_ROOT)
        assert_denied("echo 'rm -rf /srv/data' |& sh -s", RM_ROOT)

    @pytest.mark.parametrize("consumer", ["grep x", "wc -l", "head -1", "cat"])
    def test_pipe_with_stderr_into_something_inert_stays_allowed(self, consumer):
        """The other half of reading `|&` as one operator (review on #91 round
        7): consuming only the `|` left the next stage reading `& grep x`,
        whose program parsed as `&` — on no allowlist, so an inert pipeline
        looked executable. A deny here is a false positive, not caution."""
        assert_allowed(f"echo 'rm -rf /srv/data' |& {consumer}")

    @pytest.mark.parametrize(
        "command",
        [
            # Review finding on #91 round 4: the shell requires no whitespace
            # around a redirection, and `str.split()`-shaped tokenization read
            # `/srv/data>/tmp/x` as one argument — so route 3 saw no write.
            "echo rm -rf /srv/data>/tmp/x ; bash /tmp/x",
            "echo rm -rf /srv/data>>/tmp/x ; bash /tmp/x",
            "echo 'rm -rf /srv/data'>/tmp/x ; bash /tmp/x",
            "printf %s 'rm -rf /srv/data'>/tmp/x ; bash /tmp/x",
            # …and it can be glued to a token of a LATER stage instead
            "echo 'rm -rf /srv/data' | cat>/tmp/x ; bash /tmp/x",
            "echo 'rm -rf /srv/data' | tr a a>/tmp/x ; bash /tmp/x",
            "grep -o 'rm -rf /srv/data' f>/tmp/x ; bash /tmp/x",
        ],
    )
    def test_a_redirection_glued_to_a_word_is_still_a_write(self, command):
        assert_denied(command, RM_ROOT)

    def test_a_glued_redirection_with_nothing_to_run_it_is_still_fine(self):
        assert_allowed("echo rm -rf /srv/data>/tmp/x")
        assert_allowed("echo 'rm -rf /srv/data' | cat>/tmp/x")

    @pytest.mark.parametrize("sink", ["cat", "tee"])
    def test_a_glued_redirection_does_not_rename_the_program(self, sink):
        """The same mis-parse reached TOM-379's data-sink test: `foo>/tmp/cat`
        was read as the program `cat`, so an arbitrary program's heredoc body
        was blanked as if it were data bound for a file."""
        assert_denied(f"foo>/tmp/{sink} <<'EOF'\nrm -rf /srv/data\nEOF", RM_ROOT)

    @pytest.mark.parametrize("opener", ["cat>/tmp/f", "cat >/tmp/f", "cat<<'EOF'"])
    def test_and_a_real_data_sink_is_recognised_however_it_is_spaced(self, opener):
        # The other half of the same mis-parse: these were FALSE POSITIVES.
        suffix = "" if opener.endswith("'EOF'") else " <<'EOF'"
        assert_allowed(f"{opener}{suffix}\nrm -rf /srv/data\nEOF")

    @pytest.mark.parametrize("dup", ["2>&1", ">&2", "2>&-"])
    def test_a_descriptor_duplication_is_not_a_write(self, dup):
        # `2>&1` opens no file, so route 3 does not apply and the executor
        # elsewhere in the call is irrelevant. Reading it as a write would
        # block a shape that puts nothing on disk at all.
        assert_allowed(f"echo 'rm -rf /srv/data' {dup} ; bash /tmp/x")

    def test_a_comment_is_discarded_by_the_shell_not_written_anywhere(self):
        # The counterpart: a comment's text cannot reach a file or a pipe, so
        # an executor elsewhere in the call is irrelevant to it.
        assert_allowed("# rm -rf /srv/data\nbash /tmp/x")

    @pytest.mark.parametrize(
        "command",
        [
            'echo "$(rm -rf /srv/data)"',
            "echo `rm -rf /srv/data`",
            "grep x <(rm -rf /srv/data)",
            # Double quotes do NOT stop a substitution.
            'echo "prefix $(rm -rf /srv/data) suffix"',
            'echo "prefix `rm -rf /srv/data` suffix"',
        ],
    )
    def test_a_substitution_inside_the_data_only_stage_is_not_data(self, command):
        assert_denied(command, RM_ROOT)

    @pytest.mark.parametrize(
        "command",
        [
            # Review finding on #91 round 11: the plainness test was a raw
            # substring check, so a pipe inside quotes — the commonest thing
            # this exemption exists for — stopped the stage being data.
            "echo 'rm -rf /srv/data | note'",
            'echo "rm -rf /srv/data | note"',
            "grep 'rm -rf /srv/data|note' file",
            "echo 'rm -rf /srv/data' > /tmp/f",
            "echo 'rm -rf /srv/data | note' > /tmp/f",
            # Single quotes and a backslash DO stop a substitution.
            "echo 'rm -rf /srv/data $(x)'",
            "echo 'rm -rf /srv/data `x`'",
            "grep 'rm -rf /srv/data <(x)' file",
            "echo rm\\ -rf\\ /srv/data\\|note",
        ],
    )
    def test_an_operator_the_shell_will_not_act_on_is_still_data(self, command):
        assert_allowed(command)

    def test_the_quote_aware_test_does_not_lose_a_real_operator(self):
        """A backslash inside SINGLE quotes is a literal, so the quote closes
        at the next `'` and what follows is unquoted. Reading it as an escape
        would swallow that quote and leave the scanner believing the rest of
        the stage is quoted — so the substitution here would look inert.

        The substitution rather than a pipe, deliberately: a pipe is caught by
        route 2 whatever the plainness test believes, so a test using one
        would pass with this logic broken."""
        assert_denied("echo 'a\\' $(rm -rf /srv/data)", RM_ROOT)
        assert_denied("echo 'rm -rf /srv/data\\' | bash", RM_ROOT)

    def test_a_consumer_that_cannot_execute_does_not_void_it(self):
        # tee writes a file; nothing in this call runs it. Same shape, and the
        # same verdict, as `cat > /tmp/x <<'EOF' … EOF`.
        assert_allowed("echo 'rm -rf /srv/data' | tee /tmp/x")


# ------------------------------------------------------- unit: the surface


class TestDataOnlyStagesOnTheSurface:
    """Character-exact assertions: a verdict alone cannot tell "blanked the
    arguments" from "blanked the whole line" or "skipped every pattern"."""

    def test_only_the_arguments_are_blanked(self):
        cmd = "echo hi && rm -rf /srv/data"
        assert guard.execution_surface(cmd) == "echo    && rm -rf /srv/data"

    def test_the_program_word_survives_but_nothing_else_does(self):
        cmd = "grep -r 'rm -rf /srv/data' ."
        assert guard.execution_surface(cmd) == "grep" + " " * (len(cmd) - 4)

    def test_a_redirection_is_an_action_and_stays_on_the_surface(self):
        # `printf 'x' > /etc/passwd` is a write to a system file whoever does
        # it, so the operator and its target are not blanked with the args.
        cmd = "printf 'x' > /etc/passwd"
        assert guard.execution_surface(cmd) == "printf     > /etc/passwd"

    def test_a_comment_stage_is_blanked_whole(self):
        cmd = "# rm -rf /srv/data\nls"
        assert guard.execution_surface(cmd) == " " * 18 + "\nls"

    def test_an_assignment_prefix_leaves_the_command_after_it_intact(self):
        cmd = "FOO=1 rm -rf /srv/data"
        assert guard.execution_surface(cmd) == cmd

    def test_an_assignment_only_stage_is_data(self):
        cmd = "FOO='rm -rf /srv/data'"
        assert guard.execution_surface(cmd) == " " * len(cmd)

    def test_nothing_is_blanked_when_the_call_can_execute(self):
        cmd = "echo 'rm -rf /srv/data' | bash"
        assert guard.execution_surface(cmd) == cmd


class TestIsSafeContextIsAStrictSubsetOfTheSurface:
    """It survives with a narrower meaning — EVERY stage is data-only — and it
    is deliberately a fast path rather than a second opinion. A prefix-shaped
    shortcut that can DISAGREE with the surface is the bug this ticket is
    about, so the invariant to hold is: whatever it accepts, the surface would
    have blanked to nothing but program words anyway."""

    @pytest.mark.parametrize(
        "command",
        [
            "FOO=1 rm -rf /srv/data",
            "echo hi && rm -rf /srv/data",
            "# note\nrm -rf /srv/data",
            'echo "$(rm -rf /srv/data)"',
            "grep -rn x . | wc -l",  # `wc` is not data-only, so not the whole command
            "git clean -fd --dry-run",  # `git` can run anything
            "printf 'x' > /etc/passwd",  # writes a file
        ],
    )
    def test_false_unless_the_whole_command_is_inert_data(self, command):
        assert guard.is_safe_context(command) is False

    @pytest.mark.parametrize(
        "command",
        ["grep -r 'rm -rf /srv/data' .", "# rm -rf /srv/data", "echo hi | grep x"],
    )
    def test_true_when_every_stage_is_data_only(self, command):
        assert guard.is_safe_context(command) is True

    @pytest.mark.parametrize(
        "command",
        [
            "grep -r 'rm -rf /srv/data' .",
            "echo 'git reset --hard HEAD~1'",
            "# rm -rf /srv/data",
            "MSG='rm -rf /srv/data'",
            "printf '%s' 'rm -rf /srv/data'",
            "echo hi | grep 'rm -rf /srv/data'",
        ],
    )
    def test_what_it_accepts_the_surface_would_have_blanked_anyway(self, command):
        """The subset invariant, asserted rather than asserted-about: remove
        the fast path and the verdict must not move."""
        assert guard.is_safe_context(command) is True
        surface = guard.execution_surface(command)
        matched = [d for p, d, _s in guard.ALL_PATTERNS if p.search(surface)]
        assert matched == [], f"surface {surface!r} still matches {matched}"

    def test_a_dry_run_is_allowed_by_the_surface_not_by_the_fast_path(self):
        # `git` can run anything (`git -c alias.x='!…'`), so the fast path
        # refuses it — and the stage is blanked all the same, because being an
        # executor is not what disqualifies a stage from having its own
        # arguments blanked.
        assert guard.is_safe_context("git clean -fd --dry-run") is False
        assert guard.execution_surface("git clean -fd --dry-run") == "git" + " " * 20
        assert_allowed("git clean -fd --dry-run")


class TestExecutionSurface:
    def test_length_is_preserved_so_anchored_patterns_keep_meaning(self):
        cmd = "cat > /tmp/f <<'EOF'\nrm -rf /srv/data\nEOF"
        assert len(guard.execution_surface(cmd)) == len(cmd)

    def test_body_becomes_spaces_and_newlines_survive(self):
        cmd = "cat > /tmp/f <<'EOF'\nrm -rf /srv/data\nEOF"
        assert (
            guard.execution_surface(cmd)
            == "cat > /tmp/f <<'EOF'\n" + " " * 16 + "\nEOF"
        )

    def test_newlines_inside_a_multiline_body_are_kept(self):
        # Line structure has to survive blanking or the `$`-anchored patterns
        # (`git restore .`, `rm -rf .`) silently change meaning.
        cmd = "cat > /tmp/f <<'EOF'\nfirst line\nsecond line\nEOF"
        assert (
            guard.execution_surface(cmd)
            == "cat > /tmp/f <<'EOF'\n" + " " * 10 + "\n" + " " * 11 + "\nEOF"
        )

    def test_nothing_is_blanked_for_an_unlisted_consumer(self):
        cmd = "bash <<'EOF'\nrm -rf /srv/data\nEOF"
        assert guard.execution_surface(cmd) == cmd

    def test_an_unquoted_body_with_a_substitution_is_not_blanked_at_all(self):
        # Not "blanked except the substitution span": finding where a
        # substitution ENDS needs a shell parser (see `_SUBSTITUTION_MARKERS`).
        cmd = "cat > /tmp/f <<EOF\nab $(id) cd\nEOF"
        assert guard.execution_surface(cmd) == cmd

    def test_an_unquoted_body_without_substitutions_is_still_blanked(self):
        cmd = "cat > /tmp/f <<EOF\nrm -rf /srv/data\nEOF"
        assert (
            guard.execution_surface(cmd) == "cat > /tmp/f <<EOF\n" + " " * 16 + "\nEOF"
        )

    def test_unterminated_heredoc_body_runs_to_end_of_input(self):
        # bash never executes an unterminated heredoc body either.
        cmd = "cat > /tmp/f <<'EOF'\nrm -rf /srv/data"
        assert guard.execution_surface(cmd) == "cat > /tmp/f <<'EOF'\n" + " " * 16

    def test_a_command_with_no_data_region_is_returned_unchanged(self):
        # Inert programs on purpose: a non-inert one would short-circuit at the
        # executor gate and never reach the blanking path this asserts about.
        cmd = "cat /tmp/notes && rm -rf /srv/data"
        assert guard.execution_surface(cmd) == cmd

    def test_python_payload_is_blanked_only_between_the_quotes(self):
        cmd = "python3 -c 'print(1)'"
        assert guard.execution_surface(cmd) == "python3 -c '" + " " * 8 + "'"

    def test_python_payload_mentioning_subprocess_is_left_alone(self):
        cmd = "python3 -c 'import subprocess as s'"
        assert guard.execution_surface(cmd) == cmd


class TestFailOpenAndScope:
    def test_non_bash_tools_are_never_screened(self):
        decision, _ = decide("git push --force origin main", tool_name="Write")
        assert decision == "allow"

    def test_surface_falls_back_to_the_whole_command_on_internal_error(
        self, monkeypatch
    ):
        """An unforeseen error must scan everything (block-side), never wedge."""

        def boom(*_args, **_kwargs):
            raise RuntimeError("synthetic")

        monkeypatch.setattr(guard, "_blank_heredoc_bodies", boom)
        cmd = "cat > /tmp/f <<'EOF'\nrm -rf /srv/data\nEOF"
        assert guard.execution_surface(cmd) == cmd

    def test_malformed_stdin_does_not_wedge_the_call(self):
        proc = subprocess.run(
            [sys.executable, str(HOOK)],
            input="not json",
            capture_output=True,
            text=True,
            timeout=30,
            env=_HOOK_ENV,
        )
        assert proc.returncode == 0
        assert json.loads(proc.stdout) == {}


class TestTheSuiteHasNoSideEffects:
    """Guards on the guards: a `block` verdict appends to an audit log and
    POSTs a high-priority ntfy alert. This file provokes ~40 of them per run.
    If the sandboxing in `_HOOK_ENV` ever stops working, these fail here
    rather than on somebody's phone."""

    def test_the_audit_log_lands_in_the_sandbox_home(self):
        log = (
            Path(_SANDBOX_HOME)
            / ".claude"
            / "permission-audit"
            / "destructive-blocks.jsonl"
        )
        before = log.stat().st_size if log.exists() else 0
        assert_denied("git reset --hard HEAD~1", RESET_HARD)
        assert log.exists(), "hook wrote its audit log outside the sandbox HOME"
        assert log.stat().st_size > before
        assert json.loads(log.read_text().splitlines()[-1])["description"] == RESET_HARD

    def test_the_proxy_the_hook_runs_behind_refuses_locally(self):
        """The premise of the sandbox: the ntfy POST never leaves the box."""
        from urllib.error import URLError
        from urllib.request import ProxyHandler, build_opener

        opener = build_opener(ProxyHandler({"http": _DEAD_PROXY, "https": _DEAD_PROXY}))
        with pytest.raises(URLError):
            opener.open("https://ntfy.sh/this-request-must-not-be-made", timeout=5)

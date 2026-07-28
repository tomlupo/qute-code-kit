"""Tests for the destructive-command guard, focused on TOM-379.

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
POSTs a high-priority ntfy alert. This file provokes ~40 blocks per run, so an
unsandboxed run pages a real phone forty times. `HOME` is redirected to a temp
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

    def test_other_interpreters_are_not_exempt(self):
        """Documented limitation: only python is exempted, because every
        other interpreter needs its own shell-out vocabulary."""
        assert_denied("perl -e 'print \"rm -rf /srv/data\"'", RM_ROOT)
        assert_denied("node -e 'console.log(\"rm -rf /srv/data\")'", RM_ROOT)


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
        # Bodies arrive in opener order: `A` belongs to cat, `B` to bash.
        assert_denied(
            "cat > /tmp/a <<'A' ; bash <<'B'\ngit reset --hard\nA\nrm -rf /srv/data\nB",
            RM_ROOT,
        )

    def test_here_string_is_not_a_heredoc(self):
        assert_denied("cat > /tmp/f <<<'rm -rf /srv/data'", RM_ROOT)


class TestCommandWordResolution:
    """Which program a segment runs decides whether its heredoc is data, so
    the leading-token walk has to survive the usual decorations."""

    def test_absolute_path_to_a_data_sink(self):
        assert_allowed("/bin/cat > /tmp/f <<'EOF'\ngit reset --hard HEAD~1\nEOF")

    def test_env_assignment_prefix_before_a_data_sink(self):
        # NOT written as `LC_ALL=C cat …`: a command *starting* with an
        # uppercase assignment is exempted wholesale by the pre-existing
        # `^[A-Z_]+=` rule in `is_safe_context`, so that spelling would pass
        # without exercising the surface at all — a test measuring nothing.
        # (That rule is a live bypass; reported separately, not fixed here.)
        assert_allowed("true && FOO=1 cat > /tmp/f <<'EOF'\ngit reset --hard\nEOF")

    def test_leading_redirection_before_a_data_sink(self):
        assert_allowed("2>/dev/null cat > /tmp/f <<'EOF'\ngit reset --hard HEAD~1\nEOF")

    def test_an_absolute_path_to_a_shell_is_still_a_shell(self):
        assert_denied("/bin/bash <<'EOF'\nrm -rf /srv/data\nEOF", RM_ROOT)


# ------------------------------------------------------- unit: the surface


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

    def test_expansion_span_survives_verbatim_in_an_unquoted_heredoc(self):
        cmd = "cat > /tmp/f <<EOF\nab $(id) cd\nEOF"
        assert guard.execution_surface(cmd) == "cat > /tmp/f <<EOF\n   $(id)   \nEOF"

    def test_unterminated_heredoc_body_runs_to_end_of_input(self):
        # bash never executes an unterminated heredoc body either.
        cmd = "cat > /tmp/f <<'EOF'\nrm -rf /srv/data"
        assert guard.execution_surface(cmd) == "cat > /tmp/f <<'EOF'\n" + " " * 16

    def test_a_command_with_no_data_region_is_returned_unchanged(self):
        cmd = "git push --force origin main && rm -rf /srv/data"
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

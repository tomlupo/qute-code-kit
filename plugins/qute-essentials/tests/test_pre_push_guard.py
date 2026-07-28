"""Tests for the pre-push branch guard (TOM-348).

Two layers, deliberately:

  * **Unit** — the stdin ref-line parser, the pre-commit env fallback, the
    guarded-destination decision, and the config resolution. Cheap, exhaustive
    on shapes.
  * **Integration** — real git repos in a tmp dir pushing to a real local bare
    remote, with the hook installed by `install_pre_push_guard.py`. This is the
    layer that matters: the whole point of `pre-push` over a command-string
    parser is that git decides what the refs are, so a test that only feeds
    synthetic stdin would be testing the wrong half.

The integration tests cover both installation worlds: the default
`.git/hooks` + `pre-commit` framework world, and the `core.hooksPath` world
where the framework's install is not usable at all.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
GUARD = ROOT / "templates" / "hooks" / "pre-push-branch-guard"
DISPATCHER = ROOT / "templates" / "hooks" / "pre-push"
INSTALLER = ROOT / "scripts" / "install_pre_push_guard.py"
ZERO = "0" * 40
ZERO256 = "0" * 64


def _load_guard():
    spec = importlib.util.spec_from_loader(
        "qute_pre_push_guard",
        importlib.machinery.SourceFileLoader("qute_pre_push_guard", str(GUARD)),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


guard = _load_guard()

_ispec = importlib.util.spec_from_file_location(
    "qute_install_pre_push_guard", str(INSTALLER)
)
installer = importlib.util.module_from_spec(_ispec)
_ispec.loader.exec_module(installer)
is_pre_commit_shim = installer.is_pre_commit_shim


# ------------------------------------------------------------------ unit


class TestParseRefLines:
    def test_single_update(self):
        line = f"refs/heads/feat/x {'a' * 40} refs/heads/main {'b' * 40}"
        assert guard.parse_ref_lines(line) == [
            ("refs/heads/feat/x", "a" * 40, "refs/heads/main", "b" * 40)
        ]

    def test_multiple_lines(self):
        text = (
            f"refs/heads/a {'1' * 40} refs/heads/a {ZERO}\n"
            f"refs/heads/b {'2' * 40} refs/heads/b {ZERO}\n"
        )
        assert len(guard.parse_ref_lines(text)) == 2

    def test_deletion_uses_the_literal_delete_token(self):
        # `git push origin --delete main` sends "(delete)" as the local ref.
        refs = guard.parse_ref_lines(f"(delete) {ZERO} refs/heads/main {'c' * 40}")
        assert refs == [("(delete)", ZERO, "refs/heads/main", "c" * 40)]

    @pytest.mark.parametrize("bad", ["", "\n", "only three fields", "a b c d e"])
    def test_malformed_lines_are_dropped_not_guessed_at(self, bad):
        assert guard.parse_ref_lines(bad) == []

    def test_zero_sentinel_both_hash_lengths(self):
        assert guard._is_zero(ZERO)
        assert guard._is_zero(ZERO256)
        assert not guard._is_zero("0" * 39 + "1")


class TestPreCommitEnvFallback:
    def test_reconstructs_one_ref(self):
        env = {
            "PRE_COMMIT_REMOTE_BRANCH": "refs/heads/main",
            "PRE_COMMIT_LOCAL_BRANCH": "refs/heads/feat/x",
            "PRE_COMMIT_FROM_REF": "d" * 40,
            "PRE_COMMIT_TO_REF": "e" * 40,
        }
        assert guard.refs_from_pre_commit_env(env) == [
            ("refs/heads/feat/x", "e" * 40, "refs/heads/main", "d" * 40)
        ]

    def test_absent_when_not_under_pre_commit(self):
        assert guard.refs_from_pre_commit_env({}) == []

    def test_stdin_wins_over_env(self):
        env = {"PRE_COMMIT_REMOTE_BRANCH": "refs/heads/main"}
        refs, source = guard.collect_refs(
            f"refs/heads/x {'1' * 40} refs/heads/feat/y {'2' * 40}", env
        )
        assert source == "stdin"
        assert refs[0][2] == "refs/heads/feat/y"

    def test_env_used_when_stdin_empty(self):
        env = {"PRE_COMMIT_REMOTE_BRANCH": "refs/heads/main"}
        refs, source = guard.collect_refs("", env)
        assert source == "pre-commit-env"
        assert refs[0][2] == "refs/heads/main"


class TestEvaluate:
    GUARDED = {"main", "dev"}

    def _refs(self, local_sha, remote_ref, remote_sha):
        return [("refs/heads/src", local_sha, remote_ref, remote_sha)]

    def test_protected_update_refused(self):
        refs = self._refs("a" * 40, "refs/heads/main", "b" * 40)
        assert guard.evaluate(refs, self.GUARDED) == ("main", "update")

    def test_integration_update_refused(self):
        refs = self._refs("a" * 40, "refs/heads/dev", "b" * 40)
        assert guard.evaluate(refs, self.GUARDED) == ("dev", "update")

    def test_feature_branch_allowed(self):
        refs = self._refs("a" * 40, "refs/heads/feat/x", "b" * 40)
        assert guard.evaluate(refs, self.GUARDED) is None

    def test_tag_allowed(self):
        refs = self._refs("a" * 40, "refs/tags/v1.0.0", ZERO)
        assert guard.evaluate(refs, self.GUARDED) is None

    def test_deletion_of_guarded_branch_refused(self):
        refs = [("(delete)", ZERO, "refs/heads/dev", "b" * 40)]
        assert guard.evaluate(refs, self.GUARDED) == ("dev", "delete")

    def test_deletion_of_unguarded_branch_allowed(self):
        refs = [("(delete)", ZERO, "refs/heads/feat/x", "b" * 40)]
        assert guard.evaluate(refs, self.GUARDED) is None

    def test_creating_a_guarded_branch_refused(self):
        refs = self._refs("a" * 40, "refs/heads/main", ZERO)
        assert guard.evaluate(refs, self.GUARDED) == ("main", "create")

    def test_guarded_ref_anywhere_in_a_multi_ref_push(self):
        refs = [
            ("refs/heads/a", "1" * 40, "refs/heads/feat/a", "2" * 40),
            ("refs/heads/b", "3" * 40, "refs/heads/main", "4" * 40),
        ]
        assert guard.evaluate(refs, self.GUARDED) == ("main", "update")

    def test_branch_named_like_a_guarded_one_is_not_matched(self):
        refs = self._refs("a" * 40, "refs/heads/mainline", "b" * 40)
        assert guard.evaluate(refs, self.GUARDED) is None


class TestLoadConfig:
    def _repo(self, tmp_path, cfg):
        (tmp_path / ".claude").mkdir(parents=True, exist_ok=True)
        if cfg is not None:
            (tmp_path / ".claude" / "git-guard.json").write_text(cfg)
        return tmp_path

    def test_no_file_means_not_opted_in(self, tmp_path):
        assert guard.load_config(self._repo(tmp_path, None)) is None

    def test_empty_object_gets_house_defaults(self, tmp_path, monkeypatch):
        monkeypatch.setattr(guard, "_remote_branch_exists", lambda *_: True)
        cfg = guard.load_config(self._repo(tmp_path, "{}"))
        assert cfg["protected"] == "main"
        assert cfg["integration"] == "dev"

    def test_dev_default_requires_origin_dev_to_exist(self, tmp_path, monkeypatch):
        monkeypatch.setattr(guard, "_remote_branch_exists", lambda *_: False)
        cfg = guard.load_config(self._repo(tmp_path, "{}"))
        assert cfg["integration"] is None

    def test_explicit_null_integration_is_honoured(self, tmp_path, monkeypatch):
        monkeypatch.setattr(guard, "_remote_branch_exists", lambda *_: True)
        cfg = guard.load_config(self._repo(tmp_path, '{"integration_branch": null}'))
        assert cfg["integration"] is None

    def test_custom_branches(self, tmp_path):
        cfg = guard.load_config(
            self._repo(
                tmp_path,
                '{"protected_branch": "master", "integration_branch": "staging"}',
            )
        )
        assert cfg["protected"] == "master"
        assert cfg["integration"] == "staging"

    def test_integration_equal_to_protected_collapses(self, tmp_path):
        cfg = guard.load_config(
            self._repo(
                tmp_path, '{"protected_branch": "main", "integration_branch": "main"}'
            )
        )
        assert cfg["integration"] is None

    # --- malformed config must fail CLOSED -------------------------------
    #
    # The presence of this file is somebody stating they want the repo
    # protected. A config that cannot be understood is that intent unmet, and a
    # guard that silently is not guarding is worse than no guard at all: the
    # repo LOOKS protected, so nobody re-checks.

    def test_malformed_json_fails_closed(self, tmp_path):
        with pytest.raises(guard.ConfigError, match="not valid JSON"):
            guard.load_config(self._repo(tmp_path, "{not json"))

    def test_json_that_is_not_an_object_fails_closed(self, tmp_path):
        with pytest.raises(guard.ConfigError, match="must contain a JSON object"):
            guard.load_config(self._repo(tmp_path, "[]"))

    @pytest.mark.parametrize(
        "value,was",
        [
            ("123", "silently matched no branch name — repo looked guarded"),
            ("true", "silently matched no branch name"),
            ('["main", "dev"]', "raised, then hit the fail-open handler"),
            ('{"a": 1}', "an object"),
            ('""', "empty string"),
            ('"ma in"', "not a valid branch name, so could never match a ref"),
        ],
    )
    def test_non_string_protected_branch_fails_closed(self, tmp_path, value, was):
        with pytest.raises(guard.ConfigError):
            guard.load_config(self._repo(tmp_path, f'{{"protected_branch": {value}}}'))

    def test_non_string_integration_branch_fails_closed(self, tmp_path):
        with pytest.raises(guard.ConfigError, match="integration_branch"):
            guard.load_config(self._repo(tmp_path, '{"integration_branch": 5}'))

    def test_non_string_release_tool_fails_closed(self, tmp_path):
        with pytest.raises(guard.ConfigError, match="release_tool"):
            guard.load_config(self._repo(tmp_path, '{"release_tool": 9}'))

    def test_message_names_field_value_and_the_supported_shape(self, tmp_path):
        """A refusal that does not say how to express the intent sends people
        back to editing config blind."""
        with pytest.raises(guard.ConfigError) as exc:
            guard.load_config(
                self._repo(tmp_path, '{"protected_branch": ["main","dev"]}')
            )
        msg = str(exc.value)
        assert "protected_branch" in msg  # the field
        assert '["main", "dev"]' in msg  # the value they wrote
        assert "must be a string" in msg  # what was expected
        assert "two branch slots, not a list" in msg  # how to say what they meant
        assert "integration_branch" in msg  # ...naming the other slot

    def test_unknown_keys_warn_but_do_not_refuse(self, tmp_path, capsys, monkeypatch):
        """Forward compatibility: the sibling guard reads this same file and may
        grow a field first. Hard-failing on a key we do not know yet would let
        one layer's release break the other."""
        monkeypatch.setattr(guard, "_remote_branch_exists", lambda *_: False)
        cfg = guard.load_config(self._repo(tmp_path, '{"future_field": 1}'))
        assert cfg["protected"] == "main"
        assert "unrecognised field(s) future_field" in capsys.readouterr().err


# ----------------------------------------------------------- integration

pytestmark_git = pytest.mark.skipif(
    shutil.which("git") is None, reason="git not available"
)


def _git_env(home: Path) -> dict:
    cfg = home / "gitconfig"
    cfg.write_text(
        "[user]\n  name = Test\n  email = t@example.com\n"
        "[init]\n  defaultBranch = main\n"
        '[protocol "file"]\n  allow = always\n'
    )
    return dict(
        os.environ,
        HOME=str(home),
        GIT_CONFIG_GLOBAL=str(cfg),
        GIT_CONFIG_SYSTEM="/dev/null",
    )


def _run(args, cwd, env, **kw):
    return subprocess.run(
        args, cwd=str(cwd), env=env, capture_output=True, text=True, **kw
    )


@pytest.fixture
def sandbox(tmp_path):
    """A repo with `main` + `dev` on a real bare remote, opted in to the guard."""
    home = tmp_path / "home"
    home.mkdir()
    env = _git_env(home)
    remote = tmp_path / "remote.git"
    repo = tmp_path / "repo"
    _run(["git", "init", "-q", "--bare", str(remote)], tmp_path, env)
    _run(["git", "init", "-q", str(repo)], tmp_path, env)
    _run(["git", "remote", "add", "origin", str(remote)], repo, env)
    (repo / "README.md").write_text("hello\n")
    _run(["git", "add", "-A"], repo, env)
    _run(["git", "commit", "-qm", "chore: init"], repo, env)
    _run(["git", "push", "-q", "--no-verify", "-u", "origin", "main"], repo, env)
    _run(["git", "branch", "dev"], repo, env)
    _run(["git", "push", "-q", "--no-verify", "origin", "dev"], repo, env)
    _run(["git", "fetch", "-q", "origin"], repo, env)
    (repo / ".claude").mkdir()
    (repo / ".claude" / "git-guard.json").write_text("{}\n")
    return {"repo": repo, "remote": remote, "env": env, "home": home}


def _install(sandbox, *extra):
    return _run(
        [sys.executable, str(INSTALLER), "--repo", str(sandbox["repo"]), *extra],
        sandbox["repo"],
        sandbox["env"],
    )


def _commit(sandbox, msg="chore: change"):
    repo = sandbox["repo"]
    (repo / "README.md").write_text((repo / "README.md").read_text() + msg + "\n")
    _run(["git", "add", "-A"], repo, sandbox["env"])
    _run(["git", "commit", "-qm", msg], repo, sandbox["env"])


def _push(sandbox, *args):
    return _run(["git", "push", *args], sandbox["repo"], sandbox["env"])


@pytestmark_git
class TestNativeWorld:
    """Default `.git/hooks`, no pre-commit framework in play."""

    def test_install_reports_and_verifies(self, sandbox):
        out = _install(sandbox)
        assert out.returncode == 0, out.stdout + out.stderr
        assert "world:      native" in out.stdout
        assert "result:     OK" in out.stdout
        hook = sandbox["repo"] / ".git" / "hooks" / "pre-push"
        assert os.access(hook, os.X_OK)

    def test_push_to_protected_is_refused_with_guidance(self, sandbox):
        _install(sandbox)
        _run(["git", "switch", "-qc", "feat/x"], sandbox["repo"], sandbox["env"])
        _commit(sandbox)
        out = _push(sandbox, "origin", "feat/x:main")
        assert out.returncode != 0
        combined = out.stdout + out.stderr
        assert "REFUSED" in combined
        assert "git switch -c" in combined  # says what to do instead
        assert "--no-verify" in combined  # names the deliberate override

    def test_push_to_integration_is_refused(self, sandbox):
        _install(sandbox)
        _run(["git", "switch", "-qc", "feat/x"], sandbox["repo"], sandbox["env"])
        _commit(sandbox)
        assert _push(sandbox, "origin", "feat/x:dev").returncode != 0

    def test_push_to_feature_branch_is_allowed(self, sandbox):
        _install(sandbox)
        _run(["git", "switch", "-qc", "feat/x"], sandbox["repo"], sandbox["env"])
        _commit(sandbox)
        out = _push(sandbox, "origin", "feat/x")
        assert out.returncode == 0, out.stdout + out.stderr

    def test_tag_push_is_allowed(self, sandbox):
        _install(sandbox)
        _run(
            ["git", "tag", "-a", "v0.1.0", "-m", "rel"], sandbox["repo"], sandbox["env"]
        )
        assert _push(sandbox, "origin", "v0.1.0").returncode == 0

    def test_deleting_a_guarded_branch_is_refused(self, sandbox):
        _install(sandbox)
        out = _push(sandbox, "origin", "--delete", "dev")
        assert out.returncode != 0
        assert "delete 'dev'" in out.stdout + out.stderr

    def test_no_verify_proceeds(self, sandbox):
        _install(sandbox)
        _run(["git", "switch", "-qc", "feat/x"], sandbox["repo"], sandbox["env"])
        _commit(sandbox)
        out = _push(sandbox, "--no-verify", "origin", "feat/x:main")
        assert out.returncode == 0, out.stdout + out.stderr

    def test_repo_without_config_file_is_not_opted_in(self, sandbox):
        (sandbox["repo"] / ".claude" / "git-guard.json").unlink()
        _install(sandbox)
        _commit(sandbox)
        out = _push(sandbox, "origin", "main")
        assert out.returncode == 0, out.stdout + out.stderr

    # --- the shapes that defeated the command-string parser ---------------

    def test_push_origin_HEAD_from_protected_is_refused(self, sandbox):
        _install(sandbox)
        _commit(sandbox)
        out = _push(sandbox, "origin", "HEAD")
        assert out.returncode != 0
        assert "'main'" in out.stdout + out.stderr

    def test_repo_flag_push_is_refused(self, sandbox):
        _install(sandbox)
        _commit(sandbox)
        out = _push(sandbox, "--repo=origin")
        assert out.returncode != 0

    def test_git_alias_wrapping_the_push_is_refused(self, sandbox):
        _install(sandbox)
        _commit(sandbox)
        out = _run(
            ["git", "-c", "alias.yolo=push origin HEAD", "yolo"],
            sandbox["repo"],
            sandbox["env"],
        )
        assert out.returncode != 0

    def test_inline_env_assignment_is_refused(self, sandbox):
        _install(sandbox)
        _commit(sandbox)
        out = _run(
            ["env", "SOME=1", "git", "push", "origin", "main"],
            sandbox["repo"],
            sandbox["env"],
        )
        assert out.returncode != 0


@pytestmark_git
class TestHooksPathWorld:
    """`core.hooksPath` — where the pre-commit framework's install is unusable."""

    def _set_hooks_path(self, sandbox, existing: str | None = None):
        repo, env = sandbox["repo"], sandbox["env"]
        (repo / ".githooks").mkdir()
        _run(["git", "config", "core.hooksPath", ".githooks"], repo, env)
        if existing is not None:
            hook = repo / ".githooks" / "pre-push"
            hook.write_text(existing)
            hook.chmod(0o755)

    def test_installs_into_the_configured_hooks_path(self, sandbox):
        self._set_hooks_path(sandbox)
        out = _install(sandbox)
        assert out.returncode == 0, out.stdout + out.stderr
        assert "world:      hooksPath" in out.stdout
        assert (sandbox["repo"] / ".githooks" / "pre-push").exists()
        assert not (sandbox["repo"] / ".git" / "hooks" / "pre-push").exists()
        _commit(sandbox)
        assert _push(sandbox, "origin", "main").returncode != 0

    def test_refuses_to_clobber_a_foreign_hook(self, sandbox):
        self._set_hooks_path(sandbox, "#!/bin/sh\nexit 0\n")
        out = _install(sandbox)
        assert out.returncode != 0
        assert "BLOCKED" in out.stdout
        assert (
            sandbox["repo"] / ".githooks" / "pre-push"
        ).read_text() == "#!/bin/sh\nexit 0\n"

    def test_adopt_existing_chains_the_old_hook_with_the_ref_lines(self, sandbox):
        self._set_hooks_path(
            sandbox,
            "#!/usr/bin/env bash\nwhile read -r a b c d; do "
            'echo "legacy saw $c" >&2; done\nexit 0\n',
        )
        out = _install(sandbox, "--adopt-existing")
        assert out.returncode == 0, out.stdout + out.stderr
        legacy = sandbox["repo"] / ".githooks" / "pre-push.d" / "00-legacy-pre-push"
        assert legacy.exists()

        _run(["git", "switch", "-qc", "feat/x"], sandbox["repo"], sandbox["env"])
        _commit(sandbox)
        allowed = _push(sandbox, "origin", "feat/x")
        assert allowed.returncode == 0, allowed.stdout + allowed.stderr
        # The chained hook must still receive stdin — the dispatcher reads the
        # ref lines once and replays them.
        assert "legacy saw refs/heads/feat/x" in allowed.stderr

        assert _push(sandbox, "origin", "feat/x:main").returncode != 0


@pytestmark_git
@pytest.mark.skipif(
    shutil.which("pre-commit") is None, reason="pre-commit framework not installed"
)
class TestPreCommitWorld:
    """A repo that uses pre-commit must still get the STRONGER mechanism.

    The framework's `pre-push` stage cannot see branch deletions or the tail of
    a multi-ref push. That is an acceptable tradeoff for a convenience hook and
    not for the enforcement layer, so `auto` must never select it while the
    native slot is available.
    """

    def _add_config(self, sandbox, stage="pre-commit"):
        (sandbox["repo"] / ".pre-commit-config.yaml").write_text(
            "repos:\n"
            "-   repo: local\n"
            "    hooks:\n"
            "    -   id: shout\n"
            "        name: shout\n"
            "        entry: bash -c 'echo PRECOMMIT-HOOK-RAN >&2'\n"
            "        language: system\n"
            "        always_run: true\n"
            "        pass_filenames: false\n"
            "        verbose: true\n"
            f"        stages: [{stage}]\n"
        )

    def test_auto_picks_native_when_the_slot_is_free(self, sandbox):
        self._add_config(sandbox)
        out = _install(sandbox)
        assert out.returncode == 0, out.stdout + out.stderr
        assert "mechanism:  native" in out.stdout
        assert (sandbox["repo"] / ".git" / "hooks" / "pre-push").exists()
        # and it must NOT have edited the repo's pre-commit config
        cfg = (sandbox["repo"] / ".pre-commit-config.yaml").read_text()
        assert "qute-pre-push-branch-guard" not in cfg

    def test_native_choice_sees_a_multi_ref_push_in_full(self, sandbox):
        """The concrete thing the framework path would have missed."""
        self._add_config(sandbox)
        _install(sandbox)
        _commit(sandbox)  # local main is now ahead of origin/main
        _run(["git", "switch", "-qc", "feat/x"], sandbox["repo"], sandbox["env"])
        _commit(sandbox)
        out = _push(sandbox, "origin", "feat/x", "main")
        combined = out.stdout + out.stderr
        assert out.returncode != 0, combined
        assert "'main'" in combined
        # nothing landed — the refusal covered the whole push
        assert (
            _run(
                ["git", "ls-remote", "--heads", "origin", "feat/x"],
                sandbox["repo"],
                sandbox["env"],
            ).stdout.strip()
            == ""
        )

    def test_native_choice_sees_deletions(self, sandbox):
        self._add_config(sandbox)
        _install(sandbox)
        assert _push(sandbox, "origin", "--delete", "dev").returncode != 0

    def test_existing_shim_is_relocated_and_still_runs_exactly_once(self, sandbox):
        self._add_config(sandbox, stage="pre-push")
        _run(
            ["pre-commit", "install", "--hook-type", "pre-push"],
            sandbox["repo"],
            sandbox["env"],
        )
        assert is_pre_commit_shim(sandbox["repo"] / ".git" / "hooks" / "pre-push")

        out = _install(sandbox)
        assert out.returncode == 0, out.stdout + out.stderr
        assert (
            sandbox["repo"] / ".git" / "hooks" / "pre-push.d" / "50-pre-commit"
        ).exists()

        _run(["git", "switch", "-qc", "feat/x"], sandbox["repo"], sandbox["env"])
        _commit(sandbox)
        allowed = _push(sandbox, "origin", "feat/x")
        assert allowed.returncode == 0, allowed.stdout + allowed.stderr
        combined = allowed.stdout + allowed.stderr
        assert combined.count("PRECOMMIT-HOOK-RAN") == 1, combined

    def test_coverage_survives_pre_commit_reclaiming_the_slot(self, sandbox):
        """`pre-commit install` DOES take the slot back — measured, not assumed.

        It moves our dispatcher to `<slot>.legacy`, which its shim runs first
        with the raw stdin and whose exit code it ORs into its own. So full
        fidelity survives; this test is what stops that from silently changing.
        """
        self._add_config(sandbox, stage="pre-push")
        _install(sandbox)
        _run(
            ["pre-commit", "install", "--hook-type", "pre-push"],
            sandbox["repo"],
            sandbox["env"],
        )
        hooks = sandbox["repo"] / ".git" / "hooks"
        assert is_pre_commit_shim(hooks / "pre-push")
        assert "qute-pre-push-dispatcher" in (hooks / "pre-push.legacy").read_text()

        _run(["git", "switch", "-qc", "feat/x"], sandbox["repo"], sandbox["env"])
        _commit(sandbox)
        allowed = _push(sandbox, "origin", "feat/x")
        assert allowed.returncode == 0, allowed.stdout + allowed.stderr
        # no double-run of the repo's own pre-commit hooks
        assert (allowed.stdout + allowed.stderr).count("PRECOMMIT-HOOK-RAN") == 1
        # and the deletion path — the thing the framework alone cannot see
        assert _push(sandbox, "origin", "--delete", "dev").returncode != 0
        assert _install(sandbox, "--check").returncode == 0

    def test_force_install_removes_the_guard_and_check_says_so(self, sandbox):
        """`pre-commit install -f` deletes `<slot>.legacy`. Detect, don't pretend."""
        self._add_config(sandbox, stage="pre-push")
        _install(sandbox)
        _run(
            ["pre-commit", "install", "-f", "--hook-type", "pre-push"],
            sandbox["repo"],
            sandbox["env"],
        )
        assert not (sandbox["repo"] / ".git" / "hooks" / "pre-push.legacy").exists()
        out = _install(sandbox, "--check", "--json")
        assert out.returncode != 0
        assert json.loads(out.stdout)["ok"] is False

    def test_explicit_framework_mechanism_fails_verification(self, sandbox):
        """If someone forces the weaker path, verification must FAIL, not warn."""
        self._add_config(sandbox)
        out = _install(sandbox, "--mechanism", "pre-commit", "--json")
        assert out.returncode != 0
        report = json.loads(out.stdout)
        cov = report["verification"]["coverage"]
        assert cov["protected_update"] is True  # it does catch the common case
        assert cov["delete_guarded"] is False  # but not deletions
        assert cov["multi_ref"] is False  # nor the tail of a multi-ref push
        assert report["ok"] is False


@pytestmark_git
class TestSharedHookPathIsNotAPerRepoInstall:
    """The rule is WHERE THE HOOK PATH POINTS, not which config named it.

    `git config --local core.hooksPath /home/me/.githooks` is exactly as shared
    as the global form: every repo pointed at that directory gets the same hook
    file, and the second repo to be "installed" silently inherits the first
    one's. Judging config scope instead of the resolved path let both of the
    repo-local shapes below straight through.
    """

    def _global_hooks_path(self, sandbox, tmp_path):
        shared = tmp_path / "shared-hooks"
        shared.mkdir(exist_ok=True)
        cfg = sandbox["home"] / "gitconfig"
        cfg.write_text(cfg.read_text() + f'[core]\n  hooksPath = "{shared}"\n')
        return shared

    def _local_hooks_path(self, sandbox, value):
        _run(
            ["git", "config", "--local", "core.hooksPath", str(value)],
            sandbox["repo"],
            sandbox["env"],
        )

    # --- the shapes the scope-based rule let straight through -------------

    def test_repo_local_absolute_path_outside_the_tree_is_refused(
        self, sandbox, tmp_path
    ):
        shared = tmp_path / "shared-hooks"
        shared.mkdir(exist_ok=True)
        self._local_hooks_path(sandbox, shared)
        # precondition: git considers this LOCAL config, so the old scope rule
        # would have called it a per-repo install
        assert _run(
            ["git", "config", "--local", "--get", "core.hooksPath"],
            sandbox["repo"],
            sandbox["env"],
        ).stdout.strip()

        out = _install(sandbox)
        assert out.returncode != 0, out.stdout
        assert "BLOCKED" in out.stdout
        assert list(shared.iterdir()) == []

    def test_repo_local_relative_path_escaping_the_tree_is_refused(
        self, sandbox, tmp_path
    ):
        escaped = sandbox["repo"].parent / "shared-hooks"
        escaped.mkdir(exist_ok=True)
        self._local_hooks_path(sandbox, "../shared-hooks")
        out = _install(sandbox)
        assert out.returncode != 0, out.stdout
        assert "BLOCKED" in out.stdout
        assert list(escaped.iterdir()) == []

    def test_second_repo_does_not_silently_inherit_the_first_ones_hook(
        self, sandbox, tmp_path
    ):
        """The concrete harm behind the rule."""
        shared = tmp_path / "shared-hooks"
        shared.mkdir(exist_ok=True)
        self._local_hooks_path(sandbox, shared)
        assert _install(sandbox, "--allow-shared-hooks-path").returncode == 0
        assert (shared / "pre-push").exists()

        second = tmp_path / "second"
        _run(["git", "init", "-q", str(second)], tmp_path, sandbox["env"])
        (second / ".claude").mkdir()
        (second / ".claude" / "git-guard.json").write_text("{}\n")
        _run(
            ["git", "config", "--local", "core.hooksPath", str(shared)],
            second,
            sandbox["env"],
        )
        out = _run(
            [sys.executable, str(INSTALLER), "--repo", str(second)],
            second,
            sandbox["env"],
        )
        assert out.returncode != 0
        # and the refusal must point at the hook that is already there
        assert "already" in out.stdout.lower()

    # --- the legitimate in-tree case must NOT need the flag ---------------

    def test_in_tree_hooks_path_installs_without_the_flag(self, sandbox):
        (sandbox["repo"] / ".githooks").mkdir()
        self._local_hooks_path(sandbox, ".githooks")
        out = _install(sandbox)
        assert out.returncode == 0, out.stdout + out.stderr
        assert (sandbox["repo"] / ".githooks" / "pre-push").exists()
        report = json.loads(_install(sandbox, "--check", "--json").stdout)
        assert report["hook_path_location"] == "in-repo"

    def test_default_git_hooks_dir_is_in_repo(self, sandbox):
        report = json.loads(_install(sandbox, "--json").stdout)
        assert report["hook_path_location"] == "in-repo"
        assert report["ok"] is True

    # --- global scope, refused by that same one rule ----------------------

    def test_global_hooks_path_is_refused_by_the_same_rule(self, sandbox, tmp_path):
        shared = self._global_hooks_path(sandbox, tmp_path)
        out = _install(sandbox)
        assert out.returncode != 0
        assert "BLOCKED" in out.stdout
        assert list(shared.iterdir()) == []

    def test_refusal_says_what_it_detected(self, sandbox, tmp_path):
        self._global_hooks_path(sandbox, tmp_path)
        out = _install(sandbox)
        assert "git runs:" in out.stdout
        assert "this repo is at:" in out.stdout
        assert "OUTSIDE the repository" in out.stdout
        assert "gitconfig" in out.stdout
        assert "--allow-shared-hooks-path" in out.stdout

    def test_proceeds_with_the_explicit_flag(self, sandbox, tmp_path):
        shared = self._global_hooks_path(sandbox, tmp_path)
        out = _install(sandbox, "--allow-shared-hooks-path")
        assert out.returncode == 0, out.stdout + out.stderr
        assert (shared / "pre-push").exists()

    def test_config_scope_no_longer_decides_anything(self, sandbox, tmp_path):
        """Same path, two config scopes, one verdict."""
        shared = tmp_path / "shared-hooks"
        shared.mkdir(exist_ok=True)
        self._local_hooks_path(sandbox, shared)
        local_rc = _install(sandbox).returncode
        _run(
            ["git", "config", "--local", "--unset", "core.hooksPath"],
            sandbox["repo"],
            sandbox["env"],
        )
        self._global_hooks_path(sandbox, tmp_path)
        global_rc = _install(sandbox).returncode
        assert local_rc == global_rc != 0


@pytestmark_git
class TestVerificationIsAMeasurement:
    def test_check_only_does_not_install(self, sandbox):
        out = _install(sandbox, "--check")
        assert out.returncode != 0
        assert not (sandbox["repo"] / ".git" / "hooks" / "pre-push").exists()

    def test_uninstalled_hook_is_reported_as_not_reachable(self, sandbox):
        out = _install(sandbox, "--check", "--json")
        report = json.loads(out.stdout)
        assert report["ok"] is False
        assert report["verification"]["reachable"] is False

    def test_inert_when_repo_not_opted_in(self, sandbox):
        (sandbox["repo"] / ".claude" / "git-guard.json").unlink()
        out = _install(sandbox, "--json")
        report = json.loads(out.stdout)
        assert report["ok"] is False
        names = [c["name"] for c in report["verification"]["checks"]]
        assert any("opted in" in n for n in names)

    def test_opt_in_flag_creates_the_config(self, sandbox):
        (sandbox["repo"] / ".claude" / "git-guard.json").unlink()
        out = _install(sandbox, "--opt-in")
        assert out.returncode == 0, out.stdout + out.stderr
        assert (
            sandbox["repo"] / ".claude" / "git-guard.json"
        ).read_text().strip() == "{}"

    def test_idempotent(self, sandbox):
        first = _install(sandbox)
        second = _install(sandbox)
        assert second.returncode == 0
        assert "unchanged" in second.stdout
        assert first.returncode == 0


@pytestmark_git
class TestFailsOpenLoudly:
    def test_internal_error_allows_the_push_but_says_so(self, sandbox, tmp_path):
        """A guard bug must not wedge every push — but it must never be silent."""
        _install(sandbox)
        broken = sandbox["repo"] / ".claude" / "hooks" / "pre-push-branch-guard"
        text = broken.read_text().replace(
            "def evaluate(refs, guarded):",
            "def evaluate(refs, guarded):\n    raise RuntimeError('boom')",
        )
        broken.write_text(text)
        _commit(sandbox)
        out = _push(sandbox, "origin", "main")
        assert out.returncode == 0
        assert "internal error" in out.stdout + out.stderr


@pytestmark_git
class TestInstallerNeverWritesOutsideTheRepo:
    """Three doors led outside during review; one gate now closes all of them.

    A `core.hooksPath` from global config, a repo-local one naming an outside
    directory, and a destination the repo checked in as a SYMLINK are the same
    bug wearing different clothes. `WriteGate` walks down from an approved root
    with `O_NOFOLLOW` per component, so escaping is structurally unreachable
    rather than something each call site has to remember to check.
    """

    def test_symlinked_guard_script_target_is_refused(self, sandbox, tmp_path):
        victim = tmp_path / "victim.txt"
        victim.write_text("PRECIOUS DATA")
        hooks = sandbox["repo"] / ".claude" / "hooks"
        hooks.mkdir(parents=True)
        (hooks / "pre-push-branch-guard").symlink_to(victim)

        out = _install(sandbox)
        assert out.returncode != 0
        assert "SYMLINK" in out.stdout
        assert victim.read_text() == "PRECIOUS DATA"

    def test_symlinked_config_target_is_refused(self, sandbox, tmp_path):
        victim = tmp_path / "victim.json"
        (sandbox["repo"] / ".claude" / "git-guard.json").unlink()
        (sandbox["repo"] / ".claude" / "git-guard.json").symlink_to(victim)
        out = _install(sandbox, "--opt-in")
        assert out.returncode != 0
        assert "SYMLINK" in out.stdout
        assert not victim.exists()

    def test_symlinked_directory_component_is_refused(self, sandbox, tmp_path):
        outside = tmp_path / "outside-dir"
        outside.mkdir()
        (sandbox["repo"] / ".claude" / "hooks").symlink_to(outside)
        out = _install(sandbox)
        assert out.returncode != 0
        assert "SYMLINK" in out.stdout
        assert list(outside.iterdir()) == []

    def test_symlinked_hook_slot_is_refused(self, sandbox, tmp_path):
        victim = tmp_path / "hook-victim"
        victim.write_text("original\n")
        (sandbox["repo"] / ".githooks").mkdir()
        (sandbox["repo"] / ".githooks" / "pre-push").symlink_to(victim)
        _run(
            ["git", "config", "--local", "core.hooksPath", ".githooks"],
            sandbox["repo"],
            sandbox["env"],
        )
        out = _install(sandbox, "--adopt-existing")
        assert out.returncode != 0
        assert "symlink" in out.stdout.lower()
        assert victim.read_text() == "original\n"

    def test_nothing_is_written_before_the_containment_rule_runs(
        self, sandbox, tmp_path
    ):
        """The ordering bug: the rule is decorative if files land before it."""
        shared = tmp_path / "shared-hooks"
        shared.mkdir()
        (sandbox["repo"] / ".claude" / "git-guard.json").unlink()
        (sandbox["repo"] / ".claude").rmdir()
        _run(
            ["git", "config", "--local", "core.hooksPath", str(shared)],
            sandbox["repo"],
            sandbox["env"],
        )
        out = _install(sandbox, "--opt-in")
        assert out.returncode != 0
        # neither the opt-in config nor the guard script may exist yet
        assert not (sandbox["repo"] / ".claude").exists()
        assert list(shared.iterdir()) == []

    def test_approved_shared_dir_is_writable_but_nothing_else_is(
        self, sandbox, tmp_path
    ):
        shared = tmp_path / "shared-hooks"
        shared.mkdir()
        _run(
            ["git", "config", "--local", "core.hooksPath", str(shared)],
            sandbox["repo"],
            sandbox["env"],
        )
        out = _install(sandbox, "--allow-shared-hooks-path")
        assert out.returncode == 0, out.stdout + out.stderr
        assert (shared / "pre-push").exists()
        # the repo's own files still went into the repo, not the shared dir
        assert (
            sandbox["repo"] / ".claude" / "hooks" / "pre-push-branch-guard"
        ).is_file()

    def test_gate_rejects_paths_outside_its_roots(self, tmp_path):
        root = tmp_path / "root"
        root.mkdir()
        gate = installer.WriteGate([root])
        with pytest.raises(installer.WriteRefused):
            gate.write(tmp_path / "elsewhere.txt", "x")
        with pytest.raises(installer.WriteRefused):
            gate.write(root / ".." / "escape.txt", "x")
        assert gate.write(root / "a" / "b" / "ok.txt", "x") == "created"
        assert (root / "a" / "b" / "ok.txt").read_text() == "x"


@pytestmark_git
class TestMalformedConfigRefusesRealPushes:
    """End-to-end counterpart of the unit tests: a bad config stops a push."""

    @pytest.mark.parametrize(
        "cfg",
        [
            '{"protected_branch": 123}',
            '{"protected_branch": ["main","dev"]}',
            '{"protected_branch": true}',
            "not json",
        ],
    )
    def test_bad_config_refuses_even_a_feature_branch_push(self, sandbox, cfg):
        _install(sandbox)
        (sandbox["repo"] / ".claude" / "git-guard.json").write_text(cfg)
        _run(["git", "switch", "-qc", "feat/x"], sandbox["repo"], sandbox["env"])
        _commit(sandbox)
        out = _push(sandbox, "origin", "feat/x")
        combined = out.stdout + out.stderr
        assert out.returncode != 0, "a config that guards nothing must not be silent"
        assert "config is unusable" in combined

    def test_bad_config_never_lets_a_push_to_main_through(self, sandbox):
        _install(sandbox)
        (sandbox["repo"] / ".claude" / "git-guard.json").write_text(
            '{"protected_branch": 123}'
        )
        _commit(sandbox)
        assert _push(sandbox, "origin", "main").returncode != 0

    def test_valid_config_still_allows_a_feature_push(self, sandbox):
        _install(sandbox)
        _run(["git", "switch", "-qc", "feat/x"], sandbox["repo"], sandbox["env"])
        _commit(sandbox)
        assert _push(sandbox, "origin", "feat/x").returncode == 0

    def test_no_verify_still_overrides_a_bad_config(self, sandbox):
        _install(sandbox)
        (sandbox["repo"] / ".claude" / "git-guard.json").write_text("not json")
        _run(["git", "switch", "-qc", "feat/x"], sandbox["repo"], sandbox["env"])
        _commit(sandbox)
        assert _push(sandbox, "--no-verify", "origin", "feat/x").returncode == 0


class TestOptInDetectionUsesLstat:
    """`is_file()` follows symlinks and is False for a broken one.

    A repo can carry a tracked `.claude/git-guard.json` that is a symlink to a
    gitignored or machine-specific path — a normal thing to do, not an attack.
    It reads as opted in to anyone looking at `git ls-files`, while the guard
    treated it as "no config" and waved every push through. Absent is still a
    no-op; present-but-not-a-regular-file now fails closed.
    """

    def _cfg(self, tmp_path):
        (tmp_path / ".claude").mkdir(parents=True, exist_ok=True)
        return tmp_path / ".claude" / "git-guard.json"

    def test_absent_config_is_still_a_no_op(self, tmp_path):
        self._cfg(tmp_path)
        assert guard.load_config(tmp_path) is None

    def test_broken_symlink_fails_closed(self, tmp_path):
        self._cfg(tmp_path).symlink_to(tmp_path / "does-not-exist.json")
        with pytest.raises(guard.ConfigError, match="symlink"):
            guard.load_config(tmp_path)

    def test_symlink_to_a_real_config_fails_closed(self, tmp_path):
        real = tmp_path / "real.json"
        real.write_text("{}")
        self._cfg(tmp_path).symlink_to(real)
        with pytest.raises(guard.ConfigError, match="symlink"):
            guard.load_config(tmp_path)

    def test_directory_named_like_the_config_fails_closed(self, tmp_path):
        self._cfg(tmp_path).mkdir()
        with pytest.raises(guard.ConfigError, match="directory"):
            guard.load_config(tmp_path)

    def test_regular_file_still_works(self, tmp_path, monkeypatch):
        monkeypatch.setattr(guard, "_remote_branch_exists", lambda *_: False)
        self._cfg(tmp_path).write_text("{}")
        assert guard.load_config(tmp_path)["protected"] == "main"


class TestQualifiedRefsNormalise:
    """`refs/heads/main` passed `check-ref-format refs/heads/refs/heads/main`
    — a legal ref name — then never matched a push to `main`.

    Chosen fix: NORMALISE to the short name rather than reject the spelling, so
    the guarded set always holds exactly what `evaluate()` compares against.
    Both spellings must therefore be indistinguishable.
    """

    def _cfg(self, tmp_path, body):
        (tmp_path / ".claude").mkdir(parents=True, exist_ok=True)
        (tmp_path / ".claude" / "git-guard.json").write_text(body)
        return tmp_path

    @pytest.mark.parametrize("spelling", ["main", "refs/heads/main"])
    def test_both_spellings_resolve_to_the_short_name(
        self, tmp_path, spelling, monkeypatch
    ):
        monkeypatch.setattr(guard, "_remote_branch_exists", lambda *_: False)
        cfg = guard.load_config(
            self._cfg(tmp_path, f'{{"protected_branch": "{spelling}"}}')
        )
        assert cfg["protected"] == "main"

    @pytest.mark.parametrize("spelling", ["dev", "refs/heads/dev"])
    def test_integration_branch_normalises_too(self, tmp_path, spelling):
        cfg = guard.load_config(
            self._cfg(tmp_path, f'{{"integration_branch": "{spelling}"}}')
        )
        assert cfg["integration"] == "dev"

    @pytest.mark.parametrize("spelling", ["main", "refs/heads/main"])
    def test_both_spellings_guard_the_same_push(self, tmp_path, spelling, monkeypatch):
        monkeypatch.setattr(guard, "_remote_branch_exists", lambda *_: False)
        cfg = guard.load_config(
            self._cfg(tmp_path, f'{{"protected_branch": "{spelling}"}}')
        )
        guarded = {b for b in (cfg["protected"], cfg["integration"]) if b}
        refs = [("refs/heads/x", "a" * 40, "refs/heads/main", "b" * 40)]
        assert guard.evaluate(refs, guarded) == ("main", "update")

    def test_collapse_still_works_through_the_qualified_spelling(self, tmp_path):
        """protected == integration must collapse regardless of spelling."""
        cfg = guard.load_config(
            self._cfg(
                tmp_path,
                '{"protected_branch": "main", "integration_branch": "refs/heads/main"}',
            )
        )
        assert cfg["integration"] is None

    @pytest.mark.parametrize(
        "value",
        ["refs/tags/v1", "refs/remotes/origin/main", "refs/heads/", "refs/", "refs/x"],
    )
    def test_non_branch_qualified_refs_fail_closed(self, tmp_path, value):
        with pytest.raises(guard.ConfigError):
            guard.load_config(self._cfg(tmp_path, f'{{"protected_branch": "{value}"}}'))

    def test_message_says_what_the_field_takes(self, tmp_path):
        with pytest.raises(guard.ConfigError) as exc:
            guard.load_config(
                self._cfg(tmp_path, '{"protected_branch": "refs/tags/v1"}')
            )
        msg = str(exc.value)
        assert "refs/tags/v1" in msg
        assert "branch NAME" in msg


@pytestmark_git
class TestQualifiedRefAndBadOptInOnRealPushes:
    def test_qualified_spelling_refuses_a_real_push_to_main(self, sandbox):
        _install(sandbox)
        (sandbox["repo"] / ".claude" / "git-guard.json").write_text(
            '{"protected_branch": "refs/heads/main"}'
        )
        _commit(sandbox)
        out = _push(sandbox, "origin", "main")
        assert out.returncode != 0, out.stdout + out.stderr
        assert "REFUSED" in out.stdout + out.stderr

    def test_qualified_spelling_still_allows_a_feature_push(self, sandbox):
        _install(sandbox)
        (sandbox["repo"] / ".claude" / "git-guard.json").write_text(
            '{"protected_branch": "refs/heads/main"}'
        )
        _run(["git", "switch", "-qc", "feat/x"], sandbox["repo"], sandbox["env"])
        _commit(sandbox)
        assert _push(sandbox, "origin", "feat/x").returncode == 0

    def test_broken_symlink_config_refuses_a_real_push(self, sandbox):
        _install(sandbox)
        cfg = sandbox["repo"] / ".claude" / "git-guard.json"
        cfg.unlink()
        cfg.symlink_to(sandbox["repo"] / "gone.json")
        _run(["git", "switch", "-qc", "feat/x"], sandbox["repo"], sandbox["env"])
        _commit(sandbox)
        out = _push(sandbox, "origin", "feat/x")
        assert out.returncode != 0
        assert "config is unusable" in out.stdout + out.stderr

    def test_installer_verification_agrees_with_the_guard_on_spelling(self, sandbox):
        """The installer must not carry its own idea of the guarded set."""
        (sandbox["repo"] / ".claude" / "git-guard.json").write_text(
            '{"protected_branch": "refs/heads/main"}'
        )
        out = _install(sandbox, "--json")
        report = json.loads(out.stdout)
        assert report["ok"] is True, out.stdout
        names = " ".join(c["name"] for c in report["verification"]["checks"])
        assert "'main'" in names  # short name, not refs/heads/main

    def test_installer_reports_an_unusable_config_instead_of_crashing(self, sandbox):
        (sandbox["repo"] / ".claude" / "git-guard.json").write_text(
            '{"protected_branch": ["main","dev"]}'
        )
        out = _install(sandbox, "--json")
        report = json.loads(out.stdout)
        assert report["ok"] is False
        assert any("usable" in c["name"] for c in report["verification"]["checks"]), (
            out.stdout
        )

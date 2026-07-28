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

    def test_malformed_json_fails_open(self, tmp_path, capsys):
        assert guard.load_config(self._repo(tmp_path, "{not json")) is None
        assert "unreadable or not valid JSON" in capsys.readouterr().err


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
class TestSharedHooksPathIsNotAPerRepoInstall:
    """`git config --get core.hooksPath` reads global config too.

    A repo that only inherits a user-wide `core.hooksPath` has a hook file
    shared by every repo of that user, so writing there is not the per-repo
    install the caller asked for. It must be refused by default.
    """

    def _set_global_hooks_path(self, sandbox, tmp_path):
        shared = tmp_path / "shared-hooks"
        shared.mkdir()
        cfg = sandbox["home"] / "gitconfig"
        cfg.write_text(cfg.read_text() + f'[core]\n  hooksPath = "{shared}"\n')
        # precondition: effective but not local
        assert _run(
            ["git", "config", "--get", "core.hooksPath"],
            sandbox["repo"],
            sandbox["env"],
        ).stdout.strip()
        assert not _run(
            ["git", "config", "--local", "--get", "core.hooksPath"],
            sandbox["repo"],
            sandbox["env"],
        ).stdout.strip()
        return shared

    def test_refuses_without_the_flag_and_writes_nothing(self, sandbox, tmp_path):
        shared = self._set_global_hooks_path(sandbox, tmp_path)
        out = _install(sandbox)
        assert out.returncode != 0
        assert "BLOCKED" in out.stdout
        assert "USER-WIDE" in out.stdout
        assert list(shared.iterdir()) == []

    def test_report_names_the_scope_and_the_origin(self, sandbox, tmp_path):
        self._set_global_hooks_path(sandbox, tmp_path)
        report = json.loads(_install(sandbox, "--json").stdout)
        assert report["hooks_path_scope"] == "shared"
        assert "gitconfig" in report["hooks_path_origin"]

    def test_proceeds_with_the_explicit_flag(self, sandbox, tmp_path):
        shared = self._set_global_hooks_path(sandbox, tmp_path)
        out = _install(sandbox, "--allow-shared-hooks-path")
        assert out.returncode == 0, out.stdout + out.stderr
        assert (shared / "pre-push").exists()

    def test_repo_local_hooks_path_needs_no_flag(self, sandbox):
        (sandbox["repo"] / ".githooks").mkdir()
        _run(
            ["git", "config", "--local", "core.hooksPath", ".githooks"],
            sandbox["repo"],
            sandbox["env"],
        )
        out = _install(sandbox)
        assert out.returncode == 0, out.stdout + out.stderr
        assert (
            json.loads(_install(sandbox, "--check", "--json").stdout)[
                "hooks_path_scope"
            ]
            == "local"
        )


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

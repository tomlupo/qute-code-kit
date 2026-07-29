"""Tests for the legacy git-guard migration step (TOM-351).

Real repos in a tmp dir, not mocks. The thing under test is a file edit, so a
test that asserts against a mocked filesystem asserts against its own fixture.
Four worlds, each one a repo that exists on disk:

  * **legacy** — the 2026-06-18 hand copy wired into a `settings.json` that also
    carries OTHER hooks. This is the one that matters: the migration has to be
    surgical, so the assertion is that the siblings survive BYTE-FOR-BYTE, not
    that they are "still there" semantically.
  * **migrated** — already through the step. Must be a no-op.
  * **clean** — never had the copy. Must be a no-op beyond the stamp.
  * **no-integration** — a repo with `origin/dev` that nonetheless has no
    integration branch (quantbox-live). The stamp must say `null` OUT LOUD;
    an omission there is silently the opposite answer.

Assertions are on parsed structure and on exact bytes, never on a substring of
a report — a report is what the code chose to say about itself.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "migrate_git_guard.py"
GUARD = ROOT / "hooks" / "git-workflow-guard.py"

_spec = importlib.util.spec_from_file_location("qute_migrate_git_guard", str(SCRIPT))
mig = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mig)


LEGACY_HOOK_BODY = '#!/usr/bin/env python3\n"""2026-06-18 hand copy."""\n'

# A settings.json shaped like the real ones: the legacy guard is ONE entry among
# several, in an event list that must come out intact around it.
SETTINGS_WITH_SIBLINGS = """{
  "permissions": {
    "allow": [
      "Bash(git status:*)"
    ]
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \\"$CLAUDE_PROJECT_DIR/.claude/hooks/other-guard.py\\""
          },
          {
            "type": "command",
            "command": "python3 \\"$CLAUDE_PROJECT_DIR/.claude/hooks/git-workflow-guard.py\\""
          }
        ]
      },
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \\"$CLAUDE_PROJECT_DIR/.claude/hooks/fmt.py\\""
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echo done"
          }
        ]
      }
    ]
  }
}
"""

# The quantbox shape: the legacy guard is the ONLY hook, so the whole chain
# above it goes empty and must be pruned rather than left as litter.
SETTINGS_ONLY_LEGACY = """{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \\"$CLAUDE_PROJECT_DIR/.claude/hooks/git-workflow-guard.py\\""
          }
        ]
      }
    ]
  }
}
"""


def _git(repo: Path, *args: str):
    return subprocess.run(
        ["git", *args], cwd=str(repo), capture_output=True, text=True, check=True
    )


def make_repo(tmp_path: Path, name: str, *, origin_dev: bool = False) -> Path:
    """A real git repo, optionally with a real `origin/dev` remote-tracking ref."""
    repo = tmp_path / name
    (repo / ".claude").mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    (repo / "README.md").write_text("x\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "init")

    remote = tmp_path / f"{name}-remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-q", "origin", "main")
    if origin_dev:
        _git(repo, "push", "-q", "origin", "main:dev")
    _git(repo, "fetch", "-q", "origin")
    return repo


def run_script(repo: Path, *args: str):
    import sys

    out = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(repo), *args],
        capture_output=True,
        text=True,
    )
    return out


# ------------------------------------------------------- legacy removal


def test_removes_legacy_hook_and_only_its_wiring(tmp_path):
    repo = make_repo(tmp_path, "legacy")
    (repo / ".claude" / "hooks").mkdir()
    (repo / ".claude" / "hooks" / "git-workflow-guard.py").write_text(LEGACY_HOOK_BODY)
    (repo / ".claude" / "hooks" / "other-guard.py").write_text("# other\n")
    settings = repo / ".claude" / "settings.json"
    settings.write_text(SETTINGS_WITH_SIBLINGS)

    out = run_script(repo)
    assert out.returncode == 0, out.stderr

    # The file is gone; the co-resident hook is not.
    assert not (repo / ".claude" / "hooks" / "git-workflow-guard.py").exists()
    assert (repo / ".claude" / "hooks" / "other-guard.py").read_text() == "# other\n"

    after = settings.read_text()
    data = json.loads(after)

    # Structure: exactly one entry left the Bash group, nothing else moved.
    pre = data["hooks"]["PreToolUse"]
    assert [g.get("matcher") for g in pre] == ["Bash", "Write"]
    assert [h["command"] for h in pre[0]["hooks"]] == [
        'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/other-guard.py"'
    ]
    assert data["hooks"]["Stop"][0]["hooks"][0]["command"] == "echo done"
    assert data["permissions"] == {"allow": ["Bash(git status:*)"]}

    # Bytes: the file must equal the original MINUS exactly the legacy entry
    # (and the comma that joined it). An equality against a literal derived from
    # the input is the assertion that cannot pass against a mangled file — a
    # substring check here would survive the whole rest of the file being lost.
    entry_block = (
        "          },\n"
        "          {\n"
        '            "type": "command",\n'
        '            "command": "python3 \\"$CLAUDE_PROJECT_DIR/.claude/hooks/git-workflow-guard.py\\""\n'
        "          }\n"
    )
    assert entry_block in SETTINGS_WITH_SIBLINGS  # the fixture still has the shape
    assert after == SETTINGS_WITH_SIBLINGS.replace(entry_block, "          }\n")


def test_prunes_emptied_containers(tmp_path):
    repo = make_repo(tmp_path, "onlylegacy")
    (repo / ".claude" / "hooks").mkdir()
    (repo / ".claude" / "hooks" / "git-workflow-guard.py").write_text(LEGACY_HOOK_BODY)
    settings = repo / ".claude" / "settings.json"
    settings.write_text(SETTINGS_ONLY_LEGACY)

    assert run_script(repo).returncode == 0

    data = json.loads(settings.read_text())
    # No `[]`, no `{}`, no orphan matcher group: the key itself is gone.
    assert "hooks" not in data
    assert "[]" not in settings.read_text()
    # The hooks dir held nothing else, so it goes too.
    assert not (repo / ".claude" / "hooks").exists()


def test_a_name_merely_containing_the_basename_is_not_the_legacy_hook(tmp_path):
    """Near-miss names must survive. This step DELETES; the match has to be exact.

    A raw substring test removes `not-git-workflow-guard.py` and
    `git-workflow-guard.py.bak`, and — being alone in their groups — takes their
    whole containers with them. The failure is destructive and silent.
    """
    for command in (
        'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/not-git-workflow-guard.py"',
        "python3 .claude/hooks/git-workflow-guard.py.bak",
        "echo git-workflow-guard.py.disabled",
    ):
        assert mig._names_legacy_script(command) is False, command

    # …while every real spelling still matches.
    for command in (
        'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/git-workflow-guard.py"',
        "python3 ./.claude/hooks/git-workflow-guard.py",
        "uv run /abs/path/.claude/hooks/git-workflow-guard.py",
        r"python3 .claude\hooks\git-workflow-guard.py",
    ):
        assert mig._names_legacy_script(command) is True, command

    # End to end: a repo wired to a near-miss comes out untouched.
    repo = make_repo(tmp_path, "nearmiss")
    settings = repo / ".claude" / "settings.json"
    body = SETTINGS_ONLY_LEGACY.replace(
        "/git-workflow-guard.py", "/not-git-workflow-guard.py"
    )
    settings.write_text(body)
    assert run_script(repo).returncode == 0
    assert settings.read_text() == body  # byte-for-byte


def test_leaves_unrelated_settings_file_untouched(tmp_path):
    repo = make_repo(tmp_path, "unrelated")
    settings = repo / ".claude" / "settings.json"
    body = '{\n  "hooks": {\n    "PreToolUse": [\n      {\n        "matcher": "Bash",\n        "hooks": [\n          {\n            "type": "command",\n            "command": "echo hi"\n          }\n        ]\n      }\n    ]\n  }\n}\n'
    settings.write_text(body)

    assert run_script(repo).returncode == 0
    assert settings.read_text() == body  # byte-for-byte


def test_settings_local_json_is_migrated_too(tmp_path):
    repo = make_repo(tmp_path, "local")
    (repo / ".claude" / "settings.local.json").write_text(SETTINGS_ONLY_LEGACY)
    assert run_script(repo).returncode == 0
    assert "hooks" not in json.loads(
        (repo / ".claude" / "settings.local.json").read_text()
    )


def test_malformed_settings_is_reported_not_mangled(tmp_path):
    repo = make_repo(tmp_path, "broken")
    settings = repo / ".claude" / "settings.json"
    settings.write_text("{ not json\n")
    out = run_script(repo)
    assert out.returncode == 1
    assert settings.read_text() == "{ not json\n"


# ------------------------------------------------------------ stamping


def test_stamps_empty_config_when_defaults_suffice(tmp_path):
    repo = make_repo(tmp_path, "clean", origin_dev=True)
    assert run_script(repo).returncode == 0
    # `{}` is complete: the guard supplies `main` + detected `dev`.
    assert json.loads((repo / ".claude" / "git-guard.json").read_text()) == {}


def test_explicit_null_integration_is_written_when_origin_dev_exists(tmp_path):
    repo = make_repo(tmp_path, "nointegration", origin_dev=True)
    assert run_script(repo, "--integration-branch", "none").returncode == 0
    raw = json.loads((repo / ".claude" / "git-guard.json").read_text())
    assert "integration_branch" in raw and raw["integration_branch"] is None

    # And the guard must READ it as "no integration branch" — the stamp is only
    # correct if the reader agrees with it.
    gspec = importlib.util.spec_from_file_location("qute_gwg", str(GUARD))
    gmod = importlib.util.module_from_spec(gspec)
    gspec.loader.exec_module(gmod)
    assert gmod._load_config(repo)["integration"] is None


def test_omits_null_integration_when_there_is_no_origin_dev(tmp_path):
    """Without `origin/dev`, detection already yields none — so say nothing."""
    repo = make_repo(tmp_path, "nodev")
    assert run_script(repo, "--integration-branch", "none").returncode == 0
    assert json.loads((repo / ".claude" / "git-guard.json").read_text()) == {}


def test_non_default_branches_are_written(tmp_path):
    repo = make_repo(tmp_path, "custom", origin_dev=True)
    assert (
        run_script(
            repo,
            "--protected-branch",
            "master",
            "--integration-branch",
            "staging",
            "--release-tool",
            "commitizen (/ship)",
        ).returncode
        == 0
    )
    assert json.loads((repo / ".claude" / "git-guard.json").read_text()) == {
        "protected_branch": "master",
        "integration_branch": "staging",
        "release_tool": "commitizen (/ship)",
    }


def test_explicitly_requested_house_defaults_are_still_omitted(tmp_path):
    """Asking for `main` + `dev` where those ARE the defaults still writes `{}`.

    Writing them anyway would be harmless-looking and wrong: a field in the file
    reads as a per-repo decision, so the repo would look like it had pinned
    `main` on purpose when nobody chose anything.
    """
    repo = make_repo(tmp_path, "explicitdefaults", origin_dev=True)
    assert (
        run_script(
            repo, "--protected-branch", "main", "--integration-branch", "dev"
        ).returncode
        == 0
    )
    assert json.loads((repo / ".claude" / "git-guard.json").read_text()) == {}


@pytest.mark.parametrize(
    "flag,value",
    [
        ("--integration-branch", "refs/remotes/origin/dev"),
        ("--integration-branch", "bad..name"),
        ("--integration-branch", "trailing "),
        ("--protected-branch", "refs/tags/v1"),
        ("--protected-branch", "feat//x"),
    ],
)
def test_branch_arguments_the_enforcement_layer_would_refuse_are_not_stamped(
    tmp_path, flag, value
):
    """A stamped config `pre-push` rejects breaks EVERY push in the repo.

    And it would be written by the step whose report says "migrated" — the same
    failure shape as the symlink and lstat cases. So the CLI value goes through
    the reader's own validation (imported, not mirrored) and a refusal stamps
    nothing.
    """
    repo = make_repo(tmp_path, f"badbranch-{abs(hash((flag, value)))}")
    out = run_script(repo, flag, value)
    assert out.returncode == 1
    assert not (repo / ".claude" / "git-guard.json").exists()

    # The refusal is the reader's own, so a repo could not have been left in a
    # state the reader accepts-but-we-rejected or vice versa.
    pre_push = ROOT / "templates" / "hooks" / "pre-push-branch-guard"
    pspec = importlib.util.spec_from_loader(
        "qute_pre_push_branchcheck",
        importlib.machinery.SourceFileLoader(
            "qute_pre_push_branchcheck", str(pre_push)
        ),
    )
    pmod = importlib.util.module_from_spec(pspec)
    pspec.loader.exec_module(pmod)
    key = flag.lstrip("-").replace("-", "_")
    with pytest.raises(pmod.ConfigError):
        pmod._branch_field(repo, {key: value}, key, allow_null=False)


def test_qualified_branch_argument_is_normalised_not_stamped_verbatim(tmp_path):
    """`refs/heads/dev` is legal but must be written as `dev`.

    Both layers normalise it that way, so a file that keeps the qualified form
    says something neither reader will echo back — and the "is this the default
    anyway?" comparison would miss, stamping a field nobody asked for.
    """
    repo = make_repo(tmp_path, "qualified")  # no origin/dev
    assert run_script(repo, "--integration-branch", "refs/heads/dev").returncode == 0
    assert json.loads((repo / ".claude" / "git-guard.json").read_text()) == {
        "integration_branch": "dev"
    }

    # And the qualified spelling of a HOUSE DEFAULT is still recognised as one.
    repo2 = make_repo(tmp_path, "qualified-default", origin_dev=True)
    assert run_script(repo2, "--protected-branch", "refs/heads/main").returncode == 0
    assert json.loads((repo2 / ".claude" / "git-guard.json").read_text()) == {}


def test_existing_config_is_never_rewritten(tmp_path):
    repo = make_repo(tmp_path, "hasconfig", origin_dev=True)
    cfg = repo / ".claude" / "git-guard.json"
    body = '{\n    "protected_branch": "main",\n    "integration_branch": "dev"\n}\n'
    cfg.write_text(body)
    assert run_script(repo).returncode == 0
    assert cfg.read_text() == body


@pytest.mark.parametrize("kind", ["symlink", "broken-symlink", "directory"])
def test_non_regular_config_is_a_problem_and_pre_push_agrees(tmp_path, kind):
    """ "Present" must mean the same thing here and at the enforcement layer.

    `pre-push` reads this path with `lstat` and raises `ConfigError` on anything
    that is not a regular file — it refuses every push rather than quietly
    guarding nothing. `is_file()` here would have followed the symlink (and
    answered False for a broken one), so the migrator would report the repo
    migrated, or stamp over it, while every push in that repo fails.
    """
    repo = make_repo(tmp_path, f"nonregular-{kind}")
    cfg = repo / ".claude" / "git-guard.json"
    if kind == "symlink":
        (repo / "real.json").write_text("{}\n")
        cfg.symlink_to(repo / "real.json")
    elif kind == "broken-symlink":
        cfg.symlink_to(tmp_path / "does-not-exist")
    else:
        cfg.mkdir()

    out = run_script(repo)
    assert out.returncode == 1
    assert "not a regular file" in out.stdout
    # Nothing was overwritten: the path is still what it was.
    assert cfg.is_symlink() if "symlink" in kind else cfg.is_dir()

    # And `pre-push` — the layer that actually refuses the push — says the same.
    pre_push = ROOT / "templates" / "hooks" / "pre-push-branch-guard"
    pspec = importlib.util.spec_from_loader(
        "qute_pre_push_for_migrate",
        importlib.machinery.SourceFileLoader(
            "qute_pre_push_for_migrate", str(pre_push)
        ),
    )
    pmod = importlib.util.module_from_spec(pspec)
    pspec.loader.exec_module(pmod)
    with pytest.raises(pmod.ConfigError):
        pmod.load_config(repo)


def test_no_stamp_with_no_config_says_the_repo_is_not_opted_in(tmp_path):
    """`--no-stamp` must not let the summary imply a config exists.

    The report is the only thing anyone reads afterwards, and "config already in
    place" over an ABSENT config is the one sentence that would stop a reader
    looking for why both guard layers are inert in that repo.
    """
    repo = make_repo(tmp_path, "nostamp")
    out = run_script(repo, "--no-stamp")
    assert out.returncode == 0
    assert not (repo / ".claude" / "git-guard.json").exists()
    assert "already present" not in out.stdout
    assert "NOT opted in" in out.stdout


def test_refuses_to_stamp_through_a_symlinked_claude_dir(tmp_path):
    """`.claude` pointing out of the tree must not become a write to elsewhere.

    The stamp is the one write that CREATES its path (`mkdir(parents=True)` +
    `write_text`), so it follows a symlink by default — and the damage is
    silent: another repo ends up with a `git-guard.json` arming a guard nobody
    opted it into. Caught on the RESOLVED path, so an outside `.claude` and an
    outside ancestor are the same case.
    """
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    repo = tmp_path / "symlinked"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    (repo / ".claude").symlink_to(outside, target_is_directory=True)

    out = run_script(repo)
    assert out.returncode == 1
    # The write did not happen anywhere: not in the repo, not at the target.
    assert not (outside / "git-guard.json").exists()
    assert list(outside.iterdir()) == []


def test_stamper_default_detection_matches_the_guard(tmp_path):
    """The stamper's "this is the default anyway" must be the guard's default."""
    for dev in (True, False):
        repo = make_repo(tmp_path, f"agree{dev}", origin_dev=dev)
        assert mig.remote_branch_exists(repo, "dev") is dev
        (repo / ".claude" / "git-guard.json").write_text("{}\n")
        gspec = importlib.util.spec_from_file_location("qute_gwg2", str(GUARD))
        gmod = importlib.util.module_from_spec(gspec)
        gspec.loader.exec_module(gmod)
        expected = "dev" if dev else None
        assert gmod._load_config(repo)["integration"] == expected


# ---------------------------------------------------------- idempotence


def _snapshot(repo: Path) -> dict:
    return {
        str(p.relative_to(repo)): p.read_bytes()
        for p in sorted((repo / ".claude").rglob("*"))
        if p.is_file()
    }


@pytest.mark.parametrize("world", ["legacy", "migrated", "clean"])
def test_second_run_is_a_no_op(tmp_path, world):
    repo = make_repo(tmp_path, f"idem-{world}", origin_dev=True)
    if world == "legacy":
        (repo / ".claude" / "hooks").mkdir()
        (repo / ".claude" / "hooks" / "git-workflow-guard.py").write_text(
            LEGACY_HOOK_BODY
        )
        (repo / ".claude" / "settings.json").write_text(SETTINGS_WITH_SIBLINGS)
    elif world == "migrated":
        (repo / ".claude" / "git-guard.json").write_text("{}\n")

    assert run_script(repo).returncode == 0
    first = _snapshot(repo)
    out = run_script(repo)
    assert out.returncode == 0
    assert _snapshot(repo) == first

    # And the second run says so, rather than reporting phantom work.
    assert json.loads(run_script(repo, "--json").stdout)["changed"] is False


def test_check_mode_writes_nothing(tmp_path):
    repo = make_repo(tmp_path, "checkmode")
    (repo / ".claude" / "hooks").mkdir()
    (repo / ".claude" / "hooks" / "git-workflow-guard.py").write_text(LEGACY_HOOK_BODY)
    (repo / ".claude" / "settings.json").write_text(SETTINGS_ONLY_LEGACY)
    before = _snapshot(repo)

    out = run_script(repo, "--check", "--json")
    assert out.returncode == 0
    assert json.loads(out.stdout)["changed"] is True
    assert _snapshot(repo) == before


# --------------------------------------------------- contract documentation


def test_contract_prose_states_the_opt_in_and_the_overrides():
    """The two facts a repo's CLAUDE.md must carry, asserted on the prose source.

    `templates/rules/` is retired (f93dbc5); this is the file step 5 writes into
    CLAUDE.md, so it is where the guard's contract has to live.
    """
    prose = (ROOT / "templates" / "contract" / "git-workflow.md").read_text()
    assert not (ROOT / "templates" / "rules").exists()
    for fact in (
        ".claude/git-guard.json",
        "presence",
        "/guard git-workflow off",
        "--no-verify",
    ):
        assert fact in prose, f"contract prose does not state: {fact}"

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


def test_existing_config_is_never_rewritten(tmp_path):
    repo = make_repo(tmp_path, "hasconfig", origin_dev=True)
    cfg = repo / ".claude" / "git-guard.json"
    body = '{\n    "protected_branch": "main",\n    "integration_branch": "dev"\n}\n'
    cfg.write_text(body)
    assert run_script(repo).returncode == 0
    assert cfg.read_text() == body


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

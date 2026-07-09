"""Tests for the jimek-onboard detect + template + validate logic.

These do NOT require a dispatcher checkout — they exercise detection heuristics,
templating, and the bundled structural validator. The bundled validator encodes
the same critical invariant as the authoritative loader for `rigor.<tier>.path`,
so the W1c "commit" regression is caught here in CI.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "jimek_onboard.py"
_spec = importlib.util.spec_from_file_location("jimek_onboard", _SCRIPT)
jo = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(jo)


def _make_repo(
    tmp_path: Path, name: str, claude_md: str = "", pyproject: str = ""
) -> Path:
    repo = tmp_path / name
    repo.mkdir()
    (repo / ".git").mkdir()  # enough for detection; git commands degrade gracefully
    if claude_md:
        (repo / "CLAUDE.md").write_text(claude_md, encoding="utf-8")
    if pyproject:
        (repo / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    return repo


# ── detection ────────────────────────────────────────────────────────────────
def test_detect_default_repo_uses_main_and_commit_to_default(tmp_path):
    conv = jo.detect_conventions(_make_repo(tmp_path, "some-lib"))
    assert conv["base"] == "main"
    assert conv["trivial_path"] == "commit-to-default"
    assert conv["live_capital"] is False


def test_detect_known_dev_base_repo(tmp_path):
    conv = jo.detect_conventions(_make_repo(tmp_path, "dm-evo"))
    assert conv["base"] == "dev"


def test_detect_base_from_doc_marker(tmp_path):
    repo = _make_repo(
        tmp_path, "widget", claude_md="All work: feat branch → PR to dev."
    )
    assert jo.detect_conventions(repo)["base"] == "dev"


def test_detect_forbids_direct_commits_forces_pr_trivial(tmp_path):
    repo = _make_repo(
        tmp_path, "widget", claude_md="This repo forbids direct commits to main."
    )
    assert jo.detect_conventions(repo)["trivial_path"] == "pr"


def test_detect_live_capital_repo(tmp_path):
    assert (
        jo.detect_conventions(_make_repo(tmp_path, "quantbox"))["live_capital"] is True
    )


def test_detect_live_capital_from_marker(tmp_path):
    repo = _make_repo(tmp_path, "widget", claude_md="This is a live-capital surface.")
    assert jo.detect_conventions(repo)["live_capital"] is True


def test_detect_tag_pattern_from_commitizen(tmp_path):
    repo = _make_repo(
        tmp_path,
        "widget",
        pyproject='[tool.commitizen]\ntag_format = "v$version"\n',
    )
    assert jo.detect_conventions(repo)["tag_pattern"] == "v*"


def test_tag_pattern_survives_inline_comment(tmp_path):
    repo = _make_repo(
        tmp_path,
        "widget",
        pyproject='[tool.commitizen]\ntag_format = "rel-$version"  # trailing comment\n',
    )
    assert jo.detect_conventions(repo)["tag_pattern"] == "rel-*"


def test_tag_pattern_defaults_without_pyproject(tmp_path):
    assert jo.detect_conventions(_make_repo(tmp_path, "widget"))["tag_pattern"] == "v*"


def test_assignee_is_a_login_never_a_display_name(tmp_path):
    # No gh + no git override → the fleet-login fallback, never a spaced name.
    conv = jo.detect_conventions(_make_repo(tmp_path, "widget"))
    assert " " not in conv["assignee"]
    doc = yaml.safe_load(jo.render_jimek_yml(conv))
    assert doc["prFlow"]["assignTo"] == conv["assignee"]


# ── templating ───────────────────────────────────────────────────────────────
def _render(**overrides) -> dict:
    conv = {
        "name": "widget",
        "base": "main",
        "trivial_path": "commit-to-default",
        "live_capital": False,
        "tag_pattern": "v*",
        "release_branch": "main",
        "assignee": "tomlupo",
    }
    conv.update(overrides)
    return yaml.safe_load(jo.render_jimek_yml(conv))


def test_render_is_valid_yaml_and_has_core_keys():
    doc = _render()
    for key in ("version", "board_states", "concurrency", "rigor", "worktree", "turns"):
        assert key in doc
    assert doc["version"] == 1


def test_render_all_rigor_paths_are_schema_valid():
    for tp in ("commit-to-default", "pr"):
        doc = _render(trivial_path=tp)
        for tier, spec in doc["rigor"].items():
            assert spec["path"] in jo.VALID_PATHS, f"{tier} -> {spec['path']}"


def test_render_never_emits_the_w1c_commit_bug():
    text = jo.render_jimek_yml(
        {
            "name": "widget",
            "base": "dev",
            "trivial_path": "pr",
            "live_capital": True,
            "tag_pattern": "v*",
            "release_branch": "main",
            "assignee": "tomlupo",
        }
    )
    # No bare `path: commit` anywhere (only `commit-to-default` is legal).
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("path:"):
            assert stripped.split(":", 1)[1].strip() in jo.VALID_PATHS


def test_render_base_branch_propagates():
    assert _render(base="dev")["baseBranch"] == "dev"


def test_render_live_capital_sets_escalation():
    doc = _render(live_capital=True)
    assert doc["escalation"]["block_on"] == [
        "live_capital",
        "irreversible_op",
        "design_fork",
    ]
    assert _render(live_capital=False)["escalation"]["block_on"] == []


def test_render_commit_to_default_trivial_has_no_review():
    doc = _render(trivial_path="commit-to-default")
    assert doc["rigor"]["trivial"]["review"] == []


# ── review-gate branch trigger (regression: 2026-07-09 codex blocker) ─────────
def test_review_gate_triggers_on_detected_master_base():
    # A master-base repo must get a gate that fires on `master`, else onboarding
    # installs a gate that never runs for the repo's PRs.
    conv = _render_conv()
    conv.update(base="master", release_branch="master")
    text = jo.render_review_gate_yml(conv)
    doc = yaml.safe_load(text)
    branches = doc[True]["pull_request"]["branches"]  # YAML `on:` parses to True
    assert branches == ["master"]
    # And the GitHub Actions expressions survived intact (not mangled).
    assert "${{ github.token }}" in text
    assert "${COUNT:-0}" in text


def test_review_gate_covers_base_and_release_for_dev_repos():
    conv = _render_conv()
    conv.update(base="dev", release_branch="main")
    doc = yaml.safe_load(jo.render_review_gate_yml(conv))
    assert doc[True]["pull_request"]["branches"] == ["dev", "main"]


def test_review_gate_is_valid_yaml_and_single_job():
    doc = yaml.safe_load(jo.render_review_gate_yml(_render_conv()))
    assert "require-independent-reviewer" in doc["jobs"]


def test_builtin_validate_skips_when_pyyaml_absent(monkeypatch):
    # Simulate a plain-python3 runner with no PyYAML: the check must SKIP
    # (return None), not raise or report a blocking error — so main() can still
    # stamp (regression: 2026-07-09 codex blocker on the hard PyYAML dep).
    import builtins

    real_import = builtins.__import__

    def _no_yaml(name, *a, **k):
        if name == "yaml":
            raise ImportError("No module named 'yaml'")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", _no_yaml)
    assert jo.builtin_validate(jo.render_jimek_yml(_render_conv())) is None


# ── bundled validator ────────────────────────────────────────────────────────
def test_builtin_validate_accepts_rendered():
    assert jo.builtin_validate(jo.render_jimek_yml(_render_conv())) == []


def _render_conv() -> dict:
    return {
        "name": "widget",
        "base": "main",
        "trivial_path": "commit-to-default",
        "live_capital": False,
        "tag_pattern": "v*",
        "release_branch": "main",
        "assignee": "tomlupo",
    }


def test_builtin_validate_rejects_commit_path():
    bad = jo.render_jimek_yml(_render_conv()).replace(
        "path: commit-to-default", "path: commit"
    )
    errors = jo.builtin_validate(bad)
    assert any("commit" in e and "invalid" in e for e in errors)


def test_builtin_validate_rejects_missing_key():
    doc = yaml.safe_load(jo.render_jimek_yml(_render_conv()))
    del doc["worktree"]
    errors = jo.builtin_validate(yaml.safe_dump(doc))
    assert any("worktree" in e for e in errors)


def test_builtin_validate_rejects_commit_to_default_with_review():
    doc = yaml.safe_load(jo.render_jimek_yml(_render_conv()))
    doc["rigor"]["trivial"]["review"] = ["codex"]
    errors = jo.builtin_validate(yaml.safe_dump(doc))
    assert any("commit-to-default cannot require review" in e for e in errors)

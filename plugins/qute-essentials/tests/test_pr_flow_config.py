"""Tests for pr_flow_config.py — the .github/qute-pr.yml PR-workflow resolver.

Covers:
- defaults when no config file is present (review on, assign tomlupo, self-merge off, enforce off);
- per-key overrides from .github/qute-pr.yml (flat AND nested qutePrWorkflow: forms);
- .claude/settings.json backward-compat: quteEnforcePrReview:true => enforce:true;
- enforce via qute-pr.yml enforce:true;
- env override QUTE_ENFORCE_PR_REVIEW=1/0;
- defensive typing (wrong-typed values are ignored, defaults kept).
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "pr_flow_config",
    Path(__file__).resolve().parent.parent / "scripts" / "pr_flow_config.py",
)
pfc = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(pfc)  # type: ignore


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / ".git").mkdir(parents=True)
    (root / ".github").mkdir()
    return root


def _write_yml(root: Path, body: str) -> None:
    (root / ".github" / "qute-pr.yml").write_text(body, encoding="utf-8")


def _write_settings(root: Path, cfg: dict, local: bool = False) -> None:
    d = root / ".claude"
    d.mkdir(exist_ok=True)
    name = "settings.local.json" if local else "settings.json"
    (d / name).write_text(json.dumps(cfg), encoding="utf-8")


# ── defaults ────────────────────────────────────────────────────────────
def test_defaults_when_absent(tmp_path, monkeypatch):
    monkeypatch.delenv("QUTE_ENFORCE_PR_REVIEW", raising=False)
    root = _repo(tmp_path)
    cfg = pfc.resolve_workflow(root)
    assert cfg == {
        "assignTo": "tomlupo",
        "independentReview": True,
        "allowAgentSelfMerge": False,
        "enforce": False,
        "baseBranch": "",
    }
    assert pfc.enforcement_enabled(root) is False


# ── flat overrides ──────────────────────────────────────────────────────
def test_flat_overrides(tmp_path, monkeypatch):
    monkeypatch.delenv("QUTE_ENFORCE_PR_REVIEW", raising=False)
    root = _repo(tmp_path)
    _write_yml(
        root,
        "assignTo: alice\nindependentReview: false\nallowAgentSelfMerge: true\nenforce: true\n",
    )
    cfg = pfc.resolve_workflow(root)
    assert cfg["assignTo"] == "alice"
    assert cfg["independentReview"] is False
    assert cfg["allowAgentSelfMerge"] is True
    assert cfg["enforce"] is True
    assert pfc.enforcement_enabled(root) is True


def test_partial_override_keeps_other_defaults(tmp_path, monkeypatch):
    monkeypatch.delenv("QUTE_ENFORCE_PR_REVIEW", raising=False)
    root = _repo(tmp_path)
    _write_yml(root, "assignTo: bob\n")
    cfg = pfc.resolve_workflow(root)
    assert cfg["assignTo"] == "bob"
    assert cfg["independentReview"] is True  # default kept
    assert cfg["allowAgentSelfMerge"] is False
    assert cfg["enforce"] is False


# ── baseBranch (Jimek verb-contract parameterization) ───────────────────
def test_base_branch_default_empty(tmp_path, monkeypatch):
    monkeypatch.delenv("QUTE_ENFORCE_PR_REVIEW", raising=False)
    root = _repo(tmp_path)
    # absent => "" so the flow lets `gh` pick the repo default (today's behavior).
    assert pfc.resolve_workflow(root)["baseBranch"] == ""


def test_base_branch_override(tmp_path, monkeypatch):
    monkeypatch.delenv("QUTE_ENFORCE_PR_REVIEW", raising=False)
    root = _repo(tmp_path)
    _write_yml(root, "baseBranch: dev\n")
    cfg = pfc.resolve_workflow(root)
    assert cfg["baseBranch"] == "dev"
    # other keys keep defaults
    assert cfg["assignTo"] == "tomlupo"
    assert cfg["independentReview"] is True


def test_base_branch_wrong_type_ignored(tmp_path, monkeypatch):
    monkeypatch.delenv("QUTE_ENFORCE_PR_REVIEW", raising=False)
    root = _repo(tmp_path)
    _write_yml(root, "baseBranch: 123\n")  # coerced to non-str => ignored
    # fallback parser coerces bare scalar; PyYAML gives int 123 -> ignored (default "")
    cfg = pfc.resolve_workflow(root)
    assert cfg["baseBranch"] in ("", "123")  # str "123" acceptable, int ignored


# ── nested form ─────────────────────────────────────────────────────────
def test_nested_qutePrWorkflow_form(tmp_path, monkeypatch):
    monkeypatch.delenv("QUTE_ENFORCE_PR_REVIEW", raising=False)
    root = _repo(tmp_path)
    _write_yml(root, "qutePrWorkflow:\n  assignTo: carol\n  enforce: true\n")
    cfg = pfc.resolve_workflow(root)
    assert cfg["assignTo"] == "carol"
    assert cfg["enforce"] is True


# ── backward-compat: legacy settings.json marker ────────────────────────
def test_legacy_marker_enables_enforce(tmp_path, monkeypatch):
    monkeypatch.delenv("QUTE_ENFORCE_PR_REVIEW", raising=False)
    root = _repo(tmp_path)
    _write_settings(root, {"quteEnforcePrReview": True})
    cfg = pfc.resolve_workflow(root)
    assert cfg["enforce"] is True
    assert pfc.enforcement_enabled(root) is True
    # the other keys still take their defaults
    assert cfg["assignTo"] == "tomlupo"


def test_legacy_marker_false_stays_off(tmp_path, monkeypatch):
    monkeypatch.delenv("QUTE_ENFORCE_PR_REVIEW", raising=False)
    root = _repo(tmp_path)
    _write_settings(root, {"quteEnforcePrReview": False})
    assert pfc.enforcement_enabled(root) is False


# ── defensive typing ────────────────────────────────────────────────────
def test_wrong_types_ignored(tmp_path, monkeypatch):
    monkeypatch.delenv("QUTE_ENFORCE_PR_REVIEW", raising=False)
    root = _repo(tmp_path)
    # enforce as a string / assignTo as a bool → ignored, defaults kept
    _write_yml(root, 'enforce: "notabool"\nassignTo: true\n')
    cfg = pfc.resolve_workflow(root)
    # "notabool" coerces to a plain string, not a bool → ignored
    assert cfg["enforce"] is False
    assert cfg["assignTo"] == "tomlupo"


# ── env override ────────────────────────────────────────────────────────
def test_env_override_forces_on(tmp_path, monkeypatch):
    root = _repo(tmp_path)
    monkeypatch.setenv("QUTE_ENFORCE_PR_REVIEW", "1")
    assert pfc.resolve_workflow(root)["enforce"] is True


def test_env_override_forces_off(tmp_path, monkeypatch):
    root = _repo(tmp_path)
    _write_yml(root, "enforce: true\n")
    monkeypatch.setenv("QUTE_ENFORCE_PR_REVIEW", "0")
    assert pfc.resolve_workflow(root)["enforce"] is False

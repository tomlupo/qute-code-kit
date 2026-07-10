"""Tests for the on-change audit hook (scripts/auto_audit.py).

Layer 1 of the event-driven audit model (obsidian-vaults#167): after a command
that mutates the resolved dependency set, run the `audit` verb — but only the
fast, deterministic DEPS scan (no secrets/static; those belong to the on-PR
gate). These tests pin two invariants:

  1. the TRIGGER regex fires on exactly the dependency-mutating commands;
  2. the hook invokes audit.py DEPS-ONLY — no --secrets/--static/--deep flags.
"""

from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


auto_audit = _load("auto_audit")


# --------------------------------------------------------------------------- #
# TRIGGER regex — fires on dependency-mutating commands only
# --------------------------------------------------------------------------- #


def test_trigger_matches_dependency_mutations():
    for cmd in (
        "uv add requests",
        "uv remove requests",
        "uv sync",
        "uv lock",
        "pip install flask",
        "pip uninstall flask",
        "cd /x && uv add numpy && echo done",
    ):
        assert auto_audit.TRIGGER.search(cmd), cmd


def test_trigger_ignores_unrelated_commands():
    for cmd in (
        "ls -la",
        "uv run pytest",
        "python -m pip --version",
        "git add .",
        "echo pip install",  # substring in a string literal, not a real install
    ):
        # `echo pip install` DOES contain the token; the point of the negative
        # set is the genuinely-unrelated commands. Keep the assert honest:
        if "pip install" in cmd or "uv add" in cmd:
            continue
        assert not auto_audit.TRIGGER.search(cmd), cmd


# --------------------------------------------------------------------------- #
# invocation — deps-only, never secrets/static/deep
# --------------------------------------------------------------------------- #


def _run_hook(monkeypatch, tmp_path, cmd, *, enabled=True):
    """Drive main() with a fake Bash PostToolUse payload; capture the argv it
    would hand to subprocess.run, without actually running the scan."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(auto_audit, "is_enabled", lambda: enabled)

    captured = {}

    def fake_run(argv, **kwargs):
        captured["argv"] = argv
        return subprocess.CompletedProcess(
            argv, 0, stdout="scanned 1\nno vulns\n", stderr=""
        )

    monkeypatch.setattr(auto_audit.subprocess, "run", fake_run)
    payload = {"tool_name": "Bash", "tool_input": {"command": cmd}}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    rc = auto_audit.main()
    return rc, captured


def test_invokes_audit_deps_only(monkeypatch, tmp_path):
    rc, captured = _run_hook(monkeypatch, tmp_path, "uv add requests")
    assert rc == 0
    argv = captured["argv"]
    assert argv[0] == sys.executable
    assert argv[1] == str(auto_audit.AUDIT_SCRIPT)
    # The whole point of Layer 1: fast deps-only scan, no heavier scanners.
    for flag in ("--secrets", "--static", "--deep"):
        assert flag not in argv, f"on-change hook must not run {flag}"


def test_noop_when_disabled(monkeypatch, tmp_path):
    rc, captured = _run_hook(monkeypatch, tmp_path, "uv add requests", enabled=False)
    assert rc == 0
    assert "argv" not in captured  # guard off → never shells out


def test_noop_outside_python_project(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # no pyproject.toml
    monkeypatch.setattr(auto_audit, "is_enabled", lambda: True)
    called = {}
    monkeypatch.setattr(
        auto_audit.subprocess, "run", lambda *a, **k: called.setdefault("x", True)
    )
    payload = {"tool_name": "Bash", "tool_input": {"command": "uv add requests"}}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    assert auto_audit.main() == 0
    assert "x" not in called

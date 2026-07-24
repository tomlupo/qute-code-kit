"""Tests for the Linear task backend (scripts/tasks/linear.py).

Focus is the `add` path emitting the "Dispatchable task" skeleton (TOM-216) so
agent-filed issues match the UI-templated ones. The module is stdlib-only and
its network I/O funnels through `gql`, so `cmd_add` is exercised by
monkeypatching `gql` to capture the mutation variables — no network.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

LINEAR = Path(__file__).resolve().parent.parent / "scripts" / "tasks" / "linear.py"


def _load():
    spec = importlib.util.spec_from_file_location("linear_backend", LINEAR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


linear = _load()

SKELETON_HEADINGS = ("What", "Repro", "Acceptance criteria", "Pointers", "Tier hint")


def test_dispatchable_body_emits_all_skeleton_headings():
    body = linear.dispatchable_body("Login 500 on empty password")
    for heading in SKELETON_HEADINGS:
        assert f"## {heading}" in body, f"missing skeleton heading: {heading}"
    # free text lands under What
    assert "Login 500 on empty password" in body


def test_dispatchable_body_skeletons_even_empty_input():
    body = linear.dispatchable_body("")
    for heading in SKELETON_HEADINGS:
        assert f"## {heading}" in body


def test_dispatchable_body_passthrough_when_already_skeletoned():
    already = "## What\n\nA thing.\n\n## Acceptance criteria\n\n- [ ] it works\n"
    assert linear.dispatchable_body(already) == already.strip()


def test_cmd_add_sends_skeleton_description(monkeypatch, capsys):
    captured = {}

    def fake_gql(query, variables=None):
        captured["query"] = query
        captured["variables"] = variables or {}
        if "teams(" in query:  # team_id lookup
            return {"teams": {"nodes": [{"id": "team-uuid", "key": "TOM"}]}}
        # issueCreate
        return {
            "issueCreate": {
                "success": True,
                "issue": {"identifier": "TOM-999", "url": "https://x/TOM-999"},
            }
        }

    monkeypatch.setattr(linear, "gql", fake_gql)
    monkeypatch.setattr(linear, "team_key", lambda: "TOM")

    linear.cmd_add("Fix the widget", "widget explodes on click")

    description = captured["variables"]["input"]["description"]
    for heading in SKELETON_HEADINGS:
        assert f"## {heading}" in description
    assert "widget explodes on click" in description
    assert "TOM-999" in capsys.readouterr().out


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))

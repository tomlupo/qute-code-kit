"""Tests for the weekly deep-sweep scheduler (scripts/deep_sweep.py).

The heavy work (scanning) lives in the audit verb and is tested in test_audit.py;
here we pin the SCHEDULER's own logic: live-capital-first ordering, aggregation,
exit-code roll-up, and the report render — with audit.run_audit monkeypatched so
no external scanners are needed.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


deep_sweep = _load("deep_sweep")
audit = deep_sweep.audit


# --------------------------------------------------------------------------- #
# ordering — live-capital first, then alphabetical
# --------------------------------------------------------------------------- #


def test_order_puts_priority_first_in_given_order():
    repos = [
        {"name": "zeta"},
        {"name": "dm-evo"},
        {"name": "alpha"},
        {"name": "quantbox-live"},
    ]
    ordered = [
        r["name"] for r in deep_sweep.order_repos(repos, ["quantbox-live", "dm-evo"])
    ]
    assert ordered == ["quantbox-live", "dm-evo", "alpha", "zeta"]


def test_order_no_priority_is_alphabetical():
    repos = [{"name": "b"}, {"name": "a"}, {"name": "c"}]
    assert [r["name"] for r in deep_sweep.order_repos(repos, [])] == ["a", "b", "c"]


# --------------------------------------------------------------------------- #
# sweep roll-up — exit codes and aggregation
# --------------------------------------------------------------------------- #


def _fake_run_audit(monkeypatch, mapping):
    """mapping: repo-name → (counts_dict, exit_code)."""

    def fake(root, *, deep=False, **kw):
        name = Path(root).name
        counts, code = mapping[name]
        # minimal scanners dict compatible with _public_scanner
        return {}, counts, code

    monkeypatch.setattr(audit, "run_audit", fake)


def _counts(total=0, **sev):
    c = audit._empty_counts()
    c.update(sev)
    c["total"] = total
    return c


def _mkrepos(tmp_path, *names):
    """Create git repos (dir + .git) so discover_local picks them up."""
    for n in names:
        (tmp_path / n / ".git").mkdir(parents=True)


def test_sweep_clean(monkeypatch, tmp_path):
    _mkrepos(tmp_path, "quantbox-live", "dm-evo")
    _fake_run_audit(
        monkeypatch,
        {"quantbox-live": (_counts(0), 0), "dm-evo": (_counts(0), 0)},
    )
    summary = deep_sweep.run_sweep(
        config_path=None,
        cli_roots=[str(tmp_path)],
        only_host=None,
        priority=["quantbox-live", "dm-evo"],
        limit=None,
    )
    assert summary["exit_code"] == 0
    assert summary["swept"] == 2
    assert [r["name"] for r in summary["repos"]] == ["quantbox-live", "dm-evo"]


def test_sweep_findings_roll_up_to_exit_1(monkeypatch, tmp_path):
    _mkrepos(tmp_path, "quantbox-live", "dm-evo")
    _fake_run_audit(
        monkeypatch,
        {
            "quantbox-live": (_counts(0), 0),
            "dm-evo": (_counts(2, high=2), 1),
        },
    )
    summary = deep_sweep.run_sweep(
        config_path=None,
        cli_roots=[str(tmp_path)],
        only_host=None,
        priority=["quantbox-live", "dm-evo"],
        limit=None,
    )
    assert summary["exit_code"] == 1
    assert summary["findings_total"] == 2


def test_sweep_all_unscannable_is_exit_2(monkeypatch, tmp_path):
    _mkrepos(tmp_path, "dead")
    _fake_run_audit(monkeypatch, {"dead": (_counts(0), 2)})
    summary = deep_sweep.run_sweep(
        config_path=None,
        cli_roots=[str(tmp_path)],
        only_host=None,
        priority=[],
        limit=None,
    )
    assert summary["exit_code"] == 2


def test_limit_caps_repos(monkeypatch, tmp_path):
    _mkrepos(tmp_path, "a", "b", "c")
    _fake_run_audit(
        monkeypatch,
        {"a": (_counts(0), 0), "b": (_counts(0), 0), "c": (_counts(0), 0)},
    )
    summary = deep_sweep.run_sweep(
        config_path=None,
        cli_roots=[str(tmp_path)],
        only_host=None,
        priority=None,
        limit=2,
    )
    assert summary["swept"] == 2


def test_render_report_is_markdown_table():
    summary = {
        "swept": 1,
        "findings_total": 3,
        "priority": ["quantbox-live"],
        "repos": [
            {
                "name": "quantbox-live",
                "host": "core",
                "exit_code": 1,
                "counts": _counts(3, high=1, medium=2),
            }
        ],
    }
    out = deep_sweep.render_report(summary, "2026-07-10")
    assert "Weekly deep audit sweep — 2026-07-10" in out
    assert "| quantbox-live | core |" in out
    assert "findings" in out

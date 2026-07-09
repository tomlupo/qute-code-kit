"""Tests for the multi-scanner audit verb (scripts/audit.py).

Scanners shell out to external binaries (pip-audit/gitleaks/semgrep) which we do
NOT assume are installed in CI. Tests therefore:
  - exercise the pure aggregation / exit-code / JSON-contract logic directly;
  - drive the graceful-degrade path by monkeypatching `shutil.which` to None;
  - drive the deps/secrets/static parsers by monkeypatching `subprocess.run`.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


audit = _load("audit")


# --------------------------------------------------------------------------- #
# aggregation + exit-code logic
# --------------------------------------------------------------------------- #


def _scan(available=True, ran=True, ok=True, sev=None):
    s = {c: 0 for c in audit.SEVERITIES}
    if sev:
        s.update(sev)
    findings = sum(s.values())
    return audit._scanner_result(
        available=available, ran=ran, ok=ok, findings=findings, severity=s
    )


def test_aggregate_sums_severity_across_scanners():
    scanners = {
        "deps": _scan(sev={"high": 2}),
        "secrets": _scan(sev={"critical": 1}),
        "static": _scan(sev={"medium": 3, "low": 1}),
    }
    counts = audit.aggregate(scanners)
    assert counts == {"critical": 1, "high": 2, "medium": 3, "low": 1, "total": 7}


def test_exit_zero_when_ran_and_clean():
    scanners = {"deps": _scan()}
    assert audit.compute_exit(scanners, 0) == 0


def test_exit_one_when_findings():
    scanners = {"deps": _scan(sev={"high": 1})}
    assert audit.compute_exit(scanners, 1) == 1


def test_exit_two_when_nothing_ran():
    scanners = {"static": audit._degraded("semgrep not on PATH")}
    assert audit.compute_exit(scanners, 0) == 2


def test_exit_two_when_a_scanner_errored_even_if_another_ran_clean():
    # hygiene ran clean, but semgrep errored operationally → not a clean pass.
    scanners = {
        "hygiene": _scan(),  # ran, ok=True, no findings
        "static": audit._scanner_result(
            available=True, ran=False, ok=False, reason="semgrep exit 2"
        ),
    }
    assert audit.compute_exit(scanners, 0) == 2


def test_exit_one_takes_priority_over_scanner_error():
    scanners = {
        "deps": _scan(sev={"high": 1}),
        "static": audit._scanner_result(
            available=True, ran=False, ok=False, reason="semgrep exit 2"
        ),
    }
    assert audit.compute_exit(scanners, 1) == 1


def test_degraded_binary_absent_is_still_clean_exit():
    # ok is None (binary absent) is graceful degradation, not an error.
    scanners = {
        "hygiene": _scan(),
        "secrets": audit._degraded("gitleaks not on PATH"),
    }
    assert audit.compute_exit(scanners, 0) == 0


# --------------------------------------------------------------------------- #
# graceful degradation — binary absent
# --------------------------------------------------------------------------- #


def test_secrets_degrades_without_gitleaks(monkeypatch, tmp_path):
    monkeypatch.setattr(audit.shutil, "which", lambda _: None)
    res = audit.run_secrets(tmp_path)
    assert res["available"] is False and res["ran"] is False
    assert "gitleaks" in res["reason"]


def test_static_degrades_without_semgrep(monkeypatch, tmp_path):
    monkeypatch.setattr(audit.shutil, "which", lambda _: None)
    res = audit.run_static(tmp_path)
    assert res["available"] is False and res["ran"] is False
    assert "semgrep" in res["reason"]


def test_deep_degrades_scanners_but_hygiene_still_runs(monkeypatch, tmp_path):
    # No pyproject, no external scanners installed. secrets/static degrade;
    # hygiene is pure-python so it still runs → the audit is not fatal (exit 0).
    monkeypatch.setattr(audit.shutil, "which", lambda _: None)
    scanners, counts, exit_code = audit.run_audit(tmp_path, deps=True, deep=True)
    assert scanners["secrets"]["available"] is False
    assert scanners["static"]["available"] is False
    assert scanners["hygiene"]["ran"] is True
    assert exit_code == 0  # nothing found, but something ran


def test_secrets_only_no_binary_exits_two(monkeypatch, tmp_path):
    # --secrets --no-deps with gitleaks absent → no scanner runs → exit 2.
    monkeypatch.setattr(audit.shutil, "which", lambda _: None)
    scanners, counts, exit_code = audit.run_audit(tmp_path, deps=False, secrets=True)
    assert exit_code == 2


# --------------------------------------------------------------------------- #
# deps parser
# --------------------------------------------------------------------------- #


def test_run_deps_parses_vulns(monkeypatch, tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    monkeypatch.setattr(audit.shutil, "which", lambda _: "/usr/bin/uv")
    payload = {
        "dependencies": [
            {"name": "safe", "version": "1.0", "vulns": []},
            {
                "name": "bad",
                "version": "2.0",
                "vulns": [
                    {"id": "CVE-1", "aliases": ["GHSA-x"], "fix_versions": ["2.1"]}
                ],
            },
        ]
    }

    def fake_run(*a, **k):
        return subprocess.CompletedProcess(a, 1, json.dumps(payload), "")

    monkeypatch.setattr(audit.subprocess, "run", fake_run)
    res = audit.run_deps(tmp_path)
    assert res["ran"] and res["findings"] == 1
    assert res["severity"]["high"] == 1
    assert res["details"][0]["package"] == "bad"


def test_run_deps_no_pyproject_is_not_fatal(tmp_path):
    res = audit.run_deps(tmp_path)
    assert res["available"] is True and res["ran"] is False
    assert "pyproject" in res["reason"]


# --------------------------------------------------------------------------- #
# secrets + static parsers (mocked binaries)
# --------------------------------------------------------------------------- #


def test_run_secrets_counts_findings_critical(monkeypatch, tmp_path):
    monkeypatch.setattr(audit.shutil, "which", lambda _: "/usr/bin/gitleaks")
    leaks = [{"RuleID": "aws-key", "File": "a.py", "StartLine": 3}]

    def fake_run(cmd, *a, **k):
        # gitleaks writes its report to the --report-path file
        idx = cmd.index("--report-path")
        Path(cmd[idx + 1]).write_text(json.dumps(leaks))
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(audit.subprocess, "run", fake_run)
    res = audit.run_secrets(tmp_path)
    assert res["ran"] and res["findings"] == 1
    assert res["severity"]["critical"] == 1


def test_run_secrets_nonzero_exit_is_failure_not_clean(monkeypatch, tmp_path):
    monkeypatch.setattr(audit.shutil, "which", lambda _: "/usr/bin/gitleaks")

    def fake_run(cmd, *a, **k):
        # operational failure: non-zero, no report written
        return subprocess.CompletedProcess(cmd, 2, "", "fatal: bad flag")

    monkeypatch.setattr(audit.subprocess, "run", fake_run)
    res = audit.run_secrets(tmp_path)
    assert res["ran"] is False and res["ok"] is False
    assert "gitleaks exit 2" in res["reason"]


def test_run_static_fatal_exit_is_failure_not_clean(monkeypatch, tmp_path):
    monkeypatch.setattr(audit.shutil, "which", lambda _: "/usr/bin/semgrep")

    def fake_run(cmd, *a, **k):
        # exit >=2 is a semgrep fatal error, even with partial/empty JSON
        return subprocess.CompletedProcess(cmd, 2, "{}", "config error")

    monkeypatch.setattr(audit.subprocess, "run", fake_run)
    res = audit.run_static(tmp_path)
    assert res["ran"] is False and res["ok"] is False
    assert "semgrep exit 2" in res["reason"]


def test_run_static_maps_semgrep_severity(monkeypatch, tmp_path):
    monkeypatch.setattr(audit.shutil, "which", lambda _: "/usr/bin/semgrep")
    out = {
        "results": [
            {
                "check_id": "r1",
                "path": "a.py",
                "start": {"line": 1},
                "extra": {"severity": "ERROR"},
            },
            {
                "check_id": "r2",
                "path": "b.py",
                "start": {"line": 2},
                "extra": {"severity": "WARNING"},
            },
            {
                "check_id": "r3",
                "path": "c.py",
                "start": {"line": 3},
                "extra": {"severity": "INFO"},
            },
        ]
    }

    def fake_run(cmd, *a, **k):
        return subprocess.CompletedProcess(cmd, 1, json.dumps(out), "")

    monkeypatch.setattr(audit.subprocess, "run", fake_run)
    res = audit.run_static(tmp_path)
    assert res["findings"] == 3
    assert res["severity"] == {"critical": 0, "high": 1, "medium": 1, "low": 1}


# --------------------------------------------------------------------------- #
# hygiene (pure python — no binary)
# --------------------------------------------------------------------------- #


def test_hygiene_flags_sensitive_files(tmp_path):
    (tmp_path / ".env").write_text("SECRET=1")
    (tmp_path / "server.pem").write_text("-----BEGIN KEY-----")
    (tmp_path / "ok.py").write_text("print(1)")
    res = audit.run_hygiene(tmp_path)
    files = {d["file"] for d in res["details"]}
    assert files == {".env", "server.pem"}
    # untracked (no git) → high, not critical
    assert res["severity"]["high"] == 2
    assert res["severity"]["critical"] == 0


def test_hygiene_respects_file_cap(monkeypatch, tmp_path):
    (tmp_path / "a.txt").write_text("x")
    (tmp_path / ".env").write_text("s")
    monkeypatch.setattr(audit, "_HYGIENE_FILE_CAP", 1)
    res = audit.run_hygiene(tmp_path)
    # cap hit after the first file → the .env may not be reached, but it must
    # not crash and must still return a well-formed result
    assert res["ran"] is True and res["available"] is True


def test_bad_path_returns_structured_exit_two(tmp_path, capsys):
    missing = tmp_path / "nope"
    code = audit.main(["--json", "--path", str(missing)])
    assert code == 2
    out = [ln for ln in capsys.readouterr().out.splitlines() if ln.strip()]
    obj = json.loads(out[-1])
    assert obj["verb"] == "audit" and obj["exit_code"] == 2 and obj["ok"] is False


def test_hygiene_skips_vendored_dirs(tmp_path):
    vendored = tmp_path / "node_modules" / "pkg"
    vendored.mkdir(parents=True)
    (vendored / ".env").write_text("x")
    res = audit.run_hygiene(tmp_path)
    assert res["findings"] == 0


# --------------------------------------------------------------------------- #
# JSON contract (#161)
# --------------------------------------------------------------------------- #


def test_build_json_shape():
    scanners = {"deps": _scan(sev={"high": 1})}
    counts = audit.aggregate(scanners)
    obj = audit.build_json(scanners, counts, 1, "deps")
    assert obj["verb"] == "audit"
    assert obj["ok"] is True
    assert obj["exit_code"] == 1
    assert obj["findings"]["high"] == 1
    assert obj["findings"]["total"] == 1
    # per-scanner status trimmed of verbose details
    assert set(obj["scanners"]["deps"]) == {
        "available",
        "ran",
        "ok",
        "findings",
        "severity",
        "reason",
    }
    assert "details" not in obj["scanners"]["deps"]


def test_build_json_ok_false_when_exit_two():
    scanners = {"static": audit._degraded("no semgrep")}
    obj = audit.build_json(scanners, audit.aggregate(scanners), 2, "deep")
    assert obj["ok"] is False


def test_json_mode_emits_single_stdout_line(monkeypatch, tmp_path, capsys):
    # deps-only on an empty dir with no uv → deps does not run → exit 2.
    monkeypatch.setattr(audit.shutil, "which", lambda _: None)
    monkeypatch.chdir(tmp_path)
    code = audit.main(["--json"])
    captured = capsys.readouterr()
    # exactly one line on stdout, and it parses as the contract object
    stdout_lines = [ln for ln in captured.out.splitlines() if ln.strip()]
    assert len(stdout_lines) == 1
    obj = json.loads(stdout_lines[0])
    assert obj["verb"] == "audit" and obj["exit_code"] == code
    # human summary went to stderr, not stdout
    assert "audit summary" in captured.err


def test_default_mode_is_deps_only(monkeypatch, tmp_path):
    monkeypatch.setattr(audit.shutil, "which", lambda _: None)
    scanners, counts, code = audit.run_audit(tmp_path)
    assert set(scanners) == {"deps"}


def test_mode_label():
    assert audit._mode_label(True, False, False) == "deep"
    assert audit._mode_label(True, False, False, deps=False) == "deep-nodeps"
    assert audit._mode_label(False, False, False) == "deps"
    assert audit._mode_label(False, True, True) == "deps+secrets+static"
    # --no-deps must not claim deps ran
    assert audit._mode_label(False, True, False, deps=False) == "secrets"
    assert audit._mode_label(False, False, False, deps=False) == "none"

"""Tests for repo_inventory — cross-host git-repo enumeration.

Local discovery is exercised against a temp tree; remote (ssh) discovery is
exercised via a mocked subprocess so no network is required. Config precedence
(CLI > env > file > cwd default) is covered.
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


inv = _load("repo_inventory")


def _make_repo(base: Path, name: str) -> Path:
    repo = base / name
    (repo / ".git").mkdir(parents=True)
    return repo


def test_discover_local_finds_repos(tmp_path):
    _make_repo(tmp_path, "alpha")
    _make_repo(tmp_path / "nested", "beta")
    (tmp_path / "not-a-repo").mkdir()
    repos = inv.discover_local([str(tmp_path)])
    names = {r["name"] for r in repos}
    assert names == {"alpha", "beta"}


def test_discover_local_does_not_descend_into_repo(tmp_path):
    repo = _make_repo(tmp_path, "alpha")
    # a .git-looking subdir inside a repo must not be reported separately
    (repo / "vendor" / "sub" / ".git").mkdir(parents=True)
    repos = inv.discover_local([str(tmp_path)])
    assert [r["name"] for r in repos] == ["alpha"]


def test_discover_local_respects_max_depth(tmp_path):
    deep = tmp_path / "a" / "b" / "c" / "d"
    _make_repo(deep, "toodeep")
    repos = inv.discover_local([str(tmp_path)], max_depth=2)
    assert repos == []


def test_discover_local_dedups(tmp_path):
    _make_repo(tmp_path, "alpha")
    repos = inv.discover_local([str(tmp_path), str(tmp_path)])
    assert len(repos) == 1


def test_cli_roots_override_config(tmp_path, monkeypatch):
    _make_repo(tmp_path, "alpha")
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({"hosts": {"core": {"roots": ["/nonexistent"]}}}))
    monkeypatch.delenv("QUTE_AUDIT_ROOTS", raising=False)
    out = inv.build_inventory(cli_roots=[str(tmp_path)], config_path=cfg)
    assert out["count"] == 1
    assert "local" in out["hosts"]


def test_env_roots_used_when_no_cli(tmp_path, monkeypatch):
    _make_repo(tmp_path, "alpha")
    monkeypatch.setenv("QUTE_AUDIT_ROOTS", str(tmp_path))
    out = inv.build_inventory(config_path=tmp_path / "missing.json")
    assert out["count"] == 1


def test_default_is_cwd_when_no_config(tmp_path, monkeypatch):
    _make_repo(tmp_path, "alpha")
    monkeypatch.delenv("QUTE_AUDIT_ROOTS", raising=False)
    monkeypatch.chdir(tmp_path)
    out = inv.build_inventory(config_path=tmp_path / "missing.json")
    assert out["count"] == 1


def test_multi_host_config_local(tmp_path, monkeypatch):
    core = tmp_path / "core"
    forge = tmp_path / "forge"
    _make_repo(core, "core-repo")
    _make_repo(forge, "forge-repo")
    cfg = tmp_path / "cfg.json"
    cfg.write_text(
        json.dumps(
            {
                "hosts": {
                    "core": {"roots": [str(core)]},
                    "forge": {"roots": [str(forge)]},
                }
            }
        )
    )
    monkeypatch.delenv("QUTE_AUDIT_ROOTS", raising=False)
    out = inv.build_inventory(config_path=cfg)
    assert out["count"] == 2
    assert {r["host"] for r in out["repos"]} == {"core", "forge"}


def test_only_host_filter(tmp_path, monkeypatch):
    core = tmp_path / "core"
    _make_repo(core, "core-repo")
    cfg = tmp_path / "cfg.json"
    cfg.write_text(
        json.dumps(
            {
                "hosts": {
                    "core": {"roots": [str(core)]},
                    "forge": {"roots": ["/x"], "ssh": "f"},
                }
            }
        )
    )
    monkeypatch.delenv("QUTE_AUDIT_ROOTS", raising=False)
    out = inv.build_inventory(only_host="core", config_path=cfg)
    assert set(out["hosts"]) == {"core"}


def test_remote_host_parsed(tmp_path, monkeypatch):
    cfg = tmp_path / "cfg.json"
    cfg.write_text(
        json.dumps({"hosts": {"forge": {"roots": ["/srv"], "ssh": "forge"}}})
    )
    monkeypatch.delenv("QUTE_AUDIT_ROOTS", raising=False)

    def fake_run(cmd, *a, **k):
        assert cmd[0] == "ssh"
        return subprocess.CompletedProcess(cmd, 0, "/srv/one/.git\n/srv/two/.git\n", "")

    monkeypatch.setattr(inv.subprocess, "run", fake_run)
    out = inv.build_inventory(config_path=cfg)
    assert out["count"] == 2
    assert {r["name"] for r in out["repos"]} == {"one", "two"}


def test_remote_host_degrades_gracefully(tmp_path, monkeypatch):
    cfg = tmp_path / "cfg.json"
    cfg.write_text(
        json.dumps({"hosts": {"forge": {"roots": ["/srv"], "ssh": "forge"}}})
    )
    monkeypatch.delenv("QUTE_AUDIT_ROOTS", raising=False)

    def fake_run(cmd, *a, **k):
        return subprocess.CompletedProcess(cmd, 255, "", "ssh: connect: refused")

    monkeypatch.setattr(inv.subprocess, "run", fake_run)
    out = inv.build_inventory(config_path=cfg)
    assert out["count"] == 0
    assert out["hosts"]["forge"]["error"]  # reported, not crashed


def test_remote_host_empty_roots_refused(tmp_path, monkeypatch):
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({"hosts": {"forge": {"roots": [], "ssh": "forge"}}}))
    monkeypatch.delenv("QUTE_AUDIT_ROOTS", raising=False)

    def boom(*a, **k):  # ssh must never be invoked with no roots
        raise AssertionError("ssh should not run with empty roots")

    monkeypatch.setattr(inv.subprocess, "run", boom)
    out = inv.build_inventory(config_path=cfg)
    assert out["count"] == 0
    assert "no roots" in out["hosts"]["forge"]["error"]


def test_json_cli(tmp_path, monkeypatch, capsys):
    _make_repo(tmp_path, "alpha")
    monkeypatch.delenv("QUTE_AUDIT_ROOTS", raising=False)
    code = inv.main(["--roots", str(tmp_path), "--json"])
    assert code == 0
    obj = json.loads(capsys.readouterr().out.strip())
    assert obj["count"] == 1

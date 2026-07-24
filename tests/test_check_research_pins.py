"""Unit tests for the canonical research gate (templates/research/check_research_pins.py).

Exercises the ADR-0007 provenance-on-conclude branches with tmp-repo fixtures:
a concluded+pinned line missing hashes FAILS; concluded+historical with a repro_note
PASSES; an active line is exempt; snapshot-frozen requires the snapshot on disk.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

GATE_PATH = (
    Path(__file__).resolve().parents[1]
    / "templates"
    / "research"
    / "check_research_pins.py"
)

_spec = importlib.util.spec_from_file_location("check_research_pins", GATE_PATH)
assert _spec and _spec.loader
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)

VALID_SHA256 = "a" * 64
VALID_SHA40 = "b" * 40

BASE_CONFIG = """\
research_root: research
pin_targets: []
structural_rules:
  forbidden_dirs: []
  required_per_research: []
  require_sha_pins: false
"""


def _make_repo(tmp_path: Path) -> Path:
    (tmp_path / ".research-config.yaml").write_text(BASE_CONFIG)
    (tmp_path / "research").mkdir()
    return tmp_path


def _line(tmp_path: Path, name: str, readme: str) -> Path:
    d = tmp_path / "research" / name
    d.mkdir(parents=True)
    (d / "README.md").write_text(readme)
    return d


def _run(tmp_path: Path) -> list[str]:
    code, errors = gate.check(tmp_path)
    assert code == (1 if errors else 0)
    return errors


def test_active_line_is_exempt(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    _line(tmp_path, "act", "---\nline: act\nstatus: active\n---\n# act\n")
    assert _run(tmp_path) == []


def test_concluded_pinned_missing_hashes_fails(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    d = _line(
        tmp_path,
        "pin",
        "---\nline: pin\nstatus: concluded\nreproducibility_class: pinned\n"
        f"provenance:\n  engine_commit: {VALID_SHA40}\n  ran_at: 2026-07-24\n---\n# pin\n",
    )
    (d / "data_inputs.yaml").write_text(
        "engine: dm-evo\ninputs:\n  - path: config/reference/x.csv\n    sha256: TBD\n"
    )
    errors = _run(tmp_path)
    assert any("no valid sha256" in e for e in errors), errors


def test_concluded_pinned_full_provenance_passes(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    d = _line(
        tmp_path,
        "pin",
        "---\nline: pin\nstatus: concluded\nreproducibility_class: pinned\n"
        f"provenance:\n  engine_commit: {VALID_SHA40}\n  ran_at: 2026-07-24\n---\n# pin\n",
    )
    (d / "data_inputs.yaml").write_text(
        f"engine: dm-evo\ninputs:\n  - path: config/reference/x.csv\n    sha256: {VALID_SHA256}\n"
    )
    assert _run(tmp_path) == []


def test_concluded_pinned_tbd_provenance_fails(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    d = _line(
        tmp_path,
        "pin",
        "---\nline: pin\nstatus: concluded\nreproducibility_class: pinned\n"
        "provenance:\n  engine_commit: TBD\n  ran_at: TBD\n---\n# pin\n",
    )
    (d / "data_inputs.yaml").write_text(
        f"engine: dm-evo\ninputs:\n  - path: config/reference/x.csv\n    sha256: {VALID_SHA256}\n"
    )
    errors = _run(tmp_path)
    assert any("engine_commit" in e for e in errors), errors


def test_concluded_historical_with_note_passes(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    _line(
        tmp_path,
        "hist",
        "---\nline: hist\nstatus: concluded\nreproducibility_class: historical\n"
        "repro_note: inputs predate the contract and are unrecoverable\n---\n# hist\n",
    )
    assert _run(tmp_path) == []


def test_concluded_historical_without_note_fails(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    _line(
        tmp_path,
        "hist",
        "---\nline: hist\nstatus: concluded\nreproducibility_class: historical\n"
        "repro_note: null\n---\n# hist\n",
    )
    errors = _run(tmp_path)
    assert any("repro_note" in e for e in errors), errors


def test_concluded_live_data_with_note_passes(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    _line(
        tmp_path,
        "live",
        "---\nline: live\nstatus: concluded\nreproducibility_class: live-data\n"
        "repro_note: reads a live external API that cannot be pinned\n---\n# live\n",
    )
    assert _run(tmp_path) == []


def test_concluded_without_class_fails(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    _line(
        tmp_path, "noclass", "---\nline: noclass\nstatus: concluded\n---\n# noclass\n"
    )
    errors = _run(tmp_path)
    assert any("reproducibility_class is not set" in e for e in errors), errors


def test_concluded_invalid_class_fails(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    _line(
        tmp_path,
        "bad",
        "---\nline: bad\nstatus: concluded\nreproducibility_class: whatever\n---\n# bad\n",
    )
    errors = _run(tmp_path)
    assert any("invalid reproducibility_class" in e for e in errors), errors


def test_snapshot_frozen_missing_file_fails(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    d = _line(
        tmp_path,
        "snap",
        "---\nline: snap\nstatus: concluded\nreproducibility_class: snapshot-frozen\n---\n# snap\n",
    )
    (d / "data_inputs.yaml").write_text(
        f"engine: dm-evo\ninputs:\n  - path: data/frozen.csv\n    sha256: {VALID_SHA256}\n"
    )
    errors = _run(tmp_path)
    assert any("not present under the line" in e for e in errors), errors


def test_snapshot_frozen_with_file_passes(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    d = _line(
        tmp_path,
        "snap",
        "---\nline: snap\nstatus: concluded\nreproducibility_class: snapshot-frozen\n---\n# snap\n",
    )
    (d / "data").mkdir()
    (d / "data" / "frozen.csv").write_text("col\n1\n")
    (d / "data_inputs.yaml").write_text(
        f"engine: dm-evo\ninputs:\n  - path: data/frozen.csv\n    sha256: {VALID_SHA256}\n"
    )
    assert _run(tmp_path) == []


def test_template_dir_is_skipped(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    # A _template with a concluded-looking README must never be gated.
    _line(
        tmp_path,
        "_template",
        "---\nline: '{{NAME}}'\nstatus: concluded\n---\n# template\n",
    )
    assert _run(tmp_path) == []


def test_missing_config_fails(tmp_path: Path) -> None:
    code, errors = gate.check(tmp_path)
    assert code == 1
    assert any("not found" in e for e in errors)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))

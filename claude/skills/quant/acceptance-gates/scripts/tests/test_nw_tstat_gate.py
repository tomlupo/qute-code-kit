"""CLI tests for the Newey-West (HAC) t-stat + min-OOS-window gate.

The HAC math itself now lives in the framework (``quantbox.analysis.hac``) and is
regression-tested there (``quantbox/tests/test_analysis_hac.py`` +
``test_hac_parity.py``). This suite covers only what the thin CLI owns: loading,
the fail-loud non-finite policy surfaced end-to-end, the ``--oos-periods`` cap,
and the two-part gate decision. Both codex-found holes stay pinned as CLI
regressions:

1. A file with 200 legit + 500 corrupt (NaN) rows must NOT quietly pass
   --min-oos-periods on the surviving 200 — it must refuse outright.
2. --oos-periods must never be trusted beyond the actual finite return count.

Run: pytest scripts/tests/test_nw_tstat_gate.py -q
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPTS = Path(__file__).resolve().parent.parent

# nw-tstat-gate.py is hyphenated (CLI convention) -> load it explicitly. Importing
# it exercises the thin CLI's `from quantbox.analysis import newey_west_tstat`.
_SPEC = importlib.util.spec_from_file_location("nw_tstat_gate_cli", SCRIPTS / "nw-tstat-gate.py")
nw_gate_cli = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(nw_gate_cli)


# ---------------------------------------------------------------------------
# HOLE 1: silent NaN/Inf drop before counting n_obs — must FAIL LOUDLY (CLI)
# ---------------------------------------------------------------------------


def test_cli_corrupt_file_raises_instead_of_silently_shrinking_sample(tmp_path):
    """The exact codex scenario: 200 legit + 500 NaN rows must NOT quietly report
    n_obs=200 and pass on the surviving subset — it must refuse outright."""
    rng = np.random.default_rng(5)
    good = rng.normal(0.002, 0.01, 200)
    corrupt = np.full(500, np.nan)
    series = np.concatenate([good, corrupt])
    f = tmp_path / "returns.csv"
    pd.Series(series, name="return").to_csv(f, index=False)

    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "nw-tstat-gate.py"),
            "--returns",
            str(f),
            "--min-oos-periods",
            "150",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    err = json.loads(proc.stderr)
    assert "NaN/Inf" in err["error"]


def test_cli_corrupt_file_with_explicit_opt_out_reports_the_drop(tmp_path):
    rng = np.random.default_rng(5)
    good = rng.normal(0.002, 0.01, 200)
    corrupt = np.full(50, np.nan)
    series = np.concatenate([good, corrupt])
    f = tmp_path / "returns.csv"
    pd.Series(series, name="return").to_csv(f, index=False)

    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "nw-tstat-gate.py"),
            "--returns",
            str(f),
            "--min-oos-periods",
            "150",
            "--allow-nonfinite-drop",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["n_obs_raw"] == 250
    assert out["n_nonfinite_dropped"] == 50
    assert out["n_obs"] == 200


# ---------------------------------------------------------------------------
# HOLE 2: --oos-periods trusted beyond the actual finite return count
# ---------------------------------------------------------------------------


def test_cli_oos_periods_exceeding_finite_count_is_rejected(tmp_path):
    """Claiming a 3-year OOS window on 30 real observations must raise, not be
    recorded as a legitimate longer window."""
    rng = np.random.default_rng(9)
    r = rng.normal(0.001, 0.01, 30)
    f = tmp_path / "returns.csv"
    pd.Series(r, name="return").to_csv(f, index=False)

    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "nw-tstat-gate.py"),
            "--returns",
            str(f),
            "--oos-periods",
            "756",  # ~3y of daily data — far more than the 30 real obs
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    err = json.loads(proc.stderr)
    assert "exceeds" in err["error"]


def test_cli_oos_periods_within_finite_count_is_accepted(tmp_path):
    """A narrower --oos-periods claim (e.g. IS+OOS mixed file, only count the OOS
    tail) is a legitimate use and must be honoured exactly."""
    rng = np.random.default_rng(9)
    r = rng.normal(0.001, 0.01, 400)
    f = tmp_path / "returns.csv"
    pd.Series(r, name="return").to_csv(f, index=False)

    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "nw-tstat-gate.py"),
            "--returns",
            str(f),
            "--oos-periods",
            "252",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["oos_window_periods"] == 252
    assert out["n_obs"] == 400  # the t-stat itself still uses all finite obs


def test_cli_negative_min_oos_periods_rejected(tmp_path):
    rng = np.random.default_rng(2)
    r = rng.normal(0.001, 0.01, 100)
    f = tmp_path / "returns.csv"
    pd.Series(r, name="return").to_csv(f, index=False)

    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "nw-tstat-gate.py"),
            "--returns",
            str(f),
            "--min-oos-periods",
            "-5",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0


# ---------------------------------------------------------------------------
# End-to-end gate behaviour
# ---------------------------------------------------------------------------


def test_cli_gate_pass_requires_both_nw_and_window_checks(tmp_path):
    rng = np.random.default_rng(13)
    r = rng.normal(0.003, 0.01, 400)  # strong positive drift, plenty of data
    f = tmp_path / "returns.csv"
    pd.Series(r, name="return").to_csv(f, index=False)

    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "nw-tstat-gate.py"),
            "--returns",
            str(f),
            "--t-threshold",
            "2.0",
            "--min-oos-periods",
            "252",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["gate_pass"] == (out["nw_pass"] and out["oos_window_pass"])


def test_cli_short_window_fails_gate_even_with_strong_tstat(tmp_path):
    rng = np.random.default_rng(13)
    r = rng.normal(0.01, 0.01, 60)  # strong drift, but short window
    f = tmp_path / "returns.csv"
    pd.Series(r, name="return").to_csv(f, index=False)

    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "nw-tstat-gate.py"),
            "--returns",
            str(f),
            "--t-threshold",
            "1.5",
            "--min-oos-periods",
            "252",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["oos_window_pass"] is False
    assert out["gate_pass"] is False

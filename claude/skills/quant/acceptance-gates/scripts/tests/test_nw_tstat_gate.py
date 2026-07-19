"""Tests for the Newey-West (HAC) t-stat + min-OOS-window gate.

Previously MISSING entirely (2026-07-19 acceptance-gates skill split) — codex's
adversarial review of the wave-3 draft found two holes in nw-tstat-gate.py that
let a corrupt/degenerate return series slip a robustness gate:

1. The loader silently dropped NaN/Inf returns via a boolean mask BEFORE n_obs
   was counted, so a file with 200 legit + 500 corrupt rows could quietly pass
   --min-oos-periods on the surviving 200 — a real data-quality failure hiding
   behind a green gate.
2. --oos-periods was trusted even when it EXCEEDED the actual finite return
   count, letting a caller claim a longer OOS window than the data supports.

Both are pinned as regressions here, alongside the existing math coverage.

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
import pytest

SCRIPTS = Path(__file__).resolve().parent.parent

# nw-tstat-gate.py is hyphenated (CLI convention) -> load it explicitly.
_SPEC = importlib.util.spec_from_file_location(
    "nw_tstat_gate_cli", SCRIPTS / "nw-tstat-gate.py"
)
nw_gate_cli = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(nw_gate_cli)


# ---------------------------------------------------------------------------
# nw_tstat() — the shared math (pure function, no I/O)
# ---------------------------------------------------------------------------


def test_nw_tstat_iid_normal_matches_naive_se_at_zero_lags():
    """With lags=0, the Newey-West SE collapses to the plain iid SE of the mean."""
    rng = np.random.default_rng(3)
    r = rng.normal(0.001, 0.02, 2000)
    out = nw_gate_cli.nw_tstat(r, lags=0)
    naive_se = r.std(ddof=0) / np.sqrt(len(r))
    assert out["nw_se"] == pytest.approx(naive_se, abs=1e-8)
    assert out["mean_return"] == pytest.approx(float(r.mean()), abs=1e-8)


def test_nw_tstat_autocorrelated_returns_inflates_se_vs_naive():
    """Positively autocorrelated returns must widen the NW SE vs the naive iid SE —
    that inflation is the entire point of using HAC over a plain t-test."""
    rng = np.random.default_rng(11)
    eps = rng.normal(0, 1, 3000)
    ar = np.zeros(3000)
    for t in range(1, 3000):
        ar[t] = 0.6 * ar[t - 1] + eps[t]
    r = ar * 0.001 + 0.0005
    out = nw_gate_cli.nw_tstat(r)
    naive_se = r.std(ddof=0) / np.sqrt(len(r))
    assert out["nw_se"] > naive_se


def test_nw_tstat_degenerate_single_obs_returns_none_not_nan():
    out = nw_gate_cli.nw_tstat(np.array([0.01]))
    assert out["n_obs"] == 1
    assert out["nw_tstat"] is None
    assert out["nw_se"] is None


def test_nw_tstat_zero_variance_returns_none_not_inf():
    out = nw_gate_cli.nw_tstat(np.zeros(100))
    assert out["nw_tstat"] is None
    assert out["nw_se"] is None


# ---------------------------------------------------------------------------
# HOLE 1: silent NaN/Inf drop before counting n_obs — must now FAIL LOUDLY
# ---------------------------------------------------------------------------


def test_finite_returns_rejects_nan_by_default():
    r = np.array([0.01, 0.02, np.nan, 0.01, -0.01])
    with pytest.raises(ValueError, match="NaN/Inf"):
        nw_gate_cli._finite_returns(r, allow_nonfinite_drop=False)


def test_finite_returns_rejects_inf_by_default():
    r = np.array([0.01, np.inf, 0.01, -0.01])
    with pytest.raises(ValueError, match="NaN/Inf"):
        nw_gate_cli._finite_returns(r, allow_nonfinite_drop=False)


def test_finite_returns_allows_explicit_opt_out():
    r = np.array([0.01, 0.02, np.nan, 0.01, -0.01])
    finite, n_dropped = nw_gate_cli._finite_returns(r, allow_nonfinite_drop=True)
    assert n_dropped == 1
    assert finite.size == 4


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


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))

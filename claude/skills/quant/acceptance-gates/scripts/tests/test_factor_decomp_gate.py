"""Tests for the factor-decomposition (Jensen's-alpha) gate.

Guards the 2026-07-19 hardening: codex's adversarial review of the wave-3 draft
found that an EMPTY factor list (e.g. ``--factor-columns ","``, which parses to
``[]`` and bypasses the "use all numeric columns" fallback since that fallback
only triggers when the flag is None) produced a valid intercept-only regression
that could PASS purely on raw mean return — exactly the "is this just beta in
disguise" failure this gate exists to catch.

Run: pytest scripts/tests/test_factor_decomp_gate.py -q
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

SCRIPTS = Path(__file__).resolve().parent.parent

_SPEC = importlib.util.spec_from_file_location(
    "factor_decomp_gate_cli", SCRIPTS / "factor-decomp-gate.py"
)
fd_gate_cli = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(fd_gate_cli)


def test_factor_regression_rejects_empty_factor_names():
    rng = np.random.default_rng(1)
    y = rng.normal(0.001, 0.01, 200)
    F = np.empty((200, 0))
    with pytest.raises(ValueError, match="at least one factor"):
        fd_gate_cli.factor_regression(y, F, [])


def test_factor_regression_recovers_known_alpha_and_beta():
    """Sanity: y = alpha + beta*factor + noise recovers alpha/beta within tolerance."""
    rng = np.random.default_rng(4)
    n = 2000
    factor = rng.normal(0.0, 0.01, n)
    true_alpha, true_beta = 0.0005, 0.8
    y = true_alpha + true_beta * factor + rng.normal(0, 0.002, n)
    reg = fd_gate_cli.factor_regression(y, factor, ["mkt"])
    assert reg["alpha"] == pytest.approx(true_alpha, abs=2e-4)
    assert reg["betas"]["mkt"] == pytest.approx(true_beta, abs=0.1)


def test_cli_rejects_empty_factor_columns_flag(tmp_path):
    """The exact codex scenario: --factor-columns "," parses to [] and must not
    silently fall through to an intercept-only regression."""
    rng = np.random.default_rng(2)
    n = 300
    idx = pd.date_range("2020-01-01", periods=n, freq="D")
    ret = pd.DataFrame({"returns": rng.normal(0.002, 0.01, n)}, index=idx)
    factors = pd.DataFrame({"mkt": rng.normal(0.0, 0.01, n)}, index=idx)
    rf = tmp_path / "returns.csv"
    ff = tmp_path / "factors.csv"
    ret.to_csv(rf)
    factors.to_csv(ff)

    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "factor-decomp-gate.py"),
            "--returns",
            str(rf),
            "--factors",
            str(ff),
            "--factor-columns",
            ",",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert "at least one named factor" in proc.stderr


def test_cli_intercept_only_would_have_passed_on_raw_mean_pre_fix(tmp_path):
    """Regression-proof of the actual failure mode: a strong positive-mean return
    series with NO real factor control must not be gate-passable at all — the CLI
    must refuse rather than run degenerate math that happens to look significant."""
    rng = np.random.default_rng(6)
    n = 300
    idx = pd.date_range("2020-01-01", periods=n, freq="D")
    # Strong, unambiguous positive-mean series — the kind that WOULD clear an
    # intercept-only "alpha" test with a healthy t-stat if the empty-factor hole
    # were still open.
    ret = pd.DataFrame({"returns": rng.normal(0.01, 0.005, n)}, index=idx)
    factors = pd.DataFrame({"mkt": rng.normal(0.0, 0.01, n)}, index=idx)
    rf = tmp_path / "returns.csv"
    ff = tmp_path / "factors.csv"
    ret.to_csv(rf)
    factors.to_csv(ff)

    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "factor-decomp-gate.py"),
            "--returns",
            str(rf),
            "--factors",
            str(ff),
            "--factor-columns",
            "",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0


def test_cli_named_factor_end_to_end(tmp_path):
    rng = np.random.default_rng(8)
    n = 500
    idx = pd.date_range("2020-01-01", periods=n, freq="D")
    factor = rng.normal(0.0, 0.01, n)
    y = 0.0004 + 0.5 * factor + rng.normal(0, 0.002, n)
    ret = pd.DataFrame({"returns": y}, index=idx)
    factors = pd.DataFrame({"mkt": factor}, index=idx)
    rf = tmp_path / "returns.csv"
    ff = tmp_path / "factors.csv"
    ret.to_csv(rf)
    factors.to_csv(ff)

    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "factor-decomp-gate.py"),
            "--returns",
            str(rf),
            "--factors",
            str(ff),
            "--factor-columns",
            "mkt",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    import json

    out = json.loads(proc.stdout)
    assert out["n_factors"] == 1
    assert out["gate_pass"] == (out["alpha_pass"] and out["obs_pass"])


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))

"""CLI tests for the factor-decomposition (Jensen's-alpha) gate.

The regression + HAC math now lives in the framework
(``quantbox.analysis.hac.factor_regression``) and is regression-tested there.
This suite covers only what the thin CLI owns: column resolution, the empty
factor-list guard (the codex-found "beta-in-disguise" hole), and the end-to-end
gate decision.

Run: pytest scripts/tests/test_factor_decomp_gate.py -q
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

_SPEC = importlib.util.spec_from_file_location("factor_decomp_gate_cli", SCRIPTS / "factor-decomp-gate.py")
fd_gate_cli = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(fd_gate_cli)


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
    out = json.loads(proc.stdout)
    assert out["n_factors"] == 1
    assert out["gate_pass"] == (out["alpha_pass"] and out["obs_pass"])

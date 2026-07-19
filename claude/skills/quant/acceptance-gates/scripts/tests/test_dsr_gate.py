"""CLI tests for the Deflated Sharpe Ratio (DSR) gate.

The DSR math itself now lives in the framework (``quantbox.analysis.dsr``) and its
regression suite — including the pinned false-PASS band, the impossible-Pearson-
moments identity, and the non-finite handling — lives in
``quantbox/tests/test_analysis_dsr.py``. This suite covers only what the thin CLI
owns: the n_trials-range policy, the conservative-end gate decision, threshold
validation, the mutually-exclusive input paths, and end-to-end JSON shape. The
false-PASS band is re-pinned here at the CLI boundary.

Run: pytest scripts/tests/test_dsr_gate.py -q
"""

from __future__ import annotations

import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

SCRIPTS = Path(__file__).resolve().parent.parent

# scripts/dsr-gate.py is hyphenated (CLI convention) -> load it explicitly. Importing
# it exercises the thin CLI's `from quantbox.analysis import ...`.
_SPEC = importlib.util.spec_from_file_location("dsr_gate_cli", SCRIPTS / "dsr-gate.py")
dsr_gate_cli = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(dsr_gate_cli)


# ---------------------------------------------------------------------------
# CLI policy + validation (main() directly)
# ---------------------------------------------------------------------------


def test_cli_periods_zero_rejected_not_coerced_to_one():
    """The old CLI silently coerced --periods 0 to 1, turning N obs into N years."""
    with pytest.raises(ValueError):
        dsr_gate_cli.main(
            [
                "--sharpe",
                "0.4",
                "--skew",
                "0.0",
                "--kurtosis",
                "3.0",
                "--n-obs",
                "500",
                "--n-trials",
                "10",
                "--periods",
                "0",
            ]
        )


def test_cli_requires_skew_kurtosis_with_sharpe():
    """--sharpe alone (no --skew/--kurtosis/--n-obs) must be refused, not defaulted."""
    with pytest.raises(SystemExit):
        dsr_gate_cli.main(["--sharpe", "0.4", "--n-trials", "10"])


def test_cli_rejects_zero_n_trials_in_range():
    with pytest.raises(ValueError):
        dsr_gate_cli.main(
            [
                "--sharpe",
                "0.4",
                "--skew",
                "0.0",
                "--kurtosis",
                "3.0",
                "--n-obs",
                "500",
                "--n-trials",
                "0",
            ]
        )


def test_cli_rejects_zero_n_trials_mixed_into_range():
    """A single bad entry anywhere in the range invalidates the whole call."""
    with pytest.raises(ValueError):
        dsr_gate_cli.main(
            [
                "--sharpe",
                "0.4",
                "--skew",
                "0.0",
                "--kurtosis",
                "3.0",
                "--n-obs",
                "500",
                "--n-trials",
                "5,10,0,50",
            ]
        )


def test_cli_rejects_empty_n_trials_range():
    with pytest.raises(ValueError):
        dsr_gate_cli.main(
            [
                "--sharpe",
                "0.4",
                "--skew",
                "0.0",
                "--kurtosis",
                "3.0",
                "--n-obs",
                "500",
                "--n-trials",
                "",
            ]
        )


@pytest.mark.parametrize(
    "bad_threshold", [0, -1, 1, 1.5, math.inf, -math.inf, math.nan]
)
def test_cli_rejects_invalid_threshold(bad_threshold):
    """--threshold 0/negative/>=1/non-finite would make nearly any DSR pass -- refuse them."""
    with pytest.raises((ValueError, SystemExit)):
        dsr_gate_cli.main(
            [
                "--sharpe",
                "0.4",
                "--skew",
                "0.0",
                "--kurtosis",
                "3.0",
                "--n-obs",
                "500",
                "--n-trials",
                "10",
                "--threshold",
                str(bad_threshold),
            ]
        )


def test_cli_rejects_impossible_pearson_moments():
    """skew=2, kurtosis=1 is impossible (min at skew=2 is 5) -- the CLI must propagate
    the same rejection quantbox.analysis.dsr enforces, not swallow it."""
    with pytest.raises(ValueError, match="impossible moments"):
        dsr_gate_cli.main(
            [
                "--sharpe",
                "0.4",
                "--skew",
                "2.0",
                "--kurtosis",
                "1.0",
                "--n-obs",
                "500",
                "--n-trials",
                "10",
            ]
        )


def test_cli_returns_and_summary_mutually_exclusive(tmp_path):
    returns_file = tmp_path / "returns.csv"
    pd.Series(np.random.default_rng(1).normal(0.001, 0.01, 300), name="return").to_csv(
        returns_file, index=False
    )
    with pytest.raises(SystemExit):
        dsr_gate_cli.main(
            ["--returns", str(returns_file), "--sharpe", "0.4", "--n-trials", "10"]
        )


# ---------------------------------------------------------------------------
# CLI end-to-end (subprocess, exercises the actual entry point)
# ---------------------------------------------------------------------------


def _run_cli(args: list[str]) -> dict:
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "dsr-gate.py"), *args],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    return json.loads(proc.stdout)


def test_cli_returns_path_end_to_end(tmp_path):
    rng = np.random.default_rng(7)
    r = rng.normal(0.0015, 0.012, 1000)
    returns_file = tmp_path / "returns.csv"
    pd.Series(r, name="return").to_csv(returns_file, index=False)
    out = _run_cli(
        ["--returns", str(returns_file), "--n-trials", "1,5,20", "--periods", "365"]
    )
    assert out["T"] == 1000
    assert set(out["by_n_trials"].keys()) == {"1", "5", "20"}
    assert out["n_trials_conservative"] == 20
    assert "dsr_conservative" in out and 0.0 <= out["dsr_conservative"] <= 1.0
    assert out["dsr_pass"] == (out["dsr_conservative"] >= out["threshold"])


def test_cli_reports_range_and_gates_on_max_n_trials():
    """DSR at n_trials=1 can pass while the conservative (max) end fails — the gate
    must decide from the conservative end, not the most flattering one."""
    out = _run_cli(
        [
            "--sharpe",
            "1.5",
            "--skew",
            "-0.1",
            "--kurtosis",
            "4.0",
            "--n-obs",
            "1000",
            "--n-trials",
            "1,5,20,100",
            "--periods",
            "365",
        ]
    )
    dsrs = {int(n): v["dsr"] for n, v in out["by_n_trials"].items()}
    assert dsrs[1] >= dsrs[5] >= dsrs[20] >= dsrs[100]
    assert out["n_trials_conservative"] == 100
    assert out["dsr_conservative"] == pytest.approx(dsrs[100])
    assert out["dsr_pass"] == (dsrs[100] >= out["threshold"])


def test_cli_default_n_trials_range_matches_carver_convention():
    """Default range mirrors carver_prelive_gauntlet.py's sensitivity sweep."""
    out = _run_cli(
        ["--sharpe", "1.0", "--skew", "0.0", "--kurtosis", "3.0", "--n-obs", "500"]
    )
    assert {int(n) for n in out["by_n_trials"]} == {1, 5, 10, 20, 50, 100}
    assert out["n_trials_conservative"] == 100


def test_cli_summary_path_end_to_end():
    out = _run_cli(
        [
            "--sharpe",
            "1.5",
            "--skew",
            "-0.1",
            "--kurtosis",
            "4.0",
            "--n-obs",
            "1000",
            "--n-trials",
            "5",
            "--periods",
            "365",
        ]
    )
    assert out["n_trials_conservative"] == 5
    assert out["T"] == 1000


def test_false_pass_band_cli_end_to_end_fails_gate():
    """The verified false-PASS band, driven through the actual CLI (conservative end,
    n_trials=20) with the default 0.95 threshold — must FAIL."""
    z_naive = 3.3
    T = 365
    sr_ann = z_naive  # periods=365, T=365 -> n_years=1 -> sr_ann == z_naive
    out = _run_cli(
        [
            "--sharpe",
            str(sr_ann),
            "--skew",
            "0.0",
            "--kurtosis",
            "3.0",
            "--n-obs",
            str(T),
            "--n-trials",
            "20",
            "--periods",
            "365",
        ]
    )
    assert out["dsr_conservative"] == pytest.approx(0.9147, abs=5e-3)
    assert out["dsr_pass"] is False

"""Tests for the genuine Deflated Sharpe Ratio (DSR) gate.

Guards the 2026-07-19 correctness fix (obsidian-vaults issue, quantbox-lab
branch quark/fix-dsr-gate): the previous gate computed t = sharpe * sqrt(n_years)
against a Bonferroni-corrected NORMAL null — silently assuming zero
skew/kurtosis and using no real expected-max-Sharpe deflation. That is a plain
significance test, not DSR. This suite exercises the real math in
scripts/lib/dsr.py and the CLI plumbing in scripts/dsr-gate.py (which reports
DSR across a RANGE of n_trials and gates on the conservative/max end, per the
carver_prelive_gauntlet.py convention), and pins the specific false-PASS band
the old gate let through.

Run: pytest scripts/tests/test_dsr_gate.py -q
"""

from __future__ import annotations

import importlib.util
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats

SCRIPTS = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(SCRIPTS / "lib"))
import dsr  # noqa: E402

deflated_sharpe_ratio = dsr.deflated_sharpe_ratio
deflated_sharpe_ratio_from_returns = dsr.deflated_sharpe_ratio_from_returns
expected_max_sr = dsr.expected_max_sr

# scripts/dsr-gate.py is hyphenated (CLI convention) -> load it explicitly.
_SPEC = importlib.util.spec_from_file_location("dsr_gate_cli", SCRIPTS / "dsr-gate.py")
dsr_gate_cli = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(dsr_gate_cli)


# ---------------------------------------------------------------------------
# scripts/lib/dsr.py — the shared math
# ---------------------------------------------------------------------------


def test_expected_max_sr_known_value_n20():
    """Bailey & Lopez de Prado (2014) exact form, N=20 -> ~1.9007."""
    assert expected_max_sr(20) == pytest.approx(1.9007079511811988, abs=1e-9)


def test_expected_max_sr_single_trial_is_zero():
    """A single trial has no multiple-testing penalty -> e_max=0, sr0=0."""
    assert expected_max_sr(1) == 0.0


def test_expected_max_sr_rejects_nonpositive_trials():
    """No silent coercion to 1 — removing the penalty must be an explicit choice."""
    with pytest.raises(ValueError):
        expected_max_sr(0)
    with pytest.raises(ValueError):
        expected_max_sr(-5)


def test_dsr_normal_returns_matches_hand_derivation():
    """skew=0, kurtosis=3 (normal): sr_std = sqrt((1 + 0.5*sr^2)/(T-1))."""
    sr, T, n_trials = 0.1, 500, 10
    result = deflated_sharpe_ratio(
        sr=sr, T=T, skew=0.0, kurtosis=3.0, n_trials=n_trials
    )
    expected_sr_std = math.sqrt((1 - 0.0 * sr + (3.0 - 1) / 4 * sr**2) / (T - 1))
    assert result.sr_std == pytest.approx(expected_sr_std, rel=1e-9)
    expected_sr0 = expected_sr_std * expected_max_sr(n_trials)
    assert result.sr0_period == pytest.approx(expected_sr0, rel=1e-9)
    expected_z = (sr - expected_sr0) / expected_sr_std
    assert result.z == pytest.approx(expected_z, rel=1e-9)
    assert result.dsr == pytest.approx(stats.norm.cdf(expected_z), rel=1e-9)


def test_dsr_deflates_more_with_more_trials():
    """More trials -> larger e_max -> larger sr0 -> lower DSR, all else equal."""
    kwargs = dict(sr=0.15, T=500, skew=-0.2, kurtosis=4.0)
    d1 = deflated_sharpe_ratio(n_trials=1, **kwargs)
    d20 = deflated_sharpe_ratio(n_trials=20, **kwargs)
    d100 = deflated_sharpe_ratio(n_trials=100, **kwargs)
    assert d1.sr0_period < d20.sr0_period < d100.sr0_period
    assert d1.dsr > d20.dsr > d100.dsr


def test_dsr_fat_tails_reduce_confidence_vs_normal():
    """Higher kurtosis (fatter tails) inflates sr_std -> lower DSR than the normal case."""
    kwargs = dict(sr=0.2, T=500, n_trials=10)
    normal = deflated_sharpe_ratio(skew=0.0, kurtosis=3.0, **kwargs)
    fat_tailed = deflated_sharpe_ratio(skew=0.0, kurtosis=9.0, **kwargs)
    assert fat_tailed.sr_std > normal.sr_std
    assert fat_tailed.dsr < normal.dsr


def test_dsr_from_returns_matches_direct_computation():
    rng = np.random.default_rng(42)
    r = rng.standard_t(df=5, size=800) * 0.01 + 0.0003
    from_returns = deflated_sharpe_ratio_from_returns(r, n_trials=15)
    sr = r.mean() / r.std(ddof=1)
    sk = float(stats.skew(r))
    ku = float(stats.kurtosis(r, fisher=False))
    direct = deflated_sharpe_ratio(sr=sr, T=len(r), skew=sk, kurtosis=ku, n_trials=15)
    assert from_returns.dsr == pytest.approx(direct.dsr, rel=1e-9)


# ---------------------------------------------------------------------------
# Degenerate-input holes — must FAIL LOUDLY, never silently weaken the gate
# ---------------------------------------------------------------------------


def test_infinite_sharpe_rejected():
    with pytest.raises(ValueError):
        deflated_sharpe_ratio(sr=math.inf, T=500, skew=0.0, kurtosis=3.0, n_trials=10)


def test_nonpositive_n_trials_rejected_not_coerced():
    """The old gate silently coerced n_trials<=0 to 1, removing the Bonferroni penalty."""
    with pytest.raises(ValueError):
        deflated_sharpe_ratio(sr=0.1, T=500, skew=0.0, kurtosis=3.0, n_trials=0)
    with pytest.raises(ValueError):
        deflated_sharpe_ratio(sr=0.1, T=500, skew=0.0, kurtosis=3.0, n_trials=-3)


def test_too_few_observations_rejected():
    with pytest.raises(ValueError):
        deflated_sharpe_ratio(sr=0.1, T=1, skew=0.0, kurtosis=3.0, n_trials=10)


def test_zero_variance_returns_rejected():
    with pytest.raises(ValueError):
        deflated_sharpe_ratio_from_returns(np.zeros(200), n_trials=10)


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
    import json

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
    """Default range mirrors scripts/analysis/carver_prelive_gauntlet.py's
    sensitivity sweep (1, 5, 10, 20, 50, 100)."""
    out = _run_cli(
        ["--sharpe", "1.0", "--skew", "0.0", "--kurtosis", "3.0", "--n-obs", "500"]
    )
    assert set(int(n) for n in out["by_n_trials"]) == {1, 5, 10, 20, 50, 100}
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


# ---------------------------------------------------------------------------
# THE REGRESSION: the verified false-PASS band, pinned as FAIL under real DSR
# ---------------------------------------------------------------------------
#
# Reconstructed from the task's verified consequence: with the OLD gate's
# naive normal-null z-stat (z = sharpe_ann * sqrt(n_years)) at z in [3.1, 3.6]
# and N=20 trials, the old gate PASSED (Bonferroni-adjusted normal p-value
# under alpha/20) while true DSR sits at 0.88-0.95 -- i.e. it can be BELOW a
# 0.95 acceptance bar. We reproduce the exact scenario (skew=0, kurtosis=3 --
# i.e. even in the BEST case with no fat-tail penalty, deflation alone moves
# the verdict) via 1 year of daily data (T=365, periods=365) so
# sr_annualized == z_naive.


@pytest.mark.parametrize(
    "z_naive,expected_dsr",
    [
        (3.1, 0.8800),
        (3.5, 0.9413),
    ],
)
def test_false_pass_band_now_fails_under_real_dsr(z_naive, expected_dsr):
    T = 365
    sr_period = z_naive / math.sqrt(T)  # so sr_annualized == z_naive with periods=365
    result = deflated_sharpe_ratio(
        sr=sr_period, T=T, skew=0.0, kurtosis=3.0, n_trials=20
    )

    # Sanity: this IS the band the old gate would have passed.
    old_style_pvalue = 2 * (1 - stats.norm.cdf(abs(z_naive)))
    old_style_alpha_adj = 0.05 / 20
    old_gate_would_pass = bool(z_naive > 0 and old_style_pvalue < old_style_alpha_adj)
    assert old_gate_would_pass is True

    # The real DSR in this band is below a 0.95 acceptance threshold.
    assert result.dsr == pytest.approx(expected_dsr, abs=5e-3)
    assert result.dsr < 0.95


def test_false_pass_band_cli_end_to_end_fails_gate():
    """Same scenario, driven through the actual CLI (conservative end, n_trials=20)
    with the default 0.95 threshold."""
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


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))

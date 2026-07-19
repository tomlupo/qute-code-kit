"""Shared deflated-Sharpe-ratio (DSR) math.

Bailey & López de Prado (2014), "The Deflated Sharpe Ratio", with the Mertens
(2002) correction for skew/kurtosis in the variance of the Sharpe estimator.

SINGLE SOURCE OF TRUTH — both ``scripts/dsr-gate.py`` (the dev-loop CLI gate)
and ``scripts/analysis/carver_prelive_gauntlet.py`` (the pre-live gauntlet)
import this module rather than reimplementing the math. If you find yourself
about to write ``skew``/``kurtosis``/``expected max SR`` formulas anywhere
else in this repo, import from here instead.

All Sharpe/skew/kurtosis inputs and outputs here are in PER-PERIOD units
(daily, if your returns are daily) — annualisation is a display concern for
the caller, not part of the DSR test itself.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

from scipy import stats

EULER_MASCHERONI = 0.5772156649015329


@dataclass(frozen=True)
class DSRResult:
    T: int
    sr_period: float
    skew: float
    kurtosis: float  # non-excess (Pearson) kurtosis — matches scipy.stats.kurtosis(fisher=False)
    sr_std: float  # std of the Sharpe-ratio estimator, per-period units
    sr0_period: float  # expected-max-SR deflation benchmark, per-period units
    z: float  # (sr - sr0) / sr_std
    psr_vs_zero: float  # P(true SR > 0) — undeflated, single-trial reference
    dsr: float  # P(true SR > deflated benchmark) — the actual DSR statistic
    n_trials: int
    n_obs_raw: int = 0  # raw observation count BEFORE any non-finite filtering
    n_nonfinite_dropped: int = 0  # how many NaN/Inf observations were dropped (0 unless opted in)


def expected_max_sr(n_trials: int) -> float:
    """Expected max Sharpe over ``n_trials`` iid N(0,1) trials.

    Exact Bailey & López de Prado (2014) form (not the leading-order
    asymptotic, which under-deflates at small N).

    Raises ValueError for n_trials <= 0 — there is no such thing as "zero or
    negative trials"; silently coercing this to 1 (as the old gate did)
    quietly removes the entire multiple-testing penalty.
    """
    if n_trials <= 0:
        raise ValueError(f"n_trials must be a positive integer, got {n_trials!r}")
    if n_trials == 1:
        return 0.0
    return (1 - EULER_MASCHERONI) * stats.norm.ppf(1 - 1.0 / n_trials) + EULER_MASCHERONI * stats.norm.ppf(
        1 - 1.0 / (n_trials * math.e)
    )


def sr_estimator_std(T: int, sr: float, skew: float, kurtosis: float) -> float:
    """Std of the Sharpe-ratio estimator (Mertens 2002 / Bailey-López de Prado), per-period units."""
    if T <= 1:
        raise ValueError(f"need at least 2 observations to estimate SR variance, got T={T!r}")
    variance = (1 - skew * sr + (kurtosis - 1) / 4 * sr**2) / (T - 1)
    if variance < 0:
        # Can happen with pathological (garbage) skew/kurtosis/sr combinations.
        # Fail loudly rather than silently sqrt()-ing a negative number to NaN.
        raise ValueError(
            f"negative SR-estimator variance ({variance!r}) from T={T}, sr={sr}, "
            f"skew={skew}, kurtosis={kurtosis} — check inputs"
        )
    return math.sqrt(variance)


def deflated_sharpe_ratio(sr: float, T: int, skew: float, kurtosis: float, n_trials: int) -> DSRResult:
    """Compute the genuine Deflated Sharpe Ratio.

    Parameters are all PER-PERIOD (not annualised): ``sr`` is the per-period
    Sharpe, ``skew``/``kurtosis`` are the per-period return-distribution
    moments, ``T`` is the number of return observations.

    Returns a DSRResult; ``result.dsr`` is P(true SR exceeds the
    multiple-testing-deflated benchmark) — compare against a threshold
    (e.g. 0.95) to decide pass/fail. This function does not itself apply a
    threshold — an acceptance gate is a policy decision made by the caller.
    """
    if not math.isfinite(sr):
        raise ValueError(f"sharpe must be finite, got {sr!r}")
    if not math.isfinite(skew) or not math.isfinite(kurtosis):
        raise ValueError(f"skew/kurtosis must be finite, got skew={skew!r} kurtosis={kurtosis!r}")

    sr_std = sr_estimator_std(T, sr, skew, kurtosis)
    if sr_std == 0:
        raise ValueError("zero SR-estimator std (degenerate/constant returns) — cannot compute DSR")

    e_max = expected_max_sr(n_trials)
    sr0 = sr_std * e_max
    z = (sr - sr0) / sr_std
    psr0 = stats.norm.cdf(sr / sr_std)
    dsr = stats.norm.cdf(z)

    return DSRResult(
        T=T,
        sr_period=sr,
        skew=skew,
        kurtosis=kurtosis,
        sr_std=sr_std,
        sr0_period=sr0,
        z=z,
        psr_vs_zero=psr0,
        dsr=dsr,
        n_trials=n_trials,
        # Called directly with already-computed moments — no filtering has
        # happened at this layer, so raw == surviving and nothing was dropped.
        n_obs_raw=T,
        n_nonfinite_dropped=0,
    )


def deflated_sharpe_ratio_from_returns(returns, n_trials: int, *, allow_nonfinite_drop: bool = False) -> DSRResult:
    """Convenience wrapper: compute DSR directly from a per-period returns series.

    ``returns`` is any 1-D array-like of per-period returns (pandas Series /
    numpy array / list).

    Non-finite handling matches ``nw-tstat-gate.py``'s ``--allow-nonfinite-drop``
    convention exactly, by design (same skill, same invariant — "every gate
    fails loudly, never silently passes"):

    - By default (``allow_nonfinite_drop=False``), ANY NaN or ±Inf value in
      ``returns`` RAISES ``ValueError``. A corrupted/degenerate returns file
      must never silently pass on the surviving subset with no disclosure of
      how many observations vanished.
    - Pass ``allow_nonfinite_drop=True`` to explicitly opt into dropping
      non-finite observations and continuing. The returned ``DSRResult``
      then reports both ``n_obs_raw`` (the observation count before
      filtering) and ``n_nonfinite_dropped`` (how many were dropped) so the
      loss is always visible in the output, never silently absorbed into
      ``T``.

    Degenerate input (fewer than 2 finite observations, zero variance) still
    raises via the same paths as ``deflated_sharpe_ratio``.
    """
    import numpy as np

    raw = np.asarray(returns, dtype=float)
    finite_mask = np.isfinite(raw)
    n_dropped = int((~finite_mask).sum())
    if n_dropped and not allow_nonfinite_drop:
        raise ValueError(
            f"{n_dropped} of {raw.size} return observations are NaN/Inf — refusing to "
            "silently drop them (a corrupted returns file must not pass on the surviving "
            "subset). Pass allow_nonfinite_drop=True to explicitly opt into dropping them "
            "and continuing."
        )
    r = raw[finite_mask]
    T = len(r)
    if T <= 1:
        raise ValueError(f"need at least 2 finite return observations, got T={T!r}")
    std = r.std(ddof=1)
    if std == 0:
        raise ValueError("zero-variance returns — cannot compute a Sharpe ratio")
    sr = r.mean() / std
    skew = float(stats.skew(r))
    kurtosis = float(stats.kurtosis(r, fisher=False))
    result = deflated_sharpe_ratio(sr=sr, T=T, skew=skew, kurtosis=kurtosis, n_trials=n_trials)
    return replace(result, n_obs_raw=int(raw.size), n_nonfinite_dropped=n_dropped)

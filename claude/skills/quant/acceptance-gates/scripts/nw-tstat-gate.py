#!/usr/bin/env python3
"""Deterministic Newey-West (HAC) t-stat + min-OOS-window gate for dev-loop Step 3.

Sibling to ``dsr-gate.py``. Two robustness checks the DSR gate does NOT cover
(obsidian-vaults#38):

1. **Newey-West t-stat on mean return.** The DSR gate works off the annualised
   Sharpe and a trial count; it assumes i.i.d. returns. Real strategy returns are
   autocorrelated (momentum/trend overlap, overlapping windows), which INFLATES a
   naive t-stat. The HAC (heteroskedasticity-and-autocorrelation-consistent)
   Newey-West standard error corrects for that serial correlation, so the t-stat
   on the mean return is honest. Gate: ``nw_tstat >= --t-threshold`` AND mean > 0.

2. **Named minimum OOS-window length.** A passing t-stat over a 30-day sample is
   not the same as one over 3 years. This records the OOS window length as a HARD
   frontmatter field and fails the gate when it is shorter than ``--min-oos-periods``
   — so "tested out-of-sample on too little data" can never hide behind a Sharpe.

Pure math — keep it out of the model's turns so the verdict is reproducible.

  PROVENANCE + HARDENING (2026-07-19): ported from quantbox-lab's wave-3 draft
  (branch quark/wave3-gates-clean); codex's adversarial review found two holes
  in that draft that let a corrupt/degenerate return series slip through, both
  closed here:

  (a) the loader silently dropped NaN/Inf returns via a boolean mask BEFORE
      ``n_obs`` was ever counted — a file with 200 legit returns and 500
      corrupt (NaN) rows would silently report n_obs=200 and could clear
      ``--min-oos-periods`` on the surviving subset, hiding a real data-quality
      failure behind a passing gate. Fixed: non-finite values now RAISE
      (``--allow-nonfinite-drop`` opts back into the old drop-and-continue
      behavior explicitly, for callers who have already vetted the source).
  (b) ``--oos-periods`` was trusted even when it EXCEEDED the actual finite
      return count — a caller could claim a 3-year OOS window on a file that
      only has 30 real observations and the gate would record and grade that
      claim uncritically. Fixed: ``--oos-periods`` is now capped to (and must
      not exceed) the actual finite observation count; exceeding it raises.

Usage:
  nw-tstat-gate.py --returns oos_returns.parquet [--column returns] \\
      [--t-threshold 2.0] [--min-oos-periods 252] [--lags N] [--oos-periods N]

The ``--returns`` file should be the OOS return series (one return per period).
Pass ``--oos-periods`` to record a window length other than ``len(returns)`` (e.g.
when the file mixes IS+OOS and you only want the OOS span counted) — it can only
SHRINK the recorded window relative to the finite-observation count, never inflate it.

Prints JSON: {n_obs, n_obs_raw, n_nonfinite_dropped, nw_lags, mean_return, nw_se,
              nw_tstat, nw_pvalue, nw_pass, oos_window_periods, min_oos_periods,
              oos_window_pass, gate_pass}.
"""

from __future__ import annotations

import argparse
import json
import math
import sys

import numpy as np
from scipy.stats import norm

# Columns to try, in order, when --column is not given and the frame has >1 col.
_RETURN_COL_CANDIDATES = ("returns", "return", "ret", "rets", "pnl", "r")


def _newey_west_auto_lags(n: int) -> int:
    """Newey-West (1994) automatic lag truncation: floor(4 * (n/100)^(2/9))."""
    return int(math.floor(4 * (n / 100.0) ** (2.0 / 9.0)))


def _finite_returns(
    raw: np.ndarray, *, allow_nonfinite_drop: bool
) -> tuple[np.ndarray, int]:
    """Validate a raw return array: FAIL LOUDLY on NaN/Inf unless explicitly opted out.

    Returns (finite_returns, n_dropped). Raises ValueError when non-finite values
    are present and ``allow_nonfinite_drop`` is False — a corrupt input must never
    silently shrink the sample the gate then reports as complete.
    """
    r = np.asarray(raw, dtype=float)
    finite_mask = np.isfinite(r)
    n_dropped = int((~finite_mask).sum())
    if n_dropped and not allow_nonfinite_drop:
        raise ValueError(
            f"{n_dropped} of {r.size} return observations are NaN/Inf — refusing to silently "
            "drop them (a corrupt file must not pass on the surviving subset). Pass "
            "--allow-nonfinite-drop to explicitly opt into dropping them and continuing."
        )
    return r[finite_mask], n_dropped


def nw_tstat(returns: np.ndarray, lags: int | None = None) -> dict:
    """Newey-West HAC t-stat on the mean of ``returns``.

    Long-run variance via the Bartlett kernel:
        LRV = gamma_0 + 2 * sum_{l=1..L} (1 - l/(L+1)) * gamma_l
    SE of the mean = sqrt(LRV / n); t = mean / SE. Returns the t-stat, two-sided
    p-value, the lag count used, and the components. A degenerate series (n < 2 or
    zero long-run variance) yields a None t-stat rather than inf/nan.

    ``returns`` MUST already be finite (see ``_finite_returns``) — this function
    does not itself filter NaN/Inf.
    """
    r = np.asarray(returns, dtype=float)
    n = r.size
    if n < 2:
        return {
            "n_obs": n,
            "nw_lags": 0,
            "mean_return": None,
            "nw_se": None,
            "nw_tstat": None,
            "nw_pvalue": None,
        }

    if lags is None:
        lags = _newey_west_auto_lags(n)
    lags = max(0, min(lags, n - 1))  # can't use more lags than we have data

    mu = float(r.mean())
    e = r - mu
    lrv = float(e @ e) / n  # gamma_0
    for lag in range(1, lags + 1):
        cov = float(e[lag:] @ e[:-lag]) / n  # gamma_l
        weight = 1.0 - lag / (lags + 1.0)  # Bartlett kernel
        lrv += 2.0 * weight * cov

    if lrv <= 0:
        return {
            "n_obs": n,
            "nw_lags": lags,
            "mean_return": round(mu, 8),
            "nw_se": None,
            "nw_tstat": None,
            "nw_pvalue": None,
        }

    se = math.sqrt(lrv / n)
    t = mu / se
    pval = 2.0 * (1.0 - norm.cdf(abs(t)))
    return {
        "n_obs": n,
        "nw_lags": lags,
        "mean_return": round(mu, 8),
        "nw_se": round(se, 8),
        "nw_tstat": round(t, 4),
        "nw_pvalue": round(pval, 6),
    }


def _read_returns(path: str, column: str | None) -> np.ndarray:
    """Load a raw return series from parquet / csv / whitespace-delimited text.

    Does NOT filter NaN/Inf — that is ``_finite_returns``'s job, so the caller
    controls (and the output records) whether/how many were dropped.
    """
    lower = path.lower()
    if lower.endswith(".parquet"):
        import pandas as pd

        df = pd.read_parquet(path)
    elif lower.endswith(".csv"):
        import pandas as pd

        df = pd.read_csv(path)
    else:  # plain text: one number per line
        return np.loadtxt(path, dtype=float).ravel()

    if column is not None:
        if column not in df.columns:
            raise SystemExit(f"column {column!r} not in {list(df.columns)}")
        return df[column].to_numpy(dtype=float)
    # Auto-pick: a single column, else a known return-column name.
    numeric = df.select_dtypes("number")
    if numeric.shape[1] == 1:
        return numeric.iloc[:, 0].to_numpy(dtype=float)
    for cand in _RETURN_COL_CANDIDATES:
        if cand in df.columns:
            return df[cand].to_numpy(dtype=float)
    raise SystemExit(
        f"could not infer return column from {list(df.columns)}; pass --column"
    )


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--returns", required=True, help="OOS return series (parquet/csv/txt)"
    )
    ap.add_argument("--column", default=None, help="return column name (else auto)")
    ap.add_argument(
        "--t-threshold", type=float, default=2.0, help="min |Newey-West t| to pass"
    )
    ap.add_argument(
        "--min-oos-periods",
        type=int,
        default=252,
        help="named minimum OOS-window length (periods); recorded + gated",
    )
    ap.add_argument(
        "--lags",
        type=int,
        default=None,
        help="HAC lags (default: Newey-West auto, floor(4*(n/100)^(2/9)))",
    )
    ap.add_argument(
        "--oos-periods",
        type=int,
        default=None,
        help=(
            "override the recorded OOS window length (default: finite-return count). "
            "Can only be <= the finite-return count — it may narrow the claimed window "
            "(e.g. an IS+OOS mixed file) but never inflate it beyond what the data supports."
        ),
    )
    ap.add_argument(
        "--allow-nonfinite-drop",
        action="store_true",
        help=(
            "explicitly opt into silently dropping NaN/Inf return observations before "
            "counting n_obs (default: refuse and raise on any non-finite value)"
        ),
    )
    args = ap.parse_args(argv)

    if args.min_oos_periods <= 0:
        raise ValueError(
            f"--min-oos-periods must be positive, got {args.min_oos_periods!r}"
        )

    raw = _read_returns(args.returns, args.column)
    r, n_dropped = _finite_returns(raw, allow_nonfinite_drop=args.allow_nonfinite_drop)
    nw = nw_tstat(r, lags=args.lags)

    # Gate 1 — honest t-stat: positive mean AND |t| over the threshold.
    nw_pass = bool(
        nw["nw_tstat"] is not None
        and nw["mean_return"] is not None
        and nw["mean_return"] > 0
        and nw["nw_tstat"] >= args.t_threshold
    )

    # Gate 2 — named minimum OOS window, capped to (never exceeding) the actual
    # finite-observation count. A claimed window longer than the real data is a
    # bug/lie, not a legitimate override — it must raise, not be recorded as-is.
    n_finite = nw["n_obs"]
    if args.oos_periods is not None:
        if args.oos_periods > n_finite:
            raise ValueError(
                f"--oos-periods={args.oos_periods} exceeds the actual finite-return count "
                f"({n_finite}) — cannot claim a longer OOS window than the data supports"
            )
        if args.oos_periods <= 0:
            raise ValueError(
                f"--oos-periods must be positive, got {args.oos_periods!r}"
            )
        oos_window = args.oos_periods
    else:
        oos_window = n_finite
    oos_window_pass = bool(oos_window >= args.min_oos_periods)

    out = {
        **nw,
        "n_obs_raw": int(raw.size),
        "n_nonfinite_dropped": n_dropped,
        "nw_pass": nw_pass,
        "oos_window_periods": oos_window,
        "min_oos_periods": args.min_oos_periods,
        "oos_window_pass": oos_window_pass,
        # The robustness gate passes only when BOTH checks clear.
        "gate_pass": bool(nw_pass and oos_window_pass),
    }
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except ValueError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        raise SystemExit(2) from e

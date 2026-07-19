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

  The HAC statistic itself lives in the framework —
  ``quantbox.analysis.hac.newey_west_tstat`` (statsmodels-backed, see that
  module's parity note). This repo owns ZERO of the HAC statistics: this file is
  CLI plumbing only — load the return series, call the framework, apply the
  min-OOS-window and t-stat gate policy, print JSON. The non-finite
  fail-loudly invariant (NaN/Inf RAISE unless ``--allow-nonfinite-drop``) and
  the Newey-West lag rule also live in the framework; the CLI adds only the
  ``--oos-periods`` cap (a window claim can only SHRINK the finite-observation
  count, never inflate it) and the pass/fail thresholds.

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
import sys

import numpy as np
from quantbox.analysis import newey_west_tstat

# Columns to try, in order, when --column is not given and the frame has >1 col.
_RETURN_COL_CANDIDATES = ("returns", "return", "ret", "rets", "pnl", "r")


def _read_returns(path: str, column: str | None) -> np.ndarray:
    """Load a raw return series from parquet / csv / whitespace-delimited text.

    Does NOT filter NaN/Inf — that is the framework's ``require_finite`` job (via
    ``newey_west_tstat``), so the caller controls (and the output records)
    whether/how many were dropped.
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


def _round_nw(nw: dict) -> dict:
    """Round the framework's full-precision stats for JSON display (presentation only)."""
    out = dict(nw)
    for key, ndigits in (
        ("mean_return", 8),
        ("nw_se", 8),
        ("nw_tstat", 4),
        ("nw_pvalue", 6),
    ):
        if out.get(key) is not None:
            out[key] = round(out[key], ndigits)
    return out


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
    # The framework validates finiteness (raise-by-default / opt-in drop) and
    # computes the HAC t-stat. This CLI owns none of that math.
    nw = _round_nw(
        newey_west_tstat(
            raw, lags=args.lags, allow_nonfinite_drop=args.allow_nonfinite_drop
        )
    )

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

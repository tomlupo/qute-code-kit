#!/usr/bin/env python3
"""Deterministic factor-decomposition (Jensen's-alpha) gate for dev-loop Step 3.

Sibling to ``dsr-gate.py`` and ``nw-tstat-gate.py``. Those two gates ask *is the
return real and significant?* This gate asks a different, harder question: *is the
return NOVEL, or is it just paid-for factor exposure?* A strategy can clear the DSR
and Newey-West gates with a perfectly honest, significant positive mean return and
still be worthless as a *new* edge — because that return is nothing more than a
levered bet on BTC-beta, cross-sectional momentum, or carry, all of which are
already-known, already-harvestable factors. Promoting such a strategy adds no
diversification and no skill; it just re-packages a factor the book already owns.

The gate regresses the candidate's return series on a set of KNOWN factor return
series:

    r_strategy(t) = alpha + sum_j beta_j * f_j(t) + e(t)

- ``beta_j``  = the strategy's loading on factor j (how much of its return is that
  factor's exposure).
- ``alpha``   = Jensen's alpha: the average return LEFT OVER after controlling for
  every factor. This residual is the only part that could plausibly be skill / a
  novel edge.

GATE (null hypothesis H0: alpha <= 0 — "no residual edge beyond factors"):
  PASS  when alpha is significantly > 0 (one-sided HAC t-stat >= --t-threshold).
  FLAG/FAIL otherwise — the return is explained by factor exposure, not skill.

Standard errors on the coefficients are Newey-West HAC (Bartlett kernel), exactly
as in ``nw-tstat-gate.py``: strategy returns are autocorrelated (overlapping
signals, trend overlap), and OLS/White SEs would understate the alpha's SE and
rubber-stamp a spurious edge. HAC corrects the SE of the intercept specifically.

  The regression + HAC math lives in the framework —
  ``quantbox.analysis.hac.factor_regression`` (statsmodels-backed). This repo owns
  ZERO of the regression statistics: this file is CLI plumbing only — load the two
  frames, resolve/inner-join the columns, guard against an empty factor list, call
  the framework, apply the alpha t-stat + min-obs gate policy, print JSON.

Point-in-time factors: the regression math is agnostic to how the factor series
were built, but the GATE IS ONLY AS HONEST AS ITS FACTORS. Factor series MUST be
constructed point-in-time (weights formed from information available at t-1,
realised at t) or a look-ahead-contaminated factor will absorb genuine alpha and
produce a false FAIL — or a look-ahead-leaking strategy will masquerade as alpha.
Building the point-in-time crypto factor panel is a harness-specific,
data-aware job that belongs to the consuming research repo (NOT this portable
gate) — feed an already-built factor series in via ``--factors``.

  HARDENING (2026-07-19): codex's adversarial review found a hole where an EMPTY
  factor list (e.g. ``--factor-columns ","``, which parses to ``[]``) produced a
  valid, intercept-only regression that could PASS purely on the raw mean return —
  exactly the "is this just beta in disguise" failure this gate exists to catch.
  Guarded here: an explicitly empty (post-parse) factor-column list raises, whether
  it came from ``--factor-columns`` or an empty auto-detected numeric-column set.
  The framework's ``factor_regression`` also refuses an empty ``factor_names``.

Usage:
  factor-decomp-gate.py --returns strat_returns.parquet \\
      --factors factors.parquet [--column returns] [--factor-columns mkt,mom,carry] \\
      [--t-threshold 2.0] [--lags N] [--min-obs 60]

Both files are indexed by date; the strategy and factor series are inner-joined on
their common dates before regressing (so a factor panel that starts later just
trims the sample — recorded in ``n_obs``).

Prints JSON: {n_obs, n_factors, factors, betas, alpha, alpha_se, alpha_tstat,
              alpha_pvalue_onesided, r_squared, hac_lags, t_threshold, alpha_pass,
              min_obs, obs_pass, gate_pass, note}.
"""

from __future__ import annotations

import argparse
import json
import sys

from quantbox.analysis import factor_regression


def _read_frame(path: str):
    """Load a date-indexed frame from parquet / csv (first column = index)."""
    lower = path.lower()
    if lower.endswith(".parquet"):
        import pandas as pd

        return pd.read_parquet(path)
    if lower.endswith(".csv"):
        import pandas as pd

        return pd.read_csv(path, index_col=0, parse_dates=True)
    raise SystemExit(f"unsupported file type (need .parquet/.csv): {path}")


_RETURN_COL_CANDIDATES = ("returns", "return", "ret", "rets", "pnl", "r")


def _pick_return_column(df, column: str | None):
    """Resolve the strategy return column (mirrors nw-tstat-gate's auto-pick)."""
    if column is not None:
        if column not in df.columns:
            raise SystemExit(f"column {column!r} not in {list(df.columns)}")
        return column
    numeric = df.select_dtypes("number")
    if numeric.shape[1] == 1:
        return numeric.columns[0]
    for cand in _RETURN_COL_CANDIDATES:
        if cand in df.columns:
            return cand
    raise SystemExit(f"could not infer return column from {list(df.columns)}; pass --column")


def _round_reg(reg: dict) -> dict:
    """Round the framework's full-precision regression stats for JSON display."""
    out = dict(reg)
    if out.get("betas") is not None:
        out["betas"] = {name: round(b, 8) for name, b in out["betas"].items()}
    for key, ndigits in (
        ("alpha", 8),
        ("alpha_se", 8),
        ("alpha_tstat", 4),
        ("alpha_pvalue_onesided", 6),
        ("r_squared", 6),
    ):
        if out.get(key) is not None:
            out[key] = round(out[key], ndigits)
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--returns", required=True, help="strategy return series (parquet/csv)")
    ap.add_argument("--factors", required=True, help="factor return panel (parquet/csv)")
    ap.add_argument("--column", default=None, help="strategy return column (else auto)")
    ap.add_argument(
        "--factor-columns",
        default=None,
        help="comma-separated factor columns to use (else all numeric columns)",
    )
    ap.add_argument(
        "--t-threshold",
        type=float,
        default=2.0,
        help="min one-sided HAC t-stat on alpha to PASS (default 2.0)",
    )
    ap.add_argument(
        "--lags",
        type=int,
        default=None,
        help="HAC lags (default: Newey-West auto, floor(4*(n/100)^(2/9)))",
    )
    ap.add_argument(
        "--min-obs",
        type=int,
        default=60,
        help="minimum overlapping observations to trust the regression",
    )
    args = ap.parse_args(argv)

    import pandas as pd

    sdf = _read_frame(args.returns)
    fdf = _read_frame(args.factors)
    scol = _pick_return_column(sdf, args.column)

    if args.factor_columns is not None:
        fcols = [c.strip() for c in args.factor_columns.split(",") if c.strip()]
        missing = [c for c in fcols if c not in fdf.columns]
        if missing:
            raise SystemExit(f"factor columns {missing} not in {list(fdf.columns)}")
    else:
        fcols = list(fdf.select_dtypes("number").columns)

    # An empty factor list — whether explicitly passed ("--factor-columns ,") or the
    # (unlikely) auto-detect fallback finding zero numeric columns — is NOT a valid
    # "no factors" case for THIS gate: an intercept-only fit can pass on raw mean
    # return alone, which is exactly the beta-in-disguise failure the gate exists
    # to catch. Refuse it outright rather than silently running a degenerate fit.
    if not fcols:
        raise SystemExit(
            "no factor columns resolved (empty --factor-columns, or the factor file has no "
            "numeric columns) — a factor decomposition needs at least one named factor; an "
            "intercept-only regression is not a decomposition and would rubber-stamp raw beta"
        )

    # Inner-join strategy + factors on their common dates, then drop any row with a
    # missing value so the design matrix is complete. This trims (never pads) the
    # sample — a factor panel that starts later just shortens n_obs.
    joined = pd.concat([sdf[[scol]].rename(columns={scol: "__y__"}), fdf[fcols]], axis=1)
    joined = joined.dropna()

    y = joined["__y__"].to_numpy(dtype=float)
    F = joined[fcols].to_numpy(dtype=float)

    reg = _round_reg(factor_regression(y, F, fcols, lags=args.lags))

    # Gate 1 — residual (Jensen's) alpha significantly > 0.
    alpha_pass = bool(
        reg["alpha"] is not None
        and reg["alpha_tstat"] is not None
        and reg["alpha"] > 0
        and reg["alpha_tstat"] >= args.t_threshold
    )
    # Gate 2 — enough overlapping data to trust the decomposition at all.
    obs_pass = bool(reg["n_obs"] >= args.min_obs)

    if reg["alpha_tstat"] is None:
        note = "degenerate regression (too few obs or collinear factors) — cannot decompose"
    elif not obs_pass:
        note = f"too few overlapping obs ({reg['n_obs']} < {args.min_obs})"
    elif alpha_pass:
        note = "residual alpha significant > 0 after factor controls — plausibly novel edge"
    else:
        note = "no significant residual alpha — return explained by factor exposure (FLAG)"

    out = {
        **reg,
        "t_threshold": args.t_threshold,
        "alpha_pass": alpha_pass,
        "min_obs": args.min_obs,
        "obs_pass": obs_pass,
        # Gate passes only when there is a significant residual edge on enough data.
        "gate_pass": bool(alpha_pass and obs_pass),
        "note": note,
    }
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

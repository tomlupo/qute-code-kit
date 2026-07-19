#!/usr/bin/env python3
"""Genuine Deflated Sharpe Ratio (DSR) gate — reports across a RANGE of n_trials.

DSR (Bailey & López de Prado, 2014) tests whether an observed Sharpe ratio
still looks skillful once you deflate for (a) the shape of the actual return
distribution — skew and kurtosis inflate/deflate the variance of the Sharpe
estimator (Mertens correction) — and (b) how many trials/configs were tried
before this one was picked (the expected-max-Sharpe benchmark over
``n_trials``). Both terms are load-bearing; omitting either is not DSR, it is
a plain Sharpe-significance test wearing a DSR label.

  PROVENANCE: ported verbatim from quantbox-lab's corrected dsr-gate.py
  (branch quark/fix-dsr-gate, commit b392073, 2026-07-19). That fix replaced
  a prior version which computed t = sharpe * sqrt(n_years) against a
  Bonferroni-corrected NORMAL null — i.e. silently assumed zero skew/kurtosis
  and used leading-order (not exact) deflation. Verified false-PASS band at
  N=20 trials: an old-style z-stat in [3.1, 3.6] passed the old gate while
  the true DSR sat at 0.88-0.95 — BELOW the 0.95 acceptance bar.

  RANGE CONVENTION (adopted here, not present in the original single-N gate):
  a single n_trials count is almost never an honest, uncontested number — the
  true trial count depends on how you bound "the search" (this exact config
  sweep? every variant ever tried? every hypothesis in the vault?). Reporting
  DSR at ONE n_trials lets the number hinge entirely on that judgment call.
  Instead this gate reports DSR across a RANGE (default 1,5,10,20,50,100 —
  quantbox-lab's scripts/analysis/carver_prelive_gauntlet.py convention) and
  takes the gate PASS/FAIL decision from the CONSERVATIVE (highest n_trials,
  i.e. most-deflated, lowest-DSR) end of that range. A strategy that only
  clears the gate at n_trials=1 is not a strategy that clears the gate.

The math itself lives in lib/dsr.py (import-shared with quantbox-lab's
scripts/analysis/carver_prelive_gauntlet.py) — this file is CLI plumbing
only: parse args, load returns, call the shared function once per n_trials
in the range, apply the acceptance threshold at the conservative end, print
JSON.

Two ways to provide input — pick ONE:

  1. --returns <file>   (RECOMMENDED, the only way to get genuine DSR)
     A CSV or Parquet file with a single numeric column of PER-PERIOD
     returns (e.g. daily). Skew, kurtosis, T, and the per-period Sharpe are
     all computed from the actual data — no assumptions.

       dsr-gate.py --returns returns.csv --n-trials 1,5,10,20,50,100 --periods 365

  2. --sharpe/--skew/--kurtosis/--n-obs   (summary-stats path)
     For when you don't have the raw return series but DO have its moments
     (e.g. from a report). ALL FOUR are required together — there is no
     silent default for skew/kurtosis. Passing --sharpe alone without
     --skew/--kurtosis is refused: a Sharpe number alone cannot produce a
     real DSR, and defaulting skew=0/kurtosis=3 would silently degrade this
     back into the old normal-null bug.

       dsr-gate.py --sharpe 0.42 --skew -0.3 --kurtosis 5.1 --n-obs 1278 \\
                    --n-trials 1,5,10,20,50,100 --periods 365

In both paths, --sharpe/--sr-annualized in the JSON output are ANNUALISED
for readability; the DSR test itself runs on per-period units internally
(lib/dsr.py).

Prints JSON: {sr_period, sr_annualized, T, n_years, skew, kurtosis,
by_n_trials: {n_trials: {sr_std, sr0_annualized, z, psr_vs_zero, dsr}, ...},
n_trials_conservative, dsr_conservative, threshold, dsr_pass}.
``dsr_pass`` is decided ONLY from the conservative (max n_trials) entry.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from dsr import deflated_sharpe_ratio, deflated_sharpe_ratio_from_returns  # noqa: E402

DEFAULT_N_TRIALS_RANGE = "1,5,10,20,50,100"


def _parse_n_trials_range(raw: str) -> list[int]:
    """Parse a comma-separated n_trials range; every entry must be a positive int."""
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        raise ValueError(f"--n-trials must not be empty, got {raw!r}")
    out: list[int] = []
    for p in parts:
        try:
            n = int(p)
        except ValueError as e:
            raise ValueError(
                f"--n-trials entries must be integers, got {p!r} in {raw!r}"
            ) from e
        if n <= 0:
            raise ValueError(
                f"--n-trials entries must be positive, got {n!r} in {raw!r} "
                "(no multiple-testing penalty removal)"
            )
        out.append(n)
    return out


def _load_returns_column(path: str):
    import pandas as pd

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"returns file not found: {path}")
    if p.suffix.lower() == ".parquet":
        df = pd.read_parquet(p)
    else:
        df = pd.read_csv(p)

    if df.shape[1] == 1:
        col = df.iloc[:, 0]
    else:
        candidates = [
            c for c in df.columns if str(c).lower() in ("return", "returns", "ret", "r")
        ]
        if not candidates:
            raise ValueError(
                f"returns file has {df.shape[1]} columns and none is named "
                f"'return'/'returns'/'ret'/'r' — ambiguous, refusing to guess: {list(df.columns)}"
            )
        col = df[candidates[0]]
    return col.astype(float)


def _by_n_trials(
    *,
    n_trials_range: list[int],
    sr_period_of,
    T: int,
    skew: float,
    kurtosis: float,
    periods: int,
):
    """Compute the DSR result at each n_trials in the range. sr_period_of is a callable
    T -> sr for the summary path parity, but here sr_period is fixed — kept simple:
    caller passes the already-computed per-period sr via sr_period_of() returning it.
    """
    ann = math.sqrt(periods)
    sr_period = sr_period_of
    by_n: dict[int, dict] = {}
    for n in n_trials_range:
        res = deflated_sharpe_ratio(
            sr=sr_period, T=T, skew=skew, kurtosis=kurtosis, n_trials=n
        )
        by_n[n] = {
            "sr_std": round(res.sr_std, 6),
            "sr0_annualized": round(res.sr0_period * ann, 4),
            "z": round(res.z, 4),
            "psr_vs_zero": round(res.psr_vs_zero, 6),
            "dsr": round(res.dsr, 6),
        }
    return by_n


def run_from_returns(args) -> dict:
    if args.periods <= 0:
        raise ValueError(f"--periods must be positive, got {args.periods!r}")
    n_trials_range = _parse_n_trials_range(args.n_trials)

    returns = _load_returns_column(args.returns)
    # Compute T/skew/kurtosis/sr_period once from the data (n_trials-independent),
    # then sweep n_trials through the shared deflated_sharpe_ratio() function.
    seed = deflated_sharpe_ratio_from_returns(returns, n_trials=n_trials_range[0])
    n_years = seed.T / args.periods
    by_n = _by_n_trials(
        n_trials_range=n_trials_range,
        sr_period_of=seed.sr_period,
        T=seed.T,
        skew=seed.skew,
        kurtosis=seed.kurtosis,
        periods=args.periods,
    )
    return _to_output(
        seed, by_n=by_n, n_years=n_years, periods=args.periods, threshold=args.threshold
    )


def run_from_summary(args) -> dict:
    if args.periods <= 0:
        raise ValueError(f"--periods must be positive, got {args.periods!r}")
    n_trials_range = _parse_n_trials_range(args.n_trials)
    if args.n_obs <= 1:
        raise ValueError(f"--n-obs must be > 1, got {args.n_obs!r}")
    if not math.isfinite(args.sharpe):
        raise ValueError(f"--sharpe must be finite, got {args.sharpe!r}")

    sr_period = args.sharpe / math.sqrt(args.periods)  # annualised -> per-period
    seed = deflated_sharpe_ratio(
        sr=sr_period,
        T=args.n_obs,
        skew=args.skew,
        kurtosis=args.kurtosis,
        n_trials=n_trials_range[0],
    )
    n_years = args.n_obs / args.periods
    by_n = _by_n_trials(
        n_trials_range=n_trials_range,
        sr_period_of=sr_period,
        T=args.n_obs,
        skew=args.skew,
        kurtosis=args.kurtosis,
        periods=args.periods,
    )
    return _to_output(
        seed, by_n=by_n, n_years=n_years, periods=args.periods, threshold=args.threshold
    )


def _to_output(
    seed, *, by_n: dict, n_years: float, periods: int, threshold: float
) -> dict:
    ann = math.sqrt(periods)
    n_conservative = max(by_n.keys())  # highest n_trials = most deflated = conservative
    dsr_conservative = by_n[n_conservative]["dsr"]
    return {
        "sr_period": round(seed.sr_period, 6),
        "sr_annualized": round(seed.sr_period * ann, 4),
        "T": seed.T,
        "n_years": round(n_years, 4),
        "skew": round(seed.skew, 4),
        "kurtosis": round(seed.kurtosis, 4),
        "by_n_trials": {str(n): v for n, v in sorted(by_n.items())},
        "n_trials_conservative": n_conservative,
        "dsr_conservative": dsr_conservative,
        "threshold": threshold,
        # Gate decision is taken ONLY from the conservative (max n_trials) end.
        "dsr_pass": bool(dsr_conservative >= threshold),
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--returns",
        type=str,
        default=None,
        help="path to a CSV/Parquet file of per-period returns",
    )
    ap.add_argument(
        "--sharpe",
        type=float,
        default=None,
        help="ANNUALISED Sharpe (summary-stats path only)",
    )
    ap.add_argument(
        "--skew",
        type=float,
        default=None,
        help="per-period return skew (summary-stats path only, REQUIRED with --sharpe)",
    )
    ap.add_argument(
        "--kurtosis",
        type=float,
        default=None,
        help="per-period non-excess kurtosis, i.e. 3.0=normal (summary-stats path only, REQUIRED with --sharpe)",
    )
    ap.add_argument(
        "--n-obs",
        type=int,
        default=None,
        help="number of return observations (summary-stats path only, REQUIRED with --sharpe)",
    )
    ap.add_argument(
        "--n-trials",
        type=str,
        default=DEFAULT_N_TRIALS_RANGE,
        help=(
            "comma-separated n_trials range to report DSR across (default "
            f"'{DEFAULT_N_TRIALS_RANGE}', carver_prelive_gauntlet.py convention). "
            "The gate decision is taken from the MAX (most conservative) value."
        ),
    )
    ap.add_argument(
        "--periods", type=int, default=365, help="periods per year (quantbox uses 365)"
    )
    ap.add_argument(
        "--threshold",
        type=float,
        default=0.95,
        help="DSR acceptance threshold (default 0.95, Bailey/López de Prado)",
    )
    args = ap.parse_args(argv)

    if args.returns is not None:
        extra = [
            n
            for n in ("sharpe", "skew", "kurtosis", "n_obs")
            if getattr(args, n) is not None
        ]
        if extra:
            ap.error(
                f"--returns is mutually exclusive with summary-stats args: {extra}"
            )
        out = run_from_returns(args)
    elif args.sharpe is not None:
        missing = [n for n in ("skew", "kurtosis", "n_obs") if getattr(args, n) is None]
        if missing:
            ap.error(
                f"--sharpe requires --{', --'.join(missing)} too — DSR needs the return "
                "distribution's actual moments; there is no default skew/kurtosis "
                "(that was the old bug). Provide them explicitly, or use --returns instead."
            )
        out = run_from_summary(args)
    else:
        ap.error(
            "provide either --returns <file>, or --sharpe together with --skew/--kurtosis/--n-obs"
        )

    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (ValueError, FileNotFoundError) as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        raise SystemExit(2) from e

"""audit_score — reusable helpers to AUDIT a benchmark-anchored (benchmark=50) score.

Three primitives behind the fund-scoring-audit method:
  decompose() — split each fund's score_evo into score_i / score_B / σ_g / n / flag,
                so you judge the CAUSE (easy benchmark? thin σ? real?) not the level.
  factor_fit()— regress a fund's returns on factor series (a rate/bond index → duration
                beta; equity vs bond → equity-weight; a region/style ETF → that tilt).
                For region/style disambiguation prefer UNIVARIATE corr_gate — regional
                indices are ~0.9 collinear so joint betas are unstable.
  corr_gate() — 3Y weekly-return ρ of a fund to a CANDIDATE anchor vs the INCUMBENT;
                adopt the candidate only if ρ(candidate) ≥ ρ(incumbent).

Universe-agnostic; the LOADER SEAM below is the dm-evo/PLN reference — repoint it to
your own score table + returns panel + benchmark series and the analysis is unchanged.

Usage:  python audit_score.py CODE [CODE ...]      # audit named funds
        python audit_score.py --top 10             # audit the universe extremes
        python audit_score.py --bottom 10
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ---- LOADER SEAM (dm-evo/PLN reference — repoint these for another universe) --------
HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "output"  # score table dir; adapt
DATA = HERE.parent / "data"  # snapshot ETF/index benchmarks not in the registry; adapt
DM = HERE.parents[4] / "dm-evo"  # adapt or set via env
SCORE_TABLE = OUT / "score_evo_experiment.parquet"  # per-fund score_i/score_B/σ/evo/flag
WEEKS_3Y = 156


def _load_scores() -> pd.DataFrame:
    return pd.read_parquet(SCORE_TABLE)


def _weekly() -> pd.DataFrame:
    """Wide weekly-return panel: fund prices + registry + snapshot benchmark series."""
    px = pd.read_parquet(DM / "data/processed/fund_prices/fund_prices.parquet", columns=["code", "date", "price"])
    px["date"] = pd.to_datetime(px["date"])
    w = px.pivot_table(index="date", columns="code", values="price", aggfunc="last").sort_index()
    sig = pd.read_parquet(DM / "data/processed/tactical-signals/signals_data.parquet")
    sig.index = pd.to_datetime(sig.index)
    both = w.join(sig, how="outer").sort_index()
    # snapshot ETF/index benchmarks not in the registry (ashr, cwb, cash, gdx, …):
    # each parquet is (date, TICKER) — needed to correlation-gate a candidate anchor.
    if DATA.exists():
        for p in sorted(DATA.glob("*.parquet")):
            df = pd.read_parquet(p)
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
                for col in [c for c in df.columns if c != "date"]:
                    both[col] = df.set_index("date")[col].reindex(both.index, method="ffill")
    return both.resample("W-FRI").last().pct_change()


# ------------------------------------------------------------------------------------


def decompose(codes=None, top=None, bottom=None) -> pd.DataFrame:
    """Pull the parts that explain the level. Sort handles --top/--bottom."""
    s = _load_scores()
    s = s[s["score_evo"].notna()].copy()
    if codes:
        s = s[s["code"].isin(codes)]
    elif top:
        s = s.sort_values("score_evo", ascending=False).head(top)
    elif bottom:
        s = s.sort_values("score_evo").head(bottom)
    cols = [
        c
        for c in ("code", "name", "final_group", "score_i", "score_B", "sigma_g", "score_evo", "flag")
        if c in s.columns
    ]
    return s[cols]


def factor_fit(code: str, factors: list[str], rets: pd.DataFrame | None = None) -> dict:
    """OLS betas of a fund's 3Y weekly returns on factor series (duration / equity-weight
    / region proxies) + realized ann return & vol. A high rate-index beta ⇒ long duration;
    equity-vs-bond beta ⇒ equity weight. For region/style prefer univariate corr_gate
    (regional indices are collinear → joint betas unstable)."""
    rets = _weekly() if rets is None else rets
    cols = [f for f in factors if f in rets.columns]
    d = rets[[code, *cols]].dropna().tail(WEEKS_3Y)
    if len(d) < 60:
        return {"code": code, "n": len(d), "note": "insufficient history"}
    X = np.column_stack([np.ones(len(d))] + [d[f].values for f in cols])
    beta = np.atleast_1d(np.linalg.lstsq(X, d[code].values, rcond=None)[0])
    out = {
        "code": code,
        "n": len(d),
        "ann_ret": (1 + d[code]).prod() ** (52 / len(d)) - 1,
        "vol": d[code].std() * np.sqrt(52),
    }
    for f, b in zip(cols, np.atleast_1d(beta[1:]), strict=True):
        out[f"beta_{f}"] = float(b)
    return out


def corr_gate(code: str, candidate: str, incumbent: str, rets: pd.DataFrame | None = None) -> dict:
    """Adopt `candidate` anchor only if its 3Y weekly-return ρ to the fund ≥ ρ(incumbent)."""
    rets = _weekly() if rets is None else rets
    d = rets[[code, candidate, incumbent]].dropna().tail(WEEKS_3Y)
    r_c, r_i = d[code].corr(d[candidate]), d[code].corr(d[incumbent])
    return {
        "code": code,
        f"rho_{candidate}": round(r_c, 3),
        f"rho_{incumbent}": round(r_i, 3),
        "verdict": "ADOPT candidate" if r_c >= r_i else "KEEP incumbent",
        "n": len(d),
    }


if __name__ == "__main__":
    args = sys.argv[1:]
    pd.set_option("display.width", 200, "display.max_colwidth", 50)
    if args and args[0] == "--top":
        print(decompose(top=int(args[1])).to_string(index=False))
    elif args and args[0] == "--bottom":
        print(decompose(bottom=int(args[1])).to_string(index=False))
    elif args:
        print(decompose(codes=args).to_string(index=False))
    else:
        print(__doc__)

"""Single-benchmark attribution test — R² of each member vs its group benchmark.

Method step [2] of the fund-classification skill, and the *added* test beyond
return-coherence (cohesion.py). Cohesion asks "do members move together"; this
asks the separate Morningstar-style question "can ONE assigned benchmark
attribute ALL members" — a group can be internally coherent yet collectively
mis-benchmarked (high intra-ρ, low R² to the assigned ETF).

For each group it regresses every member's periodic return on the group's
assigned benchmark series and collects R² per fund, then crosses benchmark-fit
(median R²) with cohesion (median intra-group ρ) into a quadrant that routes
the fix:

    high ρ + low R²  -> WRONG BENCHMARK  (group coherent; re-benchmark)
    low  ρ + low R²  -> SPLIT CANDIDATE  (decompose)
    high ρ + high R² -> HEALTHY
    (cash/mandate-defined groups are exempt — R²≈0 is expected, not a violation)

Governance: AUGMENT / propose-to-human. Output is evidence for advisor review.

CAVEAT (see SKILL.md "Single-currency R² conflation" trap): R² is computed in
ONE risk currency (PLN here); a low value conflates a wrong benchmark, a
hedge-denomination mismatch, and genuine active dispersion. Never declare a
violation on R² alone — use the coherence cross-check, and re-run per hedge
denomination before splitting an FI/mixed group.

Reads (from sibling dm-evo, gitignored there — not packaged):
  - data/processed/fund_prices/fund_prices.parquet   (NAV history; superset incl. benchmark ETFs)
  - data/processed/etf_prices/fx_to_usd.parquet      (USD per unit of EUR/GBP/PLN)
  - config/reference/fund_mapping.csv                (layer1/layer2)
  - config/reference/benchmark_map.csv               (L2 -> benchmark ETF, weighted)

Writes (this dir's output/, gitignored):
  - benchmark_fit_by_fund.csv    per fund: R² vs assigned benchmark
  - benchmark_fit_by_group.csv   per L2: median/min R², %<floor, coherence, quadrant

Adapting to a new universe: change only the loader seam — load_prices / load_fx
/ load_labels / load_benchmark_map and the WINDOW / currency constants below.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

# --- config / loader seam ---
DM = Path(os.environ.get("DM_EVO_ROOT") or (Path(__file__).resolve().parents[5] / "dm-evo"))
OUT = Path(__file__).resolve().parent / "output"
OUT.mkdir(exist_ok=True)

WEEKLY_WINDOW = 156  # ~3y of W-FRI observations
MIN_OBS = 104  # >=2y of weekly returns to score a fund
RISK_CCY = "PLN"  # investor risk currency; funds+benchmarks converted to this
GROUP_COL = "layer2"  # benchmark_map is keyed on L2
COH_HI = 0.60  # coherence threshold for the quadrant

# per-asset-class R² floors — FI naturally lower vs a single govt/agg ETF
FLOORS = {"FI": 0.30, "MIX": 0.40, "_default": 0.50}


def floor_for(layer1: str) -> float:
    if isinstance(layer1, str):
        if layer1.startswith("FI"):
            return FLOORS["FI"]
        if layer1.startswith("MIX") or "MIXED" in layer1.upper():
            return FLOORS["MIX"]
    return FLOORS["_default"]


def load_labels() -> pd.DataFrame:
    m = pd.read_csv(DM / "config/reference/fund_mapping.csv")
    m = m[m.get("source", "") == "taxonomy_v4"] if "source" in m else m  # real funds
    lab = m.set_index("code")[["layer1", "layer2"]].dropna(subset=["layer2"])
    # dm-evo renamed fund_master.csv -> instrument_master.csv (v0.11.0); try the
    # new name first, fall back to the old so this runs against any dm-evo ref.
    master = DM / "config/reference/instrument_master.csv"
    if not master.exists():
        master = DM / "config/reference/fund_master.csv"
    try:
        fm = pd.read_csv(master)
        ncol = next((c for c in fm.columns if c.lower() in ("name", "fundname", "fund_name")), None)
        ccol = next((c for c in fm.columns if c.lower() in ("code", "fundcode", "fund_code")), None)
        if ncol and ccol:
            lab = lab.join(fm.set_index(ccol)[ncol].rename("name"))
    except FileNotFoundError:
        pass
    if "name" not in lab:
        lab["name"] = pd.NA
    return lab


def load_benchmark_map() -> dict[str, list[tuple[str, float]]]:
    bm = pd.read_csv(DM / "config/reference/benchmark_map.csv")
    bm = bm[bm.level == "L2"]
    return {k: list(zip(g.benchmark_code, g.weight, strict=False)) for k, g in bm.groupby("code")}


def load_fx() -> pd.DataFrame:
    fx = pd.read_parquet(DM / "data/processed/etf_prices/fx_to_usd.parquet")
    fx["USD"] = 1.0
    return fx


# NAV history + per-code currency, loaded once and reused
_PX = pd.read_parquet(
    DM / "data/processed/fund_prices/fund_prices.parquet",
    columns=["code", "date", "price", "currency"],
).dropna(subset=["price"])
_CCY = _PX.drop_duplicates("code").set_index("code")["currency"]
_FX = load_fx()


def weekly_returns(codes: list[str]) -> pd.DataFrame:
    """Weekly W-FRI log returns for `codes`, converted to RISK_CCY (funds x weeks)."""
    sub = _PX[_PX.code.isin(codes)]
    px = sub.pivot_table(index="date", columns="code", values="price", aggfunc="last").sort_index()
    fxw = _FX.reindex(px.index, method="ffill")
    risk = fxw[RISK_CCY]
    for c in px.columns:
        cur = _CCY.get(c, "USD")
        if cur not in fxw.columns:
            px[c] = np.nan  # unsupported currency -> drop from panel
            continue
        px[c] = px[c] * fxw[cur] / risk  # ccy -> USD -> RISK_CCY
    wk = px.resample("W-FRI").last().iloc[-(WEEKLY_WINDOW + 1) :]
    return np.log(wk).diff().iloc[1:]


def r2(a: pd.Series, b: pd.Series) -> float:
    pair = pd.concat([a, b], axis=1).dropna()
    if len(pair) < MIN_OBS:
        return np.nan
    r = pair.iloc[:, 0].corr(pair.iloc[:, 1])
    return float(r * r) if pd.notna(r) else np.nan


def quadrant(median_r2: float, coherence: float, floor: float, cash: bool) -> str:
    if cash:
        return "cash / mandate-defined (R2 test N/A)"
    if pd.isna(median_r2) or pd.isna(coherence):
        return "unscored"
    fit_ok, coh_ok = median_r2 >= floor, coherence >= COH_HI
    if coh_ok and fit_ok:
        return "healthy"
    if coh_ok and not fit_ok:
        return "wrong benchmark"
    if fit_ok:
        return "loose but benchmark holds"
    return "split candidate"


def main() -> None:
    lab = load_labels()
    bench_of = load_benchmark_map()

    # benchmark return panel (all referenced ETF codes, in RISK_CCY)
    bcodes = sorted({bc for parts in bench_of.values() for bc, _ in parts})
    bench_rets = weekly_returns(bcodes)

    def blended(l2: str):
        parts = bench_of.get(l2)
        if not parts:
            return None, None
        cols = [bc for bc, _ in parts if bc in bench_rets.columns]
        if not cols:
            return None, "+".join(bc for bc, _ in parts)
        w = np.array([wt for bc, wt in parts if bc in bench_rets.columns], float)
        w /= w.sum()
        label = "+".join(f"{bc}*{wt:g}" if wt != 1 else bc for bc, wt in parts)
        return (bench_rets[cols] * w).sum(axis=1, min_count=1), label

    funds = [c for c in lab.index if c in set(_PX.code.unique())]
    frets = weekly_returns(funds)
    frets = frets[[c for c in frets.columns if frets[c].notna().sum() >= MIN_OBS]]

    # ---- per-fund R² ----
    rows = []
    for code in frets.columns:
        l1, l2 = lab.loc[code, "layer1"], lab.loc[code, "layer2"]
        bser, blabel = blended(l2)
        val = r2(frets[code], bser) if bser is not None else np.nan
        rows.append(
            {
                "code": code,
                "name": lab.loc[code, "name"],
                "layer1": l1,
                "layer2": l2,
                "benchmark": blabel,
                "r2": None if pd.isna(val) else round(val, 4),
                "floor": floor_for(l1),
            }
        )
    fund_df = pd.DataFrame(rows)
    fund_df.to_csv(OUT / "benchmark_fit_by_fund.csv", index=False)

    # ---- per-group aggregation + quadrant ----
    grp_rows = []
    for l2, g in fund_df.groupby("layer2"):
        r2s = g["r2"].dropna().astype(float)
        codes = [c for c in g.code if c in frets.columns]
        coh = np.nan
        if len(codes) >= 2:
            cm = frets[codes].corr(min_periods=MIN_OBS)
            iu = cm.where(np.triu(np.ones(cm.shape), 1).astype(bool)).stack()
            coh = float(iu.median()) if len(iu) else np.nan
        l1 = g.layer1.mode().iat[0] if len(g) else ""
        fl = floor_for(l1)
        bench = g.benchmark.iat[0]
        cash = bool(isinstance(bench, str) and "CASH" in bench)
        med = np.nan if r2s.empty else float(r2s.median())
        grp_rows.append(
            {
                "layer2": l2,
                "layer1": l1,
                "n_funds": len(g),
                "benchmark": bench,
                "median_r2": None if r2s.empty else round(med, 4),
                "min_r2": None if r2s.empty else round(float(r2s.min()), 4),
                "pct_below_floor": None if r2s.empty else round(float((r2s < fl).mean()), 4),
                "coherence_rho": None if pd.isna(coh) else round(coh, 4),
                "floor": fl,
                "quadrant": quadrant(med, coh, fl, cash),
            }
        )
    group_df = pd.DataFrame(grp_rows).sort_values("median_r2", na_position="first")
    group_df.to_csv(OUT / "benchmark_fit_by_group.csv", index=False)

    n_scored = int(fund_df.r2.notna().sum())
    print(
        f"snapshot={frets.index.max().date()}  scored={n_scored}/{len(fund_df)}  "
        f"groups={len(group_df)}  window={WEEKLY_WINDOW}w  ccy={RISK_CCY}"
    )
    print("\nquadrant counts:")
    print(group_df.quadrant.value_counts().to_string())
    print("\nworst real-benchmark groups (n>=15):")
    real = group_df[
        (~group_df.benchmark.fillna("").str.contains("CASH")) & group_df.median_r2.notna() & (group_df.n_funds >= 15)
    ]
    cols = ["layer2", "n_funds", "median_r2", "pct_below_floor", "coherence_rho", "quadrant"]
    print(real.sort_values("median_r2").head(8)[cols].to_string(index=False))
    print(f"\nwrote {OUT / 'benchmark_fit_by_fund.csv'} and {OUT / 'benchmark_fit_by_group.csv'}")


if __name__ == "__main__":
    main()

"""Benchmark-anchored segment score (benchmark=50) — prototype (task 8).

Demonstrates the NEW per-L2 'market segment' score: re-center a composite so the
group BENCHMARK lands at 50, dispersion standardized (1 std = 10 pts). Separate
from the raw within-L1 composite (which is unchanged).

  segment_score_i = clip(50 + (z_i - z_benchmark) * 10, 0, 100)

where z_* is the within-group z-score of a composite. PROTOTYPE NOTE: the
composite here is a transparent self-contained proxy (z-mean of annualized
return + Sortino + info-ratio-vs-group), computed IDENTICALLY for funds and the
benchmark-as-phantom-fund. Production swaps in dm-evo's real 4-pillar composite,
re-centered the same way. The mechanic + the key validation (benchmark vs
median: does the benchmark sit away from the peer median?) are what we test.

Benchmark series from the TAA panel (data/processed/tactical-signals/signals_data.parquet).
FX caveat: equity benchmarks are native-ccy (EQ_GL ~ USD); PLN-hedged funds vs
native is approximately right, unhedged needs PLN-conversion (flagged per group).
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

# dm-evo checkout (live data/config). DM_EVO_ROOT overrides (worktree/CI/other host);
# else the sibling dm-evo beside the lab-repo root (parents[4]).
DM = Path(os.environ.get("DM_EVO_ROOT") or (Path(__file__).resolve().parents[5] / "dm-evo"))
OUT = Path(__file__).resolve().parent / "output"
OUT.mkdir(exist_ok=True)
WINDOW, MIN_OBS = 156, 130

GROUPS = [
    {
        "label": "PL Govt Bonds (FI_PL core)",
        "sel": "PL Govt Bonds PLN",
        "bench": "TBSP",
        "kind": "level",
        "fx": "PLN — clean",
    },
    {
        "label": "PL Govt Short (FI_PL_SHORT core)",
        "sel": "PL Govt Short Term PLN",
        "bench": "WIBOR_6M",
        "kind": "cash_rate",
        "fx": "PLN — CASH synth from WIBOR",
    },
    {
        "label": "Global DM Equity (EQ_DM core)",
        "sel": "Global DM Equity",
        "bench": "EQ_GL",
        "kind": "level",
        "fx": "EQ_GL native USD ~ hedged; unhedged would need xUSDPLN",
    },
]


def weekly_returns_pln():
    sc = pd.read_parquet(
        DM / "data/processed/fund_selection/scores.parquet", columns=["code", "currency"]
    ).drop_duplicates("code")
    pln = set(sc[sc.currency == "PLN"].code)
    px = pd.read_parquet(
        DM / "data/processed/fund_prices/fund_prices.parquet", columns=["code", "date", "price"]
    ).dropna(subset=["price"])
    px = px[px.code.isin(pln)]
    wide = px.pivot_table(index="date", columns="code", values="price", aggfunc="last").sort_index()
    return np.log(wide.resample("W-FRI").last()).diff().iloc[1:]


def bench_weekly(signals: pd.DataFrame, col: str, kind: str, index) -> pd.Series:
    s = signals[col].reindex(signals.index).ffill()
    wk = s.resample("W-FRI").last()
    if kind == "level":
        r = np.log(wk).diff()
    elif kind == "cash_rate":  # annualized % -> weekly TR
        r = np.log1p((wk / 100.0) / 52.0)
    else:
        raise ValueError(kind)
    return r.reindex(index)


def metrics(r: pd.Series, group_med: pd.Series) -> dict:
    r = r.dropna()
    if len(r) < MIN_OBS:
        return {}
    ann = np.expm1(r.mean() * 52)
    downside = r[r < 0].std() * np.sqrt(52)
    sortino = (ann / downside) if downside and downside > 0 else np.nan
    excess = (r - group_med.reindex(r.index)).dropna()
    info = (excess.mean() / excess.std()) * np.sqrt(52) if excess.std() > 0 else np.nan
    return {"ann_return": ann, "sortino": sortino, "info_ratio": info}


def main():
    rets = weekly_returns_pln()
    rets = rets.iloc[-(WINDOW + 1) :]
    m = pd.read_csv(DM / "config/reference/fund_mapping.csv").set_index("code")["selection_group"]
    nm = (
        pd.read_parquet(DM / "data/processed/quotations/quotations.parquet", columns=["code", "name"])
        .drop_duplicates("code")
        .set_index("code")["name"]
        .str.replace(r"\\", "", regex=True)
    )
    signals = pd.read_parquet(DM / "data/processed/tactical-signals/signals_data.parquet")

    pd.set_option("display.width", 170, "display.float_format", lambda x: f"{x:.2f}")
    all_rows = []
    for g in GROUPS:
        funds = [c for c in m.index[m == g["sel"]] if c in rets.columns]
        sub = rets[funds].dropna(how="all")
        group_med = sub.median(axis=1)
        bench_r = bench_weekly(signals, g["bench"], g["kind"], sub.index)

        # composite metric per fund + benchmark
        feat = {c: metrics(sub[c], group_med) for c in funds}
        feat = {c: v for c, v in feat.items() if v}
        bm = metrics(bench_r, group_med)
        F = pd.DataFrame(feat).T
        cols = ["ann_return", "sortino", "info_ratio"]
        # z-score within group; benchmark z vs the same fund mean/std
        mu, sd = F[cols].mean(), F[cols].std()
        Z = (F[cols] - mu) / sd
        comp = Z.mean(axis=1)
        bm_z = pd.Series({k: (bm[k] - mu[k]) / sd[k] for k in cols}).mean()
        seg = (50 + (comp - bm_z) * 10).clip(0, 100)

        med_comp = comp.median()
        med_seg = float(np.clip(50 + (med_comp - bm_z) * 10, 0, 100))
        pct_beat = float((seg > 50).mean() * 100)

        print(f"\n{'=' * 84}\n{g['label']}  | benchmark={g['bench']}  | n={len(F)}  | {g['fx']}\n{'=' * 84}")
        print(
            f"  benchmark ann_return={bm['ann_return']:.2%}  sortino={bm['sortino']:.2f}  info_ratio={bm['info_ratio']:.2f}"
        )
        print(f"  benchmark z-vs-funds = {bm_z:+.2f} std  ->  benchmark segment score = 50.0 (anchor)")
        print(f"  MEDIAN fund segment score = {med_seg:.1f}   (= the benchmark-vs-median test)")
        print(f"  funds beating benchmark (segment>50): {pct_beat:.0f}%")
        tbl = pd.DataFrame({"segment_score": seg.round(1), "ann_return": F["ann_return"], "sortino": F["sortino"]})
        tbl["name"] = [str(nm.get(c, ""))[:32] for c in tbl.index]
        tbl = tbl.sort_values("segment_score", ascending=False)
        print("\n  top 3:\n" + tbl.head(3).to_string())
        print("  bottom 3:\n" + tbl.tail(3).to_string())
        for c in tbl.index:
            all_rows.append({"group": g["sel"], "code": c, "segment_score": tbl.loc[c, "segment_score"]})

    pd.DataFrame(all_rows).to_csv(OUT / "segment_scores_demo.csv", index=False)
    print(f"\n{'=' * 84}\nINTERPRETATION")
    print("  median fund segment < 50  => benchmark beats the typical active fund (anchor is informative)")
    print("  median fund segment ~ 50  => benchmark ~ peer median (re-centering ~ today's median anchor)")
    print(f"\nwrote {OUT}/segment_scores_demo.csv")


if __name__ == "__main__":
    main()

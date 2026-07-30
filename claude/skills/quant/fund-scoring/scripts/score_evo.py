"""score_evo — benchmark-anchored calibrated fund score within the new L2 grouping.

Design: docs/superpowers/specs/2026-06-02-score-evo-design.md (decisions D1-D9).

    score_evo(i) = clip( 50 + (score_i - score_B,g) / max(sigma_g, SIGMA_FLOOR) * MULT, 0, 100 )

- score_i   : production composite from scores.parquet, UNCHANGED.
- score_B,g : group g's benchmark composite, computed Option-1 (project the
              benchmark onto the FUNDS-ONLY L1 cohort z-stats; funds untouched).
- sigma_g   : std of score_i across funds in the new-L2 group g.
- MULT=15   : 1 within-group std = 15 pts.  SIGMA_FLOOR=5.0 pts.

Anchor = a FRESHLY computed cross-section (prod_scoring.compute_fresh_scores,
cached to output/fresh_detail.parquet) at the latest properly-scoreable W-FRI
(2026-05-22). That date is 4-PILLAR (pillar_ml populated), so score_B blends
pillars_4p. Cohort z-stats come from the fresh detail's own raw indicators
(Gate A verifies our z-reproduction matches the detail's z columns).

Benchmarks are CURRENCY-AGNOSTIC (decision): a PLN fund (hedged or unhedged) is
compared directly to its native-currency ETF benchmark — no FX conversion.

Benchmark ML pillar = ML-NEUTRAL (group-median fund pillar_ml). The model's
rank/label features (rank_pct, rank_accel, q1_freq_12m, category_enc) are
ill-posed for a non-fund benchmark; the 0.10-weight ML term is bounded (see
report). v1 = latest date, PLN-only, long-history TAA-registry benchmarks.
"""

from __future__ import annotations

import sys
import os
from pathlib import Path

import numpy as np
import pandas as pd

DM = Path(os.environ.get("DM_EVO_ROOT") or Path(__file__).resolve().parents[3] / "dm-evo")
sys.path.insert(0, str(DM))
OUT = Path(__file__).resolve().parent / "output"
OUT.mkdir(exist_ok=True)

from src.fund_scoring.config_loader import load_scoring_config  # noqa: E402
from src.fund_scoring.features import (  # noqa: E402
    hit_rate,
    info_ratio,
    profit_factor,
    sortino,
    spread_ratio,
    total_return,
)
from src.fund_scoring.frequency import WEEKLY  # noqa: E402

# --- tunables (D7) ---
MULT = 15.0
SIGMA_FLOOR = 5.0

_CFG = load_scoring_config()
# Fresh 2026-05-22 anchor is 4-PILLAR (918/932 funds carry pillar_ml), so score_B
# blends pillars_4p. The benchmark ML pillar is set ML-NEUTRAL (group-median);
# tactical pillars are projected from the cohort z-stats.
_W = _CFG["pillars_4p"]  # mom .50 / cons .20 / qual .20 / ml .10

MOM = [
    "total_return_6m",
    "total_return_9m",
    "total_return_12m",
    "spread_ratio_6m",
    "spread_ratio_9m",
    "spread_ratio_12m",
]
CON = ["info_ratio_12m", "info_ratio_24m", "info_ratio_36m", "hit_rate_12m", "hit_rate_24m", "hit_rate_36m"]
QUA = ["sortino_12m", "sortino_24m", "sortino_36m", "profit_factor_12m", "profit_factor_24m", "profit_factor_36m"]
IND_ALL = MOM + CON + QUA

# --- benchmark resolution (D6: long-history TAA-registry series) ---
# group -> (registry series, kind). kind: level | cash_rate | blend.
# blend value = list of (series, weight). status absent => anchored.
NO_ANCHOR = {
    "Specialist Equity",
    "EQ_DM Other",
    "Specialist EM Equity",
    "EQ_EM Other",
    "PL Other Bonds",
    "FI_GL Other",
    "[FI_GL] Global Govt Bonds PLN",
    "[FI_GL] Global Short Duration Bonds PLN",
    "[ALT_ABS] Absolute Return",
}
BENCH = {
    "Global DM Equity": ("EQ_GL", "level"),
    "US Equity": ("EQ_US", "level"),
    "European Equity": ("EQ_EUR", "level"),
    "Technology": ("L2_TECH", "level"),
    "EM Broad Equity": ("EQ_EM", "level"),
    "PL Equity": ("WIG_TR", "level"),
    "PL Equity Small/Mid": ("L2_MWIG40", "level"),
    "Asia/China Equity": ("EQ_EM", "level"),  # FX-agnostic; broad EM (Asia-dominated), FXI too narrow
    "Gold & Mining Equity": (
        "GDX",
        "level",
    ),  # gold-miners ETF (snapshot data/gdx.parquet); registry has no miners series
    "PL Govt/Core Bonds": ("TBSP", "level"),
    "Global Core Bonds": ("FI_GL", "level"),
    "US/USD Govt Bonds": ("BM_FI_AGG", "level"),  # currency-agnostic comparison
    "IG Corporate Bonds": ("FI_IG", "level"),
    "EM Debt": ("FI_EM", "level"),
    "HY Bonds": ("FI_HY", "level"),
    "PL Govt Short": ("WIBOR_6M", "cash_rate"),
    "PL Corp Short": ("WIBOR_6M", "cash_rate"),
    "Gold": ("COM_GOLD", "level"),  # gold spot — confirmed best (rho 0.86-0.91); PLN funds lag fee-free USD phantom
    "Precious Metals": ("SLV", "level"),  # silver ETF (data/silver.parquet); group is silver-dominated (2/3 funds);
    # rho 0.85 (vs COM_GOLD 0.67, GLTR-basket 0.84). Centers silver funds within-asset; GLTR basket overstated them.
    "Commodities": ("COM_BROAD", "level"),
    "Mixed GL Flexible": ([("EQ_GL", 0.60), ("FI_GL", 0.40)], "blend"),
    "Mixed PL Flexible": ([("EQ_GL", 0.60), ("FI_GL", 0.40)], "blend"),
    "Mixed GL Conservative": ([("EQ_GL", 0.30), ("FI_GL", 0.70)], "blend"),
    "Mixed PL Conservative": ([("EQ_GL", 0.30), ("FI_GL", 0.70)], "blend"),
}


def _scale100(z: float | pd.Series) -> float | pd.Series:
    return (np.clip(z, -3, 3) + 3) / 6 * 100


def load_inputs():
    # Re-scored cross-section (rescore_new_l2.py -> output/rescored_detail.parquet):
    # funds' score_i recomputed with the NEW L2 as benchmark_category, so funds and
    # the benchmark phantom now share one peer basis (relative-metric reference
    # mismatch eliminated at the root). Run rescore_new_l2.py first.
    det = pd.read_parquet(OUT / "rescored_detail.parquet")
    det["date"] = pd.to_datetime(det["date"])
    anchor = det["date"].max()
    # Full anchor cross-section (ALL currencies) — production z-scores EQ/COM/MIX
    # categories across mixed currencies, so cohort stats need the non-PLN peers.
    det_all = det[det["date"] == anchor].copy()
    rc = pd.read_csv("output/pln_reclassification.csv")[["code", "name", "layer1", "final_group", "role"]]
    # benchmark_category each fund was scored against (final_group if >=8 PLN peers,
    # else scoring_category L1 fallback) — drives the benchmark phantom's peer set.
    bc = pd.read_parquet(OUT / "rescored_scores.parquet")[["code", "benchmark_category"]]
    det_pln = det_all[det_all["currency"] == "PLN"].merge(rc, on="code", how="inner").merge(bc, on="code", how="left")
    return det_all, det_pln, anchor


def cohort_stats(det: pd.DataFrame):
    """Per (scoring category, indicator): winsor bounds [5,95], mu, sigma of the
    winsorized fund values. Mirrors features.zscore_within_category. Returns
    nested dict cat -> ind -> (lo, hi, mu, sigma), plus a Gate-A z-reproduction
    max-abs-diff vs production's z_ columns."""
    stats: dict[str, dict[str, tuple]] = {}
    max_z_diff = 0.0
    for cat, sub in det.groupby("category"):
        if len(sub) < 3:
            continue
        stats[cat] = {}
        for ind in IND_ALL:
            raw = sub[f"raw_{ind}"]
            lo, hi = raw.quantile(0.05), raw.quantile(0.95)
            w = raw.clip(lo, hi)
            mu, sigma = w.mean(), w.std()
            stats[cat][ind] = (lo, hi, mu, sigma)
            if sigma and sigma > 0:
                z_repro = (w - mu) / sigma
                diff = (z_repro - sub[f"z_{ind}"]).abs().max()
                if pd.notna(diff):
                    max_z_diff = max(max_z_diff, diff)
    return stats, max_z_diff


def _series_to_daily_price(signals: pd.DataFrame, spec, kind: str) -> pd.DataFrame:
    """Build a daily price frame (col '__B__') for a benchmark spec."""
    idx = signals.index
    if kind == "level":
        s = signals[spec].ffill()
        px = s
    elif kind == "cash_rate":  # annualized % -> daily TR accrual -> price index
        r = signals[spec].ffill() / 100.0 / 252.0
        px = (1.0 + r.fillna(0)).cumprod()
    elif kind == "blend":
        rets = None
        for col, w in spec:
            cr = signals[col].ffill().pct_change().fillna(0) * w
            rets = cr if rets is None else rets + cr
        px = (1.0 + rets).cumprod()
    else:
        raise ValueError(kind)
    return pd.DataFrame({"__B__": px}, index=idx).dropna()


def bench_indicators(signals, fund_prices_group: pd.DataFrame, spec, kind, anchor):
    """The benchmark's 12 raw indicators at `anchor`, reusing dm-evo features.py.
    Relative metrics computed vs the new-L2 group funds (benchmark included in
    the peer frame -> ~1/(n+1) contamination, accepted for v1)."""
    bp = _series_to_daily_price(signals, spec, kind)
    bp = bp[bp.index <= anchor]
    # combined daily frame: benchmark + group funds (for relative peer set)
    fp = fund_prices_group[fund_prices_group.index <= anchor]
    comb = fp.join(bp, how="outer").sort_index()
    cat = pd.Series("G", index=comb.columns)  # one peer category for relatives

    out: dict[str, float] = {}

    def _at(df):
        if anchor in df.index:
            return df.loc[anchor, "__B__"]
        sub = df["__B__"].dropna()
        return sub.iloc[-1] if len(sub) else np.nan

    for m in (6, 9, 12):
        out[f"total_return_{m}m"] = _at(total_return(bp, m, WEEKLY))
        out[f"spread_ratio_{m}m"] = _at(spread_ratio(comb, m, cat, WEEKLY))
    for m in (12, 24, 36):
        out[f"info_ratio_{m}m"] = _at(info_ratio(comb, m, cat, WEEKLY))
        out[f"hit_rate_{m}m"] = _at(hit_rate(comb, m, cat, WEEKLY))
        out[f"sortino_{m}m"] = _at(sortino(bp, m, WEEKLY))
        out[f"profit_factor_{m}m"] = _at(profit_factor(bp, m, WEEKLY))
    return out


def project_pillars(raw: dict, cstats: dict[str, tuple], ml_neutral: float):
    """Project benchmark raw indicators onto funds-only cohort z-stats -> 4-pillar
    score_B. Benchmark ML pillar = ml_neutral (group-median; rank/label ML
    features are ill-posed for a non-fund benchmark). No-loss guard:
    profit_factor/sortino NaN (no downside) -> cap z=3."""

    def zind(ind):
        if ind not in cstats:
            return np.nan
        lo, hi, mu, sigma = cstats[ind]
        x = raw.get(ind, np.nan)
        if pd.isna(x):
            # no-loss guard for quality ratios with no downside -> top of cohort
            if ind.startswith(("sortino", "profit_factor")):
                return 3.0
            return np.nan
        if not sigma or sigma <= 0:
            return 0.0
        return (np.clip(x, lo, hi) - mu) / sigma

    def pillar(names):
        zs = [zind(n) for n in names]
        zs = [z for z in zs if pd.notna(z)]
        return _scale100(np.mean(zs)) if zs else np.nan

    mom, cons, qual = pillar(MOM), pillar(CON), pillar(QUA)
    score_b = mom * _W["momentum"] + cons * _W["consistency"] + qual * _W["quality"] + ml_neutral * _W["ml"]
    return score_b, mom, cons, qual


def main():
    det_all, det, anchor = load_inputs()
    cstats, gate_a = cohort_stats(det_all)
    print(
        f"anchor date: {anchor.date()} | PLN funds: {len(det)} | cohort funds: {len(det_all)} "
        f"| scoring cats: {len(cstats)}"
    )
    print(
        f"GATE A (z-reproduction max abs diff vs production z_): {gate_a:.4f}  -> {'PASS' if gate_a < 0.01 else 'FAIL'}"
    )

    signals = pd.read_parquet(DM / "data/processed/tactical-signals/signals_data.parquet")
    signals.index = pd.to_datetime(signals.index)
    # Snapshot benchmarks not in the TAA registry -> add as columns.
    # GDX = gold-miners (Gold & Mining Equity); SLV = silver (Precious Metals);
    # GLTR = PM-basket (alternative kept for cross-check, not the operative anchor).
    for fname, col in (("gdx.parquet", "GDX"), ("silver.parquet", "SLV"), ("pm_basket.parquet", "GLTR")):
        s = pd.read_parquet(OUT.parent / "data" / fname).set_index("date")[col]
        signals[col] = s.reindex(signals.index, method="ffill")
    # PLN fund prices (for benchmark relative-metric peer medians)
    px = pd.read_parquet(
        DM / "data/processed/fund_prices/fund_prices.parquet", columns=["code", "date", "price"]
    ).dropna(subset=["price"])
    px["date"] = pd.to_datetime(px["date"])
    px = px[px.code.isin(det.code)]
    wide = px.pivot_table(index="date", columns="code", values="price", aggfunc="last").sort_index()

    rows = []
    for grp, sub in det.groupby("final_group"):
        cat = sub["category"].mode().iat[0]
        cs = cstats.get(cat, {})
        sigma_g = sub["score"].std()
        if grp in NO_ANCHOR or grp not in BENCH:
            for _, r in sub.iterrows():
                rows.append(
                    dict(
                        code=r.code,
                        name=r["name"],
                        scoring_cat=cat,
                        final_group=grp,
                        role=r.role,
                        score_i=r.score,
                        score_B=np.nan,
                        sigma_g=sigma_g,
                        score_evo=np.nan,
                        flag="no_anchor",
                    )
                )
            continue
        spec, kind = BENCH[grp]
        ml_neutral = sub["pillar_ml"].median()
        if pd.isna(ml_neutral):
            ml_neutral = 50.0
        # Benchmark's relative metrics use the SAME peer set the group's funds were
        # scored against (their benchmark_category): the new-L2 group when >=8 PLN
        # peers, else the L1 scoring-category fallback. This keeps the phantom and the
        # funds on one relative-metric basis even for thin groups (no reintroduced
        # mismatch). Reduces to the group's own funds for the >=8 case.
        bench_cat_g = sub["benchmark_category"].mode().iat[0] if sub["benchmark_category"].notna().any() else grp
        peer_codes = [c for c in det.loc[det["benchmark_category"] == bench_cat_g, "code"] if c in wide.columns]
        if len(peer_codes) < 2:
            peer_codes = [c for c in sub.code if c in wide.columns]
        raw = bench_indicators(signals, wide[peer_codes], spec, kind, anchor)
        score_b, mom, cons, qual = project_pillars(raw, cs, ml_neutral)
        sden = max(sigma_g, SIGMA_FLOOR)
        flag = "low_confidence" if len(sub) < 8 else "ok"
        for _, r in sub.iterrows():
            evo = float(np.clip(50 + (r.score - score_b) / sden * MULT, 0, 100))
            rows.append(
                dict(
                    code=r.code,
                    name=r["name"],
                    scoring_cat=cat,
                    final_group=grp,
                    role=r.role,
                    score_i=r.score,
                    score_B=round(score_b, 2),
                    sigma_g=round(sigma_g, 2),
                    score_evo=round(evo, 1),
                    flag=flag,
                )
            )

    res = pd.DataFrame(rows)
    res.to_parquet(OUT / "score_evo.parquet", index=False)

    # --- group summary ---
    anc = res[res.score_evo.notna()]
    g = (
        anc.groupby("final_group")
        .agg(
            n=("code", "size"),
            bench_score_B=("score_B", "first"),
            sigma_g=("sigma_g", "first"),
            med_evo=("score_evo", "median"),
            max_evo=("score_evo", "max"),
            min_evo=("score_evo", "min"),
            pct_beat=("score_evo", lambda s: (s > 50).mean() * 100),
        )
        .reset_index()
        .sort_values("n", ascending=False)
    )
    pd.set_option("display.width", 160, "display.max_rows", 60, "display.float_format", lambda x: f"{x:.1f}")
    print(
        f"\nanchored groups: {res.final_group.nunique() - res[res.flag == 'no_anchor'].final_group.nunique()} "
        f"| funds scored: {anc.code.nunique()} | no_anchor: {(res.flag == 'no_anchor').sum()}"
    )
    print("\n" + g.to_string(index=False))
    print(f"\nwrote {OUT}/score_evo.parquet  ({len(res)} rows)")
    print(
        "NOTE: 4-pillar anchor; benchmarks currency-agnostic (no FX). Benchmark ML "
        "pillar = group-median (rank/label ML features ill-posed for a non-fund benchmark)."
    )


if __name__ == "__main__":
    main()

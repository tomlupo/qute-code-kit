"""score_evo_v2 — pipeline step 5b: benchmark-anchored calibrated fund score on
the FINAL (re-frozen) taxonomy, with the retrained-ML composite from step 5a.

Adapts score_evo.py to the final taxonomy. Two structural changes vs the v1 scorer:

  1. GROUPING SOURCE. v1 read the funds' selection group from
     `output/pln_reclassification.csv` (`final_group`) and the relative peer set
     from `rescored_scores.parquet` (`benchmark_category`). v2 reads BOTH from the
     single source of truth `output/experiment_grouping.parquet`
     (`selection_L2` + `benchmark_category`) and the composite from
     `output/final_scores_v2.parquet` / `final_detail_v2.parquet` (retrained ML,
     final grouping). The 6 `unrated` funds are absent from final_scores_v2 by
     construction.

  2. ANCHOR MAP. The EQ_EM anchors are repointed to the final L2 groups
     (selection_L2 -> registry series / sourced ETF):
        EM Broad Equity      -> EQ_EM   (registry; broad EM, role of EEM)
        Asia Equity          -> AAXJ    (sourced snapshot)
        China Equity         -> L2_CHINA (registry; role of FXI)
        India Equity         -> INDA    (sourced snapshot)
        Latin America Equity -> ILF     (sourced snapshot)
        Poland & CEE Equity  -> WIG_TR  (registry; role of WIG)
        PL Equity Small/Mid  -> L2_MWIG40 (registry; role of MWIG40)
     EQ_DM / FI / COM / MIX anchors are carried over from score_evo.py unchanged,
     plus two FI-cleanup anchors so every PLN FI fund scores:
        FI_GL Other          -> FI_GL   (registry; global-bond catch-all, BNDW role)
        Cash / Money Market  -> WIBOR_6M cash_rate (CASH: ETFBCASH.WA + WIBOR backfill)
     Special / Unrated has NO anchor (and is not even in the scored set).

Core math is REUSED verbatim from score_evo.py (cohort_stats, bench_indicators,
project_pillars, the Option-1 projection, the
`score_evo = clip(50 + (score_i - score_B)/max(sigma_g,5)*15, 0, 100)` formula).
Benchmarks are CURRENCY-AGNOSTIC; benchmark ML pillar = group-median (ML-neutral).

Output: output/score_evo_experiment.parquet.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# Reuse the v1 scorer's machinery verbatim (same dm-evo features.py / config).
import score_evo as v1  # noqa: E402

DM = v1.DM
OUT = Path(__file__).resolve().parent / "output"
GROUPING = OUT / "experiment_grouping.parquet"

# --- tunables (inherited) ---
MULT = v1.MULT
SIGMA_FLOOR = v1.SIGMA_FLOOR
SHRINK_K = 8  # shrinkage pseudo-count toward the scoring-category sigma (= MIN_BENCHMARK_PEERS)
SIGMA_GUARD = 3.0  # numerical guard only; the shrinkage governs thin groups
CCY_SUFFIXES = ("_PLN", "_USD", "_EUR", "_GBP")


def _is_ccy_split_cat(scat: str) -> bool:
    """FI_* / ALT_* / MIX_DEF carry a currency suffix and are scored WITHIN currency
    (carry/hedging is a persistent directional bias). EQ / COM / MIX_AGR are
    currency-MIXED — their evo cohort spans all currencies (PLN only at presentation)."""
    return str(scat).endswith(CCY_SUFFIXES)


# --- FINAL anchor map (selection_L2 -> (series, kind)) -----------------------
# EQ_EM repointed to the final L2 split; everything else carried over from
# score_evo.BENCH. kind: level | cash_rate | blend. Series resolved against the
# TAA signals registry, with sourced-ETF snapshots (GDX/SLV/AAXJ/INDA/ILF) added
# as columns (see _load_signals).
NO_ANCHOR = {
    "Special / Unrated",  # leverage/inverse/exotic — not scoreable (also pre-excluded)
    "Specialist Equity",
    "EQ_DM Other",
    "[ALT_ABS] Absolute Return",
    "Absolute Return",
    # NOTE: the FI residual labels (FI_GL Other, [FI_GL] Global Govt/Short Dur Bonds PLN,
    # PL Corp Short Term PLN, Global Core Bonds PLN, PL Govt Bonds PLN, COM_GOLD) are now
    # normalized/anchored by the FI cleanup in build_experiment_grouping.py + the
    # FI_GL Other / Cash anchors below — so they are no longer no_anchor.
}
BENCH = {
    # --- EQ_DM (carried from score_evo.py) ---
    "Global DM Equity": ("EQ_GL", "level"),
    "US Equity": ("EQ_US", "level"),
    "European Equity": ("EQ_EUR", "level"),
    "Technology": ("L2_TECH", "level"),
    "Gold & Mining Equity": ("GDX", "level"),  # snapshot data/gdx.parquet
    # --- EQ_EM (FINAL taxonomy) ---
    "EM Broad Equity": ("EQ_EM", "level"),  # registry broad EM (role of EEM)
    "Asia Equity": ("AAXJ", "level"),  # sourced snapshot data/aaxj.parquet
    "China Equity": ("L2_CHINA", "level"),  # registry China (role of FXI — offshore H-shares)
    "China A-Shares Equity": ("ASHR", "level"),  # onshore CSI 300 (data/ashr.parquet); ρ-gated
    "India Equity": ("INDA", "level"),  # sourced snapshot data/inda.parquet
    "Latin America Equity": ("ILF", "level"),  # sourced snapshot data/ilf.parquet
    "Poland & CEE Equity": ("WIG_TR", "level"),  # registry WIG total return
    "PL Equity Small/Mid": ("L2_MWIG40", "level"),  # registry mWIG40
    # --- FI (carried from score_evo.py) ---
    "PL Govt/Core Bonds": ("TBSP", "level"),
    "Global Core Bonds": ("FI_GL", "level"),
    "US/USD Govt Bonds": ("BM_FI_AGG", "level"),
    "IG Corporate Bonds": ("FI_IG", "level"),
    "EM Debt": ("FI_EM", "level"),
    "HY Bonds": ("FI_HY", "level"),
    # Convertibles carve-out (2026-06-05): anchored to CWB (convertibles ETF), NOT a
    # pure-credit index. CWB > FI_EM/FI_HY correlation-gated in fetch_cwb.py. Relative
    # peers fall back to FI_CREDIT_PLN (n=2 < MIN_BENCHMARK_PEERS). low_confidence.
    "Convertible Bonds": ("CWB", "level"),  # snapshot data/cwb.parquet
    # PL Govt Short → the realistic CASH series (dm-evo: ETFBCASH + WIBOR backfill, seam
    # 2024-01-02), NOT the fee-free WIBOR accrual — investable, small real vol (no Sortino
    # no-loss blowup). PL Corp Short stays on WIBOR cash_rate (credit, lenient hurdle).
    "PL Govt Short": ("CASH", "level"),
    "PL Corp Short": ("WIBOR_6M", "cash_rate"),
    # PL Other Bonds (advisor role=other residual: PL universal/govt/muni/corp) -> broad PL govt
    # proxy; low-confidence per its 'other' role.
    "PL Other Bonds": ("TBSP", "level"),
    # --- FI thin groups (FI CLEANUP anchors) ---
    "FI_GL Other": ("FI_GL", "level"),  # macro/specialist global bond catch-all (BNDW role)
    "Cash / Money Market": ("CASH", "level"),  # dm-evo CASH series (ETFBCASH + WIBOR backfill)
    # --- COM (carried from score_evo.py) ---
    "Gold": ("COM_GOLD", "level"),
    "Precious Metals": ("SLV", "level"),  # snapshot data/silver.parquet
    "Commodities": ("COM_BROAD", "level"),
    # --- MIX (carried from score_evo.py) ---
    # Mixed GL → GLOBAL blend (these funds hold global assets).
    "Mixed GL Flexible": ([("EQ_GL", 0.60), ("FI_GL", 0.40)], "blend"),
    "Mixed GL Balanced": ([("EQ_GL", 0.50), ("FI_GL", 0.50)], "blend"),
    "Mixed GL Conservative": ([("EQ_GL", 0.30), ("FI_GL", 0.70)], "blend"),
    # Mixed PL → POLISH blend WIG_TR/TBSP (2026-06-05). These funds hold predominantly
    # Polish assets; a global blend mis-benchmarks them (PL bonds' high-WIBOR carry beat
    # global bonds → bond-heavy PL funds beat a global blend regardless of tier, the
    # artifact that made the Balanced carve-out score ~100). WIG_TR + TBSP are registry
    # series (also the Poland & CEE / PL Govt anchors). Balanced = 50/50 tier.
    "Mixed PL Flexible": ([("WIG_TR", 0.60), ("TBSP", 0.40)], "blend"),
    "Mixed PL Balanced": ([("WIG_TR", 0.50), ("TBSP", 0.50)], "blend"),
    "Mixed PL Conservative": ([("WIG_TR", 0.30), ("TBSP", 0.70)], "blend"),
}

# Snapshot ETF series (not in the TAA registry) -> added as signal columns.
SNAPSHOTS = (
    ("gdx.parquet", "GDX"),
    ("silver.parquet", "SLV"),
    ("pm_basket.parquet", "GLTR"),
    ("aaxj.parquet", "AAXJ"),
    ("inda.parquet", "INDA"),
    ("ilf.parquet", "ILF"),
    ("cwb.parquet", "CWB"),  # convertibles anchor (Convertible Bonds L2)
    ("ashr.parquet", "ASHR"),  # onshore CSI 300 anchor (China A-Shares Equity L2)
    ("cash.parquet", "CASH"),  # dm-evo CASH series (ETFBCASH + WIBOR backfill) for PL short/cash
)


def load_inputs():
    """Final-taxonomy cross-section: funds' composite from final_detail_v2 (retrained
    ML, re-frozen grouping) + selection_L2 / benchmark_category from the single
    source of truth experiment_grouping.parquet. PLN-only for the deliverable;
    full cross-section retained for cohort z-stats (EQ/COM/MIX z across currencies)."""
    det = pd.read_parquet(OUT / "final_detail_v2.parquet")
    det["date"] = pd.to_datetime(det["date"])
    anchor = det["date"].max()
    det_all = det[det["date"] == anchor].copy()

    g = pd.read_parquet(GROUPING)[["code", "selection_L2", "benchmark_category"]]
    # detail already carries selection_L2 / benchmark_category (mapped in rescore_v2),
    # but re-join from the grouping to guarantee the single-source-of-truth labels.
    det_all = det_all.drop(columns=["selection_L2", "benchmark_category"], errors="ignore").merge(
        g, on="code", how="left"
    )
    det_all = det_all.rename(columns={"selection_L2": "final_group"})

    # name (for the sheet) — pull from the classify CSVs (union; first non-null).
    names = _load_names()
    det_all["name"] = det_all["code"].map(names).fillna(det_all["code"])

    det_pln = det_all[det_all["currency"] == "PLN"].copy()
    return det_all, det_pln, anchor


def _load_names() -> dict[str, str]:
    names: dict[str, str] = {}
    for fn in ("eqem_l1_l2_l3.csv", "eqdm_l1_l2_l3.csv", "fi_l1_l2_l3.csv", "com_l1_l2_l3.csv", "mixalt_l1_l2_l3.csv"):
        p = OUT / fn
        if not p.exists():
            continue
        df = pd.read_csv(p)
        if "name" in df.columns:
            for c, n in zip(df["code"], df["name"], strict=False):
                names.setdefault(c, n)
    return names


def _load_signals():
    signals = pd.read_parquet(DM / "data/processed/tactical-signals/signals_data.parquet")
    signals.index = pd.to_datetime(signals.index)
    for fname, col in SNAPSHOTS:
        p = OUT.parent / "data" / fname
        if not p.exists():
            continue
        s = pd.read_parquet(p).set_index("date")[col]
        signals[col] = s.reindex(signals.index, method="ffill")
    return signals


def main():
    det_all, det, anchor = load_inputs()
    cstats, gate_a = v1.cohort_stats(det_all)
    print(
        f"anchor date: {anchor.date()} | PLN funds: {len(det)} | cohort funds: {len(det_all)} "
        f"| scoring cats: {len(cstats)}"
    )
    print(
        f"GATE A (z-reproduction max abs diff vs production z_): {gate_a:.4f} -> {'PASS' if gate_a < 0.01 else 'FAIL'}"
    )

    signals = _load_signals()
    # ALL-currency fund prices: for currency-mixed cats the benchmark's relative-metric
    # peer medians must use the same cross-currency cohort the funds were scored against
    # (ccy-split benchmark_category strings self-restrict to PLN downstream).
    px = pd.read_parquet(
        DM / "data/processed/fund_prices/fund_prices.parquet", columns=["code", "date", "price"]
    ).dropna(subset=["price"])
    px["date"] = pd.to_datetime(px["date"])
    px = px[px.code.isin(det_all.code)]
    wide = px.pivot_table(index="date", columns="code", values="price", aggfunc="last").sort_index()

    rows = []
    scat_sigma = det_all.groupby("category")["score"].std()  # scoring-category dispersion (shrink target)
    for grp, sub in det.groupby("final_group"):
        cat = sub["category"].mode().iat[0]
        cs = cstats.get(cat, {})
        # evo cohort: ALL currencies for currency-mixed cats (the basis score_i was built
        # on); within-PLN for ccy-split cats (FI/ALT/MIX_DEF — carry-segmented).
        cohort = sub if _is_ccy_split_cat(cat) else det_all[det_all["final_group"] == grp]
        n_cohort = int(cohort["score"].notna().sum())
        sigma_grp = cohort["score"].std()
        # shrink the group sigma toward the (always-populous) scoring-category sigma so
        # genuinely-thin cohorts (convertibles, Gold, India) borrow a stable dispersion.
        sigma_scat = scat_sigma.get(cat, np.nan)
        if pd.notna(sigma_grp) and pd.notna(sigma_scat):
            sigma_g = (n_cohort * sigma_grp + SHRINK_K * sigma_scat) / (n_cohort + SHRINK_K)
        else:
            sigma_g = sigma_grp if pd.notna(sigma_grp) else sigma_scat
        if grp in NO_ANCHOR or grp not in BENCH:
            for _, r in sub.iterrows():
                rows.append(
                    dict(
                        code=r.code,
                        name=r["name"],
                        scoring_cat=cat,
                        final_group=grp,
                        score_i=r.score,
                        score_B=np.nan,
                        sigma_g=sigma_g,
                        score_evo=np.nan,
                        flag="no_anchor",
                    )
                )
            continue
        spec, kind = BENCH[grp]
        ml_neutral = cohort["pillar_ml"].median()
        if pd.isna(ml_neutral):
            ml_neutral = 50.0
        # Benchmark relatives use the SAME peer set the funds were scored against
        # (their benchmark_category), over ALL currencies — keeping phantom + funds on
        # one basis. ccy-split benchmark_category strings are ccy-suffixed so they
        # self-restrict to PLN; mixed bench_cat pulls the full cross-currency cohort.
        bench_cat_g = sub["benchmark_category"].mode().iat[0] if sub["benchmark_category"].notna().any() else grp
        peer_codes = [c for c in det_all.loc[det_all["benchmark_category"] == bench_cat_g, "code"] if c in wide.columns]
        if len(peer_codes) < 2:
            peer_codes = [c for c in cohort.code if c in wide.columns]
        raw = v1.bench_indicators(signals, wide[peer_codes], spec, kind, anchor)
        score_b, _mom, _cons, _qual = v1.project_pillars(raw, cs, ml_neutral)
        sden = max(sigma_g, SIGMA_GUARD)
        base_flag = "low_confidence" if n_cohort < 8 else "ok"
        for _, r in sub.iterrows():
            if pd.isna(r.score):
                # no composite (insufficient history) -> can't anchor; flag explicitly
                rows.append(
                    dict(
                        code=r.code,
                        name=r["name"],
                        scoring_cat=cat,
                        final_group=grp,
                        score_i=np.nan,
                        score_B=round(score_b, 2),
                        sigma_g=round(sigma_g, 2),
                        score_evo=np.nan,
                        flag="no_score",
                    )
                )
                continue
            evo = float(np.clip(50 + (r.score - score_b) / sden * MULT, 0, 100))
            rows.append(
                dict(
                    code=r.code,
                    name=r["name"],
                    scoring_cat=cat,
                    final_group=grp,
                    score_i=r.score,
                    score_B=round(score_b, 2),
                    sigma_g=round(sigma_g, 2),
                    score_evo=round(evo, 1),
                    flag=base_flag,
                )
            )

    res = pd.DataFrame(rows)
    res.to_parquet(OUT / "score_evo_experiment.parquet", index=False)

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
    pd.set_option("display.width", 170, "display.max_rows", 60, "display.float_format", lambda x: f"{x:.1f}")
    n_anchored = res.final_group.nunique() - res[res.flag == "no_anchor"].final_group.nunique()
    print(
        f"\nanchored groups: {n_anchored} | funds scored: {anc.code.nunique()} | "
        f"no_anchor: {(res.flag == 'no_anchor').sum()} (in {res[res.flag == 'no_anchor'].final_group.nunique()} groups)"
    )
    print("\n" + g.to_string(index=False))
    print(f"\nwrote {OUT}/score_evo_experiment.parquet  ({len(res)} rows)")


if __name__ == "__main__":
    main()

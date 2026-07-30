"""Rule-based core/satellite allocation prototype (ADR-0007).

Selection ranks on EVO Score (`score`, = score_i). Score-vs-ETF is carried as a
SOFT signal only (not a gate). Per L1: core = top EVO-Score fund tagged
alloc_role='core'; satellites = top fund per satellite L2, hard-capped (10%/5%).
Emits P1-P5 portfolios + per-L1 candidate tables + correlation matrices (for
editorial less-correlated satellite picks). Diffs vs the current-dev engine run.

Reads dm-evo PRODUCTION inputs (scores.parquet @ 2026-06-12, fund_mapping,
fund_prices) so the diff isolates the allocation logic. Read-only.
"""

from __future__ import annotations
import os
from pathlib import Path
import numpy as np
import pandas as pd

DM = Path(os.environ.get("DM_EVO_ROOT") or "/home/tom/workspace/projects/dm-evo")
OUT = Path(__file__).resolve().parent
BASE_CSV = DM / "output/portfolio-construction/weekly/2026-06-12/run_20260618/portfolio_allocation.csv"

# realized L1 budget per profile (from the current-dev engine run; respects SAA)
L1_BUDGET = {
    "P1": {"FI_PL_SHORT": 50, "FI_PL": 50},
    "P2": {"FI_PL_SHORT": 20, "FI_PL": 40, "FI_GL": 15, "FI_CREDIT": 5, "EQ_DM": 20},
    "P3": {"FI_PL_SHORT": 20, "FI_PL": 30, "FI_GL": 10, "EQ_DM": 35, "COM_GOLD": 5},
    "P4": {"FI_PL_SHORT": 10, "FI_GL": 5, "EQ_DM": 45, "EQ_EM": 30, "COM_BROAD": 10},
    "P5": {"EQ_DM": 55, "EQ_EM": 35, "COM_BROAD": 10},
}
CORE_ONLY = {"FI_PL_SHORT", "COM_GOLD", "COM_BROAD"}
ALL_SAT = {"FI_CREDIT", "ALT_CRP"}
CORE_SHARE = {"FI_PL": 0.8, "FI_GL": 0.7, "EQ_DM": 0.6, "EQ_EM": 0.6}
# Pinned core L2s per L1 (ordered; each contributes its top EVO-Score fund).
# EQ_DM = broad Global-DM core + US co-core; EQ_EM core = broad EM (NOT Asia).
# Core-eligible L2s per L1. Cores are picked by BEST EVO from this pool (one per L2 when
# the set spans multiple L2s, so EQ_DM diversifies across Blend/Style/US; same-L2 sleeves
# like FI_PL can hold 2-3 funds). No pin order — best score anchors. US is core-eligible.
CORE_ELIGIBLE = {
    "EQ_DM": {"Global Blend", "Global Style", "US"},
    "EQ_EM": {"EM Broad Equity"},
    "COM_GOLD": {"Gold (Commodity)"},  # gold, not silver/PM
}
# Fewer-funds policy: core spills across up to MAX_CORE funds (no single-fund >cap;
# 3 = handcraft territory); at most MAX_SATS satellites per sleeve, leftover budget
# spills back into the core rather than sprinkling sub-cap 5% positions.
MAX_CORE = 3
MAX_SATS = 2
# AUM/NAV floors: HARD 25mln (excluded unless explicitly overridden), SOFT 50mln
# (allowed but flagged — prefer larger). TFI house cap 35% (SOFT — yields if enforcing
# it would block the allocation, i.e. no same-sleeve alternative from another house).
AUM_HARD = 25.0
AUM_SOFT = 50.0
TFI_CAP = 35.0
# SOFT diversifier policy (rule of thumb, NOT a hard rule): a satellite correlating
# > this with an existing pick is FLAGGED as redundant and the budget is steered to a
# lower-corr alternative by default — but it is overridable (the score given up is shown).
CORR_SOFT = 0.80
PER_FUND_CAP = 20.0
SAT_CAP = 10.0
SAT_CAP_NARROW = 5.0
GRID = 5.0
NARROW_L2 = {
    "Technology Equity",
    "Clean Energy Equity",
    "Healthcare Equity",
    "Real Estate Equity",
    "Gold & Mining Equity",
    "China A-Shares Equity",
    "India Equity",
    "Latin America Equity",
    "Convertible Bonds",
    "High-Yield Bonds",
    "Sector / Thematic Equity",
    "Thematic/Sector",  # new EQ_DM L2 (narrow -> 5% cap)
    "Gold & Mining",  # new EQ_DM L2 (defensive diversifier, narrow cap)
}


def round_grid(x):
    return round(x / GRID) * GRID


def load_universe():
    sc = pd.read_parquet(DM / "data/processed/fund_selection/scores.parquet")
    sc["date"] = pd.to_datetime(sc["date"])
    sc = sc[sc["date"] == sc["date"].max()][["code", "category", "score", "currency", "benchmark_category"]]
    m = pd.read_csv(DM / "config/reference/fund_mapping.csv")
    m = m[(~m.dedup_exclude) & (~m.unrated) & (~m.horizon_selected)]
    m = m[["code", "layer1", "layer2", "alloc_role", "selection_group"]]
    u = sc.merge(m, on="code", how="inner")
    u = u[u["currency"] == "PLN"].copy()
    # instrument_master: is_evo (allocatable universe), name, tfi_company (house)
    im = pd.read_csv(DM / "config/reference/instrument_master.csv")
    evo = set(im.loc[im["is_evo"], "code"])
    u["name"] = u["code"].map(im.set_index("code")["name"])
    u["tfi"] = u["code"].map(im.set_index("code")["tfi_company"])
    n_before = len(u)
    u = u[u["code"].isin(evo)].copy()
    # AUM (PLN mln) from fund_data_evo; FX-convert non-PLN NAVs (rough spot)
    fx = {"PLN": 1.0, "USD": 4.0, "EUR": 4.3, "JPY": 0.027}
    fd = pd.read_parquet(DM / "data/processed/fund_data_evo/date=2026-06-12/part-00000.parquet")
    fd = fd[["code", "totalnetassetvalue", "totalnetassetvaluecurrency"]].dropna(subset=["totalnetassetvalue"])
    fd["aum_mln"] = fd["totalnetassetvalue"] * fd["totalnetassetvaluecurrency"].map(fx).fillna(1.0) / 1e6
    u = u.merge(fd[["code", "aum_mln"]], on="code", how="left")
    # AUM floors: HARD 25mln (drop, override-only) / SOFT 50mln (kept, flagged)
    n_evo = len(u)
    u = u[(u["aum_mln"].isna()) | (u["aum_mln"] >= AUM_HARD)].copy()
    u["aum_soft_flag"] = u["aum_mln"].notna() & (u["aum_mln"] < AUM_SOFT)
    print(
        f"is_evo: {n_before}->{n_evo} EVO | AUM hard {AUM_HARD}m: ->{len(u)} | "
        f"soft<{AUM_SOFT}m flagged: {int(u['aum_soft_flag'].sum())}"
    )
    # soft signal
    sv = pd.read_parquet(DM / "data/processed/fund_selection/score_vs_etf.parquet")
    sv = sv[sv["date"] == sv["date"].max()][["code", "score_vs_etf"]].drop_duplicates("code")
    u = u.merge(sv, on="code", how="left")
    # SRI from the engine run (already resolved)
    base = pd.read_csv(BASE_CSV)
    sri = base.drop_duplicates("code").set_index("code")["sri"]
    u["sri"] = u["code"].map(sri)
    # EQ_DM L2/L3 redesign override (2026-06-19): remap layer2/alloc_role from the
    # proposed mapping; REVIEW-flagged funds can't anchor a core (demote to satellite).
    rm = OUT / "eqdm_l2l3_proposed.csv"
    if rm.exists():
        em = pd.read_csv(rm).set_index("code")
        u = u.set_index("code")
        for c in em.index:
            if c in u.index and u.at[c, "layer1"] == "EQ_DM":
                u.at[c, "layer2"] = em.at[c, "new_L2"]
                role = em.at[c, "new_role"]
                fl = em.at[c, "flag"]
                if isinstance(fl, str) and "REVIEW" in fl:
                    role = "satellite"
                u.at[c, "alloc_role"] = role
        u = u.reset_index()
        print(f"EQ_DM remap: -> {sorted(u.loc[u.layer1 == 'EQ_DM', 'layer2'].unique())}")
    return u, base


def weekly_returns(codes):
    px = pd.read_parquet(DM / "data/processed/fund_prices/fund_prices.parquet", columns=["code", "date", "price"])
    px = px[px.code.isin(codes)].dropna(subset=["price"])
    px["date"] = pd.to_datetime(px["date"])
    w = px.pivot_table(index="date", columns="code", values="price", aggfunc="last").sort_index()
    w = w.resample("W-FRI").last().tail(157)  # ~3y weekly
    return np.log(w).diff().dropna(how="all")


def sat_cap_for(row, profile):
    l2 = row["layer2"]
    sri = row["sri"]
    cap = SAT_CAP
    if l2 in NARROW_L2:
        cap = SAT_CAP_NARROW
    # high-SRI suitability: P1/P2 tighter
    if pd.notna(sri):
        ceil = {"P1": 3, "P2": 4, "P3": 5, "P4": 5, "P5": 6}[profile]
        if sri > ceil:
            cap = min(cap, SAT_CAP_NARROW)
    return cap


def _redundant(code, picked, corr, thr=CORR_SOFT):
    """True if `code` correlates > thr with any already-picked holding (the
    0.80 true-diversifier rule of thumb). Missing corr -> not redundant (admit)."""
    if corr is None or code not in corr.columns:
        return False, None
    for pc in picked:
        if pc in corr.columns:
            c = corr.loc[code, pc]
            if pd.notna(c) and c > thr:
                return True, (pc, float(c))
    return False, None


def _cap_of(role, l2):
    if role == "core":
        return PER_FUND_CAP
    return SAT_CAP_NARROW if l2 in NARROW_L2 else SAT_CAP


def _fill(funds, budget, role, profile, picked, corr, dropped, l1, *, max_n, unique_l2, exclude_l2, soft):
    """Top-heavy fill across `funds` (Series, score-ordered). Respects per-fund cap,
    one-per-L2 if unique_l2, soft 0.80 diversifier policy if soft. Returns (rows, rem)."""
    rows, rem, used_l2 = [], budget, set(exclude_l2)
    for r in funds:
        if rem <= 0 or len(rows) >= max_n:
            break
        l2 = r["layer2"]
        if unique_l2 and l2 in used_l2:
            continue
        if soft:
            red, why = _redundant(r["code"], picked, corr)
            if red:
                if dropped is not None:
                    dropped.append((profile, l1, r["code"], l2, why, r["score"]))
                continue
        cap = (
            SAT_CAP_NARROW
            if (role == "satellite" and l2 in NARROW_L2)
            else (sat_cap_for(r, profile) if role == "satellite" else PER_FUND_CAP)
        )
        w = round_grid(min(rem, cap))
        if w <= 0:
            continue
        rows.append((r["code"], l2, role, w, r["score"], r["score_vs_etf"]))
        picked.append(r["code"])
        used_l2.add(l2)
        rem -= w
    return rows, rem


def _spill(rows, rem):
    """Push leftover budget into existing holdings up to their caps (core first) —
    fewer funds, no sub-cap dribs. Returns updated rows + any unabsorbed remainder."""
    if rem <= 0:
        return rows, rem
    order = sorted(range(len(rows)), key=lambda i: 0 if rows[i][2] == "core" else 1)
    for i in order:
        if rem <= 0:
            break
        head = _cap_of(rows[i][2], rows[i][1]) - rows[i][3]
        take = round_grid(min(head, rem))
        if take > 0:
            rows[i] = (*rows[i][:3], rows[i][3] + take, *rows[i][4:])
            rem -= take
    return rows, rem


def allocate_l1(u, l1, budget, profile, corr=None, dropped=None):
    """Core first (up to MAX_CORE funds, 20%-capped — no single-fund overflow), then
    up to MAX_SATS true-diversifier satellites; leftover SPILLS into the core (fewer
    funds, well diversified). EQ_DM=Global DM+US, EQ_EM=EM Broad, COM_GOLD=Gold (pins)."""
    pool = u[u["layer1"] == l1].copy()
    if pool.empty or budget <= 0:
        return []
    core_l2set = CORE_ELIGIBLE.get(l1)
    if core_l2set:
        core_pool = pool[pool["layer2"].isin(core_l2set)]
        sat_pool = pool[~pool["layer2"].isin(core_l2set)]
        core_unique = len(core_l2set) > 1  # EQ_DM spans Blend/Style/US -> one per type
    else:
        core_pool = pool[pool["alloc_role"] == "core"]
        if core_pool.empty:
            core_pool = pool
        sat_pool = pool[pool["alloc_role"] == "satellite"]
        core_unique = False  # single-L2 sleeves (FI_PL) can hold 2-3 same-L2 funds
    sats_all = sat_pool.sort_values("score", ascending=False)
    core_funds = [r for _, r in core_pool.sort_values("score", ascending=False).iterrows()]
    picked = []

    if l1 in ALL_SAT:  # no core (e.g. FI_CREDIT) — diversifier-gated satellites only
        rows, rem = _fill(
            [r for _, r in sats_all.iterrows()],
            budget,
            "satellite",
            profile,
            picked,
            corr,
            dropped,
            l1,
            max_n=MAX_SATS,
            unique_l2=True,
            exclude_l2=set(),
            soft=True,
        )
        rows, _ = _spill(rows, rem)
        return rows

    if l1 in CORE_ONLY:  # whole budget is core (safe / single-asset sleeves)
        rows, rem = _fill(
            core_funds,
            budget,
            "core",
            profile,
            picked,
            corr,
            dropped,
            l1,
            max_n=MAX_CORE,
            unique_l2=False,
            exclude_l2=set(),
            soft=False,
        )
        rows, _ = _spill(rows, rem)
        return rows

    cshare = CORE_SHARE.get(l1, 0.7)
    w_core = round_grid(cshare * budget)
    core_rows, core_rem = _fill(
        core_funds,
        w_core,
        "core",
        profile,
        picked,
        corr,
        dropped,
        l1,
        max_n=MAX_CORE,
        unique_l2=core_unique,
        exclude_l2=set(),
        soft=False,
    )
    core_l2s = {r[1] for r in core_rows}
    w_sat = budget - sum(r[3] for r in core_rows)  # carry any unfilled core budget into sat phase
    sat_rows, sat_rem = _fill(
        [r for _, r in sats_all.iterrows()],
        w_sat,
        "satellite",
        profile,
        picked,
        corr,
        dropped,
        l1,
        max_n=MAX_SATS,
        unique_l2=True,
        exclude_l2=core_l2s,
        soft=True,
    )
    rows = core_rows + sat_rows
    rows, rem = _spill(rows, sat_rem)  # leftover -> existing holdings (core first), fewer funds
    if rem > 0:  # still room only if every holding capped -> add one more core fund
        extra, rem2 = _fill(
            [r for r in core_funds if r["code"] not in picked],
            rem,
            "core",
            profile,
            picked,
            corr,
            dropped,
            l1,
            max_n=1,
            unique_l2=core_unique,  # don't add a 2nd same-type core (e.g. 2nd Value)
            exclude_l2=core_l2s if core_unique else set(),
            soft=False,
        )
        rows += extra
    return rows


def enforce_tfi(prof_rows, u, corr, cap=TFI_CAP):
    """SOFT 35% house cap: while a TFI exceeds cap, swap its lowest-conviction holding
    for the next-best same-L2 fund from a DIFFERENT house (corr-respecting). If no such
    alternative exists, the cap YIELDS (allocation possibilities win) and we flag it."""
    flags = []
    tfi_of = dict(zip(u["code"], u["tfi"]))

    def tally():
        t = {}
        for r in prof_rows:
            h = tfi_of.get(r["code"])
            if h:
                t[h] = t.get(h, 0.0) + r["weight"]
        return t

    for _ in range(30):
        over = [(h, w) for h, w in tally().items() if w > cap + 1e-9]
        if not over:
            break
        house, w = max(over, key=lambda x: x[1])
        held = {r["code"] for r in prof_rows}
        # try to relieve: lowest-conviction holding of this house first (satellite, low EVO)
        victims = sorted(
            [r for r in prof_rows if tfi_of.get(r["code"]) == house],
            key=lambda r: (0 if r["role"] == "satellite" else 1, r["evo"]),
        )
        swapped = False
        for v in victims:
            alt = u[(u["layer1"] == v["l1"]) & (u["layer2"] == v["l2"])].sort_values("score", ascending=False)
            for _, a in alt.iterrows():
                if tfi_of.get(a["code"]) == house or a["code"] in held:
                    continue
                others = [r["code"] for r in prof_rows if r["code"] != v["code"]]
                red, _ = _redundant(a["code"], others, corr)
                if red:
                    continue
                v["code"], v["evo"], v["svetf"], v["name"] = a["code"], a["score"], a["score_vs_etf"], a["name"]
                swapped = True
                break
            if swapped:
                break
        if not swapped:
            flags.append((house, round(w)))  # cap yields — no same-sleeve alternative
            break
    return prof_rows, flags


def main():
    u, base = load_universe()
    pd.set_option("display.width", 200, "display.max_rows", 200, "display.float_format", lambda x: f"{x:.1f}")

    # ---- per-L1 candidate tables (core + top satellite per L2) ----
    print("=" * 90)
    print("PER-L1 CANDIDATES (EVO Score ranked; svetf = soft Score-vs-ETF signal)")
    print("=" * 90)
    cand_codes = {}
    for l1 in ["FI_PL_SHORT", "FI_PL", "FI_GL", "FI_CREDIT", "EQ_DM", "EQ_EM", "COM_GOLD", "COM_BROAD"]:
        pool = u[u["layer1"] == l1]
        if pool.empty:
            continue
        core = pool[pool.alloc_role == "core"].sort_values("score", ascending=False).head(3)
        sats = (
            pool[pool.alloc_role == "satellite"]
            .sort_values("score", ascending=False)
            .groupby("layer2", as_index=False)
            .head(1)
            .sort_values("score", ascending=False)
        )
        print(f"\n### {l1}")
        show = pd.concat([core.assign(_r="CORE"), sats.assign(_r="sat")])
        print(show[["_r", "code", "layer2", "score", "score_vs_etf", "sri"]].to_string(index=False))
        cand_codes[l1] = list(dict.fromkeys(list(core.code) + list(sats.code)))

    # ---- correlation matrices (for editorial less-correlated picks) ----
    print("\n" + "=" * 90)
    print("CORRELATION MATRICES per L1 (3y weekly returns) — pick less-correlated satellites")
    print("=" * 90)
    # broad return set: top-3 funds per (l1, layer2) so allocation fallbacks are covered
    broad = u.sort_values("score", ascending=False).groupby(["layer1", "layer2"]).head(3)["code"].tolist()
    rets = weekly_returns(sorted(set(broad)))
    corr_all = rets.corr()
    for l1, codes in cand_codes.items():
        codes = [c for c in codes if c in rets.columns]
        if len(codes) < 2:
            continue
        cm = rets[codes].corr()
        print(f"\n### {l1}")
        print(cm.round(2).to_string())

    # ---- portfolios ----
    print("\n" + "=" * 90)
    print("RULE-BASED CORE/SATELLITE PORTFOLIOS vs CURRENT-DEV BASELINE")
    print("=" * 90)
    new_rows = []
    dropped = []
    tfi_flags_all = {}
    name_of = dict(zip(u["code"], u["name"]))
    aum_of = dict(zip(u["code"], u["aum_mln"]))
    softaum = dict(zip(u["code"], u["aum_soft_flag"]))
    for prof, budgets in L1_BUDGET.items():
        prof_rows = []
        for l1, b in budgets.items():
            for code, l2, role, w, sc, sv in allocate_l1(u, l1, b, prof, corr=corr_all, dropped=dropped):
                prof_rows.append(
                    dict(
                        profile=prof,
                        l1=l1,
                        l2=l2,
                        role=role,
                        code=code,
                        weight=w,
                        evo=sc,
                        svetf=sv,
                        name=name_of.get(code, code),
                    )
                )
        # SOFT 35% TFI house cap (yields if no same-sleeve alternative)
        prof_rows, tfi_flags = enforce_tfi(prof_rows, u, corr_all)
        tfi_flags_all[prof] = tfi_flags
        print(f"\n────────── {prof} ──────────")
        for r in prof_rows:
            tag = "●" if r["role"] == "core" else "·"
            sv = r["svetf"]
            svs = f"svetf={sv:.0f}" if pd.notna(sv) else "svetf= na"
            am = aum_of.get(r["code"])
            amf = " ⚠<50m" if softaum.get(r["code"]) else (f"  {am:.0f}m" if pd.notna(am) else "")
            print(
                f"  {r['l1']:<12}{tag} {r['l2']:<24} {r['weight']:>4.0f}%  evo={r['evo']:>4.0f}  {svs}{amf}  {r['name']}"
            )
        print(f"  {'TOTAL':<14} {sum(r['weight'] for r in prof_rows):>27.0f}%")
        new_rows.extend(prof_rows)

    nd = pd.DataFrame(new_rows)
    nd.to_csv(OUT / "core_satellite_portfolios.csv", index=False)

    print("\n" + "=" * 90)
    print(f"TFI HOUSE CAP {TFI_CAP:.0f}% — post-swap house exposure per profile")
    print("=" * 90)
    for prof in L1_BUDGET:
        p = nd[nd.profile == prof]
        tfi_of = dict(zip(u["code"], u["tfi"]))
        t = p.assign(tfi=p.code.map(tfi_of)).groupby("tfi").weight.sum().sort_values(ascending=False)
        top = "; ".join(f"{k} {v:.0f}%" for k, v in t.head(3).items())
        fl = tfi_flags_all.get(prof) or []
        fls = f"  | CAP YIELDED: {fl}" if fl else ""
        print(f"  {prof}: {top}{fls}")

    # ---- satellites de-prioritized by the SOFT diversifier policy (overridable) ----
    print("\n" + "=" * 90)
    print(
        f"SATELLITES DE-PRIORITIZED by the {CORR_SOFT:.2f} SOFT diversifier policy (overridable; score given up shown)"
    )
    print("=" * 90)
    seen = set()
    for prof, l1, code, l2, why, sc in dropped:
        key = (l1, code)
        if key in seen:
            continue
        seen.add(key)
        wc, cv = why if why else ("?", float("nan"))
        print(
            f"  {l1:<10} {code:<16} {l2:<26} evo={sc:>4.0f}  redundant: corr {cv:.2f} vs {wc} (override if score edge justifies)"
        )

    # ---- diff summary vs baseline ----
    print("\n" + "=" * 90)
    print("KEY DIFFS vs current-dev")
    print("=" * 90)
    for prof in L1_BUDGET:
        b = base[(base.profile == prof) & (base.weight_pct.fillna(0) > 0)]
        n = nd[nd.profile == prof]

        # max single-country US / Poland exposure
        def expo(df, codecol, wcol, l2col, keys):
            return df[df[l2col].astype(str).str.contains("|".join(keys), case=False, na=False)][wcol].sum()

        us_b = expo(b, "code", "weight_pct", "selection_category", ["US Equity"])
        us_n = expo(n, "code", "weight", "l2", ["US Equity"])
        pl_b = expo(b, "code", "weight_pct", "selection_category", ["Poland", "PL Small"])
        pl_n = expo(n, "code", "weight", "l2", ["Poland", "PL Small"])
        max_sat_b = b[
            b.selection_category.astype(str).str.contains("Sector|Thematic|Healthcare|Tech", na=False)
        ].weight_pct.max()
        print(
            f"{prof}: US  base={us_b:>4.0f}% new={us_n:>4.0f}% | PL(as EM) base={pl_b:>4.0f}% new={pl_n:>4.0f}% | biggest thematic base={max_sat_b if pd.notna(max_sat_b) else 0:>4.0f}% new≤{SAT_CAP:.0f}%"
        )
    print(f"\nwrote {OUT}/core_satellite_portfolios.csv")


if __name__ == "__main__":
    main()

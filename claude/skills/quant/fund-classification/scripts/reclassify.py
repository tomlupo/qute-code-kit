"""Per-fund reclassification: current selection_group -> final L2 (task 9).

Turns taxonomy_final_pln.yaml decisions into a concrete per-fund mapping for
advisor sign-off + the taxonomy xlsx update. Rules:
  - KEPT groups -> renamed final group (+ role/standalone/benchmark from YAML).
  - EXPLICIT moves/isolates (cross-L1, leverage, mislabelled) -> hardcoded from analysis.
  - NEW satellite SEEDS (Gold&Mining, Asia/China, US/USD Govt) -> from sub-cluster runs.
  - Remaining DISSOLVED-group funds -> nearest coherent destination by correlation
    (>= THRESH), else residual (Specialist for equity / Other for FI).

PLN-only, latest 156w. Output: per-fund CSV with basis (kept/explicit/seed/clustered/residual).
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
WINDOW, MIN_OBS, THRESH = 156, 130, 0.55

# final group -> (role, standalone_eligible, benchmark)
FINAL = {
    "PL Govt/Core Bonds": ("core", True, "TBSP"),
    "PL Other Bonds": ("other", False, "—"),
    "PL Govt Short": ("core", True, "CASH"),
    "PL Corp Short": ("satellite", False, "CASH"),
    "PL Short Other": ("other", False, "—"),
    "Global Core Bonds": ("core", True, "FI_GL/BNDW (hedged+carry)"),
    "US/USD Govt Bonds": ("satellite", False, "BM_FI_AGG xUSDPLN"),
    "IG Corporate Bonds": ("satellite", False, "FI_IG/LQD"),
    "FI_GL Other": ("other", False, "—"),
    "EM Debt": ("satellite", False, "FI_EM/EMB"),
    "HY Bonds": ("satellite", False, "FI_HY/HYG"),
    "Global DM Equity": ("core", True, "IWDA"),
    "US Equity": ("satellite", True, "CSPX"),
    "European Equity": ("satellite", True, "IMEU"),
    "Technology": ("satellite", False, "tech UCITS"),
    "Gold & Mining Equity": ("satellite", False, "gold-miners UCITS"),
    "Specialist Equity": ("satellite", False, "per-fund theme UCITS"),
    "EQ_DM Other": ("other", False, "—"),
    "EM Broad Equity": ("core", True, "EIMI"),
    "PL Equity": ("satellite", True, "WIG_TR"),
    "PL Equity Small/Mid": ("satellite", False, "MWIG40"),
    "Asia/China Equity": ("satellite", False, "MSCI China/EM-Asia UCITS"),
    "Specialist EM Equity": ("satellite", False, "per-region UCITS"),
    "EQ_EM Other": ("other", False, "—"),
    "Gold": ("satellite", True, "gold UCITS (SGLN)"),
    "Precious Metals": ("satellite", True, "PM UCITS"),
    "Commodities": ("satellite", True, "broad-commodity UCITS"),
    "Mixed GL Flexible": ("core", True, "VNGA60/80"),
    "Mixed PL Flexible": ("satellite", True, "VNGA60+PL"),
    "Mixed GL Conservative": ("core", True, "VNGA20/40"),
    "Mixed PL Conservative": ("satellite", True, "VNGA20/40+PL"),
}

KEPT = {  # current selection_group -> final group (no change in membership)
    "PL Govt Bonds PLN": "PL Govt/Core Bonds",
    "PL Govt Short Term PLN": "PL Govt Short",
    "PL Corp Short Term PLN": "PL Corp Short",
    "IG Corporate Bonds PLN": "IG Corporate Bonds",
    "EM Debt PLN": "EM Debt",
    "HY Bonds PLN": "HY Bonds",
    "Global DM Equity": "Global DM Equity",
    "US Equity": "US Equity",
    "European Equity": "European Equity",
    "Technology": "Technology",
    "EM Broad Equity": "EM Broad Equity",
    "PL Equity": "PL Equity",
    "PL Equity Small Mid": "PL Equity Small/Mid",
    "Gold": "Gold",
    "Precious Metals": "Precious Metals",
    "Commodities": "Commodities",
    "Mixed GL Flexible": "Mixed GL Flexible",
    "Mixed PL Flexible": "Mixed PL Flexible",
    "Mixed GL Conservative": "Mixed GL Conservative",
    "Mixed PL Conservative": "Mixed PL Conservative",
}
MERGE = {"Miners Sector": "Gold & Mining Equity"}  # merged into new satellite
DISSOLVED = {"PL Universal Bonds PLN", "Global Core Bonds PLN", "Other Sectors", "EM Other Equity"}

SEEDS = {
    "Gold & Mining Equity": ["AXA35", "BGF053_A2H_PLN", "BGF056_A2H_PLN", "PCS55", "PZU81", "SUP58"],
    "Asia/China Equity": [
        "AIG11",
        "BGF001_A2H_PLN",
        "FIL007_AH_PLN",
        "FOR31",
        "FTI033_N_PLN",
        "SIS079_A1H_PLN",
        "SIS104_A1H_PLN",
    ],
    "US/USD Govt Bonds": ["PCS54", "PIO10", "PIO87"],
}
EXPLICIT = {  # code -> final group (cross-L1 moves + isolates)
    "CON004_A_PLN": "PL Govt/Core Bonds",
    "MIL33": "PL Govt/Core Bonds",
    "NOB27": "PL Govt/Core Bonds",
    "FOR36": "PL Govt Short",
    "QRS07": "EQ_EM Other",
    "QRS34": "PL Other Bonds",
    "PLJ51": "PL Other Bonds",
    "GSF013_AH_PLN": "FI_GL Other",
    "AXA38A1": "FI_GL Other",
    "PIO13": "FI_GL Other",
    "FOR37": "FI_GL Other",
    "MON24": "FI_GL Other",
    "KAH33": "EQ_DM Other",
    "KAH34": "EQ_DM Other",
}
# dissolved current group -> (candidate destinations [final groups], residual)
DEST = {
    # candidates = groups a dissolved fund may ATTACH to (>=THRESH); residual = default.
    # Core groups are NOT candidates (a specialist/leftover must not contaminate a core);
    # for a SPLIT (Global Core) the residual IS the core and only explicit funds depart.
    "PL Universal Bonds PLN": (
        ["PL Govt/Core Bonds", "PL Govt Short"],
        "PL Other Bonds",
    ),  # nearest of long-core vs short; weak fits -> Other
    "Global Core Bonds PLN": ([], "Global Core Bonds"),  # split: explicit departures only, rest stays core
    "Other Sectors": (["Gold & Mining Equity", "Technology"], "Specialist Equity"),
    "EM Other Equity": (["Asia/China Equity"], "Specialist EM Equity"),
}


def main():
    sc = pd.read_parquet(
        DM / "data/processed/fund_selection/scores.parquet", columns=["code", "currency"]
    ).drop_duplicates("code")
    pln = set(sc[sc.currency == "PLN"].code)
    m = pd.read_csv(DM / "config/reference/fund_mapping.csv").set_index("code")[["layer1", "selection_group"]]
    nm = (
        pd.read_parquet(DM / "data/processed/quotations/quotations.parquet", columns=["code", "name"])
        .drop_duplicates("code")
        .set_index("code")["name"]
        .str.replace(r"\\", "", regex=True)
    )
    px = pd.read_parquet(
        DM / "data/processed/fund_prices/fund_prices.parquet", columns=["code", "date", "price"]
    ).dropna(subset=["price"])
    px = px[px.code.isin(pln)]
    wide = px.pivot_table(index="date", columns="code", values="price", aggfunc="last").sort_index()
    rets = np.log(wide.resample("W-FRI").last()).diff().iloc[1:].iloc[-(WINDOW + 1) :]
    obs = rets.notna().sum()
    corr = rets[obs[obs >= MIN_OBS].index].corr(min_periods=MIN_OBS)

    # destination member sets for nearest assignment (seeds + current-group members)
    def members(final_group):
        seed = SEEDS.get(final_group, [])
        cur = [c for c, fg in KEPT.items() if fg == final_group]  # current groups feeding it
        codes = list(seed)
        for cg in cur:
            codes += list(m.index[m.selection_group == cg])
        if final_group == "PL Govt/Core Bonds":
            codes += list(m.index[m.selection_group == "PL Govt Bonds PLN"])
        if final_group == "Global Core Bonds":
            codes += list(m.index[m.selection_group == "Global Core Bonds PLN"])  # the core cluster (residual default)
        return [c for c in set(codes) if c in corr.columns]

    rows = []
    pln_funds = [c for c in pln if c in m.index]
    for c in pln_funds:
        L1, cg = m.loc[c, "layer1"], m.loc[c, "selection_group"]
        basis, fg = None, None
        if c in EXPLICIT:
            fg, basis = EXPLICIT[c], "explicit"
        elif c in {x for s in SEEDS.values() for x in s}:
            fg = next(g for g, s in SEEDS.items() if c in s)
            basis = "seed"
        elif cg in KEPT:
            fg, basis = KEPT[cg], "kept"
        elif cg in MERGE:
            fg, basis = MERGE[cg], "merge"
        elif cg in DISSOLVED:
            cands, residual = DEST[cg]
            best_g, best_r = None, -np.inf
            if c in corr.columns:
                for dg in cands:
                    mem = [x for x in members(dg) if x != c]
                    if mem:
                        r = corr.loc[c, mem].mean()
                        if r > best_r:
                            best_r, best_g = r, dg
            if best_g and best_r >= THRESH:
                fg, basis = best_g, f"clustered(rho={best_r:.2f})"
            else:
                fg, basis = residual, f"residual(best={best_r:.2f})" if np.isfinite(best_r) else "residual(no-hist)"
        else:
            fg, basis = f"[{L1}] {cg}", "out-of-scope"  # ALT_* etc.

        role, standalone, bench = FINAL.get(fg, ("satellite", False, "—"))
        rows.append(
            {
                "code": c,
                "name": str(nm.get(c, ""))[:34],
                "layer1": L1,
                "current_group": cg,
                "final_group": fg,
                "role": role,
                "standalone_eligible": standalone,
                "benchmark": bench,
                "basis": basis,
            }
        )

    df = pd.DataFrame(rows).sort_values(["layer1", "final_group", "code"])
    df.to_csv(OUT / "pln_reclassification.csv", index=False)

    moved = df[df.basis.str.startswith(("explicit", "seed", "clustered", "residual", "merge"))]
    print(
        f"PLN funds mapped: {len(df)}  |  changed group: {len(moved)}  |  kept: {(df.basis == 'kept').sum()}  |  out-of-scope: {(df.basis == 'out-of-scope').sum()}"
    )
    print("\n=== final group summary (allocation L1s) ===")
    alloc = df[~df.basis.eq("out-of-scope")]
    summ = (
        alloc.groupby(["layer1", "final_group", "role"])
        .agg(n=("code", "size"), standalone=("standalone_eligible", "first"))
        .reset_index()
    )
    print(summ.to_string(index=False))
    print("\n=== sample of CHANGED funds ===")
    print(moved[["code", "name", "current_group", "final_group", "basis"]].head(25).to_string(index=False))
    print(f"\nwrote {OUT}/pln_reclassification.csv ({len(df)} funds)")


if __name__ == "__main__":
    main()

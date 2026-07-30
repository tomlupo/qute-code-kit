"""Rolling-window stability gate for the PLN taxonomy proposal (component [1] final).

Single-snapshot correlations are regime-unstable. Before any regroup reaches an
advisor, the signal must PERSIST. This recomputes cohesion / merge / split /
isolate across 3 trailing 156w windows stepped 52w apart and keeps only signals
present in >= MIN_PERSIST of the windows where the group/fund actually exists.

Emits an advisor-ready final action table. Still propose-to-human: nothing here
edits the xlsx.

Reuses the same method as cohesion.py / propose_taxonomy_pln.py (Mantegna
distance, average-linkage sub-clustering).

Writes (output/):
  - pln_stability_groups.csv   per group x window: n, intra_rho, + persistence verdict
  - pln_actions_final.csv      per current group: recommended action + persistence
  - pln_proposed_mapping_final.csv  per fund: current -> proposed (stable signals only)
"""

from __future__ import annotations

import os
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform

# dm-evo checkout (live data/config). DM_EVO_ROOT overrides (worktree/CI/other host);
# else the sibling dm-evo beside the lab-repo root (parents[4]).
DM = Path(os.environ.get("DM_EVO_ROOT") or (Path(__file__).resolve().parents[5] / "dm-evo"))
OUT = Path(__file__).resolve().parent / "output"
OUT.mkdir(exist_ok=True)

WINDOW = 156  # weeks per window (~3y)
STEP = 52  # weeks between window ends (~1y)
N_WINDOWS = 3
MIN_OBS = 130
MIN_PERSIST = 2  # signal must appear in >= this many of the windows-where-eligible

ALLOC_L0 = {"EQ", "FI", "FI_AGG", "MIX", "COM"}
COHERENT_MIN = 0.60  # a group must be this tight to be a genuine merge partner
SEP_MARGIN = 0.05  # merge if min(intra_A,intra_B) - between <= this
WEAK_RHO = 0.55  # group below this = dissolve/split candidate
SPLIT_CUT_RHO = 0.65
SPLIT_MIN_SUB = 3
ISOLATE_RHO = 0.20  # tightened (true singletons: rho->0/negative to everything)
GROUP_COL = "selection_group"


def load_weekly_returns_pln():
    sc = pd.read_parquet(
        DM / "data/processed/fund_selection/scores.parquet", columns=["code", "currency"]
    ).drop_duplicates("code")
    pln = set(sc.loc[sc.currency == "PLN", "code"])
    px = pd.read_parquet(
        DM / "data/processed/fund_prices/fund_prices.parquet", columns=["code", "date", "price"]
    ).dropna(subset=["price"])
    px = px[px.code.isin(pln)]
    wide = px.pivot_table(index="date", columns="code", values="price", aggfunc="last").sort_index()
    wk = wide.resample("W-FRI").last()
    return np.log(wk).diff().iloc[1:]


def load_labels():
    m = pd.read_csv(DM / "config/reference/fund_mapping.csv")
    return m.set_index("code")[["layer0", "layer1", "selection_group"]]


def analyze_window(rets_slice: pd.DataFrame, lab: pd.DataFrame):
    """One window -> (group_intra rows, coherent-merge pairs, split groups, isolate codes)."""
    obs = rets_slice.notna().sum()
    cols = obs[obs >= MIN_OBS].index
    rets_slice = rets_slice[cols]
    funds = [c for c in rets_slice.columns if c in lab.index and pd.notna(lab.loc[c, GROUP_COL])]
    rets_slice = rets_slice[funds]
    corr = rets_slice.corr(min_periods=MIN_OBS).fillna(0.0)
    C = corr.to_numpy(copy=True)
    np.fill_diagonal(C, 1.0)
    funds = list(corr.columns)
    l1 = lab.loc[funds, "layer1"].to_numpy()
    grp = lab.loc[funds, GROUP_COL].to_numpy()

    group_rows, merges, splits, isolates = [], set(), set(), set()

    for L in pd.unique(l1):
        li = np.where(l1 == L)[0]
        sub_groups = grp[li]
        Csub = C[np.ix_(li, li)]
        gl = pd.unique(sub_groups)
        idx = {g: np.where(sub_groups == g)[0] for g in gl}

        # group-pair mean-rho matrix
        intra = {}
        for g in gl:
            m = idx[g]
            intra[g] = Csub[np.ix_(m, m)][~np.eye(len(m), dtype=bool)].mean() if len(m) >= 2 else np.nan
            group_rows.append({"layer1": L, GROUP_COL: g, "n": len(m), "intra_rho": intra[g]})

        for ga, gb in combinations(gl, 2):
            between = Csub[np.ix_(idx[ga], idx[gb])].mean()
            ra, rb = intra[ga], intra[gb]
            if (
                np.isfinite(ra)
                and np.isfinite(rb)
                and ra >= COHERENT_MIN
                and rb >= COHERENT_MIN
                and (min(ra, rb) - between) <= SEP_MARGIN
            ):
                merges.add((L, frozenset({ga, gb})))

        for g in gl:
            m = idx[g]
            if len(m) < 2 * SPLIT_MIN_SUB:
                continue
            Cg = Csub[np.ix_(m, m)]
            Dg = np.sqrt(np.clip(2 * (1 - Cg), 0, None))
            np.fill_diagonal(Dg, 0.0)
            Z = linkage(squareform(Dg, checks=False), method="average")
            subl = fcluster(Z, t=np.sqrt(2 * (1 - SPLIT_CUT_RHO)), criterion="distance")
            big = [s for s, c in zip(*np.unique(subl, return_counts=True), strict=False) if c >= SPLIT_MIN_SUB]
            if len(big) >= 2:
                splits.add((L, g))

        for fi in range(len(li)):
            best = -np.inf
            for g in gl:
                others = [k for k in idx[g] if k != fi]
                if others:
                    best = max(best, Csub[fi, others].mean())
            if np.isfinite(best) and best < ISOLATE_RHO:
                isolates.add(funds[li[fi]])

    return pd.DataFrame(group_rows), merges, splits, isolates


def main() -> None:
    weekly = load_weekly_returns_pln()
    lab = load_labels()
    n = len(weekly)
    ends = [n - 1 - STEP * k for k in range(N_WINDOWS)]
    ends = [e for e in ends if e - WINDOW + 1 >= 0]
    win_labels = [f"W{k + 1}({weekly.index[e].date()})" for k, e in enumerate(ends)]
    print(f"PLN stability: {len(ends)} windows of {WINDOW}w: " + ", ".join(win_labels))

    grp_intra = defaultdict(dict)  # (L1,group) -> {win: intra}
    grp_n = defaultdict(dict)
    grp_present = defaultdict(set)
    merge_count = defaultdict(set)
    split_count = defaultdict(set)
    iso_hit = defaultdict(set)
    fund_label = {}
    fund_eligible_windows = defaultdict(set)

    for w, e in enumerate(ends):
        sl = weekly.iloc[e - WINDOW + 1 : e + 1]
        gdf, merges, splits, isolates = analyze_window(sl, lab)
        for _, r in gdf.iterrows():
            key = (r["layer1"], r[GROUP_COL])
            if r["n"] >= 2:
                grp_intra[key][w] = r["intra_rho"]
                grp_n[key][w] = r["n"]
                grp_present[key].add(w)
        for L, pair in merges:
            merge_count[(L, pair)].add(w)
        for s in splits:
            split_count[s].add(w)
        # fund eligibility / isolate persistence
        obs = sl.notna().sum()
        eligible = set(obs[obs >= MIN_OBS].index) & set(lab.index)
        for c in eligible:
            fund_eligible_windows[c].add(w)
            if c in lab.index:
                fund_label[c] = (lab.loc[c, "layer1"], lab.loc[c, GROUP_COL])
        for c in isolates:
            iso_hit[c].add(w)

    # ---- group cohesion stability ----
    g_rows = []
    for key, wins in grp_intra.items():
        L, g = key
        present = grp_present[key]
        mean_intra = np.nanmean(list(wins.values()))
        weak_in = sum(1 for v in wins.values() if v < WEAK_RHO)
        verdict = (
            "stable-weak"
            if weak_in >= MIN_PERSIST
            else "stable-strong"
            if all(v >= WEAK_RHO for v in wins.values()) and len(present) >= MIN_PERSIST
            else "mixed"
        )
        row = {
            "layer1": L,
            GROUP_COL: g,
            "alloc": lab[lab[GROUP_COL] == g]["layer0"].iloc[0] in ALLOC_L0 if (lab[GROUP_COL] == g).any() else False,
            "mean_intra": mean_intra,
            "windows_present": len(present),
            "weak_windows": weak_in,
            "verdict": verdict,
        }
        for w in range(len(ends)):
            row[f"intra_W{w + 1}"] = wins.get(w, np.nan)
        g_rows.append(row)
    gstab = pd.DataFrame(g_rows).sort_values(["alloc", "mean_intra"], ascending=[False, True])
    gstab.to_csv(OUT / "pln_stability_groups.csv", index=False)

    # ---- stable merges / splits ----
    stable_merges = {k: w for k, w in merge_count.items() if len(w) >= MIN_PERSIST}
    stable_splits = {k: w for k, w in split_count.items() if len(w) >= MIN_PERSIST}
    stable_isolates = {
        c: iso_hit[c]
        for c in iso_hit
        if len(iso_hit[c]) >= MIN_PERSIST and len(fund_eligible_windows[c]) >= MIN_PERSIST
    }

    # ---- final action table per current group ----
    act_rows = []
    for key in grp_intra:
        L, g = key
        alloc = lab[GROUP_COL] == g
        is_alloc = lab[alloc]["layer0"].iloc[0] in ALLOC_L0 if alloc.any() else False
        verdict = gstab[(gstab.layer1 == L) & (gstab[GROUP_COL] == g)]["verdict"].iloc[0]
        actions = []
        if verdict == "stable-weak":
            actions.append("DISSOLVE/SPLIT (persistently incoherent)")
        if (L, g) in stable_splits:
            actions.append(f"SPLIT [{len(stable_splits[(L, g)])}/{len(ends)}w]")
        partners = [sorted(p - {g})[0] for (LL, p) in stable_merges if LL == L and g in p]
        if partners:
            actions.append("MERGE with " + "; ".join(partners) + " [persisted]")
        if not actions:
            actions.append("KEEP")
        act_rows.append(
            {
                "layer1": L,
                "alloc": is_alloc,
                GROUP_COL: g,
                "mean_intra": np.nanmean(list(grp_intra[key].values())),
                "verdict": verdict,
                "action": " | ".join(actions),
            }
        )
    actions = pd.DataFrame(act_rows).sort_values(["alloc", "layer1", "mean_intra"], ascending=[False, True, True])
    actions.to_csv(OUT / "pln_actions_final.csv", index=False)

    # ---- final proposed mapping (stable isolates only) ----
    map_rows = []
    for c, (L, g) in fund_label.items():
        if c in stable_isolates:
            map_rows.append(
                {
                    "code": c,
                    "layer1": L,
                    "current_group": g,
                    "action": "isolate",
                    "proposed_group": f"ISOLATE::{c}",
                    "isolate_windows": len(stable_isolates[c]),
                    "eligible_windows": len(fund_eligible_windows[c]),
                }
            )
    pd.DataFrame(map_rows).to_csv(OUT / "pln_proposed_mapping_final.csv", index=False)

    # ---- report ----
    pd.set_option("display.width", 180, "display.max_columns", 25, "display.float_format", lambda x: f"{x:.3f}")
    aa = actions[actions.alloc]
    print(
        f"\n{'=' * 82}\nFINAL ACTIONS — PLN allocation groups (stable signals only, >={MIN_PERSIST}/{len(ends)} windows):\n{'=' * 82}"
    )
    print(aa[["layer1", GROUP_COL, "mean_intra", "verdict", "action"]].to_string(index=False))

    print(f"\n{'=' * 82}\nStable MERGES (both groups coherent, persisted):\n{'=' * 82}")
    for (L, pair), wins in sorted(stable_merges.items()):
        print(f"  {L}: {' + '.join(sorted(pair))}   [{len(wins)}/{len(ends)} windows]")
    if not stable_merges:
        print("  (none)")

    print(f"\n{'=' * 82}\nStable ISOLATES (true singletons, rho<{ISOLATE_RHO} to all, persisted):\n{'=' * 82}")
    if stable_isolates:
        for c in sorted(stable_isolates, key=lambda c: len(stable_isolates[c]), reverse=True):
            L, g = fund_label[c]
            print(
                f"  {c:16s} {L:10s} {g:24s}  isolate in {len(stable_isolates[c])}/{len(fund_eligible_windows[c])} eligible windows"
            )
    else:
        print("  (none)")

    print("\nwrote: pln_stability_groups.csv  pln_actions_final.csv  pln_proposed_mapping_final.csv")


if __name__ == "__main__":
    main()

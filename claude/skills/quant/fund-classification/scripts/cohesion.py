"""L2 group cohesion + clustering recommender — prototype (component [1]).

Brainstorm context: docs trail in the dm-evo-lab session. We score within L1
(``scoring_category``) but *select* within L2 (``selection_group`` = L2 + ccy
for FI). The descriptive fund->L2 mapping produces groups that may not be
return-coherent. This prototype measures L2 cohesion quantitatively and
*proposes* (never auto-applies) regroupings — extending the existing
``l2_return_outliers.py`` (avg-peer-rho < 0.5 flag) from flagging to grouping.

Governance: AUGMENT / propose-to-human. Output is evidence for advisor review,
not a rewrite of the taxonomy. The xlsx stays source of truth.

Reads (from sibling dm-evo, gitignored there — not packaged):
  - data/processed/fund_prices/fund_prices.parquet   (NAV history)
  - config/reference/fund_mapping.csv                (layer1/layer2/selection_group)
  - config/reference/fund_master.csv                 (fund names, best-effort)

Writes (this dir's output/, gitignored):
  - l2_cohesion.csv     per selection_group: cohesion metrics
  - l2_misfits.csv      per fund: funds closer to another group than their own
  - l1_clustering.csv   per L1: data-driven clusters vs existing labels (ARI)

Method follows the promoted MST diagnostic (src/fund_diagnostics/correlation_mst.py):
3Y W-FRI weekly log returns, Pearson pairwise-complete, Mantegna distance
d = sqrt(2(1-rho)).
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform
from sklearn.metrics import adjusted_rand_score, silhouette_samples

# --- config ---
# dm-evo checkout (live data/config). DM_EVO_ROOT overrides (worktree/CI/other host);
# else the sibling dm-evo beside the lab-repo root (parents[4]).
DM = Path(os.environ.get("DM_EVO_ROOT") or (Path(__file__).resolve().parents[5] / "dm-evo"))
OUT = Path(__file__).resolve().parent / "output"
OUT.mkdir(exist_ok=True)

WEEKLY_WINDOW = 156  # ~3y of W-FRI observations
MIN_OBS = 130  # min weekly returns to keep a fund (matches MST diagnostic)
OUTLIER_RHO = 0.50  # existing l2_return_outliers avg-peer-rho floor
CLUSTER_CUT_RHO = 0.50  # agglomerative cut: merge while avg within-cluster rho >= this
GROUP_COL = "selection_group"  # operative selection pool (L2 + ccy for FI)


def load_returns() -> pd.DataFrame:
    """3Y W-FRI weekly log returns, funds x weeks, min-obs filtered."""
    px = pd.read_parquet(
        DM / "data/processed/fund_prices/fund_prices.parquet",
        columns=["code", "date", "price"],
    ).dropna(subset=["price"])
    wide = px.pivot_table(index="date", columns="code", values="price", aggfunc="last").sort_index()
    wk = wide.resample("W-FRI").last().iloc[-(WEEKLY_WINDOW + 1) :]
    rets = np.log(wk).diff().iloc[1:]
    obs = rets.notna().sum()
    keep = obs[obs >= MIN_OBS].index
    return rets[keep]


def load_labels() -> pd.DataFrame:
    m = pd.read_csv(DM / "config/reference/fund_mapping.csv")
    lab = m.set_index("code")[["layer1", "layer2", "selection_group"]]
    # best-effort fund names for readability
    try:
        fm = pd.read_csv(DM / "config/reference/fund_master.csv")
        name_col = next((c for c in fm.columns if c.lower() in ("name", "fundname", "fund_name")), None)
        code_col = next((c for c in fm.columns if c.lower() in ("code", "fundcode", "fund_code")), None)
        if name_col and code_col:
            lab = lab.join(fm.set_index(code_col)[name_col].rename("name"))
    except Exception:
        lab["name"] = pd.NA
    if "name" not in lab.columns:
        lab["name"] = pd.NA
    return lab


def main() -> None:
    rets = load_returns()
    snap = rets.index.max()
    lab = load_labels()

    funds = [c for c in rets.columns if c in lab.index and pd.notna(lab.loc[c, GROUP_COL])]
    rets = rets[funds]
    lab = lab.loc[funds]
    print(f"snapshot={snap.date()}  funds={len(funds)}  window={WEEKLY_WINDOW}w  min_obs={MIN_OBS}")

    corr = rets.corr(min_periods=MIN_OBS)
    # NaN corr (insufficient pairwise overlap) -> treat as uncorrelated (rho=0)
    n_nan = int(corr.isna().to_numpy().sum())  # off-diagonal only; pandas diagonal is 1.0
    C = corr.fillna(0.0).to_numpy(copy=True)
    np.fill_diagonal(C, 1.0)
    dist = np.sqrt(np.clip(2 * (1 - C), 0, None))
    np.fill_diagonal(dist, 0.0)

    grp = lab[GROUP_COL].to_numpy()
    l1 = lab["layer1"].to_numpy()
    n = len(funds)
    off = ~np.eye(n, dtype=bool)

    # ---- per-fund: avg rho to own group, and best 'other group within same L1' ----
    rows = []
    for i, code in enumerate(funds):
        g, my_l1 = grp[i], l1[i]
        own = (grp == g) & off[i]
        avg_own = C[i, own].mean() if own.any() else np.nan
        # candidate groups in same L1, excluding own
        sib_groups = pd.unique(grp[(l1 == my_l1) & (grp != g)])
        best_other_g, best_other_rho = None, -np.inf
        for og in sib_groups:
            mask = grp == og
            r = C[i, mask].mean()
            if r > best_other_rho:
                best_other_rho, best_other_g = r, og
        rows.append(
            {
                "code": code,
                "name": lab.loc[code, "name"],
                "layer1": my_l1,
                GROUP_COL: g,
                "avg_rho_own": avg_own,
                "best_other_group": best_other_g,
                "best_other_rho": best_other_rho if np.isfinite(best_other_rho) else np.nan,
            }
        )
    fund_df = pd.DataFrame(rows)
    fund_df["misfit_low_cohesion"] = fund_df["avg_rho_own"] < OUTLIER_RHO
    fund_df["misfit_nearer_other"] = fund_df["best_other_rho"] > fund_df["avg_rho_own"]
    misfits = fund_df[fund_df["misfit_low_cohesion"] | fund_df["misfit_nearer_other"]].copy()
    misfits = misfits.sort_values("avg_rho_own")
    misfits.to_csv(OUT / "l2_misfits.csv", index=False)

    # ---- per-group cohesion ----
    grp_rows = []
    for g in pd.unique(grp):
        gi = np.where(grp == g)[0]
        my_l1 = l1[gi[0]]
        if len(gi) >= 2:
            sub = C[np.ix_(gi, gi)]
            intra = sub[~np.eye(len(gi), dtype=bool)]
            avg_intra, med_intra = intra.mean(), np.median(intra)
        else:
            avg_intra = med_intra = np.nan
        # inter: members of g vs other funds in same L1
        other = np.where((l1 == my_l1) & (grp != g))[0]
        avg_inter = C[np.ix_(gi, other)].mean() if (len(gi) and len(other)) else np.nan
        grp_rows.append(
            {
                "layer1": my_l1,
                GROUP_COL: g,
                "n_funds": len(gi),
                "avg_intra_rho": avg_intra,
                "median_intra_rho": med_intra,
                "avg_inter_rho_within_L1": avg_inter,
                "intra_minus_inter": (avg_intra - avg_inter)
                if np.isfinite(avg_intra) and np.isfinite(avg_inter)
                else np.nan,
                "n_misfits": int(((misfits["layer1"] == my_l1) & (misfits[GROUP_COL] == g)).sum()),
            }
        )
    cohesion = pd.DataFrame(grp_rows).sort_values(["layer1", "avg_intra_rho"])

    # ---- within-L1 silhouette + clustering vs existing labels ----
    sil_per_fund = np.full(n, np.nan)
    clus_rows = []
    for L in pd.unique(l1):
        idx = np.where(l1 == L)[0]
        labels = pd.factorize(grp[idx])[0]
        k_existing = len(np.unique(labels))
        if len(idx) < 4 or k_existing < 2:
            continue
        sub_d = dist[np.ix_(idx, idx)]
        # silhouette of existing L2 split within this L1
        if 2 <= k_existing <= len(idx) - 1:
            sil = silhouette_samples(sub_d, labels, metric="precomputed")
            sil_per_fund[idx] = sil
        # data-driven clustering: average linkage, cut at d corresponding to CLUSTER_CUT_RHO
        condensed = squareform(sub_d, checks=False)
        Z = linkage(condensed, method="average")
        cut_d = np.sqrt(2 * (1 - CLUSTER_CUT_RHO))
        data_labels = fcluster(Z, t=cut_d, criterion="distance")
        clus_rows.append(
            {
                "layer1": L,
                "n_funds": len(idx),
                "n_groups_existing": k_existing,
                "n_clusters_found": len(np.unique(data_labels)),
                "ARI_vs_existing": adjusted_rand_score(labels, data_labels),
                "silhouette_existing": float(np.nanmean(sil_per_fund[idx]))
                if np.isfinite(sil_per_fund[idx]).any()
                else np.nan,
            }
        )
    clustering = pd.DataFrame(clus_rows).sort_values("silhouette_existing")
    cohesion["silhouette_existing"] = [
        float(np.nanmean(sil_per_fund[np.where(grp == g)[0]]))
        if np.isfinite(sil_per_fund[np.where(grp == g)[0]]).any()
        else np.nan
        for g in cohesion[GROUP_COL]
    ]
    cohesion.to_csv(OUT / "l2_cohesion.csv", index=False)
    clustering.to_csv(OUT / "l1_clustering.csv", index=False)

    # ---- report ----
    pd.set_option("display.width", 160, "display.max_columns", 20)
    print(f"\nNaN correlations (insufficient overlap, set to rho=0): {n_nan}")
    print(f"\n{'=' * 70}\nLEAST cohesive selection_groups (avg intra rho, n>=3):\n{'=' * 70}")
    weak = cohesion[cohesion["n_funds"] >= 3].nsmallest(12, "avg_intra_rho")
    print(
        weak[
            ["layer1", GROUP_COL, "n_funds", "avg_intra_rho", "intra_minus_inter", "silhouette_existing", "n_misfits"]
        ].to_string(index=False)
    )

    print(f"\n{'=' * 70}\nGroups where intra <= inter (peers no tighter than the rest of L1):\n{'=' * 70}")
    bad = cohesion[(cohesion["intra_minus_inter"] <= 0.05) & (cohesion["n_funds"] >= 3)]
    print(
        bad[
            ["layer1", GROUP_COL, "n_funds", "avg_intra_rho", "avg_inter_rho_within_L1", "intra_minus_inter"]
        ].to_string(index=False)
        if len(bad)
        else "  (none)"
    )

    print(f"\n{'=' * 70}\nL1s where data-driven clusters disagree most with existing L2 (low ARI):\n{'=' * 70}")
    print(clustering.head(12).to_string(index=False))

    print(
        f"\n{'=' * 70}\nMisfit funds (closer to another group, or avg own rho < {OUTLIER_RHO}): {len(misfits)} of {n}\n{'=' * 70}"
    )
    show = misfits.head(20).copy()
    show["avg_rho_own"] = show["avg_rho_own"].round(3)
    show["best_other_rho"] = show["best_other_rho"].round(3)
    print(
        show[["code", "layer1", GROUP_COL, "avg_rho_own", "best_other_group", "best_other_rho"]].to_string(index=False)
    )

    print(f"\nwrote: {OUT}/l2_cohesion.csv  l2_misfits.csv  l1_clustering.csv")


if __name__ == "__main__":
    main()

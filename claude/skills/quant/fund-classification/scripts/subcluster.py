"""Sub-cluster one selection_group to characterise a SPLIT/DISSOLVE proposal.

Usage: subcluster.py "<selection_group name>"
PLN-only, latest 156w. Shows the sub-clusters (with fund names + intra-rho) so a
loose group can be split into coherent pieces or dissolved.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform

# dm-evo checkout (live data/config). DM_EVO_ROOT overrides (worktree/CI/other host);
# else the sibling dm-evo beside the lab-repo root (parents[4]).
DM = Path(os.environ.get("DM_EVO_ROOT") or (Path(__file__).resolve().parents[5] / "dm-evo"))
WINDOW, MIN_OBS, CUT_RHO = 156, 130, 0.65


def main(group: str):
    m = pd.read_csv(DM / "config/reference/fund_mapping.csv").set_index("code")
    sc = pd.read_parquet(
        DM / "data/processed/fund_selection/scores.parquet", columns=["code", "currency"]
    ).drop_duplicates("code")
    pln = set(sc[sc.currency == "PLN"].code)
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
    rets = rets[obs[obs >= MIN_OBS].index]
    corr = rets.corr(min_periods=MIN_OBS)

    members = [c for c in m.index[m.selection_group == group] if c in corr.columns]
    missing = [c for c in m.index[m.selection_group == group] if c not in corr.columns]
    C = corr.loc[members, members].to_numpy()
    D = np.sqrt(np.clip(2 * (1 - C), 0, None))
    np.fill_diagonal(D, 0.0)
    Z = linkage(squareform(D, checks=False), method="average")
    labels = fcluster(Z, t=np.sqrt(2 * (1 - CUT_RHO)), criterion="distance")

    print(f"'{group}': {len(members)} PLN funds with history ({len(missing)} no-history: {missing})")
    print(f"sub-clustered at rho>={CUT_RHO}:\n")
    for s in sorted(set(labels), key=lambda s: -(labels == s).sum()):
        idx = np.where(labels == s)[0]
        codes = [members[i] for i in idx]
        if len(idx) >= 2:
            sub = C[np.ix_(idx, idx)]
            intra = sub[~np.eye(len(idx), dtype=bool)].mean()
        else:
            intra = float("nan")
        tag = "CORE" if len(idx) == max((labels == x).sum() for x in set(labels)) else f"sub{s}"
        print(f"  [{tag}] n={len(idx)} intra_rho={intra:.3f}")
        for c in codes:
            print(f"        {c:16s} {str(nm.get(c, ''))[:46]}")
        print()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "Global Core Bonds PLN")

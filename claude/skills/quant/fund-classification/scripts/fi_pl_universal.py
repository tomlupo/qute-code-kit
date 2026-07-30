"""FI_PL 'PL Universal Bonds PLN' dissolve analysis — per-fund reclassification data.

The group is persistently incoherent (rho 0.51, intra < inter). This shows, for
each of its funds, the avg correlation to each candidate destination group so an
advisor can decide: fold to govt core, move to credit, isolate, or keep.

PLN-only, latest 156w (with a 3-window stability cross-check on the nearest group).
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

WINDOW, STEP, N_WIN, MIN_OBS = 156, 52, 3, 130
GROUP_COL = "selection_group"

# candidate destination groups a universal-bond fund could plausibly belong to
CANDIDATES = [
    "PL Govt Bonds PLN",
    "PL Universal Bonds PLN",  # own (excl self)
    "PL Corp Short Term PLN",
    "PL Govt Short Term PLN",
    "HY Bonds PLN",
    "EM Debt PLN",
]
SUBJECT = "PL Universal Bonds PLN"


def weekly_returns_pln():
    sc = pd.read_parquet(
        DM / "data/processed/fund_selection/scores.parquet", columns=["code", "currency"]
    ).drop_duplicates("code")
    pln = set(sc.loc[sc.currency == "PLN", "code"])
    px = pd.read_parquet(
        DM / "data/processed/fund_prices/fund_prices.parquet", columns=["code", "date", "price"]
    ).dropna(subset=["price"])
    px = px[px.code.isin(pln)]
    wide = px.pivot_table(index="date", columns="code", values="price", aggfunc="last").sort_index()
    return np.log(wide.resample("W-FRI").last()).diff().iloc[1:]


def names():
    q = pd.read_parquet(DM / "data/processed/quotations/quotations.parquet", columns=["code", "name"]).drop_duplicates(
        "code"
    )
    q["name"] = q["name"].astype(str).str.replace(r"\\", "", regex=True)
    return q.set_index("code")["name"]


def nearest_in_window(rets_slice, lab, subj_codes, nm):
    obs = rets_slice.notna().sum()
    rets_slice = rets_slice[obs[obs >= MIN_OBS].index]
    corr = rets_slice.corr(min_periods=MIN_OBS)
    present = [c for c in subj_codes if c in corr.columns]
    rows = {}
    for c in present:
        best_g, best_r = None, -np.inf
        for g in CANDIDATES:
            members = lab.index[(lab[GROUP_COL] == g)]
            members = [m for m in members if m in corr.columns and m != c]
            if not members:
                continue
            r = corr.loc[c, members].mean()
            if r > best_r:
                best_r, best_g = r, g
        rows[c] = (best_g, best_r)
    return rows


def main():
    lab = pd.read_csv(DM / "config/reference/fund_mapping.csv").set_index("code")[["layer1", GROUP_COL]]
    nm = names()
    weekly = weekly_returns_pln()
    n = len(weekly)
    ends = [n - 1 - STEP * k for k in range(N_WIN) if n - 1 - STEP * k - WINDOW + 1 >= 0]

    subj_codes = list(lab.index[lab[GROUP_COL] == SUBJECT])

    # latest-window full table
    sl0 = weekly.iloc[ends[0] - WINDOW + 1 : ends[0] + 1]
    obs = sl0.notna().sum()
    sl0 = sl0[obs[obs >= MIN_OBS].index]
    corr = sl0.corr(min_periods=MIN_OBS)

    rows = []
    for c in subj_codes:
        if c not in corr.columns:
            rows.append({"code": c, "name": nm.get(c, "")[:34], "note": "insufficient history"})
            continue
        rec = {"code": c, "name": str(nm.get(c, ""))[:34]}
        for g in CANDIDATES:
            members = [m for m in lab.index[lab[GROUP_COL] == g] if m in corr.columns and m != c]
            rec[g] = corr.loc[c, members].mean() if members else np.nan
        # nearest excluding own group
        ext = {g: rec[g] for g in CANDIDATES if g != SUBJECT and pd.notna(rec[g])}
        rec["nearest_ext"] = max(ext, key=ext.get) if ext else None
        rec["nearest_ext_rho"] = ext[rec["nearest_ext"]] if ext else np.nan
        rows.append(rec)
    df = pd.DataFrame(rows)

    # stability of nearest-external across windows
    near_hits = {c: [] for c in subj_codes}
    for e in ends:
        sl = weekly.iloc[e - WINDOW + 1 : e + 1]
        res = nearest_in_window(sl, lab, subj_codes, nm)
        for c, (g, r) in res.items():
            near_hits[c].append(g)
    df["nearest_stable"] = df["code"].map(
        lambda c: max(set(near_hits[c]), key=near_hits[c].count) if near_hits[c] else None
    )
    df["nearest_persist"] = df["code"].map(
        lambda c: (
            f"{near_hits[c].count(max(set(near_hits[c]), key=near_hits[c].count))}/{len(near_hits[c])}"
            if near_hits[c]
            else ""
        )
    )

    # suggestion
    def suggest(r):
        if pd.isna(r.get("nearest_ext_rho", np.nan)):
            return "isolate (no history)"
        own = r.get(SUBJECT, np.nan)
        ext, extr = r["nearest_ext"], r["nearest_ext_rho"]
        if extr < 0.45:
            return "ISOLATE (fits nothing)"
        if pd.notna(own) and own >= extr:
            return "keep in Universal (own tightest)"
        return f"-> {ext}"

    df["suggestion"] = df.apply(suggest, axis=1)
    df.to_csv(OUT / "fi_pl_universal_reclass.csv", index=False)

    pd.set_option("display.width", 200, "display.max_columns", 30, "display.float_format", lambda x: f"{x:.2f}")
    cols = ["code", "name"] + CANDIDATES + ["nearest_ext", "nearest_ext_rho", "nearest_persist", "suggestion"]
    print(f"FI_PL '{SUBJECT}' — {len(subj_codes)} funds, per-fund correlation to candidate groups (latest 156w):\n")
    print(df[cols].sort_values("nearest_ext_rho", ascending=False).to_string(index=False))
    print("\nsuggestion tally:")
    print(
        df["suggestion"].apply(lambda s: s if s.startswith(("->", "ISOLATE", "keep")) else s).value_counts().to_string()
    )
    print(f"\nwrote {OUT}/fi_pl_universal_reclass.csv")


if __name__ == "__main__":
    main()

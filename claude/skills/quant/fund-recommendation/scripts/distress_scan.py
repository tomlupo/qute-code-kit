"""distress_scan — run the distress trigger battery over a fund universe, monthly.

Tiers (doctrine: anticipatory signals FREEZE, realized signals EJECT):
  L3   hard: price stale / NAV frozen (+ external event register)      -> immediate eject
  L2   2-of-N with >=1 REALIZED signal (crash, tracking break)         -> eject from E
  L1.5 2-of-N anticipatory only (flow run, ML gate)                    -> freeze (no new money)
  L1   any single signal                                               -> watch

Thresholds below are the BEST-GUESS set (see references/process_spec.md for the
status ledger); calibrate via the label-set sweep before promoting to v1.0.

Usage:  python distress_scan.py
Output: tier counts per month + named L2/L3 fund-months.

--- DATA-LOADING SEAM (adapt for your universe) -------------------------------
load_universe() -> {code: {"group": str, "flow_series": [..]|None, "flow_months": [..]|None,
                           "ml_flag": bool}}      (ml_flag = anticipatory model gate, optional)
load_prices(codes) -> wide daily price DataFrame (date x code).
The dm-evo reference reads the dashboard data JSON + dm-evo fund_prices.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

# --- BEST-GUESS THRESHOLDS ----------------------------------------------------
FLOW_3M = -0.10  # 3m net flow <= -10% of AUM
FLOW_STREAK = 5  # or >=5 consecutive negative months
CRASH_SIG = 2.0  # 13w return < group median - 2*sigma_group
TRACK_LO, TRACK_BASE = 0.30, 0.60  # rho_13w < 0.30 while rho_156w >= 0.60
STALE_D, FROZEN_W = 30, 8  # price stale > 30d / NAV unchanged >= 8 weeks
MIN_GROUP = 5  # min funds for crash/track group stats
EOMS = ["2026-01-30", "2026-02-27", "2026-03-27", "2026-04-24", "2026-05-22"]

# --- seam: dm-evo reference loaders -------------------------------------------
LAB = Path(
    os.environ.get("DM_EVO_LAB_RESEARCH") or Path(__file__).resolve().parents[4] / "research/selection-l2-taxonomy"
)
DM = Path(os.environ.get("DM_EVO_ROOT") or Path(__file__).resolve().parents[5] / "dm-evo")


def load_universe() -> dict[str, dict]:
    run = sorted((LAB / "output" / "dashboard_runs").iterdir())[-1]
    d = json.loads((run / "dashboard_data.json").read_text())
    return {
        f["code"]: {
            "group": f["group"],
            "flow_series": f.get("flow_series"),
            "flow_months": f.get("flow_months"),
            "ml_flag": "ml_elevated" in f.get("chips", []),  # static — no history (upper bound)
        }
        for f in d["funds"]
        if not f["is_bench"] and f["is_evo"]
    }


def load_prices(codes) -> pd.DataFrame:
    px = pd.read_parquet(
        DM / "data/processed/fund_prices/fund_prices.parquet", columns=["code", "date", "price"]
    ).dropna()
    px = px[px.code.isin(codes)]
    return px.pivot_table(index="date", columns="code", values="price").sort_index()


# --- universe-agnostic battery --------------------------------------------------
def scan() -> pd.DataFrame:
    uni = load_universe()
    wide = load_prices(set(uni))
    wk = wide.resample("W-FRI").last()
    wr = np.log(wk).diff()
    gser = pd.Series({c: u["group"] for c, u in uni.items()})
    rows = []
    for dt in EOMS:
        t = pd.Timestamp(dt)
        idx = wk.index[wk.index <= t]
        w13 = wr.loc[idx[-13] : idx[-1]]
        w156 = wr.loc[idx[-156] : idx[-1]] if len(idx) >= 156 else wr.loc[: idx[-1]]
        ret13 = (np.exp(w13.sum()) - 1).where(w13.notna().sum() >= 10)
        crash, track, frozen, flow = set(), set(), set(), set()
        for g, members in gser.groupby(gser).groups.items():
            m = [c for c in members if c in ret13.index and pd.notna(ret13[c])]
            if len(m) < MIN_GROUP:
                continue
            med, sig = ret13[m].median(), ret13[m].std()
            crash |= {c for c in m if sig and ret13[c] < med - CRASH_SIG * sig}
            gi13, gi156 = w13[m].mean(axis=1), w156[m].mean(axis=1)
            for c in m:
                r13 = w13[c].corr(gi13 - w13[c] / len(m))
                rb = w156[c].corr(gi156 - w156[c] / len(m))
                if pd.notna(r13) and pd.notna(rb) and r13 < TRACK_LO and rb >= TRACK_BASE:
                    track.add(c)
        for c in uni:
            if c not in wide.columns:
                continue
            s = wide[c].dropna()
            s = s[s.index <= t]
            if s.empty:
                continue
            if (t - s.index[-1]).days > STALE_D or (
                len(s.tail(FROZEN_W)) >= FROZEN_W and s.tail(FROZEN_W).nunique() == 1
            ):
                frozen.add(c)
            u = uni[c]
            ser, mo = u["flow_series"], u["flow_months"]
            if ser and mo:
                upto = [v for m, v in zip(mo, ser) if m <= dt[:7] and v is not None]
                if len(upto) >= 3 and sum(upto[-3:]) / 100 <= FLOW_3M:
                    flow.add(c)
                streak = 0
                for v in reversed(upto):
                    if v < 0:
                        streak += 1
                    else:
                        break
                if streak >= FLOW_STREAK:
                    flow.add(c)
        for c, u in uni.items():
            sig = {"flow": c in flow, "ml": u["ml_flag"], "crash": c in crash, "track": c in track}
            n = sum(sig.values())
            realized = sig["crash"] or sig["track"]
            if c in frozen:
                tier = "L3"
            elif n >= 2 and realized:
                tier = "L2"
            elif n >= 2:
                tier = "L1.5"
            elif n == 1:
                tier = "L1"
            else:
                continue
            rows.append(
                {
                    "date": dt,
                    "code": c,
                    "tier": tier,
                    "group": u["group"],
                    "signals": "+".join(k for k, v in sig.items() if v) or "frozen",
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    df = scan()
    print(
        df.pivot_table(index="date", columns="tier", values="code", aggfunc="count").fillna(0).astype(int).to_string()
    )
    print("\nL3 funds:", sorted(df[df.tier == "L3"].code.unique()))
    print("\nL2 (realized eject) fund-months:")
    for _, r in df[df.tier == "L2"].iterrows():
        print(f"  {r['date']}  {r['code']:16s} {r['group']:26s} {r['signals']}")


if __name__ == "__main__":
    main()

"""ew_cadence — simulate the E/W recommendation cadence on a monthly score panel.

Structure per group: E = 2*slots (primaries + named replacements, all recommended),
W = staging gate (rank-refreshed, tenure tracked). Rank-based hysteresis variants:

  A: challenger out-ranks incumbent 2 consecutive EoMs   (too twitchy at monthly cadence)
  B: 3 consecutive EoMs                                  (recommended — validated 0-trade YTD)
  C: better trailing-3-EoM median rank                   (reacts like A — not recommended)

Usage:  python ew_cadence.py <GROUP_NAME> [SLOTS]
Output: per-variant monthly table (primaries / replacements / W / events) + trade count.

--- DATA-LOADING SEAM (adapt for your universe) -------------------------------
load_panel(group) must return ({eom_date_str: {code: composite_score}}, [eligible codes]).
The dm-evo reference reads the production monthly pillar panel (4P pillars, re-weighted
to the 3P composite) + the lab anchor month, and excludes young-track funds. Only the
WITHIN-GROUP ORDERING is consumed, so composite scale changes across sources are fine.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd

# --- seam: dm-evo reference loader -------------------------------------------
LAB = Path(
    os.environ.get("DM_EVO_LAB_RESEARCH") or Path(__file__).resolve().parents[4] / "research/selection-l2-taxonomy"
)
DM = Path(os.environ.get("DM_EVO_ROOT") or Path(__file__).resolve().parents[5] / "dm-evo")
W3 = {"pillar_momentum": 0.50, "pillar_consistency": 0.25, "pillar_quality": 0.25}
EOMS = ["2025-12-31", "2026-01-31", "2026-02-28", "2026-03-31", "2026-04-24"]  # + lab anchor below
HYST_STREAK = {"A": 2, "B": 3}  # C = trailing-median, handled separately
W_TENURE_MIN = 1  # months on W before E-eligibility


def load_panel(group: str) -> tuple[dict[str, dict[str, float]], list[str]]:
    run = sorted((LAB / "output" / "dashboard_runs").iterdir())[-1]
    d = json.loads((run / "dashboard_data.json").read_text())
    members = [f["code"] for f in d["funds"] if not f["is_bench"] and f["is_evo"] and f["group"] == group]
    young = {f["code"] for f in d["funds"] if not f["is_bench"] and "young" in f.get("chips", [])}
    s = pd.read_parquet(DM / "data/processed/fund_selection/scores.parquet", columns=["date", "code", *W3])
    s = s[s.code.isin(members)].copy()
    s["date"] = pd.to_datetime(s["date"])
    s["c"] = sum(s[c] * w for c, w in W3.items())
    panel = {dt: s[s.date == dt].set_index("code")["c"].to_dict() for dt in EOMS}
    ev = pd.read_parquet(LAB / "output/score_evo_3p.parquet")
    panel["2026-05-22"] = ev[ev.code.isin(members)].set_index("code")["score_i"].to_dict()
    return panel, [c for c in members if c not in young]


# --- universe-agnostic simulator ----------------------------------------------
def month_ranks(panel: dict, elig: list[str]) -> dict[str, dict[str, int]]:
    out = {}
    for dt, sc in panel.items():
        v = {c: sc.get(c) for c in elig if pd.notna(sc.get(c))}
        out[dt] = {c: i + 1 for i, c in enumerate(sorted(v, key=lambda c: -v[c]))}
    return out


def simulate(panel: dict, elig: list[str], slots: int, variant: str):
    ranks = month_ranks(panel, elig)
    months = list(panel)
    n_e = 2 * slots
    E_pri = E_rep = W = None
    tenW, stEW, stInE = {}, {}, {}
    trades, hist = 0, []
    for i, dt in enumerate(months):
        r, events = ranks[dt], []
        if E_pri is None:
            order = sorted(r, key=r.get)
            E_pri, E_rep, W = order[:slots], order[slots:n_e], order[n_e : n_e + 2]
            for w in W:
                tenW[w] = 1
            hist.append((dt, E_pri[:], E_rep[:], W[:], "seed"))
            continue

        def med(c, k=3):
            win = months[max(0, i - k + 1) : i + 1]
            return pd.Series([ranks[m].get(c, 99) for m in win]).median()

        def fires(streaks, c):
            need = HYST_STREAK.get(variant)
            return streaks.get(c, 0) >= need if need else None

        # replacement -> primary (a client trade)
        weak_p = max(E_pri, key=lambda c: r.get(c, 99))
        for c in E_rep:
            stInE[c] = stInE.get(c, 0) + 1 if r.get(c, 99) < r.get(weak_p, 99) else 0
        cand = [c for c in E_rep if (fires(stInE, c) if variant != "C" else med(c) < med(weak_p))]
        if cand:
            ch = min(cand, key=lambda c: r.get(c, 99))
            E_pri = [c for c in E_pri if c != weak_p] + [ch]
            E_rep = [c for c in E_rep if c != ch] + [weak_p]
            trades += 1
            events.append(f"PRIMARY swap {weak_p}->{ch}")
            stInE = {}
        # W -> E (bench change, trade-free unless a primary fell)
        bot_e = max(E_pri + E_rep, key=lambda c: r.get(c, 99))
        for c in W:
            stEW[c] = stEW.get(c, 0) + 1 if r.get(c, 99) < r.get(bot_e, 99) else 0
        cand = [
            c
            for c in W
            if tenW.get(c, 0) >= W_TENURE_MIN and (fires(stEW, c) if variant != "C" else med(c) < med(bot_e))
        ]
        if cand:
            ch = min(cand, key=lambda c: r.get(c, 99))
            if bot_e in E_pri:
                stepup = min(E_rep, key=lambda c: r.get(c, 99))
                E_pri = [c for c in E_pri if c != bot_e] + [stepup]
                E_rep = [c for c in E_rep if c != stepup] + [ch]
                trades += 1
                events.append(f"E-exit {bot_e}; step-up {stepup}; W->E {ch}")
            else:
                E_rep = [c for c in E_rep if c != bot_e] + [ch]
                events.append(f"E-exit {bot_e}; W->E {ch} (bench, no trade)")
            W = [c for c in W if c != ch]
            stEW = {}
        inE = set(E_pri) | set(E_rep)
        W = [c for c in sorted(r, key=r.get) if c not in inE][:2]
        for c in W:
            tenW[c] = tenW.get(c, 0) + 1
        E_pri.sort(key=lambda c: r.get(c, 99))
        E_rep.sort(key=lambda c: r.get(c, 99))
        hist.append((dt, E_pri[:], E_rep[:], W[:], "; ".join(events)))
    return trades, hist


def main() -> None:
    group = sys.argv[1] if len(sys.argv) > 1 else "PL Govt Bonds"
    slots = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    panel, elig = load_panel(group)
    print(f"group={group} | slots={slots} | eligible={len(elig)}")
    for v, label in [("A", "rank-streak 2m"), ("B", "rank-streak 3m  <- recommended"), ("C", "3m median rank")]:
        trades, hist = simulate(panel, elig, slots, v)
        print(f"\n=== variant {v} ({label}) — primary trades: {trades} ===")
        for dt, ep, er, w, ev in hist:
            print(f"{dt}  P:[{','.join(ep)}] R:[{','.join(er)}] W:[{','.join(w)}] {ev}")


if __name__ == "__main__":
    main()

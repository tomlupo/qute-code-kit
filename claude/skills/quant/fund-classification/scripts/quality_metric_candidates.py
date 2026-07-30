"""Quality-pillar metric replacement — candidate correlation study.

The quality pillar = sortino + profit_factor; both -> inf on a no-loss (cash)
series. Goal: find 2 robust replacements that (a) rank-correlate tightly with the
originals on RISK-BEARING funds (so model behaviour is preserved) and (b) degrade
gracefully at zero downside. Method (per request): compute a basket of candidate
indicators across the PLN universe and rank by Spearman corr with sortino /
profit_factor; flag which still divide by a downside quantity (need a guard) vs
which are bounded.

PLN funds, latest 156w weekly. Correlations computed on funds with FINITE
sortino & profit_factor (i.e. risk-bearing; cash excluded by construction).
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
WINDOW, MIN_OBS, A = 156, 130, 52  # weekly annualization

# candidate -> (divides_by_downside_so_needs_guard, higher_is_better, magnitude_aware)
META = {
    "sortino": (True, True, True),
    "profit_factor": (True, True, True),  # originals
    "omega_mar0": (True, True, True),
    "tail_ratio": (True, True, True),
    "gain_to_pain": (True, True, True),
    "calmar": (True, True, True),
    "sharpe": (True, True, True),
    "win_rate": (False, True, False),
    "neg_max_dd": (False, True, True),
    "neg_ulcer": (False, True, True),
    "neg_downside_dev": (False, True, True),
}


def fund_metrics(r: pd.Series) -> dict | None:
    r = r.dropna()
    if len(r) < MIN_OBS:
        return None
    ann = np.expm1(r.mean() * A)
    std = r.std() * np.sqrt(A)
    dn = r[r < 0]
    downside = np.sqrt((dn**2).mean()) * np.sqrt(A) if len(dn) else 0.0
    cum = (1 + r).cumprod()
    dd = cum / cum.cummax() - 1
    mdd = dd.min()
    gains, losses = r[r > 0].sum(), -r[r < 0].sum()
    p95, p05 = r.quantile(0.95), r.quantile(0.05)
    return {
        "sortino": ann / downside if downside > 0 else np.nan,
        "profit_factor": gains / losses if losses > 0 else np.nan,
        "omega_mar0": gains / losses if losses > 0 else np.nan,  # = profit_factor at MAR=0
        "tail_ratio": abs(p95) / abs(p05) if p05 < 0 else np.nan,
        "gain_to_pain": r.sum() / losses if losses > 0 else np.nan,
        "calmar": ann / abs(mdd) if mdd < 0 else np.nan,
        "sharpe": ann / std if std > 0 else np.nan,
        "win_rate": (r > 0).mean(),
        "neg_max_dd": mdd,  # <=0, higher (closer 0) = better
        "neg_ulcer": -np.sqrt((dd**2).mean()),
        "neg_downside_dev": -downside,
    }


def main():
    sc = pd.read_parquet(
        DM / "data/processed/fund_selection/scores.parquet", columns=["code", "currency"]
    ).drop_duplicates("code")
    pln = set(sc[sc.currency == "PLN"].code)
    px = pd.read_parquet(
        DM / "data/processed/fund_prices/fund_prices.parquet", columns=["code", "date", "price"]
    ).dropna(subset=["price"])
    px = px[px.code.isin(pln)]
    wide = px.pivot_table(index="date", columns="code", values="price", aggfunc="last").sort_index()
    rets = np.log(wide.resample("W-FRI").last()).diff().iloc[1:].iloc[-(WINDOW + 1) :]

    rows = {c: fund_metrics(rets[c]) for c in rets.columns}
    F = pd.DataFrame({c: v for c, v in rows.items() if v}).T
    n_all = len(F)
    risky = F.dropna(subset=["sortino", "profit_factor"])  # finite originals
    print(
        f"PLN funds with history: {n_all}  |  risk-bearing (finite sortino & PF): {len(risky)}  |  no-loss/cash-like (sortino=nan): {F['sortino'].isna().sum()}"
    )

    corr = pd.DataFrame(index=[c for c in META if c not in ("sortino", "profit_factor")])
    corr["rank_corr_sortino"] = [risky[c].corr(risky["sortino"], method="spearman") for c in corr.index]
    corr["rank_corr_profit_factor"] = [risky[c].corr(risky["profit_factor"], method="spearman") for c in corr.index]
    corr["needs_guard(÷downside)"] = [META[c][0] for c in corr.index]
    corr["magnitude_aware"] = [META[c][2] for c in corr.index]
    corr = corr.sort_values("rank_corr_sortino", ascending=False)

    pd.set_option("display.width", 130, "display.float_format", lambda x: f"{x:.3f}")
    print(
        f"\n{'=' * 80}\nSpearman rank-corr of candidates vs originals (risk-bearing funds, n={len(risky)}):\n{'=' * 80}"
    )
    print(corr.to_string())
    corr.to_csv(OUT / "quality_metric_candidates.csv")

    # how many funds is each candidate DEFINED for (robustness across whole universe incl cash)?
    print(f"\n=== coverage: % of ALL {n_all} funds with a finite value (higher = more robust) ===")
    cov = (F.notna().mean() * 100).round(1).sort_values(ascending=False)
    print(cov.to_string())
    print(f"\nwrote {OUT}/quality_metric_candidates.csv")


if __name__ == "__main__":
    main()

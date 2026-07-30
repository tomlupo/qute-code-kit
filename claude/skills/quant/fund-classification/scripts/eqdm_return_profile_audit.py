"""EQ_DM return-profile role audit.

This is a review aid for the core/style/thematic distinction. It does not edit
taxonomy files. It compares each EQ_DM fund's weekly PLN return profile against
broad/style/thematic ETF anchors converted to PLN, then emits candidates whose
current L2 or alloc_role may deserve human review.
"""

from __future__ import annotations

import math
import os
from pathlib import Path

import numpy as np
import pandas as pd

DM = Path(os.environ.get("DM_EVO_ROOT") or Path(__file__).resolve().parents[4])
OUT = Path(__file__).resolve().parent / "output"
OUT.mkdir(exist_ok=True)

LAYER1 = "EQ_DM"
ANCHORS = ("URTH", "SPY", "QQQ")
WINDOWS = {"1Y": 52, "3Y": 156, "5Y": 260}
MIN_WEEKS = 104


def _annual_return(returns: pd.Series) -> float:
    returns = returns.dropna()
    if returns.empty:
        return np.nan
    return float((1 + returns).prod() ** (52 / len(returns)) - 1)


def _annual_vol(returns: pd.Series) -> float:
    returns = returns.dropna()
    if len(returns) < 2:
        return np.nan
    return float(returns.std() * math.sqrt(52))


def _max_drawdown(returns: pd.Series) -> float:
    returns = returns.dropna()
    if returns.empty:
        return np.nan
    curve = (1 + returns).cumprod()
    return float((curve / curve.cummax() - 1).min())


def _load_usdpln() -> pd.Series:
    nbp = pd.read_parquet(DM / "data/raw/tactical-signals/nbp.parquet")
    nbp = nbp[nbp["series_name"].eq("USDPLN")].copy()
    nbp["observation_date"] = pd.to_datetime(nbp["observation_date"])
    return nbp.set_index("observation_date")["value"].sort_index()


def _load_weekly_returns(codes: list[str]) -> pd.DataFrame:
    prices = pd.read_parquet(
        DM / "data/processed/fund_prices/fund_prices.parquet",
        columns=["code", "date", "price", "currency"],
    )
    prices = prices[prices["code"].isin(codes + list(ANCHORS))].dropna(subset=["price"]).copy()
    prices["date"] = pd.to_datetime(prices["date"])
    wide = prices.pivot_table(index="date", columns="code", values="price", aggfunc="last").sort_index()
    wide = wide.join(_load_usdpln().rename("USDPLN"), how="left")
    wide["USDPLN"] = wide["USDPLN"].ffill()
    for anchor in ANCHORS:
        if anchor in wide:
            wide[f"{anchor}_PLN"] = wide[anchor] * wide["USDPLN"]
    cols = codes + [f"{anchor}_PLN" for anchor in ANCHORS if f"{anchor}_PLN" in wide]
    weekly = wide[cols].resample("W-FRI").last()
    return weekly.pct_change()


def _load_eqdm_universe() -> pd.DataFrame:
    mapping = pd.read_csv(DM / "config/reference/fund_mapping.csv")
    master = pd.read_csv(DM / "config/reference/instrument_master.csv")
    mapping = mapping[mapping["layer1"].eq(LAYER1)].copy()
    mapping = mapping[~mapping["dedup_exclude"].fillna(False).astype(bool)]
    mapping = mapping.merge(
        master[["code", "name", "currency", "role", "is_evo", "excluded_reason"]],
        on="code",
        how="left",
    )
    mapping = mapping[mapping["role"].eq("product")]
    mapping = mapping[mapping["excluded_reason"].fillna("").eq("")]
    return mapping.sort_values(["layer2", "code"])


def _best_anchor_metrics(fund_returns: pd.Series, returns: pd.DataFrame) -> dict[str, float | str]:
    rows = []
    metrics: dict[str, float | str] = {}
    for anchor in ANCHORS:
        col = f"{anchor}_PLN"
        if col not in returns:
            continue
        pair = pd.concat([fund_returns, returns[col]], axis=1, sort=False).dropna()
        pair.columns = ["fund", "anchor"]
        if len(pair) < MIN_WEEKS:
            continue
        beta = pair["fund"].cov(pair["anchor"]) / pair["anchor"].var()
        metrics[f"{anchor.lower()}_corr"] = pair["fund"].corr(pair["anchor"])
        metrics[f"{anchor.lower()}_beta"] = beta
        rows.append(
            {
                "anchor": anchor,
                "corr": pair["fund"].corr(pair["anchor"]),
                "beta": beta,
                "anchor_ann_return": _annual_return(pair["anchor"]),
                "anchor_ann_vol": _annual_vol(pair["anchor"]),
                "anchor_max_dd": _max_drawdown(pair["anchor"]),
            }
        )
    if not rows:
        return {
            "best_anchor": pd.NA,
            "best_anchor_corr": np.nan,
            "best_anchor_beta": np.nan,
            "best_anchor_ann_return": np.nan,
            "best_anchor_ann_vol": np.nan,
            "best_anchor_max_dd": np.nan,
        }
    best = max(rows, key=lambda row: row["corr"])
    metrics.update({f"best_anchor_{k}" if k != "anchor" else "best_anchor": v for k, v in best.items()})
    return metrics


def _holdings_profile(code: str) -> dict[str, float | str]:
    path = DM / "data/published/holdings.parquet"
    if not path.exists():
        return {"holdings_date": pd.NA, "holdings_n": np.nan, "top10_pct": np.nan, "usd_pct": np.nan}
    holdings = pd.read_parquet(path)
    sub = holdings[holdings["analizy_code"].astype(str).eq(code)].copy()
    if sub.empty:
        return {"holdings_date": pd.NA, "holdings_n": np.nan, "top10_pct": np.nan, "usd_pct": np.nan}
    sub["report_date"] = pd.to_datetime(sub["report_date"])
    latest = sub[sub["report_date"].eq(sub["report_date"].max())].copy()
    latest["share_percentage"] = pd.to_numeric(latest["share_percentage"], errors="coerce")
    return {
        "holdings_date": latest["report_date"].max().date().isoformat(),
        "holdings_n": int(len(latest)),
        "top10_pct": float(latest.nlargest(10, "share_percentage")["share_percentage"].sum()),
        "usd_pct": float(latest.loc[latest["currency"].eq("USD"), "share_percentage"].sum()),
    }


def _candidate(row: pd.Series) -> tuple[str, str]:
    layer2 = str(row["layer2"])
    layer3 = str(row.get("layer3", ""))
    role = str(row.get("alloc_role", ""))
    qqq_beta = row.get("qqq_beta", np.nan)
    qqq_corr = row.get("qqq_corr", np.nan)
    vol = row["ann_vol_3y"]
    dd = row["max_dd_3y"]

    thematic_terms = (
        "technology",
        "technologii",
        "tech",
        "innovation",
        "innowacji",
        "biotech",
        "healthcare",
        "medycz",
        "climate",
        "energy",
        "energ",
        "water",
        "infrastructure",
        "consumer trends",
        "space",
        "cyber",
        "natural resources",
        "nieruchomo",
        "real estate",
    )
    looks_thematic = (
        pd.notna(qqq_beta)
        and qqq_beta >= 1.20
        and pd.notna(qqq_corr)
        and qqq_corr >= 0.70
        and (pd.notna(vol) and vol >= 0.28 or pd.notna(dd) and dd <= -0.32)
    )
    name_blob = f"{row['name']} {layer3}".lower()
    name_theme = any(term in name_blob for term in thematic_terms)

    if layer2 == "Thematic/Sector":
        if layer3 in {"Dividend/Income"}:
            return "review_thematic_to_style", "income/dividend behaves more like style than sector"
        if layer3 in {"Sustainable/ESG", "ESG-integrated"} and not name_theme:
            return "review_thematic_to_style", "ESG label may be style/overlay, not narrow theme"
        return "confirm_thematic_satellite", "thematic L2 remains capped satellite"

    if layer2 in {"Global Blend", "Global Style", "US Regional Equity"}:
        if looks_thematic or (name_theme and layer2 != "US Regional Equity"):
            return "review_core_to_thematic", "core/style L2 but thematic/high-beta profile"
        if role != "core":
            return "review_alloc_role", "core L2 with non-core alloc_role"
        return "confirm_core_or_style", "core/style behavior acceptable"

    if layer2 == "Ex-US Regional Equity":
        return "confirm_regional_satellite", "regional sleeve, not broad core"

    if layer2 == "Gold & Mining":
        return "confirm_sector_satellite", "sector sleeve, capped satellite"

    return "review_other", "unhandled EQ_DM L2"


def main() -> None:
    universe = _load_eqdm_universe()
    codes = universe["code"].astype(str).tolist()
    returns = _load_weekly_returns(codes)
    rows = []
    for _, meta in universe.iterrows():
        code = str(meta["code"])
        if code not in returns:
            continue
        fund_returns = returns[code].dropna()
        if len(fund_returns) < MIN_WEEKS:
            status, reason = "insufficient_history", f"{len(fund_returns)} weekly returns"
        else:
            status, reason = "pending", ""
        row = meta.to_dict()
        row["weeks"] = int(len(fund_returns))
        for label, weeks in WINDOWS.items():
            sub = fund_returns.tail(weeks)
            suffix = label.lower()
            row[f"ann_return_{suffix}"] = _annual_return(sub)
            row[f"ann_vol_{suffix}"] = _annual_vol(sub)
            row[f"max_dd_{suffix}"] = _max_drawdown(sub)
            row[f"total_return_{suffix}"] = float((1 + sub).prod() - 1) if len(sub) else np.nan
        row.update(_best_anchor_metrics(fund_returns.tail(WINDOWS["3Y"]), returns.tail(WINDOWS["3Y"])))
        row.update(_holdings_profile(code))
        if status == "pending":
            status, reason = _candidate(pd.Series(row))
        row["audit_status"] = status
        row["audit_reason"] = reason
        rows.append(row)

    out = pd.DataFrame(rows)
    pct_cols = [
        c
        for c in out.columns
        if c.startswith(("ann_return_", "ann_vol_", "max_dd_", "total_return_"))
        or c
        in {
            "best_anchor_corr",
            "best_anchor_beta",
            "best_anchor_ann_return",
            "best_anchor_ann_vol",
            "best_anchor_max_dd",
            "top10_pct",
            "usd_pct",
        }
    ]
    csv_out = OUT / "eqdm_return_profile_audit.csv"
    out.to_csv(csv_out, index=False)

    review = out[out["audit_status"].astype(str).str.startswith("review_")].copy()
    review = review.sort_values(["audit_status", "layer2", "code"])
    md_out = OUT / "eqdm_return_profile_audit.md"
    with md_out.open("w", encoding="utf-8") as fh:
        fh.write("# EQ_DM Return-Profile Role Audit\n\n")
        fh.write("Review aid only. This file does not change taxonomy.\n\n")
        fh.write(f"- funds: {len(out)}\n")
        fh.write(f"- review candidates: {len(review)}\n")
        fh.write("- anchors: URTH/SPY/QQQ converted to PLN with NBP USDPLN\n\n")
        fh.write("## Status Counts\n\n")
        fh.write(out["audit_status"].value_counts().to_frame("count").to_markdown())
        fh.write("\n\n## Review Candidates\n\n")
        if review.empty:
            fh.write("No review candidates.\n")
        else:
            cols = [
                "code",
                "name",
                "layer2",
                "layer3",
                "alloc_role",
                "audit_status",
                "audit_reason",
                "weeks",
                "ann_return_3y",
                "ann_vol_3y",
                "max_dd_3y",
                "best_anchor",
                "best_anchor_corr",
                "best_anchor_beta",
                "qqq_corr",
                "qqq_beta",
                "top10_pct",
                "usd_pct",
            ]
            pretty = review[cols].copy()
            for col in [c for c in pretty.columns if c in pct_cols]:
                pretty[col] = pretty[col].map(lambda x: "" if pd.isna(x) else round(float(x), 4))
            fh.write(pretty.to_markdown(index=False))
            fh.write("\n")

    display = out.copy()
    for col in pct_cols:
        if col in display:
            display[col] = display[col].map(lambda x: np.nan if pd.isna(x) else round(float(x), 4))
    print(f"wrote {csv_out}")
    print(f"wrote {md_out}")
    print("\nStatus counts:")
    print(out["audit_status"].value_counts().to_string())
    if not review.empty:
        print("\nReview candidates:")
        cols = ["code", "name", "layer2", "layer3", "audit_status", "ann_return_3y", "ann_vol_3y", "max_dd_3y", "best_anchor", "best_anchor_corr", "best_anchor_beta", "qqq_corr", "qqq_beta"]
        print(display.loc[review.index, cols].to_string(index=False))


if __name__ == "__main__":
    main()

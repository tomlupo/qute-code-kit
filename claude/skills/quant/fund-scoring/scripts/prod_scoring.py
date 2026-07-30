"""Compute fresh production fund scores at an arbitrary as_of date.

Mirrors dm-evo's pipelines/fund_selection/compute_scores.py main() flow (load
universe -> prices -> freshness gate -> ML pillars -> score_funds) but returns
the frames in-memory instead of writing scores.parquet. Lets score_evo anchor on
a freshly-computed cross-section (e.g. 2026-05-22) rather than the stale
2026-04-24 snapshot. 4-pillar when ml_dataset covers the date, else 3-pillar.
"""

from __future__ import annotations

import sys
import os
from pathlib import Path

import pandas as pd

DM = Path(os.environ.get("DM_EVO_ROOT") or Path(__file__).resolve().parents[3] / "dm-evo")
# dm-evo is src-layout: pipelines import `src.X`, src modules import top-level
# `shared.X`/`fund_scoring.X`. Put BOTH on path so all internal imports resolve
# to this checkout (else top-level `shared` resolves to a stale site-packages
# copy whose PROJECT_ROOT points into the venv). See CLAUDE.md live-dev hatch.
sys.path.insert(0, str(DM / "src"))
sys.path.insert(0, str(DM))

from src.fund_scoring import ScoringConfig, score_funds  # noqa: E402
from src.fund_scoring.frequency import WEEKLY, resample_prices  # noqa: E402
from src.fund_scoring.freshness import filter_freshness  # noqa: E402
from src.fund_scoring.loaders import load_prices, load_scoring_universe  # noqa: E402
from src.fund_scoring.ml.inference import compute_ml_pillars  # noqa: E402


def compute_fresh_scores(as_of: str, max_lag_days: int = 5):
    """Return (scores_df, detail_df) computed as of `as_of` (W-FRI cadence)."""
    scoring_date = pd.Timestamp(as_of)
    codes, scoring_category, benchmark_category, currency = load_scoring_universe(as_of=scoring_date)
    prices = load_prices(codes)
    prices = prices[prices.index <= scoring_date]

    codes, _diag = filter_freshness(codes, prices, scoring_date, max_lag_days=max_lag_days, strict=False)
    fresh = set(codes)
    prices = prices[[c for c in prices.columns if c in fresh]]
    scoring_category = scoring_category.reindex(codes).dropna()
    benchmark_category = benchmark_category.reindex(codes).dropna()
    currency = currency.reindex(codes).dropna()

    target_date = pd.Timestamp(resample_prices(prices, WEEKLY).index.max())
    ml_pillars = compute_ml_pillars(scoring_category, target_date)
    config = ScoringConfig.tactical_4p() if ml_pillars is not None else ScoringConfig.tactical_3p()

    scores, detail = score_funds(
        prices,
        scoring_category,
        benchmark_category=benchmark_category,
        config=config,
        ml_pillar_scores=ml_pillars,
        freq=WEEKLY,
        detail_for_date=target_date,
        currency=currency,
    )
    scores["currency"] = scores["code"].map(currency)
    scores["benchmark_category"] = scores["code"].map(benchmark_category)
    detail["currency"] = detail["code"].map(currency)
    return scores, detail, target_date


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", default="2026-05-22")
    a = ap.parse_args()
    scores, detail, target = compute_fresh_scores(a.as_of)
    out = Path(__file__).resolve().parent / "output"
    out.mkdir(exist_ok=True)
    detail[detail["date"] == target].to_parquet(out / "fresh_detail.parquet", index=False)
    scores[scores["date"] == target].to_parquet(out / "fresh_scores.parquet", index=False)
    latest = scores[scores["date"] == scores["date"].max()]
    print(f"requested as_of={a.as_of} | emission date={target.date()}")
    print(f"scored rows (all dates)={len(scores)} | latest-date funds={len(latest)}")
    print(
        f"latest-date 4-pillar (pillar_ml non-null)={latest['pillar_ml'].notna().sum()} | "
        f"3-pillar fallback={latest['pillar_ml'].isna().sum()}"
    )
    pln = latest[latest["currency"] == "PLN"]
    print(f"PLN funds at emission date={len(pln)} | categories={pln['category'].nunique()}")

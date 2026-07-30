"""Fetch GDX (VanEck Gold Miners ETF, USD) -> snapshot for the Gold & Mining
Equity benchmark.

The registry has no gold-miners series (COM_GOLD is bullion, not miners), so the
'Gold & Mining Equity' L2 group was unanchored. GDX is the standard gold-miners
benchmark. Currency-agnostic per the score_evo decision (no FX conversion).
Pulled from Yahoo's public chart API (adjusted close, dividend-inclusive); no key
or extra dependency. Snapshot to data/gdx.parquet for reproducibility.
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parent / "data"
OUT.mkdir(exist_ok=True)
URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/GDX"
    "?period1=1514764800&period2=1780000000&interval=1d"  # 2018-01-01 .. ~2026-06
)


def main():
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        js = json.loads(r.read().decode())
    res = js["chart"]["result"][0]
    ts = pd.to_datetime(res["timestamp"], unit="s").normalize()
    adj = res["indicators"]["adjclose"][0]["adjclose"]
    df = pd.DataFrame({"date": ts, "GDX": adj}).dropna()
    df = df.drop_duplicates("date").sort_values("date").reset_index(drop=True)
    df.to_parquet(OUT / "gdx.parquet", index=False)
    print(f"GDX: {df.date.min().date()} -> {df.date.max().date()} ({len(df)} obs)")
    print(f"wrote {OUT}/gdx.parquet")


if __name__ == "__main__":
    main()

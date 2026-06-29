#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pandas>=2.0",
#   "requests>=2.28",
#   "python-dotenv>=1.0",
# ]
# ///
"""
CoinGecko fetcher — daily crypto price / market-cap / volume.

Rounds out the skill's crypto floor alongside CCXT (which gives exchange OHLCV):
CoinGecko is keyed by *coin id* (e.g. ``bitcoin``, ``ethereum``) and is the
right source for market-cap and cross-exchange daily price/volume.

Free / Demo tier works with no key (rate-limited ~10-30 req/min); a demo key
(`COINGECKO_API_KEY`) raises the limit and is sent as the `x-cg-demo-api-key`
header.

Usage:
    uv run fetch_coingecko.py bitcoin 2024-01-01 2024-12-31
    uv run fetch_coingecko.py ethereum 2024-01-01
    uv run fetch_coingecko.py                 # self-test
"""

import os
import sys
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
import requests

from utils import (
    create_identifier,
    get_cache_manager,
    get_rate_limiter,
    handle_api_error,
    normalize_date,
)


class CoinGeckoFetcher:
    """Fetcher for CoinGecko daily market data (price / mcap / volume)."""

    BASE_URL = "https://api.coingecko.com/api/v3"

    def __init__(
        self,
        api_key: Optional[str] = None,
        use_cache: bool = True,
        cache_hours: int = 24,
    ):
        self.api_key = api_key or os.environ.get("COINGECKO_API_KEY")
        self.use_cache = use_cache
        self.cache_hours = cache_hours
        self.cache = get_cache_manager()
        self.rate_limiter = get_rate_limiter()

    def fetch(
        self,
        coin_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        vs_currency: str = "usd",
    ) -> pd.DataFrame:
        """Fetch daily history for a CoinGecko coin id.

        Returns a standardized DataFrame: Date, Close, Market_Cap, Volume.
        """
        coin_id = coin_id.lower()
        cache_id = create_identifier(
            f"{coin_id}_{vs_currency}",
            normalize_date(start_date) if start_date else None,
            normalize_date(end_date) if end_date else None,
            "coingecko",
        )
        if self.use_cache:
            cached = self.cache.get("coingecko", cache_id, max_age_hours=self.cache_hours)
            if cached is not None:
                print(f"[CoinGecko] Using cached data for {coin_id}")
                return cached

        # Range endpoint takes unix seconds; default to a wide window.
        start_ts = int(
            pd.Timestamp(start_date or "2013-01-01").replace(tzinfo=timezone.utc).timestamp()
        )
        end_ts = int(
            (pd.Timestamp(end_date) if end_date else pd.Timestamp(datetime.now(timezone.utc)))
            .replace(tzinfo=timezone.utc)
            .timestamp()
        )
        url = f"{self.BASE_URL}/coins/{coin_id}/market_chart/range"
        params = {"vs_currency": vs_currency, "from": start_ts, "to": end_ts}
        headers = {"x-cg-demo-api-key": self.api_key} if self.api_key else {}

        try:
            self.rate_limiter.wait("coingecko")
            print(f"[CoinGecko] Fetching {coin_id} ({vs_currency})")
            r = requests.get(url, params=params, headers=headers, timeout=30)
            if r.status_code == 404:
                raise ValueError(f"Unknown coin id: {coin_id}")
            if r.status_code == 429:
                raise ValueError("CoinGecko rate limit exceeded. Wait and retry.")
            r.raise_for_status()
            data = r.json()
            prices = data.get("prices", [])
            if not prices:
                raise ValueError(f"No data returned for coin id: {coin_id}")

            df = pd.DataFrame(prices, columns=["ts", "Close"])
            df["Date"] = pd.to_datetime(df["ts"], unit="ms").dt.tz_localize(None).dt.normalize()
            mcap = dict((int(t), v) for t, v in data.get("market_caps", []))
            vol = dict((int(t), v) for t, v in data.get("total_volumes", []))
            df["Market_Cap"] = df["ts"].map(mcap)
            df["Volume"] = df["ts"].map(vol)
            df = (
                df.drop(columns=["ts"])
                .drop_duplicates("Date", keep="last")
                .sort_values("Date")
                .reset_index(drop=True)[["Date", "Close", "Market_Cap", "Volume"]]
            )

            if self.use_cache:
                self.cache.set("coingecko", cache_id, df)
            return df
        except Exception as e:  # noqa: BLE001
            handle_api_error("CoinGecko", e, coin_id)
            raise


def fetch_coingecko(
    coin_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    api_key: Optional[str] = None,
    use_cache: bool = True,
) -> pd.DataFrame:
    """Convenience wrapper."""
    return CoinGeckoFetcher(api_key=api_key, use_cache=use_cache).fetch(
        coin_id, start_date, end_date
    )


if __name__ == "__main__":
    if len(sys.argv) > 1:
        tk = sys.argv[1]
        sd = sys.argv[2] if len(sys.argv) > 2 else None
        ed = sys.argv[3] if len(sys.argv) > 3 else None
        print(fetch_coingecko(tk, sd, ed).tail())
    else:
        df = fetch_coingecko("bitcoin", "2026-06-01")
        print(f"  OK bitcoin rows={len(df)} last={df['Date'].max().date()}")

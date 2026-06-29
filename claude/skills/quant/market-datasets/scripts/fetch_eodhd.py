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
EODHD (EOD Historical Data) fetcher.

Best for UCITS/ETF and global multi-exchange coverage keyed by exchange-suffixed
symbol or ISIN. REST API over HTTPS — reachable from datacenters/VPS where
Stooq/Yahoo are geo-blocked or rate-limited. Splits/dividend-adjusted EOD.

Coverage validated 2026-06-29 on a 42-instrument ETF benchmark universe: 100%
resolution incl. US (.US), London UCITS (.LSE), GPW Beta ETFs (.WAR), and
indices (.INDX), fresher than yfinance.

Tiers:
- free: ~1yr history, 20 calls/day (validation only)
- paid (EOD Historical Data ~$20/mo): full history, 100k calls/day

Requires API key: https://eodhd.com/
API key via:
1. .env file: EODHD_API_KEY=your_key
2. Environment variable: EODHD_API_KEY
3. Direct parameter

Usage:
    uv run fetch_eodhd.py SPY 2024-01-01 2024-12-31      # -> SPY.US
    uv run fetch_eodhd.py IMEU.LSE 2024-01-01            # explicit exchange
    uv run fetch_eodhd.py ETFBW20TR.WAR 2024-01-01       # GPW Beta ETF
    uv run fetch_eodhd.py ^BCOM 2024-01-01               # index -> BCOM.INDX
    uv run fetch_eodhd.py                                # self-tests (needs key)
"""

import os
import sys
from datetime import date
from typing import Optional

import pandas as pd
import requests

from utils import (
    create_identifier,
    get_cache_manager,
    get_rate_limiter,
    handle_api_error,
    normalize_date,
    normalize_date_display,
    standardize_dataframe,
)


def eodhd_symbol(ticker: str) -> str:
    """Map a bare/suffixed ticker to an EODHD symbol.

    - Already exchange-suffixed (contains '.') -> passthrough (e.g. IMEU.LSE)
    - Leading '^' index -> NAME.INDX (e.g. ^BCOM -> BCOM.INDX)
    - Yahoo Warsaw suffix '.WA' -> '.WAR'
    - Yahoo London suffix '.L' -> '.LSE'
    - bare ticker -> '.US'
    """
    t = ticker.strip()
    if t.startswith("^"):
        return t[1:] + ".INDX"
    if t.endswith(".WA"):
        return t[:-3] + ".WAR"
    if t.endswith(".L"):
        return t[:-2] + ".LSE"
    if "." in t:
        return t  # already exchange-suffixed (e.g. IMEU.LSE, ETFBW20TR.WAR)
    return t + ".US"


class EODHDFetcher:
    """Fetcher for EODHD (eodhd.com) end-of-day market data."""

    BASE_URL = "https://eodhd.com/api"

    def __init__(
        self,
        api_key: Optional[str] = None,
        use_cache: bool = True,
        cache_hours: int = 24,
    ):
        self.api_key = api_key or os.environ.get("EODHD_API_KEY")
        if not self.api_key:
            raise ValueError(
                "EODHD API key required. Set EODHD_API_KEY environment variable "
                "or pass api_key parameter. Get a key at: https://eodhd.com/"
            )
        self.use_cache = use_cache
        self.cache_hours = cache_hours
        self.cache = get_cache_manager()
        self.rate_limiter = get_rate_limiter()

    def fetch(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """Fetch EOD data from EODHD.

        Args:
            ticker: bare or exchange-suffixed symbol (see ``eodhd_symbol``)
            start_date: YYYY-MM-DD or YYYYMMDD
            end_date: YYYY-MM-DD or YYYYMMDD

        Returns:
            Standardized DataFrame: Date, Open, High, Low, Close, Volume, Adj_Close
        """
        symbol = eodhd_symbol(ticker)

        start_norm = normalize_date(start_date) if start_date else None
        end_norm = normalize_date(end_date) if end_date else None
        cache_id = create_identifier(symbol, start_norm, end_norm, "eodhd")

        if self.use_cache:
            cached = self.cache.get("eodhd", cache_id, max_age_hours=self.cache_hours)
            if cached is not None:
                print(f"[EODHD] Using cached data for {symbol}")
                return cached

        url = f"{self.BASE_URL}/eod/{symbol}"
        params = {"api_token": self.api_key, "fmt": "json", "period": "d"}
        if start_date:
            params["from"] = normalize_date_display(start_date)
        if end_date:
            params["to"] = normalize_date_display(end_date)

        try:
            self.rate_limiter.wait("eodhd")
            print(f"[EODHD] Fetching {symbol}")
            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 401:
                raise ValueError("Invalid EODHD API key")
            if response.status_code == 403:
                raise ValueError(
                    f"EODHD forbidden for {symbol} — symbol not in your plan "
                    "(free tier is limited; a few US symbols only)"
                )
            if response.status_code == 429:
                raise ValueError("EODHD daily rate limit exceeded. Wait and retry.")
            response.raise_for_status()

            data = response.json()
            if not isinstance(data, list) or not data:
                raise ValueError(f"No data returned for symbol: {symbol}")

            df = pd.DataFrame(data)
            df.rename(
                columns={
                    "date": "Date",
                    "open": "Open",
                    "high": "High",
                    "low": "Low",
                    "close": "Close",
                    "volume": "Volume",
                    "adjusted_close": "Adj_Close",
                },
                inplace=True,
            )
            df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
            df.sort_values("Date", inplace=True)
            df.reset_index(drop=True, inplace=True)
            df = standardize_dataframe(df, "eodhd")

            if self.use_cache:
                self.cache.set("eodhd", cache_id, df)
            return df

        except Exception as e:
            handle_api_error("EODHD", e, symbol)
            raise

    def fetch_multiple(
        self,
        tickers: list,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> dict:
        """Fetch multiple tickers -> {ticker: DataFrame}."""
        results = {}
        for ticker in tickers:
            try:
                results[ticker] = self.fetch(ticker, start_date, end_date)
            except Exception as e:
                print(f"[EODHD] Skipping {ticker}: {e}")
        return results


def fetch_eodhd(
    ticker: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    api_key: Optional[str] = None,
    use_cache: bool = True,
) -> pd.DataFrame:
    """Convenience function to fetch EOD data from EODHD."""
    return EODHDFetcher(api_key=api_key, use_cache=use_cache).fetch(ticker, start_date, end_date)


if __name__ == "__main__":
    if not os.environ.get("EODHD_API_KEY"):
        print("Set EODHD_API_KEY to test. Get a key at: https://eodhd.com/")
        sys.exit(1)

    if len(sys.argv) > 1:
        tk = sys.argv[1]
        sd = sys.argv[2] if len(sys.argv) > 2 else None
        ed = sys.argv[3] if len(sys.argv) > 3 else None
        out = fetch_eodhd(tk, sd, ed)
        print(out.tail())
    else:
        # self-tests: one symbol per exchange family
        for tk in ["SPY", "IMEU.LSE", "ETFBW20TR.WAR", "^BCOM"]:
            try:
                df = fetch_eodhd(tk, "2026-06-01")
                print(
                    f"  OK   {tk:<16} -> {eodhd_symbol(tk):<16} rows={len(df)} last={df['Date'].max().date()}"
                )
            except Exception as e:  # noqa: BLE001
                print(f"  FAIL {tk}: {e}")

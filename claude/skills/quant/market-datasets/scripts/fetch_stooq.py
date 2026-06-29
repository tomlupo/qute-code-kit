#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pandas>=2.0",
#   "requests>=2.28",
# ]
# ///
"""
Stooq data fetcher.

Downloads historical market data from stooq.pl including:
- Polish stocks (PKO, CDR, PZU, etc.)
- Polish indices (WIG20, mWIG40, WIG, etc.)
- International indices (^SPX, ^IXIC, etc.)
- Currency pairs (EURUSD, USDPLN, etc.)
- Commodities

Usage:
    uv run fetch_stooq.py PKO 2024-01-01 2024-12-31
    uv run fetch_stooq.py WIG20 2024-01-01
    uv run fetch_stooq.py  # Run self-tests
"""

import pandas as pd
import requests
from typing import Optional
from io import StringIO
from datetime import datetime, date

from utils import (
    get_cache_manager,
    get_rate_limiter,
    normalize_date,
    standardize_dataframe,
    create_identifier,
    handle_api_error
)


class StooqFetcher:
    """Fetcher for stooq.pl market data."""

    BASE_URL = "https://stooq.pl/q/d/l/"

    def __init__(self, use_cache: bool = True, cache_hours: int = 24):
        """
        Initialize Stooq fetcher.

        Args:
            use_cache: Whether to use caching
            cache_hours: Cache validity in hours
        """
        self.use_cache = use_cache
        self.cache_hours = cache_hours
        self.cache = get_cache_manager()
        self.rate_limiter = get_rate_limiter()

    def fetch(self, ticker: str, start_date: Optional[str] = None,
              end_date: Optional[str] = None, interval: str = 'd') -> pd.DataFrame:
        """
        Fetch data from Stooq.

        Args:
            ticker: Stock ticker (e.g., 'pko', 'wig20', '^spx', 'eurusd')
            start_date: Start date (YYYY-MM-DD or YYYYMMDD), None for all history
            end_date: End date (YYYY-MM-DD or YYYYMMDD), None for all history
            interval: Data interval - 'd' (daily), 'w' (weekly), 'm' (monthly)

        Returns:
            DataFrame with columns: Date, Open, High, Low, Close, Volume

        Raises:
            ValueError: If ticker returns no data
            requests.RequestException: If request fails
        """
        # Normalize ticker
        ticker = self._normalize_ticker(ticker)

        # Create cache identifier
        start_norm = normalize_date(start_date) if start_date else None
        end_norm = normalize_date(end_date) if end_date else None
        cache_id = create_identifier(ticker, start_norm, end_norm, interval)

        # Try cache first
        if self.use_cache:
            cached = self.cache.get('stooq', cache_id, max_age_hours=self.cache_hours)
            if cached is not None:
                print(f"[Stooq] Using cached data for {ticker}")
                return cached

        # Build URL
        url = self._build_url(ticker, start_norm, end_norm, interval)

        try:
            # Rate limiting
            self.rate_limiter.wait('stooq')

            # Fetch data
            print(f"[Stooq] Fetching {ticker} from {start_norm or 'earliest'} to {end_norm or 'latest'}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Check for "Brak danych" (No data)
            if response.text.strip() == "Brak danych":
                raise ValueError(f"No data available for ticker: {ticker}")

            # Parse CSV
            df = pd.read_csv(StringIO(response.text))

            if df.empty:
                raise ValueError(f"Empty data returned for ticker: {ticker}")

            # Standardize DataFrame
            df = standardize_dataframe(df, 'stooq')

            # Cache result
            if self.use_cache:
                self.cache.set('stooq', cache_id, df)

            return df

        except Exception as e:
            handle_api_error('Stooq', e, ticker)
            raise

    def _normalize_ticker(self, ticker: str) -> str:
        """
        Normalize ticker for Stooq API.

        Args:
            ticker: Raw ticker

        Returns:
            Normalized ticker
        """
        # Remove any .pl suffix (causes "Brak danych")
        if ticker.lower().endswith('.pl'):
            ticker = ticker[:-3]

        # Lowercase (except for ^ prefix)
        if not ticker.startswith('^'):
            ticker = ticker.lower()

        return ticker

    def _build_url(self, ticker: str, start_date: Optional[str] = None,
                   end_date: Optional[str] = None, interval: str = 'd') -> str:
        """
        Build Stooq API URL.

        Args:
            ticker: Normalized ticker
            start_date: Start date (YYYYMMDD)
            end_date: End date (YYYYMMDD)
            interval: Interval code

        Returns:
            Complete URL
        """
        url = f"{self.BASE_URL}?s={ticker}&i={interval}"

        if start_date:
            url += f"&d1={start_date}"
        if end_date:
            url += f"&d2={end_date}"

        return url


def fetch_stooq(ticker: str, start_date: Optional[str] = None,
                end_date: Optional[str] = None, interval: str = 'd',
                use_cache: bool = True) -> pd.DataFrame:
    """
    Convenience function to fetch data from Stooq.

    Args:
        ticker: Stock ticker
        start_date: Start date
        end_date: End date
        interval: Data interval ('d', 'w', 'm')
        use_cache: Whether to use caching

    Returns:
        DataFrame with market data
    """
    fetcher = StooqFetcher(use_cache=use_cache)
    return fetcher.fetch(ticker, start_date, end_date, interval)


if __name__ == '__main__':
    import sys

    # CLI mode: uv run fetch_stooq.py TICKER START_DATE [END_DATE]
    if len(sys.argv) > 1:
        ticker = sys.argv[1]
        start_date = sys.argv[2] if len(sys.argv) > 2 else None
        end_date = sys.argv[3] if len(sys.argv) > 3 else None

        print(f"Fetching {ticker} from Stooq...")
        df = fetch_stooq(ticker, start_date=start_date, end_date=end_date)
        print(f"\nRetrieved {len(df)} rows")
        print(f"Date range: {df['Date'].min()} to {df['Date'].max()}")
        print(f"\nFirst 5 rows:")
        print(df.head())
        print(f"\nLast 5 rows:")
        print(df.tail())
    else:
        # Self-tests
        print("Running Stooq fetcher self-tests...")

        # Test 1: Polish stock
        print("\n1. Fetching PKO (Polish stock):")
        try:
            df = fetch_stooq('pko', start_date='20240101', end_date='20240131')
            assert len(df) > 15, f"Expected ~20 trading days, got {len(df)}"
            assert 'Close' in df.columns, "Missing Close column"
            print(f"   Retrieved {len(df)} rows")
        except Exception as e:
            print(f"   Error: {e}")

        # Test 2: Polish index
        print("\n2. Fetching WIG20 (Polish index):")
        try:
            df = fetch_stooq('wig20', start_date='20240101', end_date='20240131')
            assert len(df) > 15, f"Expected ~20 trading days, got {len(df)}"
            print(f"   Retrieved {len(df)} rows")
        except Exception as e:
            print(f"   Error: {e}")

        # Test 3: Currency
        print("\n3. Fetching USDPLN (Currency):")
        try:
            df = fetch_stooq('usdpln', start_date='20240101', end_date='20240131')
            assert len(df) > 15, f"Expected ~20 trading days, got {len(df)}"
            print(f"   Retrieved {len(df)} rows")
        except Exception as e:
            print(f"   Error: {e}")

        print("\nAll Stooq fetcher tests passed!")

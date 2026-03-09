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
Tiingo data fetcher.

Downloads historical market data from Tiingo API.
Best for US stocks with 30+ years of history and generous free tier.

Free tier: 50 req/hour, 1000 req/day, 500 symbols/month
Requires API key: https://api.tiingo.com/

API key can be provided via:
1. .env file: TIINGO_API_KEY=your_key
2. Environment variable: TIINGO_API_KEY
3. Direct parameter

Usage:
    uv run fetch_tiingo.py AAPL 2024-01-01 2024-12-31
    uv run fetch_tiingo.py MSFT 2024-01-01
    uv run fetch_tiingo.py  # Run self-tests (requires API key)
"""

import os
import pandas as pd
import requests
from typing import Optional
from datetime import datetime, date

from utils import (
    get_cache_manager,
    get_rate_limiter,
    normalize_date,
    normalize_date_display,
    standardize_dataframe,
    create_identifier,
    handle_api_error
)


class TiingoFetcher:
    """Fetcher for Tiingo market data."""

    BASE_URL = "https://api.tiingo.com"

    def __init__(self, api_key: Optional[str] = None, use_cache: bool = True,
                 cache_hours: int = 24):
        """
        Initialize Tiingo fetcher.

        Args:
            api_key: Tiingo API key (or set TIINGO_API_KEY env var)
            use_cache: Whether to use caching
            cache_hours: Cache validity in hours
        """
        self.api_key = api_key or os.environ.get('TIINGO_API_KEY')
        if not self.api_key:
            raise ValueError(
                "Tiingo API key required. Set TIINGO_API_KEY environment variable "
                "or pass api_key parameter. Get free key at: https://api.tiingo.com/"
            )

        self.use_cache = use_cache
        self.cache_hours = cache_hours
        self.cache = get_cache_manager()
        self.rate_limiter = get_rate_limiter()

        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Token {self.api_key}'
        }

    def fetch(self, ticker: str, start_date: Optional[str] = None,
              end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Fetch EOD data from Tiingo.

        Args:
            ticker: Stock ticker (e.g., 'AAPL', 'MSFT')
            start_date: Start date (YYYY-MM-DD or YYYYMMDD)
            end_date: End date (YYYY-MM-DD or YYYYMMDD)

        Returns:
            DataFrame with columns: Date, Open, High, Low, Close, Volume, Adj_Close

        Raises:
            ValueError: If ticker invalid or no data returned
            requests.RequestException: If request fails
        """
        # Normalize ticker (Tiingo uses uppercase)
        ticker = ticker.upper()

        # Create cache identifier
        start_norm = normalize_date(start_date) if start_date else None
        end_norm = normalize_date(end_date) if end_date else None
        cache_id = create_identifier(ticker, start_norm, end_norm, 'tiingo')

        # Try cache first
        if self.use_cache:
            cached = self.cache.get('tiingo', cache_id, max_age_hours=self.cache_hours)
            if cached is not None:
                print(f"[Tiingo] Using cached data for {ticker}")
                return cached

        # Build URL
        url = f"{self.BASE_URL}/tiingo/daily/{ticker}/prices"
        params = {}

        if start_date:
            params['startDate'] = normalize_date_display(start_date)
        if end_date:
            params['endDate'] = normalize_date_display(end_date)

        try:
            # Rate limiting
            self.rate_limiter.wait('tiingo')

            # Fetch data
            start_display = normalize_date_display(start_date) if start_date else 'earliest'
            end_display = normalize_date_display(end_date) if end_date else 'latest'
            print(f"[Tiingo] Fetching {ticker} from {start_display} to {end_display}")

            response = requests.get(url, headers=self.headers, params=params, timeout=30)

            # Handle errors
            if response.status_code == 404:
                raise ValueError(f"Ticker not found: {ticker}")
            elif response.status_code == 401:
                raise ValueError("Invalid Tiingo API key")
            elif response.status_code == 429:
                raise ValueError("Tiingo rate limit exceeded. Wait and retry.")

            response.raise_for_status()

            data = response.json()

            if not data:
                raise ValueError(f"No data returned for ticker: {ticker}")

            # Convert to DataFrame
            df = pd.DataFrame(data)

            # Rename columns to standard format
            column_mapping = {
                'date': 'Date',
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume',
                'adjOpen': 'Adj_Open',
                'adjHigh': 'Adj_High',
                'adjLow': 'Adj_Low',
                'adjClose': 'Adj_Close',
                'adjVolume': 'Adj_Volume',
                'divCash': 'Dividend',
                'splitFactor': 'Split'
            }
            df.rename(columns=column_mapping, inplace=True)

            # Parse date and remove timezone
            df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)

            # Sort by date
            df.sort_values('Date', inplace=True)
            df.reset_index(drop=True, inplace=True)

            # Cache result
            if self.use_cache:
                self.cache.set('tiingo', cache_id, df)

            return df

        except Exception as e:
            handle_api_error('Tiingo', e, ticker)
            raise

    def get_metadata(self, ticker: str) -> dict:
        """
        Get ticker metadata from Tiingo.

        Args:
            ticker: Stock ticker

        Returns:
            Dictionary with ticker metadata
        """
        ticker = ticker.upper()
        url = f"{self.BASE_URL}/tiingo/daily/{ticker}"

        try:
            self.rate_limiter.wait('tiingo')
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            handle_api_error('Tiingo', e, ticker)
            return {}

    def fetch_multiple(self, tickers: list, start_date: Optional[str] = None,
                      end_date: Optional[str] = None) -> dict:
        """
        Fetch multiple tickers.

        Args:
            tickers: List of ticker symbols
            start_date: Start date
            end_date: End date

        Returns:
            Dictionary mapping ticker -> DataFrame
        """
        results = {}

        for ticker in tickers:
            try:
                df = self.fetch(ticker, start_date, end_date)
                results[ticker] = df
            except Exception as e:
                print(f"[Tiingo] Skipping {ticker}: {e}")
                continue

        return results


def fetch_tiingo(ticker: str, start_date: Optional[str] = None,
                end_date: Optional[str] = None, api_key: Optional[str] = None,
                use_cache: bool = True) -> pd.DataFrame:
    """
    Convenience function to fetch data from Tiingo.

    Args:
        ticker: Stock ticker
        start_date: Start date
        end_date: End date
        api_key: Tiingo API key (or set TIINGO_API_KEY env var)
        use_cache: Whether to use caching

    Returns:
        DataFrame with market data
    """
    fetcher = TiingoFetcher(api_key=api_key, use_cache=use_cache)
    return fetcher.fetch(ticker, start_date, end_date)


if __name__ == '__main__':
    # Test examples
    import sys

    api_key = os.environ.get('TIINGO_API_KEY')
    if not api_key:
        print("Set TIINGO_API_KEY environment variable to test")
        print("Get free API key at: https://api.tiingo.com/")
        sys.exit(1)

    print("Testing Tiingo fetcher...")

    # Test 1: US stock
    print("\n1. Fetching AAPL (US stock):")
    try:
        df = fetch_tiingo('AAPL', start_date='20240101', end_date='20240131')
        print(f"   Retrieved {len(df)} rows")
        print(f"   Columns: {list(df.columns)}")
        print(df.head())
    except Exception as e:
        print(f"   Error: {e}")

    # Test 2: ETF
    print("\n2. Fetching SPY (S&P 500 ETF):")
    try:
        df = fetch_tiingo('SPY', start_date='20240101', end_date='20240131')
        print(f"   Retrieved {len(df)} rows")
        print(df.head())
    except Exception as e:
        print(f"   Error: {e}")

    # Test 3: Get metadata
    print("\n3. Getting MSFT metadata:")
    try:
        fetcher = TiingoFetcher()
        meta = fetcher.get_metadata('MSFT')
        print(f"   Name: {meta.get('name')}")
        print(f"   Exchange: {meta.get('exchangeCode')}")
        print(f"   Start date: {meta.get('startDate')}")
    except Exception as e:
        print(f"   Error: {e}")

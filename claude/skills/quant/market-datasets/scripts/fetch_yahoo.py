#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pandas>=2.0",
#   "yfinance>=0.2.0",
# ]
# ///
"""
Yahoo Finance fetcher.

Downloads market data using yfinance library.
Best for US stocks, ETFs, and international equities.

Usage:
    uv run fetch_yahoo.py AAPL 2024-01-01 2024-12-31
    uv run fetch_yahoo.py PKO.WA 2024-01-01
    uv run fetch_yahoo.py  # Run self-tests
"""

import pandas as pd
from typing import Optional
from datetime import datetime, date

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("[Yahoo] Warning: yfinance not installed. Run: pip install yfinance")

from utils import (
    get_cache_manager,
    get_rate_limiter,
    normalize_date,
    normalize_date_display,
    standardize_dataframe,
    create_identifier,
    handle_api_error
)


class YahooFetcher:
    """Fetcher for Yahoo Finance data via yfinance."""

    def __init__(self, use_cache: bool = True, cache_hours: int = 24):
        """
        Initialize Yahoo Finance fetcher.

        Args:
            use_cache: Whether to use caching
            cache_hours: Cache validity in hours
        """
        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance package not available. Install with: pip install yfinance")

        self.use_cache = use_cache
        self.cache_hours = cache_hours
        self.cache = get_cache_manager()
        self.rate_limiter = get_rate_limiter()

    def fetch(self, ticker: str, start_date: Optional[str] = None,
              end_date: Optional[str] = None, interval: str = '1d') -> pd.DataFrame:
        """
        Fetch data from Yahoo Finance.

        Args:
            ticker: Stock ticker (e.g., 'AAPL', 'MSFT', '^GSPC', 'PKO.WA')
            start_date: Start date (YYYY-MM-DD or YYYYMMDD), None for max history
            end_date: End date (YYYY-MM-DD or YYYYMMDD), None for today
            interval: Data interval - '1d', '1wk', '1mo', '1h', etc.

        Returns:
            DataFrame with columns: Date, Open, High, Low, Close, Volume, Adj_Close

        Raises:
            ValueError: If ticker invalid or no data returned
        """
        # Create cache identifier
        start_norm = normalize_date(start_date) if start_date else None
        end_norm = normalize_date(end_date) if end_date else None
        cache_id = create_identifier(ticker, start_norm, end_norm, interval)

        # Try cache first
        if self.use_cache:
            cached = self.cache.get('yahoo', cache_id, max_age_hours=self.cache_hours)
            if cached is not None:
                print(f"[Yahoo] Using cached data for {ticker}")
                return cached

        # Convert dates to display format for yfinance
        start_display = normalize_date_display(start_date) if start_date else None
        end_display = normalize_date_display(end_date) if end_date else None

        try:
            # Rate limiting
            self.rate_limiter.wait('yahoo')

            # Fetch data
            print(f"[Yahoo] Fetching {ticker} from {start_display or 'max'} to {end_display or 'today'}")

            ticker_obj = yf.Ticker(ticker)
            df = ticker_obj.history(
                start=start_display,
                end=end_display,
                interval=interval,
                auto_adjust=False,  # Keep Adj Close separate
                actions=False  # Don't include dividends/splits in main DataFrame
            )

            if df.empty:
                raise ValueError(f"No data returned for ticker: {ticker}")

            # Reset index to make Date a column
            df.reset_index(inplace=True)

            # Standardize column names
            df = standardize_dataframe(df, 'yahoo')

            # Cache result
            if self.use_cache:
                self.cache.set('yahoo', cache_id, df)

            return df

        except Exception as e:
            handle_api_error('Yahoo', e, ticker)
            raise

    def get_info(self, ticker: str) -> dict:
        """
        Get ticker information/metadata.

        Args:
            ticker: Stock ticker

        Returns:
            Dictionary with ticker information
        """
        try:
            ticker_obj = yf.Ticker(ticker)
            return ticker_obj.info
        except Exception as e:
            handle_api_error('Yahoo', e, ticker)
            return {}

    def fetch_multiple(self, tickers: list, start_date: Optional[str] = None,
                      end_date: Optional[str] = None, interval: str = '1d') -> dict:
        """
        Fetch multiple tickers.

        Args:
            tickers: List of ticker symbols
            start_date: Start date
            end_date: End date
            interval: Data interval

        Returns:
            Dictionary mapping ticker -> DataFrame
        """
        results = {}

        for ticker in tickers:
            try:
                df = self.fetch(ticker, start_date, end_date, interval)
                results[ticker] = df
            except Exception as e:
                print(f"[Yahoo] Skipping {ticker}: {e}")
                continue

        return results


def fetch_yahoo(ticker: str, start_date: Optional[str] = None,
                end_date: Optional[str] = None, interval: str = '1d',
                use_cache: bool = True) -> pd.DataFrame:
    """
    Convenience function to fetch data from Yahoo Finance.

    Args:
        ticker: Stock ticker
        start_date: Start date
        end_date: End date
        interval: Data interval ('1d', '1wk', '1mo')
        use_cache: Whether to use caching

    Returns:
        DataFrame with market data
    """
    fetcher = YahooFetcher(use_cache=use_cache)
    return fetcher.fetch(ticker, start_date, end_date, interval)


if __name__ == '__main__':
    # Test examples
    if not YFINANCE_AVAILABLE:
        print("yfinance not available. Install with: pip install yfinance")
    else:
        print("Testing Yahoo Finance fetcher...")

        # Test 1: US stock
        print("\n1. Fetching AAPL (US stock):")
        try:
            df = fetch_yahoo('AAPL', start_date='20240101', end_date='20241231')
            print(f"   Retrieved {len(df)} rows")
            print(df.head())
        except Exception as e:
            print(f"   Error: {e}")

        # Test 2: Index
        print("\n2. Fetching ^GSPC (S&P 500):")
        try:
            df = fetch_yahoo('^GSPC', start_date='20240101')
            print(f"   Retrieved {len(df)} rows")
            print(df.head())
        except Exception as e:
            print(f"   Error: {e}")

        # Test 3: Polish stock on WSE
        print("\n3. Fetching PKO.WA (PKO on Warsaw Stock Exchange):")
        try:
            df = fetch_yahoo('PKO.WA', start_date='20240101')
            print(f"   Retrieved {len(df)} rows")
            print(df.head())
        except Exception as e:
            print(f"   Error: {e}")

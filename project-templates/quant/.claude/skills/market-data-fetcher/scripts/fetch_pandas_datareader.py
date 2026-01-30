#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pandas>=2.0",
#   "pandas-datareader>=0.10.0",
# ]
# ///
"""
pandas-datareader wrapper.

Meta-fetcher that provides access to multiple data sources through pandas-datareader.

Supported sources: stooq, yahoo, fred, av-daily (Alpha Vantage), iex, etc.

Usage:
    uv run fetch_pandas_datareader.py AAPL 2024-01-01 2024-12-31 --source stooq
    uv run fetch_pandas_datareader.py GDP 2020-01-01 --source fred
    uv run fetch_pandas_datareader.py  # Run self-tests
"""

import pandas as pd
from typing import Optional, Literal
from datetime import datetime, date

try:
    import pandas_datareader as pdr
    from pandas_datareader.data import DataReader
    PANDAS_DATAREADER_AVAILABLE = True
except ImportError:
    PANDAS_DATAREADER_AVAILABLE = False
    print("[pandas-datareader] Warning: pandas-datareader not installed. Run: pip install pandas-datareader")

from utils import (
    get_cache_manager,
    get_rate_limiter,
    normalize_date,
    normalize_date_display,
    standardize_dataframe,
    create_identifier,
    handle_api_error
)


class PandasDataReaderFetcher:
    """Wrapper for pandas-datareader multi-source data access."""

    SUPPORTED_SOURCES = [
        'stooq',      # Stooq (Polish & international stocks)
        'yahoo',      # Yahoo Finance
        'fred',       # FRED economic data
        'av-daily',   # Alpha Vantage (requires API key)
        'iex',        # IEX Cloud (requires API key)
        'quandl',     # Quandl (requires API key)
    ]

    def __init__(self, use_cache: bool = True, cache_hours: int = 24):
        """
        Initialize pandas-datareader fetcher.

        Args:
            use_cache: Whether to use caching
            cache_hours: Cache validity in hours
        """
        if not PANDAS_DATAREADER_AVAILABLE:
            raise ImportError(
                "pandas-datareader not available. Install with: pip install pandas-datareader"
            )

        self.use_cache = use_cache
        self.cache_hours = cache_hours
        self.cache = get_cache_manager()
        self.rate_limiter = get_rate_limiter()

    def fetch(self, ticker: str, source: str = 'yahoo',
              start_date: Optional[str] = None,
              end_date: Optional[str] = None,
              **kwargs) -> pd.DataFrame:
        """
        Fetch data using pandas-datareader.

        Args:
            ticker: Ticker symbol (format depends on source)
            source: Data source ('stooq', 'yahoo', 'fred', etc.)
            start_date: Start date (YYYY-MM-DD or YYYYMMDD)
            end_date: End date (YYYY-MM-DD or YYYYMMDD)
            **kwargs: Additional arguments passed to DataReader

        Returns:
            DataFrame with market data

        Raises:
            ValueError: If source invalid or no data returned
        """
        if source not in self.SUPPORTED_SOURCES:
            raise ValueError(
                f"Source '{source}' not supported. "
                f"Supported sources: {', '.join(self.SUPPORTED_SOURCES)}"
            )

        # Create cache identifier
        start_norm = normalize_date(start_date) if start_date else None
        end_norm = normalize_date(end_date) if end_date else None
        cache_id = f"{source}_{create_identifier(ticker, start_norm, end_norm)}"

        # Try cache first
        if self.use_cache:
            cached = self.cache.get('pandas_datareader', cache_id,
                                   max_age_hours=self.cache_hours)
            if cached is not None:
                print(f"[pandas-datareader] Using cached data for {ticker} from {source}")
                return cached

        # Convert dates to display format
        start_display = normalize_date_display(start_date) if start_date else None
        end_display = normalize_date_display(end_date) if end_date else None

        try:
            # Rate limiting
            self.rate_limiter.wait(f'pdr_{source}')

            # Fetch data
            print(f"[pandas-datareader] Fetching {ticker} from {source} "
                  f"({start_display or 'earliest'} to {end_display or 'latest'})")

            df = DataReader(
                ticker,
                source,
                start=start_display,
                end=end_display,
                **kwargs
            )

            if df.empty:
                raise ValueError(f"No data returned for {ticker} from {source}")

            # Reset index if needed (make Date a column)
            if isinstance(df.index, pd.DatetimeIndex):
                df.reset_index(inplace=True)

            # Standardize (best effort, some sources may not have all columns)
            try:
                df = standardize_dataframe(df, f'pdr_{source}')
            except Exception as e:
                print(f"[pandas-datareader] Warning: Could not standardize DataFrame: {e}")

            # Cache result
            if self.use_cache:
                self.cache.set('pandas_datareader', cache_id, df)

            return df

        except Exception as e:
            handle_api_error(f'pandas-datareader ({source})', e, ticker)
            raise

    def fetch_multiple(self, tickers: list, source: str = 'yahoo',
                      start_date: Optional[str] = None,
                      end_date: Optional[str] = None,
                      **kwargs) -> dict:
        """
        Fetch multiple tickers from pandas-datareader.

        Args:
            tickers: List of ticker symbols
            source: Data source
            start_date: Start date
            end_date: End date
            **kwargs: Additional arguments

        Returns:
            Dictionary mapping ticker -> DataFrame
        """
        results = {}

        for ticker in tickers:
            try:
                df = self.fetch(ticker, source, start_date, end_date, **kwargs)
                results[ticker] = df
            except Exception as e:
                print(f"[pandas-datareader] Skipping {ticker}: {e}")
                continue

        return results

    @staticmethod
    def list_sources() -> list:
        """
        List supported sources.

        Returns:
            List of supported source names
        """
        return PandasDataReaderFetcher.SUPPORTED_SOURCES


def fetch_pandas_datareader(ticker: str, source: str = 'yahoo',
                            start_date: Optional[str] = None,
                            end_date: Optional[str] = None,
                            use_cache: bool = True,
                            **kwargs) -> pd.DataFrame:
    """
    Convenience function to fetch data via pandas-datareader.

    Args:
        ticker: Ticker symbol
        source: Data source
        start_date: Start date
        end_date: End date
        use_cache: Whether to use caching
        **kwargs: Additional arguments

    Returns:
        DataFrame with market data
    """
    fetcher = PandasDataReaderFetcher(use_cache=use_cache)
    return fetcher.fetch(ticker, source, start_date, end_date, **kwargs)


if __name__ == '__main__':
    # Test examples
    if not PANDAS_DATAREADER_AVAILABLE:
        print("pandas-datareader not available. Install with: pip install pandas-datareader")
    else:
        print("Testing pandas-datareader fetcher...")

        # Test 1: Yahoo via pandas-datareader
        print("\n1. Fetching AAPL from Yahoo:")
        try:
            df = fetch_pandas_datareader('AAPL', source='yahoo',
                                        start_date='20240101',
                                        end_date='20240131')
            print(f"   Retrieved {len(df)} rows")
            print(df.head())
        except Exception as e:
            print(f"   Error: {e}")

        # Test 2: Stooq via pandas-datareader
        print("\n2. Fetching PKO from Stooq:")
        try:
            df = fetch_pandas_datareader('pko', source='stooq',
                                        start_date='20240101',
                                        end_date='20240131')
            print(f"   Retrieved {len(df)} rows")
            print(df.head())
        except Exception as e:
            print(f"   Error: {e}")

        # Test 3: FRED via pandas-datareader
        print("\n3. Fetching GDP from FRED:")
        try:
            df = fetch_pandas_datareader('GDP', source='fred',
                                        start_date='20200101',
                                        end_date='20241231')
            print(f"   Retrieved {len(df)} rows")
            print(df.head())
        except Exception as e:
            print(f"   Error: {e}")

        # Test 4: List sources
        print("\n4. Supported sources:")
        print("   " + ", ".join(PandasDataReaderFetcher.list_sources()))

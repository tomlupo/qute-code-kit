#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pandas>=2.0",
#   "python-dotenv>=1.0",
# ]
# ///
"""
Shared utilities for market data fetchers.

Provides caching, date handling, rate limiting, error handling,
and environment variable loading for all data source implementations.

Usage:
    uv run utils.py  # Run self-tests
"""

import json
import os
import time
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Union, Dict, Any
import pandas as pd
import hashlib

# Load .env file for API keys
try:
    from dotenv import load_dotenv

    # Search for .env in multiple locations
    for env_path in [
        Path(__file__).parent.parent / '.env',  # Skill root (.claude/skills/market-data-fetcher/.env)
        Path.cwd() / '.env',                     # Current working directory
        Path.home() / '.env',                    # Home directory (fallback)
    ]:
        if env_path.exists():
            load_dotenv(env_path)
            break
except ImportError:
    pass  # python-dotenv not installed, rely on system env vars


def get_api_key(key_name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get API key from environment variables (loaded from .env or system).

    Args:
        key_name: Name of environment variable (e.g., 'TIINGO_API_KEY')
        default: Default value if not found

    Returns:
        API key value or default
    """
    return os.getenv(key_name, default)


class CacheManager:
    """Manages file-based caching for market data."""

    def __init__(self, cache_dir: str = "data/cache/market_data"):
        """
        Initialize cache manager.

        Args:
            cache_dir: Base directory for cache storage
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_cache_path(self, source: str, identifier: str, format: str = "csv") -> Path:
        """
        Get cache file path for a data request.

        Args:
            source: Data source name (stooq, nbp, yahoo, fred)
            identifier: Unique identifier (e.g., ticker_start_end)
            format: File format (csv, json)

        Returns:
            Path to cache file
        """
        source_dir = self.cache_dir / source
        source_dir.mkdir(exist_ok=True)
        return source_dir / f"{identifier}.{format}"

    def get(self, source: str, identifier: str, format: str = "csv",
            max_age_hours: Optional[int] = None) -> Optional[Union[pd.DataFrame, Dict]]:
        """
        Retrieve cached data if available and not expired.

        Args:
            source: Data source name
            identifier: Unique identifier
            format: File format
            max_age_hours: Maximum cache age in hours (None = no expiry)

        Returns:
            Cached data or None if not found/expired
        """
        cache_path = self.get_cache_path(source, identifier, format)

        if not cache_path.exists():
            return None

        # Check age
        if max_age_hours is not None:
            file_age = time.time() - cache_path.stat().st_mtime
            if file_age > max_age_hours * 3600:
                return None

        try:
            if format == "csv":
                return pd.read_csv(cache_path, parse_dates=['Date'] if 'Date' in pd.read_csv(cache_path, nrows=0).columns else None)
            elif format == "json":
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error reading cache: {e}")
            return None

    def set(self, source: str, identifier: str, data: Union[pd.DataFrame, Dict],
            format: str = "csv") -> None:
        """
        Store data in cache.

        Args:
            source: Data source name
            identifier: Unique identifier
            data: Data to cache
            format: File format
        """
        cache_path = self.get_cache_path(source, identifier, format)

        try:
            if format == "csv" and isinstance(data, pd.DataFrame):
                data.to_csv(cache_path, index=False)
            elif format == "json" and isinstance(data, dict):
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error writing cache: {e}")


class RateLimiter:
    """Simple rate limiter with delay between requests."""

    def __init__(self, min_delay_seconds: float = 1.0):
        """
        Initialize rate limiter.

        Args:
            min_delay_seconds: Minimum delay between requests
        """
        self.min_delay = min_delay_seconds
        self.last_request_time = {}

    def wait(self, source: str) -> None:
        """
        Wait if necessary to respect rate limit for a source.

        Args:
            source: Data source name
        """
        if source in self.last_request_time:
            elapsed = time.time() - self.last_request_time[source]
            if elapsed < self.min_delay:
                time.sleep(self.min_delay - elapsed)

        self.last_request_time[source] = time.time()


def normalize_date(dt: Union[str, date, datetime, pd.Timestamp]) -> str:
    """
    Normalize date to YYYYMMDD format.

    Args:
        dt: Date in various formats

    Returns:
        Date string in YYYYMMDD format
    """
    if isinstance(dt, str):
        # Try parsing common formats
        for fmt in ['%Y-%m-%d', '%Y%m%d', '%d-%m-%Y', '%m/%d/%Y']:
            try:
                parsed = datetime.strptime(dt, fmt)
                return parsed.strftime('%Y%m%d')
            except ValueError:
                continue
        raise ValueError(f"Unable to parse date: {dt}")
    elif isinstance(dt, (date, datetime, pd.Timestamp)):
        return dt.strftime('%Y%m%d')
    else:
        raise TypeError(f"Unsupported date type: {type(dt)}")


def normalize_date_display(dt: Union[str, date, datetime, pd.Timestamp]) -> str:
    """
    Normalize date to YYYY-MM-DD format for display.

    Args:
        dt: Date in various formats

    Returns:
        Date string in YYYY-MM-DD format
    """
    yyyymmdd = normalize_date(dt)
    return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:]}"


def standardize_dataframe(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """
    Standardize DataFrame format across sources.

    Ensures consistent column names and date handling.

    Args:
        df: Input DataFrame
        source: Source name for logging

    Returns:
        Standardized DataFrame with columns: Date, Open, High, Low, Close, Volume
    """
    # Make a copy to avoid modifying original
    df = df.copy()

    # Column mapping from various sources
    column_mapping = {
        # Stooq (Polish)
        'Data': 'Date',
        'Otwarcie': 'Open',
        'Najwyzszy': 'High',
        'Najnizszy': 'Low',
        'Zamkniecie': 'Close',
        'Wolumen': 'Volume',
        # Common English
        'date': 'Date',
        'open': 'Open',
        'high': 'High',
        'low': 'Low',
        'close': 'Close',
        'volume': 'Volume',
        # Yahoo Finance / pandas-datareader
        'Open': 'Open',
        'High': 'High',
        'Low': 'Low',
        'Close': 'Close',
        'Volume': 'Volume',
        'Adj Close': 'Adj_Close',
    }

    # Rename columns
    df.rename(columns=column_mapping, inplace=True)

    # Ensure Date column is datetime
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])

    # Sort by date
    if 'Date' in df.columns:
        df.sort_values('Date', inplace=True)
        df.reset_index(drop=True, inplace=True)

    return df


def create_identifier(ticker: str, start_date: Optional[str] = None,
                     end_date: Optional[str] = None, interval: str = 'd') -> str:
    """
    Create unique identifier for caching.

    Args:
        ticker: Ticker symbol
        start_date: Start date
        end_date: End date
        interval: Data interval (d, w, m)

    Returns:
        Unique identifier string
    """
    parts = [ticker.lower(), interval]
    if start_date:
        parts.append(start_date)
    if end_date:
        parts.append(end_date)
    return "_".join(parts)


def handle_api_error(source: str, error: Exception, ticker: str) -> None:
    """
    Handle and log API errors consistently.

    Args:
        source: Data source name
        error: Exception that occurred
        ticker: Ticker that caused error
    """
    print(f"[{source}] Error fetching data for {ticker}: {str(error)}")


# Global instances for reuse
_cache_manager = CacheManager()
_rate_limiter = RateLimiter()


def get_cache_manager() -> CacheManager:
    """Get global cache manager instance."""
    return _cache_manager


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance."""
    return _rate_limiter


if __name__ == "__main__":
    # Self-tests
    print("Running utils.py self-tests...")

    # Test date normalization
    assert normalize_date("2024-01-15") == "20240115", "Date normalization failed"
    assert normalize_date("20240115") == "20240115", "Date passthrough failed"
    assert normalize_date_display("20240115") == "2024-01-15", "Date display failed"
    print("  Date normalization tests passed")

    # Test cache identifier creation
    assert create_identifier("PKO", "20240101", "20241231") == "pko_d_20240101_20241231", "Identifier creation failed"
    print("  Identifier creation tests passed")

    # Test API key retrieval (should return None or value if set)
    key = get_api_key("TEST_API_KEY_THAT_DOES_NOT_EXIST")
    assert key is None, "Expected None for missing key"
    key_with_default = get_api_key("TEST_API_KEY_THAT_DOES_NOT_EXIST", "default_value")
    assert key_with_default == "default_value", "Default value not returned"
    print("  API key retrieval tests passed")

    # Test cache manager
    cache = get_cache_manager()
    assert cache is not None, "Cache manager should not be None"
    print("  Cache manager tests passed")

    # Test rate limiter
    limiter = get_rate_limiter()
    assert limiter is not None, "Rate limiter should not be None"
    print("  Rate limiter tests passed")

    print("\nAll utils.py tests passed!")

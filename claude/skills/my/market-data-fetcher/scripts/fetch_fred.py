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
FRED (Federal Reserve Economic Data) API fetcher.

Downloads economic indicators from FRED database.
Requires API key from https://fred.stlouisfed.org/docs/api/api_key.html

API key can be provided via:
1. .env file: FRED_API_KEY=your_key
2. Environment variable: FRED_API_KEY
3. Config file: config/fred_api_key.txt
4. Direct parameter

Usage:
    uv run fetch_fred.py GDP 2020-01-01 2024-12-31
    uv run fetch_fred.py UNRATE 2020-01-01
    uv run fetch_fred.py  # Run self-tests (requires API key)
"""

import pandas as pd
import requests
from typing import Optional
from datetime import datetime, date
import os

from utils import (
    get_cache_manager,
    get_rate_limiter,
    normalize_date,
    normalize_date_display,
    create_identifier,
    handle_api_error
)


class FREDFetcher:
    """Fetcher for FRED economic data."""

    BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

    def __init__(self, api_key: Optional[str] = None, use_cache: bool = True,
                 cache_hours: int = 24):
        """
        Initialize FRED fetcher.

        Args:
            api_key: FRED API key (optional if set in env or config)
            use_cache: Whether to use caching
            cache_hours: Cache validity in hours
        """
        self.api_key = self._get_api_key(api_key)
        if not self.api_key:
            raise ValueError(
                "FRED API key required. Set FRED_API_KEY environment variable, "
                "create config/fred_api_key.txt, or pass api_key parameter. "
                "Get key at: https://fred.stlouisfed.org/docs/api/api_key.html"
            )

        self.use_cache = use_cache
        self.cache_hours = cache_hours
        self.cache = get_cache_manager()
        self.rate_limiter = get_rate_limiter()

    def _get_api_key(self, api_key: Optional[str] = None) -> Optional[str]:
        """
        Get FRED API key from various sources.

        Priority:
        1. Direct parameter
        2. Environment variable
        3. Config file

        Args:
            api_key: Direct API key

        Returns:
            API key or None
        """
        # 1. Direct parameter
        if api_key:
            return api_key

        # 2. Environment variable
        env_key = os.environ.get('FRED_API_KEY')
        if env_key:
            return env_key

        # 3. Config file
        config_paths = [
            'config/fred_api_key.txt',
            'U:/config_files/fred_api_key.txt',
            os.path.expanduser('~/.fred_api_key')
        ]

        for path in config_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        key = f.read().strip()
                        if key:
                            return key
                except Exception:
                    continue

        return None

    def fetch(self, series_id: str, start_date: Optional[str] = None,
              end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Fetch economic data series from FRED.

        Args:
            series_id: FRED series ID (e.g., 'GDP', 'UNRATE', 'CPIAUCSL')
            start_date: Start date (YYYY-MM-DD or YYYYMMDD)
            end_date: End date (YYYY-MM-DD or YYYYMMDD)

        Returns:
            DataFrame with columns: Date, Value

        Raises:
            ValueError: If series_id invalid or no data returned
            requests.RequestException: If request fails
        """
        # Create cache identifier
        start_norm = normalize_date(start_date) if start_date else None
        end_norm = normalize_date(end_date) if end_date else None
        cache_id = create_identifier(series_id, start_norm, end_norm)

        # Try cache first
        if self.use_cache:
            cached = self.cache.get('fred', cache_id, max_age_hours=self.cache_hours)
            if cached is not None:
                print(f"[FRED] Using cached data for {series_id}")
                return cached

        # Convert dates to display format
        start_display = normalize_date_display(start_date) if start_date else None
        end_display = normalize_date_display(end_date) if end_date else None

        # Build request parameters
        params = {
            'series_id': series_id,
            'api_key': self.api_key,
            'file_type': 'json'
        }

        if start_display:
            params['observation_start'] = start_display
        if end_display:
            params['observation_end'] = end_display

        try:
            # Rate limiting
            self.rate_limiter.wait('fred')

            # Fetch data
            print(f"[FRED] Fetching {series_id} from {start_display or 'earliest'} to {end_display or 'latest'}")
            response = requests.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()

            # Parse JSON
            data = response.json()

            if 'error_code' in data:
                raise ValueError(f"FRED API error: {data.get('error_message', 'Unknown error')}")

            # Extract observations
            df = self._parse_response(data, series_id)

            if df.empty:
                raise ValueError(f"No data returned for series: {series_id}")

            # Cache result
            if self.use_cache:
                self.cache.set('fred', cache_id, df)

            return df

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                raise ValueError(f"Invalid series ID or parameters: {series_id}")
            handle_api_error('FRED', e, series_id)
            raise
        except Exception as e:
            handle_api_error('FRED', e, series_id)
            raise

    def _parse_response(self, data: dict, series_id: str) -> pd.DataFrame:
        """
        Parse FRED API JSON response.

        Args:
            data: JSON response
            series_id: Series ID

        Returns:
            Parsed DataFrame
        """
        if 'observations' not in data:
            return pd.DataFrame()

        observations = []
        for obs in data['observations']:
            # Skip missing values
            if obs['value'] == '.':
                continue

            observations.append({
                'Date': pd.to_datetime(obs['date']),
                'Value': float(obs['value']),
                'Series_ID': series_id
            })

        df = pd.DataFrame(observations)

        # Sort by date
        if not df.empty:
            df.sort_values('Date', inplace=True)
            df.reset_index(drop=True, inplace=True)

        return df

    def get_series_info(self, series_id: str) -> dict:
        """
        Get metadata about a FRED series.

        Args:
            series_id: FRED series ID

        Returns:
            Dictionary with series information
        """
        url = "https://api.stlouisfed.org/fred/series"
        params = {
            'series_id': series_id,
            'api_key': self.api_key,
            'file_type': 'json'
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if 'seriess' in data and len(data['seriess']) > 0:
                return data['seriess'][0]
            return {}

        except Exception as e:
            handle_api_error('FRED', e, series_id)
            return {}

    def fetch_multiple(self, series_ids: list, start_date: Optional[str] = None,
                      end_date: Optional[str] = None) -> dict:
        """
        Fetch multiple series.

        Args:
            series_ids: List of FRED series IDs
            start_date: Start date
            end_date: End date

        Returns:
            Dictionary mapping series_id -> DataFrame
        """
        results = {}

        for series_id in series_ids:
            try:
                df = self.fetch(series_id, start_date, end_date)
                results[series_id] = df
            except Exception as e:
                print(f"[FRED] Skipping {series_id}: {e}")
                continue

        return results


def fetch_fred(series_id: str, start_date: Optional[str] = None,
               end_date: Optional[str] = None, api_key: Optional[str] = None,
               use_cache: bool = True) -> pd.DataFrame:
    """
    Convenience function to fetch FRED economic data.

    Args:
        series_id: FRED series ID
        start_date: Start date
        end_date: End date
        api_key: FRED API key (optional if in env/config)
        use_cache: Whether to use caching

    Returns:
        DataFrame with economic data
    """
    fetcher = FREDFetcher(api_key=api_key, use_cache=use_cache)
    return fetcher.fetch(series_id, start_date, end_date)


if __name__ == '__main__':
    # Test examples
    print("Testing FRED fetcher...")

    try:
        # Test 1: GDP
        print("\n1. Fetching GDP:")
        df = fetch_fred('GDP', start_date='20200101', end_date='20241231')
        print(f"   Retrieved {len(df)} rows")
        print(df.head())
        print(df.tail())

        # Test 2: Unemployment rate
        print("\n2. Fetching UNRATE (Unemployment Rate):")
        df = fetch_fred('UNRATE', start_date='20240101')
        print(f"   Retrieved {len(df)} rows")
        print(df.head())

        # Test 3: Get series info
        print("\n3. Getting GDP series info:")
        fetcher = FREDFetcher()
        info = fetcher.get_series_info('GDP')
        print(f"   Title: {info.get('title')}")
        print(f"   Units: {info.get('units')}")
        print(f"   Frequency: {info.get('frequency')}")

    except ValueError as e:
        print(f"\nAPI key not configured: {e}")
        print("\nTo use FRED:")
        print("1. Get API key from https://fred.stlouisfed.org/docs/api/api_key.html")
        print("2. Set environment variable: FRED_API_KEY=your_key")
        print("3. Or create config/fred_api_key.txt with your key")
    except Exception as e:
        print(f"   Error: {e}")

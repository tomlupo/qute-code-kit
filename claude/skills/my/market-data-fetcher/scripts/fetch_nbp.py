#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pandas>=2.0",
#   "requests>=2.28",
# ]
# ///
"""
NBP (Narodowy Bank Polski) API fetcher.

Downloads official PLN exchange rates from NBP API.
API Documentation: http://api.nbp.pl/

Rate tables:
- Table A: Foreign exchange rates (most common currencies)
- Table B: Foreign exchange rates (less common currencies)
- Table C: Buy/sell rates

Usage:
    uv run fetch_nbp.py USD 2024-01-01 2024-12-31
    uv run fetch_nbp.py EUR 2024-01-01
    uv run fetch_nbp.py  # Run self-tests
"""

import pandas as pd
import requests
from typing import Optional, Literal
from datetime import datetime, date

from utils import (
    get_cache_manager,
    get_rate_limiter,
    normalize_date,
    normalize_date_display,
    create_identifier,
    handle_api_error
)


class NBPFetcher:
    """Fetcher for NBP API exchange rates."""

    BASE_URL = "http://api.nbp.pl/api/exchangerates"

    def __init__(self, use_cache: bool = True, cache_hours: int = 24):
        """
        Initialize NBP fetcher.

        Args:
            use_cache: Whether to use caching
            cache_hours: Cache validity in hours
        """
        self.use_cache = use_cache
        self.cache_hours = cache_hours
        self.cache = get_cache_manager()
        self.rate_limiter = get_rate_limiter()

    def fetch(self, currency_code: str,
              start_date: Optional[str] = None,
              end_date: Optional[str] = None,
              table: Literal['A', 'B', 'C'] = 'A') -> pd.DataFrame:
        """
        Fetch exchange rates from NBP API.

        Args:
            currency_code: Three-letter currency code (e.g., 'USD', 'EUR', 'GBP')
            start_date: Start date (YYYY-MM-DD or YYYYMMDD)
            end_date: End date (YYYY-MM-DD or YYYYMMDD)
            table: Rate table - 'A' (most common), 'B' (others), 'C' (buy/sell)

        Returns:
            DataFrame with columns: Date, Currency, Mid (or Bid/Ask for table C)

        Raises:
            ValueError: If currency code or dates invalid
            requests.RequestException: If request fails
        """
        # Normalize currency code
        currency_code = currency_code.upper()

        # Create cache identifier
        start_norm = normalize_date(start_date) if start_date else None
        end_norm = normalize_date(end_date) if end_date else None
        cache_id = f"{currency_code}_{table}_{start_norm}_{end_norm}"

        # Try cache first
        if self.use_cache:
            cached = self.cache.get('nbp', cache_id, format='json',
                                   max_age_hours=self.cache_hours)
            if cached is not None:
                print(f"[NBP] Using cached data for {currency_code}")
                return pd.DataFrame(cached)

        # Build URL
        url = self._build_url(currency_code, start_norm, end_norm, table)

        try:
            # Rate limiting
            self.rate_limiter.wait('nbp')

            # Fetch data
            print(f"[NBP] Fetching {currency_code} (Table {table}) from {start_norm or 'earliest'} to {end_norm or 'latest'}")
            response = requests.get(url, timeout=30, headers={'Accept': 'application/json'})
            response.raise_for_status()

            # Parse JSON
            data = response.json()

            # Extract rates
            df = self._parse_response(data, currency_code, table)

            if df.empty:
                raise ValueError(f"No data returned for {currency_code}")

            # Cache result (as dict for JSON)
            if self.use_cache:
                self.cache.set('nbp', cache_id, df.to_dict(orient='records'), format='json')

            return df

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise ValueError(f"Currency code '{currency_code}' not found in table {table}")
            handle_api_error('NBP', e, currency_code)
            raise
        except Exception as e:
            handle_api_error('NBP', e, currency_code)
            raise

    def _parse_response(self, data: dict, currency_code: str, table: str) -> pd.DataFrame:
        """
        Parse NBP API JSON response into DataFrame.

        Args:
            data: JSON response from API
            currency_code: Currency code
            table: Table type

        Returns:
            Parsed DataFrame
        """
        rates_data = []

        if 'rates' in data:
            for rate in data['rates']:
                row = {
                    'Date': pd.to_datetime(rate['effectiveDate']),
                    'Currency': currency_code
                }

                if table in ['A', 'B']:
                    row['Mid'] = rate['mid']
                elif table == 'C':
                    row['Bid'] = rate['bid']
                    row['Ask'] = rate['ask']

                rates_data.append(row)

        df = pd.DataFrame(rates_data)

        # Sort by date
        if not df.empty:
            df.sort_values('Date', inplace=True)
            df.reset_index(drop=True, inplace=True)

        return df

    def _build_url(self, currency_code: str, start_date: Optional[str] = None,
                   end_date: Optional[str] = None, table: str = 'A') -> str:
        """
        Build NBP API URL.

        Args:
            currency_code: Currency code
            start_date: Start date (YYYYMMDD)
            end_date: End date (YYYYMMDD)
            table: Table type

        Returns:
            Complete URL
        """
        # Convert dates to display format (YYYY-MM-DD) for NBP API
        start_display = normalize_date_display(start_date) if start_date else None
        end_display = normalize_date_display(end_date) if end_date else None

        if start_display and end_display:
            # Date range query
            url = f"{self.BASE_URL}/rates/{table}/{currency_code}/{start_display}/{end_display}/"
        elif start_display:
            # From start date to today
            today = datetime.now().strftime('%Y-%m-%d')
            url = f"{self.BASE_URL}/rates/{table}/{currency_code}/{start_display}/{today}/"
        else:
            # Latest rate only
            url = f"{self.BASE_URL}/rates/{table}/{currency_code}/last/255/"

        return url

    def fetch_multiple(self, currency_codes: list, start_date: Optional[str] = None,
                      end_date: Optional[str] = None, table: str = 'A') -> pd.DataFrame:
        """
        Fetch multiple currencies and combine into single DataFrame.

        Args:
            currency_codes: List of currency codes
            start_date: Start date
            end_date: End date
            table: Rate table

        Returns:
            Combined DataFrame with all currencies
        """
        all_data = []

        for code in currency_codes:
            try:
                df = self.fetch(code, start_date, end_date, table)
                all_data.append(df)
            except Exception as e:
                print(f"[NBP] Skipping {code}: {e}")
                continue

        if not all_data:
            raise ValueError("No data retrieved for any currency")

        # Combine all DataFrames
        combined = pd.concat(all_data, ignore_index=True)
        combined.sort_values(['Date', 'Currency'], inplace=True)
        combined.reset_index(drop=True, inplace=True)

        return combined


def fetch_nbp(currency_code: str, start_date: Optional[str] = None,
              end_date: Optional[str] = None, table: str = 'A',
              use_cache: bool = True) -> pd.DataFrame:
    """
    Convenience function to fetch NBP exchange rates.

    Args:
        currency_code: Currency code (e.g., 'USD', 'EUR')
        start_date: Start date
        end_date: End date
        table: Rate table ('A', 'B', or 'C')
        use_cache: Whether to use caching

    Returns:
        DataFrame with exchange rates
    """
    fetcher = NBPFetcher(use_cache=use_cache)
    return fetcher.fetch(currency_code, start_date, end_date, table)


if __name__ == '__main__':
    # Test examples
    print("Testing NBP fetcher...")

    # Test 1: USD rates
    print("\n1. Fetching USD rates (Table A):")
    try:
        df = fetch_nbp('USD', start_date='20240101', end_date='20241231')
        print(f"   Retrieved {len(df)} rows")
        print(df.head())
        print(df.tail())
    except Exception as e:
        print(f"   Error: {e}")

    # Test 2: EUR rates
    print("\n2. Fetching EUR rates (Table A):")
    try:
        df = fetch_nbp('EUR', start_date='20240101')
        print(f"   Retrieved {len(df)} rows")
        print(df.head())
    except Exception as e:
        print(f"   Error: {e}")

    # Test 3: Multiple currencies
    print("\n3. Fetching multiple currencies:")
    try:
        fetcher = NBPFetcher()
        df = fetcher.fetch_multiple(['USD', 'EUR', 'GBP'],
                                    start_date='20240101',
                                    end_date='20240131')
        print(f"   Retrieved {len(df)} rows")
        print(df.head(10))
    except Exception as e:
        print(f"   Error: {e}")

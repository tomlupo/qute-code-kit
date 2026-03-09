#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pandas>=2.0",
#   "requests>=2.28",
#   "beautifulsoup4>=4.12",
# ]
# ///
"""
Stooq Corporate Actions Fetcher

Fetches corporate actions data from stooq.pl including:
- Dividends (Dywidenda)
- Subscription rights (Prawo Poboru)
- Acquisition rights (Prawo Nabycia)
- Allotment rights (Prawo Objęcia)
- Stock splits (Split)
- Denominations (Denominacja)

URL Pattern: https://stooq.pl/q/m/?s={ticker}&l=0

Usage:
    uv run fetch_stooq_corporate_actions.py PKO
    uv run fetch_stooq_corporate_actions.py CDR
    uv run fetch_stooq_corporate_actions.py  # Run self-tests
"""

import pandas as pd
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict
from datetime import datetime
import re
from io import StringIO

from utils import (
    get_cache_manager,
    get_rate_limiter,
    create_identifier,
    handle_api_error
)


class StooqCorporateActionsFetcher:
    """Fetcher for stooq.pl corporate actions data."""

    BASE_URL = "https://stooq.pl/q/m/"

    # Event type mapping (Polish to English)
    EVENT_TYPES = {
        'Dywidenda': 'Dividend',
        'Prawo Poboru': 'Subscription Rights',
        'Prawo Nabycia': 'Acquisition Rights',
        'Prawo Objęcia': 'Allotment Rights',
        'Split': 'Stock Split',
        'Denominacja': 'Denomination'
    }

    def __init__(self, use_cache: bool = True, cache_hours: int = 168):  # 1 week cache
        """
        Initialize corporate actions fetcher.

        Args:
            use_cache: Whether to use caching
            cache_hours: Cache validity (default 168h = 1 week)
        """
        self.use_cache = use_cache
        self.cache_hours = cache_hours
        self.cache = get_cache_manager()
        self.rate_limiter = get_rate_limiter()

    def fetch(self, ticker: str) -> pd.DataFrame:
        """
        Fetch corporate actions for a ticker.

        Args:
            ticker: Stock ticker (e.g., 'pko', 'cdr', 'pzu')

        Returns:
            DataFrame with columns:
                - Date: Action date
                - Event: Event type (English)
                - Event_PL: Event type (Polish)
                - Nominal: Nominal value
                - Divisor: Adjustment divisor
                - Pct: Percentage (if available in event name)

        Raises:
            ValueError: If ticker returns no data
            requests.RequestException: If request fails
        """
        # Normalize ticker
        ticker = self._normalize_ticker(ticker)

        # Create cache identifier
        cache_id = create_identifier(ticker, 'corporate_actions')

        # Try cache first
        if self.use_cache:
            cached = self.cache.get('stooq_ca', cache_id, max_age_hours=self.cache_hours)
            if cached is not None:
                print(f"[Stooq CA] Using cached data for {ticker}")
                return cached

        # Build URL
        url = f"{self.BASE_URL}?s={ticker}&l=0"  # l=0 means show all

        try:
            # Rate limiting
            self.rate_limiter.wait('stooq')

            # Fetch data
            print(f"[Stooq CA] Fetching corporate actions for {ticker}...")
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Find the operations table
            table = soup.find('table')
            if not table:
                print(f"[Stooq CA] No corporate actions found for {ticker}")
                return pd.DataFrame(columns=['Date', 'Event', 'Event_PL', 'Nominal', 'Divisor', 'Pct'])

            # Parse table
            rows = []
            for tr in table.find_all('tr')[1:]:  # Skip header
                cells = tr.find_all('td')
                if len(cells) >= 4:
                    date_str = cells[0].get_text(strip=True)
                    event_str = cells[1].get_text(strip=True)
                    nominal_str = cells[2].get_text(strip=True)
                    divisor_str = cells[3].get_text(strip=True)

                    # Parse date (e.g., "pon, 4 sie 2025")
                    date = self._parse_polish_date(date_str)

                    # Parse event type and percentage
                    event_pl, pct = self._parse_event(event_str)
                    event_en = self.EVENT_TYPES.get(event_pl, event_pl)

                    # Parse numerical values
                    try:
                        nominal = float(nominal_str.replace(',', '.'))
                    except:
                        nominal = None

                    try:
                        divisor = float(divisor_str.replace(',', '.'))
                    except:
                        divisor = None

                    rows.append({
                        'Date': date,
                        'Event': event_en,
                        'Event_PL': event_pl,
                        'Nominal': nominal,
                        'Divisor': divisor,
                        'Pct': pct
                    })

            if not rows:
                print(f"[Stooq CA] No corporate actions parsed for {ticker}")
                df = pd.DataFrame(columns=['Date', 'Event', 'Event_PL', 'Nominal', 'Divisor', 'Pct'])
            else:
                df = pd.DataFrame(rows)
                df = df.sort_values('Date').reset_index(drop=True)

                print(f"[Stooq CA] Found {len(df)} corporate actions for {ticker}")
                print(f"   Types: {df['Event'].value_counts().to_dict()}")

            # Cache result
            if self.use_cache:
                self.cache.set('stooq_ca', cache_id, df)

            return df

        except Exception as e:
            handle_api_error('Stooq CA', e, ticker)
            raise

    def _normalize_ticker(self, ticker: str) -> str:
        """Normalize ticker for Stooq (lowercase, no .pl)"""
        if ticker.lower().endswith('.pl'):
            ticker = ticker[:-3]
        return ticker.lower()

    def _parse_polish_date(self, date_str: str) -> pd.Timestamp:
        """
        Parse Polish date string.

        Examples:
            "pon, 4 sie 2025" -> 2025-08-04
            "śro, 7 sie 2024" -> 2024-08-07
        """
        # Polish month abbreviations
        months = {
            'sty': 1, 'lut': 2, 'mar': 3, 'kwi': 4, 'maj': 5, 'cze': 6,
            'lip': 7, 'sie': 8, 'wrz': 9, 'paź': 10, 'lis': 11, 'gru': 12
        }

        # Extract day, month, year
        # Pattern: "day_name, day month year"
        parts = date_str.split(',')[1].strip().split()
        if len(parts) == 3:
            day = int(parts[0])
            month_str = parts[1]
            year = int(parts[2])

            month = months.get(month_str, 1)

            return pd.Timestamp(year=year, month=month, day=day)
        else:
            raise ValueError(f"Cannot parse date: {date_str}")

    def _parse_event(self, event_str: str) -> tuple:
        """
        Parse event string to extract type and percentage.

        Examples:
            "Dywidenda 6.75%" -> ("Dywidenda", 6.75)
            "Prawo Poboru 7.72%" -> ("Prawo Poboru", 7.72)
            "Split" -> ("Split", None)
        """
        # Extract percentage if present
        pct_match = re.search(r'(\d+\.?\d*)\s*%', event_str)
        pct = float(pct_match.group(1)) if pct_match else None

        # Remove percentage from event type
        event_type = re.sub(r'\s+\d+\.?\d*\s*%', '', event_str).strip()

        return event_type, pct

    def calculate_adjusted_prices(self, prices: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """
        Calculate adjusted prices using corporate actions.

        Args:
            prices: DataFrame with Date and Close columns
            ticker: Stock ticker

        Returns:
            DataFrame with additional Close_Adj column

        Methodology:
            - Stooq divisors are cumulative adjustment factors
            - To adjust: Price_Adjusted = Price_Raw / Cumulative_Divisor
            - We need to build cumulative divisor from all events
        """
        print(f"\n[Stooq CA] Calculating adjusted prices for {ticker}...")

        # Fetch corporate actions
        ca = self.fetch(ticker)

        if ca.empty:
            print(f"   No corporate actions, returning unadjusted prices")
            prices['Close_Adj'] = prices['Close']
            return prices

        # Ensure dates are datetime
        prices = prices.copy()
        prices['Date'] = pd.to_datetime(prices['Date'])
        ca['Date'] = pd.to_datetime(ca['Date'])

        # Sort by date
        ca = ca.sort_values('Date')

        # Calculate cumulative divisor for each date
        # Start with 1.0 (no adjustment for latest data)
        # Work backwards: older data needs more adjustment

        # Get all unique dates
        all_dates = pd.DataFrame({'Date': sorted(set(prices['Date'].tolist() + ca['Date'].tolist()))})

        # Merge corporate actions
        all_dates = all_dates.merge(ca[['Date', 'Divisor']], on='Date', how='left')

        # Forward fill divisors (divisor applies from event date forward)
        all_dates['Divisor'] = all_dates['Divisor'].fillna(1.0)

        # Calculate cumulative divisor from LATEST date backwards
        # This ensures latest prices are not adjusted, older prices are
        all_dates = all_dates.sort_values('Date', ascending=False)
        all_dates['Cumulative_Divisor'] = all_dates['Divisor'].cumprod()
        all_dates = all_dates.sort_values('Date')

        # Merge with prices
        result = prices.merge(all_dates[['Date', 'Cumulative_Divisor']], on='Date', how='left')

        # Fill missing cumulative divisors
        result['Cumulative_Divisor'] = result['Cumulative_Divisor'].fillna(1.0)

        # Calculate adjusted close
        result['Close_Adj'] = result['Close'] / result['Cumulative_Divisor']

        print(f"   Applied {len(ca)} corporate actions")
        print(f"   Adjustment range: {result['Cumulative_Divisor'].min():.6f} to {result['Cumulative_Divisor'].max():.6f}")

        return result[['Date', 'Open', 'High', 'Low', 'Close', 'Close_Adj', 'Volume']]


def fetch_corporate_actions(ticker: str, use_cache: bool = True) -> pd.DataFrame:
    """
    Convenience function to fetch corporate actions.

    Args:
        ticker: Stock ticker
        use_cache: Whether to use caching

    Returns:
        DataFrame with corporate actions
    """
    fetcher = StooqCorporateActionsFetcher(use_cache=use_cache)
    return fetcher.fetch(ticker)


def calculate_adjusted_prices(prices: pd.DataFrame, ticker: str, use_cache: bool = True) -> pd.DataFrame:
    """
    Convenience function to calculate adjusted prices.

    Args:
        prices: DataFrame with Date, Close columns
        ticker: Stock ticker
        use_cache: Whether to use caching

    Returns:
        DataFrame with Close_Adj column added
    """
    fetcher = StooqCorporateActionsFetcher(use_cache=use_cache)
    return fetcher.calculate_adjusted_prices(prices, ticker)


if __name__ == '__main__':
    import sys
    sys.path.insert(0, '.')
    from fetch_stooq import fetch_stooq

    print("Testing Stooq Corporate Actions Fetcher...")

    # Test 1: Fetch corporate actions
    print("\n" + "="*80)
    print("TEST 1: Fetch Corporate Actions for PKO")
    print("="*80)

    try:
        ca = fetch_corporate_actions('pko')
        print(f"\nFetched {len(ca)} corporate actions:")
        print(ca.to_string())
    except Exception as e:
        print(f"Error: {e}")

    # Test 2: Calculate adjusted prices
    print("\n" + "="*80)
    print("TEST 2: Calculate Adjusted Prices")
    print("="*80)

    try:
        # Fetch raw prices
        prices = fetch_stooq('pko', start_date='20200101', end_date='20241231')
        print(f"\nFetched {len(prices)} days of price data")

        # Calculate adjusted prices
        fetcher = StooqCorporateActionsFetcher()
        adjusted = fetcher.calculate_adjusted_prices(prices, 'pko')

        print(f"\nAdjusted prices calculated:")
        print(adjusted[['Date', 'Close', 'Close_Adj']].head(10).to_string())
        print("...")
        print(adjusted[['Date', 'Close', 'Close_Adj']].tail(10).to_string())

        # Compare
        print(f"\nAdjustment Impact:")
        print(f"   Latest (unadjusted): {adjusted.iloc[-1]['Close']:.2f}")
        print(f"   Latest (adjusted): {adjusted.iloc[-1]['Close_Adj']:.2f}")
        print(f"   Oldest (unadjusted): {adjusted.iloc[0]['Close']:.2f}")
        print(f"   Oldest (adjusted): {adjusted.iloc[0]['Close_Adj']:.2f}")
        print(f"   Total adjustment factor: {adjusted.iloc[0]['Close'] / adjusted.iloc[0]['Close_Adj']:.4f}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pandas>=2.0",
# ]
# ///
"""
Stooq Corporate Actions Fetcher using Firecrawl

Efficiently fetches corporate actions data from stooq.pl using Firecrawl MCP.
This is the RECOMMENDED method - simple, reliable, and uses existing infrastructure.

Requires FIRECRAWL_API_KEY environment variable or .env file.

Usage:
    uv run fetch_stooq_corporate_actions_firecrawl.py PKO
    uv run fetch_stooq_corporate_actions_firecrawl.py  # Run self-tests

Module usage:
    from fetch_stooq_corporate_actions_firecrawl import fetch_corporate_actions, calculate_adjusted_prices

    # Fetch corporate actions
    ca = fetch_corporate_actions('pko')

    # Calculate adjusted prices
    adjusted = calculate_adjusted_prices(prices_df, 'pko')
"""

import pandas as pd
import re
from datetime import datetime
from typing import Optional
from pathlib import Path
import pickle


class StooqCorporateActionsFirecrawl:
    """Fetcher for stooq.pl corporate actions using Firecrawl MCP."""

    # Event type mapping (Polish to English)
    EVENT_TYPES = {
        'Dywidenda': 'Dividend',
        'Prawo Poboru': 'Subscription Rights',
        'Prawo Nabycia': 'Acquisition Rights',
        'Prawo Objęcia': 'Allotment Rights',
        'Split': 'Stock Split',
        'Denominacja': 'Denomination'
    }

    def __init__(self, use_cache: bool = True, cache_hours: int = 168):
        """
        Initialize fetcher.

        Args:
            use_cache: Whether to cache results (default True)
            cache_hours: Cache validity in hours (default 168 = 1 week)
        """
        self.use_cache = use_cache
        self.cache_hours = cache_hours
        self.cache_dir = Path('data/cache/corporate_actions')
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch(self, ticker: str, firecrawl_scrape_func) -> pd.DataFrame:
        """
        Fetch corporate actions for a ticker.

        Args:
            ticker: Stock ticker (e.g., 'pko', 'cdr')
            firecrawl_scrape_func: The firecrawl scraping function to use

        Returns:
            DataFrame with columns:
                - Date: Action date
                - Event: Event type (English)
                - Event_PL: Event type (Polish)
                - Nominal: Nominal value
                - Divisor: Adjustment divisor
                - Pct: Percentage (from event name)
        """
        # Normalize ticker
        ticker = self._normalize_ticker(ticker)

        # Check cache first
        if self.use_cache:
            cached = self._load_from_cache(ticker)
            if cached is not None:
                print(f"[Stooq CA] Using cached data for {ticker}")
                return cached

        # Fetch from Firecrawl
        url = f"https://stooq.pl/q/m/?s={ticker}"

        print(f"[Stooq CA] Fetching corporate actions for {ticker} via Firecrawl...")

        try:
            result = firecrawl_scrape_func(url, formats=['markdown'])
            markdown = result.get('markdown', '')

            # Parse markdown table
            df = self._parse_markdown_table(markdown)

            if df.empty:
                print(f"[Stooq CA] No corporate actions found for {ticker}")
            else:
                print(f"[Stooq CA] Found {len(df)} corporate actions for {ticker}")
                print(f"   Types: {df['Event'].value_counts().to_dict()}")

            # Cache result
            if self.use_cache:
                self._save_to_cache(ticker, df)

            return df

        except Exception as e:
            print(f"[Stooq CA] Error fetching {ticker}: {e}")
            return pd.DataFrame(columns=['Date', 'Event', 'Event_PL', 'Nominal', 'Divisor', 'Pct'])

    def _parse_markdown_table(self, markdown: str) -> pd.DataFrame:
        """
        Parse corporate actions table from markdown.

        Expected format:
        | Data | Zdarzenie | Nominalnie | Dzielnik |
        | pon, 4 sie 2025 | Dywidenda 6.75% | 5.48 | 1.07241015 |
        """
        rows = []

        # Find all table rows with pipe separators
        lines = markdown.split('\n')
        in_table = False

        for line in lines:
            # Skip header and separator lines
            if '| Data |' in line or '| --- |' in line or '|---' in line:
                in_table = True
                continue

            if not in_table:
                continue

            # Parse data row
            if line.strip().startswith('|') and line.count('|') >= 4:
                parts = [p.strip() for p in line.split('|')]

                # Filter empty parts
                parts = [p for p in parts if p]

                if len(parts) >= 4:
                    date_str = parts[0]
                    event_str = parts[1]
                    nominal_str = parts[2]
                    divisor_str = parts[3]

                    # Skip if this looks like a header
                    if 'Data' in date_str or 'Zdarzenie' in event_str:
                        continue

                    try:
                        # Parse date
                        date = self._parse_polish_date(date_str)

                        # Parse event type and percentage
                        event_pl, pct = self._parse_event(event_str)
                        event_en = self.EVENT_TYPES.get(event_pl, event_pl)

                        # Parse numeric values
                        nominal = float(nominal_str.replace(',', '.')) if nominal_str and nominal_str != '-' else None
                        divisor = float(divisor_str.replace(',', '.')) if divisor_str and divisor_str != '-' else None

                        rows.append({
                            'Date': date,
                            'Event': event_en,
                            'Event_PL': event_pl,
                            'Nominal': nominal,
                            'Divisor': divisor,
                            'Pct': pct
                        })
                    except Exception as e:
                        print(f"[Stooq CA] Warning: Could not parse row: {parts[:2]} - {e}")
                        continue

        if not rows:
            return pd.DataFrame(columns=['Date', 'Event', 'Event_PL', 'Nominal', 'Divisor', 'Pct'])

        df = pd.DataFrame(rows)
        df = df.sort_values('Date').reset_index(drop=True)
        return df

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
            'lip': 7, 'sie': 8, 'wrz': 9, 'paź': 10, 'paz': 10, 'lis': 11, 'gru': 12
        }

        # Extract day, month, year: "day_name, day month year"
        parts = date_str.split(',')
        if len(parts) >= 2:
            date_parts = parts[1].strip().split()
            if len(date_parts) >= 3:
                day = int(date_parts[0])
                month_str = date_parts[1]
                year = int(date_parts[2])

                month = months.get(month_str, 1)

                return pd.Timestamp(year=year, month=month, day=day)

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

    def _normalize_ticker(self, ticker: str) -> str:
        """Normalize ticker (lowercase, no .pl suffix)"""
        if ticker.lower().endswith('.pl'):
            ticker = ticker[:-3]
        return ticker.lower()

    def _load_from_cache(self, ticker: str) -> Optional[pd.DataFrame]:
        """Load corporate actions from cache if fresh enough"""
        cache_file = self.cache_dir / f'{ticker}.pkl'

        if not cache_file.exists():
            return None

        # Check age
        age_hours = (datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)).total_seconds() / 3600

        if age_hours > self.cache_hours:
            return None

        try:
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            print(f"[Stooq CA] Warning: Cache read error for {ticker}: {e}")
            return None

    def _save_to_cache(self, ticker: str, df: pd.DataFrame):
        """Save corporate actions to cache"""
        cache_file = self.cache_dir / f'{ticker}.pkl'

        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(df, f)
        except Exception as e:
            print(f"[Stooq CA] Warning: Cache write error for {ticker}: {e}")

    def calculate_adjusted_prices(self, prices: pd.DataFrame, ticker: str,
                                 firecrawl_scrape_func) -> pd.DataFrame:
        """
        Calculate adjusted prices using corporate actions.

        Args:
            prices: DataFrame with Date and Close columns
            ticker: Stock ticker
            firecrawl_scrape_func: Firecrawl scraping function

        Returns:
            DataFrame with Close_Adj column added

        Methodology:
            - Fetch corporate actions
            - Apply divisors cumulatively from latest to earliest
            - Adjusted_Price(t) = Unadjusted_Price(t) / Cumulative_Divisor(t)
        """
        print(f"\n[Stooq CA] Calculating adjusted prices for {ticker}...")

        # Fetch corporate actions
        ca = self.fetch(ticker, firecrawl_scrape_func)

        if ca.empty:
            print(f"   No corporate actions, returning unadjusted prices")
            prices = prices.copy()
            prices['Close_Adj'] = prices['Close']
            return prices

        # Ensure dates are datetime
        prices = prices.copy()
        prices['Date'] = pd.to_datetime(prices['Date'])
        ca['Date'] = pd.to_datetime(ca['Date'])

        # Get all unique dates
        all_dates = pd.DataFrame({
            'Date': sorted(set(prices['Date'].tolist() + ca['Date'].tolist()))
        })

        # Merge corporate actions
        all_dates = all_dates.merge(ca[['Date', 'Divisor']], on='Date', how='left')

        # Fill missing divisors with 1.0 (no adjustment)
        all_dates['Divisor'] = all_dates['Divisor'].fillna(1.0)

        # Calculate cumulative divisor from LATEST date backwards
        # This ensures latest prices remain unadjusted
        all_dates = all_dates.sort_values('Date', ascending=False)
        all_dates['Cumulative_Divisor'] = all_dates['Divisor'].cumprod()
        all_dates = all_dates.sort_values('Date')

        # Merge with prices
        result = prices.merge(all_dates[['Date', 'Cumulative_Divisor']], on='Date', how='left')

        # Fill any missing cumulative divisors
        result['Cumulative_Divisor'] = result['Cumulative_Divisor'].fillna(1.0)

        # Calculate adjusted close
        result['Close_Adj'] = result['Close'] / result['Cumulative_Divisor']

        print(f"   Applied {len(ca)} corporate actions")
        print(f"   Adjustment range: {result['Cumulative_Divisor'].min():.6f} to {result['Cumulative_Divisor'].max():.6f}")

        # Return with standard columns
        return result[['Date', 'Open', 'High', 'Low', 'Close', 'Close_Adj', 'Volume']]


# Convenience functions for use in other scripts

def fetch_corporate_actions(ticker: str, firecrawl_scrape_func, use_cache: bool = True) -> pd.DataFrame:
    """
    Fetch corporate actions for a ticker.

    Args:
        ticker: Stock ticker (e.g., 'pko')
        firecrawl_scrape_func: Firecrawl scraping function
        use_cache: Whether to use caching

    Returns:
        DataFrame with corporate actions
    """
    fetcher = StooqCorporateActionsFirecrawl(use_cache=use_cache)
    return fetcher.fetch(ticker, firecrawl_scrape_func)


def calculate_adjusted_prices(prices: pd.DataFrame, ticker: str,
                             firecrawl_scrape_func, use_cache: bool = True) -> pd.DataFrame:
    """
    Calculate adjusted prices using corporate actions.

    Args:
        prices: DataFrame with Date, Close columns
        ticker: Stock ticker
        firecrawl_scrape_func: Firecrawl scraping function
        use_cache: Whether to use caching

    Returns:
        DataFrame with Close_Adj column added
    """
    fetcher = StooqCorporateActionsFirecrawl(use_cache=use_cache)
    return fetcher.calculate_adjusted_prices(prices, ticker, firecrawl_scrape_func)

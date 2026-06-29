#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pandas>=2.0",
#   "requests>=2.28",
# ]
# ///
"""
Yahoo Finance Direct API fetcher.

Bypasses yfinance library and uses direct API calls to avoid rate limiting issues.
Supports ISIN-to-ticker conversion via Yahoo search API.
Fetches prices, dividends, and splits.

Usage:
    uv run fetch_yahoo_direct.py XTB.WA 2024-01-01 2024-12-31
    uv run fetch_yahoo_direct.py PLXTRDM00011 2024-01-01  # ISIN
    uv run fetch_yahoo_direct.py  # Run self-tests

Module usage:
    from fetch_yahoo_direct import YahooDirectFetcher, fetch_by_isin

    # By ticker
    fetcher = YahooDirectFetcher()
    prices, dividends, splits = fetcher.fetch('XTB.WA', '2024-01-01', '2025-01-01')

    # By ISIN (auto-converts to ticker)
    prices, dividends, splits, mapping = fetch_by_isin(
        ['PLXTRDM00011', 'US0378331005'],
        start_date='2024-01-01',
        end_date='2025-01-01'
    )
"""

import requests
import pandas as pd
from typing import Optional, Tuple
from datetime import datetime
import time


class YahooDirectFetcher:
    """Fetcher using Yahoo Finance direct API (bypasses yfinance library)."""

    BASE_URL = 'https://query1.finance.yahoo.com/v8/finance/chart'
    SEARCH_URL = 'https://query2.finance.yahoo.com/v1/finance/search'
    HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    def __init__(self, delay: float = 0.5):
        """
        Initialize fetcher.

        Args:
            delay: Delay between requests in seconds (rate limiting)
        """
        self.delay = delay
        self._last_request = 0

    def _rate_limit(self):
        """Apply rate limiting between requests."""
        elapsed = time.time() - self._last_request
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self._last_request = time.time()

    def isin_to_ticker(self, isin: str) -> Optional[str]:
        """
        Convert ISIN to Yahoo Finance ticker using search API.

        Args:
            isin: ISIN code (e.g., 'PLXTRDM00011')

        Returns:
            Yahoo Finance ticker (e.g., 'XTB.WA') or None if not found
        """
        self._rate_limit()

        try:
            resp = requests.get(
                self.SEARCH_URL,
                params={'q': isin, 'quotesCount': 5},
                headers=self.HEADERS,
                timeout=10
            )
            data = resp.json()

            if data.get('quotes'):
                # Return first result's symbol
                return data['quotes'][0]['symbol']
        except Exception as e:
            print(f"[Yahoo Direct] Error searching for {isin}: {e}")

        return None

    def fetch(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        include_events: bool = True
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Fetch price data, dividends, and splits from Yahoo Finance.

        Args:
            ticker: Yahoo Finance ticker symbol (e.g., 'XTB.WA', 'AAPL')
            start_date: Start date (YYYY-MM-DD), None for 1 year ago
            end_date: End date (YYYY-MM-DD), None for today
            include_events: Whether to fetch dividends and splits

        Returns:
            Tuple of (prices_df, dividends_df, splits_df)
        """
        self._rate_limit()

        # Convert dates to timestamps
        if start_date:
            start_ts = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp())
        else:
            start_ts = int((datetime.now().timestamp()) - 365 * 24 * 60 * 60)

        if end_date:
            end_ts = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp()) + 86400
        else:
            end_ts = int(datetime.now().timestamp()) + 86400

        params = {
            'period1': start_ts,
            'period2': end_ts,
            'interval': '1d',
        }
        if include_events:
            params['events'] = 'div,splits'

        try:
            resp = requests.get(
                f'{self.BASE_URL}/{ticker}',
                params=params,
                headers=self.HEADERS,
                timeout=15
            )
            data = resp.json()

            if 'chart' not in data or not data['chart']['result']:
                return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

            result = data['chart']['result'][0]

            # Parse prices
            timestamps = result.get('timestamp', [])
            if not timestamps:
                return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

            quotes = result['indicators']['quote'][0]

            prices_df = pd.DataFrame({
                'date': pd.to_datetime(timestamps, unit='s'),
                'open': quotes.get('open'),
                'high': quotes.get('high'),
                'low': quotes.get('low'),
                'close': quotes.get('close'),
                'volume': quotes.get('volume')
            })

            # Adjusted close
            if 'adjclose' in result['indicators']:
                prices_df['adj_close'] = result['indicators']['adjclose'][0]['adjclose']

            # Parse events
            events = result.get('events', {})

            # Dividends
            dividends = []
            if 'dividends' in events:
                for ts, div_data in events['dividends'].items():
                    dividends.append({
                        'date': pd.to_datetime(int(ts), unit='s'),
                        'dividend': div_data['amount']
                    })
            dividends_df = pd.DataFrame(dividends) if dividends else pd.DataFrame()

            # Splits
            splits = []
            if 'splits' in events:
                for ts, split_data in events['splits'].items():
                    splits.append({
                        'date': pd.to_datetime(int(ts), unit='s'),
                        'numerator': split_data['numerator'],
                        'denominator': split_data['denominator'],
                        'ratio': split_data['numerator'] / split_data['denominator']
                    })
            splits_df = pd.DataFrame(splits) if splits else pd.DataFrame()

            return prices_df, dividends_df, splits_df

        except Exception as e:
            print(f"[Yahoo Direct] Error fetching {ticker}: {e}")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    def fetch_prices_only(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Fetch only price data (no dividends/splits).

        Args:
            ticker: Yahoo Finance ticker symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            DataFrame with OHLCV data
        """
        prices, _, _ = self.fetch(ticker, start_date, end_date, include_events=False)
        return prices


def fetch_by_isin(
    isins: list,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    delay: float = 0.5
) -> Tuple[dict, dict, dict, dict]:
    """
    Fetch prices and dividends for multiple ISINs.

    Automatically converts ISINs to Yahoo Finance tickers using search API.

    Args:
        isins: List of ISIN codes
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        delay: Delay between requests in seconds

    Returns:
        Tuple of (prices_dict, dividends_dict, splits_dict, isin_to_ticker_mapping)
        Each dict is keyed by ISIN.
    """
    fetcher = YahooDirectFetcher(delay=delay)

    prices = {}
    dividends = {}
    splits = {}
    isin_to_ticker = {}

    for i, isin in enumerate(isins):
        print(f"[{i+1}/{len(isins)}] Processing {isin}...", end=' ')

        # Convert ISIN to ticker
        ticker = fetcher.isin_to_ticker(isin)
        if not ticker:
            print("NOT FOUND")
            continue

        isin_to_ticker[isin] = ticker
        print(f"-> {ticker}", end=' ')

        # Fetch data
        p, d, s = fetcher.fetch(ticker, start_date, end_date)

        if not p.empty:
            p['isin'] = isin
            p['ticker'] = ticker
            prices[isin] = p
            print(f"({len(p)} prices", end='')
        else:
            print("(NO DATA", end='')

        if not d.empty:
            d['isin'] = isin
            d['ticker'] = ticker
            dividends[isin] = d
            print(f", {len(d)} divs", end='')

        if not s.empty:
            s['isin'] = isin
            s['ticker'] = ticker
            splits[isin] = s
            print(f", {len(s)} splits", end='')

        print(")")

    return prices, dividends, splits, isin_to_ticker


def save_isin_data(
    isins: list,
    output_dir: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> None:
    """
    Fetch data for ISINs and save to Excel files.

    Args:
        isins: List of ISIN codes
        output_dir: Directory to save output files
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Creates:
        - {output_dir}/prices.xlsx
        - {output_dir}/dividends.xlsx
        - {output_dir}/splits.xlsx (if any)
        - {output_dir}/isin_ticker_mapping.xlsx
    """
    import os
    os.makedirs(output_dir, exist_ok=True)

    prices, dividends, splits, mapping = fetch_by_isin(isins, start_date, end_date)

    # Combine and save prices
    if prices:
        prices_df = pd.concat(prices.values(), ignore_index=True)
        prices_df.to_excel(f'{output_dir}/prices.xlsx', index=False)
        print(f"Saved prices: {len(prices_df)} rows, {len(prices)} ISINs")

    # Combine and save dividends
    if dividends:
        divs_df = pd.concat(dividends.values(), ignore_index=True)
        divs_df.to_excel(f'{output_dir}/dividends.xlsx', index=False)
        print(f"Saved dividends: {len(divs_df)} rows")

    # Combine and save splits
    if splits:
        splits_df = pd.concat(splits.values(), ignore_index=True)
        splits_df.to_excel(f'{output_dir}/splits.xlsx', index=False)
        print(f"Saved splits: {len(splits_df)} rows")

    # Save mapping
    mapping_df = pd.DataFrame(list(mapping.items()), columns=['isin', 'ticker'])
    mapping_df.to_excel(f'{output_dir}/isin_ticker_mapping.xlsx', index=False)
    print(f"Saved mapping: {len(mapping_df)} ISINs")


if __name__ == '__main__':
    print("Testing Yahoo Finance Direct API fetcher...")

    # Test 1: Single ticker
    print("\n1. Fetching XTB.WA (Polish stock):")
    fetcher = YahooDirectFetcher()
    prices, divs, splits = fetcher.fetch('XTB.WA', '2024-01-01', '2025-01-01')
    print(f"   Prices: {len(prices)} rows")
    print(f"   Dividends: {len(divs)} rows")
    print(f"   Splits: {len(splits)} rows")
    if not prices.empty:
        print(prices.tail())

    # Test 2: ISIN lookup
    print("\n2. ISIN to ticker conversion:")
    ticker = fetcher.isin_to_ticker('PLXTRDM00011')
    print(f"   PLXTRDM00011 -> {ticker}")

    # Test 3: Multiple ISINs
    print("\n3. Fetching multiple ISINs:")
    test_isins = ['PLXTRDM00011', 'US0378331005']
    prices, divs, splits, mapping = fetch_by_isin(
        test_isins,
        start_date='2024-01-01',
        end_date='2024-12-31'
    )
    print(f"\nMapping: {mapping}")
    print(f"Prices fetched for: {list(prices.keys())}")
    print(f"Dividends fetched for: {list(divs.keys())}")

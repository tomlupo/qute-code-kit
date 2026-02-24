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
FinancialData.Net data fetcher.

Downloads market data from FinancialData.Net API (https://financialdata.net).
Covers US/international stocks, ETFs, commodities, crypto, forex, options,
futures, fundamentals, financial statements, ratios, and more.

Requires API key: https://financialdata.net
Free tier available with basic endpoints; Standard/Premium for advanced data.

API key can be provided via:
1. .env file: FINANCIAL_DATA_API_KEY=your_key
2. Environment variable: FINANCIAL_DATA_API_KEY
3. Direct parameter

Usage:
    uv run fetch_financialdata.py AAPL 2024-01-01 2024-12-31
    uv run fetch_financialdata.py MSFT 2024-01-01
    uv run fetch_financialdata.py  # Run self-tests (requires API key)
"""

import os
import pandas as pd
import requests
from typing import Optional, Any
from datetime import datetime, date

from utils import (
    get_cache_manager,
    get_rate_limiter,
    normalize_date,
    normalize_date_display,
    create_identifier,
    handle_api_error,
)


class FinancialDataFetcher:
    """Fetcher for FinancialData.Net market data."""

    BASE_URL = "https://financialdata.net/api/v1"

    # Endpoint definitions: (path, default_limit, tier)
    ENDPOINTS = {
        # Symbol lists (Free)
        "stock-symbols": ("stock-symbols", 500),
        "international-stock-symbols": ("international-stock-symbols", 500),
        "etf-symbols": ("etf-symbols", 500),
        "commodity-symbols": ("commodity-symbols", None),
        "otc-symbols": ("otc-symbols", 500),
        "index-symbols": ("index-symbols", None),
        "crypto-symbols": ("crypto-symbols", 500),
        "forex-symbols": ("forex-symbols", None),
        "futures-symbols": ("futures-symbols", 500),
        # Market data
        "stock-quotes": ("stock-quotes", 300),
        "stock-prices": ("stock-prices", 300),
        "international-stock-prices": ("international-stock-prices", 300),
        "minute-prices": ("minute-prices", 300),
        "latest-prices": ("latest-prices", 300),
        "commodity-prices": ("commodity-prices", 300),
        "otc-prices": ("otc-prices", 300),
        "otc-volume": ("otc-volume", None),
        # Indexes
        "index-quotes": ("index-quotes", 300),
        "index-prices": ("index-prices", 300),
        "index-constituents": ("index-constituents", 300),
        # Derivatives
        "option-chain": ("option-chain", 300),
        "option-prices": ("option-prices", 300),
        "option-greeks": ("option-greeks", 300),
        "futures-prices": ("futures-prices", 300),
        # Crypto
        "crypto-information": ("crypto-information", None),
        "crypto-quotes": ("crypto-quotes", 300),
        "crypto-prices": ("crypto-prices", 300),
        "crypto-minute-prices": ("crypto-minute-prices", 300),
        # Forex
        "forex-quotes": ("forex-quotes", 300),
        "forex-prices": ("forex-prices", 300),
        "forex-minute-prices": ("forex-minute-prices", 300),
        # Company info
        "company-information": ("company-information", None),
        "international-company-information": ("international-company-information", None),
        "key-metrics": ("key-metrics", None),
        "market-cap": ("market-cap", None),
        "employee-count": ("employee-count", None),
        "executive-compensation": ("executive-compensation", 100),
        "securities-information": ("securities-information", None),
        # Financial statements
        "income-statements": ("income-statements", 50),
        "balance-sheet-statements": ("balance-sheet-statements", 50),
        "cash-flow-statements": ("cash-flow-statements", 50),
        "international-income-statements": ("international-income-statements", 50),
        "international-balance-sheet-statements": ("international-balance-sheet-statements", 50),
        "international-cash-flow-statements": ("international-cash-flow-statements", 50),
        # Financial ratios
        "liquidity-ratios": ("liquidity-ratios", 50),
        "solvency-ratios": ("solvency-ratios", 50),
        "efficiency-ratios": ("efficiency-ratios", 50),
        "profitability-ratios": ("profitability-ratios", 50),
        "valuation-ratios": ("valuation-ratios", 50),
        # News & events
        "press-releases": ("press-releases", 1),
        "sec-press-releases": ("sec-press-releases", None),
        "fed-press-releases": ("fed-press-releases", None),
        "earnings-calendar": ("earnings-calendar", None),
        "ipo-calendar": ("ipo-calendar", None),
        "splits-calendar": ("splits-calendar", None),
        "dividends-calendar": ("dividends-calendar", None),
        "economic-calendar": ("economic-calendar", None),
        # Insider & institutional
        "insider-transactions": ("insider-transactions", None),
        "proposed-sales": ("proposed-sales", None),
        "senate-trading": ("senate-trading", None),
        "house-trading": ("house-trading", None),
        "institutional-investors": ("institutional-investors", None),
        "institutional-holdings": ("institutional-holdings", None),
        "institutional-portfolio-statistics": ("institutional-portfolio-statistics", None),
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        use_cache: bool = True,
        cache_hours: int = 24,
    ):
        """
        Initialize FinancialData.Net fetcher.

        Args:
            api_key: API key (or set FINANCIAL_DATA_API_KEY env var)
            use_cache: Whether to use caching
            cache_hours: Cache validity in hours
        """
        self.api_key = api_key or os.environ.get("FINANCIAL_DATA_API_KEY")
        if not self.api_key:
            raise ValueError(
                "FinancialData.Net API key required. Set FINANCIAL_DATA_API_KEY "
                "environment variable or pass api_key parameter. "
                "Get key at: https://financialdata.net"
            )

        self.use_cache = use_cache
        self.cache_hours = cache_hours
        self.cache = get_cache_manager()
        self.rate_limiter = get_rate_limiter()

    def _request(
        self,
        endpoint: str,
        params: Optional[dict] = None,
        paginate: bool = False,
    ) -> list[dict]:
        """
        Make API request with optional auto-pagination.

        Args:
            endpoint: API endpoint path (e.g. 'stock-prices')
            params: Query parameters (excluding key)
            paginate: Whether to auto-paginate through all results

        Returns:
            List of result dictionaries

        Raises:
            ValueError: If endpoint unknown or API returns error
            requests.RequestException: On network failure
        """
        if endpoint not in self.ENDPOINTS:
            raise ValueError(
                f"Unknown endpoint: {endpoint}. "
                f"Valid endpoints: {', '.join(sorted(self.ENDPOINTS.keys()))}"
            )

        path, page_limit = self.ENDPOINTS[endpoint]
        url = f"{self.BASE_URL}/{path}"

        params = dict(params or {})
        params["key"] = self.api_key

        all_data: list[dict] = []
        offset = 0

        while True:
            if paginate and page_limit and offset > 0:
                params["offset"] = offset

            self.rate_limiter.wait("financialdata")

            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 401:
                raise ValueError("Invalid FinancialData.Net API key")
            if response.status_code == 403:
                raise ValueError(
                    f"Access denied for endpoint '{endpoint}'. "
                    "Check your subscription tier."
                )
            if response.status_code == 429:
                raise ValueError("FinancialData.Net rate limit exceeded. Wait and retry.")

            response.raise_for_status()

            data = response.json()

            if isinstance(data, list):
                all_data.extend(data)
            elif isinstance(data, dict):
                # Some endpoints return a dict wrapper
                all_data.append(data)

            # Stop pagination if not requested, no limit, or fewer results than limit
            if (
                not paginate
                or page_limit is None
                or (isinstance(data, list) and len(data) < page_limit)
            ):
                break

            offset += page_limit

        return all_data

    def fetch(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        endpoint: str = "stock-prices",
        paginate: bool = True,
        **kwargs,
    ) -> pd.DataFrame:
        """
        Fetch price data from FinancialData.Net.

        Args:
            ticker: Stock/asset identifier (e.g. 'AAPL', 'MSFT')
            start_date: Start date (YYYY-MM-DD or YYYYMMDD)
            end_date: End date (YYYY-MM-DD or YYYYMMDD)
            endpoint: API endpoint to use (default: 'stock-prices')
            paginate: Auto-paginate through all results
            **kwargs: Additional query parameters

        Returns:
            DataFrame with market data

        Raises:
            ValueError: If ticker invalid or no data returned
        """
        ticker_upper = ticker.upper()

        # Build cache identifier
        start_norm = normalize_date(start_date) if start_date else None
        end_norm = normalize_date(end_date) if end_date else None
        cache_id = create_identifier(
            f"{ticker_upper}_{endpoint}", start_norm, end_norm, "financialdata"
        )

        # Try cache first
        if self.use_cache:
            cached = self.cache.get(
                "financialdata", cache_id, max_age_hours=self.cache_hours
            )
            if cached is not None:
                print(f"[FinancialData] Using cached data for {ticker_upper}")
                return cached

        # Build params
        params: dict[str, Any] = {}

        # Endpoints using 'identifiers' (plural, comma-separated) vs 'identifier' (single)
        plural_endpoints = {"stock-quotes", "index-quotes", "crypto-quotes", "forex-quotes"}
        if endpoint in plural_endpoints:
            params["identifiers"] = ticker_upper
        else:
            params["identifier"] = ticker_upper

        # Date handling for minute-prices and crypto-minute-prices
        if endpoint in ("minute-prices", "crypto-minute-prices", "forex-minute-prices"):
            if start_date:
                params["date"] = normalize_date_display(start_date)
        # Period for financial statements and ratios
        elif endpoint in (
            "income-statements", "balance-sheet-statements", "cash-flow-statements",
            "international-income-statements", "international-balance-sheet-statements",
            "international-cash-flow-statements",
            "liquidity-ratios", "solvency-ratios", "efficiency-ratios",
            "profitability-ratios", "valuation-ratios",
        ):
            if "period" not in kwargs:
                params["period"] = "year"

        # Add extra kwargs as params
        params.update(kwargs)

        try:
            start_display = normalize_date_display(start_date) if start_date else "earliest"
            end_display = normalize_date_display(end_date) if end_date else "latest"
            print(
                f"[FinancialData] Fetching {ticker_upper} ({endpoint}) "
                f"from {start_display} to {end_display}"
            )

            data = self._request(endpoint, params, paginate=paginate)

            if not data:
                raise ValueError(
                    f"No data returned for {ticker_upper} from endpoint '{endpoint}'"
                )

            df = pd.DataFrame(data)

            # Normalize date columns
            for col in ("date", "Date"):
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors="coerce")
                    if df[col].dt.tz is not None:
                        df[col] = df[col].dt.tz_localize(None)
                    df.rename(columns={col: "Date"}, inplace=True)

            # Standardize OHLCV column names for price endpoints
            price_endpoints = {
                "stock-prices", "international-stock-prices", "commodity-prices",
                "otc-prices", "index-prices", "crypto-prices", "forex-prices",
                "futures-prices", "latest-prices", "minute-prices",
                "crypto-minute-prices", "forex-minute-prices",
            }
            if endpoint in price_endpoints:
                col_map = {
                    "open": "Open",
                    "high": "High",
                    "low": "Low",
                    "close": "Close",
                    "volume": "Volume",
                    "adjClose": "Adj_Close",
                    "adj_close": "Adj_Close",
                }
                df.rename(columns=col_map, inplace=True)

            # Sort by Date if available
            if "Date" in df.columns:
                df.sort_values("Date", inplace=True)
                df.reset_index(drop=True, inplace=True)

            # Cache result
            if self.use_cache:
                self.cache.set("financialdata", cache_id, df)

            return df

        except Exception as e:
            handle_api_error("FinancialData", e, ticker_upper)
            raise

    def get_stock_prices(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """Fetch historical stock prices."""
        return self.fetch(ticker, start_date, end_date, endpoint="stock-prices")

    def get_stock_quotes(self, tickers: str) -> pd.DataFrame:
        """Fetch real-time stock quotes. Tickers comma-separated (e.g. 'AAPL,MSFT')."""
        return self.fetch(tickers, endpoint="stock-quotes", paginate=False)

    def get_international_stock_prices(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """Fetch international stock prices."""
        return self.fetch(
            ticker, start_date, end_date, endpoint="international-stock-prices"
        )

    def get_minute_prices(
        self, ticker: str, trade_date: str
    ) -> pd.DataFrame:
        """Fetch intraday minute prices for a specific date."""
        return self.fetch(ticker, start_date=trade_date, endpoint="minute-prices")

    def get_commodity_prices(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """Fetch commodity prices."""
        return self.fetch(ticker, start_date, end_date, endpoint="commodity-prices")

    def get_index_prices(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """Fetch index prices."""
        return self.fetch(ticker, start_date, end_date, endpoint="index-prices")

    def get_crypto_prices(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """Fetch cryptocurrency prices."""
        return self.fetch(ticker, start_date, end_date, endpoint="crypto-prices")

    def get_forex_prices(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """Fetch forex prices."""
        return self.fetch(ticker, start_date, end_date, endpoint="forex-prices")

    def get_option_chain(self, ticker: str) -> pd.DataFrame:
        """Fetch option chain for a ticker."""
        return self.fetch(ticker, endpoint="option-chain")

    def get_option_greeks(self, ticker: str) -> pd.DataFrame:
        """Fetch option Greeks for a ticker."""
        return self.fetch(ticker, endpoint="option-greeks")

    def get_futures_prices(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """Fetch futures prices."""
        return self.fetch(ticker, start_date, end_date, endpoint="futures-prices")

    def get_company_info(self, ticker: str) -> pd.DataFrame:
        """Fetch company information."""
        return self.fetch(ticker, endpoint="company-information", paginate=False)

    def get_key_metrics(self, ticker: str) -> pd.DataFrame:
        """Fetch key financial metrics."""
        return self.fetch(ticker, endpoint="key-metrics", paginate=False)

    def get_income_statements(
        self, ticker: str, period: str = "year"
    ) -> pd.DataFrame:
        """Fetch income statements (period: 'year' or 'quarter')."""
        return self.fetch(ticker, endpoint="income-statements", period=period)

    def get_balance_sheet(
        self, ticker: str, period: str = "year"
    ) -> pd.DataFrame:
        """Fetch balance sheet statements (period: 'year' or 'quarter')."""
        return self.fetch(ticker, endpoint="balance-sheet-statements", period=period)

    def get_cash_flow(
        self, ticker: str, period: str = "year"
    ) -> pd.DataFrame:
        """Fetch cash flow statements (period: 'year' or 'quarter')."""
        return self.fetch(ticker, endpoint="cash-flow-statements", period=period)

    def get_financial_ratios(
        self, ticker: str, ratio_type: str = "profitability", period: str = "year"
    ) -> pd.DataFrame:
        """
        Fetch financial ratios.

        Args:
            ticker: Stock ticker
            ratio_type: One of 'liquidity', 'solvency', 'efficiency',
                       'profitability', 'valuation'
            period: 'year' or 'quarter'
        """
        endpoint = f"{ratio_type}-ratios"
        return self.fetch(ticker, endpoint=endpoint, period=period)

    def get_symbols(self, symbol_type: str = "stock") -> pd.DataFrame:
        """
        Fetch symbol lists.

        Args:
            symbol_type: One of 'stock', 'international-stock', 'etf',
                        'commodity', 'otc', 'index', 'crypto', 'forex', 'futures'
        """
        endpoint = f"{symbol_type}-symbols"
        return self.fetch("", endpoint=endpoint, paginate=True)

    def get_earnings_calendar(self) -> pd.DataFrame:
        """Fetch upcoming earnings calendar."""
        return self.fetch("", endpoint="earnings-calendar", paginate=False)

    def get_insider_transactions(self, ticker: str) -> pd.DataFrame:
        """Fetch insider transactions for a ticker."""
        return self.fetch(ticker, endpoint="insider-transactions")

    def get_senate_trading(self) -> pd.DataFrame:
        """Fetch recent senate trading disclosures."""
        return self.fetch("", endpoint="senate-trading")

    def get_house_trading(self) -> pd.DataFrame:
        """Fetch recent house trading disclosures."""
        return self.fetch("", endpoint="house-trading")

    def get_institutional_holders(self, ticker: str) -> pd.DataFrame:
        """Fetch institutional holders for a ticker."""
        return self.fetch(ticker, endpoint="institutional-holdings")

    def fetch_multiple(
        self,
        tickers: list[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        endpoint: str = "stock-prices",
    ) -> dict[str, pd.DataFrame]:
        """
        Fetch data for multiple tickers.

        Args:
            tickers: List of ticker symbols
            start_date: Start date
            end_date: End date
            endpoint: API endpoint to use

        Returns:
            Dictionary mapping ticker -> DataFrame
        """
        results = {}

        for ticker in tickers:
            try:
                df = self.fetch(ticker, start_date, end_date, endpoint=endpoint)
                results[ticker] = df
            except Exception as e:
                print(f"[FinancialData] Skipping {ticker}: {e}")
                continue

        return results


def fetch_financialdata(
    ticker: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    api_key: Optional[str] = None,
    use_cache: bool = True,
    endpoint: str = "stock-prices",
    **kwargs,
) -> pd.DataFrame:
    """
    Convenience function to fetch data from FinancialData.Net.

    Args:
        ticker: Stock/asset identifier
        start_date: Start date
        end_date: End date
        api_key: API key (or set FINANCIAL_DATA_API_KEY env var)
        use_cache: Whether to use caching
        endpoint: API endpoint (default: 'stock-prices')
        **kwargs: Additional query parameters

    Returns:
        DataFrame with market data
    """
    fetcher = FinancialDataFetcher(api_key=api_key, use_cache=use_cache)
    return fetcher.fetch(ticker, start_date, end_date, endpoint=endpoint, **kwargs)


if __name__ == "__main__":
    import sys

    api_key = os.environ.get("FINANCIAL_DATA_API_KEY")
    if not api_key:
        print("Set FINANCIAL_DATA_API_KEY environment variable to test")
        print("Get API key at: https://financialdata.net")
        sys.exit(1)

    print("Testing FinancialData.Net fetcher...\n")

    # Test 1: Stock prices (Free tier)
    print("1. Fetching AAPL stock prices:")
    try:
        df = fetch_financialdata("AAPL", start_date="20240101", end_date="20240131")
        print(f"   Retrieved {len(df)} rows")
        print(f"   Columns: {list(df.columns)}")
        print(df.head())
    except Exception as e:
        print(f"   Error: {e}")

    # Test 2: Commodity prices (Free tier)
    print("\n2. Fetching gold commodity prices:")
    try:
        df = fetch_financialdata(
            "GC", start_date="20240101", end_date="20240131",
            endpoint="commodity-prices",
        )
        print(f"   Retrieved {len(df)} rows")
        print(df.head())
    except Exception as e:
        print(f"   Error: {e}")

    # Test 3: Company information (Standard tier)
    print("\n3. Fetching MSFT company info:")
    try:
        df = fetch_financialdata("MSFT", endpoint="company-information")
        print(f"   Retrieved {len(df)} rows")
        print(df.head())
    except Exception as e:
        print(f"   Error: {e}")

    # Test 4: Income statements (Standard tier)
    print("\n4. Fetching AAPL income statements:")
    try:
        df = fetch_financialdata("AAPL", endpoint="income-statements", period="year")
        print(f"   Retrieved {len(df)} rows")
        print(df.head())
    except Exception as e:
        print(f"   Error: {e}")

    # Test 5: Stock symbols list (Free tier)
    print("\n5. Fetching stock symbol list (first page):")
    try:
        df = fetch_financialdata("", endpoint="stock-symbols")
        print(f"   Retrieved {len(df)} symbols")
        print(df.head())
    except Exception as e:
        print(f"   Error: {e}")

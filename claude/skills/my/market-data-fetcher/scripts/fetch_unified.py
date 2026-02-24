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
Unified market data fetcher with intelligent routing.

Automatically selects the best data source based on:
- Ticker pattern/format
- Data type (stock, index, currency, economic indicator)
- Geographic market
- Security master registry (ISIN lookup, ticker conversion)
- Fallback logic if primary source fails

Usage:
    uv run fetch_unified.py PKO 2024-01-01 2024-12-31
    uv run fetch_unified.py PLXTRDM00011 2024-01-01  # ISIN lookup
    uv run fetch_unified.py USDPLN 2024-01-01       # FX pair
    uv run fetch_unified.py BTC/USDT 2024-01-01     # Crypto
    uv run fetch_unified.py  # Run self-tests
"""

import pandas as pd
from typing import Optional, Literal, List, Tuple
import re

# Import TickerRegistry for security lookups
try:
    from ticker_registry import TickerRegistry
    REGISTRY_AVAILABLE = True
except ImportError:
    REGISTRY_AVAILABLE = False

# Import all fetchers
try:
    from fetch_stooq import StooqFetcher
    STOOQ_AVAILABLE = True
except ImportError:
    STOOQ_AVAILABLE = False

try:
    from fetch_nbp import NBPFetcher
    NBP_AVAILABLE = True
except ImportError:
    NBP_AVAILABLE = False

try:
    from fetch_yahoo import YahooFetcher
    YAHOO_AVAILABLE = True
except ImportError:
    YAHOO_AVAILABLE = False

try:
    from fetch_fred import FREDFetcher
    FRED_AVAILABLE = True
except ImportError:
    FRED_AVAILABLE = False

try:
    from fetch_pandas_datareader import PandasDataReaderFetcher
    PDR_AVAILABLE = True
except ImportError:
    PDR_AVAILABLE = False

try:
    from fetch_tiingo import TiingoFetcher
    TIINGO_AVAILABLE = True
except ImportError:
    TIINGO_AVAILABLE = False

try:
    from fetch_ccxt import CCXTFetcher, is_crypto_symbol
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False

    def is_crypto_symbol(s):
        """Fallback if ccxt not available."""
        return '/' in s or s.upper().endswith(('USDT', 'USDC', 'BTC'))

try:
    from fetch_financialdata import FinancialDataFetcher
    FINANCIALDATA_AVAILABLE = True
except ImportError:
    FINANCIALDATA_AVAILABLE = False


class UnifiedMarketDataFetcher:
    """
    Unified market data fetcher with intelligent source selection.
    """

    # Polish stock symbols (common ones)
    POLISH_STOCKS = [
        'pko', 'cdr', 'pzu', 'peo', 'pkn', 'kgh', 'pge', 'lpp',
        'ale', 'dnp', 'cps', 'jsw', 'pzu', 'tpe', 'mil', 'orange'
    ]

    # Polish indices
    POLISH_INDICES = [
        'wig', 'wig20', 'mwig40', 'swig80', 'wig30', 'wig-ukraine'
    ]

    # FRED series patterns (economic indicators)
    FRED_PATTERNS = [
        r'^[A-Z]{2,10}$',  # Short uppercase codes like GDP, UNRATE, CPIAUCSL
        r'.*RATE.*',        # Contains RATE
        r'.*CPI.*',         # Contains CPI
        r'.*GDP.*',         # Contains GDP
    ]

    # NBP currency codes
    NBP_CURRENCIES = [
        'USD', 'EUR', 'GBP', 'CHF', 'JPY', 'CAD', 'AUD', 'SEK',
        'NOK', 'DKK', 'CZK', 'HUF', 'RON', 'BGN', 'HRK'
    ]

    def __init__(self, use_cache: bool = True, cache_hours: int = 24,
                 fred_api_key: Optional[str] = None, tiingo_api_key: Optional[str] = None,
                 financialdata_api_key: Optional[str] = None,
                 crypto_exchange: str = 'binance', use_registry: bool = True):
        """
        Initialize unified fetcher.

        Args:
            use_cache: Whether to use caching
            cache_hours: Cache validity in hours
            fred_api_key: FRED API key (optional)
            tiingo_api_key: Tiingo API key (optional, or set TIINGO_API_KEY env var)
            financialdata_api_key: FinancialData.Net API key (optional, or set FINANCIAL_DATA_API_KEY env var)
            crypto_exchange: Default crypto exchange for CCXT (default: binance)
            use_registry: Whether to use TickerRegistry for lookups
        """
        self.use_cache = use_cache
        self.cache_hours = cache_hours
        self.fred_api_key = fred_api_key
        self.tiingo_api_key = tiingo_api_key
        self.financialdata_api_key = financialdata_api_key
        self.crypto_exchange = crypto_exchange

        # Initialize TickerRegistry for ISIN/ticker lookups
        self.registry = None
        if use_registry and REGISTRY_AVAILABLE:
            try:
                self.registry = TickerRegistry()
            except Exception as e:
                print(f"[Unified] TickerRegistry unavailable: {e}")

        # Initialize available fetchers
        self.fetchers = {}

        if STOOQ_AVAILABLE:
            self.fetchers['stooq'] = StooqFetcher(use_cache, cache_hours)

        if NBP_AVAILABLE:
            self.fetchers['nbp'] = NBPFetcher(use_cache, cache_hours)

        if YAHOO_AVAILABLE:
            self.fetchers['yahoo'] = YahooFetcher(use_cache, cache_hours)

        if FRED_AVAILABLE and fred_api_key:
            try:
                self.fetchers['fred'] = FREDFetcher(fred_api_key, use_cache, cache_hours)
            except ValueError:
                print("[Unified] FRED API key not configured, FRED unavailable")

        if PDR_AVAILABLE:
            self.fetchers['pdr'] = PandasDataReaderFetcher(use_cache, cache_hours)

        # Initialize Tiingo (requires API key)
        if TIINGO_AVAILABLE:
            try:
                self.fetchers['tiingo'] = TiingoFetcher(tiingo_api_key, use_cache, cache_hours)
            except ValueError:
                print("[Unified] Tiingo API key not configured, Tiingo unavailable")

        # Initialize CCXT for crypto (no API key needed for public data)
        if CCXT_AVAILABLE:
            try:
                self.fetchers['ccxt'] = CCXTFetcher(crypto_exchange, use_cache, cache_hours)
            except Exception as e:
                print(f"[Unified] CCXT unavailable: {e}")

        # Initialize FinancialData.Net (requires API key)
        if FINANCIALDATA_AVAILABLE:
            try:
                self.fetchers['financialdata'] = FinancialDataFetcher(
                    financialdata_api_key, use_cache, cache_hours
                )
            except ValueError:
                print("[Unified] FinancialData.Net API key not configured, FinancialData unavailable")

    def fetch(self, identifier: str, start_date: Optional[str] = None,
              end_date: Optional[str] = None, source: Optional[str] = None,
              **kwargs) -> pd.DataFrame:
        """
        Fetch market data with automatic source selection.

        Supports ISINs, UIDs, and ticker symbols. Uses TickerRegistry for
        smart routing when identifier is found in security master.

        Args:
            identifier: ISIN, UID, or ticker symbol
            start_date: Start date (YYYY-MM-DD or YYYYMMDD)
            end_date: End date (YYYY-MM-DD or YYYYMMDD)
            source: Force specific source (None for auto-routing)
            **kwargs: Additional arguments passed to fetcher

        Returns:
            DataFrame with market data

        Raises:
            ValueError: If no suitable source found or data retrieval fails
        """
        # Try to resolve identifier via registry
        security = None
        if self.registry:
            security = self.registry.get_security(identifier)
            if security:
                print(f"[Unified] Found '{identifier}' in registry: {security.name} ({security.uid})")

        # If source specified, use it directly (with ticker conversion if security found)
        if source:
            ticker = identifier
            if security:
                source_ticker = security.get_ticker(source)
                if source_ticker:
                    ticker = source_ticker
            return self._fetch_from_source(source, ticker, start_date, end_date, **kwargs)

        # Auto-detect best source using registry or pattern matching
        if security:
            sources, ticker_map = self._route_security(security)
        else:
            sources = self._route_ticker(identifier)
            ticker_map = {s: identifier for s in sources}

        print(f"[Unified] Routing '{identifier}' -> {', '.join(sources)}")

        # Try sources in order with fallback
        last_error = None
        for source_name in sources:
            try:
                ticker = ticker_map.get(source_name, identifier)
                return self._fetch_from_source(source_name, ticker, start_date, end_date, **kwargs)
            except Exception as e:
                print(f"[Unified] {source_name} failed: {e}")
                last_error = e
                continue

        # All sources failed
        raise ValueError(
            f"All sources failed for '{identifier}'. Last error: {last_error}"
        )

    def _route_security(self, security) -> Tuple[List[str], dict]:
        """
        Determine best sources for a known security.

        Uses instrument type and available tickers to route.

        Args:
            security: Security object from registry

        Returns:
            Tuple of (source priority list, ticker mapping dict)
        """
        sources = []
        ticker_map = {}

        instrument_type = security.instrument_type

        # Define source priority based on instrument type and geography
        if instrument_type == 'equity':
            if security.country == 'PL':
                # Polish stocks: Stooq has best coverage, Yahoo as fallback
                priority = ['stooq', 'yahoo', 'pdr']
            else:
                # International stocks: Yahoo first
                priority = ['yahoo', 'stooq', 'pdr']

        elif instrument_type == 'index':
            if security.country == 'PL':
                priority = ['stooq', 'yahoo', 'pdr']
            else:
                priority = ['yahoo', 'stooq', 'pdr']

        elif instrument_type == 'currency':
            # FX pairs: NBP for PLN rates, Stooq for others
            if security.uid and 'PLN' in security.uid:
                priority = ['nbp', 'stooq', 'yahoo']
            else:
                priority = ['stooq', 'yahoo', 'pdr']

        else:
            # Default priority
            priority = ['yahoo', 'stooq', 'pdr']

        # Build source list and ticker map based on available tickers
        for src in priority:
            if src not in self.fetchers:
                continue

            ticker = security.get_ticker(src)
            if ticker:
                sources.append(src)
                ticker_map[src] = ticker
            elif src == 'nbp' and security.instrument_type == 'currency':
                # NBP uses currency codes, not tickers
                # Extract currency from uid like fx_USDPLN -> USD
                if security.uid and security.uid.startswith('fx_'):
                    currency = security.uid[3:6]  # First currency in pair
                    sources.append(src)
                    ticker_map[src] = currency

        # If no tickers found, fallback to ISIN or uid
        if not sources:
            sources = list(self.fetchers.keys())
            fallback = security.isin or security.uid
            ticker_map = {s: fallback for s in sources}

        return sources, ticker_map

    def _route_ticker(self, ticker: str) -> List[str]:
        """
        Determine best sources for a ticker.

        Args:
            ticker: Ticker symbol

        Returns:
            List of source names in priority order
        """
        ticker_lower = ticker.lower()
        ticker_upper = ticker.upper()

        # Check for crypto symbols first (BTC/USDT, ETHUSDT, etc.)
        if is_crypto_symbol(ticker) and 'ccxt' in self.fetchers:
            return ['ccxt']

        # Check for Polish stocks
        if ticker_lower in self.POLISH_STOCKS:
            # Stooq is best for Polish stocks, Tiingo as fallback for dividends
            sources = ['stooq', 'yahoo']
            if 'tiingo' in self.fetchers:
                sources.append('tiingo')
            sources.append('pdr')
            return sources

        # Check for Polish indices
        if ticker_lower in self.POLISH_INDICES:
            return ['stooq', 'yahoo', 'pdr']

        # Check for NBP currency request (direct 3-letter code)
        if ticker_upper in self.NBP_CURRENCIES and NBP_AVAILABLE:
            return ['nbp', 'stooq', 'yahoo']

        # Check for currency pairs (e.g., USDPLN, EURUSD)
        if re.match(r'^[A-Z]{6}$', ticker_upper):  # 6-letter currency pair
            return ['stooq', 'yahoo', 'pdr']

        # Check for FRED series
        for pattern in self.FRED_PATTERNS:
            if re.match(pattern, ticker_upper):
                if 'fred' in self.fetchers:
                    return ['fred', 'pdr']

        # Check for international indices (^SPX, ^IXIC, etc.)
        if ticker.startswith('^'):
            return ['yahoo', 'stooq', 'pdr']

        # Check for US stocks (all caps, short)
        if ticker.isupper() and 1 <= len(ticker) <= 5:
            # Tiingo is excellent for US stocks with better free tier
            sources = ['yahoo']
            if 'tiingo' in self.fetchers:
                sources.append('tiingo')
            if 'financialdata' in self.fetchers:
                sources.append('financialdata')
            sources.extend(['pdr', 'stooq'])
            return sources

        # Check for explicit market suffix (.WA, .US, etc.)
        if '.' in ticker:
            suffix = ticker.split('.')[-1].upper()
            if suffix == 'WA':  # Warsaw Stock Exchange
                return ['yahoo', 'stooq', 'pdr']
            else:
                sources = ['yahoo']
                if 'tiingo' in self.fetchers:
                    sources.append('tiingo')
                if 'financialdata' in self.fetchers:
                    sources.append('financialdata')
                sources.extend(['pdr', 'stooq'])
                return sources

        # Default fallback order (Yahoo first, Tiingo and FinancialData as backup)
        sources = ['yahoo']
        if 'tiingo' in self.fetchers:
            sources.append('tiingo')
        if 'financialdata' in self.fetchers:
            sources.append('financialdata')
        sources.extend(['stooq', 'pdr'])
        return sources

    def _fetch_from_source(self, source: str, ticker: str,
                          start_date: Optional[str] = None,
                          end_date: Optional[str] = None,
                          **kwargs) -> pd.DataFrame:
        """
        Fetch data from specific source.

        Args:
            source: Source name
            ticker: Ticker symbol
            start_date: Start date
            end_date: End date
            **kwargs: Additional arguments

        Returns:
            DataFrame with market data
        """
        if source not in self.fetchers:
            raise ValueError(f"Source '{source}' not available")

        fetcher = self.fetchers[source]

        # Handle source-specific quirks
        if source == 'nbp':
            # NBP needs table parameter
            table = kwargs.pop('table', 'A')
            return fetcher.fetch(ticker, start_date, end_date, table=table)

        elif source == 'pdr':
            # pandas-datareader needs explicit source parameter
            pdr_source = kwargs.pop('pdr_source', 'yahoo')
            return fetcher.fetch(ticker, pdr_source, start_date, end_date, **kwargs)

        elif source == 'ccxt':
            # CCXT needs timeframe parameter
            timeframe = kwargs.pop('timeframe', '1d')
            return fetcher.fetch(ticker, start_date, end_date, timeframe=timeframe, **kwargs)

        elif source == 'financialdata':
            # FinancialData.Net - supports endpoint parameter for different data types
            endpoint = kwargs.pop('fd_endpoint', 'stock-prices')
            return fetcher.fetch(ticker, start_date, end_date, endpoint=endpoint, **kwargs)

        else:
            # Standard fetchers (stooq, yahoo, fred, tiingo)
            return fetcher.fetch(ticker, start_date, end_date, **kwargs)

    def compare_sources(self, ticker: str, sources: List[str],
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> dict:
        """
        Fetch data from multiple sources for comparison.

        Args:
            ticker: Ticker symbol
            sources: List of source names to compare
            start_date: Start date
            end_date: End date

        Returns:
            Dictionary mapping source -> DataFrame
        """
        results = {}

        for source in sources:
            try:
                df = self._fetch_from_source(source, ticker, start_date, end_date)
                results[source] = df
            except Exception as e:
                print(f"[Unified] {source} failed: {e}")
                results[source] = None

        return results

    def list_available_sources(self) -> List[str]:
        """
        List currently available sources.

        Returns:
            List of source names
        """
        return list(self.fetchers.keys())


def fetch_market_data(identifier: str, start_date: Optional[str] = None,
                     end_date: Optional[str] = None,
                     source: Optional[str] = None,
                     use_cache: bool = True,
                     use_registry: bool = True,
                     fred_api_key: Optional[str] = None,
                     tiingo_api_key: Optional[str] = None,
                     financialdata_api_key: Optional[str] = None,
                     crypto_exchange: str = 'binance',
                     **kwargs) -> pd.DataFrame:
    """
    Main convenience function for fetching market data.

    Auto-routes to best source unless source specified.
    Supports ISINs, UIDs, ticker symbols, and crypto pairs.

    Args:
        identifier: ISIN, UID, ticker symbol, or crypto pair (e.g., 'BTC/USDT')
        start_date: Start date
        end_date: End date
        source: Force specific source (None for auto)
        use_cache: Whether to use caching
        use_registry: Whether to use TickerRegistry for lookups
        fred_api_key: FRED API key (optional)
        tiingo_api_key: Tiingo API key (optional, or set TIINGO_API_KEY env var)
        financialdata_api_key: FinancialData.Net API key (optional, or set FINANCIAL_DATA_API_KEY env var)
        crypto_exchange: Default crypto exchange for CCXT (default: binance)
        **kwargs: Additional arguments (e.g., timeframe='1h' for crypto, fd_endpoint for FinancialData)

    Returns:
        DataFrame with market data
    """
    fetcher = UnifiedMarketDataFetcher(
        use_cache=use_cache,
        use_registry=use_registry,
        fred_api_key=fred_api_key,
        tiingo_api_key=tiingo_api_key,
        financialdata_api_key=financialdata_api_key,
        crypto_exchange=crypto_exchange,
    )
    return fetcher.fetch(identifier, start_date, end_date, source, **kwargs)


if __name__ == '__main__':
    # Test examples
    print("Testing Unified Market Data Fetcher...\n")

    fetcher = UnifiedMarketDataFetcher()

    print(f"Available sources: {', '.join(fetcher.list_available_sources())}")
    if fetcher.registry:
        print(f"Registry loaded: {len(fetcher.registry._securities)} securities")
    print()

    # Test 1: Polish stock (should route to Stooq)
    print("1. Fetching PKO (Polish stock by ticker):")
    try:
        df = fetcher.fetch('pko', start_date='20240101', end_date='20240131')
        print(f"   Retrieved {len(df)} rows from auto-selected source")
        print(df.head(3))
    except Exception as e:
        print(f"   Error: {e}")

    # Test 2: Fetch by ISIN (should lookup in registry)
    print("\n2. Fetching XTB by ISIN (PLXTRDM00011):")
    try:
        df = fetcher.fetch('PLXTRDM00011', start_date='20240101', end_date='20240131')
        print(f"   Retrieved {len(df)} rows from auto-selected source")
        print(df.head(3))
    except Exception as e:
        print(f"   Error: {e}")

    # Test 3: Fetch by UID
    print("\n3. Fetching WIG20 by UID (idx_WIG20):")
    try:
        df = fetcher.fetch('idx_WIG20', start_date='20240101', end_date='20240131')
        print(f"   Retrieved {len(df)} rows from auto-selected source")
        print(df.head(3))
    except Exception as e:
        print(f"   Error: {e}")

    # Test 4: US stock (should route to Yahoo)
    print("\n4. Fetching AAPL (US stock):")
    try:
        df = fetcher.fetch('AAPL', start_date='20240101', end_date='20240131')
        print(f"   Retrieved {len(df)} rows from auto-selected source")
        print(df.head(3))
    except Exception as e:
        print(f"   Error: {e}")

    # Test 5: Index (should route to Yahoo or Stooq)
    print("\n5. Fetching ^GSPC (S&P 500):")
    try:
        df = fetcher.fetch('^GSPC', start_date='20240101', end_date='20240131')
        print(f"   Retrieved {len(df)} rows from auto-selected source")
        print(df.head(3))
    except Exception as e:
        print(f"   Error: {e}")

    # Test 6: Force specific source with ISIN
    print("\n6. Fetching PLXTRDM00011 from Yahoo (forced):")
    try:
        df = fetcher.fetch('PLXTRDM00011', start_date='20240101', end_date='20240131',
                          source='yahoo')
        print(f"   Retrieved {len(df)} rows")
        print(df.head(3))
    except Exception as e:
        print(f"   Error: {e}")

    # Test 7: Compare sources
    print("\n7. Comparing PKO from different sources:")
    try:
        comparison = fetcher.compare_sources('pko', ['stooq', 'yahoo'],
                                            start_date='20240115',
                                            end_date='20240119')
        for source, df in comparison.items():
            if df is not None:
                print(f"   {source}: {len(df)} rows")
            else:
                print(f"   {source}: Failed")
    except Exception as e:
        print(f"   Error: {e}")

    # Test 8: Crypto (should route to CCXT)
    print("\n8. Fetching BTC/USDT (crypto):")
    try:
        df = fetcher.fetch('BTC/USDT', start_date='20240101', end_date='20240131')
        print(f"   Retrieved {len(df)} rows from auto-selected source")
        print(df.head(3))
    except Exception as e:
        print(f"   Error: {e}")

    # Test 9: Crypto with different format
    print("\n9. Fetching ETHUSDT (crypto, no slash):")
    try:
        df = fetcher.fetch('ETHUSDT', start_date='20240101', end_date='20240115')
        print(f"   Retrieved {len(df)} rows from auto-selected source")
        print(df.head(3))
    except Exception as e:
        print(f"   Error: {e}")

    # Test 10: Tiingo (if available)
    if 'tiingo' in fetcher.fetchers:
        print("\n10. Fetching MSFT via Tiingo:")
        try:
            df = fetcher.fetch('MSFT', start_date='20240101', end_date='20240131',
                              source='tiingo')
            print(f"   Retrieved {len(df)} rows")
            print(df.head(3))
        except Exception as e:
            print(f"   Error: {e}")
    else:
        print("\n10. Tiingo not available (set TIINGO_API_KEY)")

    # Test 11: FinancialData.Net (if available)
    if 'financialdata' in fetcher.fetchers:
        print("\n11. Fetching AAPL via FinancialData.Net:")
        try:
            df = fetcher.fetch('AAPL', start_date='20240101', end_date='20240131',
                              source='financialdata')
            print(f"   Retrieved {len(df)} rows")
            print(df.head(3))
        except Exception as e:
            print(f"   Error: {e}")
    else:
        print("\n11. FinancialData.Net not available (set FINANCIAL_DATA_API_KEY)")

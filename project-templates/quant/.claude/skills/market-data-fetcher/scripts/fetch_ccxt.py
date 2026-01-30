#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pandas>=2.0",
#   "ccxt>=4.0",
# ]
# ///
"""
CCXT crypto data fetcher.

Downloads historical cryptocurrency OHLCV data from multiple exchanges
using the CCXT library (CryptoCurrency eXchange Trading Library).

Supported exchanges: Binance, Kraken, Coinbase, and 100+ more.
Free tier: Unlimited historical data, no API key required for public data.

Usage:
    uv run fetch_ccxt.py BTC/USDT 2024-01-01 2024-12-31
    uv run fetch_ccxt.py ETH/USD 2024-01-01 --exchange kraken
    uv run fetch_ccxt.py  # Run self-tests
"""

import pandas as pd
from typing import Optional, List, Literal
from datetime import datetime, timedelta

try:
    import ccxt
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False
    print("[CCXT] Warning: ccxt not installed. Run: pip install ccxt")

from utils import (
    get_cache_manager,
    get_rate_limiter,
    normalize_date,
    normalize_date_display,
    create_identifier,
    handle_api_error
)


# Common exchange aliases
EXCHANGE_ALIASES = {
    'binance': 'binance',
    'kraken': 'kraken',
    'coinbase': 'coinbasepro',
    'coinbasepro': 'coinbasepro',
    'kucoin': 'kucoin',
    'bybit': 'bybit',
    'okx': 'okx',
    'okex': 'okx',
    'bitfinex': 'bitfinex',
    'huobi': 'huobi',
    'gate': 'gateio',
    'gateio': 'gateio',
}

# Timeframe mapping
TIMEFRAME_MAP = {
    '1m': '1m',
    '5m': '5m',
    '15m': '15m',
    '30m': '30m',
    '1h': '1h',
    '4h': '4h',
    '1d': '1d',
    'd': '1d',
    'daily': '1d',
    '1w': '1w',
    'w': '1w',
    'weekly': '1w',
}


class CCXTFetcher:
    """Fetcher for cryptocurrency data via CCXT."""

    def __init__(self, exchange: str = 'binance', use_cache: bool = True,
                 cache_hours: int = 24):
        """
        Initialize CCXT fetcher.

        Args:
            exchange: Exchange name (binance, kraken, coinbase, etc.)
            use_cache: Whether to use caching
            cache_hours: Cache validity in hours
        """
        if not CCXT_AVAILABLE:
            raise ImportError("ccxt package not available. Install with: pip install ccxt")

        # Resolve exchange alias
        exchange_id = EXCHANGE_ALIASES.get(exchange.lower(), exchange.lower())

        if not hasattr(ccxt, exchange_id):
            raise ValueError(f"Exchange not supported: {exchange}")

        self.exchange_id = exchange_id
        self.exchange = getattr(ccxt, exchange_id)({
            'enableRateLimit': True,  # Built-in rate limiting
        })

        self.use_cache = use_cache
        self.cache_hours = cache_hours
        self.cache = get_cache_manager()
        self.rate_limiter = get_rate_limiter()

    def fetch(self, symbol: str, start_date: Optional[str] = None,
              end_date: Optional[str] = None, timeframe: str = '1d',
              limit: int = 1000) -> pd.DataFrame:
        """
        Fetch OHLCV data from exchange.

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT', 'ETH/USD', 'BTC/EUR')
            start_date: Start date (YYYY-MM-DD or YYYYMMDD)
            end_date: End date (YYYY-MM-DD or YYYYMMDD)
            timeframe: Candle timeframe ('1m', '5m', '1h', '1d', '1w')
            limit: Max candles per request (exchange dependent)

        Returns:
            DataFrame with columns: Date, Open, High, Low, Close, Volume

        Raises:
            ValueError: If symbol invalid or no data returned
        """
        # Normalize symbol format
        symbol = self._normalize_symbol(symbol)
        timeframe = TIMEFRAME_MAP.get(timeframe, timeframe)

        # Verify symbol exists on exchange
        if not self.exchange.has['fetchOHLCV']:
            raise ValueError(f"Exchange {self.exchange_id} doesn't support OHLCV data")

        # Create cache identifier
        start_norm = normalize_date(start_date) if start_date else None
        end_norm = normalize_date(end_date) if end_date else None
        cache_id = create_identifier(
            f"{self.exchange_id}_{symbol.replace('/', '_')}",
            start_norm, end_norm, timeframe
        )

        # Try cache first
        if self.use_cache:
            cached = self.cache.get('ccxt', cache_id, max_age_hours=self.cache_hours)
            if cached is not None:
                print(f"[CCXT] Using cached data for {symbol} from {self.exchange_id}")
                return cached

        try:
            # Convert dates to timestamps
            since = None
            if start_date:
                start_dt = pd.Timestamp(normalize_date_display(start_date))
                since = int(start_dt.timestamp() * 1000)

            end_ts = None
            if end_date:
                end_dt = pd.Timestamp(normalize_date_display(end_date))
                end_ts = int(end_dt.timestamp() * 1000)

            # Fetch data in batches (some exchanges have limits)
            all_ohlcv = []
            current_since = since

            print(f"[CCXT] Fetching {symbol} from {self.exchange_id} ({timeframe})")

            while True:
                self.rate_limiter.wait('ccxt')

                ohlcv = self.exchange.fetch_ohlcv(
                    symbol,
                    timeframe=timeframe,
                    since=current_since,
                    limit=limit
                )

                if not ohlcv:
                    break

                all_ohlcv.extend(ohlcv)

                # Check if we've reached the end date
                last_timestamp = ohlcv[-1][0]
                if end_ts and last_timestamp >= end_ts:
                    break

                # Check if we got fewer than requested (end of data)
                if len(ohlcv) < limit:
                    break

                # Move to next batch
                current_since = last_timestamp + 1

                # Safety limit to prevent infinite loops
                if len(all_ohlcv) > 100000:
                    print(f"[CCXT] Warning: Reached 100k candles limit")
                    break

            if not all_ohlcv:
                raise ValueError(f"No data returned for {symbol}")

            # Convert to DataFrame
            df = pd.DataFrame(all_ohlcv, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])

            # Convert timestamp to datetime
            df['Date'] = pd.to_datetime(df['Timestamp'], unit='ms')
            df.drop('Timestamp', axis=1, inplace=True)

            # Filter by end date if specified
            if end_date:
                end_dt = pd.Timestamp(normalize_date_display(end_date))
                df = df[df['Date'] <= end_dt]

            # Reorder columns
            df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]

            # Sort and deduplicate
            df.sort_values('Date', inplace=True)
            df.drop_duplicates(subset=['Date'], keep='last', inplace=True)
            df.reset_index(drop=True, inplace=True)

            print(f"[CCXT] Retrieved {len(df)} candles")

            # Cache result
            if self.use_cache:
                self.cache.set('ccxt', cache_id, df)

            return df

        except Exception as e:
            handle_api_error('CCXT', e, symbol)
            raise

    def _normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol format for CCXT.

        Args:
            symbol: Raw symbol

        Returns:
            Normalized symbol (e.g., 'BTC/USDT')
        """
        symbol = symbol.upper()

        # Already in correct format
        if '/' in symbol:
            return symbol

        # Common patterns without slash
        # BTCUSDT -> BTC/USDT
        # ETHBTC -> ETH/BTC
        quote_currencies = ['USDT', 'USD', 'EUR', 'GBP', 'BTC', 'ETH', 'USDC', 'BUSD', 'PLN']

        for quote in quote_currencies:
            if symbol.endswith(quote):
                base = symbol[:-len(quote)]
                if base:
                    return f"{base}/{quote}"

        # If no pattern matched, return as-is
        return symbol

    def list_symbols(self) -> List[str]:
        """
        List available trading pairs on the exchange.

        Returns:
            List of symbol strings
        """
        self.exchange.load_markets()
        return list(self.exchange.symbols)

    @staticmethod
    def list_exchanges() -> List[str]:
        """
        List supported exchanges.

        Returns:
            List of exchange IDs
        """
        if CCXT_AVAILABLE:
            return ccxt.exchanges
        return []

    def get_ticker_info(self, symbol: str) -> dict:
        """
        Get current ticker info (price, volume, etc.).

        Args:
            symbol: Trading pair

        Returns:
            Dictionary with ticker info
        """
        symbol = self._normalize_symbol(symbol)
        try:
            self.rate_limiter.wait('ccxt')
            return self.exchange.fetch_ticker(symbol)
        except Exception as e:
            handle_api_error('CCXT', e, symbol)
            return {}


def fetch_crypto(symbol: str, start_date: Optional[str] = None,
                end_date: Optional[str] = None, exchange: str = 'binance',
                timeframe: str = '1d', use_cache: bool = True) -> pd.DataFrame:
    """
    Convenience function to fetch crypto data.

    Args:
        symbol: Trading pair (e.g., 'BTC/USDT', 'ETHUSDT', 'ETH/USD')
        start_date: Start date
        end_date: End date
        exchange: Exchange name (binance, kraken, coinbase, etc.)
        timeframe: Candle timeframe ('1m', '1h', '1d', '1w')
        use_cache: Whether to use caching

    Returns:
        DataFrame with OHLCV data
    """
    fetcher = CCXTFetcher(exchange=exchange, use_cache=use_cache)
    return fetcher.fetch(symbol, start_date, end_date, timeframe)


def is_crypto_symbol(symbol: str) -> bool:
    """
    Check if a symbol looks like a crypto trading pair.

    Used by unified fetcher for routing.

    Args:
        symbol: Symbol to check

    Returns:
        True if likely a crypto symbol
    """
    symbol_upper = symbol.upper()

    # Contains slash (BTC/USDT)
    if '/' in symbol:
        return True

    # Ends with common crypto quote currencies
    crypto_quotes = ['USDT', 'USD', 'USDC', 'BUSD', 'BTC', 'ETH']
    for quote in crypto_quotes:
        if symbol_upper.endswith(quote) and len(symbol_upper) > len(quote):
            # Check if base is a known crypto
            base = symbol_upper[:-len(quote)]
            known_cryptos = ['BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOGE', 'DOT', 'AVAX',
                           'LINK', 'MATIC', 'UNI', 'LTC', 'ATOM', 'NEAR', 'FIL']
            if base in known_cryptos:
                return True

    return False


if __name__ == '__main__':
    # Test examples
    if not CCXT_AVAILABLE:
        print("ccxt not available. Install with: pip install ccxt")
    else:
        print("Testing CCXT fetcher...")

        # Test 1: Bitcoin from Binance
        print("\n1. Fetching BTC/USDT from Binance (daily):")
        try:
            df = fetch_crypto('BTC/USDT', start_date='20240101', end_date='20240131')
            print(f"   Retrieved {len(df)} rows")
            print(df.head())
        except Exception as e:
            print(f"   Error: {e}")

        # Test 2: Ethereum from Binance (hourly)
        print("\n2. Fetching ETH/USDT from Binance (hourly, last 24h):")
        try:
            start = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
            df = fetch_crypto('ETH/USDT', start_date=start, timeframe='1h')
            print(f"   Retrieved {len(df)} rows")
            print(df.tail())
        except Exception as e:
            print(f"   Error: {e}")

        # Test 3: Symbol detection
        print("\n3. Testing crypto symbol detection:")
        test_symbols = ['BTC/USDT', 'ETHUSDT', 'AAPL', 'pko', 'SOLUSD', 'EUR/USD']
        for sym in test_symbols:
            is_crypto = is_crypto_symbol(sym)
            print(f"   {sym}: {'crypto' if is_crypto else 'not crypto'}")

        # Test 4: Symbol normalization
        print("\n4. Testing symbol normalization:")
        fetcher = CCXTFetcher('binance')
        test_symbols = ['BTCUSDT', 'ETH/USD', 'btcusd', 'SOLETH']
        for sym in test_symbols:
            normalized = fetcher._normalize_symbol(sym)
            print(f"   {sym} -> {normalized}")

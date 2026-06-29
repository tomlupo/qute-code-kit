# Usage Patterns

Complete code examples for all data fetching patterns.

## Pattern 1: Simple Data Fetch (Auto-Routing)

```python
from fetch_unified import fetch_market_data

df = fetch_market_data('pko', start_date='2024-01-01')        # Polish stock → Stooq
df = fetch_market_data('AAPL', start_date='2024-01-01')       # US stock → Yahoo (Tiingo fallback)
df = fetch_market_data('USD', start_date='2024-01-01')        # Currency → Stooq or NBP
df = fetch_market_data('BTC/USDT', start_date='2024-01-01')   # Crypto → CCXT/Binance
df = fetch_market_data('GDP', start_date='2020-01-01')        # Macro → FRED
```

## Pattern 2: Force Specific Source

```python
df = fetch_market_data('pko', source='stooq', start_date='2024-01-01')
df = fetch_market_data('PKO.WA', source='yahoo', start_date='2024-01-01')
df = fetch_market_data('USD', source='nbp', table='A', start_date='2024-01-01')
df = fetch_market_data('MSFT', source='tiingo', start_date='2024-01-01')
df = fetch_market_data('BTC/USDT', source='ccxt', timeframe='1h')
df = fetch_market_data('ETH/USD', source='ccxt', crypto_exchange='kraken')
```

## Pattern 3: Multi-Source Comparison

```python
from fetch_unified import UnifiedMarketDataFetcher

fetcher = UnifiedMarketDataFetcher()
comparison = fetcher.compare_sources(
    ticker='pko', sources=['stooq', 'yahoo'],
    start_date='2024-01-01', end_date='2024-01-31'
)

for source, df in comparison.items():
    if df is not None:
        print(f"{source}: {len(df)} rows, avg close: {df['Close'].mean():.2f}")
```

## Pattern 4: Direct Source Usage

```python
from fetch_stooq import fetch_stooq
df = fetch_stooq('pko', start_date='20240101', end_date='20241231', interval='d')

from fetch_nbp import fetch_nbp
df = fetch_nbp('USD', start_date='20240101', table='A')

from fetch_yahoo import fetch_yahoo
df = fetch_yahoo('AAPL', start_date='2024-01-01', interval='1d')

from fetch_fred import fetch_fred
df = fetch_fred('GDP', start_date='2020-01-01', api_key='your_key')
```

## Pattern 5: Fetch by ISIN (Yahoo Direct API)

```python
from fetch_yahoo_direct import fetch_by_isin, YahooDirectFetcher

# Multiple ISINs - returns prices, dividends, splits, and mapping
isins = ['PLXTRDM00011', 'US0378331005']  # XTB, Apple
prices, dividends, splits, mapping = fetch_by_isin(
    isins, start_date='2024-01-01', end_date='2025-01-01'
)

# Access by ISIN
xtb_prices = prices['PLXTRDM00011']

# Single ticker with direct API (bypasses yfinance rate limiting)
fetcher = YahooDirectFetcher()
prices_df, divs_df, splits_df = fetcher.fetch('XTB.WA', '2024-01-01', '2025-01-01')

# ISIN to ticker lookup
ticker = fetcher.isin_to_ticker('PLXTRDM00011')  # Returns 'XTB.WA'
```

## Pattern 6: Save ISIN Data to Files

```python
from fetch_yahoo_direct import save_isin_data

save_isin_data(
    ['PLXTRDM00011', 'PLCCC0000016', 'PLBSK0000017'],
    output_dir='data/prices/yfinance',
    start_date='2024-11-01', end_date='2026-01-08'
)
# Creates: prices.xlsx, dividends.xlsx, splits.xlsx, isin_ticker_mapping.xlsx
```

## Pattern 7: TickerRegistry for ISIN/Ticker Conversion

```python
from ticker_registry import TickerRegistry, isin_to_yahoo, isin_to_stooq

registry = TickerRegistry()

# Lookup by any identifier
security = registry.get_security('PLXTRDM00011')      # By ISIN
security = registry.get_security('XTB.WA')             # By Yahoo ticker

# Access properties
print(security.name)                    # 'XTB'
print(security.isin)                    # 'PLXTRDM00011'
print(security.get_ticker('yahoo'))     # 'XTB.WA'
print(security.get_ticker('stooq'))     # 'xtb'

# Convert between formats
yahoo = registry.convert_ticker('PLXTRDM00011', to_source='yahoo')   # 'XTB.WA'
stooq = registry.convert_ticker('XTB.WA', to_source='stooq')         # 'xtb'

# Convenience functions
yahoo = isin_to_yahoo('PLXTRDM00011')   # 'XTB.WA'
stooq = isin_to_stooq('PLXTRDM00011')   # 'xtb'
```

## Pattern 8: Fetch by ISIN with Unified Fetcher

```python
from fetch_unified import fetch_market_data

df = fetch_market_data('PLXTRDM00011', start_date='2024-01-01')           # Auto-resolve
df = fetch_market_data('idx_WIG20', start_date='2024-01-01')              # By uid
df = fetch_market_data('PLXTRDM00011', source='yahoo', start_date='2024-01-01')  # Force source
```

## Pattern 9: Auto-Discover Missing Yahoo Tickers

```python
from ticker_registry import TickerRegistry

registry = TickerRegistry()
discovered = registry.discover_missing_yahoo_tickers(['US0378331005', 'GB0002634946'])
# {'US0378331005': 'AAPL', 'GB0002634946': 'BA.L'}

all_discovered = registry.discover_missing_yahoo_tickers()  # All missing
```

## Pattern 10: Adding New Securities to Registry

```python
from ticker_registry import TickerRegistry, Security
from datetime import datetime

registry = TickerRegistry()

security = Security(
    uid='isin_GB0002634946', isin='GB0002634946', name='BAE Systems',
    instrument_type='equity', country='GB', exchange='LSE',
    tickers={'yahoo': 'BA.L', 'stooq': 'ba.uk'},
    mapping_source='manual', last_updated=datetime.now()
)
registry.register_security(security)
registry.add_ticker_mapping('PLXTRDM00011', 'bloomberg', 'XTB PW Equity')
registry.save()
```

## Date Format Handling

All fetchers accept flexible date formats:
- `'2024-01-01'` (YYYY-MM-DD)
- `'20240101'` (YYYYMMDD)
- `datetime` / `date` / `pd.Timestamp` objects

## Troubleshooting

### "No module named 'yfinance'"
```bash
pip install yfinance
```

### "FRED API key required"
```bash
export FRED_API_KEY="your_key"
```

### "No data available for ticker"
1. Check ticker format (see ticker_formats.md)
2. Try different source
3. Verify date range is valid

### Slow Performance
1. Enable caching (default)
2. Reduce date range
3. Batch requests with fetcher instance

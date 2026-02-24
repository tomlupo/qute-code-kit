---
name: market-data-fetcher
description: Fetch market data from multiple sources (Stooq, NBP, Yahoo Finance, FRED, FinancialData.Net, pandas-datareader) with intelligent routing. Best for ad-hoc data queries, multi-source comparisons, and historical data downloads. Use when users request stock prices, indices, FX rates, economic indicators, fundamentals, options, or financial statements.
argument-hint: "[ticker] [start-date] [end-date]"
allowed-tools: Bash, Read
---

# Market Data Fetcher Skill

Unified market data fetching with intelligent source selection and fallback logic.

## Purpose

Provide seamless access to market data from multiple sources through a single interface. Automatically routes requests to the best data source based on ticker pattern, asset type, and geographic market.

## When to Use This Skill

Use this skill when users request:
- Historical stock prices (Polish or international)
- Index data (WIG20, S&P 500, etc.)
- Exchange rates (official PLN rates or market rates)
- Economic indicators (GDP, inflation, unemployment)
- **Cryptocurrency data (BTC, ETH, altcoins)**
- Multi-source data comparison
- Ad-hoc market data queries

## Supported Data Sources

1. **Stooq** (stooq.pl)
   - Polish stocks, indices, international securities
   - Free, no authentication required
   - Best for: Polish market data
   - **Dividend treatment**: Adjusted prices only (historical prices adjusted for dividends)

2. **NBP API** (api.nbp.pl)
   - Official Polish National Bank exchange rates
   - Free, no authentication required
   - Best for: Official PLN FX rates

3. **Yahoo Finance** (via yfinance or direct API)
   - Global stocks, ETFs, indices
   - Free, no authentication required
   - Best for: US stocks, international equities
   - **Direct API**: Bypasses yfinance rate limiting, supports ISIN lookup
   - **Corporate actions**: Dividends and splits via `events=div,splits`
   - **Dividend treatment**: Both raw (`close`) and adjusted (`adj_close`) prices

4. **Tiingo** (api.tiingo.com) - **NEW**
   - US stocks, ETFs, 86,000+ securities
   - Requires free API key (1000 req/day)
   - Best for: Yahoo Finance fallback, 30+ years history
   - **Dividend treatment**: Both raw and adjusted prices

5. **CCXT/Binance** (Cryptocurrency) - **NEW**
   - All crypto pairs (BTC, ETH, altcoins)
   - Free, no API key required
   - Best for: Cryptocurrency analysis
   - **Timeframes**: 1m, 5m, 1h, 4h, 1d, 1w
   - **Exchanges**: Binance (default), Kraken, Coinbase, 100+ more

6. **FRED** (fred.stlouisfed.org)
   - US economic indicators from Federal Reserve
   - Requires free API key
   - Best for: Macroeconomic data

7. **FinancialData.Net** (financialdata.net) - **NEW**
   - US/international stocks, ETFs, commodities, crypto, forex
   - Options, futures, financial statements, ratios, insider trading
   - Requires API key (free tier available)
   - Best for: Fundamentals, options data, institutional/insider data
   - **Endpoints**: 50+ covering prices, statements, ratios, calendars
   - **MCP server**: Available for direct AI agent integration

8. **pandas-datareader**
   - Meta-source accessing multiple providers
   - Useful fallback
   - Best for: When primary sources fail

### Dividend Treatment Summary

| Source | Price Type | Use For |
|--------|------------|---------|
| Stooq | Adjusted only | Total return calculations |
| Yahoo Finance | Both (close + adj_close) | P&L (close), returns (adj_close) |

**Key insight**: Stooq `Close` = Yahoo `adj_close` (validated 95.8% match rate)

See `references/dividend_treatment.md` for detailed documentation.

## Core Workflow

### Step 1: Determine if Skill Applies

Ask: Does the user need to fetch market data?

Examples of applicable requests:
- "Get PKO stock prices for 2024"
- "Download WIG20 index data"
- "Fetch USD/PLN exchange rates"
- "Get S&P 500 historical data"
- "Compare Apple stock from different sources"

### Step 2: Use the Unified Fetcher

The primary entry point is `scripts/fetch_unified.py`, which provides intelligent routing.

**CLI usage (with uv run)**:
```bash
# All scripts are self-contained with PEP 723 inline dependencies
uv run scripts/fetch_unified.py PKO 2024-01-01 2024-12-31
uv run scripts/fetch_stooq.py WIG20 2024-01-01
uv run scripts/fetch_nbp.py USD 2024-01-01 2024-12-31
uv run scripts/fetch_yahoo.py AAPL 2024-01-01
uv run scripts/fetch_financialdata.py AAPL 2024-01-01 2024-12-31
```

**Python module usage**:
```python
import sys
sys.path.append('market-data-fetcher/scripts')

from fetch_unified import fetch_market_data

# Auto-routing (recommended)
df = fetch_market_data('pko', start_date='2024-01-01', end_date='2024-12-31')
```

**The unified fetcher will**:
1. Analyze ticker pattern
2. Select best source automatically
3. Try fallback sources if primary fails
4. Return standardized DataFrame

### Step 3: Handle Results

All fetchers return pandas DataFrames with standardized columns:
- `Date` - Date (datetime)
- `Open` - Opening price
- `High` - Highest price
- `Low` - Lowest price
- `Close` - Closing price
- `Volume` - Trading volume (if available)
- `Adj_Close` - Adjusted close (Yahoo only)

For economic data (FRED, NBP):
- `Date` - Date
- `Value` - Indicator value
- `Currency` or `Series_ID` - Identifier

## Usage Patterns

### Pattern 1: Simple Data Fetch (Auto-Routing)

Use for most queries - let the skill choose the best source:

```python
from fetch_unified import fetch_market_data

# Polish stock - routes to Stooq
df = fetch_market_data('pko', start_date='2024-01-01')

# US stock - routes to Yahoo (Tiingo fallback)
df = fetch_market_data('AAPL', start_date='2024-01-01')

# Currency - routes to Stooq or NBP
df = fetch_market_data('USD', start_date='2024-01-01')

# Cryptocurrency - routes to CCXT/Binance
df = fetch_market_data('BTC/USDT', start_date='2024-01-01')
df = fetch_market_data('ETHUSDT', start_date='2024-01-01')  # Also works

# Economic indicator - routes to FRED (if API key available)
df = fetch_market_data('GDP', start_date='2020-01-01')
```

### Pattern 2: Force Specific Source

Use when user explicitly requests a source or auto-routing fails:

```python
# Force Stooq
df = fetch_market_data('pko', source='stooq', start_date='2024-01-01')

# Force Yahoo
df = fetch_market_data('PKO.WA', source='yahoo', start_date='2024-01-01')

# Force NBP for official rates
df = fetch_market_data('USD', source='nbp', table='A', start_date='2024-01-01')

# Force Tiingo (requires TIINGO_API_KEY env var)
df = fetch_market_data('MSFT', source='tiingo', start_date='2024-01-01')

# Force CCXT with different exchange or timeframe
df = fetch_market_data('BTC/USDT', source='ccxt', timeframe='1h')  # Hourly
df = fetch_market_data('ETH/USD', source='ccxt', crypto_exchange='kraken')
```

### Pattern 3: Multi-Source Comparison

Use when user wants to compare data across sources:

```python
from fetch_unified import UnifiedMarketDataFetcher

fetcher = UnifiedMarketDataFetcher()

# Compare PKO from Stooq and Yahoo
comparison = fetcher.compare_sources(
    ticker='pko',
    sources=['stooq', 'yahoo'],
    start_date='2024-01-01',
    end_date='2024-01-31'
)

for source, df in comparison.items():
    if df is not None:
        print(f"{source}: {len(df)} rows, avg close: {df['Close'].mean():.2f}")
```

### Pattern 4: Direct Source Usage

Use individual fetchers when you know exactly which source is needed:

```python
# Stooq directly
from fetch_stooq import fetch_stooq
df = fetch_stooq('pko', start_date='20240101', end_date='20241231', interval='d')

# NBP directly
from fetch_nbp import fetch_nbp
df = fetch_nbp('USD', start_date='20240101', table='A')

# Yahoo directly
from fetch_yahoo import fetch_yahoo
df = fetch_yahoo('AAPL', start_date='2024-01-01', interval='1d')

# FRED directly
from fetch_fred import fetch_fred
df = fetch_fred('GDP', start_date='2020-01-01', api_key='your_key')
```

### Pattern 5: Fetch by ISIN (Yahoo Direct API)

Use when you have ISINs instead of tickers - automatically converts ISIN to Yahoo ticker:

```python
from fetch_yahoo_direct import fetch_by_isin, YahooDirectFetcher

# Multiple ISINs - returns prices, dividends, splits, and mapping
isins = ['PLXTRDM00011', 'US0378331005']  # XTB, Apple
prices, dividends, splits, mapping = fetch_by_isin(
    isins,
    start_date='2024-01-01',
    end_date='2025-01-01'
)

# Access by ISIN
xtb_prices = prices['PLXTRDM00011']
xtb_divs = dividends.get('PLXTRDM00011', pd.DataFrame())

# Single ticker with direct API (bypasses yfinance rate limiting)
fetcher = YahooDirectFetcher()
prices_df, divs_df, splits_df = fetcher.fetch('XTB.WA', '2024-01-01', '2025-01-01')

# ISIN to ticker lookup
ticker = fetcher.isin_to_ticker('PLXTRDM00011')  # Returns 'XTB.WA'
```

### Pattern 6: Save ISIN Data to Files

Fetch and save data for multiple ISINs to Excel files:

```python
from fetch_yahoo_direct import save_isin_data

isins = ['PLXTRDM00011', 'PLCCC0000016', 'PLBSK0000017']

save_isin_data(
    isins,
    output_dir='data/prices/yfinance',
    start_date='2024-11-01',
    end_date='2026-01-08'
)

# Creates:
#   data/prices/yfinance/prices.xlsx
#   data/prices/yfinance/dividends.xlsx
#   data/prices/yfinance/splits.xlsx (if any)
#   data/prices/yfinance/isin_ticker_mapping.xlsx
```

### Pattern 7: Using TickerRegistry for ISIN/Ticker Conversion

The TickerRegistry provides a unified lookup system for converting between identifiers across data sources:

```python
from ticker_registry import TickerRegistry, convert_ticker, isin_to_yahoo, isin_to_stooq

# Initialize registry (loads from security_master.csv)
registry = TickerRegistry()

# Lookup by any identifier (uid, ISIN, or ticker)
security = registry.get_security('PLXTRDM00011')      # By ISIN
security = registry.get_security('isin_PLXTRDM00011') # By uid
security = registry.get_security('XTB.WA')            # By Yahoo ticker
security = registry.get_security('xtb')               # By Stooq ticker

# Access security properties
print(security.name)                    # 'XTB'
print(security.isin)                    # 'PLXTRDM00011'
print(security.get_ticker('yahoo'))     # 'XTB.WA'
print(security.get_ticker('stooq'))     # 'xtb'

# Convert between ticker formats
yahoo_ticker = registry.convert_ticker('PLXTRDM00011', to_source='yahoo')   # 'XTB.WA'
stooq_ticker = registry.convert_ticker('XTB.WA', to_source='stooq')         # 'xtb'

# Convenience functions (use default registry)
yahoo = isin_to_yahoo('PLXTRDM00011')   # 'XTB.WA'
stooq = isin_to_stooq('PLXTRDM00011')   # 'xtb'
```

### Pattern 8: Fetch by ISIN with Unified Fetcher

The unified fetcher integrates with TickerRegistry for ISIN-based lookups:

```python
from fetch_unified import fetch_market_data

# Fetch by ISIN - auto-resolves to correct ticker for best source
df = fetch_market_data('PLXTRDM00011', start_date='2024-01-01')

# Fetch by uid
df = fetch_market_data('idx_WIG20', start_date='2024-01-01')

# Force specific source with ISIN - converts to source-specific ticker
df = fetch_market_data('PLXTRDM00011', source='yahoo', start_date='2024-01-01')
```

### Pattern 9: Auto-Discover Missing Yahoo Tickers

Discover Yahoo tickers for ISINs not yet in the registry:

```python
from ticker_registry import TickerRegistry

registry = TickerRegistry()

# Discover Yahoo tickers for specific ISINs
discovered = registry.discover_missing_yahoo_tickers(['US0378331005', 'GB0002634946'])
# {'US0378331005': 'AAPL', 'GB0002634946': 'BA.L'}

# Discover for all ISINs in registry that are missing Yahoo tickers
all_discovered = registry.discover_missing_yahoo_tickers()
```

### Pattern 10: Adding New Securities to Registry

Register new securities manually or via auto-discovery:

```python
from ticker_registry import TickerRegistry, Security
from datetime import datetime

registry = TickerRegistry()

# Add manually
security = Security(
    uid='isin_GB0002634946',
    isin='GB0002634946',
    name='BAE Systems',
    instrument_type='equity',
    country='GB',
    exchange='LSE',
    tickers={'yahoo': 'BA.L', 'stooq': 'ba.uk'},
    mapping_source='manual',
    last_updated=datetime.now()
)
registry.register_security(security)

# Add ticker mapping to existing security
registry.add_ticker_mapping('PLXTRDM00011', 'bloomberg', 'XTB PW Equity')

# Save registry to CSV
registry.save()
```

### Pattern 11: FinancialData.Net (Prices, Fundamentals, Options)

Use for stock prices, company fundamentals, financial statements, options data, and institutional/insider trading:

```python
from fetch_financialdata import FinancialDataFetcher, fetch_financialdata

# Stock prices (Free tier)
df = fetch_financialdata('AAPL', start_date='2024-01-01', end_date='2024-12-31')

# Company information (Standard tier)
df = fetch_financialdata('MSFT', endpoint='company-information')

# Income statements
df = fetch_financialdata('AAPL', endpoint='income-statements', period='year')

# Balance sheet
df = fetch_financialdata('AAPL', endpoint='balance-sheet-statements', period='quarter')

# Financial ratios
df = fetch_financialdata('AAPL', endpoint='profitability-ratios')

# Option chain
df = fetch_financialdata('AAPL', endpoint='option-chain')

# Crypto prices
df = fetch_financialdata('BTC', endpoint='crypto-prices')

# Forex prices
df = fetch_financialdata('EURUSD', endpoint='forex-prices')

# Insider transactions
df = fetch_financialdata('AAPL', endpoint='insider-transactions')

# Senate/House trading
fetcher = FinancialDataFetcher()
df = fetcher.get_senate_trading()

# Via unified fetcher (auto-routing includes FinancialData as fallback)
from fetch_unified import fetch_market_data
df = fetch_market_data('AAPL', source='financialdata', start_date='2024-01-01')

# Access fundamentals via unified fetcher
df = fetch_market_data('AAPL', source='financialdata', fd_endpoint='income-statements')
```

## Date Format Handling

All fetchers accept flexible date formats:
- `'2024-01-01'` (YYYY-MM-DD)
- `'20240101'` (YYYYMMDD)
- `datetime` objects
- `date` objects
- `pd.Timestamp` objects

Dates are automatically normalized internally.

## Ticker Format Reference

Refer to `references/ticker_formats.md` for comprehensive ticker formats, but here are quick examples:

**Stooq**:
- Polish stocks: `pko`, `cdr`, `pzu` (lowercase)
- Indices: `wig20`, `mwig40` (lowercase)
- Currency pairs: `usdpln`, `eurusd` (6-letter)

**Yahoo Finance**:
- US stocks: `AAPL`, `MSFT`, `GOOGL` (uppercase)
- Polish stocks: `PKO.WA`, `CDR.WA` (uppercase + .WA)
- Indices: `^GSPC`, `^IXIC` (caret prefix)

**NBP**:
- Currency codes: `USD`, `EUR`, `GBP` (3-letter uppercase)

**FRED**:
- Series IDs: `GDP`, `UNRATE`, `CPIAUCSL` (exact ID)

## Caching

All fetchers use file-based caching by default:
- **Location**: `data/cache/market_data/{source}/`
- **Default TTL**: 24 hours
- **Format**: CSV for price data, JSON for other data

**Cache benefits**:
- Faster repeated queries
- Reduces API load
- Enables offline work

**Control caching**:
```python
# Disable cache
df = fetch_market_data('pko', use_cache=False)

# Custom cache duration
fetcher = UnifiedMarketDataFetcher(cache_hours=48)
```

## Error Handling

The skill includes comprehensive error handling with informative messages:

```python
try:
    df = fetch_market_data('INVALID_TICKER')
except ValueError as e:
    print(f"Invalid ticker or no data: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

**Common errors**:
- `ValueError`: Invalid ticker, no data found, date range issues
- `requests.RequestException`: Network errors
- `ImportError`: Required package not installed

## Configuration

### FRED API Key (Optional)

FRED requires a free API key. Configure via:

1. **Environment variable** (recommended):
   ```bash
   export FRED_API_KEY="your_api_key"
   ```

2. **Config file**: Create `config/fred_api_key.txt` with your key

3. **Direct parameter**:
   ```python
   fetcher = UnifiedMarketDataFetcher(fred_api_key='your_key')
   ```

Get API key at: https://fred.stlouisfed.org/docs/api/api_key.html

See `references/api_setup.md` for detailed setup instructions.

### Package Dependencies

Required:
```bash
pip install pandas requests
```

Optional (enables specific sources):
```bash
pip install yfinance pandas-datareader
```

## Reference Documentation

Load these files when needed for detailed information:

- **`references/sources_overview.md`**: Comprehensive source comparison, when to use each source, coverage details
- **`references/ticker_formats.md`**: Complete ticker format reference for all sources, cross-source mappings
- **`references/api_setup.md`**: Detailed API key setup, troubleshooting, configuration options
- **`references/dividend_treatment.md`**: How sources handle dividend adjustments, raw vs adjusted prices, validation results
- **`references/security_master.md`**: Security master schema, UID conventions, TickerRegistry API documentation

Suggest loading these files when:
- User asks about source capabilities
- Ticker format questions arise
- Setup or configuration issues occur
- User wants to understand source selection
- Questions about dividend adjustments or price types (raw vs adjusted)
- Comparing data between Stooq and Yahoo Finance
- Need to understand total return vs P&L calculations
- Need to convert between ISINs and tickers, or between ticker formats
- Working with security master data or TickerRegistry

## Example Queries

### Query 1: "Get PKO stock prices for 2024"

```python
from fetch_unified import fetch_market_data

df = fetch_market_data('pko', start_date='2024-01-01', end_date='2024-12-31')

print(f"Retrieved {len(df)} trading days")
print(f"Date range: {df['Date'].min()} to {df['Date'].max()}")
print(f"Average closing price: {df['Close'].mean():.2f} PLN")
print(f"Min: {df['Close'].min():.2f}, Max: {df['Close'].max():.2f}")

# Display first and last few rows
print("\nFirst 5 days:")
print(df.head())
print("\nLast 5 days:")
print(df.tail())
```

### Query 2: "Compare WIG20 from Stooq and Yahoo"

```python
from fetch_unified import UnifiedMarketDataFetcher

fetcher = UnifiedMarketDataFetcher()

comparison = fetcher.compare_sources(
    ticker='wig20',
    sources=['stooq', 'yahoo'],
    start_date='2024-01-01',
    end_date='2024-01-31'
)

# Compare close prices
for source, df in comparison.items():
    if df is not None:
        print(f"\n{source.upper()}:")
        print(f"  Rows: {len(df)}")
        print(f"  Avg Close: {df['Close'].mean():.2f}")
        print(f"  Date range: {df['Date'].min()} to {df['Date'].max()}")
    else:
        print(f"\n{source.upper()}: Failed to fetch")
```

### Query 3: "Get official USD/PLN rates from NBP"

```python
from fetch_unified import fetch_market_data

# Auto-routes to NBP
df = fetch_market_data('USD', source='nbp', table='A', start_date='2024-01-01')

print(f"Retrieved {len(df)} NBP rates")
print(f"Average USD/PLN mid rate: {df['Mid'].mean():.4f}")

print("\nRecent rates:")
print(df.tail())
```

### Query 4: "Download S&P 500 weekly data"

```python
from fetch_unified import fetch_market_data

# Auto-routes to Yahoo
df = fetch_market_data('^GSPC', start_date='2023-01-01', end_date='2024-12-31')

# For weekly data, resample
weekly = df.set_index('Date').resample('W').agg({
    'Open': 'first',
    'High': 'max',
    'Low': 'min',
    'Close': 'last',
    'Volume': 'sum'
}).reset_index()

print(f"Weekly data: {len(weekly)} weeks")
print(weekly.tail())
```

### Query 5: "Get US GDP data from FRED"

```python
from fetch_unified import fetch_market_data

# Requires FRED API key configured
df = fetch_market_data('GDP', start_date='2020-01-01')

print(f"GDP data points: {len(df)}")
print(f"Latest GDP: {df.iloc[-1]['Value']:.1f} billion USD")
print(f"Date: {df.iloc[-1]['Date']}")

print("\nRecent GDP values:")
print(df.tail())
```

## Best Practices

### 1. Use Auto-Routing by Default

Let the skill choose the best source:
```python
# Good - auto-routing
df = fetch_market_data('pko')

# Also good - explicit source only when needed
df = fetch_market_data('pko', source='stooq')
```

### 2. Enable Caching

Cache significantly improves performance:
```python
# Cache is enabled by default (good)
df = fetch_market_data('pko')

# Disable only when fresh data critical
df = fetch_market_data('pko', use_cache=False)
```

### 3. Handle Errors Gracefully

Always wrap in try-except:
```python
try:
    df = fetch_market_data(ticker)
except ValueError as e:
    print(f"Data not found: {e}")
    # Try alternative source or ticker format
except Exception as e:
    print(f"Error: {e}")
    # Log and continue
```

### 4. Validate Results

Check data quality:
```python
df = fetch_market_data('pko')

# Basic validation
assert not df.empty, "No data returned"
assert 'Date' in df.columns, "Date column missing"
assert 'Close' in df.columns, "Close price missing"
assert df['Close'].notna().all(), "Missing price data"

print(f"✓ Data validated: {len(df)} rows")
```

### 5. Use Batch Methods When Available

Fetch multiple tickers efficiently:
```python
from fetch_unified import UnifiedMarketDataFetcher

fetcher = UnifiedMarketDataFetcher()

# Better than individual calls
tickers = ['pko', 'cdr', 'pzu']
for ticker in tickers:
    df = fetcher.fetch(ticker, start_date='2024-01-01')
    # Process df
```

## Limitations & Gotchas

### Source Availability

- **yfinance** required for Yahoo Finance
- **pandas-datareader** optional (useful fallback)
- **FRED** requires API key

Check available sources:
```python
fetcher = UnifiedMarketDataFetcher()
print("Available sources:", fetcher.list_available_sources())
```

### Ticker Format Sensitivity

Different sources use different ticker formats:
- Stooq: `pko` (lowercase)
- Yahoo: `PKO.WA` (uppercase + suffix)

Auto-routing handles this, but be aware when forcing sources.

### Date Range Limitations

- Weekend/holiday gaps normal for stock data
- NBP: Business days only
- FRED: Lower frequency (quarterly, monthly)

### Rate Limiting

Be respectful:
- Default 1-2 second delay between requests
- Use caching to minimize API calls
- Batch similar requests together

## Troubleshooting

### Problem: "No module named 'yfinance'"

**Solution**: Install yfinance
```bash
pip install yfinance
```

Or use other sources (Stooq, NBP).

### Problem: "FRED API key required"

**Solution**: Configure API key (see `references/api_setup.md`)
```bash
export FRED_API_KEY="your_key"
```

Or skip FRED and use other sources.

### Problem: "No data available for ticker"

**Solutions**:
1. Check ticker format (see `references/ticker_formats.md`)
2. Try different source
3. Verify ticker exists on that source
4. Check date range is valid

### Problem: Slow Performance

**Solutions**:
1. Enable caching (default)
2. Reduce date range
3. Batch requests
4. Check network connectivity

---

## Project Migration

After prototyping with this skill, you can migrate fetchers to your production project.

### Migrate a Data Source

```bash
# List available sources
uv run scripts/migrate_to_project.py --list

# Migrate Stooq fetcher to your project
uv run scripts/migrate_to_project.py stooq --target src/data_sources/

# Migrate with utilities and .env template
uv run scripts/migrate_to_project.py yahoo --target src/market_data/ --include-utils --include-env

# Migrate all fetchers
uv run scripts/migrate_to_project.py all --target src/fetchers/ --include-utils --include-env
```

### What Migration Produces

```
src/data_sources/           # Your target directory
├── fetch_stooq.py          # Self-contained with PEP 723 dependencies
├── utils.py                # Shared utilities (if --include-utils)
└── .env.example            # API key template (if --include-env)
```

### After Migration

The migrated scripts work standalone:
```bash
uv run src/data_sources/fetch_stooq.py PKO 2024-01-01 2024-12-31
```

Or import in your code:
```python
sys.path.insert(0, 'src/data_sources')
from fetch_stooq import fetch_stooq
df = fetch_stooq('pko', '2024-01-01')
```

---

## Summary

Use `fetch_unified.fetch_market_data()` as the primary interface. It provides:
- ✓ Intelligent source routing
- ✓ Automatic fallback
- ✓ Standardized output
- ✓ Built-in caching
- ✓ Comprehensive error handling
- ✓ ISIN and UID support via TickerRegistry
- ✓ Cross-source ticker conversion
- ✓ CLI support via `uv run` (PEP 723)
- ✓ Project migration for production use

**Quick Start (CLI)**:
```bash
uv run scripts/fetch_unified.py PKO 2024-01-01 2024-12-31
```

**API Keys**: Copy `.env.example` to `.env` and add your keys for Tiingo, FRED, etc.

For ticker/ISIN conversions, use `ticker_registry.TickerRegistry()` or convenience functions like `isin_to_yahoo()`.

For detailed information, consult the reference files in `references/` directory.

---
name: market-datasets
description: Fetch market data, fundamentals, and financial datasets from multiple sources (EODHD, NBP, Yahoo Finance, FRED, Tiingo, CCXT, FinancialData.Net) with intelligent routing, plus long-history construction patterns for investment research. Use when users request stock prices, indices, FX rates, economic indicators, cryptocurrency data, fundamentals, options, financial statements, or need to build multi-decade return series for backtesting.
argument-hint: "[ticker] [start-date] [end-date]"
allowed-tools: Bash, Read
---

# Market Datasets

Unified market data fetching with intelligent source selection, plus long-history asset construction for investment research.

## When to Use

- **Fetching**: Historical stock prices, indices, FX rates, economic indicators, crypto
- **Construction**: Building multi-decade return series for backtesting (ETF + academic backfill)
- **Comparison**: Cross-source data validation
- **Conversion**: ISIN/ticker lookups across sources

## Supported Sources

| Source | Best For | Auth | Coverage |
|--------|----------|------|----------|
| **EODHD** | **Polish market (auto-routed first when the key is set)**; UCITS/ETF + global multi-exchange; datacenter-reachable (paid, personal-use plans) | API key | GPW `.WAR`, WIG-family `.INDX`, US/EU stocks, ETFs, FX, ISIN-keyed; splits/div-adjusted |
| **NBP** | Official PLN FX | Free | PLN exchange rates |
| **Yahoo** | Global equities (**ad-hoc primary**); Polish fallback without an EODHD key (`.WA`) | Free | Stocks, ETFs, indices, FX worldwide |
| **Tiingo** | Yahoo fallback | API key | US stocks/ETFs, 30+ years |
| **CCXT/Binance** | Crypto OHLCV | Free | All crypto pairs, multiple timeframes |
| **CoinGecko** | Crypto price/market-cap by coin id | Free (opt-in) | Daily price, mcap, volume |
| **FRED** | Macro indicators | API key | US economic data |
| **FinancialData.Net** | Fundamentals, options, insider | API key | US/intl stocks, options, statements, ratios |
| **Shiller** | Long-history equity/bonds | Free | Monthly S&P 500 + 10Y yield (1871+) |
| **Damodaran** | Long-history annual | Free | Annual S&P, T-Bond, T-Bill, Gold (1928+) |

### Dividend Treatment

| Source | Price Type | Use For |
|--------|------------|---------|
| Yahoo | Both (`Close` raw + `Adj_Close`) | P&L (`Close`), returns (`Adj_Close`) |
| EODHD | Both (`Close` raw + `Adj_Close`) | Same — but `Adj_Close` is recomputed on every dividend |

**Key trap**: an adjusted series is rewritten backwards at each dividend, so an
incrementally APPENDED adjusted history loses dividends — chain returns instead.
See [references/dividend_treatment.md](references/dividend_treatment.md).

## Core Workflow

### Step 1: Determine Approach

| Need | Approach |
|------|----------|
| Current/recent prices (ad-hoc) | Auto-routing via unified fetcher — **Yahoo primary** |
| Polish stocks / WIG indices / `.WA` tickers | Auto-routed: **EODHD** (`.WAR`, `.INDX`) when `EODHD_API_KEY` is set. Without the key: stocks/ETFs fall back to Yahoo (`.WA`); a WSE **index raises** — Yahoo has no history for them (keyless alternative: `gpw-benchmark-scraper`) |
| ETF / UCITS prices | **EODHD, opt-in** — force `source='eodhd'` (paid; confirm cost) |
| Datacenter/VPS where Yahoo is blocked | EODHD (REST, no geo-block) — force `source='eodhd'` |
| PLN FX rates | Auto-routed: NBP first, then Yahoo (`USDPLN=X`) |
| Multi-decade backtest series | Long-history construction (see below) |
| ISIN-based lookups | TickerRegistry + Yahoo Direct API |
| Crypto data | CCXT/Binance routing |

### Step 2: Fetch Data

**CLI** (all scripts are self-contained with PEP 723 inline dependencies):
```bash
uv run scripts/fetch_unified.py PKO 2024-01-01 2024-12-31
uv run scripts/fetch_eodhd.py WIG20.INDX 2024-01-01     # Polish index (EODHD)
uv run scripts/fetch_nbp.py USD 2024-01-01 2024-12-31
uv run scripts/fetch_yahoo.py AAPL 2024-01-01
uv run scripts/fetch_eodhd.py SPY 2024-01-01            # ETF/UCITS (EODHD)
uv run scripts/fetch_financialdata.py AAPL 2024-01-01 2024-12-31
```

**Python**:
```python
import sys; sys.path.append('market-datasets/scripts')
from fetch_unified import fetch_market_data

df = fetch_market_data('pko', start_date='2024-01-01')        # Polish → EODHD PKO.WAR, else Yahoo PKO.WA
df = fetch_market_data('AAPL', start_date='2024-01-01')       # US → Yahoo
df = fetch_market_data('USD', source='nbp', table='A')        # FX → NBP
df = fetch_market_data('BTC/USDT', start_date='2024-01-01')   # Crypto → CCXT
df = fetch_market_data('PLXTRDM00011', start_date='2024-01-01')  # ISIN → auto-resolve
```

### Step 3: Handle Results

All fetchers return pandas DataFrames with standardized columns:

| Column | Description |
|--------|-------------|
| `Date` | datetime |
| `Open`, `High`, `Low`, `Close` | OHLC prices |
| `Volume` | Trading volume (if available) |
| `Adj_Close` | Adjusted close (Yahoo, EODHD) |

Economic data (FRED, NBP): `Date`, `Value`, `Currency`/`Series_ID`.

## Quick Examples

```python
# 1. Simple fetch with auto-routing
df = fetch_market_data('pko', start_date='2024-01-01', end_date='2024-12-31')

# 2. Multi-source comparison
from fetch_unified import UnifiedMarketDataFetcher
fetcher = UnifiedMarketDataFetcher()
comparison = fetcher.compare_sources('PKO.WA', ['eodhd', 'yahoo'], start_date='2024-01-01')

# 3. ISIN batch fetch
from fetch_yahoo_direct import fetch_by_isin
prices, dividends, splits, mapping = fetch_by_isin(
    ['PLXTRDM00011', 'US0378331005'], start_date='2024-01-01'
)
```

For all usage patterns, see [references/usage_patterns.md](references/usage_patterns.md).

## Long-History Asset Construction

For investment research requiring multi-decade return series (backtesting, risk calibration), use the **ETF-primary, academic-backfill** pattern.

### Strategy

```
ETF/fund data (real, 1976-2025)  ←  PRIMARY: highest quality
    ↕ splice point
Academic data (synthetic, 1928+)  ←  BACKFILL: extends history
```

### Standard Asset Class Proxies

| Asset Class | Primary Source | Backfill Source | Splice Point |
|-------------|---------------|-----------------|--------------|
| **Equity** | VFINX (yfinance) | Shiller S&P 500 price+dividends | ~1976 |
| **FI_AGG** (core bonds) | VBMFX (yfinance) | Shiller 10Y yield → synthetic bond return | ~1987 |
| **FI_SHORT** (short duration) | 50% SHV + 50% VFISX | 50% FRED TB3MS + 50% synthetic dur-2Y | ~1991 |
| **Commodities** (gold) | EODHD `XAUUSD.FOREX` | From 1990-01-02 (probed 2026-09-30); `GC=F` is not on EODHD | N/A |

### Key Construction Patterns

**Splice**: Use primary where available, backfill for earlier dates. No blending.
```python
splice_date = primary.index.min()
backfill_part = backfill[backfill.index < splice_date]
result = pd.concat([backfill_part, primary]).sort_index()
```

**Synthetic bond return** from yield:
```python
coupon = yield_series.shift(1) / 12
price_change = -duration * (yield_series - yield_series.shift(1))
monthly_return = coupon + price_change
```

**Total return from price + dividends**:
```python
total_return = (price + dividend / 12) / price.shift(1) - 1
```

For complete source details, download patterns, and validation methodology, see [references/long_history_construction.md](references/long_history_construction.md).

Reference implementation: `research/strategic-asset-allocation/build_asset_data_v2.py`.

## Ticker Formats

| Source | Example | Format |
|--------|---------|--------|
| EODHD | `PKO.WAR`, `WIG20.INDX`, `USDPLN.FOREX`, `SPY.US` | `SYMBOL.EXCHANGE` |
| Yahoo | `PKO.WA`, `^GSPC`, `AAPL`, `USDPLN=X` | uppercase, suffix/caret |
| NBP | `USD`, `EUR` | 3-letter ISO |
| FRED | `GDP`, `UNRATE`, `TB3MS` | exact series ID |
| CCXT | `BTC/USDT`, `ETHUSDT` | pair format |

Full reference: [references/ticker_formats.md](references/ticker_formats.md).

## Caching

File-based caching enabled by default:
- **Location**: `data/cache/market_data/{source}/`
- **Default TTL**: 24 hours

```python
df = fetch_market_data('pko', use_cache=False)           # Disable cache
fetcher = UnifiedMarketDataFetcher(cache_hours=48)       # Custom TTL
```

## Configuration

### API Keys

| Source | Setup | Required? |
|--------|-------|-----------|
| FRED | `export FRED_API_KEY="..."` or `config/fred_api_key.txt` | For macro data |
| Tiingo | `export TIINGO_API_KEY="..."` | For Yahoo fallback |
| FinancialData.Net | `export FINANCIAL_DATA_API_KEY="..."` | For fundamentals, options, insider data |
| EODHD | `export EODHD_API_KEY="..."` | For Polish routing (else Yahoo), UCITS/ETF |

See [references/api_setup.md](references/api_setup.md).

## Error Handling

```python
try:
    df = fetch_market_data(ticker)
except ValueError as e:
    print(f"Invalid ticker or no data: {e}")  # Bad ticker, empty result, date issues
except Exception as e:
    print(f"Network or other error: {e}")
```

## Best Practices

1. **Use auto-routing by default** — let the fetcher choose the best source
2. **Enable caching** — reduces API load, enables offline work
3. **Validate results** — check `not df.empty`, expected columns, no NaN gaps
4. **Batch requests** — loop with fetcher instance, don't re-instantiate
5. **Respect rate limits** — 1-2s delay between requests (built in)

## Removed Sources

- **Stooq** — removed 2026-09-30. It blocks datacenter IPs (Hetzner, since
  2026-04-21) and serves a JavaScript browser challenge ("This site requires
  JavaScript to verify your browser") to any non-browser client, so no agent or
  LLM session can fetch from it. `source='stooq'` raises `ValueError` saying so;
  Polish instruments now route to EODHD / Yahoo, PLN FX to NBP / Yahoo.

## Reference Documentation

Load these when needed for detailed information:

| Reference | When to Load |
|-----------|-------------|
| [usage_patterns.md](references/usage_patterns.md) | All usage patterns with full code |
| [long_history_construction.md](references/long_history_construction.md) | Academic sources, splice methodology, validation |
| [sources_overview.md](references/sources_overview.md) | Detailed source comparison, coverage |
| [ticker_formats.md](references/ticker_formats.md) | Complete ticker format mappings |
| [eodhd.md](references/eodhd.md) | EODHD coverage, plan limits, ISIN→listing pinning, holdings/index gaps |
| [api_setup.md](references/api_setup.md) | API key setup, troubleshooting |
| [dividend_treatment.md](references/dividend_treatment.md) | Raw vs adjusted prices, validation |
| [security_master.md](references/security_master.md) | TickerRegistry API, UID conventions |
| [instrument_registry_schema.yaml](references/instrument_registry_schema.yaml) | Shared registry schema for dataset repos |
| [migration.md](references/migration.md) | Migrating fetchers to production projects |

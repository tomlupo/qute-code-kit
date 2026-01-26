# Market Data Sources Overview

Comprehensive comparison of all supported data sources for the market-data-fetcher skill.

## Quick Reference Table

| Source | Best For | Coverage | Auth Required | Rate Limits | Cost |
|--------|----------|----------|---------------|-------------|------|
| **Stooq** | Polish stocks & indices | Polish market, some international | No | Informal (~1-2s delay) | Free |
| **NBP API** | PLN exchange rates | Official PLN rates vs major currencies | No | None documented | Free |
| **Yahoo Finance** | US stocks & global equities | Global stocks, ETFs, indices | No | Informal (~1s delay) | Free |
| **Tiingo** | US stocks fallback | 86,000+ securities, 30+ years | Yes (API key) | 50/hr, 1000/day | Free |
| **CCXT (Binance)** | Cryptocurrency | BTC, ETH, altcoins | No | Exchange limits | Free |
| **FRED** | Economic indicators | US economic data (GDP, CPI, rates) | Yes (API key) | None documented | Free |
| **pandas-datareader** | Meta-source fallback | Multiple sources via single interface | Varies | Varies | Free |

## Dividend Treatment Quick Reference

| Source | Price Type | Dividends Available | Use For |
|--------|------------|---------------------|---------|
| **Stooq** | Adjusted only | No (prices pre-adjusted) | Total return calculations |
| **Yahoo Finance** | Both (close + adj_close) | Yes (via API) | P&L calc (close), returns (adj_close) |
| **NBP** | N/A | N/A | FX rates only |
| **FRED** | N/A | N/A | Economic data only |

See `references/dividend_treatment.md` for detailed dividend handling documentation.

---

## Detailed Source Descriptions

### 1. Stooq (stooq.pl)

**Purpose**: Free historical market data for Polish and international securities.

**Coverage**:
- Polish stocks (PKO, CDR, PZU, etc.)
- Polish indices (WIG20, mWIG40, WIG, sWIG80)
- International indices (^SPX, ^IXIC, ^DJI)
- Currency pairs (EURUSD, USDPLN, EURPLN)
- Some commodities

**Data Available**:
- OHLCV (Open, High, Low, Close, Volume)
- Daily, weekly, monthly intervals
- Extensive historical data (1990s+)

**Dividend Treatment**: ⚠️ **Adjusted prices only**
- All OHLC values are **dividend-adjusted** automatically
- When dividends paid, historical prices adjusted DOWN
- Adjustment factor: `(price - dividend) / price`
- Multiple dividends compound (older data has larger adjustments)
- **Cannot recover raw prices** from Stooq alone
- Validated: Stooq prices match Yahoo Finance `adj_close` (95.8% of 48 tickers within 1%)
- See `references/dividend_treatment.md` for details

**Strengths**:
- Free, no registration
- Excellent Polish market coverage
- Long historical data
- Simple CSV API
- Consistent dividend adjustment methodology

**Limitations**:
- No raw/unadjusted prices available
- No dividend amounts API
- Limited international coverage
- No real-time data
- Informal rate limits (be polite)

**Best For**:
- Polish stock analysis
- Total return calculations
- Performance attribution (returns)
- mWIG40 portfolio tracking
- Historical backtesting (Polish market)

**Not Suitable For**:
- Calculating actual P&L on specific trades (use Yahoo `close`)
- Getting dividend payment amounts (use Yahoo Finance)

**Example Tickers**:
- `pko` - PKO Bank Polski
- `wig20` - WIG20 index
- `usdpln` - USD/PLN exchange rate

---

### 2. NBP API (api.nbp.pl)

**Purpose**: Official Polish National Bank exchange rates.

**Coverage**:
- PLN exchange rates vs major currencies (USD, EUR, GBP, CHF, etc.)
- Table A: Most common currencies (daily rates)
- Table B: Less common currencies
- Table C: Buy/sell rates

**Data Available**:
- Mid rates (Tables A & B)
- Bid/Ask rates (Table C)
- Daily data
- Historical data from ~2002

**Strengths**:
- Official NBP rates
- Free JSON API
- No authentication required
- Reliable and maintained

**Limitations**:
- PLN pairs only (no USD/EUR etc.)
- Daily frequency only
- Market days only (no weekends)

**Best For**:
- Official PLN FX rates for accounting
- Fund NAV calculations
- Regulatory reporting

**Example Codes**:
- `USD` - US Dollar
- `EUR` - Euro
- `GBP` - British Pound

---

### 3. Yahoo Finance (via yfinance or Direct API)

**Purpose**: Comprehensive global market data.

**Coverage**:
- US stocks (NASDAQ, NYSE, etc.)
- International stocks (with market suffix)
- ETFs
- Indices
- Cryptocurrencies
- Some commodities

**Data Available**:
- OHLCV + Adjusted Close
- Intraday to monthly intervals
- Dividends and stock splits
- Company info/metadata

**Two Access Methods**:

1. **yfinance library** (`fetch_yahoo.py`)
   - Standard Python library
   - May experience rate limiting (HTTP 429 errors)

2. **Direct API** (`fetch_yahoo_direct.py`) - **Recommended**
   - Bypasses yfinance rate limiting issues
   - Supports ISIN-to-ticker automatic conversion
   - Returns prices, dividends, and splits separately

**Corporate Actions Captured**:
| Action | Captured? | API Parameter |
|--------|-----------|---------------|
| Dividends | Yes | `events=div` |
| Stock splits | Yes | `events=splits` |
| Rights issues | No | - |
| Spin-offs | No | - |

**Dividend Treatment**: Both raw and adjusted prices available
- `close` = Raw/unadjusted price (actual trading price)
- `adj_close` = Dividend-adjusted price (for total returns)
- `adj_close` matches Stooq prices (validated 95.8% within 1%)
- Use `close` for P&L calculations, `adj_close` for return calculations
- See `references/dividend_treatment.md` for details

**Strengths**:
- Comprehensive US market coverage
- Global reach with market suffixes
- High data quality
- Adjusted prices for splits/dividends
- Free (no authentication required)
- ISIN lookup via search API

**Limitations**:
- Unofficial API (could change)
- yfinance library prone to rate limiting (use Direct API instead)
- Polish stocks: Limited history
- Does NOT capture: rights issues, spin-offs, buybacks

**Best For**:
- US stock analysis
- International equities
- Cross-market comparisons
- Portfolio tracking
- Fetching by ISIN (auto-conversion)
- Dividend and split data

**Example Tickers**:
- `AAPL` - Apple Inc.
- `^GSPC` - S&P 500 Index
- `PKO.WA` - PKO on Warsaw Stock Exchange
- `XTB.WA` - XTB on Warsaw Stock Exchange

**Example ISINs** (auto-converted via Direct API):
- `US0378331005` → `AAPL`
- `PLXTRDM00011` → `XTB.WA`
- `PLCCC0000016` → `CCC.WA`

---

### 4. Tiingo (api.tiingo.com)

**Purpose**: High-quality US stock data with generous free tier and 30+ years of history.

**Coverage**:
- US stocks (NYSE, NASDAQ, AMEX)
- ETFs
- ADRs
- 86,000+ securities

**Data Available**:
- OHLCV + Adjusted prices
- Dividend amounts
- Split factors
- 30+ years of history
- Daily frequency

**Free Tier Limits**:
- 50 requests per hour
- 1,000 requests per day
- 500 unique symbols per month

**Strengths**:
- Excellent data quality
- **Best free tier** of all stock APIs
- 30+ years of history
- Dividend and split data
- Reliable (backed by IEX data)

**Limitations**:
- **Requires API key** (free registration)
- US securities focus
- Monthly symbol limit

**Best For**:
- Yahoo Finance fallback
- Historical US stock analysis
- Dividend-adjusted returns
- Quality validation

**Setup**: Get free API key at https://api.tiingo.com/

```python
# Set environment variable
os.environ['TIINGO_API_KEY'] = 'your_api_key'

# Or pass directly
df = fetch_market_data('AAPL', source='tiingo', tiingo_api_key='your_key')
```

---

### 5. CCXT / Binance (Cryptocurrency)

**Purpose**: Cryptocurrency historical OHLCV data from Binance and 100+ exchanges.

**Coverage**:
- All Binance trading pairs (BTC, ETH, altcoins)
- 100+ exchanges via CCXT library
- Spot, futures, perpetuals

**Data Available**:
- OHLCV (Open, High, Low, Close, Volume)
- Timeframes: 1m, 5m, 15m, 1h, 4h, 1d, 1w
- Years of history (exchange dependent)

**Rate Limits**:
- Built-in CCXT rate limiting
- Exchange-specific limits respected

**Strengths**:
- **Unlimited** historical data (no API key needed)
- Multiple exchanges with unified interface
- Minute-level granularity
- Real-time available

**Limitations**:
- Requires ccxt package
- Exchange-specific quirks
- No fundamental data

**Best For**:
- Bitcoin/Ethereum analysis
- Crypto portfolio tracking
- Algorithmic trading research
- DeFi token analysis

**Supported Exchanges**:
- Binance (default)
- Kraken
- Coinbase Pro
- KuCoin
- Bybit
- OKX
- and 100+ more

**Example Usage**:

```python
# Auto-routed (detects crypto symbols)
df = fetch_market_data('BTC/USDT', start_date='20240101')

# Symbol formats (all work)
df = fetch_market_data('ETHUSDT')    # Without slash
df = fetch_market_data('ETH/USD')    # With slash
df = fetch_market_data('SOL/USDT')   # Altcoins

# Different timeframes
df = fetch_market_data('BTC/USDT', timeframe='1h')  # Hourly
df = fetch_market_data('BTC/USDT', timeframe='1w')  # Weekly

# Different exchange
fetcher = UnifiedMarketDataFetcher(crypto_exchange='kraken')
df = fetcher.fetch('BTC/USD')
```

---

### 6. FRED API (fred.stlouisfed.org)

**Purpose**: US economic indicators from Federal Reserve.

**Coverage**:
- US economic indicators
- GDP, inflation, unemployment
- Interest rates
- Consumer confidence
- Money supply
- 800,000+ time series

**Data Available**:
- Economic indicator values
- Various frequencies (daily, monthly, quarterly, annual)
- Extensive historical data
- Metadata (units, seasonality, etc.)

**Strengths**:
- Authoritative economic data
- Vast coverage
- Official Federal Reserve source
- Well-documented API
- Free with API key

**Limitations**:
- **Requires API key** (free registration)
- US-focused data only
- Low-frequency data (mostly monthly/quarterly)

**Best For**:
- Macroeconomic analysis
- Economic research
- Factor modeling
- Risk analysis

**Example Series**:
- `GDP` - Gross Domestic Product
- `UNRATE` - Unemployment Rate
- `CPIAUCSL` - Consumer Price Index
- `DGS10` - 10-Year Treasury Rate

**Setup**: See `references/api_setup.md` for API key configuration.

---

### 5. pandas-datareader

**Purpose**: Meta-source providing unified interface to multiple data providers.

**Coverage**:
- Stooq (via pandas-datareader)
- Yahoo Finance (via pandas-datareader)
- FRED (via pandas-datareader)
- Alpha Vantage (requires API key)
- IEX Cloud (requires API key)
- Quandl (requires API key)

**Data Available**:
- Depends on underlying source
- Generally: OHLCV for markets, values for economic data

**Strengths**:
- Unified interface
- Useful fallback
- Access to multiple sources
- Well-maintained library

**Limitations**:
- Requires pandas-datareader package
- Source-specific quirks
- Some sources deprecated over time
- Additional API keys may be needed

**Best For**:
- Fallback when primary sources fail
- Quick prototyping
- Multi-source data pipelines

---

## Source Selection Strategy

### Automatic Routing (Recommended)

The unified fetcher automatically selects sources based on ticker patterns:

1. **Cryptocurrency** (BTC/USDT, ETHUSDT) → CCXT/Binance
2. **Polish stocks** (pko, cdr, pzu) → Stooq
3. **PLN FX rates** (USD, EUR, GBP) → NBP API
4. **US stocks** (AAPL, MSFT, GOOGL) → Yahoo Finance → Tiingo (fallback)
5. **International indices** (^SPX, ^IXIC) → Yahoo Finance
6. **Economic indicators** (GDP, UNRATE) → FRED
7. **Currency pairs** (USDPLN, EURUSD) → Stooq
8. **Fallback** → pandas-datareader

### Manual Source Selection

Force specific source when needed:

```python
# Force Stooq for specific ticker
df = fetch_market_data('pko', source='stooq')

# Force Yahoo for Polish stock
df = fetch_market_data('PKO.WA', source='yahoo')

# Force NBP for PLN rate
df = fetch_market_data('USD', source='nbp', table='A')
```

### Multi-Source Comparison

Compare data across sources:

```python
comparison = fetcher.compare_sources('pko', ['stooq', 'yahoo'])
```

---

## Rate Limiting & Best Practices

### Respect Rate Limits

All fetchers include automatic rate limiting:
- Minimum 1-2 second delay between requests
- Configurable per source
- Automatic retry logic

### Use Caching

Enable caching to minimize requests:

```python
fetcher = UnifiedMarketDataFetcher(use_cache=True, cache_hours=24)
```

Cache locations:
- `data/cache/market_data/stooq/`
- `data/cache/market_data/nbp/`
- `data/cache/market_data/yahoo/`
- `data/cache/market_data/fred/`

### Batch Requests

Use batch methods when fetching multiple tickers:

```python
# More efficient than individual calls
results = fetcher.fetch_multiple(['pko', 'cdr', 'pzu'])
```

---

## Dependencies

### Required Packages

```bash
pip install pandas requests
```

### Optional Packages

```bash
# For Yahoo Finance
pip install yfinance

# For pandas-datareader
pip install pandas-datareader

# For Tiingo
pip install tiingo  # Or use built-in REST (no extra package)

# For Cryptocurrency (CCXT)
pip install ccxt
```

### API Keys (Optional)

- **FRED**: Required for economic data
  - Get at: https://fred.stlouisfed.org/docs/api/api_key.html
  - See: `references/api_setup.md`

- **Tiingo**: Required for Tiingo data
  - Get at: https://api.tiingo.com/
  - Set: `TIINGO_API_KEY` environment variable

- **CCXT**: No API key needed for public historical data

---

## Troubleshooting

### Source Unavailable

If a source is unavailable:
1. Check if required package is installed
2. Verify API key configuration (for FRED)
3. Check internet connectivity
4. Try fallback source

### Data Quality Issues

If data appears incorrect:
1. Compare across sources using `compare_sources()`
2. Check ticker format is correct for source
3. Verify date range is valid
4. Check for corporate actions (splits, dividends)

### Rate Limiting

If experiencing rate limiting:
1. Increase delay in rate limiter
2. Enable caching to reduce requests
3. Batch similar requests together
4. Use off-peak hours for large downloads

---

## When to Use Which Source

| Scenario | Recommended Source | Rationale |
|----------|-------------------|-----------|
| Polish fund performance attribution | Stooq | Best Polish market coverage, adjusted prices |
| Official PLN rates for accounting | NBP | Official regulatory rates |
| US stock portfolio tracking | Yahoo → Tiingo | Comprehensive US coverage, Tiingo as fallback |
| Macro factor analysis | FRED | Authoritative economic data |
| Cross-market equity comparison | Yahoo | Global reach |
| Historical Polish index data | Stooq | Long history, free access |
| Intraday US stock data | Yahoo | Supports intraday intervals |
| Data validation/cross-check | Multiple via compare_sources() | Ensures accuracy |
| **Total return calculation** | Stooq or Yahoo `adj_close` | Both are dividend-adjusted |
| **Actual P&L on trades** | Yahoo `close` | Raw prices needed |
| **Dividend amounts** | Yahoo Finance or Tiingo | Via API |
| **Validate Stooq data** | Yahoo `adj_close` | Should match within 1% |
| **Cryptocurrency analysis** | CCXT/Binance | Free unlimited history |
| **Bitcoin/ETH tracking** | CCXT | Best crypto coverage |
| **Hourly crypto data** | CCXT with `timeframe='1h'` | Supports all intervals |
| **US stocks when Yahoo fails** | Tiingo | Best free tier backup |

# Market Data Sources Overview

Comprehensive comparison of all supported data sources for the market-datasets skill.

## Quick Reference Table

| Source | Best For | Coverage | Auth Required | Rate Limits | Cost |
|--------|----------|----------|---------------|-------------|------|
| **EODHD** | Polish stocks & indices (auto-routed first when keyed); UCITS/ETF + global multi-exchange, datacenter-reachable | GPW `.WAR`, WIG-family `.INDX`, US/EU stocks, ETFs, FX; ISIN-keyed; splits/div-adjusted | Yes (API key) | Free: 20/day, ~1yr history. Paid: 100k/day, full history | Free/Paid (~$20/mo), personal-use plans |
| **NBP API** | PLN exchange rates | Official PLN rates vs major currencies | No | None documented | Free |
| **Yahoo Finance** | US stocks & global equities | Global stocks, ETFs, indices | No | Informal (~1s delay) | Free |
| **Tiingo** | US stocks fallback | 86,000+ securities, 30+ years | Yes (API key) | 50/hr, 1000/day | Free |
| **CCXT (Binance)** | Cryptocurrency | BTC, ETH, altcoins | No | Exchange limits | Free |
| **FRED** | Economic indicators | US economic data (GDP, CPI, rates) | Yes (API key) | None documented | Free |
| **FinancialData.Net** | Fundamentals, options, insider data | US/intl stocks, options, fundamentals, insider | Yes (API key) | Tier-dependent | Free/Paid |
| **pandas-datareader** | Meta-source fallback | Multiple sources via single interface | Varies | Varies | Free |

## Dividend Treatment Quick Reference

| Source | Price Type | Dividends Available | Use For |
|--------|------------|---------------------|---------|
| **EODHD** | Both (close + adjusted_close) | Yes (splits/div-adjusted) | P&L (close), returns (adjusted_close) |
| **Yahoo Finance** | Both (close + adj_close) | Yes (via API) | P&L calc (close), returns (adj_close) |
| **NBP** | N/A | N/A | FX rates only |
| **FRED** | N/A | N/A | Economic data only |

See `references/dividend_treatment.md` for detailed dividend handling documentation.

---

## Detailed Source Descriptions

### 1. NBP API (api.nbp.pl)

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

### 2. Yahoo Finance (via yfinance or Direct API)

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
- `adj_close` is rewritten on every dividend — never splice stored adjusted levels (see dividend_treatment.md)
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

### 3. Tiingo (api.tiingo.com)

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

### 4. CCXT / Binance (Cryptocurrency)

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

### 5. FRED API (fred.stlouisfed.org)

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

### 6. FinancialData.Net (financialdata.net)

**Purpose**: Comprehensive financial data API covering stocks, fundamentals, options, forex, crypto, and institutional data.

**Coverage**:
- US stocks, international stocks, ETFs, commodities, OTC
- Options (chain, prices, Greeks), futures
- Cryptocurrency, forex
- Financial statements (income, balance sheet, cash flow)
- Financial ratios (liquidity, solvency, efficiency, profitability, valuation)
- Company info, key metrics, market cap
- Insider transactions, senate/house trading
- Institutional investors, holdings
- Earnings/IPO/splits/dividends calendars
- Press releases (company, SEC, Fed)

**Data Available**:
- OHLCV prices (daily, minute)
- Real-time quotes (Premium)
- 50+ API endpoints
- JSON and CSV output formats

**Subscription Tiers**:
| Tier | Access |
|------|--------|
| **Free** | Symbol lists, stock prices, commodity prices, OTC data |
| **Standard** | Company info, financials, ratios, derivatives, crypto |
| **Premium** | Real-time quotes, international data, forex, press releases |

**Strengths**:
- Comprehensive coverage in a single API
- Options and derivatives data (chain, Greeks)
- Institutional and insider trading data
- Financial statements and ratios
- Senate/House trading disclosures
- Event calendars (earnings, IPO, splits, dividends)
- Python SDK available (`fdnpy`)

**Limitations**:
- **Requires API key** (free tier available)
- Premium endpoints need paid subscription
- Record limits per call (300-500, paginated)
- No Polish market-specific data

**Best For**:
- Fundamental analysis
- Options research
- Institutional ownership tracking
- Congressional trading monitoring
- Financial statement analysis
- Event-driven strategy research

**API Details**:
- Base URL: `https://financialdata.net/api/v1/`
- Auth: Query parameter `?key=API_KEY`
- Pagination: `offset` parameter, limits vary by endpoint (300-500)
- Timezones: EST for stocks, UTC for crypto/forex

**Example Usage**:

```python
from fetch_financialdata import FinancialDataFetcher, fetch_financialdata

# Stock prices
df = fetch_financialdata('AAPL', start_date='2024-01-01')

# Financial statements
df = fetch_financialdata('AAPL', endpoint='income-statements', period='year')

# Option chain
df = fetch_financialdata('AAPL', endpoint='option-chain')

# Insider transactions
df = fetch_financialdata('AAPL', endpoint='insider-transactions')

# Senate trading
fetcher = FinancialDataFetcher()
df = fetcher.get_senate_trading()
```

**Setup**: Get API key at https://financialdata.net, set `FINANCIAL_DATA_API_KEY` env var.

---

### 7. pandas-datareader

**Purpose**: Meta-source providing unified interface to multiple data providers.

**Coverage**:
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
2. **Polish stocks & indices** (pko, cdr, wig20, `.WA`/`.WAR`) → EODHD (`PKO.WAR`, `WIG20.INDX`) when `EODHD_API_KEY` is set → Yahoo (`PKO.WA`) for stocks/ETFs only; a WSE index without the key raises
3. **PLN FX rates** (USD, EUR, GBP, USDPLN) → NBP API → Yahoo (`USDPLN=X`)
4. **US stocks** (AAPL, MSFT, GOOGL) → Yahoo Finance → Tiingo → FinancialData.Net (fallback)
5. **International indices** (^SPX, ^IXIC) → Yahoo Finance
6. **Economic indicators** (GDP, UNRATE) → FRED
7. **Other currency pairs** (EURUSD) → Yahoo (`EURUSD=X`)
8. **Fundamentals/options** → FinancialData.Net (via `fd_endpoint` parameter)
9. **Fallback** → pandas-datareader

### Manual Source Selection

Force specific source when needed:

```python
# Force EODHD for a GPW listing
df = fetch_market_data('PKO.WAR', source='eodhd')

# Force Yahoo for Polish stock
df = fetch_market_data('PKO.WA', source='yahoo')

# Force NBP for PLN rate
df = fetch_market_data('USD', source='nbp', table='A')
```

### Multi-Source Comparison

Compare data across sources:

```python
comparison = fetcher.compare_sources('PKO.WA', ['eodhd', 'yahoo'])
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
- `data/cache/market_data/eodhd/`
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

- **FinancialData.Net**: Required for all endpoints
  - Get at: https://financialdata.net
  - Set: `FINANCIAL_DATA_API_KEY` environment variable
  - Free tier: stock prices, symbol lists
  - Standard/Premium: fundamentals, options, forex, insider data

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
| Polish fund performance attribution | EODHD → Yahoo | GPW `.WAR` + `.INDX`, adjusted prices |
| Official PLN rates for accounting | NBP | Official regulatory rates |
| US stock portfolio tracking | Yahoo → Tiingo | Comprehensive US coverage, Tiingo as fallback |
| Macro factor analysis | FRED | Authoritative economic data |
| Cross-market equity comparison | Yahoo | Global reach |
| Historical Polish index data | EODHD `.INDX` | `WIG.INDX` from 1991-04-16 |
| Intraday US stock data | Yahoo | Supports intraday intervals |
| Data validation/cross-check | Multiple via compare_sources() | Ensures accuracy |
| **Total return calculation** | Yahoo or EODHD `adj_close` | Chain returns; adjusted levels are rewritten per dividend |
| **Actual P&L on trades** | Yahoo `close` | Raw prices needed |
| **Dividend amounts** | Yahoo Finance or Tiingo | Via API |
| **Validate EODHD data** | Yahoo `adj_close` returns | Compare returns fetched together, not stored levels |
| **Cryptocurrency analysis** | CCXT/Binance | Free unlimited history |
| **Bitcoin/ETH tracking** | CCXT | Best crypto coverage |
| **Hourly crypto data** | CCXT with `timeframe='1h'` | Supports all intervals |
| **US stocks when Yahoo fails** | Tiingo → FinancialData.Net | Best free tier backup |
| **Fundamental analysis** | FinancialData.Net | Income/balance/cash flow statements |
| **Financial ratios** | FinancialData.Net | Liquidity, solvency, profitability, valuation |
| **Options research** | FinancialData.Net | Option chain, prices, Greeks |
| **Insider trading** | FinancialData.Net | Insider transactions, congress trading |
| **Institutional ownership** | FinancialData.Net | Holders, holdings, portfolio stats |
| **Event calendars** | FinancialData.Net | Earnings, IPO, splits, dividends |

### 8. EODHD (eodhd.com)

End-Of-Day Historical Data — REST API best suited to **UCITS/ETF and global
multi-exchange** coverage. Chosen as the primary ETF/benchmark feed because it
is **reachable from datacenters/VPS** where Yahoo is rate-limited, and it
resolves GPW-listed and EU-domiciled instruments that the free feeds handle
poorly. Since 2026-09-30 it is also the primary source for Polish instruments.

**Why EODHD**
- One REST endpoint per symbol: `GET https://eodhd.com/api/eod/{SYMBOL}` → JSON OHLCV + `adjusted_close`.
- Exchange-suffixed symbols: `.US`, `.LSE` (London), `.WAR` (Warsaw/GPW), `.INDX` (indices), plus ISIN lookup.
- Splits/dividend-adjusted; tz-naive daily history.
- Validated 2026-06-29 on a 42-instrument ETF benchmark universe: **100% resolution**, fresher than yfinance (incl. GPW Beta ETFs `.WAR` and UCITS `.LSE`).

**Tiers**
- Free: ~1 year history, 20 calls/day, limited symbols (validation only).
- Paid (EOD Historical Data, ~$20/mo): full multi-decade history, 100k calls/day.

**Symbol mapping** (see `scripts/fetch_eodhd.py::eodhd_symbol`): bare ticker → `.US`; Yahoo `.WA` → `.WAR`; Yahoo `.L` → `.LSE`; `^IDX` → `IDX.INDX`; already-suffixed → passthrough.

```bash
export EODHD_API_KEY="your_key"
uv run scripts/fetch_eodhd.py SPY 2024-01-01            # -> SPY.US
uv run scripts/fetch_eodhd.py IMEU.LSE 2024-01-01       # UCITS on London
uv run scripts/fetch_eodhd.py ETFBW20TR.WAR 2024-01-01  # GPW Beta ETF
uv run scripts/fetch_eodhd.py ^BCOM 2024-01-01          # -> BCOM.INDX
```

Routing: EODHD is auto-routed **first for Polish instruments only** (GPW
`.WAR`, WIG-family `.INDX`), and only when `EODHD_API_KEY` is set; everything
else keeps Yahoo primary to avoid burning paid calls. Reach for EODHD
deliberately via `source='eodhd'` for UCITS/ETF and datacenter hosts where
Yahoo is blocked. Coverage and licensing: [eodhd.md](eodhd.md).

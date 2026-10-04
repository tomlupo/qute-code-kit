# Ticker Format Reference

Comprehensive guide to ticker symbol formats across all supported data sources.

## Format Conventions by Source

### EODHD

**Exchange-suffixed symbols** (`SYMBOL.EXCHANGE`, one symbol per call). The
primary source for Polish instruments when `EODHD_API_KEY` is set.

**Polish stocks and ETFs**: GPW listings end in `.WAR`
```
PKO.WAR         # PKO Bank Polski
CDR.WAR         # CD Projekt
XTB.WAR         # XTB
ETFBW20TR.WAR   # Beta ETF WIG20TR
ETFBTBSP.WAR    # Beta ETF TBSP (bond-index proxy; the TBSP index itself is not on EODHD)
```

**Indices**: `.INDX`
```
WIG.INDX        # WIG (total return, from 1991-04-16)
WIG20.INDX      # WIG20 (price)
MWIG40.INDX     # mWIG40
SWIG80.INDX     # sWIG80
GSPC.INDX       # S&P 500
BCOM.INDX       # Bloomberg Commodity
VIX.INDX        # VIX
```

**FX, metals, crypto**
```
USDPLN.FOREX    # USD/PLN (PLN per 1 USD)
EURPLN.FOREX
XAUUSD.FOREX    # gold spot (GC=F is not on EODHD)
BTC-USD.CC      # crypto
```

**Other exchanges**
```
SPY.US          # US ETFs/stocks (bare ticker -> .US)
IMEU.LSE        # UCITS on London (Yahoo .L -> .LSE)
```

Conversion from common formats (`scripts/fetch_eodhd.py::eodhd_symbol`):
- bare ticker → `.US`
- `.WA` → `.WAR`  (Warsaw / GPW)
- `.L`  → `.LSE`  (London)
- `^IDX` → `IDX.INDX`
- already exchange-suffixed → passthrough

What the plan covers and what it does not: [eodhd.md](eodhd.md).

---

### NBP API

**Currency Codes**: 3-letter ISO codes (uppercase)
```
USD       # US Dollar
EUR       # Euro
GBP       # British Pound
CHF       # Swiss Franc
JPY       # Japanese Yen
CAD       # Canadian Dollar
AUD       # Australian Dollar
SEK       # Swedish Krona
NOK       # Norwegian Krone
DKK       # Danish Krone
CZK       # Czech Koruna
HUF       # Hungarian Forint
```

**Important Notes**:
- Must be uppercase
- Only single currencies supported (not pairs like USD/EUR)
- All rates are quoted against PLN
- Limited to currencies traded at NBP

---

### Yahoo Finance

**US Stocks**: Uppercase, no suffix
```
AAPL      # Apple Inc.
MSFT      # Microsoft Corporation
GOOGL     # Alphabet Inc. (Class A)
AMZN      # Amazon.com Inc.
TSLA      # Tesla Inc.
META      # Meta Platforms Inc.
NVDA      # NVIDIA Corporation
```

**Polish Stocks**: Uppercase + `.WA` (Warsaw) suffix
```
PKO.WA    # PKO Bank Polski
CDR.WA    # CD Projekt
PZU.WA    # PZU
PKN.WA    # PKN Orlen
KGH.WA    # KGHM
PGE.WA    # PGE
LPP.WA    # LPP
```

**International Stocks**: Ticker + market suffix
```
ASML.AS   # ASML (Amsterdam)
VOW3.DE   # Volkswagen (Frankfurt)
BP.L      # BP (London)
7203.T    # Toyota (Tokyo)
```

**Indices**: With caret prefix
```
^GSPC     # S&P 500
^IXIC     # NASDAQ Composite
^DJI      # Dow Jones Industrial Average
^FTSE     # FTSE 100
^GDAXI    # DAX
^N225     # Nikkei 225
```

**ETFs**: Standard tickers
```
SPY       # SPDR S&P 500 ETF
QQQ       # Invesco QQQ Trust
IWM       # iShares Russell 2000 ETF
EEM       # iShares MSCI Emerging Markets ETF
```

**Market Suffixes**:
- `.WA` - Warsaw Stock Exchange (Poland)
- `.L` - London Stock Exchange (UK)
- `.DE` - Frankfurt Stock Exchange (Germany)
- `.PA` - Euronext Paris (France)
- `.AS` - Euronext Amsterdam (Netherlands)
- `.T` - Tokyo Stock Exchange (Japan)
- `.HK` - Hong Kong Stock Exchange

---

### FRED

**Economic Indicators**: Short uppercase codes
```
GDP       # Gross Domestic Product
UNRATE    # Unemployment Rate
CPIAUCSL  # Consumer Price Index
PAYEMS    # Total Nonfarm Payrolls
INDPRO    # Industrial Production Index
```

**Interest Rates**:
```
DGS10     # 10-Year Treasury Constant Maturity Rate
DGS2      # 2-Year Treasury Constant Maturity Rate
FEDFUNDS  # Federal Funds Effective Rate
MORTGAGE30US # 30-Year Fixed Rate Mortgage Average
```

**Money Supply**:
```
M1SL      # M1 Money Stock
M2SL      # M2 Money Stock
```

**Consumer Sentiment**:
```
UMCSENT   # University of Michigan Consumer Sentiment
CSCICP03USM665S # Consumer Confidence Index
```

**Search for Series**: https://fred.stlouisfed.org/

---

## Cross-Source Ticker Mapping

### Same Company, Different Formats

| Company | EODHD | Yahoo | Description |
|---------|-------|-------|-------------|
| PKO Bank Polski | `PKO.WAR` | `PKO.WA` | Polish bank |
| CD Projekt | `CDR.WAR` | `CDR.WA` | Polish game developer |
| PZU | `PZU.WAR` | `PZU.WA` | Polish insurer |
| PKN Orlen | `PKN.WAR` | `PKN.WA` | Polish oil & gas |
| KGHM | `KGH.WAR` | `KGH.WA` | Polish mining |

### Indices

| Index | EODHD | Yahoo | Description |
|-------|-------|-------|-------------|
| S&P 500 | `GSPC.INDX` | `^GSPC` | US large cap |
| NASDAQ | `IXIC.INDX` | `^IXIC` | US tech |
| WIG20 | `WIG20.INDX` | — (no history on Yahoo) | Polish blue chip |

### Currency Pairs

| Pair | EODHD | NBP (component) | Yahoo |
|------|-------|-----------------|-------|
| USD/PLN | `USDPLN.FOREX` | `USD` (vs PLN) | `USDPLN=X` |
| EUR/PLN | `EURPLN.FOREX` | `EUR` (vs PLN) | `EURPLN=X` |
| EUR/USD | `EURUSD.FOREX` | N/A | `EURUSD=X` |

---

## Common Ticker Patterns

### Pattern Recognition for Routing

The unified fetcher (`fetch_unified.py::_route_ticker`) auto-routes by pattern and
translates the ticker per source (`_ticker_for_source`):

1. **Known Polish stock or index name** (`pko`, `cdr`, `wig20`) → EODHD
   (`PKO.WAR`, `WIG20.INDX`) when `EODHD_API_KEY` is set, else Yahoo for STOCKS/ETFs only (`PKO.WA`); a WSE index without the key raises (Yahoo has no history for them — `^WIG20`/`^MWIG40` return 0 rows, probed 2026-09-30)

2. **`.WA` / `.WAR` suffix** → EODHD, then Yahoo (same translation)

3. **3 uppercase letters (USD, EUR, etc.)** → NBP, then Yahoo (`USDPLN=X`)

4. **6 uppercase letters** → currency pair → `…PLN`: NBP, then Yahoo; otherwise Yahoo (`EURUSD=X`)

5. **Short uppercase (2-10 chars)** → could be a FRED series → FRED (when keyed)

6. **Starts with ^** → index → Yahoo

7. **Uppercase 1-5 letters** → likely US stock → Yahoo, then Tiingo / FinancialData

8. **Other `.XX` suffix** → international stock → Yahoo (`.INDX` → EODHD)

---

## Ticker Lookup Resources

### Polish Market

- **GPW (Warsaw Stock Exchange)**: https://www.gpw.pl/spolki
- **EODHD exchange symbol list**: `GET https://eodhd.com/api/exchange-symbol-list/WAR?api_token=KEY&fmt=json`

### US Market

- **NASDAQ**: https://www.nasdaq.com/market-activity/stocks/screener
- **NYSE**: https://www.nyse.com/listings_directory/stock
- **Yahoo Finance**: https://finance.yahoo.com/lookup

### FRED Series

- **FRED Search**: https://fred.stlouisfed.org/
- Search by keyword or browse categories
- Series ID shown in URL and metadata

---

## Special Cases & Gotchas

### Polish Stocks: EODHD vs Yahoo

**Problem**: Same company, different suffixes

**Solution**:
- For EODHD: uppercase + `.WAR` (`PKO.WAR`)
- For Yahoo: uppercase + `.WA` (`PKO.WA`)
- Unified fetcher translates automatically

### Currency Pairs: Direction Matters

**NBP API**: Always quotes **foreign currency per 1 PLN**
- `USD` from NBP = How many USD per PLN
- Returns mid rate, bid/ask for table C

**EODHD/Yahoo**: Standard market convention
- `USDPLN` = How many PLN per 1 USD
- This is opposite of some NBP interpretations

### Index Symbols: Caret Prefix

**With caret (^)**:
- Yahoo Finance standard: `^GSPC`, `^IXIC` (no WSE indices)

**Without caret**:
- EODHD: `GSPC.INDX`, `WIG20.INDX` (`^X` → `X.INDX` via `eodhd_symbol`)

### Class Shares

**Google/Alphabet**:
- `GOOGL` - Class A shares (voting rights)
- `GOOG` - Class C shares (no voting rights)

**Berkshire Hathaway**:
- `BRK.A` - Class A shares (~$500,000/share)
- `BRK.B` - Class B shares (~$333/share)

---

## Ticker Validation

### Valid Formats by Source

**EODHD**:
```python
# Valid
'PKO.WAR'       # GPW listing
'WIG20.INDX'    # Index
'USDPLN.FOREX'  # FX pair

# Invalid
'PKO.WA'        # Yahoo suffix — eodhd_symbol converts it to .WAR
'GC=F'          # Yahoo futures code, not on EODHD (use XAUUSD.FOREX)
```

**Yahoo**:
```python
# Valid
'AAPL'          # US stock
'PKO.WA'        # Polish stock with market suffix
'^GSPC'         # Index with caret

# Invalid
'pko'           # Ambiguous without .WA
```

**NBP**:
```python
# Valid
'USD'           # 3-letter ISO code, uppercase
'EUR'
'GBP'

# Invalid
'usd'           # Must be uppercase
'USDPLN'        # Pairs not supported (single currencies only)
```

**FRED**:
```python
# Valid
'GDP'           # Exact series ID
'UNRATE'
'CPIAUCSL'

# Invalid
'gdp'           # Case sensitive
'Unemployment'  # Use series ID, not name
```

---

## Ticker Normalization

The unified fetcher automatically normalizes tickers:

```python
# Automatic normalization examples

# Polish stock name → per-source suffix
'pko' → 'PKO.WAR' (EODHD) / 'PKO.WA' (Yahoo)

# US stock → Uppercase for Yahoo
'aapl' → 'AAPL' (when routed to Yahoo)

# PLN pair → NBP currency / Yahoo pair
'USDPLN' → 'USD' (NBP) / 'USDPLN=X' (Yahoo)

# Currency code → Uppercase for NBP
'usd' → 'USD' (when routed to NBP)
```

---

## ISIN Codes (Yahoo Direct API)

The Yahoo Direct API (`fetch_yahoo_direct.py`) supports automatic ISIN-to-ticker conversion.

**ISIN Format**: 12 characters - 2-letter country code + 9 alphanumeric + 1 check digit

### Common Polish ISINs

| ISIN | Yahoo Ticker | Company |
|------|--------------|---------|
| `PLPKO0000016` | `PKO.WA` | PKO Bank Polski |
| `PLXTRDM00011` | `XTB.WA` | XTB |
| `PLCCC0000016` | `CCC.WA` | CCC |
| `PLBSK0000017` | `ING.WA` | ING Bank Slaski |
| `PLKGHM000017` | `KGH.WA` | KGHM |
| `PLSOFTB00016` | `ACP.WA` | Asseco Poland |
| `PLINTCS00010` | `CAR.WA` | Inter Cars |
| `PLLVTSF00010` | `TXT.WA` | Text (LiveChat) |
| `PLJSW0000015` | `JSW.WA` | JSW |

### Common US ISINs

| ISIN | Yahoo Ticker | Company |
|------|--------------|---------|
| `US0378331005` | `AAPL` | Apple |
| `US5949181045` | `MSFT` | Microsoft |
| `US02079K3059` | `GOOGL` | Alphabet |
| `US0231351067` | `AMZN` | Amazon |
| `US88160R1014` | `TSLA` | Tesla |

### Usage with Direct API

```python
from fetch_yahoo_direct import YahooDirectFetcher, fetch_by_isin

# Single ISIN lookup
fetcher = YahooDirectFetcher()
ticker = fetcher.isin_to_ticker('PLXTRDM00011')  # Returns 'XTB.WA'

# Batch ISIN fetching
isins = ['PLXTRDM00011', 'US0378331005']
prices, dividends, splits, mapping = fetch_by_isin(
    isins,
    start_date='2024-01-01',
    end_date='2025-01-01'
)
```

### Notes on ISIN Resolution

- Yahoo search API matches ISINs to primary exchange listing
- Some ISINs may map to alternative exchanges (e.g., `.SG` for Stuttgart)
- Polish stocks typically resolve to `.WA` (Warsaw) suffix
- If `.SG` ticker returns no data, manually use `.WA` suffix

---

## Quick Reference Cheat Sheet

| You Want | Source | Format Example | Notes |
|----------|--------|----------------|-------|
| Polish stock price | EODHD | `PKO.WAR` | Needs `EODHD_API_KEY`; else Yahoo |
| US stock price | Yahoo | `AAPL` | Uppercase |
| Polish stock (Yahoo) | Yahoo | `PKO.WA` | Uppercase + .WA |
| S&P 500 | Yahoo | `^GSPC` | Caret prefix |
| USD/PLN rate | NBP or Yahoo | `USD` or `USDPLN=X` | NBP=currency, Yahoo=pair |
| US GDP | FRED | `GDP` | Exact series ID |
| mWIG40 index | EODHD | `MWIG40.INDX` | no Yahoo fallback (keyless: gpw-benchmark-scraper) |
| By ISIN | Yahoo Direct | `PLXTRDM00011` | Auto-converts to ticker |
| Dividends & splits | Yahoo Direct | `XTB.WA` | Use `events=div,splits` |

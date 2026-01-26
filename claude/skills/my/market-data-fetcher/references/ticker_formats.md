# Ticker Format Reference

Comprehensive guide to ticker symbol formats across all supported data sources.

## Format Conventions by Source

### Stooq

**Polish Stocks**: Lowercase, no suffix
```
pko       # PKO Bank Polski
cdr       # CD Projekt
pzu       # PZU
pkn       # PKN Orlen
kgh       # KGHM
pge       # PGE
lpp       # LPP
orange    # Orange Polska
```

**Polish Indices**: Lowercase
```
wig       # WIG (main index)
wig20     # WIG20 (blue chips)
mwig40    # mWIG40 (mid cap)
swig80    # sWIG80 (small cap)
wig30     # WIG30
```

**International Indices**: With caret prefix
```
^spx      # S&P 500
^ixic     # NASDAQ Composite
^dji      # Dow Jones Industrial Average
```

**Currency Pairs**: 6-letter code (lowercase)
```
usdpln    # US Dollar / Polish Zloty
eurpln    # Euro / Polish Zloty
eurusd    # Euro / US Dollar
gbpusd    # British Pound / US Dollar
```

**Important Notes**:
- Do NOT use `.pl` suffix (causes "Brak danych" error)
- Use lowercase for consistency
- Stooq ticker `pko` ≠ Yahoo ticker `PKO.WA`

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

| Company | Stooq | Yahoo | Description |
|---------|-------|-------|-------------|
| PKO Bank Polski | `pko` | `PKO.WA` | Polish bank |
| CD Projekt | `cdr` | `CDR.WA` | Polish game developer |
| PZU | `pzu` | `PZU.WA` | Polish insurer |
| PKN Orlen | `pkn` | `PKN.WA` | Polish oil & gas |
| KGHM | `kgh` | `KGH.WA` | Polish mining |

### Indices

| Index | Stooq | Yahoo | Description |
|-------|-------|-------|-------------|
| S&P 500 | `^spx` | `^GSPC` | US large cap |
| NASDAQ | `^ixic` | `^IXIC` | US tech |
| WIG20 | `wig20` | `^WIG20` | Polish blue chip |

### Currency Pairs

| Pair | Stooq | NBP (component) | Yahoo |
|------|-------|-----------------|-------|
| USD/PLN | `usdpln` | `USD` (vs PLN) | `USDPLN=X` |
| EUR/PLN | `eurpln` | `EUR` (vs PLN) | `EURPLN=X` |
| EUR/USD | `eurusd` | N/A | `EURUSD=X` |

---

## Common Ticker Patterns

### Pattern Recognition for Routing

The unified fetcher uses these patterns to auto-route:

1. **Lowercase 2-4 letters** → Likely Polish stock → Try Stooq
   - Examples: `pko`, `cdr`, `pzu`

2. **Uppercase 1-5 letters** → Likely US stock → Try Yahoo
   - Examples: `AAPL`, `MSFT`, `GOOGL`

3. **6 uppercase letters** → Likely currency pair → Try Stooq
   - Examples: `USDPLN`, `EURUSD`

4. **3 uppercase letters (USD, EUR, etc.)** → Likely NBP currency → Try NBP
   - Examples: `USD`, `EUR`, `GBP`

5. **Starts with ^** → Likely index → Try Yahoo
   - Examples: `^GSPC`, `^IXIC`

6. **Contains .XX suffix** → International stock → Try Yahoo
   - Examples: `PKO.WA`, `ASML.AS`

7. **Short uppercase (2-10 chars)** → Could be FRED series → Try FRED
   - Examples: `GDP`, `UNRATE`, `CPIAUCSL`

---

## Ticker Lookup Resources

### Polish Market

- **GPW (Warsaw Stock Exchange)**: https://www.gpw.pl/spolki
- **Stooq Symbol List**: https://stooq.pl/t/?i=528
- Search format: Company name → Stooq ticker

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

### Polish Stocks: Stooq vs Yahoo

**Problem**: Same company, different tickers

**Solution**:
- For Stooq: Use lowercase, no suffix (`pko`)
- For Yahoo: Use uppercase + `.WA` suffix (`PKO.WA`)
- Unified fetcher handles automatically

### Currency Pairs: Direction Matters

**NBP API**: Always quotes **foreign currency per 1 PLN**
- `USD` from NBP = How many USD per PLN
- Returns mid rate, bid/ask for table C

**Stooq/Yahoo**: Standard market convention
- `USDPLN` = How many PLN per 1 USD
- This is opposite of some NBP interpretations

### Index Symbols: Caret Prefix

**With caret (^)**:
- Yahoo Finance standard: `^GSPC`, `^IXIC`
- Some Stooq indices: `^spx`, `^dji`

**Without caret**:
- Polish indices on Stooq: `wig20`, `mwig40`
- Yahoo Polish indices: `^WIG20`, `^MWIG40`

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

**Stooq**:
```python
# Valid
'pko'           # Lowercase
'wig20'         # Lowercase index
'^spx'          # Index with caret
'usdpln'        # Currency pair

# Invalid
'pko.pl'        # .pl suffix causes error
'PKO'           # May work but lowercase preferred
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

# Polish stock → Lowercase for Stooq
'PKO' → 'pko' (when routed to Stooq)

# US stock → Uppercase for Yahoo
'aapl' → 'AAPL' (when routed to Yahoo)

# Remove .pl suffix for Stooq
'pko.pl' → 'pko'

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
| Polish stock price | Stooq | `pko` | Lowercase, no suffix |
| US stock price | Yahoo | `AAPL` | Uppercase |
| Polish stock (Yahoo) | Yahoo | `PKO.WA` | Uppercase + .WA |
| S&P 500 | Yahoo | `^GSPC` | Caret prefix |
| USD/PLN rate | Stooq or NBP | `usdpln` or `USD` | Stooq=pair, NBP=currency |
| US GDP | FRED | `GDP` | Exact series ID |
| mWIG40 index | Stooq | `mwig40` | Lowercase |
| By ISIN | Yahoo Direct | `PLXTRDM00011` | Auto-converts to ticker |
| Dividends & splits | Yahoo Direct | `XTB.WA` | Use `events=div,splits` |

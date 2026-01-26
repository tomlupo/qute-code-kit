# Security Master Schema

Documentation for the `security_master.csv` file and `TickerRegistry` service.

## Overview

The security master is a single CSV file that serves as the source of truth for instrument identification and cross-source ticker mappings. It enables:

- Unified lookup by any identifier (uid, ISIN, ticker)
- Cross-source ticker conversion (Yahoo, Stooq, Bloomberg, FRED)
- Auto-discovery of Yahoo tickers from ISINs

**Location**: `.claude/skills/market-data-fetcher/data/security_master.csv`

## Schema

| Column | Type | Required | Description | Example |
|--------|------|----------|-------------|---------|
| `uid` | string | **Yes** | Universal ID - primary key | `isin_PLXTRDM00011`, `idx_WIG20`, `fx_USDPLN` |
| `isin` | string | No | ISIN code (if applicable) | `PLXTRDM00011` |
| `name` | string | No | Instrument name | `XTB` |
| `instrument_type` | enum | No | Type: equity, index, currency, bond, commodity, etf | `equity` |
| `country` | string | No | ISO country code | `PL` |
| `exchange` | string | No | Primary exchange | `WSE` |
| `ticker_bloomberg` | string | No | Bloomberg ticker | `XTB PW Equity` |
| `ticker_yahoo` | string | No | Yahoo Finance ticker | `XTB.WA` |
| `ticker_stooq` | string | No | Stooq ticker (lowercase) | `xtb` |
| `ticker_fred` | string | No | FRED series ID | - |
| `sector` | string | No | Sector classification | `Technology` |
| `currency` | string | No | Trading currency | `PLN` |
| `mapping_source` | string | No | How mapping was obtained | `manual`, `yahoo_api` |
| `last_updated` | datetime | No | When mapping was verified | `2026-01-09` |

## UID Conventions

The `uid` (Universal ID) is the primary key. Format conventions:

| Instrument Type | UID Format | Example |
|-----------------|------------|---------|
| Equity (with ISIN) | `isin_{ISIN}` | `isin_PLXTRDM00011` |
| Index | `idx_{NAME}` | `idx_WIG20` |
| Currency pair | `fx_{PAIR}` | `fx_USDPLN` |
| Bond | `bond_{ISIN}` | `bond_US912828YM28` |
| Commodity | `cmd_{NAME}` | `cmd_GOLD` |
| Rate | `rate_{NAME}` | `rate_WIBOR3M` |

## TickerRegistry Usage

### Basic Usage

```python
from ticker_registry import TickerRegistry

# Initialize (loads from default CSV path)
registry = TickerRegistry()

# Lookup by any identifier
security = registry.get_security('PLXTRDM00011')  # By ISIN
security = registry.get_security('XTB.WA')        # By Yahoo ticker
security = registry.get_security('xtb')           # By Stooq ticker
security = registry.get_security('idx_WIG20')     # By uid

# Access properties
print(security.name)                    # 'XTB'
print(security.isin)                    # 'PLXTRDM00011'
print(security.get_ticker('yahoo'))     # 'XTB.WA'
print(security.get_ticker('stooq'))     # 'xtb'
```

### Ticker Conversion

```python
from ticker_registry import TickerRegistry, convert_ticker

registry = TickerRegistry()

# Convert between formats
yahoo_ticker = registry.convert_ticker('PLXTRDM00011', to_source='yahoo')  # 'XTB.WA'
stooq_ticker = registry.convert_ticker('XTB.WA', to_source='stooq')        # 'xtb'

# Convenience functions (use default registry)
from ticker_registry import isin_to_yahoo, isin_to_stooq, ticker_to_isin

yahoo = isin_to_yahoo('PLXTRDM00011')  # 'XTB.WA'
stooq = isin_to_stooq('PLXTRDM00011')  # 'xtb'
isin = ticker_to_isin('XTB.WA')        # 'PLXTRDM00011'
```

### Batch Operations

```python
registry = TickerRegistry()

# Convert multiple tickers
isins = ['PLXTRDM00011', 'PLCCC0000016', 'PLBSK0000017']
yahoo_tickers = registry.convert_tickers_batch(isins, to_source='yahoo')
# {'PLXTRDM00011': 'XTB.WA', 'PLCCC0000016': 'CCC.WA', 'PLBSK0000017': 'ING.WA'}
```

### Auto-Discovery

```python
registry = TickerRegistry()

# Discover Yahoo tickers for ISINs not in registry
discovered = registry.discover_missing_yahoo_tickers(['US0378331005', 'GB0002634946'])
# {'US0378331005': 'AAPL', 'GB0002634946': 'BA.L'}

# Discover for all ISINs missing Yahoo ticker in registry
discovered = registry.discover_missing_yahoo_tickers()
```

### Adding New Entries

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

# Add ticker to existing security
registry.add_ticker_mapping('PLXTRDM00011', 'bloomberg', 'XTB PW Equity')

# Export to DataFrame
df = registry.to_dataframe()
```

## Instrument Types

| Type | Description | Examples |
|------|-------------|----------|
| `equity` | Listed stocks | XTB, CCC, PKO |
| `index` | Market indices | WIG20, S&P 500 |
| `currency` | FX pairs | USD/PLN, EUR/USD |
| `bond` | Fixed income | Government bonds, corporate bonds |
| `commodity` | Physical commodities | Gold, Oil |
| `etf` | Exchange-traded funds | SPY, QQQ |

## Ticker Format Reference

| Source | Format | Example |
|--------|--------|---------|
| Yahoo Finance | Uppercase + exchange suffix | `XTB.WA`, `AAPL`, `^GSPC` |
| Stooq | Lowercase, no suffix | `xtb`, `pko`, `wig20` |
| Bloomberg | Uppercase + type suffix | `XTB PW Equity`, `MWIG40 Index` |
| FRED | Series ID | `GDP`, `UNRATE` |

## Data Sources for Mappings

| Source | Method | Coverage |
|--------|--------|----------|
| `manual` | Hand-curated | Full control, any format |
| `yahoo_api` | Auto-discovered via Yahoo search | ISIN → Yahoo ticker |
| `csv` | Loaded from CSV | Existing entries |

## File Location

Default path: `.claude/skills/market-data-fetcher/data/security_master.csv`

Custom path:
```python
registry = TickerRegistry(csv_path=Path('/custom/path/master.csv'))
```

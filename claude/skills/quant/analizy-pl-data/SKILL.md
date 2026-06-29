---
name: analizy-pl-data
description: This skill provides programmatic access to Polish investment fund data from analizy.pl, the leading Polish fund data aggregator. Use this skill when working with Polish investment funds, analyzing fund performance, comparing funds, downloading portfolio PDFs, or researching the Polish asset management industry. The skill covers 2,133 funds across FIO (Polish open-end), FIZ (Polish closed-end), and FZG (foreign UCITS) fund types, plus portfolio download URLs for 26 TFI providers.
---

# Analizy.pl Fund Data Retrieval Skill

## Purpose

This skill provides programmatic access to Polish investment fund data from analizy.pl, which is the leading Polish fund data aggregator. It enables retrieval of historical quotations, performance metrics, rankings, and fund metadata for 2,100+ investment funds across three product types.

**Fund Universe** (2,133 total funds):
- **FIO** (Fundusze Inwestycyjne Otwarte) - 488 Polish open-end funds
- **FIZ** (Fundusze Inwestycyjne Zamknięte) - 187 Polish closed-end funds
- **FZG** (Fundusze Zagraniczne) - 1,272 foreign funds (Luxembourg UCITS)

**Use this skill when:**
- Working with Polish investment fund data
- Analyzing fund performance or building rankings
- Comparing funds across peer groups
- Downloading portfolio composition PDFs from TFIs
- Mapping TFI companies to analizy.pl fund codes
- Researching Polish asset management industry
- Building fund screening or selection tools

## Quick Start

### Get Historical Quotations
```python
import requests

url = "https://www.analizy.pl/api/quotation/fio/SKR54"
response = requests.get(url, timeout=60)
data = response.json()
prices = data['series'][0]['price']  # [{date, value}, ...]
```

### Get Performance Metrics
```python
import pandas as pd

url = "https://www.analizy.pl/api/rate-of-return/fio/SKR54"
tables = pd.read_html(url)
performance_df = tables[0]  # Fund returns, peer average, ranking
```

### Scrape Fund Metadata (Listing Pages)
```python
from firecrawl import Firecrawl
from dotenv import load_dotenv

load_dotenv()
app = Firecrawl()

result = app.scrape(
    url="https://www.analizy.pl/fundusze-inwestycyjne-otwarte/notowania",
    formats=['markdown'],
    only_main_content=True
)
# Parse markdown to extract fund codes, names, peer groups, etc.
```

See `references/code-examples.md` for complete working examples.

## Available Data Sources

### 1. Portfolio PDF Downloads (Recommended for Holdings Data)

**Download portfolio composition reports directly:**
```
https://dokumenty.analizy.pl/pobierz/fi/{FUND_CODE}/SP/{DATE}
```

- `FUND_CODE`: Analizy.pl fund code (e.g., AIG02, PZU01, SKR01)
- `SP`: "Skład Portfela" (Portfolio Composition report type)
- `DATE`: Report date in YYYY-MM-DD format (quarter-end: 03-31, 06-30, 09-30, 12-31)

**Example URLs:**
```
https://dokumenty.analizy.pl/pobierz/fi/AIG02/SP/2025-09-30  # Rockbridge
https://dokumenty.analizy.pl/pobierz/fi/PZU01/SP/2025-09-30  # PZU
https://dokumenty.analizy.pl/pobierz/fi/SKR01/SP/2025-09-30  # Skarbiec
```

**Key insight:** Most TFIs return a single bulk PDF containing all subfunds under an umbrella code. Use `config/provider_mapping.json` for verified umbrella codes per TFI.

**Automated download script:**
```bash
# Download all providers for a quarter
uv run python scripts/datasets/fund_holdings/download_fund_holdings.py --date 2025-12-31

# Download specific provider
uv run python scripts/datasets/fund_holdings/download_fund_holdings.py --provider rockbridge --date 2025-12-31
```

**Related skill:** Use the `pdf-extraction` skill to parse downloaded PDFs into standardized data.

### 2. JSON APIs (Recommended for Price/Performance Data)

**Historical Quotations:**
- `GET https://www.analizy.pl/api/quotation/{fio|fzg}/{FUND_CODE}`
- Returns: Complete daily NAV time series (no date filtering supported)
- **Limitation**: API ignores date range params - always returns full history
- See: `references/api-reference.md`

**Performance Metrics:**
- `GET https://www.analizy.pl/api/rate-of-return/{fio|fzg}/{FUND_CODE}`
- Returns: Fund returns, peer group average, rankings across all periods
- Periods: 1M, 3M, 6M, YTD, 12M, 24M, 36M, 48M, 60M, 120M

### 2. Listing Pages (Recommended for Bulk Metadata)

**Fast bulk extraction** via Firecrawl API:
- FIO: `https://www.analizy.pl/fundusze-inwestycyjne-otwarte/notowania` (49 pages)
- FIZ: `https://www.analizy.pl/fundusze-inwestycyjne-zamkniete/notowania` (19 pages)
- FZG: `https://www.analizy.pl/fundusze-zagraniczne/notowania` (146 pages)

**Available fields:** code, name, url, peer_group, tfi_company, currency, nav_value, valuation_date, ytd_return

See: `references/fund-type-specs.md` for complete field availability matrix

### 3. Profile Pages (For Detailed Fund Information)

**Individual fund pages** (HTML scraping required):
- `https://www.analizy.pl/fundusze-inwestycyjne-otwarte/{CODE}/{SLUG}`

**Additional fields:** ISIN, inception_date, sharpe_ratio, information_ratio, std_dev, fund_manager, portfolio_holdings

See: `references/regex-patterns.md` for HTML extraction patterns

## Master Scraping Workflow

### Overview

The master scraping workflow uses **Firecrawl API v4.8.0** to efficiently extract fund metadata from listing pages.

**Performance:** Successfully scraped 1,944 funds (FIO: 485, FIZ: 187, FZG: 1,272) with 11 core fields in ~22 minutes.

### Firecrawl API v4.8.0 Setup

```python
from firecrawl import Firecrawl
from dotenv import load_dotenv

load_dotenv()  # Loads FIRECRAWL_API_KEY from .env
app = Firecrawl()  # Reads API key from environment

result = app.scrape(
    url=url,
    formats=['markdown'],
    only_main_content=True
)
markdown = result.markdown  # Document object with .markdown attribute
```

**Environment Setup:**
```bash
# Install dependencies
uv add firecrawl-py python-dotenv pandas

# Create .env file in project root
echo "FIRECRAWL_API_KEY=your-api-key-here" >> .env
```

**Rate Limiting (Critical):**
- **Free tier**: 11 requests/minute
- **Required delay**: 6.0 seconds between requests
- **Calculation**: 60s ÷ 11 req = 5.45s minimum, use 6.0s for safety

### Implementation Pattern

The scraping workflow is documented in `references/code-examples.md` with complete, portable code examples that can be copied and adapted for any project.

### Performance Metrics

| Fund Type | Pages | Time | Funds | Rate |
|-----------|-------|------|-------|------|
| FIO | 49 | ~5 min | 485 | ~10/page |
| FIZ | 19 | ~2 min | 187 | ~10/page |
| FZG | 146 | ~15 min | 1,272 | ~9/page |
| **All** | **214** | **~22 min** | **1,944** | **~9/page** |

## Data Schema

### Extracted Fields (11 Total)

1. `code` - Fund code (primary key)
2. `name` - Full fund name
3. `type` - Fund type (fio/fiz/fzg)
4. `groupname` - Peer group classification (CRITICAL for analysis)
5. `tfi_company` - Management company
6. `currency` - NAV currency (PLN, EUR, USD, etc.)
7. `url` - Fund profile page URL
8. `information_source` - "analizy.pl listing scraper"
9. `nav_value` - Current NAV per unit
10. `valuation_date` - Latest valuation date (DD.MM.YYYY)
11. `valuation_frequency` - FIZ only (miesięczna/kwartalna)

### Field Completeness (from listing pages)

- code, name, type, url, information_source: 100%
- currency: 75.1%
- groupname: 74.0%
- valuation_date: 75.1%
- nav_value: 14.4%
- tfi_company: 9.6% (FIO/FIZ only, empty for FZG)
- valuation_frequency: 8.2% (FIZ only)

## Data Consolidation

After scraping separate fund types, consolidate into single dataset:

**Process:**
1. Load FIO, FIZ, FZG CSV files
2. Normalize all to 11-field master schema
3. Rename 'group' → 'groupname' if needed (backward compatibility)
4. Concatenate and deduplicate by code
5. Validate completeness and show statistics
6. Save consolidated dataset

See `references/code-examples.md` for complete consolidation code.

## Working with Different Fund Types

Each fund type has distinct characteristics and data availability.

**FIO (Open-End Funds):**
- 488 funds, daily NAV, Polish domicile
- Best data availability (Good Practices scores, portfolio holdings)

**FIZ (Closed-End Funds):**
- 187 funds, monthly/quarterly valuation, limited liquidity
- Unique fields: valuation_frequency (miesięczna/kwartalna)

**FZG (Foreign Funds):**
- 1,272 funds, Luxembourg UCITS, multiple currencies/unit classes
- Code format: `{PROVIDER}{NUM}_{CLASS}_{CURRENCY}` (e.g., `FTI068_A_USD`)

See: `references/fund-type-specs.md` for detailed specifications

## Common Operations

### Extract Fund Metadata from Listing Pages

Use the parsing functions from `references/extraction-patterns.md`:

```python
from firecrawl import Firecrawl
import time

app = Firecrawl()
all_funds = []

for page in range(1, total_pages + 1):
    result = app.scrape(url=page_url, formats=['markdown'])
    page_funds = parse_listing_page_markdown(result.markdown, 'fio')
    all_funds.extend(page_funds)
    time.sleep(6.0)  # CRITICAL: Rate limiting
```

See: `references/extraction-patterns.md` for complete parsing functions

### Extract Metadata from Profile Pages

For detailed metadata (ISIN, Sharpe ratio, inception date):

```python
import re
import requests

def extract_fund_metadata(fund_code: str, html_text: str):
    """Extract metadata from profile page HTML."""
    # See references/regex-patterns.md for all patterns
    peer_group_pattern = r'Nazwa\s+grupy</p>\s*<p[^>]*class="[^"]*basicValue[^"]*"[^>]*>\s*<span[^>]*></span>([^<]+)</p>'
    match = re.search(peer_group_pattern, html_text)
    peer_group = match.group(1).strip() if match else None
    # ... extract other fields
    return metadata
```

See: `references/regex-patterns.md` for all extraction patterns

### Batch Processing Best Practices

1. **Rate Limiting:** Always add delays between requests
2. **Error Handling:** Wrap in try-except, log failures
3. **Progress Tracking:** Print status for long-running operations
4. **Checkpoint Saving:** Save intermediate results every N records

See: `references/extraction-patterns.md` for detailed batch processing examples

## Recommended Strategy: Two-Stage Approach

**Stage 1: Scrape Listing Pages** (~22 min for all 1,944 funds)
- Get core metadata: code, name, peer_group, currency, etc.
- Build complete fund directory

**Stage 2: Filter & Detail Scrape** (as needed)
- Filter to funds of interest using Stage 1 data
- Scrape detail pages only for filtered subset
- Get comprehensive metadata: ISIN, Sharpe ratio, holdings

**Example:**
```python
# Stage 1: Quick directory (22 min)
all_funds_df = scrape_all_listing_pages()

# Stage 2: Filter and detail (2-3 min for ~50 funds)
equity_funds = all_funds_df[
    all_funds_df['groupname'].str.contains('akcji polskich', na=False)
]
detail_metadata = scrape_detail_pages(equity_funds['url'].tolist())
```

See: `references/fund-type-specs.md` for field availability matrix

## Troubleshooting

**Common Issues:**

1. **Firecrawl Rate Limit:** Increase DELAY_BETWEEN_PAGES to 6.0 seconds
2. **No funds extracted:** Use regex pattern with `[^\)\"]+` (handles title attributes)
3. **Unicode errors on Windows:** Use ASCII equivalents or configure UTF-8
4. **API 404 errors:** Verify fund code and correct endpoint (fio vs fzg)
5. **Peer group extraction fails:** Use `basicValue` pattern from `references/regex-patterns.md`

See: `references/troubleshooting.md` for complete troubleshooting guide

## Reference Documentation

For detailed information, consult these reference files:

- **`references/api-reference.md`** - API endpoints, response structures, field definitions
- **`references/provider-mapping.md`** - TFI → umbrella code mapping for PDF downloads
- **`references/regex-patterns.md`** - All regex patterns for data extraction
- **`references/fund-type-specs.md`** - FIO/FIZ/FZG specifications and characteristics
- **`references/extraction-patterns.md`** - Parsing functions and batch processing patterns
- **`references/code-examples.md`** - Complete working code examples
- **`references/troubleshooting.md`** - Solutions to common issues

## Rate Limiting & Best Practices

1. **Add delays:** 6s for Firecrawl (listing pages), 2-4s jitter for direct HTTP (APIs)
2. **Batch pauses:** 30s rest every 50 requests for bulk downloads
3. **Cache responses:** Save API responses to avoid re-fetching
4. **Handle errors:** Use try-except blocks and log failures
5. **Set User-Agent:** Use descriptive user-agent string for HTTP requests
6. **Timeout:** Use 60+ second timeouts for large API responses
7. **Validate data:** Check field completeness and HTML entity issues

### Smart Scraping Pattern (Bulk Quotations)

```python
import random
import time

BATCH_SIZE = 50
BATCH_PAUSE = 30  # seconds

for idx, fund in enumerate(funds, 1):
    # Batch pause every 50 funds
    if idx > 1 and (idx - 1) % BATCH_SIZE == 0:
        print(f"Pausing {BATCH_PAUSE}s after {idx - 1} downloads...")
        time.sleep(BATCH_PAUSE)

    # Fetch data
    data = fetch_quotation(fund['code'], fund['type'])
    save_json(fund['code'], data)

    # Random jitter (2-4s)
    time.sleep(random.uniform(2, 4))
```

**Estimated times:**
- 485 FIO funds: ~32 minutes
- 187 FIZ funds: ~12 minutes
- 1,272 FZG funds: ~75 minutes

## Provider Mapping (TFI → Fund Codes)

The `config/provider_mapping.json` file maps TFI companies to their verified umbrella fund codes:

**Sample entries:**
| Provider | TFI Company | Umbrella Code | Notes |
|----------|-------------|---------------|-------|
| rockbridge | Rockbridge TFI | AIG02 | Rockbridge Neo umbrella |
| pzu | TFI PZU | PZU01 | Bulk report with all subfunds |
| skarbiec | Skarbiec TFI | SKR01 | SKARBIEC + BPS subfunds |
| goldmansachs | Goldman Sachs TFI | ING02 | 35 funds, 5.2MB report |
| pko | PKO TFI | PCS05 | 34 funds |
| pekao | Pekao TFI | PIO01 | 32 funds, 6.4MB report |

**Full mapping:** See `config/provider_mapping.json` for all 26 verified providers with:
- `provider_id`: Folder name for PDFs
- `umbrella_codes[]`: Verified download codes
- `umbrella_names[]`: Fund names covered
- `download_verified`: Whether URL was tested
- `notes`: Provider-specific quirks

## Summary

✅ **Portfolio PDFs:** Download holdings data via documented URL pattern
✅ **Price Data API:** Historical NAV time series
✅ **Performance API:** Returns & rankings across all periods
✅ **Listing Pages:** Fast bulk metadata extraction (Firecrawl)
✅ **Profile Pages:** Detailed metadata (HTML scraping)
✅ **Provider Mapping:** 26 TFIs with verified download codes
✅ **Coverage:** 1,944 Polish investment funds, 10+ years of history
✅ **Data Quality:** Comprehensive, validated, daily updates
✅ **Master Workflow:** 22 minutes for complete fund directory

**Key Insight:** Use listing pages for bulk extraction (Stage 1), then detail pages for selective deep analysis (Stage 2). Portfolio PDFs can be downloaded directly via the documented URL pattern. This multi-source approach provides comprehensive fund data coverage.

**Related skills:**
- `pdf-extraction`: Parse downloaded PDFs into standardized holdings data

**This skill is standalone and can be used in any project requiring Polish fund data.**

# Data Extraction Patterns

This document contains patterns and best practices for extracting fund data from both markdown (listing pages) and HTML (profile pages).

## Markdown Structure (Firecrawl Output)

Firecrawl returns listing pages as **markdown**, not HTML.

### Typical Structure

```markdown
[Profil funduszu: FUND_NAME](https://www.analizy.pl/fundusze-inwestycyjne-{type}/{CODE}/{slug})

Akcyjne  ← Category badge

## FUND_NAME

akcji polskich uniwersalne  ← Peer group
PKO TFI S.A.  ← TFI company

PLN
315.43 PLN  ← NAV value
Wartość certyfikatu

31.10.2025  ← Valuation date

+29.6%  ← YTD return
YTD
```

---

## Listing Page Extraction Functions

### Complete Listing Page Parser

```python
import re
from typing import List, Dict, Optional

def parse_listing_page_markdown(markdown: str, fund_type: str) -> List[Dict]:
    """
    Parse listing page markdown to extract fund metadata.

    Args:
        markdown: Markdown content from Firecrawl scrape
        fund_type: 'fio', 'fiz', or 'fzg'

    Returns:
        List of fund dictionaries with extracted fields
    """
    funds = []

    # Map fund type to URL pattern
    url_patterns = {
        'fio': 'fundusze-inwestycyjne-otwarte',
        'fiz': 'fundusze-inwestycyjne-zamkniete',
        'fzg': 'fundusze-zagraniczne'
    }

    url_segment = url_patterns[fund_type]

    # Extract fund headers (code, name, URL)
    header_pattern = rf'\[Profil funduszu: ([^\]]+)\]\((https://www\.analizy\.pl/{url_segment}/([A-Z0-9_]+)/[^\)\"]+)'

    matches = re.finditer(header_pattern, markdown)

    for match in matches:
        name = match.group(1).strip()
        url = match.group(2)
        code = match.group(3)

        # Extract content block for this fund (between this match and next)
        start_pos = match.end()
        # Find next fund or end of string
        next_match = re.search(r'\[Profil funduszu:', markdown[start_pos:])
        end_pos = start_pos + next_match.start() if next_match else len(markdown)

        content_block = markdown[start_pos:end_pos]

        # Extract additional fields from content block
        fund_data = {
            'code': code,
            'name': name,
            'type': fund_type,
            'url': url,
            'information_source': 'analizy.pl listing scraper',
            'groupname': extract_peer_group(content_block),
            'tfi_company': extract_tfi_company(content_block) if fund_type != 'fzg' else None,
            'currency': extract_currency(content_block),
            'nav_value': extract_nav_value(content_block),
            'valuation_date': extract_valuation_date(content_block),
            'ytd_return': extract_ytd_return(content_block)
        }

        # FIZ-specific field
        if fund_type == 'fiz':
            fund_data['valuation_frequency'] = extract_valuation_frequency(content_block)

        funds.append(fund_data)

    return funds


def extract_peer_group(content: str) -> Optional[str]:
    """Extract peer group from content block."""
    lines = content.split('\n')

    SKIP_BADGES = ['Akcyjne', 'Dłużne', 'Mieszane', 'Pozostałe', 'Absolute return']
    KEYWORDS = ['akcji', 'obligacji', 'papierów', 'mieszane', 'absolutnej',
                'dłużnych', 'polskich', 'zagranicznych', 'globalnych', 'stopy',
                'rynku', 'wzrostu', 'korporacyjnych', 'skarbowych']

    found_heading = False

    for line in lines[:25]:
        line = line.strip()

        if not line or len(line) < 8:
            continue
        if line.startswith('[') or line.startswith('http'):
            continue
        if line in SKIP_BADGES:
            continue

        if line.startswith('##'):
            found_heading = True
            continue

        if found_heading:
            if any(kw in line.lower() for kw in KEYWORDS):
                return line

    return None


def extract_tfi_company(content: str) -> Optional[str]:
    """Extract TFI company name."""
    lines = content.split('\n')

    for line in lines[:30]:
        line = line.strip()

        if 'TFI' in line or 'Towarzystwo' in line:
            if 10 < len(line) < 80:
                if not any(skip in line for skip in ['Nazwa towarzystwa', 'firma', 'opłata']):
                    return line

    return None


def extract_currency(content: str) -> str:
    """Extract currency code."""
    match = re.search(r'\b(PLN[DP]?|EUR|USD)\b', content)

    if match:
        currency_raw = match.group(1)
        return currency_raw[:3] if currency_raw.startswith('PLN') else currency_raw

    return 'PLN'


def extract_nav_value(content: str) -> Optional[str]:
    """Extract NAV value."""
    nav_match = re.search(r'([\d\s]+,\d+)\s*PLN', content)
    if nav_match:
        return nav_match.group(1).replace(' ', '').strip()
    return None


def extract_valuation_date(content: str) -> Optional[str]:
    """Extract valuation date (DD.MM.YYYY)."""
    date_match = re.search(r'\b(\d{2}\.\d{2}\.\d{4})\b', content)
    if date_match:
        return date_match.group(1)
    return None


def extract_ytd_return(content: str) -> Optional[str]:
    """Extract YTD return."""
    ytd_match = re.search(r'([+-]?\d+,\d+)%\s*YTD', content)
    if ytd_match:
        return ytd_match.group(1)
    return None


def extract_valuation_frequency(content: str) -> Optional[str]:
    """Extract valuation frequency (FIZ only)."""
    if 'miesięczna' in content:
        return 'miesięczna'
    elif 'kwartalna' in content:
        return 'kwartalna'
    return None
```

---

## HTML Profile Page Extraction

### HTML Structure

Fund profile pages contain a `<section class="productSectionInfo">` with metadata in label-value pairs:

```html
<section class="productSectionInfo">
    <div class="col">
        <div>
            <p class="basicLabel">Nazwa grupy</p>
            <p class="basicValue">
                <span class="iconDot shareFundBgColor"></span>akcji globalnych rynków rozwiniętych
            </p>
        </div>
        <div>
            <p class="basicLabel">Poziom ryzyka (SRI)</p>
            <p class="basicValue">Wysokie</p>
        </div>
        <div>
            <p class="basicLabel">Benchmark</p>
            <p class="basicValue">90% MSCI ACWI Index + 10% WIBOR O/N</p>
        </div>
    </div>
</section>
```

### Complete HTML Extraction Function

```python
import re
import requests
from typing import Dict, Optional

def extract_fund_metadata(fund_code: str, html_text: str) -> Dict[str, Optional[str]]:
    """
    Extract core metadata from fund profile page HTML.

    Returns dict with: code, peer_group_detailed, tfi_company,
    mgmt_fee_current, first_valuation_date
    """

    metadata = {'code': fund_code}

    # 1. Peer group - MOST RELIABLE PATTERN
    peer_group_pattern = r'Nazwa\s+grupy</p>\s*<p[^>]*class="[^"]*basicValue[^"]*"[^>]*>\s*<span[^>]*></span>([^<]+)</p>'
    match = re.search(peer_group_pattern, html_text, re.IGNORECASE)
    if match:
        peer_group = match.group(1).strip().replace('&nbsp;', ' ')
        metadata['peer_group_detailed'] = peer_group
    else:
        metadata['peer_group_detailed'] = None

    # 2. TFI company
    tfi_pattern = r'Nazwa\s+towarzystwa[^>]*>[^>]*>([^<]+)<'
    match = re.search(tfi_pattern, html_text)
    metadata['tfi_company'] = match.group(1).strip() if match else None

    # 3. Management fee
    fee_pattern = r'Aktualna\s+opłata\s+stała[^>]*>[^>]*>([\d,]+)\s*%'
    match = re.search(fee_pattern, html_text)
    metadata['mgmt_fee_current'] = match.group(1).replace(',', '.') if match else None

    # 4. First valuation date
    date_pattern = r'Data\s+pierwszej\s+wyceny[^>]*>[^>]*>(\d{2}\.\d{2}\.\d{4})'
    match = re.search(date_pattern, html_text)
    metadata['first_valuation_date'] = match.group(1) if match else None

    return metadata


def fetch_fund_metadata(fund_code: str, fund_url: str) -> Dict:
    """Fetch and extract metadata for a single fund."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    response = requests.get(fund_url, headers=headers, timeout=30)
    response.raise_for_status()

    return extract_fund_metadata(fund_code, response.text)
```

---

## Batch Extraction Best Practices

### Rate Limiting

```python
import time

# For listing pages (Firecrawl)
DELAY_BETWEEN_PAGES = 6.0  # 6 seconds (Firecrawl free tier: 11 req/min)

for page in range(1, total_pages + 1):
    result = app.scrape(url=url, formats=['markdown'], only_main_content=True)
    funds = parse_listing_page_markdown(result.markdown, fund_type)
    all_funds.extend(funds)

    time.sleep(DELAY_BETWEEN_PAGES)

# For detail pages (direct HTTP)
DELAY_BETWEEN_REQUESTS = 2.0  # 2 seconds

for fund in funds_list:
    metadata = fetch_fund_metadata(fund['code'], fund['url'])
    results.append(metadata)

    time.sleep(DELAY_BETWEEN_REQUESTS)
```

### Error Handling

```python
errors = []

for fund in funds_list:
    try:
        metadata = fetch_fund_metadata(fund['code'], fund['url'])
        results.append(metadata)
    except requests.RequestException as e:
        errors.append({'code': fund['code'], 'error': str(e)})
        print(f"[!] Error fetching {fund['code']}: {e}")

    time.sleep(2)

# Save errors for later retry
if errors:
    pd.DataFrame(errors).to_csv('scraping_errors.csv', index=False)
```

### Progress Tracking

```python
total = len(funds_list)

for idx, fund in enumerate(funds_list, 1):
    print(f"[{idx}/{total}] {fund['code']}...", end=" ")

    metadata = fetch_fund_metadata(fund['code'], fund['url'])

    if metadata['peer_group_detailed']:
        print(f"[OK] {metadata['peer_group_detailed'][:50]}")
    else:
        print("[FAIL] No peer group")

    time.sleep(2)
```

### Checkpoint Saving

```python
import pandas as pd

CHECKPOINT_INTERVAL = 50  # Save every 50 funds

for idx, fund in enumerate(funds_list, 1):
    metadata = fetch_fund_metadata(fund['code'], fund['url'])
    results.append(metadata)

    # Save checkpoint
    if idx % CHECKPOINT_INTERVAL == 0:
        df = pd.DataFrame(results)
        df.to_csv(f'checkpoint_{idx}.csv', index=False)
        print(f"Checkpoint saved at {idx} funds")

    time.sleep(2)
```

---

## Validation and Quality Checks

### Field Completeness Check

```python
import pandas as pd

def check_field_completeness(df: pd.DataFrame) -> pd.DataFrame:
    """Check completeness of extracted fields."""
    completeness = {}

    for col in df.columns:
        non_null = df[col].notna().sum()
        total = len(df)
        pct = (non_null / total) * 100
        completeness[col] = f"{non_null}/{total} ({pct:.1f}%)"

    return pd.DataFrame(completeness, index=['Completeness']).T


# Usage
df = pd.DataFrame(results)
print(check_field_completeness(df))
```

### HTML Entity Check

```python
def check_html_entities(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Check for HTML entities in extracted text."""
    if column not in df.columns:
        return pd.DataFrame()

    # Find rows with HTML entities
    has_entities = df[column].str.contains('&#', na=False)

    if has_entities.any():
        print(f"Warning: {has_entities.sum()} rows contain HTML entities in {column}")
        return df[has_entities][[column]]
    else:
        print(f"[OK] No HTML entities found in {column}")
        return pd.DataFrame()


# Usage
check_html_entities(df, 'peer_group_detailed')
```

### Length Validation

```python
def validate_field_lengths(df: pd.DataFrame, field_limits: dict) -> pd.DataFrame:
    """Validate field lengths against expected limits."""
    issues = []

    for field, max_length in field_limits.items():
        if field in df.columns:
            too_long = df[df[field].str.len() > max_length]
            if not too_long.empty:
                issues.append({
                    'field': field,
                    'count': len(too_long),
                    'max_found': df[field].str.len().max()
                })

    return pd.DataFrame(issues)


# Usage
field_limits = {
    'peer_group_detailed': 80,
    'tfi_company': 80,
    'code': 20,
    'currency': 5
}

issues = validate_field_lengths(df, field_limits)
if not issues.empty:
    print("Field length issues:")
    print(issues)
```

---

## Listing vs Detail Page Strategy

### When to Use Listing Pages

Use listing pages when you need:
- Fast extraction (100 funds per page, ~6 seconds per page)
- Core metadata fields (8-12 fields)
- Current NAV, returns, and peer group classification
- Complete fund directory building

### When to Use Detail Pages

Use detail pages when you need:
- Comprehensive metadata (25+ fields)
- ISIN codes for cross-referencing
- Risk metrics (Sharpe, information ratio, volatility)
- Fund manager information
- Portfolio composition (top 10 holdings)

### Recommended Two-Stage Workflow

**Stage 1: Scrape Listing Pages**
```python
# Quick directory build: ~22 minutes for all 1,944 funds
all_funds = scrape_all_listing_pages()  # Returns 8-12 fields per fund
```

**Stage 2: Filter and Detail Scrape**
```python
# Filter to funds of interest
df = pd.DataFrame(all_funds)
filtered = df[
    (df['groupname'].str.contains('akcji polskich', na=False)) &
    (df['ytd_return'].str.replace(',', '.').astype(float) > 10)
]

# Scrape detail pages for filtered subset only
for fund in filtered.itertuples():
    detail_metadata = fetch_fund_metadata(fund.code, fund.url)
    # Merge with listing data
```

**Example:** To analyze Polish equity funds with Sharpe > 1.0:
1. Scrape FIO listing pages → 488 funds with peer_group (~5 min)
2. Filter for `peer_group.contains('akcji polskich')` → 58 funds
3. Scrape detail pages for those 58 funds → Get Sharpe ratios (~2 min)
4. Final filter: Sharpe > 1.0 → 12 funds for portfolio

**Total time:** 7 minutes vs 16 minutes if scraping all detail pages first

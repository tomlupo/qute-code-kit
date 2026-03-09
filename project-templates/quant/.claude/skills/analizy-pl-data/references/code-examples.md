# Code Examples

This document contains complete, working code examples for common operations with analizy.pl fund data.

## Example 1: Get Historical Quotations for a Fund

Download complete daily NAV history from the quotation API.

```python
import requests
import json

# Get historical quotations for a fund
fund_code = "SKR54"
fund_type = "fio"  # or "fzg"

url = f"https://www.analizy.pl/api/quotation/{fund_type}/{fund_code}"
response = requests.get(url, timeout=60)
data = response.json()

# Extract price data
prices = data['series'][0]['price']

# Each price point has: {"date": "YYYY-MM-DD", "value": 123.45}
print(f"Total price points: {len(prices)}")
print(f"Latest: {prices[0]}")
print(f"Oldest: {prices[-1]}")

# Save to file
with open(f"data/{fund_code}_quotations.json", 'w') as f:
    json.dump(prices, f, indent=2)
```

**Note:** Response can be LARGE (50k+ tokens for funds with long history). Save to file immediately.

---

## Example 2: Get Performance Metrics

Retrieve calculated returns and peer rankings from the performance API.

```python
import pandas as pd

fund_code = "SKR54"
fund_type = "fio"

url = f"https://www.analizy.pl/api/rate-of-return/{fund_type}/{fund_code}"
tables = pd.read_html(url)
performance_df = tables[0]

# Table structure:
# - Columns: Period names (1M, 3M, 6M, YTD, 12M, etc.)
# - Row 0: Fund returns
# - Row 1: Peer group average
# - Row 2: Position (e.g., "2/58")

print("Fund returns:")
print(performance_df.iloc[0])

print("\nGroup average:")
print(performance_df.iloc[1])

print("\nPosition in peer group:")
print(performance_df.iloc[2])

# Extract specific period
ytd_return = performance_df.iloc[0]['YTD']
print(f"\nYTD return: {ytd_return}")
```

---

## Example 3: Scrape Fund Metadata from Listing Pages (Firecrawl)

Extract fund metadata from listing pages using Firecrawl v4.8.0.

```python
from firecrawl import Firecrawl
from dotenv import load_dotenv
import time
import pandas as pd
import re

# Load environment variables
load_dotenv()

# Initialize Firecrawl (reads FIRECRAWL_API_KEY from .env)
app = Firecrawl()

def parse_listing_page(markdown: str, fund_type: str):
    """Parse listing page markdown to extract funds."""
    funds = []

    # Map fund type to URL pattern
    url_patterns = {
        'fio': 'fundusze-inwestycyjne-otwarte',
        'fiz': 'fundusze-inwestycyjne-zamkniete',
        'fzg': 'fundusze-zagraniczne'
    }

    url_segment = url_patterns[fund_type]
    header_pattern = rf'\[Profil funduszu: ([^\]]+)\]\((https://www\.analizy\.pl/{url_segment}/([A-Z0-9_]+)/[^\)\"]+)'

    matches = re.finditer(header_pattern, markdown)

    for match in matches:
        funds.append({
            'code': match.group(3),
            'name': match.group(1).strip(),
            'url': match.group(2),
            'type': fund_type
        })

    return funds

# Scrape FIO listing pages
all_fio_funds = []
total_pages = 49  # FIO has 49 pages

for page in range(1, total_pages + 1):
    url = f"https://www.analizy.pl/fundusze-inwestycyjne-otwarte/notowania?page={page}" if page > 1 else "https://www.analizy.pl/fundusze-inwestycyjne-otwarte/notowania"

    print(f"Scraping page {page}/{total_pages}...")

    result = app.scrape(
        url=url,
        formats=['markdown'],
        only_main_content=True
    )

    page_funds = parse_listing_page(result.markdown, 'fio')
    all_fio_funds.extend(page_funds)

    print(f"  Found {len(page_funds)} funds")

    # CRITICAL: 6-second delay for rate limiting (11 req/min free tier)
    if page < total_pages:
        time.sleep(6.0)

# Save results
df = pd.DataFrame(all_fio_funds)
df.to_csv('fio_funds_directory.csv', index=False)

print(f"\nTotal FIO funds scraped: {len(all_fio_funds)}")
print(f"Saved to: fio_funds_directory.csv")
```

---

## Example 4: Batch Download Multiple Funds

Download data for multiple funds with rate limiting and error handling.

```python
import time
import requests
import json
from pathlib import Path

# Create output directory
output_dir = Path("data/quotations")
output_dir.mkdir(parents=True, exist_ok=True)

# List of fund codes to download
fund_codes = ['SKR54', 'PCS55', 'ALL91', 'PZU81']

results = {
    'success': [],
    'failed': []
}

for code in fund_codes:
    try:
        # Fetch quotation data
        url = f"https://www.analizy.pl/api/quotation/fio/{code}"
        response = requests.get(url, timeout=60)

        if response.status_code == 200:
            data = response.json()
            prices = data['series'][0]['price']

            # Save to file
            output_file = output_dir / f"{code}_quotations.json"
            with open(output_file, 'w') as f:
                json.dump(prices, f, indent=2)

            results['success'].append({
                'code': code,
                'count': len(prices),
                'file': str(output_file)
            })

            print(f"[OK] {code}: {len(prices)} quotations")
        else:
            results['failed'].append({
                'code': code,
                'error': f"HTTP {response.status_code}"
            })
            print(f"[FAIL] {code}: HTTP {response.status_code}")

    except Exception as e:
        results['failed'].append({
            'code': code,
            'error': str(e)
        })
        print(f"[ERROR] {code}: {str(e)}")

    # Rate limiting: 2-second delay between requests
    time.sleep(2)

# Summary
print(f"\n=== Summary ===")
print(f"Success: {len(results['success'])}")
print(f"Failed: {len(results['failed'])}")

if results['failed']:
    print("\nFailed downloads:")
    for item in results['failed']:
        print(f"  {item['code']}: {item['error']}")
```

---

## Example 5: Calculate Returns from Price Data

Compute returns from raw quotation data using pandas.

```python
import pandas as pd
import requests

# Fetch data
fund_code = "SKR54"
url = f"https://www.analizy.pl/api/quotation/fio/{fund_code}"
response = requests.get(url, timeout=60)
data = response.json()

# Convert to DataFrame
prices = pd.DataFrame(data['series'][0]['price'])
prices['date'] = pd.to_datetime(prices['date'])
prices = prices.sort_values('date').set_index('date')

# Calculate returns
prices['return_1d'] = prices['value'].pct_change()
prices['return_1m'] = prices['value'].pct_change(periods=21)  # ~21 trading days
prices['return_12m'] = prices['value'].pct_change(periods=252)  # ~252 trading days

# Calculate annualized volatility
daily_std = prices['return_1d'].std()
annual_vol = daily_std * (252 ** 0.5)

# Calculate Sharpe ratio (assuming 4% risk-free rate)
risk_free_rate = 0.04
avg_annual_return = prices['return_12m'].iloc[-1]  # Last 12-month return
sharpe = (avg_annual_return - risk_free_rate) / annual_vol

# Display results
latest = prices.iloc[-1]

print(f"Fund: {fund_code}")
print(f"Latest NAV: {latest['value']:.2f} PLN")
print(f"Daily return: {latest['return_1d']:.2%}")
print(f"1-month return: {latest['return_1m']:.2%}")
print(f"12-month return: {latest['return_12m']:.2%}")
print(f"Annual volatility: {annual_vol:.2%}")
print(f"Sharpe ratio: {sharpe:.2f}")

# Save processed data
prices.to_csv(f'{fund_code}_returns.csv')
```

---

## Example 6: Extract Metadata from Profile Page (HTML)

Scrape detailed metadata from individual fund profile pages.

```python
import re
import requests
from typing import Dict, Optional

def extract_fund_metadata(fund_code: str, html_text: str) -> Dict[str, Optional[str]]:
    """Extract metadata from fund profile page HTML."""

    metadata = {'code': fund_code}

    # Peer group
    peer_group_pattern = r'Nazwa\s+grupy</p>\s*<p[^>]*class="[^"]*basicValue[^"]*"[^>]*>\s*<span[^>]*></span>([^<]+)</p>'
    match = re.search(peer_group_pattern, html_text, re.IGNORECASE)
    if match:
        metadata['peer_group'] = match.group(1).strip().replace('&nbsp;', ' ')
    else:
        metadata['peer_group'] = None

    # TFI company
    tfi_pattern = r'Nazwa\s+towarzystwa[^>]*>[^>]*>([^<]+)<'
    match = re.search(tfi_pattern, html_text)
    metadata['tfi_company'] = match.group(1).strip() if match else None

    # Management fee
    fee_pattern = r'Aktualna\s+opłata\s+stała[^>]*>[^>]*>([\d,]+)\s*%'
    match = re.search(fee_pattern, html_text)
    metadata['mgmt_fee'] = match.group(1).replace(',', '.') if match else None

    # First valuation date
    date_pattern = r'Data\s+pierwszej\s+wyceny[^>]*>[^>]*>(\d{2}\.\d{2}\.\d{4})'
    match = re.search(date_pattern, html_text)
    metadata['inception_date'] = match.group(1) if match else None

    return metadata

def fetch_fund_metadata(fund_code: str, fund_url: str) -> Dict:
    """Fetch and extract metadata for a single fund."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    response = requests.get(fund_url, headers=headers, timeout=30)
    response.raise_for_status()

    return extract_fund_metadata(fund_code, response.text)

# Example usage
metadata = fetch_fund_metadata(
    'SKR54',
    'https://www.analizy.pl/fundusze-inwestycyjne-otwarte/SKR54/skarbiec-spolek-wzrostowych'
)

print(f"Code: {metadata['code']}")
print(f"Peer group: {metadata['peer_group']}")
print(f"TFI: {metadata['tfi_company']}")
print(f"Management fee: {metadata['mgmt_fee']}%")
print(f"Inception: {metadata['inception_date']}")
```

---

## Example 7: Complete Workflow - Analyze Top Polish Equity Funds

End-to-end workflow: download data, calculate metrics, rank funds.

```python
import requests
import pandas as pd
import time

# Step 1: Define funds to analyze
fund_codes = ['SKR54', 'PCS55', 'PCS33', 'PZU81', 'ALL91']

# Step 2: Download quotation data
all_data = {}

for code in fund_codes:
    try:
        url = f"https://www.analizy.pl/api/quotation/fio/{code}"
        response = requests.get(url, timeout=60)
        data = response.json()

        # Extract and store prices
        prices = pd.DataFrame(data['series'][0]['price'])
        prices['date'] = pd.to_datetime(prices['date'])
        prices = prices.sort_values('date').set_index('date')

        all_data[code] = prices
        print(f"[OK] {code}: {len(prices)} days")

        time.sleep(2)  # Rate limiting

    except Exception as e:
        print(f"[ERROR] {code}: {e}")

# Step 3: Calculate metrics
results = []

for code, prices in all_data.items():
    # Calculate returns
    prices['return_1d'] = prices['value'].pct_change()
    prices['return_1m'] = prices['value'].pct_change(periods=21)
    prices['return_12m'] = prices['value'].pct_change(periods=252)

    # Calculate volatility
    annual_vol = prices['return_1d'].std() * (252 ** 0.5)

    # Latest metrics
    latest = prices.iloc[-1]

    results.append({
        'code': code,
        'nav': latest['value'],
        'return_1m': latest['return_1m'],
        'return_12m': latest['return_12m'],
        'volatility': annual_vol
    })

# Step 4: Rank by Sharpe ratio
results_df = pd.DataFrame(results)
results_df['sharpe'] = results_df['return_12m'] / results_df['volatility']
results_df = results_df.sort_values('sharpe', ascending=False)

# Step 5: Display results
print("\n=== Fund Analysis Results ===")
print(results_df.to_string(index=False))

# Save to file
results_df.to_csv('fund_analysis_results.csv', index=False)
print("\nResults saved to: fund_analysis_results.csv")
```

**Expected Output:**
```
=== Fund Analysis Results ===
  code     nav  return_1m  return_12m  volatility   sharpe
 SKR54  315.43      0.033       0.296       0.185    1.600
 PCS33  130.23      0.028       0.242       0.168    1.440
   ...
```

---

## Example 8: Consolidate Multiple Scraping Outputs

Merge FIO, FIZ, and FZG CSV files into a master dataset.

```python
import pandas as pd
from pathlib import Path

# Load individual CSV files
fio_df = pd.read_csv('data/scraped/fio_funds.csv')
fiz_df = pd.read_csv('data/scraped/fiz_funds.csv')
fzg_df = pd.read_csv('data/scraped/fzg_funds.csv')

# Normalize column names (ensure consistency)
for df in [fio_df, fiz_df, fzg_df]:
    if 'group' in df.columns and 'groupname' not in df.columns:
        df.rename(columns={'group': 'groupname'}, inplace=True)

# Concatenate
master_df = pd.concat([fio_df, fiz_df, fzg_df], ignore_index=True)

# Deduplicate by code
master_df = master_df.drop_duplicates(subset=['code'], keep='first')

# Validate completeness
print("=== Field Completeness ===")
for col in master_df.columns:
    non_null = master_df[col].notna().sum()
    total = len(master_df)
    pct = (non_null / total) * 100
    print(f"{col:25s}: {non_null:4d}/{total:4d} ({pct:5.1f}%)")

# Save master file
output_file = 'data/processed/fund_metadata_master.csv'
master_df.to_csv(output_file, index=False)

print(f"\n[OK] Saved {len(master_df)} funds to: {output_file}")
```

---

## Environment Setup

Before running these examples, ensure you have the required dependencies:

```bash
# Install dependencies
uv add requests pandas python-dotenv firecrawl-py

# Create .env file for Firecrawl API key
echo "FIRECRAWL_API_KEY=your-api-key-here" >> .env
```

**Required Packages:**
- `requests` - HTTP library for API calls
- `pandas` - Data manipulation and analysis
- `python-dotenv` - Environment variable management
- `firecrawl-py` - Firecrawl API client (v4.8.0+)

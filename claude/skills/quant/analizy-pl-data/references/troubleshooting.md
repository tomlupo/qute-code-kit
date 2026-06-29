# Troubleshooting Guide

This document contains solutions to common issues when working with analizy.pl data.

## API Issues

### Problem: API Returns 404

**Symptoms:**
- HTTP 404 response when calling quotation or performance API
- Fund code appears valid

**Causes:**
- Fund code is invalid or incorrectly formatted
- Fund has been liquidated or delisted
- Wrong fund type (using FIO endpoint for FZG fund)

**Solutions:**
1. Verify fund code spelling and format:
   - FIO: Uppercase letters and numbers (e.g., `SKR54`)
   - FZG: Underscores for unit class/currency (e.g., `FTI068_A_USD`)

2. Check fund still exists on analizy.pl listings

3. Verify fund type matches endpoint:
   ```python
   # Correct
   https://www.analizy.pl/api/quotation/fio/SKR54
   https://www.analizy.pl/api/quotation/fzg/FTI068_A_USD

   # Wrong
   https://www.analizy.pl/api/quotation/fzg/SKR54  # FIO code on FZG endpoint
   ```

---

### Problem: Response Too Large (Timeout)

**Symptoms:**
- Timeout errors when fetching quotation API
- Request takes >60 seconds
- Memory errors when processing response

**Cause:**
- Quotation API returns years of daily data (3,000+ records)
- Default timeout too short
- Processing entire response in memory

**Solutions:**
1. Increase timeout to 60-120 seconds:
   ```python
   response = requests.get(url, timeout=120)
   ```

2. Stream response directly to file:
   ```python
   import requests

   response = requests.get(url, timeout=120, stream=True)
   with open('output.json', 'wb') as f:
       for chunk in response.iter_content(chunk_size=8192):
           f.write(chunk)
   ```

3. Process in chunks if loading to DataFrame:
   ```python
   import pandas as pd
   from io import StringIO

   # Fetch and save
   response = requests.get(url, timeout=120)
   data = response.json()

   # Convert and save immediately
   df = pd.DataFrame(data['series'][0]['price'])
   df.to_parquet('quotations.parquet')  # More efficient than CSV
   ```

---

### Problem: Rate Limited (429 Error)

**Symptoms:**
- HTTP 429 "Too Many Requests" response
- Requests succeed initially then start failing

**Cause:**
- Too many requests too quickly
- Server rate limiting triggered

**Solutions:**
1. Increase delays between requests:
   ```python
   import time

   for fund_code in fund_codes:
       response = requests.get(url)
       time.sleep(3)  # Increase from 1-2s to 3-5s
   ```

2. Implement exponential backoff:
   ```python
   import time
   import requests

   def fetch_with_backoff(url, max_retries=3):
       for attempt in range(max_retries):
           try:
               response = requests.get(url, timeout=60)
               if response.status_code == 429:
                   wait_time = 2 ** attempt  # 1s, 2s, 4s
                   print(f"Rate limited, waiting {wait_time}s...")
                   time.sleep(wait_time)
                   continue
               return response
           except requests.RequestException as e:
               if attempt == max_retries - 1:
                   raise
               time.sleep(2 ** attempt)

       raise Exception("Max retries exceeded")
   ```

---

## Scraping Issues

### Problem: Firecrawl Rate Limit Exceeded

**Symptoms:**
- Firecrawl returns rate limit error
- "11 requests per minute" error message

**Cause:**
- Delay between requests is too short
- Free tier limit: 11 requests/minute

**Solutions:**
1. Increase `DELAY_BETWEEN_PAGES` to 6.0 seconds:
   ```python
   DELAY_BETWEEN_PAGES = 6.0  # 60s ÷ 11 req = 5.45s minimum

   for page in range(1, total_pages + 1):
       result = app.scrape(url=url, formats=['markdown'])
       time.sleep(DELAY_BETWEEN_PAGES)
   ```

2. Check Firecrawl API usage:
   ```python
   # Add logging to track request timing
   import time

   start_time = time.time()
   request_times = []

   for page in range(1, total_pages + 1):
       page_start = time.time()
       result = app.scrape(url=url, formats=['markdown'])
       request_times.append(time.time() - page_start)

       print(f"Page {page}: {request_times[-1]:.2f}s")
       time.sleep(6.0)
   ```

---

### Problem: No Funds Extracted from Listing Page

**Symptoms:**
- Scraping succeeds but returns 0 funds
- Markdown content exists but parsing fails

**Cause:**
- Regex pattern doesn't handle title attributes in markdown links
- Pattern uses `[^\)]+` instead of `[^\)\"]+`

**Solution:**
Use pattern that stops at either `)` or `"`:
```python
# Wrong - doesn't handle title attributes
pattern = r'\[Profil funduszu: ([^\]]+)\]\((https://www\.analizy\.pl/[^\)]+)\)'

# Correct - stops at " or )
pattern = r'\[Profil funduszu: ([^\]]+)\]\((https://www\.analizy\.pl/[^\)\"]+)'
```

**Test:**
```python
# Save markdown from first page
result = app.scrape(url=first_page_url, formats=['markdown'])
with open('test_page.md', 'w', encoding='utf-8') as f:
    f.write(result.markdown)

# Test pattern against saved file
import re
with open('test_page.md', 'r', encoding='utf-8') as f:
    markdown = f.read()

matches = re.finditer(pattern, markdown)
print(f"Found {len(list(matches))} funds")
```

---

### Problem: Unicode Encoding Fails on Windows

**Symptoms:**
- `UnicodeEncodeError` when printing progress
- Characters like ✓, →, • fail to display

**Cause:**
- Windows console doesn't support all Unicode characters
- Default encoding is cp1252, not UTF-8

**Solutions:**
1. Use ASCII equivalents:
   ```python
   # Replace Unicode characters
   print("[OK]")    # instead of "✓"
   print("->")      # instead of "→"
   print("*")       # instead of "•"
   ```

2. Configure console for UTF-8 (Windows 10+):
   ```python
   import sys
   import io

   # Force UTF-8 output
   sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
   ```

3. Handle encoding in save operations:
   ```python
   # Save with explicit UTF-8 encoding
   df.to_csv('output.csv', index=False, encoding='utf-8-sig')  # BOM for Excel
   ```

---

### Problem: ModuleNotFoundError for firecrawl

**Symptoms:**
- `ModuleNotFoundError: No module named 'firecrawl'`
- Import fails despite installation

**Cause:**
- Package not installed
- Wrong package name (old versions)

**Solutions:**
1. Install correct package:
   ```bash
   uv add firecrawl-py python-dotenv
   ```

2. Verify installation:
   ```bash
   uv pip list | grep firecrawl
   ```

3. Check import syntax for v4.8.0:
   ```python
   # Correct for v4.8.0+
   from firecrawl import Firecrawl

   # Wrong - old v3 syntax
   from firecrawl import FirecrawlApp
   ```

---

### Problem: "No API key provided"

**Symptoms:**
- Firecrawl initialization fails
- Error: "No API key provided"

**Cause:**
- FIRECRAWL_API_KEY not in environment
- .env file not loaded or in wrong location

**Solutions:**
1. Create .env file in project root:
   ```bash
   echo "FIRECRAWL_API_KEY=your-key-here" >> .env
   ```

2. Load environment variables:
   ```python
   from dotenv import load_dotenv

   load_dotenv()  # Must be called before Firecrawl()
   app = Firecrawl()
   ```

3. Verify .env location:
   ```python
   from pathlib import Path

   env_file = Path('.env')
   if not env_file.exists():
       print(f".env not found at: {env_file.absolute()}")
   ```

4. Alternative - explicit API key:
   ```python
   import os

   api_key = os.getenv('FIRECRAWL_API_KEY')
   if not api_key:
       raise ValueError("FIRECRAWL_API_KEY not found in environment")

   app = Firecrawl(api_key=api_key)
   ```

---

## Data Quality Issues

### Problem: Peer Group Extraction Fails (Returns None)

**Symptoms:**
- Peer group field is None/empty for most funds
- Pattern works for some funds but not others

**Cause:**
- Regex pattern doesn't match HTML structure
- Different HTML templates for different fund types

**Solutions:**
1. Use reliable `basicValue` pattern:
   ```python
   pattern = r'Nazwa\s+grupy</p>\s*<p[^>]*class="[^"]*basicValue[^"]*"[^>]*>\s*<span[^>]*></span>([^<]+)</p>'
   ```

2. Test on multiple fund types:
   ```python
   test_funds = [
       ('ALL100', 'debt'),    # Debt fund
       ('SKR54', 'equity'),   # Equity fund
       ('ARK04', 'mixed')     # Mixed fund
   ]

   for code, fund_type in test_funds:
       metadata = fetch_fund_metadata(code, url)
       print(f"{code} ({fund_type}): {metadata['peer_group']}")
   ```

3. Debug by inspecting HTML:
   ```python
   # Save HTML snippet around "Nazwa grupy"
   import re

   match = re.search(r'(Nazwa\s+grupy.{200})', html_text, re.DOTALL)
   if match:
       print(match.group(1))
   ```

---

### Problem: CSV Corruption with Multiline Fields

**Symptoms:**
- CSV file has thousands of lines per record
- Data appears corrupted when loading
- Excel/pandas shows garbled content

**Cause:**
- Extracted fields contain HTML fragments spanning many lines
- Benchmark field captures entire HTML sections

**Solutions:**
1. Skip problematic fields:
   ```python
   # Don't extract benchmark - causes corruption
   # metadata['benchmark'] = extract_benchmark(html)  # SKIP THIS
   ```

2. Validate field length before saving:
   ```python
   MAX_FIELD_LENGTH = 80

   if 'peer_group' in metadata:
       if len(metadata['peer_group']) > MAX_FIELD_LENGTH:
           print(f"Warning: peer_group too long ({len(metadata['peer_group'])} chars)")
           metadata['peer_group'] = None
   ```

3. Check for HTML entities:
   ```python
   if '&#' in str(metadata.get('peer_group', '')):
       print(f"Warning: HTML entities in peer_group for {code}")
       metadata['peer_group'] = None
   ```

4. Use strict regex patterns:
   ```python
   # Non-greedy, specific stop conditions
   pattern = r'Nazwa\s+grupy</p>\s*<p[^>]*>([^<]+)</p>'  # Stops at first </p>
   ```

---

### Problem: Different Success Rates for Fund Types

**Symptoms:**
- 95% success for equity funds
- 60% success for debt funds
- Different extraction rates by category

**Cause:**
- Different HTML templates for different fund categories
- Pattern optimized for one type

**Solutions:**
1. Test pattern on all fund types before batch processing:
   ```python
   test_samples = {
       'equity': ['SKR54', 'PCS55'],
       'debt': ['ALL100', 'PZU91'],
       'mixed': ['ARK04', 'PKO21']
   }

   for category, codes in test_samples.items():
       success = 0
       for code in codes:
           metadata = fetch_fund_metadata(code, get_url(code))
           if metadata['peer_group']:
               success += 1
       print(f"{category}: {success}/{len(codes)} success")
   ```

2. Use universal pattern (basicValue):
   ```python
   # Works for all fund types
   pattern = r'Nazwa\s+grupy</p>\s*<p[^>]*class="[^"]*basicValue[^"]*"[^>]*>\s*<span[^>]*></span>([^<]+)</p>'
   ```

---

## Performance Issues

### Problem: HTML Structure Changed

**Symptoms:**
- Scraping worked previously but now fails
- All funds return None for metadata fields
- Pattern matches but extracts wrong content

**Cause:**
- Analizy.pl website redesign
- HTML class names or structure changed

**Solutions:**
1. Fetch fresh HTML and inspect:
   ```python
   import requests

   response = requests.get(url, headers=headers)
   with open('current_html.html', 'w', encoding='utf-8') as f:
       f.write(response.text)

   # Open in browser and inspect structure
   ```

2. Search for key labels:
   ```python
   # Find all instances of "Nazwa grupy"
   import re

   matches = re.finditer(r'Nazwa\s+grupy(.{300})', html, re.DOTALL)
   for i, match in enumerate(matches, 1):
       print(f"\n=== Instance {i} ===")
       print(match.group(0))
   ```

3. Update CSS selectors/patterns based on new structure

---

### Problem: Performance Table Format Changed

**Symptoms:**
- pandas.read_html() fails
- Table parsing returns wrong data
- Column names don't match expected

**Cause:**
- Analizy.pl updated table structure
- New columns added or order changed

**Solutions:**
1. Inspect actual HTML response:
   ```python
   url = "https://www.analizy.pl/api/rate-of-return/fio/SKR54"
   response = requests.get(url)

   with open('performance_table.html', 'w', encoding='utf-8') as f:
       f.write(response.text)
   ```

2. Adjust pandas parsing parameters:
   ```python
   tables = pd.read_html(url, header=0)  # Try with header
   # or
   tables = pd.read_html(url, skiprows=1)  # Skip first row
   ```

3. Parse manually if needed:
   ```python
   from bs4 import BeautifulSoup

   soup = BeautifulSoup(response.text, 'html.parser')
   table = soup.find('table')

   # Extract data manually
   rows = table.find_all('tr')
   for row in rows:
       cells = row.find_all(['td', 'th'])
       print([cell.text.strip() for cell in cells])
   ```

---

## Best Practices to Avoid Issues

1. **Always test on samples first:**
   ```python
   # Test scraper on 5 funds before running on 2,000
   test_codes = fund_codes[:5]
   for code in test_codes:
       result = scrape_fund(code)
       verify_result(result)
   ```

2. **Save checkpoints frequently:**
   ```python
   if idx % 50 == 0:
       pd.DataFrame(results).to_csv(f'checkpoint_{idx}.csv')
   ```

3. **Log errors with context:**
   ```python
   import logging

   logging.basicConfig(
       filename='scraping.log',
       level=logging.ERROR,
       format='%(asctime)s - %(message)s'
   )

   try:
       metadata = fetch_fund(code)
   except Exception as e:
       logging.error(f"Fund {code}: {e}")
   ```

4. **Validate extracted data:**
   ```python
   def validate_metadata(metadata):
       """Validate extracted metadata quality."""
       issues = []

       if metadata.get('peer_group') and len(metadata['peer_group']) > 80:
           issues.append('peer_group too long')

       if '&#' in str(metadata.get('peer_group', '')):
           issues.append('HTML entities in peer_group')

       if not metadata.get('code'):
           issues.append('missing code')

       return issues

   # Use in scraping loop
   issues = validate_metadata(metadata)
   if issues:
       print(f"Validation issues for {code}: {issues}")
   ```

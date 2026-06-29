# Regex Patterns for Data Extraction

This document contains all regex patterns for extracting fund data from analizy.pl listing pages and profile pages.

## Critical Formatting Note

**Markdown links include title attributes that break simple patterns.**

Example markdown structure:
```markdown
[Profil funduszu: Fund Name](https://www.analizy.pl/...url... "title attribute here")
```

**Key fix:** Use `[^\)\"]+` instead of `[^\)]+` to stop at either `)` or `"` (title attribute delimiter).

---

## Listing Page Patterns (Markdown)

### Fund Header Pattern

Extracts fund code, name, URL, and type from listing page markdown.

**FIO (Open-End Funds):**
```python
pattern = r'\[Profil funduszu: ([^\]]+)\]\((https://www\.analizy\.pl/fundusze-inwestycyjne-otwarte/([A-Z0-9]+)/[^\)\"]+)'
```

**FIZ (Closed-End Funds):**
```python
pattern = r'\[Profil funduszu: ([^\]]+)\]\((https://www\.analizy\.pl/fundusze-inwestycyjne-zamkniete/([A-Z0-9]+)/[^\)\"]+)'
```

**FZG (Foreign Funds):**
```python
pattern = r'\[Profil funduszu: ([^\]]+)\]\((https://www\.analizy\.pl/fundusze-zagraniczne/([A-Z0-9_]+)/[^\)\"]+)'
```

**Universal Pattern (All Types):**
```python
pattern = r'\[Profil funduszu: ([^\]]+)\]\((https://www\.analizy\.pl/fundusze-inwestycyjne-(otwarte|zamkniete|zagraniczne)/([A-Z0-9_]+)/[^\)\"]+)\)'

# Groups:
# 1: fund name
# 2: full URL
# 3: fund type (otwarte/zamkniete/zagraniczne → fio/fiz/fzg)
# 4: fund code
```

**Type Mapping:**
```python
type_map = {
    'otwarte': 'fio',
    'zamkniete': 'fiz',
    'zagraniczne': 'fzg'
}
```

---

### Peer Group Pattern

Extract peer group from markdown content after fund header.

**Python Function:**
```python
def extract_peer_group(content_after_header: str) -> str:
    """
    Extract peer group from listing page markdown.

    Peer group appears after category badge, before TFI company.
    Contains Polish keywords: akcji, obligacji, mieszane, etc.
    """
    lines = content_after_header.split('\n')

    # Skip these category badges
    SKIP_BADGES = ['Akcyjne', 'Dłużne', 'Mieszane', 'Pozostałe', 'Absolute return']

    # Polish keywords in peer groups
    KEYWORDS = ['akcji', 'obligacji', 'papierów', 'mieszane', 'absolutnej',
                'dłużnych', 'polskich', 'zagranicznych', 'globalnych', 'stopy',
                'rynku', 'wzrostu', 'korporacyjnych', 'skarbowych']

    found_heading = False

    for line in lines[:25]:
        line = line.strip()

        # Skip empty, URLs, badges
        if not line or len(line) < 8:
            continue
        if line.startswith('[') or line.startswith('http'):
            continue
        if line in SKIP_BADGES:
            continue

        # Skip heading (## Fund Name)
        if line.startswith('##'):
            found_heading = True
            continue

        # After heading, find line with Polish keywords
        if found_heading:
            if any(kw in line.lower() for kw in KEYWORDS):
                return line

    return None
```

**Common Peer Groups:**

FIO Examples:
- `akcji polskich uniwersalne`
- `papierów dłużnych polskich skarbowych`
- `mieszane polskie zrównoważone`

FIZ Examples:
- `absolutnej stopy zwrotu uniwersalne`
- `wierzytelności`

FZG Examples:
- `akcji globalnych rynków rozwiniętych`
- `obligacji globalnych`

---

### TFI Company Pattern

Extract management company name from markdown content.

**Python Function:**
```python
def extract_tfi_company(content: str) -> str:
    """Extract TFI company name from markdown content."""
    lines = content.split('\n')

    for line in lines[:30]:
        line = line.strip()

        # TFI names contain "TFI" or "Towarzystwo"
        if 'TFI' in line or 'Towarzystwo' in line:
            # Length check (TFI names are 15-80 chars)
            if 10 < len(line) < 80:
                # Skip lines that are labels, not names
                if not any(skip in line for skip in ['Nazwa towarzystwa', 'firma', 'opłata']):
                    return line

    return None
```

**TFI Name Patterns:**
- Polish: `PKO TFI S.A.`, `TFI Allianz Polska`, `Skarbiec TFI S.A.`
- Foreign (FZG): `Franklin Templeton (Lux)`, `Schroders (Lux)`, `BlackRock (Lux)`

---

### Currency Pattern

Extract currency code from markdown content.

**Regex:**
```python
pattern = r'\b(PLN[DP]?|EUR|USD)\b'
```

**Python Function:**
```python
def extract_currency(content: str) -> str:
    """Extract currency code from markdown content."""
    match = re.search(r'\b(PLN[DP]?|EUR|USD)\b', content)

    if match:
        currency_raw = match.group(1)
        # PLND = distribution units, PLNP = accumulation units
        # For directory purposes, map to base currency
        return currency_raw[:3] if currency_raw.startswith('PLN') else currency_raw

    return 'PLN'  # Default for Polish funds
```

---

### NAV Value Pattern

Extract current NAV value from markdown.

**Regex:**
```python
pattern = r'([\d\s]+,\d+)\s*PLN\s*Wartość certyfikatu'
```

**Python Function:**
```python
def extract_nav_value(content: str) -> str:
    """Extract NAV value from markdown content."""
    nav_match = re.search(r'([\d\s]+,\d+)\s*PLN\s*Wartość certyfikatu', content)
    if nav_match:
        return nav_match.group(1).replace(' ', '').strip()
    return None
```

---

### Valuation Date Pattern

Extract latest valuation date from markdown.

**Regex:**
```python
pattern = r'\b(\d{2}\.\d{2}\.\d{4})\b'
```

**Format:** DD.MM.YYYY

---

### YTD Return Pattern

Extract year-to-date return from markdown.

**Regex:**
```python
pattern = r'([+-]?\d+,\d+)%\s*YTD'
```

**Example:** `+29.6%` or `-2.1%`

---

### Valuation Frequency Pattern (FIZ Only)

Extract valuation frequency for closed-end funds.

**Python Function:**
```python
def extract_valuation_frequency(content: str) -> str:
    """Extract valuation frequency for FIZ funds."""
    if 'miesięczna' in content:
        return 'miesięczna'  # Monthly
    elif 'kwartalna' in content:
        return 'kwartalna'  # Quarterly
    return None
```

---

## Profile Page Patterns (HTML)

### Peer Group Pattern (Most Reliable)

Extract peer group from fund profile page HTML.

**Regex:**
```python
peer_group_pattern = r'Nazwa\s+grupy</p>\s*<p[^>]*class="[^"]*basicValue[^"]*"[^>]*>\s*<span[^>]*></span>([^<]+)</p>'
```

**Usage:**
```python
match = re.search(peer_group_pattern, html_text, re.IGNORECASE)
if match:
    peer_group = match.group(1).strip().replace('&nbsp;', ' ')
```

**HTML Structure:**
```html
<p class="basicLabel">Nazwa grupy</p>
<p class="basicValue">
    <span class="iconDot shareFundBgColor"></span>akcji globalnych rynków rozwiniętych
</p>
```

---

### TFI Company Pattern (HTML)

**Regex:**
```python
tfi_pattern = r'Nazwa\s+towarzystwa[^>]*>[^>]*>([^<]+)<'
```

---

### Management Fee Pattern

**Regex:**
```python
fee_pattern = r'Aktualna\s+opłata\s+stała[^>]*>[^>]*>([\d,]+)\s*%'
```

**Usage:**
```python
match = re.search(fee_pattern, html_text)
mgmt_fee = match.group(1).replace(',', '.') if match else None
```

---

### First Valuation Date Pattern

**Regex:**
```python
date_pattern = r'Data\s+pierwszej\s+wyceny[^>]*>[^>]*>(\d{2}\.\d{2}\.\d{4})'
```

**Format:** DD.MM.YYYY

---

## Complete Extraction Function (HTML)

```python
import re
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
```

---

## Common Pitfalls

### Problem 1: Benchmark field captures too much HTML
- **Cause:** Greedy regex patterns capture entire HTML sections
- **Solution:** Skip benchmark field or use very strict patterns
- **Impact:** Can corrupt CSV files with thousands of lines per record

### Problem 2: HTML entities in extracted text
- **Cause:** Polish characters encoded as HTML entities (e.g., `&#281;`)
- **Solution:** Replace `&nbsp;` with space, let pandas handle other entities
- **Check:** Look for `&#` in extracted peer groups - indicates corruption

### Problem 3: Different HTML for equity vs debt funds
- **Cause:** Analizy.pl uses different templates for different fund types
- **Solution:** Use the `basicValue` pattern which works for ALL fund types
- **Test:** Validate on both debt funds (e.g., ALL100) and equity funds (e.g., SKR54)

### Problem 4: Title attributes in markdown links
- **Cause:** Markdown links include `"title"` attributes
- **Solution:** Use `[^\)\"]+` instead of `[^\)]+` in URL capture groups
- **Example:** `[Link](url "title")` requires stopping at `"` delimiter

# Analizy.pl API Reference

This document contains detailed API endpoint specifications, response structures, and field definitions for analizy.pl data sources.

## JSON API Endpoints

Analizy.pl exposes several internal JSON APIs that return structured data.

### Historical Quotations API

Get complete historical daily NAV (Net Asset Value) time series for a fund.

**Endpoints:**
```
GET https://www.analizy.pl/api/quotation/fio/{FUND_CODE}
GET https://www.analizy.pl/api/quotation/fzg/{FUND_CODE}
```

**Parameters:**
- `{FUND_CODE}`: Fund identifier (e.g., `SKR54` for FIO, `FTI068_A_USD` for FZG)

**Response Format:** JSON

**Response Structure:**
```json
{
  "id": "fund_SKR54",
  "label": "Fundusz",
  "currency": "PLN",
  "series": [
    {
      "price": [
        {"date": "2025-10-27", "value": 315.43},
        {"date": "2025-10-26", "value": 307.25}
      ]
    }
  ]
}
```

**Key Fields:**
- `id` (string): Fund identifier with "fund_" prefix
- `label` (string): Data series label (typically "Fundusz")
- `currency` (string): NAV currency (PLN, EUR, USD, etc.)
- `series[0].price` (array): Array of price points
  - `date` (string): Quotation date in YYYY-MM-DD format
  - `value` (number): NAV per unit

**Example URLs:**
- FIO: `https://www.analizy.pl/api/quotation/fio/SKR54`
- FZG: `https://www.analizy.pl/api/quotation/fzg/FTI068_A_USD`

**Response Size:** Large (typically 1,000-3,000+ daily observations per fund)

**Usage Notes:**
- Response can be 50k+ tokens for funds with long history
- Save to file immediately if processing many funds
- Timeout: Use 60+ second timeout

---

### Performance Metrics API

Get performance table with returns across all periods.

**Endpoints:**
```
GET https://www.analizy.pl/api/rate-of-return/fio/{FUND_CODE}
GET https://www.analizy.pl/api/rate-of-return/fzg/{FUND_CODE}
```

**Parameters:**
- `{FUND_CODE}`: Fund identifier

**Response Format:** HTML table (parseable with pandas)

**Response Structure:**
HTML table with 3 rows:
- **Row 1:** Fund returns for each period (e.g., "3.3%", "29.6%")
- **Row 2:** Peer group average returns
- **Row 3:** Position in peer group (e.g., "2/58" = 2nd out of 58 funds)

**Periods Covered:**
- 1M, 3M, 6M, YTD, 12M, 24M, 36M, 48M, 60M, 120M

**Example URLs:**
- FIO: `https://www.analizy.pl/api/rate-of-return/fio/SKR54`
- FZG: `https://www.analizy.pl/api/rate-of-return/fzg/FTI068_A_USD`

**Usage Notes:**
- Use pandas.read_html() to parse response
- Row indices: 0 = fund returns, 1 = group average, 2 = position

---

### Yearly Returns API

Get calendar year returns for a fund.

**Endpoint:**
```
GET https://www.analizy.pl/api/rate-of-return/fio/{FUND_CODE}/yearly
```

**Response Format:** HTML table

**Response Structure:**
Annual performance by year (e.g., 2024: 15.2%, 2023: -2.1%, etc.)

---

### Historical Rankings API

Get historical ranking positions over time.

**Endpoint:**
```
GET https://www.analizy.pl/api/ranking/{FUND_CODE}/{PERIOD}
```

**Parameters:**
- `{FUND_CODE}`: Fund identifier
- `{PERIOD}`: `12M` or `36M`

**Example:**
```
https://www.analizy.pl/api/ranking/SKR54/12M
```

---

## Data Fields Reference

### Performance Periods

| Period Code | Meaning | Notes |
|-------------|---------|-------|
| 1M | 1 month | Last 30 days |
| 3M | 3 months | Last quarter |
| 6M | 6 months | Last half year |
| YTD | Year to date | Since Jan 1 current year |
| 12M | 12 months | Last year |
| 24M | 24 months | Last 2 years |
| 36M | 36 months | Last 3 years |
| 48M | 48 months | Last 4 years |
| 60M | 60 months | Last 5 years |
| 120M | 120 months | Last 10 years |

### Fund Metadata Fields

| Field | Type | Description | Source |
|-------|------|-------------|--------|
| code | string | Fund code (primary key) | Listing/Profile |
| name | string | Full fund name | Listing/Profile |
| type | string | Fund type (fio/fiz/fzg) | Listing/Profile |
| groupname | string | Peer group classification | Listing/Profile |
| tfi_company | string | Management company | Listing/Profile |
| currency | string | NAV currency | Listing/Profile |
| url | string | Fund profile page URL | Listing/Profile |
| nav_value | number | Current NAV per unit | Listing |
| valuation_date | string | Latest valuation date (DD.MM.YYYY) | Listing |
| valuation_frequency | string | FIZ only (miesięczna/kwartalna) | Listing |
| ytd_return | string | Year-to-date return (%) | Listing |
| isin | string | ISIN code | Profile only |
| inception_date | string | Fund inception date | Profile only |
| aum_mln_pln | number | Assets under management (millions PLN) | Listing/Profile |
| mgmt_fee_max | number | Maximum management fee (%) | Listing/Profile |
| risk_level | string | Risk indicator (1-7 scale) | Listing/Profile |
| sharpe_ratio | number | Risk-adjusted return | Profile only |
| information_ratio | number | Alpha / tracking error | Profile only |
| std_dev | number | Volatility measure | Profile only |

### Polish Terminology

| Data Point | Polish Term | Description |
|------------|-------------|-------------|
| TFI | Towarzystwo | Management company |
| AUM | Wartość aktywów | Assets under management |
| SRRI | SRRI | Synthetic Risk-Reward Indicator (1-7) |
| Sharpe Ratio | Współczynnik Sharpe'a | Risk-adjusted return |
| Std Dev | Odchylenie standardowe | Volatility measure |
| Information Ratio | Współczynnik informacyjny | Alpha / tracking error |
| Management Fee | Opłata za zarządzanie | Annual fee (%) |
| Peer Group | Nazwa grupy | Fund classification |

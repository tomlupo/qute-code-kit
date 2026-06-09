# atlasetf.pl API Reference

Reverse-engineered from the live site's network traffic (verified working).
Base URL: `https://atlasetf.pl/api/v2/`. All calls are `POST` with
`Content-Type: application/json`. No API key needed for the endpoints below;
only `/api/v2/user/*` requires a logged-in session (returns 403 otherwise).

From a server, set headers `User-Agent`, and if you get blocked, `Origin:
https://atlasetf.pl` and `Referer: https://atlasetf.pl/`. No CAPTCHA observed.

Most bodies accept `"lang"` (`"pl"` or `"en"`) and `"currency"` (`"PLN"`,
`"EUR"`, `"USD"`).

## Table of contents
1. ETF list / screener — `etf/search`
2. Per-ETF detail — `etf/details` and friends
3. Prices / quotes
4. Auth-gated endpoints

---

## 1. ETF list / screener

`POST /api/v2/etf/search`

The screener. Returns paginated ETF rows plus every filter facet. Empty filter
arrays = no filtering (returns the whole universe).

Request body:
```json
{
  "filter": {
    "class": null, "class_name": null,
    "investment_area": [], "global_category": [], "morningstar_category": [],
    "fund_yield_12m": [], "fi_average_yield_to_maturity": [],
    "fi_effective_maturity": [], "fi_average_effective_duration": [],
    "brokers": [], "broker_accounts": [], "groups": [], "providers": [],
    "distribution_policy": null, "exchanges": [], "trade_currencies": [],
    "domiciles": [], "replication": [], "age": null, "ter": [],
    "fund_size": null, "currency_risk": null, "xlm": [], "strategy_risks": [],
    "distribution_frequencies": [], "matching_index": null,
    "search_filter": null,
    "page": 1, "row_per_page": 100,
    "sort_field": "fund_name", "sort_order": "asc", "ratings": []
  },
  "lang": "pl", "currency": "PLN"
}
```

- Free-text search: set `filter.search_filter` to a string (name, ticker, ISIN,
  CUSIP).
- Pagination: `filter.page` (1-based) and `filter.row_per_page` (100 works well).
- Sorting: `filter.sort_field` (e.g. `fund_name`, `expense_ratio`,
  `return_1y`, `fund_size`) and `filter.sort_order` (`asc`/`desc`).

Response (top-level keys):
```
etfs            -> array of ETF rows (the data)
row_count       -> total matching funds (string, e.g. "13113")
row_per_page, page
class, class_groups, class_summary, brokers, accounts, providers,
distribution_policy, exchanges, domiciles, replication, age, fund_sizes,
currency_risks, trade_currencies, matching_indices, xlm, strategy_risks,
distribution_frequencies, ter, ratings, return_end_date, return_year_y0,
return_year_y1..., category_info     -> filter facet options + metadata
```

Each item in `etfs`:
```
isin, ticker, fund_name, fund_currency, fund_size, fund_size_currency,
expense_ratio (TER %), fund_provider, replication_name_lang,
distribution_policy_lang, distribution_frequency_lang, domicile_lang,
inception_date, currency_hedged_lang, rating,
return_1m, return_3m, return_6m, return_1y, return_3y, return_5y,
return_y0, return_y1, return_y2, return_y3, return_y4, return_y5
```

To pull everything: loop `page` from 1 while `(page-1)*row_per_page < row_count`.
At `row_per_page=100` that's ~`ceil(13113/100)=132` requests.

---

## 2. Per-ETF detail

All keyed by ISIN with body `{"isin": "<ISIN>", "lang": "pl", "currency": "PLN"}`.

### `POST /api/v2/etf/details` (main fundamentals)
Returns: `isin, cusip, fund_name, expense_ratio, fund_currency, domicile_id,
domicile_name_lang, replication_name_lang, distribution_frequency_lang,
distribution_policy, fund_size, fund_size_currency, inception_date,
fund_provider, fund_provider_url, ucits_compliance, legal_structure,
description, currency_hedged, currency_hedged_to, turnover_ratio,
is_inverse_short_fund, is_actively_managed, benchmark, average_spread,
base_currency, exchange, global_broad_category_lang, morningstar_category,
category_lang, investment_area_lang, administrator, listings, ...`

`listings` is an array of exchange listings, each:
`{ ticker, exchange, country_name, country_id, currency }`.

### Other detail endpoints (same `{isin,lang,currency}` body, all public/200)
- `POST /api/v2/etf/extdata` — extended data
- `POST /api/v2/etf/allocations` — holdings / sector / country allocations
- `POST /api/v2/etf/dividend` — dividend history
- `POST /api/v2/etf/documents` — KIID / factsheet document links
- `POST /api/v2/etf/currency` — currency data

---

## 3. Prices / quotes

Quote data is sourced from EOD Historical Data; codes look like `IWDA.LSE`,
`ETFBW20TR.WAR`, `EURPLN.FOREX`.

### `POST /api/v2/etf/main-page-quotes` — body `{"lang":"pl"}`
Array of instruments, each with a full `quote`
(`open/high/low/close/volume/previousClose/change/change_p/timestamp/code`) and
a `prices` array of intraday points (`timestamp`, `dateTime`, price). Good
source of live + intraday price data.

### `POST /api/v2/etf/ticker-marquee-quotes` — body `{"lang":"pl"}`
FX and index quotes (the scrolling ticker).

### Macro/aggregate feeds
- `POST /api/v2/etf/equity-markets-world` — `{"tab":"World","currency":"PLN","period":"1y"}`
- `POST /api/v2/etf/equity-sectors-world` — `{"lang":"pl","currency":"PLN","period":"1y"}`
- `POST /api/v2/etf/landing-page-map` — `{"lang":"pl","currency":"PLN"}`

### Per-instrument real-time
`POST /api/v2/etf/real-time` is used on detail pages for a listing's live/
intraday quote. It expects the listing's exchange-specific code (not just the
ISIN); the exact field wasn't pinned down. If you need per-ISIN intraday,
capture the request body from the detail page's network tab, or fall back to
matching the fund's listing code against `main-page-quotes`.

---

## 4. Auth-gated endpoints (403 without login — out of scope)
- `POST /api/v2/user/status`
- `POST /api/v2/user/favourite-etfs`
- `POST /api/v2/user/etf/fundamentals` (premium fundamentals)

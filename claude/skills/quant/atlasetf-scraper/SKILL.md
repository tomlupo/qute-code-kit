---
name: atlasetf-scraper
description: >-
  Scrape ETF data from atlasetf.pl (aka "atlas etf", "atlasETF", "atlas-etf")
  via its JSON API: the full ~13,000-fund screener, per-ISIN detail,
  fundamentals and dividends, and price/quote (OHLC) data. Use whenever the user
  wants to scrape, download, export, or query ETF data from atlasetf.pl — even
  casual phrasings that just name the site. Not for other sources (justETF,
  stooq, Yahoo, brokerage statements) or general ETF advice.
---

# atlasetf.pl Scraper

atlasetf.pl is a Polish ETF research site. The front end is a React single-page
app, so fetching the raw HTML (`GET https://atlasetf.pl/`) returns only a
"JavaScript required" shell with **no data**. Don't scrape the DOM. Instead, hit
the site's own public JSON API at `https://atlasetf.pl/api/v2/`, which is what
the app itself calls.

All endpoints are `POST` with a JSON body and need no API key for the public
data (only personal/premium account features are login-gated). This was verified
by inspecting the live site's network traffic.

## When to use this skill

Trigger whenever the user wants ETF data that lives on atlasetf.pl: a list/
screener export, fundamentals for specific funds, returns/TER comparisons, or
price/quote data. The user may phrase it as "scrape", "download", "get me a
spreadsheet of...", "pull every ETF with...", or just name the site.

## The three things people usually want

1. **The ETF list / screener** — every fund with returns, TER, size, provider, etc.
2. **Per-ETF detail** — full fundamentals for one or more ISINs.
3. **Prices / quotes** — OHLC + intraday quote data.

The bundled script handles all three. Read `references/api_reference.md` for the
exact endpoints, request bodies, and response fields before writing custom calls.

## How to do it

Use the bundled script `scripts/atlas_scraper.py` — it already encodes the
verified payloads, pagination, polite throttling, and retry/backoff. Don't
re-derive the API by hand unless the script fails; in that case consult
`references/api_reference.md`.

Common invocations (run from the skill directory):

```bash
# Full ETF list -> CSV (all ~13k funds, paginated automatically)
python scripts/atlas_scraper.py list --out etfs.csv

# Filtered list (e.g., only Polish-domiciled accumulating equity) -> CSV
python scripts/atlas_scraper.py list --search "msci world" --out world.csv

# Detail/fundamentals for one or more ISINs -> JSON
python scripts/atlas_scraper.py detail IE00B4L5YX21 IE00B5BMR087 --out detail.json

# Homepage quote/price feeds -> JSON
python scripts/atlas_scraper.py prices --out prices.json
```

Run `python scripts/atlas_scraper.py --help` for all options (language,
currency, page size, delay, output format).

If the user wants the result as a spreadsheet, the `list` command writes CSV by
default (`--out file.csv`); for `.xlsx`, pass `--format xlsx` or hand the CSV to
the spreadsheet workflow.

## Throttling and terms of use — important

atlasetf.pl is a **commercial data product**, and much of its data is licensed
from third parties (e.g. EOD Historical Data, Morningstar). Scrape considerately
so you don't hammer their servers or overstep their terms:

- The script defaults to a **1 request/second** rate limit and exponential
  backoff on errors. Keep it on. Don't crank concurrency.
- A full list pull is ~130 paginated requests; per-ETF detail is one request per
  ISIN (~13k if you pull everything), so only fetch detail for funds the user
  actually needs.
- Before any bulk pull, **remind the user to check `https://atlasetf.pl/robots.txt`
  and the site's Terms of Service**, and not to redistribute the data. If the
  user wants to scrape the entire universe repeatedly or commercially, flag that
  this may exceed acceptable use and suggest they confirm they're allowed to.
- Set a real, identifying `User-Agent` (the script does). Don't try to evade any
  rate limiting or blocks — if the site blocks you, stop and tell the user.

## Auth-gated endpoints

These return HTTP 403 without a logged-in session and are out of scope for
public scraping: `/api/v2/user/status`, `/api/v2/user/favourite-etfs`,
`/api/v2/user/etf/fundamentals` (premium fundamentals). Don't attempt to bypass
the login.

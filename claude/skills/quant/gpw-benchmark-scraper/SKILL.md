---
name: gpw-benchmark-scraper
description: >-
  Scrape data from gpwbenchmark.pl (GPW Benchmark, Warsaw Stock Exchange): WIBID
  and WIBOR delayed reference rates (the year-to-date /dane-opoznione table), the
  full list of stock/bond/strategy indices with their ISINs, and per-index
  historical OHLC time series (the karta-indeksu / chart data, keyed by ISIN).
  Use whenever the user wants to download, export, scrape, or query GPW Benchmark
  index values, index lists, or WIBOR/WIBID rates — even casual phrasings that
  just name the site. Not for atlasetf.pl, stooq, justETF, or gpw.pl equities.
---

# GPW Benchmark scraper (gpwbenchmark.pl)

gpwbenchmark.pl renders most of its data tables from its own backend endpoints
(`ajaxindex.php`, `chart-json.php`) and from server-side HTML. This skill hits
those directly. The site sits behind an F5 WAF, so use the exact request shapes
documented in `references/api_reference.md` — don't fuzz parameters.

## When to use

Trigger when the user wants any of:
1. **WIBID/WIBOR rates** — the delayed reference-rate table (year-to-date).
2. **Index list** — every GPW Benchmark index with its ISIN (and latest snapshot).
3. **Index history** — daily OHLC time series for one, several, or all indices.

## How to do it

Use the bundled script `scripts/gpw_benchmark.py`. It encodes the verified
endpoints, the CDATA/HTML parsing, request throttling (default 1 req/s), and
retry/backoff. Output is CSV.

```bash
# install deps once
pip install requests beautifulsoup4

# 1. WIBID/WIBOR delayed rates (year-to-date) -> wibid_wibor.csv
python scripts/gpw_benchmark.py rates --out wibid_wibor.csv

# 2. All indices + ISINs across every category -> indices.csv
python scripts/gpw_benchmark.py indices --out indices.csv

# 3a. History for specific ISIN(s), 1-year daily OHLC -> series_1R.csv
python scripts/gpw_benchmark.py series PL9999999474 PL9999999987 --mode 1R

# 3b. History for EVERY index (discovers ISINs first) -> series_1R.csv
python scripts/gpw_benchmark.py series --all --mode 1R --out all_series.csv

# Everything at once (rates + indices + 1Y series for all indices)
python scripts/gpw_benchmark.py all --mode 1R
```

Options: `--lang PL|EN`, `--delay <seconds>`, `--mode {14D,1M,3M,6M,1R}`,
`--batch N` (ISINs per chart request), `--tabs` (subset of index categories).
Run `python scripts/gpw_benchmark.py --help`.

## Output CSVs

- **rates** — `Date, WIBID_ON, WIBID_1M, WIBID_3M, WIBID_6M, WIBID_SW,
  WIBOR_ON, WIBOR_1M, WIBOR_3M, WIBOR_6M, WIBOR_1Y, WIBOR_SW` (tenor columns are
  derived from the live header, so they self-adjust if GPW changes them).
- **indices** — `category, section, shortcode, isin, cmng_id, num, last_time,
  twi, open, min, max, last, change_pct, portfolio_pct, turnover_thousands_pln`.
- **series** — long format: `isin, date, timestamp, open, high, low, close`
  (date is Europe/Warsaw trading date; `timestamp` is the raw epoch in seconds).

If the user wants `.xlsx`, hand the CSV to the spreadsheet workflow.

## Notes / gotchas

- **`MAX` is not a real window.** The longest server-provided history is `1R`
  (one year). For deeper history, GPW Benchmark publishes downloadable
  historical files under "Dane historyczne" — out of scope for this scraper.
- The WIBID/WIBOR table is **year-to-date only** and one business-day delayed
  (updated ~23:00).
- The same index can appear under multiple category tabs; the script
  de-duplicates by ISIN.

## Terms of use — important

WIBID® and WIBOR® are **regulated reference rates** administered by GPW
Benchmark S.A. The delayed data is published for information only.
**Redistributing** WIBOR/WIBID, or using them in automated trading or
non-visualised data applications, requires a **Market Data License Agreement**
with GPW Benchmark. Index data is likewise a commercial product.

Before any bulk or repeated pull: remind the user to check
`https://gpwbenchmark.pl/robots.txt` and the site's terms, keep the throttle on,
set a real identifying `User-Agent` in the script, and not to redistribute the
data. If the site blocks you (the WAF "Request Rejected" page), stop and tell
the user rather than trying to evade it.

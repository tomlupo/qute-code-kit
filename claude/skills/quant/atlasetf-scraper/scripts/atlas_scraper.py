#!/usr/bin/env python3
"""
atlasetf.pl scraper.

Pulls ETF data from atlasetf.pl's public JSON API (https://atlasetf.pl/api/v2/):
  - list     : the ETF screener (all ~13k funds, or filtered), -> CSV/XLSX/JSON
  - detail   : per-ETF fundamentals for one or more ISINs,      -> JSON/CSV
  - prices   : homepage quote/price feeds,                      -> JSON

The site is a JavaScript SPA, so its raw HTML has no data; this script calls the
same REST API the app uses. No API key needed for public data.

Be considerate: atlasetf.pl is a commercial product with licensed data. This
script rate-limits to ~1 req/s by default and backs off on errors. Check the
site's robots.txt and Terms of Service before bulk-scraping, and don't
redistribute the data.

Usage:
    python atlas_scraper.py list   [--search TEXT] [--sort FIELD] [--order asc|desc]
                                   [--page-size N] [--max-pages N]
                                   [--out FILE] [--format csv|xlsx|json]
    python atlas_scraper.py detail ISIN [ISIN ...] [--out FILE] [--format json|csv]
                                   [--endpoints details,allocations,dividend,...]
    python atlas_scraper.py prices [--feeds main,marquee] [--out FILE]

Common options: --lang pl|en  --currency PLN|EUR|USD  --delay SECONDS

Requires: requests  (pip install requests). XLSX output also needs: openpyxl.
"""
import argparse
import csv
import json
import sys
import time

try:
    import requests
except ImportError:
    sys.exit("This script needs the 'requests' package:  pip install requests")

BASE = "https://atlasetf.pl/api/v2"
USER_AGENT = "atlasetf-scraper/1.0 (+personal data pull; respects robots.txt)"

# Columns emitted for `list` CSV/XLSX, in a sensible order.
LIST_COLUMNS = [
    "isin", "ticker", "fund_name", "fund_provider", "fund_currency",
    "fund_size", "fund_size_currency", "expense_ratio",
    "replication_name_lang", "distribution_policy_lang",
    "distribution_frequency_lang", "domicile_lang", "inception_date",
    "currency_hedged_lang", "rating",
    "return_1m", "return_3m", "return_6m", "return_1y", "return_3y", "return_5y",
    "return_y0", "return_y1", "return_y2", "return_y3", "return_y4", "return_y5",
]


class AtlasClient:
    """Thin, polite client over the atlasetf.pl API."""

    def __init__(self, lang="pl", currency="PLN", delay=1.0, max_retries=4,
                 timeout=30):
        self.lang = lang
        self.currency = currency
        self.delay = delay            # min seconds between requests
        self.max_retries = max_retries
        self.timeout = timeout
        self._last_call = 0.0
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Origin": "https://atlasetf.pl",
            "Referer": "https://atlasetf.pl/",
        })

    def _throttle(self):
        wait = self.delay - (time.time() - self._last_call)
        if wait > 0:
            time.sleep(wait)

    def post(self, path, body):
        """POST with throttling + exponential backoff. Returns parsed JSON."""
        url = f"{BASE}/{path.lstrip('/')}"
        backoff = self.delay if self.delay > 0 else 1.0
        last_err = None
        for attempt in range(self.max_retries):
            self._throttle()
            try:
                r = self.session.post(url, data=json.dumps(body),
                                      timeout=self.timeout)
                self._last_call = time.time()
                if r.status_code == 200:
                    return r.json()
                if r.status_code == 403:
                    raise RuntimeError(
                        f"{path} returned 403 (login required / out of scope).")
                if r.status_code in (429, 500, 502, 503, 504):
                    last_err = f"HTTP {r.status_code}"
                    eprint(f"  {path}: {last_err}, retrying in {backoff:.0f}s "
                           f"(attempt {attempt+1}/{self.max_retries})")
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                raise RuntimeError(f"{path} returned HTTP {r.status_code}: "
                                   f"{r.text[:200]}")
            except requests.RequestException as e:
                last_err = str(e)
                self._last_call = time.time()
                eprint(f"  {path}: {last_err}, retrying in {backoff:.0f}s "
                       f"(attempt {attempt+1}/{self.max_retries})")
                time.sleep(backoff)
                backoff *= 2
        raise RuntimeError(f"{path} failed after {self.max_retries} attempts: "
                           f"{last_err}")

    # -- screener ---------------------------------------------------------
    def _empty_filter(self, page, page_size, search, sort, order):
        return {
            "class": None, "class_name": None, "investment_area": [],
            "global_category": [], "morningstar_category": [],
            "fund_yield_12m": [], "fi_average_yield_to_maturity": [],
            "fi_effective_maturity": [], "fi_average_effective_duration": [],
            "brokers": [], "broker_accounts": [], "groups": [], "providers": [],
            "distribution_policy": None, "exchanges": [], "trade_currencies": [],
            "domiciles": [], "replication": [], "age": None, "ter": [],
            "fund_size": None, "currency_risk": None, "xlm": [],
            "strategy_risks": [], "distribution_frequencies": [],
            "matching_index": None, "search_filter": search,
            "page": page, "row_per_page": page_size,
            "sort_field": sort, "sort_order": order, "ratings": [],
        }

    def search_page(self, page, page_size=100, search=None,
                    sort="fund_name", order="asc"):
        body = {
            "filter": self._empty_filter(page, page_size, search, sort, order),
            "lang": self.lang, "currency": self.currency,
        }
        return self.post("etf/search", body)

    def search_all(self, page_size=100, search=None, sort="fund_name",
                   order="asc", max_pages=None):
        """Yield ETF rows across all pages."""
        first = self.search_page(1, page_size, search, sort, order)
        rows = first.get("etfs", [])
        try:
            total = int(first.get("row_count") or len(rows))
        except (TypeError, ValueError):
            total = len(rows)
        total_pages = max(1, -(-total // page_size))  # ceil
        if max_pages:
            total_pages = min(total_pages, max_pages)
        eprint(f"Total matching funds: {total} -> {total_pages} page(s) "
               f"of {page_size}")
        for r in rows:
            yield r
        for page in range(2, total_pages + 1):
            eprint(f"  page {page}/{total_pages}")
            data = self.search_page(page, page_size, search, sort, order)
            for r in data.get("etfs", []):
                yield r

    # -- detail -----------------------------------------------------------
    def detail(self, isin, endpoints=("details",)):
        body = {"isin": isin, "lang": self.lang, "currency": self.currency}
        out = {"isin": isin}
        for ep in endpoints:
            try:
                out[ep] = self.post(f"etf/{ep}", body)
            except RuntimeError as e:
                out[ep] = {"_error": str(e)}
        return out

    # -- prices -----------------------------------------------------------
    def prices(self, feeds=("main", "marquee")):
        out = {}
        if "main" in feeds:
            out["main_page_quotes"] = self.post("etf/main-page-quotes",
                                                {"lang": self.lang})
        if "marquee" in feeds:
            out["ticker_marquee_quotes"] = self.post(
                "etf/ticker-marquee-quotes", {"lang": self.lang})
        return out


def eprint(*a):
    print(*a, file=sys.stderr, flush=True)


# -- output helpers -------------------------------------------------------
def write_rows(rows, out, fmt, columns):
    if fmt == "json":
        _dump_json(rows, out)
    elif fmt == "csv":
        _write_csv(rows, out, columns)
    elif fmt == "xlsx":
        _write_xlsx(rows, out, columns)
    else:
        sys.exit(f"Unknown format: {fmt}")


def _dump_json(obj, out):
    if out:
        with open(out, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        eprint(f"Wrote {out}")
    else:
        print(json.dumps(obj, ensure_ascii=False, indent=2))


def _write_csv(rows, out, columns):
    cols = columns or (list(rows[0].keys()) if rows else [])
    f = open(out, "w", newline="", encoding="utf-8-sig") if out else sys.stdout
    try:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    finally:
        if out:
            f.close()
            eprint(f"Wrote {len(rows)} rows -> {out}")


def _write_xlsx(rows, out, columns):
    try:
        from openpyxl import Workbook
    except ImportError:
        sys.exit("XLSX output needs openpyxl:  pip install openpyxl")
    if not out:
        sys.exit("--out is required for xlsx format")
    cols = columns or (list(rows[0].keys()) if rows else [])
    wb = Workbook()
    ws = wb.active
    ws.title = "ETFs"
    ws.append(cols)
    for r in rows:
        ws.append([r.get(c) for c in cols])
    wb.save(out)
    eprint(f"Wrote {len(rows)} rows -> {out}")


# -- CLI ------------------------------------------------------------------
def main(argv=None):
    p = argparse.ArgumentParser(description="Scrape ETF data from atlasetf.pl")
    p.add_argument("--lang", default="pl", choices=["pl", "en"])
    p.add_argument("--currency", default="PLN", choices=["PLN", "EUR", "USD"])
    p.add_argument("--delay", type=float, default=1.0,
                   help="Min seconds between requests (politeness; default 1.0)")
    sub = p.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("list", help="ETF screener -> CSV/XLSX/JSON")
    pl.add_argument("--search", help="Free-text filter (name/ticker/ISIN)")
    pl.add_argument("--sort", default="fund_name")
    pl.add_argument("--order", default="asc", choices=["asc", "desc"])
    pl.add_argument("--page-size", type=int, default=100)
    pl.add_argument("--max-pages", type=int, default=None,
                    help="Stop after N pages (for sampling)")
    pl.add_argument("--out")
    pl.add_argument("--format", default="csv", choices=["csv", "xlsx", "json"])

    pd = sub.add_parser("detail", help="Per-ETF fundamentals -> JSON/CSV")
    pd.add_argument("isins", nargs="+", help="One or more ISINs")
    pd.add_argument("--endpoints", default="details",
                    help="Comma-separated: details,extdata,allocations,"
                         "dividend,documents,currency")
    pd.add_argument("--out")
    pd.add_argument("--format", default="json", choices=["json", "csv"])

    pp = sub.add_parser("prices", help="Homepage quote/price feeds -> JSON")
    pp.add_argument("--feeds", default="main,marquee",
                    help="Comma-separated: main,marquee")
    pp.add_argument("--out")

    args = p.parse_args(argv)
    client = AtlasClient(lang=args.lang, currency=args.currency,
                         delay=args.delay)

    if args.cmd == "list":
        rows = list(client.search_all(
            page_size=args.page_size, search=args.search,
            sort=args.sort, order=args.order, max_pages=args.max_pages))
        cols = LIST_COLUMNS if args.format in ("csv", "xlsx") else None
        write_rows(rows, args.out, args.format, cols)

    elif args.cmd == "detail":
        endpoints = tuple(e.strip() for e in args.endpoints.split(",") if e.strip())
        results = [client.detail(isin, endpoints) for isin in args.isins]
        if args.format == "json":
            _dump_json(results if len(results) > 1 else results[0], args.out)
        else:  # flat CSV of the 'details' payload
            flat = [r.get("details", {}) for r in results
                    if isinstance(r.get("details"), dict)]
            _write_csv(flat, args.out, None)

    elif args.cmd == "prices":
        feeds = tuple(f.strip() for f in args.feeds.split(",") if f.strip())
        _dump_json(client.prices(feeds), args.out)


if __name__ == "__main__":
    main()

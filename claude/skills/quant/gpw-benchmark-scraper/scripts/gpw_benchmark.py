#!/usr/bin/env python3
"""
GPW Benchmark scraper (gpwbenchmark.pl).

Fetches three kinds of data that the gpwbenchmark.pl front end loads from its
own backend:

  1. rates    -> WIBID & WIBOR delayed reference rates (year-to-date table from
                 /dane-opoznione), one business-day delayed.
  2. indices  -> the full list of stock / bond / strategy indices with their
                 ISINs and latest snapshot (from ajaxindex.php?action=GPWIndexes).
  3. series   -> per-index historical OHLC time series (from chart-json.php),
                 for one/many ISINs or every index.

Output is CSV.

------------------------------------------------------------------------------
IMPORTANT - terms of use
------------------------------------------------------------------------------
WIBID(R) and WIBOR(R) are regulated reference rates administered by
GPW Benchmark S.A. The delayed data is published for informational purposes;
REDISTRIBUTION or use of WIBOR/WIBID in automated trading / non-visualised
applications requires a Market Data License Agreement with GPW Benchmark.
Index data is likewise a commercial product. Scrape considerately, do not
redistribute, and check https://gpwbenchmark.pl/robots.txt and the site's
terms before any bulk or repeated pull. This script defaults to ~1 request/sec.
------------------------------------------------------------------------------

Requires: requests, beautifulsoup4
    pip install requests beautifulsoup4
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from datetime import UTC, datetime

try:
    from zoneinfo import ZoneInfo

    _WARSAW = ZoneInfo("Europe/Warsaw")
except Exception:  # pragma: no cover - fallback if tzdata missing
    _WARSAW = None

try:
    import requests
except ImportError:
    sys.exit("Missing dependency: pip install requests beautifulsoup4")

try:
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit("Missing dependency: pip install beautifulsoup4")


BASE = "https://gpwbenchmark.pl"
USER_AGENT = (
    "gpw-benchmark-scraper/1.0 (personal data collection; "
    "respects robots.txt; contact: set-your-email)"
)

# Index category tabs used by ajaxindex.php?action=GPWIndexes&tab=...
# (these match the section anchors on /notowania)
INDEX_TABS = [
    "indexes",  # Indeksy glowne (main indices)
    "macroindices",  # Makroindeksy
    "indexes_other",  # Indeksy pozostale
    "national",  # Indeksy narodowe
    "sectorbased",  # Indeksy sektorowe
    "indexes_strategy",  # Indeksy strategii
    "benchmarks",  # Benchmarki
    "tbsp",  # Indeksy obligacji (bonds)
]

# Chart windows accepted by chart-json.php. "MAX" is a client-side zoom only and
# returns no data from the server, so it is intentionally excluded.
SERIES_MODES = ["14D", "1M", "3M", "6M", "1R"]


# --------------------------------------------------------------------------- #
# HTTP                                                                        #
# --------------------------------------------------------------------------- #
class Client:
    def __init__(self, lang: str = "PL", delay: float = 1.0, retries: int = 4, timeout: int = 30):
        self.lang = lang.upper()
        self.delay = delay
        self.retries = retries
        self.timeout = timeout
        self.s = requests.Session()
        self.s.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/json,*/*",
                "Accept-Language": "pl,en;q=0.8",
                "Referer": BASE + "/notowania",
            }
        )
        self._last = 0.0

    def _throttle(self):
        wait = self.delay - (time.time() - self._last)
        if wait > 0:
            time.sleep(wait)

    def get(self, url: str, params=None) -> requests.Response:
        last_err = None
        for attempt in range(self.retries):
            self._throttle()
            try:
                r = self.s.get(url, params=params, timeout=self.timeout)
                self._last = time.time()
                if r.status_code == 200:
                    return r
                if r.status_code in (429, 500, 502, 503, 504):
                    last_err = f"HTTP {r.status_code}"
                    time.sleep(self.delay * (2**attempt))
                    continue
                r.raise_for_status()
            except requests.RequestException as e:
                last_err = str(e)
                self._last = time.time()
                time.sleep(self.delay * (2**attempt))
        raise RuntimeError(f"GET failed after {self.retries} tries ({url}): {last_err}")


# --------------------------------------------------------------------------- #
# Parsing helpers                                                             #
# --------------------------------------------------------------------------- #
_NUM_CLEAN = str.maketrans({" ": "", " ": ""})


def _num(text: str):
    """'2 265,43' / '3,53' / ' - ' -> float or None."""
    if text is None:
        return None
    t = text.translate(_NUM_CLEAN).strip()
    if t in ("", "-", "–", "N/A"):
        return None
    t = t.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def extract_cdata_html(raw: str) -> str:
    """ajaxindex.php wraps the fragment in <response><html><![CDATA[ ... ]]>."""
    m = re.search(r"<!\[CDATA\[(.*?)\]\]>", raw, re.S)
    return m.group(1) if m else raw


# --------------------------------------------------------------------------- #
# 1. WIBID / WIBOR rates                                                      #
# --------------------------------------------------------------------------- #
def parse_rates(html: str):
    """Return (columns, rows) from the /dane-opoznione WIBID/WIBOR table.

    Header is two rows: group row (WIBID colspan=N, WIBOR colspan=M) + tenor row
    (Data/Termin, ON, 1M, ...). Columns come out as ['Date','WIBID_ON',...].
    """
    soup = BeautifulSoup(html, "html.parser")
    table = None
    for t in soup.find_all("table"):
        txt = t.get_text(" ", strip=True)
        if "WIBID" in txt and "WIBOR" in txt:
            table = t
            break
    if table is None:
        raise RuntimeError("WIBID/WIBOR table not found on page")

    rows = table.find_all("tr")
    # group row -> ordered (label, span)
    group_cells = rows[0].find_all(["th", "td"])
    groups = []
    for c in group_cells:
        label = c.get_text(strip=True).replace("®", "")  # drop (R)
        span = int(c.get("colspan") or 1)
        groups.append((label, span))
    # expand groups to a per-column prefix, skipping the leading empty cell
    prefixes = []
    for label, span in groups:
        for _ in range(span):
            prefixes.append(label)
    # tenor row
    tenor_cells = rows[1].find_all(["th", "td"])
    tenors = [c.get_text(strip=True) for c in tenor_cells]

    columns = ["Date"]
    # tenors[0] is "Data/Termin"; align remaining tenors with prefixes.
    # prefixes has one entry per group-column. The first group cell is empty
    # (covers the date column), so prefixes[0] == "" lines up with tenors[0].
    for i in range(1, len(tenors)):
        prefix = prefixes[i] if i < len(prefixes) else ""
        prefix = prefix.strip()
        columns.append(f"{prefix}_{tenors[i]}" if prefix else tenors[i])

    out = []
    for r in rows[2:]:
        cells = [c.get_text(strip=True) for c in r.find_all(["td", "th"])]
        if not cells or not re.match(r"^\d{4}-\d{2}-\d{2}$", cells[0]):
            continue
        rec = {"Date": cells[0]}
        for i in range(1, len(columns)):
            rec[columns[i]] = _num(cells[i]) if i < len(cells) else None
        out.append(rec)
    return columns, out


def cmd_rates(client: Client, args):
    path = "/en-dane-opoznione" if client.lang == "EN" else "/dane-opoznione"
    r = client.get(BASE + path)
    columns, rows = parse_rates(r.text)
    out = args.out or "wibid_wibor.csv"
    write_csv(out, columns, rows)
    print(f"rates: wrote {len(rows)} days x {len(columns) - 1} tenors -> {out}")


# --------------------------------------------------------------------------- #
# 2. Index list                                                               #
# --------------------------------------------------------------------------- #
# Polish column header -> canonical key + whether it is numeric
_HEADER_MAP = {
    "skrót": ("shortcode", False),
    "liczba spółek": ("num", True),
    "liczba instrumentów": ("num", True),
    "czas ost. pub.": ("last_time", False),
    "twi": ("twi", True),
    "kurs otw.": ("open", True),
    "kurs min.": ("min", True),
    "kurs maks.": ("max", True),
    "wart. ost.": ("last", True),
    "zmiana do odn. (w %)": ("change_pct", True),
    "% otw. portfela": ("portfolio_pct", True),
    "wartość obrotu skum. (w tys. zł)": ("turnover_thousands_pln", True),
    # English column variants
    "abbrev.": ("shortcode", False),
    "no. of companies": ("num", True),
    "last publ. time": ("last_time", False),
    "open price": ("open", True),
    "min. price": ("min", True),
    "max. price": ("max", True),
    "last value": ("last", True),
    "change to ref. (in %)": ("change_pct", True),
}

INDEX_COLUMNS = [
    "category",
    "section",
    "shortcode",
    "isin",
    "cmng_id",
    "num",
    "last_time",
    "twi",
    "open",
    "min",
    "max",
    "last",
    "change_pct",
    "portfolio_pct",
    "turnover_thousands_pln",
]


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip().lower()


def parse_index_table(html: str, category: str):
    """Parse an ajaxindex GPWIndexes fragment (may hold several tables) into
    one record per index, mapping each table's own header labels to columns."""
    soup = BeautifulSoup(extract_cdata_html(html), "html.parser")
    out = []
    for table in soup.find_all("table"):
        # section caption sits in the .cardBox <p> right before the table
        section = ""
        prev = table.find_previous(class_="cardBox")
        if prev:
            section = prev.get_text(strip=True)
        # header labels (skip the leading empty chart column at index 0)
        head = table.find("thead")
        header_cells = head.find_all(["th", "td"]) if head else []
        labels = [_norm(c.get_text()) for c in header_cells]
        for tr in table.find_all("tr"):
            link = tr.find("a", href=re.compile(r"karta-indeksu\?isin="))
            if not link:
                continue
            m = re.search(r"isin=([A-Z0-9]+)", link.get("href", ""))
            if not m:
                continue
            rec = {k: None for k in INDEX_COLUMNS}
            rec["category"] = category
            rec["section"] = section
            rec["isin"] = m.group(1)
            rec["shortcode"] = link.get_text(strip=True)
            chart = tr.find("a", onclick=True)
            if chart:
                cm = re.search(r"getChartModal\('[^']*','[^']*',(\d+)\)", chart.get("onclick", ""))
                if cm:
                    rec["cmng_id"] = cm.group(1)
            cells = tr.find_all("td")
            for i, td in enumerate(cells):
                if i >= len(labels):
                    break
                key_info = _HEADER_MAP.get(labels[i])
                if not key_info:
                    continue
                key, is_num = key_info
                if key == "shortcode":
                    continue  # already captured from the link
                val = td.get_text(strip=True)
                rec[key] = _num(val) if is_num else (val or None)
            out.append(rec)
    return out


def cmd_indices(client: Client, args):
    tabs = args.tabs or INDEX_TABS
    all_rows = []
    seen = set()
    for tab in tabs:
        url = f"{BASE}/ajaxindex.php"
        params = {"action": "GPWIndexes", "start": "showTable", "tab": tab, "lang": client.lang}
        try:
            r = client.get(url, params=params)
            rows = parse_index_table(r.text, tab)
        except Exception as e:
            print(f"  ! tab '{tab}' failed: {e}", file=sys.stderr)
            continue
        for rec in rows:
            key = rec["isin"]
            if key in seen:
                continue
            seen.add(key)
            all_rows.append(rec)
        print(f"  tab '{tab}': {len(rows)} indices")
    columns = INDEX_COLUMNS
    out = args.out or "indices.csv"
    write_csv(out, columns, all_rows)
    print(f"indices: wrote {len(all_rows)} unique indices -> {out}")
    return all_rows


# --------------------------------------------------------------------------- #
# 3. Historical OHLC series                                                   #
# --------------------------------------------------------------------------- #
def _epoch_to_date(t: int) -> str:
    dt = datetime.fromtimestamp(int(t), tz=UTC)
    if _WARSAW is not None:
        dt = dt.astimezone(_WARSAW)
    return dt.strftime("%Y-%m-%d")


def fetch_series(client: Client, isins, mode: str):
    """chart-json.php accepts an array of {isin, mode}; batch several at once."""
    req = [{"isin": i, "mode": mode} for i in isins]
    params = {"req": json.dumps(req, separators=(",", ":")), "t": str(int(time.time() * 1000))}
    r = client.get(BASE + "/chart-json.php", params=params)
    try:
        payload = r.json()
    except json.JSONDecodeError:
        payload = json.loads(r.text)
    rows = []
    for block in payload:
        isin = block.get("isin")
        for pt in block.get("data", []) or []:
            rows.append(
                {
                    "isin": isin,
                    "date": _epoch_to_date(pt["t"]),
                    "timestamp": pt["t"],
                    "open": pt.get("o"),
                    "high": pt.get("h"),
                    "low": pt.get("l"),
                    "close": pt.get("c"),
                }
            )
    return rows


def cmd_series(client: Client, args):
    mode = args.mode
    if mode not in SERIES_MODES:
        sys.exit(f"--mode must be one of {SERIES_MODES} (MAX is client-side only)")

    if args.all:
        idx = cmd_indices(client, argparse.Namespace(tabs=None, out="indices.csv"))
        isins = [r["isin"] for r in idx]
    else:
        isins = args.isins
    if not isins:
        sys.exit("Provide ISINs or use --all")

    batch = max(1, args.batch)
    all_rows = []
    for i in range(0, len(isins), batch):
        chunk = isins[i : i + batch]
        try:
            rows = fetch_series(client, chunk, mode)
        except Exception as e:
            print(f"  ! batch {chunk} failed: {e}", file=sys.stderr)
            continue
        all_rows.extend(rows)
        print(f"  {min(i + batch, len(isins))}/{len(isins)} indices ({len(all_rows)} rows)")
    columns = ["isin", "date", "timestamp", "open", "high", "low", "close"]
    out = args.out or f"series_{mode}.csv"
    write_csv(out, columns, all_rows)
    print(f"series[{mode}]: wrote {len(all_rows)} rows -> {out}")


# --------------------------------------------------------------------------- #
# all                                                                         #
# --------------------------------------------------------------------------- #
def cmd_all(client: Client, args):
    cmd_rates(client, argparse.Namespace(out="wibid_wibor.csv"))
    idx = cmd_indices(client, argparse.Namespace(tabs=None, out="indices.csv"))
    cmd_series(
        client,
        argparse.Namespace(
            all=False,
            isins=[r["isin"] for r in idx],
            mode=args.mode,
            batch=args.batch,
            out=f"series_{args.mode}.csv",
        ),
    )


# --------------------------------------------------------------------------- #
# CSV                                                                         #
# --------------------------------------------------------------------------- #
def write_csv(path: str, columns, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


# --------------------------------------------------------------------------- #
# CLI                                                                         #
# --------------------------------------------------------------------------- #
def build_parser():
    p = argparse.ArgumentParser(description="Scrape GPW Benchmark data to CSV.")
    p.add_argument("--lang", default="PL", choices=["PL", "EN"])
    p.add_argument(
        "--delay", type=float, default=1.0, help="seconds between requests (default 1.0)"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("rates", help="WIBID/WIBOR delayed rates -> CSV")
    pr.add_argument("--out")

    pi = sub.add_parser("indices", help="all indices + ISINs -> CSV")
    pi.add_argument("--tabs", nargs="*", help=f"subset of {INDEX_TABS}")
    pi.add_argument("--out")

    ps = sub.add_parser("series", help="historical OHLC for ISIN(s) -> CSV")
    ps.add_argument("isins", nargs="*")
    ps.add_argument("--all", action="store_true", help="every index")
    ps.add_argument("--mode", default="1R", choices=SERIES_MODES)
    ps.add_argument("--batch", type=int, default=5, help="ISINs per chart-json request (default 5)")
    ps.add_argument("--out")

    pa = sub.add_parser("all", help="rates + indices + series for everything")
    pa.add_argument("--mode", default="1R", choices=SERIES_MODES)
    pa.add_argument("--batch", type=int, default=5)

    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    client = Client(lang=args.lang, delay=args.delay)
    if args.cmd == "rates":
        cmd_rates(client, args)
    elif args.cmd == "indices":
        cmd_indices(client, args)
    elif args.cmd == "series":
        cmd_series(client, args)
    elif args.cmd == "all":
        cmd_all(client, args)


if __name__ == "__main__":
    main()

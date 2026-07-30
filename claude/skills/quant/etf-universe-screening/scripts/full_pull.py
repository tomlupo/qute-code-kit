"""Price the FULL 2,285-ETF universe, not the pre-screened 138.

The v5 demand test let each fund pick its best benchmark out of a shortlist that had
already been curated down to 138. That bakes in the curation: a fund fits badly when the
right benchmark was filtered out upstream, and we cannot tell that apart from a genuine gap.
Pricing the whole xlsx population removes the pre-filter so demand can elect the top 100.

Resumable: every ISIN's outcome is checkpointed, reruns skip what is already done.
"""

import json
import os
import time

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()
K = os.environ["EODHD_API_KEY"]
BASE = "https://eodhd.com/api"
OUT = "data/processed/etf_prices/full_universe"
os.makedirs(OUT, exist_ok=True)
CKPT = f"{OUT}/resolution.jsonl"
SERIES = f"{OUT}/series"
os.makedirs(SERIES, exist_ok=True)

EXCH_RANK = {
    "XETRA": 9,
    "F": 8,
    "STU": 6,
    "MU": 5,
    "LSE": 7,
    "MI": 6,
    "PA": 6,
    "AS": 6,
    "SW": 6,
    "VX": 6,
    "WAR": 9,
    "IL": 4,
    "TA": 1,
    "US": 3,
}
CCY_RANK = {"USD": 3, "EUR": 3, "PLN": 3, "GBP": 2, "GBX": 0, "CHF": 2, "ILA": 0, "ILS": 0}


def sget(url, **params):
    params.update(api_token=K, fmt="json")
    for attempt in range(4):
        try:
            r = requests.get(url, params=params, timeout=30)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                time.sleep(2 + attempt * 2)
                continue
            return None
        except requests.RequestException:
            time.sleep(1 + attempt)
    return None


def choose(cands, pref_ccy):
    etf = [c for c in cands if c.get("Type") in ("ETF", "FUND", "ETC", "Currency", None)] or cands

    def score(c):
        s = EXCH_RANK.get(c.get("Exchange", ""), 2) + CCY_RANK.get(c.get("Currency", ""), 1)
        if pref_ccy and c.get("Currency") == pref_ccy:
            s += 6
        if pref_ccy == "PLN" and c.get("Exchange") == "WAR":
            s += 10
        if c.get("isPrimary"):
            s += 1
        return s

    return sorted(etf, key=score, reverse=True)[0] if etf else None


uni = pd.read_excel("data/raw/lista-etf-2026-06-02.xlsx").dropna(subset=["isin"])
uni = uni.drop_duplicates(subset=["isin"])
# currency preference read off the analizy unit code suffix (…_A_USD)
uni["pref_ccy"] = uni.kod_jednostki.str.extract(r"_([A-Z]{3})$")[0]

done = set()
if os.path.exists(CKPT):
    with open(CKPT) as fh:
        for line in fh:
            try:
                done.add(json.loads(line)["isin"])
            except (json.JSONDecodeError, KeyError):
                pass
todo = uni[~uni.isin_.isin(done)] if "isin_" in uni.columns else uni[~uni["isin"].isin(done)]
print(f"universe={len(uni)}  already done={len(done)}  todo={len(todo)}", flush=True)

ck = open(CKPT, "a")
for n, (_, row) in enumerate(todo.iterrows(), 1):
    code = row["isin"]
    pref = row["pref_ccy"] if isinstance(row["pref_ccy"], str) else None
    rec = {"isin": code, "code": row["kod_jednostki"], "name": row["nazwa_jednostki"]}
    cands = sget(f"{BASE}/search/{code}")
    if not cands:
        rec.update(status="no_search_result", n_obs=0)
    else:
        ch = choose(cands, pref)
        ticker = f"{ch['Code']}.{ch['Exchange']}"
        rec.update(chosen=ticker, currency=ch.get("Currency"), n_cands=len(cands))
        eod = sget(f"{BASE}/eod/{ticker}", period="d", **{"from": "2018-01-01"})
        if not eod or not isinstance(eod, list) or len(eod) < 30:
            rec.update(status="no_or_thin_prices", n_obs=len(eod) if isinstance(eod, list) else 0)
        else:
            s = pd.DataFrame(eod)[["date", "adjusted_close"]].dropna()
            s["date"] = pd.to_datetime(s["date"])
            s = s.set_index("date")["adjusted_close"].sort_index()
            if ch.get("Currency") == "GBX":
                s = s / 100.0
                rec["currency"] = "GBP"
            s.to_frame("price").to_parquet(f"{SERIES}/{code}.parquet")
            rec.update(
                status="ok",
                n_obs=len(s),
                first=str(s.index.min().date()),
                last=str(s.index.max().date()),
            )
    ck.write(json.dumps(rec) + "\n")
    ck.flush()
    if n % 100 == 0:
        print(f"  {n}/{len(todo)}", flush=True)
    time.sleep(0.05)
ck.close()
print("DONE", flush=True)

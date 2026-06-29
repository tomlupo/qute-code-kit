# EODHD — coverage, plan limits, ISIN→listing pinning

Field notes for the EODHD source (`source='eodhd'`, `scripts/fetch_eodhd.py`,
repo client `src/shared/fetch/eodhd.py`). Verified 2026-06-29 on the paid EOD plan
against the dm-evo Bloomberg securities master (`config_market.xlsx`, 829 rows).

## Plan limits — daily refresh fits easily

- Paid EOD plan: **100,000 requests/day**; EOD = **1 request / ticker / day**.
- Full daily refresh of ~400 ETFs is <1% of the cap. Daily cadence is a non-issue.
- Cheaper bulk path: `eod-bulk-last-day/{EXCHANGE}` returns a whole exchange in one
  call — use it when refreshing many tickers on the same exchange.
- Check usage/limit: `GET https://eodhd.com/api/user?api_token=KEY` →
  `apiRequests`, `dailyRateLimit`.

## What the EOD plan does NOT include

- **ETF holdings** (`/api/fundamentals`) → `Forbidden` on the EOD-only plan;
  needs the Fundamentals add-on. Even with it, EODHD ships only the **current**
  holdings snapshot — **no historical constituents**. For historical ETF holdings
  use Bloomberg or the issuer's own holdings files.
- **MSCI / proprietary NR-TR indices** — not licensed: MSCI World (`MXWO`),
  EStoxx50 NR (`SX5T`), Stoxx600 NR (`SXXR`), S&P NTR variants all return empty.
  Native **price** indices do exist: `GSPC.INDX` (S&P 500), `GDAXI.INDX`,
  `STOXX50E.INDX`, `N100.INDX`, `BCOM.INDX`. Track MSCI World via an ETF proxy
  (`IWDA.LSE`, `SWDA.LSE`, `URTH.US`, `EUNL.XETRA`).

## Coverage on the securities master (829 rows)

| Type | Total | EODHD | Note |
|---|---|---|---|
| ETP (ETF/ETC) | 406 | **388 (96%)** | ISIN-resolvable; the tradeable feed |
| Equity / FI / Commodity Index | 372 | native price only | NR/TR variants absent (see above) |
| FX (CROSS/SPOT/FWD) | 24 | via `/forex` | not ISIN-keyed |
| SWAP / futures / OEF | 17 | ~none | Bloomberg-proprietary |

The 18 ETP misses are delisted / rebranded share classes (Lyxor→Amundi),
sanctioned Russia ETFs, and Swiss crypto ETPs — not a feed gap.

## Pinning ISIN → exact listing (do this, don't fetch by ISIN alone)

One ISIN has many EODHD listings (exchange × currency × Acc/Dist). Resolve to ONE
`CODE.EXCHANGE` by matching **exchange + currency** — both carried by a
Bloomberg-style master (`exch_code`, `currency`):

```python
import requests
res = requests.get(f"https://eodhd.com/api/search/{isin}",
                   params={"api_token": KEY, "fmt": "json", "limit": 50}).json()
# each record: {Code, Exchange, Currency, ISIN, isPrimary, previousClose, ...}
BBG_TO_EODHD = {"LN":"LSE","GR":"XETRA","GY":"XETRA","FP":"PA","IM":"MI",
                "SW":"SW","NA":"AS","SE":"ST","US":"US","PW":"WAR","WARSAW":"WAR"}
want = BBG_TO_EODHD[exch_code]
on_exch = [x for x in res if x["Exchange"] == want]
exact   = [x for x in on_exch if x["Currency"] in (ccy, "GBX" if ccy == "GBP" else ccy)]
pick    = exact[0] if exact else None
eodhd_symbol = f"{pick['Code']}.{pick['Exchange']}"
```

Matching exchange+currency uniquely pins **83%** of the ETP universe (335/406).
**Persist the resolved `eodhd_symbol` in config** (single source of truth) so the
daily feed is deterministic and never re-resolves the ISIN.

### Gotchas

- **GBX vs GBP** — LSE quotes in **pence**. Same listing, not a different ticker:
  set `price_scale = 0.01` when EODHD `Currency == "GBX"` and config wants `GBP`.
- **SIX Swiss** encodes currency in the code (`HODL-USD.SW`) — currency match picks
  the right line automatically.
- **Missing exchange** — some Milan (`IM`) / Stockholm (`SE`) lines aren't in EODHD;
  the same fund exists on LSE/XETRA in a different currency. Flag `needs_review`
  rather than silently feeding a different-currency proxy.

### Resolution status buckets

When building a `config_ticker → eodhd_symbol` map, classify each row and carry a
`needs_review` flag:

| Status | Meaning | scale | review |
|---|---|---|---|
| `EXACT` | unique exchange+currency match | 1 | no |
| `GBX_SCALED` | LSE pence quote vs GBP config | 0.01 | no |
| `EXACT_MULTI` | several exact lines; pick `isPrimary` | 1 | no |
| `EXCH_ONLY_CCY_DIFF` | right exchange, currency differs (non-GBX) | 1 | **yes** |
| `EXCH_MULTI_CCY` | ambiguous currency on exchange | 1 | **yes** |
| `ALT_EXCHANGE` | ISIN not on configured exchange; fungible alt | 1 | **yes** |
| `NOT_FOUND` | ISIN absent from EODHD | — | **yes** |

On the 406-ETP master this yields **348 auto-usable**, 58 `needs_review`.

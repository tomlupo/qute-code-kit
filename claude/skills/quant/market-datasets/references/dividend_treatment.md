# Dividend Treatment in Market Data Sources

How the price sources this skill fetches from handle dividends, and the one
trap that loses them silently.

## Quick Reference

| Source | Raw close | Adjusted close | Corporate actions |
|--------|-----------|----------------|-------------------|
| **Yahoo Finance** | `Close` | `Adj_Close` | Yes — dividends, splits (`fetch_yahoo_direct.py`) |
| **EODHD** | `Close` | `Adj_Close` (from `adjusted_close`) | Separate endpoints (`/api/div/`, `/api/splits/`) — not wrapped by this skill |
| **NBP** | N/A | N/A | N/A (FX rates only) |
| **FRED** | N/A | N/A | N/A (economic data) |

Both price sources give you **both** series. Pick by purpose:

| Need | Column |
|------|--------|
| Actual trading price, P&L on a trade | `Close` (raw) + dividends received, separately |
| Returns, performance attribution, backtests | `Adj_Close` — or raw `Close` chained with dividends yourself |

---

## How an adjusted series is built

For a dividend `D` with ex-date `t_ex`, every price **before** `t_ex` is
multiplied by

```
factor = (close[t_ex - 1] - D) / close[t_ex - 1]
```

Prices on and after the ex-date are untouched. Multiple dividends compound, so
older history carries larger cumulative adjustments. Returns computed from the
adjusted series are total returns (dividends reinvested on the ex-date).

### Example: XTB dividend (5.45 PLN, ex-div 2025-06-13), Yahoo

```
Date        Close    Adj_Close   Difference
2025-06-10  80.58    75.00       5.58 (adjusted for the dividend)
2025-06-11  79.82    74.29       5.53
2025-06-12  78.64    73.19       5.45 (= dividend amount, last cum-div day)
2025-06-13  74.12    74.12       0.00 (ex-div, no adjustment)
```

---

## The trap: adjusted levels are rewritten backwards

An adjusted series is **not append-only**. On every new dividend the provider
recomputes the whole history before the ex-date. EODHD recomputes
`adjusted_close` on every dividend; Yahoo's `Adj_Close` behaves the same way.

So if you store adjusted **levels** and append each day's new rows to what you
stored earlier, the old rows keep the pre-dividend scale while the new rows are
on the post-dividend scale — the ratio across the seam equals the raw price
ratio, and **the dividend disappears from your return series**.

Two correct ways to keep a history incrementally:

1. **Chain returns, not levels.** Store daily returns computed within one fetch
   (`adj.pct_change()`), append new returns, and rebuild the level from the
   chained returns when needed. A return between two rows fetched together is
   consistent even though both levels later get rescaled.
2. **Store raw `Close` + dividends**, and compute total return yourself:
   `r_t = (close_t + D_t) / close_{t-1} - 1`, with `D_t` on the ex-date.

Or re-fetch the full adjusted history every time and overwrite — never splice
an old adjusted fetch onto a new one.

---

## Yahoo Finance

`fetch_yahoo_direct.py` returns prices with both `close` and `adj_close`, plus
dividends (`events=div`), splits (`events=splits`) or both.

```python
import yfinance as yf

t = yf.Ticker('XTB.WA')
t.dividends   # Date, amount
t.splits      # Date, ratio
t.actions     # Date, Dividends, Stock Splits
```

## EODHD

`fetch_eodhd.py` maps `close` → `Close` and `adjusted_close` → `Adj_Close`.
Polish listings are `.WAR` (e.g. `XTB.WAR`). Dividend amounts come from a
separate EODHD endpoint the skill does not wrap; check your plan before relying
on it. Coverage and plan limits: [eodhd.md](eodhd.md).

---

## Cross-source validation

Yahoo `Adj_Close` and EODHD `Adj_Close` for the same listing should agree up to
rounding and ex-date convention. Compare **returns** over a window both fetched
at the same time, not stored levels (see the trap above):

```python
r_y = yahoo['Adj_Close'].pct_change()
r_e = eodhd['Adj_Close'].pct_change()
gap = (r_y - r_e).abs()
assert gap.max() < 0.005, f"return mismatch up to {gap.max():.4f}"
```

A persistent gap usually means a different ex-date convention or a missed
corporate action on one side.

---

## Key dates terminology

- **Last cum-dividend date** (ostatnie notowanie z prawem do dywidendy) — last
  trading day a buyer is entitled to the dividend (XTB: 2025-06-12).
- **Ex-dividend date** — first trading day without the right, usually the next
  business day (XTB: 2025-06-13). Yahoo reports the dividend on this date.
- **Record date** — when the company fixes the entitled shareholders.
- **Payment date** (dzień wypłaty) — when cash is paid (XTB: 2025-06-25).

---

## Summary

| Need | Source | Column / field |
|------|--------|----------------|
| Dividend-adjusted prices | Yahoo or EODHD | `Adj_Close` (re-fetch in full, never splice levels) |
| Raw prices | Yahoo or EODHD | `Close` |
| Dividend amounts | Yahoo (`fetch_yahoo_direct.py`) | dividends |
| Incrementally maintained total return | Either | chained returns, or raw `Close` + dividends |
| Actual P&L | Either | `Close` + dividends received |

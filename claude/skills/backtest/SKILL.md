---
name: backtest
description: "MANDATORY for any portfolio backtest, strategy comparison, or signal-methodology iteration. Covers static weight backtests (vectorbt wrapper), dynamic signal-driven strategies, and component-level experiments on existing composite signals. Triggers: backtest, compare strategies, rebalancing, portfolio simulation, signal variant testing, overlay component, weight sweep, baseline comparison, scoring methodology change. NEVER write ad-hoc backtest loops for production strategies."
---

# Portfolio Allocation Backtest

Weight-based portfolio backtesting using vectorbt. Handles drift, rebalancing, fees, and multi-strategy comparison.

## Quick Start

```python
from src.vectorbt_tools.backtesting import run
import pandas as pd

prices = pd.read_parquet("prices.parquet")
w_strategy = pd.DataFrame({"BOND": 0.6, "EQ": 0.3, "GOLD": 0.1}, index=prices.index)
w_benchmark = pd.DataFrame({"BOND": 0.5, "EQ": 0.4, "GOLD": 0.1}, index=prices.index)

pf = run(prices, {"Strategy": w_strategy, "Benchmark": w_benchmark},
         rebalancing_freq="1M", fees=0.001)
print(pf.stats())
```

## Wrapper Module

Located at `src/vectorbt_tools/backtesting.py` (already in project). Also copied to `scripts/backtesting.py` within this skill for reference.

### `run()` API

```python
run(prices, weights, rebalancing_freq=1, threshold=None, fees=0.0,
    fixed_fees=0.0, slippage=0.0, use_order_func=None, use_numba=True)
```

| Param | Type | Description |
|-------|------|-------------|
| `prices` | DataFrame | Daily prices, DatetimeIndex, columns = tickers |
| `weights` | dict | `{strategy_name: weights_DataFrame}` |
| `rebalancing_freq` | None/int/str/list | None=buy-hold, "1M"=monthly, list=explicit dates |
| `threshold` | float | Drift threshold triggering rebalance (e.g., 0.05) |
| `fees` | float | Proportional cost (0.001 = 10bps) |

Returns `vbt.Portfolio` with `.stats()`, `.returns()`, `.drawdowns`, `.orders`, `.plot()`.

### Weight DataFrame Format

- **Index**: DatetimeIndex (same as prices or rebalance dates only)
- **Columns**: ticker names matching prices columns
- **Values**: decimals 0.0-1.0, summing to ~1.0
- For dynamic strategies, populate only rebalance dates — engine forward-fills

## Usage Patterns

### Static Weights

```python
pf = run(prices, {"Conservative": w_con, "Balanced": w_bal}, rebalancing_freq="1M")
```

### Dynamic Signal-Driven (TAA)

```python
rebalance_dates = pd.date_range("2016-01-31", "2025-12-31", freq="ME")
records = []
for date in rebalance_dates:
    w = compute_weights(signals[date], corridors[profile])
    records.append({"date": date, **w})

w_df = pd.DataFrame(records).set_index("date").reindex(prices.index).ffill()
pf = run(prices, {"TAA": w_df, "SAA": benchmark_df},
         rebalancing_freq=list(rebalance_dates), fees=0.001)
```

### Rebalancing Bands

```python
pf = run(prices, {"Band5pct": w_df}, rebalancing_freq="1M", threshold=0.05)
```

### Buy and Hold

```python
pf = run(prices, {"BuyHold": w_df}, rebalancing_freq=None)
```

## Portfolio Analytics — use vbt's Portfolio API

**Once you have a `pf` (vbt Portfolio), DO NOT re-roll metrics from `pf.returns()`.** The Portfolio object exposes everything below for free. Re-rolling drawdown peak-tracking from daily returns is the same anti-pattern as a manual backtest loop.

### Quick-reference

| Need | Use | Notes |
|---|---|---|
| Full stats table | `pf.stats(agg_func=None)` | 30+ metrics per strategy as DataFrame |
| Sharpe / IR / Sortino / Calmar | `pf.sharpe_ratio()`, `pf.sortino_ratio()`, `pf.calmar_ratio()` | Arithmetic by default — see Geometric note below |
| Max drawdown summary | `pf.max_drawdown()` | Single number per strategy |
| **Every drawdown event** | `pf.drawdowns.records_readable` | DataFrame: `start_idx`, `valley_idx`, `end_idx`, `drawdown`, `duration`, `recovery_duration`, `status` |
| Recovery durations | `pf.drawdowns.recovery_duration` | Series — time-to-recover per event |
| % time in drawdown | `pf.drawdowns.coverage` | Single number 0–1 |
| Per-asset value (attribution) | `pf.value(group_by=False)` | NAV per asset over time — decomposes "where the IR came from" |
| Per-asset returns | `pf.returns(group_by=False)` | Daily return per asset |
| Trades + costs | `pf.orders.records_readable`, `pf.total_fees_paid()` | All trades, realized fee total |
| Equity curve plot | `pf.plot()`, `pf.drawdowns.plot()` | Interactive Plotly out-of-the-box |
| Daily returns (last resort) | `pf.returns()` | Use only for custom math vbt doesn't already give you |

### Drawdown analysis within a named regime

Filter `pf.drawdowns.records_readable` by date range to attribute drawdown to specific regimes (COVID, 2022 rate shock, etc.). Don't re-implement peak-tracking with `cummax()` from `pf.returns()` — that path is already paved.

```python
dd = pf.drawdowns.records_readable
dd_in_window = dd[(dd['valley_idx'] >= '2020-01-01') & (dd['valley_idx'] <= '2021-12-31')]
worst_in_covid = dd_in_window.loc[dd_in_window['drawdown'].idxmin()]
print(worst_in_covid)  # peak/valley dates, magnitude, recovery duration — all there
```

### Per-asset attribution

Want to know "did the IR come from EQ_US tilts or COM_GOLD tilts?" Use ungrouped value:

```python
asset_nav = pf.value(group_by=False)        # per-asset NAV (DataFrame)
asset_contrib = asset_nav.diff().sum()      # total contribution per asset over period
print(asset_contrib.sort_values(ascending=False))
```

### Geometric Metrics (asset management convention)

vbt's built-in Sharpe is arithmetic-annualized (~0.1–0.3 higher than geometric). For advisory/asset-management contexts, derive geometric metrics from daily returns:

```python
rets = pf.returns()                          # DataFrame if multiple strategies
cum = (1 + rets).cumprod()
cagr = cum.iloc[-1] ** (252 / len(rets)) - 1
vol = rets.std() * np.sqrt(252)
sharpe = cagr / vol
```

This is the ONE place re-rolling metrics from `pf.returns()` is justified — the Sharpe convention difference matters and vbt doesn't expose a geometric variant.

### Synthetic cash NAV (for cash-equivalent assets)

When a strategy includes a cash sleeve that doesn't have a daily price series (e.g. WIBOR/3M T-bill carry), synthesize a NAV from the rate before passing to `run()`:

```python
# Rate in % → daily compounded NAV
daily_ret = rate_series.ffill() / 100 / 252
nav = (1 + daily_ret).cumprod()
prices['CASH_SLEEVE'] = nav  # now usable as a vbt asset
```

## Critical Rules

### 1. NEVER Write Ad-Hoc Backtest Loops

Always use `run()`. Manual `np.dot(weights, returns)` loops skip weight drift and produce inflated results (observed: Sharpe 1.37 without drift vs 0.93 with drift).

### 2. Weight Drift is Non-Negotiable

Between rebalance dates, weights drift with returns. The `run()` wrapper handles this. If you must debug weights, use `run()` then inspect `pf.orders.records_readable`.

### 3. Always Include a Benchmark

Compare TAA vs SAA in the same `run()` call so both use identical prices, dates, and fees.

### 4. Test Both Monthly and Quarterly

Quarterly with drift removes timing luck. Monthly shows signal strength. Always compare both.

### 5. Lookahead Bias

Signals at date T must use only data available before T:
```python
# WRONG
w.loc["2022-01-31"] = compute(data.loc[:"2022-01-31"])
# RIGHT
w.loc["2022-01-31"] = compute(data.loc[:"2021-12-31"])
```

**Subtle variant — pool normalization.** If your signal pipeline pools across (date × category) — e.g. Carver-style bucket-pooled or globally-pooled z-scores — that pool MUST be walk-forward too:

```python
# WRONG — full-panel pool applies 2026 info to 2018 dates
mu = panel["value_z"].mean()
panel["pooled"] = (panel["value_z"] - mu) / panel["value_z"].std()

# RIGHT — at each date T, μ/σ from data ≤ T (rolling 10Y / 5Y-min matches per-cat rolling_z)
for T in sorted(panel.date.unique()):
    window = panel.loc[(panel.date > T - 10Y) & (panel.date <= T), "value_z"].dropna()
    if nunique_dates(window) < 60: continue  # min 5Y
    mask = panel.date == T
    panel.loc[mask, "pooled"] = (panel.loc[mask, "value_z"] - window.mean()) / window.std()
```

Observed empirically (dm-evo TAA v4.14.1, 2026-04-24): full-panel pool inflated avg IR by ~13% vs the walk-forward version (+0.556 → +0.484). Per-cat rolling z inputs upstream did NOT protect us — the leakage was entirely in the pool layer. Cost to avoid: one `for T in dates` loop, negligible compute.

**Rule:** before locking any methodology that uses a pool, confirm IR against a walk-forward re-run. If ranking holds, lock against the walk-forward number.

## Detailed References

For advanced topics, see:

- [pitfalls.md](references/pitfalls.md) — Weight normalization, currency, transaction costs, corridor design
- [architecture.md](references/architecture.md) — Fully vectorized TAA backtest target architecture
- [signal-precompute.md](references/signal-precompute.md) — Signal precomputation patterns for speed

# Target Architecture: Fully Vectorized TAA Backtest

Three layers with different vectorization potential:

```
Layer 1 — Signal computation (vectorized, <1 sec)
  pandas DataFrame ops across all dates × all categories at once.

Layer 2 — Stage 3 normalization (loop, ~2 sec)
  Path-dependent within each date. Must loop per date × per profile.
  Independent across dates — can parallelize but not vectorize.

Layer 3 — Portfolio simulation (vectorized via vbt, <1 sec)
  Weight drift, rebalancing, fees — handled by run().
```

## Layer 1: Vectorized Signal Computation

```python
# Value z-scores: rolling z across entire history
value_z = pd.DataFrame()
for cat, series in value_series.items():
    rolling_mean = series.rolling(120, min_periods=84).mean()
    rolling_std = series.rolling(120, min_periods=84).std()
    value_z[cat] = (series - rolling_mean) / rolling_std

# Trend momentum: shift operations
for cat, col in TREND_PRICE_COL.items():
    price = df[col]
    mom6 = price.shift(1) / price.shift(7) - 1
    mom12 = price.shift(1) / price.shift(13) - 1
    trend_raw[cat] = 0.5 * mom6 + 0.5 * mom12

# Trend z-scores (mean-centered)
trend_z = (trend_raw - trend_raw.rolling(120, min_periods=84).mean()) / trend_raw.rolling(120, min_periods=84).std()

# Continuous scoring: element-wise clip
value_cont = (value_z / 1.5).clip(-1, 1)
trend_cont = (trend_z / 1.5).clip(-1, 1)
stage1 = value_cont + trend_cont

# Relative signals: group demeaning
rel_value = value_z.sub(value_z.groupby(L0_MAP, axis=1).transform('mean'))
rel_trend = trend_cont.sub(trend_cont.mean(axis=1), axis=0).clip(-1, 1)

# Combined: all dates × all categories
combined = stage1 + 0.5 * rel_value.clip(-1, 1) + 1.0 * rel_trend + 0.5 * bucket
```

## Layer 2: Stage 3 Loop

```python
weights = {}
for date in rebalance_dates:
    scores = combined.loc[date].to_dict()
    for profile in profiles:
        w = compute_stage3(scores, neutral[profile], mins[profile], maxs[profile])
        weights[(date, profile)] = w
# 40 dates × 5 profiles = 200 calls × 0.1ms = ~20ms
```

## Layer 3: vbt Simulation

```python
for profile in profiles:
    w_df = pd.DataFrame([weights[(d, profile)] for d in rebalance_dates],
                        index=rebalance_dates).reindex(prices.index).ffill()
    strategies[f"TAA_{profile}"] = w_df

pf = run(prices, strategies, rebalancing_freq=list(rebalance_dates), fees=0.001)
```

## Performance Target

| Layer | Current | Target | Speedup |
|-------|---------|--------|---------|
| Signals | ~20s | <1s | 20× |
| Stage 3 | ~3s | ~0.02s | 150× |
| Portfolio sim | ~1s | <1s | same |
| **Total** | **~24s** | **~2s** | **~12×** |

## What Cannot Be Vectorized

Stage 3 normalization only — iterative redistribution, corridor clipping, buffer absorption, floor consolidation. Each step modifies weights in-place based on prior step. Fast (~0.1ms per call) so not a bottleneck.

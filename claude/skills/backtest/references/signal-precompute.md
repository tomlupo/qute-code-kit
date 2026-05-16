# Signal Precomputation Patterns

## Problem

When backtesting signal-driven strategies across multiple profiles, signals (Stage 1 + Stage 2) are identical for all profiles — only Stage 3 (weight normalization with profile-specific corridors) differs. Computing signals 5× per date is wasteful.

## Pattern: Precompute Once, Normalize Per Profile

```python
# SLOW: 5× redundant signal computation
for profile in profiles:
    for date in rebalance_dates:
        signals = compute_signals(data, date)         # same for all profiles!
        weights[profile][date] = normalize(signals, corridors[profile])

# FAST: precompute signals once
signal_cache = {}
for date in rebalance_dates:
    signal_cache[date] = compute_signals(data, date)  # compute once

for profile in profiles:
    for date in rebalance_dates:
        weights[profile][date] = normalize(signal_cache[date], corridors[profile])
```

Speedup: ~5× for 5 profiles (observed: 2+ min → 23 sec).

## Pattern: Vectorized Signals (Target Architecture)

Replace the date loop entirely with vectorized pandas operations:

```python
# All z-scores across all dates in one operation
value_z = (value_series - value_series.rolling(120).mean()) / value_series.rolling(120).std()
trend_z = (trend_raw - trend_raw.rolling(120).mean()) / trend_raw.rolling(120).std()

# Score and combine — DataFrame operations, no loops
combined = (value_z / 1.5).clip(-1, 1) + (trend_z / 1.5).clip(-1, 1) + ...

# Only loop for Stage 3 (path-dependent normalization)
for date in rebalance_dates:
    scores = combined.loc[date].to_dict()
    for profile in profiles:
        weights[(date, profile)] = compute_stage3(scores, corridors[profile])
```

Speedup: ~20× for signal computation (from ~20s to <1s).

## When to Use Each

| Pattern | When | Speed |
|---------|------|-------|
| Single-date (current) | PM scorecard for one eval date | ~0.2s |
| Precompute cache | Backtest with `run_taa()` | ~23s (5 profiles, 120 months) |
| Vectorized | New backtest engine | ~2s target |

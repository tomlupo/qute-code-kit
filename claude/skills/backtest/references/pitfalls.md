# Backtest Pitfalls

## Weight Normalization Flipping Signal Direction

When normalizing to 100%, preserve signal direction:
- Total > 100%: only reduce negative-signal categories
- Total < 100%: only increase positive-signal categories
- Never pro-rata scale all uniformly — can flip bearish tilt to overweight

## Negative Weights

Always `weights.clip(lower=0)`. The engine uses `Direction.LongOnly`.

## Currency Mismatch

All prices must be in the same currency. Convert before backtesting.

## Transaction Cost Drag

For quarterly rebalancing with 5-10% turnover, costs are ~0.1-0.3% annual drag. Always set `fees` — backtests without costs overstate performance.

## Corridor Design for Signal-to-Weight Translation

- Use asymmetric tilt steps: `step_up = (max - neutral) / max_score`, `step_down = (neutral - min) / max_score`
- Calibrate `max_score` to the 99th percentile of actual scores, not the theoretical max
- Score at `max_score` → exactly reaches corridor boundary

## Rebalancing Frequency vs Signal Decay

- Monthly captures more signal value but costs more in turnover
- Quarterly is realistic for advisory — signals must be persistent
- Always compare both to measure signal decay

## Weight Drift Between Rebalances (CRITICAL)

**Never skip weight drift in backtests.** Between rebalance dates, asset returns cause weights to drift from targets.

```python
# WRONG: recompute weights every period, apply immediately
for date in all_dates:
    weights = compute_weights(date)
    port_return = np.dot(weights, returns)  # no drift = overstates signal quality

# RIGHT: use run() which handles drift internally
pf = run(prices, {"Strategy": weights_df}, rebalancing_freq=list(rebalance_dates))
```

Without drift, backtests overstate performance by 20-40% (observed: Sharpe 1.37 without drift vs 0.93 with drift for the same strategy).

## Comparing Strategy Variants

1. **Pre-compute all weight DataFrames** — one per variant, same date index
2. **Pass all to `run()` in a single call** — ensures identical price data, fees, dates
3. **Always include SAA benchmark** — provides the "no TAA" baseline
4. **Test both monthly and quarterly** — quarterly with drift removes timing luck
5. **Never write ad-hoc comparison loops** — they inevitably miss drift, fees, or rebalancing logic

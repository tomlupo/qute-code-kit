# Transaction Cost Models

Realistic cost modeling for backtesting.

## Cost Components

### 1. Explicit Costs
```
explicit_cost = commission + exchange_fees + taxes
```

| Market | Commission | Exchange Fees | Stamp Duty |
|--------|------------|---------------|------------|
| US Equities | 0-1 bps | 0.1 bps | None |
| EU Equities | 1-5 bps | 0.5 bps | Varies (0-50 bps) |
| Crypto (CEX) | 1-10 bps | Included | None |
| Crypto (DEX) | 5-30 bps | Gas | None |
| Futures | $0.5-2/contract | 0.1 bps | None |

### 2. Spread Cost
```
spread_cost = 0.5 * bid_ask_spread
```

Typical spreads by liquidity:
| Liquidity Tier | Typical Spread |
|----------------|----------------|
| Large cap equity | 1-3 bps |
| Mid cap equity | 5-15 bps |
| Small cap equity | 15-50 bps |
| BTC/ETH | 1-5 bps |
| Alt crypto | 10-100 bps |

### 3. Market Impact

#### Square-Root Model (Almgren-Chriss)
```python
impact = sigma * sqrt(participation_rate * daily_volume_fraction)
```

#### Linear Impact (Conservative)
```python
impact_bps = 0.1 * (trade_value / adv_20d) * 10000
```
- ADV = Average Daily Volume (20-day)

## Total Cost Estimation

### Per-Trade Cost
```python
total_cost_bps = commission + 0.5 * spread + market_impact + slippage
```

### Slippage Estimates
| Execution Method | Slippage (bps) |
|------------------|----------------|
| Market order | 5-20 |
| Limit order (aggressive) | 2-10 |
| TWAP | 3-8 |
| VWAP | 2-5 |
| Implementation shortfall | 3-10 |

## Cost Scenarios for Backtesting

### Conservative (Recommended)
```python
cost_model = {
    'commission_bps': 2,
    'spread_bps': 5,
    'impact_coefficient': 0.1,
    'slippage_bps': 5
}
# Total: ~15-25 bps per round trip
```

### Optimistic (Lower Bound)
```python
cost_model = {
    'commission_bps': 0.5,
    'spread_bps': 2,
    'impact_coefficient': 0.05,
    'slippage_bps': 2
}
# Total: ~5-10 bps per round trip
```

### Pessimistic (Stress Test)
```python
cost_model = {
    'commission_bps': 5,
    'spread_bps': 10,
    'impact_coefficient': 0.2,
    'slippage_bps': 10
}
# Total: ~30-50 bps per round trip
```

## Strategy Breakeven Analysis

```python
def breakeven_turnover(gross_sharpe, cost_per_turn_bps, annual_vol_pct):
    """
    Max turnover before costs eliminate alpha
    gross_sharpe: Sharpe before costs
    cost_per_turn_bps: Round-trip cost in bps
    annual_vol_pct: Annual volatility as decimal
    """
    gross_return = gross_sharpe * annual_vol_pct
    max_turnover = gross_return / (cost_per_turn_bps / 10000)
    return max_turnover
```

## Capacity Estimation

```python
def strategy_capacity(avg_daily_volume, participation_limit=0.05):
    """
    Estimate max AUM before impact becomes prohibitive
    """
    daily_tradeable = avg_daily_volume * participation_limit
    # Assume 20% daily turnover
    capacity = daily_tradeable * 5
    return capacity
```

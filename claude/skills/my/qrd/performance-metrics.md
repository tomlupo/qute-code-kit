# Performance Metrics Reference

Standard calculations for quantitative strategy evaluation.

## Return Metrics

### CAGR (Compound Annual Growth Rate)
```python
cagr = (final_value / initial_value) ** (252 / trading_days) - 1
```

### Sharpe Ratio
```python
sharpe = (returns.mean() - rf_rate) / returns.std() * np.sqrt(252)
```
- Use daily returns, annualize at end
- Subtract risk-free rate (typically 3-month T-bill)

### Sortino Ratio
```python
downside_returns = returns[returns < 0]
downside_std = downside_returns.std() * np.sqrt(252)
sortino = (returns.mean() * 252 - rf_annual) / downside_std
```

### Calmar Ratio
```python
calmar = cagr / abs(max_drawdown)
```

## Risk Metrics

### Maximum Drawdown
```python
cumulative = (1 + returns).cumprod()
running_max = cumulative.cummax()
drawdown = (cumulative - running_max) / running_max
max_drawdown = drawdown.min()
```

### Value at Risk (VaR)
```python
# Parametric VaR (95%)
var_95 = returns.mean() - 1.645 * returns.std()

# Historical VaR (95%)
var_95_hist = returns.quantile(0.05)
```

### Conditional VaR (CVaR / Expected Shortfall)
```python
var_threshold = returns.quantile(0.05)
cvar = returns[returns <= var_threshold].mean()
```

### Volatility (Annualized)
```python
annual_vol = returns.std() * np.sqrt(252)
```

## Statistical Significance

### T-Statistic for Sharpe
```python
t_stat = sharpe * np.sqrt(n_years)
# Require t > 2.0 for significance at 95% level
```

### Information Ratio
```python
active_returns = strategy_returns - benchmark_returns
ir = active_returns.mean() / active_returns.std() * np.sqrt(252)
```

## Trading Metrics

### Win Rate
```python
win_rate = (returns > 0).sum() / len(returns)
```

### Profit Factor
```python
gross_profit = returns[returns > 0].sum()
gross_loss = abs(returns[returns < 0].sum())
profit_factor = gross_profit / gross_loss
```

### Turnover
```python
# Daily turnover as sum of absolute position changes
turnover = abs(weights.diff()).sum(axis=1).mean() * 252
```

## Minimum Thresholds by Strategy Type

| Strategy Type | Min Sharpe | Max DD | Min T-Stat |
|---------------|------------|--------|------------|
| Market Neutral L/S | 1.5 | 15% | 2.5 |
| Long-Only Factor | 0.5 | 25% | 2.0 |
| Momentum/Trend | 0.8 | 20% | 2.0 |
| Mean Reversion | 1.0 | 15% | 2.5 |
| HFT/Market Making | 3.0+ | 5% | 3.0 |
| Crypto Systematic | 1.0 | 30% | 2.0 |

# Backtesting Bias Checklist

Mandatory verification before accepting any backtest results.

## Data Biases

### Look-Ahead Bias
**Definition**: Using information not available at decision time

**Prevention**:
- [ ] All data indexed by "as-of" date, not reporting date
- [ ] Fundamental data lagged by publication delay (e.g., earnings +1 day)
- [ ] Price data uses prior close for signals, not current close
- [ ] Corporate actions applied retrospectively only
- [ ] Alternative data accounts for collection/processing lag

**Test**: Compare signal values at t with data available at t-1 only

### Survivorship Bias
**Definition**: Excluding delisted/failed securities

**Prevention**:
- [ ] Universe constructed point-in-time
- [ ] Delisted securities included until delist date
- [ ] Delist returns properly handled (often negative)
- [ ] Mergers/acquisitions tracked with correct final prices
- [ ] Index membership changes respected

**Test**: Compare constituents at historical dates vs current view

### Selection Bias
**Definition**: Cherry-picking assets that performed well

**Prevention**:
- [ ] Universe defined a priori, not post-hoc
- [ ] Same universe rules applied consistently
- [ ] No manual additions/exclusions based on hindsight

## Strategy Biases

### Data Mining Bias
**Definition**: Finding patterns by testing many hypotheses

**Prevention**:
- [ ] Economic rationale stated BEFORE testing
- [ ] Limited parameter combinations tested
- [ ] Bonferroni/FDR correction for multiple comparisons
- [ ] Out-of-sample testing reserved (never peeked)

**Adjustment**:
```python
# Haircut for data mining
adjusted_tstat = tstat - 0.5 * log(num_tests)
# Or use Bonferroni
significance_level = 0.05 / num_tests
```

### Overfitting Bias
**Definition**: Model fits noise, not signal

**Prevention**:
- [ ] Simple models preferred (fewer parameters)
- [ ] Walk-forward validation used
- [ ] Training/test split maintained
- [ ] Parameter stability across windows checked
- [ ] Sharpe decay from IS to OOS < 50%

**Warning Signs**:
- In-sample Sharpe >> Out-of-sample Sharpe
- Many parameters relative to data points
- Specific date/event dependencies

### Optimization Bias
**Definition**: Optimal parameters unlikely to persist

**Prevention**:
- [ ] Parameter robustness tested (plateau, not spike)
- [ ] Neighboring parameters yield similar results
- [ ] Parameters have economic interpretation
- [ ] Walk-forward shows parameter stability

## Execution Biases

### Transaction Cost Underestimation
**Prevention**:
- [ ] Realistic spread assumptions (not mid-price)
- [ ] Market impact modeled
- [ ] Slippage buffer included
- [ ] Cost scenarios tested (base, pessimistic)

### Liquidity Illusion
**Prevention**:
- [ ] Position sizes respect ADV limits (< 5%)
- [ ] Small cap positions scaled down
- [ ] Execution time constraints modeled
- [ ] Market impact increases with size

### Timing Assumption Errors
**Prevention**:
- [ ] Signal and execution timing documented
- [ ] No same-bar entry/exit
- [ ] Realistic order fill assumptions
- [ ] After-hours/pre-market handling specified

## Statistical Red Flags

| Warning Sign | Threshold | Investigation |
|--------------|-----------|---------------|
| Sharpe > 3.0 | Almost always | Check for bugs, look-ahead |
| Zero losing months | Impossible | Data/code error |
| Perfect correlation with benchmark | Suspicious | May be indexing |
| Sharpe IS/OOS ratio > 2x | Common | Overfitting likely |
| T-stat < 2.0 | Not significant | Likely noise |
| Win rate > 70% (except HFT) | Unusual | Verify position sizing |

## Validation Checklist

Before accepting results:
- [ ] All bias checks above passed
- [ ] Results replicated by second person/code
- [ ] Edge cases tested (market crashes, low liquidity periods)
- [ ] Strategy behavior makes economic sense
- [ ] No "too good to be true" metrics
- [ ] Parameter sensitivity reasonable
- [ ] Capacity realistic for intended AUM

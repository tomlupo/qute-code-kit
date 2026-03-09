# QRD: Cross-Sectional Crypto Momentum

**Version:** 1.0
**Author:** Research Team
**Date:** 2026-01-23
**Status:** In Progress

## Executive Summary

Develop a cross-sectional momentum strategy for top cryptocurrencies, exploiting continuation of relative strength/weakness. Target Sharpe > 1.0 with systematic rebalancing and robust risk management.

---

## 1. Research Hypothesis

### 1.1 Core Hypothesis
Cryptocurrencies exhibiting strong recent relative performance will continue to outperform in the near term due to attention and trend-following flows.

### 1.2 Economic Rationale
- **Attention Effect**: Retail-dominated market with strong herding behavior
- **Structural Flows**: Index inclusion, ETF rebalancing create momentum
- **Information Diffusion**: Slower price discovery in fragmented market
- **Winner Effect**: Strong performers attract more capital inflows

### 1.3 Null Hypothesis
7-day relative returns have no predictive power for subsequent 7-day returns. Reject if IC < 0.03 consistently or Sharpe < 0.5 after costs.

### 1.4 Prior Research
- Jegadeesh & Titman momentum extends to crypto (Liu & Tsyvinski, 2021)
- Shorter lookbacks work better in crypto (faster mean-reversion)
- Momentum crashes occur but are recoverable

---

## 2. Universe & Scope

### 2.1 Asset Universe
- **Instruments:** Top 50 cryptocurrencies by market cap (excluding stablecoins)
- **Filters:** Min $10M daily volume, min $100M market cap, available on 2+ major exchanges
- **Universe Size:** ~30-40 after filtering

### 2.2 Time Scope
- **Backtest Period:** 2020-01-01 to 2025-12-31
- **In-Sample:** 2020-01-01 to 2023-12-31
- **Out-of-Sample:** 2024-01-01 to 2025-12-31
- **Walk-Forward:** 6-month windows, 1-month step

### 2.3 Frequency
- **Signal Generation:** Daily (UTC 00:00)
- **Rebalancing:** Weekly (Sunday 00:00 UTC)
- **Holding Period:** 7 days average

---

## 3. Data Requirements

### 3.1 Primary Data Sources
| Data Type | Source | Frequency | History Required | Format |
|-----------|--------|-----------|------------------|--------|
| OHLCV | CoinGecko/Binance | Daily | 6 years | CSV |
| Market Cap | CoinGecko | Daily | 6 years | CSV |
| Volume | Aggregated exchanges | Daily | 6 years | CSV |

### 3.2 Data Quality Requirements
- **Missing Data Handling:** Forward fill up to 3 days, then exclude
- **Corporate Actions:** Handle forks, airdrops as separate assets
- **Survivorship Bias:** Include delisted coins until delist date
- **Look-Ahead Bias Prevention:** Use previous day's data for signals

### 3.3 Benchmark Data
- **Primary Benchmark:** Equal-weight top 20 crypto index
- **Risk-Free Rate:** 0% (crypto native, or use USDC lending rate)

---

## 4. Signal/Factor Specification

### 4.1 Signal Definition
```
Momentum_t = (Price_t / Price_{t-7}) - 1
Signal_t = CrossSectionalRank(Momentum_t)
```

### 4.2 Signal Components
| Component | Formula | Intuition |
|-----------|---------|-----------|
| Raw Return | P_t / P_{t-7} - 1 | 7-day momentum |
| CS Rank | rank(return) / N | Normalize across universe |

### 4.3 Parameters
| Parameter | Default | Range | Optimization Method |
|-----------|---------|-------|---------------------|
| Lookback | 7 days | 3-21 | Grid search (IS) |
| Hold Period | 7 days | 3-14 | Grid search (IS) |
| Long Percentile | Top 20% | 10-30% | Sensitivity analysis |
| Short Percentile | Bottom 20% | 10-30% | Sensitivity analysis |

### 4.4 Signal Processing
- **Winsorization:** Cap returns at ±50% to reduce outlier impact
- **Smoothing:** None (use raw signal)
- **Combination Method:** N/A (single factor)

---

## 5. Portfolio Construction

### 5.1 Position Sizing
- **Method:** Equal weight within long/short buckets
- **Gross Exposure:** 100% (50% long, 50% short)
- **Net Exposure:** 0% (dollar neutral)

### 5.2 Constraints
| Constraint | Value | Hard/Soft |
|------------|-------|-----------|
| Max Position Size | 15% | Hard |
| Min Position Size | 2% | Soft |
| Max BTC/ETH Weight | 20% each | Hard |
| Max Turnover | 200% weekly | Soft |

### 5.3 Rebalancing Logic
- **Trigger:** Weekly calendar (Sunday UTC)
- **Execution:** Use closing prices + 5 bps buffer
- **Buffer Rule:** No rebalance if position change < 2%

---

## 6. Risk Management

### 6.1 Risk Metrics to Monitor
| Metric | Threshold | Action if Breached |
|--------|-----------|-------------------|
| Weekly Drawdown | 10% | Reduce to 50% exposure |
| Monthly Drawdown | 20% | Pause, review |
| Daily VaR (95%) | 5% | Monitor closely |
| Correlation to BTC | > 0.6 | Review hedging |

### 6.2 Factor Exposures
- Market beta: Target 0 (neutral)
- Size exposure: Slight large-cap tilt acceptable
- Sector exposure: Monitor DeFi/L1/Meme concentrations

### 6.3 Stress Testing Scenarios
| Scenario | Description | Expected Impact |
|----------|-------------|-----------------|
| May 2021 Crash | -50% BTC drawdown | Est. -15% (momentum reversal) |
| FTX Collapse | Nov 2022 | Est. -10% (correlation spike) |
| 2024 ETF Approval | Volatility spike | Est. ±5% |

---

## 7. Transaction Costs

### 7.1 Cost Model
| Cost Component | Estimate | Source/Methodology |
|----------------|----------|-------------------|
| Commission | 5 bps | Binance VIP rates |
| Spread | 5 bps | Historical bid-ask (top 50) |
| Market Impact | 2 bps | Small position sizes |
| Slippage | 3 bps | Conservative buffer |
| **Total Round Trip** | **30 bps** | |

### 7.2 Cost Sensitivity Analysis
- Optimistic: 15 bps RT
- Base: 30 bps RT
- Pessimistic: 50 bps RT

---

## 8. Performance Metrics

### 8.1 Primary Metrics
| Metric | Target | Minimum Acceptable |
|--------|--------|-------------------|
| Sharpe Ratio | 1.5 | 1.0 |
| Sortino Ratio | 2.0 | 1.3 |
| Max Drawdown | 20% | 30% |
| CAGR | 30% | 15% |

### 8.2 Secondary Metrics
- Calmar Ratio: > 1.0
- Win Rate: > 50%
- Profit Factor: > 1.5
- Avg Win / Avg Loss: > 1.0

### 8.3 Statistical Significance
- **T-statistic Threshold:** > 2.0
- **Bootstrap CI:** 95% CI on Sharpe must exclude 0
- **Multiple Testing:** Bonferroni for lookback/hold parameter grid

---

## 9. Implementation Specification

### 9.1 Technology Stack
- **Language:** Python 3.11
- **Backtesting:** Custom vectorized engine
- **Data Storage:** Parquet files
- **Orchestration:** Cron (daily)

### 9.2 Code Structure
```
crypto-momentum/
├── data/
│   ├── raw/
│   └── processed/
├── src/
│   ├── data/
│   ├── signals/
│   ├── portfolio/
│   ├── backtest/
│   └── risk/
├── notebooks/
├── tests/
└── configs/
```

### 9.3 Testing Requirements
- Unit tests for signal calculation
- Integration test for full backtest pipeline
- Reconciliation vs manual spot checks

---

## 10. Acceptance Criteria

### 10.1 Research Phase Complete When:
- [ ] Sharpe > 1.0 in-sample
- [ ] Sharpe > 0.7 out-of-sample
- [ ] Sharpe > 0.5 after pessimistic costs
- [ ] Max DD < 30%
- [ ] T-stat > 2.0
- [ ] No look-ahead or survivorship bias
- [ ] Code tested and documented

### 10.2 Go/No-Go Decision Framework
| Outcome | Criteria | Next Action |
|---------|----------|-------------|
| Proceed | OOS Sharpe > 0.8, all bias checks pass | Paper trading |
| Iterate | OOS Sharpe 0.5-0.8 | Test parameter variants |
| Reject | OOS Sharpe < 0.5 or bias detected | Archive, document learnings |

---

## 11. Out of Scope

- Intraday trading
- Derivatives (perps, options)
- On-chain data signals
- Sentiment/social media signals
- Multi-strategy combination

---

## 12. References

- Liu, Y., & Tsyvinski, A. (2021). Risks and Returns of Cryptocurrency. Review of Financial Studies.
- Jegadeesh, N., & Titman, S. (1993). Returns to Buying Winners. Journal of Finance.

---

## User Stories

### [ ] US-001: Data Pipeline Setup
**As a** quant researcher
**I want** clean crypto OHLCV data with proper point-in-time universe
**So that** I can begin signal development without data quality issues

#### Acceptance Criteria
- [ ] OHLCV data ingested for 2020-2025
- [ ] Market cap data for universe filtering
- [ ] Delisted coins included until delist date
- [ ] Data validation tests pass (no gaps > 3 days)
- [ ] Point-in-time universe reconstruction working

#### Technical Notes
Use CoinGecko API with rate limiting. Store as Parquet partitioned by date.

---

### [ ] US-002: Momentum Signal Implementation
**As a** quant researcher
**I want** the 7-day momentum signal calculated and ranked cross-sectionally
**So that** I can evaluate its predictive power

#### Acceptance Criteria
- [ ] 7-day return calculated correctly
- [ ] Cross-sectional rank computed
- [ ] Returns winsorized at ±50%
- [ ] Unit tests verify against manual calculations
- [ ] Signal stored with date index

#### Technical Notes
```python
signal = prices.pct_change(7).rank(axis=1, pct=True)
```

---

### [ ] US-003: Backtest Engine
**As a** quant researcher
**I want** a vectorized backtest with transaction costs
**So that** I can evaluate strategy performance realistically

#### Acceptance Criteria
- [ ] Long/short portfolios constructed from signal
- [ ] Weekly rebalancing implemented
- [ ] Transaction costs applied (30 bps RT)
- [ ] Position constraints enforced
- [ ] Performance metrics calculated

#### Technical Notes
Vectorized implementation using numpy/pandas. No event-driven complexity needed for daily data.

---

### [ ] US-004: Risk Analysis
**As a** quant researcher
**I want** comprehensive risk metrics and stress test results
**So that** I can understand strategy vulnerabilities

#### Acceptance Criteria
- [ ] Drawdown series calculated
- [ ] VaR/CVaR computed
- [ ] Factor exposures (beta to BTC) measured
- [ ] Stress test scenarios simulated
- [ ] Risk dashboard generated

#### Technical Notes
Include May 2021, Nov 2022 crisis periods explicitly.

---

### [ ] US-005: Statistical Validation
**As a** quant researcher
**I want** t-statistics, bootstrap CIs, and IS/OOS comparison
**So that** I can be confident results aren't due to chance

#### Acceptance Criteria
- [ ] T-stat > 2.0 on Sharpe
- [ ] Bootstrap 95% CI excludes zero
- [ ] IS vs OOS Sharpe ratio < 2x
- [ ] Parameter sensitivity plot generated
- [ ] Overfitting diagnostic documented

#### Technical Notes
1000 bootstrap iterations. Bonferroni correction for parameter grid.

---

### [ ] US-006: Documentation & Tearsheet
**As a** quant researcher
**I want** a research report and performance tearsheet
**So that** findings can be reviewed and presented

#### Acceptance Criteria
- [ ] Performance tearsheet (equity curve, drawdown, monthly returns)
- [ ] Research notebook with methodology
- [ ] Go/No-Go recommendation documented
- [ ] Code README complete

#### Technical Notes
Use quantstats or pyfolio for tearsheet generation.

---
name: qrd
description: Quantitative Research & Development specification document creation for systematic trading strategies, alpha signals, risk models, and portfolio construction. Use when creating research specifications for: (1) Alpha signal/factor development, (2) Backtesting frameworks and requirements, (3) Portfolio optimization strategies, (4) Risk model specifications, (5) Performance attribution systems, (6) Systematic trading rule documentation. Generates structured QRD documents with hypotheses, data requirements, methodology, acceptance criteria, and implementation tasks suitable for autonomous agent execution.
---

# Quantitative Research & Development (QRD) Skill

Create structured research specification documents for quantitative finance projects. Output enables autonomous implementation by breaking complex research into atomic, testable tasks.

## Workflow

### Phase 1: Discovery (Interactive)

Ask clarifying questions to understand the research scope. Do not proceed until answers are clear.

**Required Information:**

1. **Research Objective**: What hypothesis or edge are we testing?
2. **Asset Universe**: Which instruments/markets? (equities, crypto, FX, futures, multi-asset)
3. **Strategy Type**: Alpha generation, risk management, execution, portfolio construction?
4. **Time Horizon**: Holding period and rebalancing frequency?
5. **Data Availability**: What data sources exist? What needs acquisition?
6. **Constraints**: Regulatory, capital, liquidity, technology limitations?
7. **Success Criteria**: What metrics define success? Sharpe, drawdown, turnover bounds?
8. **Existing Infrastructure**: Current tech stack, backtesting frameworks, production systems?

**Optional Clarifications** (ask if ambiguous):
- Benchmark comparisons required?
- Transaction cost assumptions?
- Risk budget or factor exposure limits?
- Live trading considerations?

### Phase 2: Document Generation

Generate `tasks/qrd-[research-name].md` following the template structure below.

## Document Template

```markdown
# QRD: [Research Name]

**Version:** 1.0
**Author:** [Author]
**Date:** [Date]
**Status:** Draft | In Review | Approved | In Progress | Complete

## Executive Summary

[2-3 sentences: What we're building, why it matters, expected outcome]

---

## 1. Research Hypothesis

### 1.1 Core Hypothesis
[Clear, falsifiable statement of the alpha source or research question]

### 1.2 Economic Rationale
[Why should this work? Behavioral, structural, or informational edge?]

### 1.3 Null Hypothesis
[What would disprove this? Specific conditions for rejection]

### 1.4 Prior Research
[Relevant academic papers, internal research, or market observations]

---

## 2. Universe & Scope

### 2.1 Asset Universe
- **Instruments:** [e.g., S&P 500 constituents, top 100 crypto by market cap]
- **Filters:** [Liquidity minimums, market cap thresholds, sector exclusions]
- **Universe Size:** [Expected N instruments after filtering]

### 2.2 Time Scope
- **Backtest Period:** [Start date] to [End date]
- **In-Sample:** [Date range for model development]
- **Out-of-Sample:** [Date range for validation]
- **Walk-Forward:** [If applicable, specify window parameters]

### 2.3 Frequency
- **Signal Generation:** [Daily, hourly, tick-level]
- **Rebalancing:** [Frequency and timing, e.g., daily close, weekly Monday open]
- **Holding Period:** [Expected average holding period]

---

## 3. Data Requirements

### 3.1 Primary Data Sources
| Data Type | Source | Frequency | History Required | Format |
|-----------|--------|-----------|------------------|--------|
| [Price]   | [Source] | [Freq]  | [Years]          | [CSV/API/DB] |
| [Volume]  | [Source] | [Freq]  | [Years]          | [CSV/API/DB] |

### 3.2 Alternative Data (if applicable)
| Data Type | Source | Frequency | History Required | Format |
|-----------|--------|-----------|------------------|--------|
| [Sentiment] | [Source] | [Freq] | [Years]        | [Format] |

### 3.3 Data Quality Requirements
- **Missing Data Handling:** [Forward fill, interpolation, exclusion rules]
- **Corporate Actions:** [Adjustment methodology for splits, dividends]
- **Survivorship Bias:** [Point-in-time universe construction approach]
- **Look-Ahead Bias Prevention:** [Data availability timestamps, publication lags]

### 3.4 Benchmark Data
- **Primary Benchmark:** [e.g., SPY, BTC, custom equal-weight]
- **Risk-Free Rate:** [Source and instrument]

---

## 4. Signal/Factor Specification

### 4.1 Signal Definition
```
Signal_t = f(Data_{t-1}, Parameters)
```
[Mathematical formulation of the signal]

### 4.2 Signal Components
| Component | Formula | Intuition |
|-----------|---------|-----------|
| [Raw Signal] | [Formula] | [Why this captures alpha] |
| [Normalization] | [Z-score, rank, etc.] | [Purpose of transformation] |

### 4.3 Parameters
| Parameter | Default | Range | Optimization Method |
|-----------|---------|-------|---------------------|
| [Lookback] | [N days] | [Min-Max] | [Grid search, Bayesian] |

### 4.4 Signal Processing
- **Winsorization:** [Percentile bounds if applicable]
- **Smoothing:** [EMA, SMA parameters if applicable]
- **Combination Method:** [If multi-factor: equal weight, IC-weighted, ML]

---

## 5. Portfolio Construction

### 5.1 Position Sizing
- **Method:** [Equal weight, volatility parity, signal-proportional, optimization]
- **Gross Exposure:** [Target gross exposure as % of capital]
- **Net Exposure:** [Long/short bias constraints]

### 5.2 Constraints
| Constraint | Value | Hard/Soft |
|------------|-------|-----------|
| Max Position Size | [%] | [Hard/Soft] |
| Sector Exposure | [%] | [Hard/Soft] |
| Turnover Limit | [% per period] | [Hard/Soft] |
| Min Holding Period | [Days] | [Hard/Soft] |

### 5.3 Rebalancing Logic
- **Trigger:** [Calendar-based, threshold-based, or hybrid]
- **Execution:** [Close prices, TWAP, VWAP assumptions]

---

## 6. Risk Management

### 6.1 Risk Metrics to Monitor
| Metric | Threshold | Action if Breached |
|--------|-----------|-------------------|
| Drawdown | [%] | [Reduce exposure, halt trading] |
| VaR (95%) | [$/%] | [Action] |
| Volatility | [Ann. %] | [Vol targeting adjustment] |

### 6.2 Factor Exposures
[List factor exposures to monitor: market beta, size, value, momentum, etc.]

### 6.3 Stress Testing Scenarios
| Scenario | Description | Expected Impact |
|----------|-------------|-----------------|
| [2008 Crisis] | [Conditions] | [Estimated loss] |
| [COVID Crash] | [Conditions] | [Estimated loss] |

---

## 7. Transaction Costs

### 7.1 Cost Model
| Cost Component | Estimate | Source/Methodology |
|----------------|----------|-------------------|
| Commission | [bps] | [Broker quotes, historical] |
| Spread | [bps] | [Historical bid-ask data] |
| Market Impact | [Formula] | [Square-root model, etc.] |
| Slippage | [bps] | [Historical execution data] |

### 7.2 Cost Sensitivity Analysis
[Define scenarios: optimistic, base case, pessimistic cost assumptions]

---

## 8. Performance Metrics

### 8.1 Primary Metrics
| Metric | Target | Minimum Acceptable |
|--------|--------|-------------------|
| Sharpe Ratio | [X] | [Y] |
| Sortino Ratio | [X] | [Y] |
| Max Drawdown | [%] | [%] |
| CAGR | [%] | [%] |

### 8.2 Secondary Metrics
- Calmar Ratio
- Win Rate
- Profit Factor
- Average Win / Average Loss
- Time in Drawdown

### 8.3 Statistical Significance
- **T-statistic Threshold:** [Minimum t-stat for significance]
- **Bootstrap Confidence Intervals:** [Methodology]
- **Multiple Testing Adjustment:** [Bonferroni, FDR if testing multiple signals]

---

## 9. Implementation Specification

### 9.1 Technology Stack
- **Language:** [Python, R, etc.]
- **Backtesting Framework:** [Custom, Zipline, Backtrader, vectorbt]
- **Data Storage:** [PostgreSQL, Parquet, HDF5]
- **Orchestration:** [Airflow, Prefect, cron]

### 9.2 Code Structure
```
project/
├── data/
│   ├── raw/           # Unprocessed data
│   └── processed/     # Clean, analysis-ready data
├── src/
│   ├── data/          # Data loaders and cleaners
│   ├── signals/       # Signal generation
│   ├── portfolio/     # Position sizing and optimization
│   ├── backtest/      # Backtesting engine
│   ├── risk/          # Risk calculations
│   └── utils/         # Common utilities
├── notebooks/         # Research notebooks
├── tests/             # Unit and integration tests
└── configs/           # Parameter configurations
```

### 9.3 Testing Requirements
- Unit tests for all signal calculations
- Integration tests for backtest pipeline
- Reconciliation tests against known benchmarks

---

## 10. Acceptance Criteria

### 10.1 Research Phase Complete When:
- [ ] Signal generates statistically significant returns in-sample
- [ ] Signal remains significant out-of-sample
- [ ] Performance survives realistic transaction costs
- [ ] Risk metrics within defined bounds
- [ ] No evidence of look-ahead or survivorship bias
- [ ] Code reviewed and tested
- [ ] Documentation complete

### 10.2 Go/No-Go Decision Framework
| Outcome | Criteria | Next Action |
|---------|----------|-------------|
| Proceed to Production | [All primary metrics met] | [Production deployment plan] |
| Iterate | [Partial success] | [Specific improvements to test] |
| Reject | [Hypothesis falsified] | [Document learnings, archive] |

---

## 11. Out of Scope

[Explicitly list what is NOT included to prevent scope creep]
- [Item 1]
- [Item 2]

---

## 12. References

- [Paper 1: Title, Authors, Link]
- [Paper 2: Title, Authors, Link]
- [Internal Document: Title, Location]

---

## User Stories

### [ ] US-001: Data Pipeline Setup
**As a** quant researcher
**I want** clean, point-in-time data loaded and validated
**So that** I can begin signal development without data quality issues

#### Acceptance Criteria
- [ ] Raw data ingested from specified sources
- [ ] Corporate actions properly adjusted
- [ ] Missing data handled per specification
- [ ] Universe filtered per criteria
- [ ] Data validation tests pass
- [ ] No look-ahead bias in data alignment

#### Technical Notes
[Specific implementation guidance]

---

### [ ] US-002: Signal Implementation
**As a** quant researcher
**I want** the signal calculated per specification
**So that** I can evaluate its predictive power

#### Acceptance Criteria
- [ ] Signal formula implemented correctly
- [ ] Parameters configurable
- [ ] Unit tests verify calculation accuracy
- [ ] Signal stored with proper timestamps
- [ ] Visualization of signal distribution available

#### Technical Notes
[Specific implementation guidance]

---

### [ ] US-003: Backtest Engine
**As a** quant researcher
**I want** a backtest simulating realistic trading
**So that** I can evaluate strategy performance

#### Acceptance Criteria
- [ ] Portfolio construction per specification
- [ ] Transaction costs applied correctly
- [ ] Rebalancing logic implemented
- [ ] Performance metrics calculated
- [ ] Results reproducible with same seed

#### Technical Notes
[Specific implementation guidance]

---

### [ ] US-004: Risk Analysis
**As a** quant researcher
**I want** comprehensive risk metrics and stress tests
**So that** I can understand strategy vulnerabilities

#### Acceptance Criteria
- [ ] All risk metrics from Section 6 calculated
- [ ] Stress test scenarios simulated
- [ ] Factor exposure analysis complete
- [ ] Risk dashboard/report generated

#### Technical Notes
[Specific implementation guidance]

---

### [ ] US-005: Performance Attribution
**As a** quant researcher
**I want** returns decomposed by source
**So that** I understand what drives performance

#### Acceptance Criteria
- [ ] Brinson attribution (if applicable)
- [ ] Factor attribution
- [ ] Sector/region attribution (if applicable)
- [ ] Attribution report generated

#### Technical Notes
[Specific implementation guidance]

---

### [ ] US-006: Statistical Validation
**As a** quant researcher
**I want** statistical tests of strategy robustness
**So that** I can be confident results aren't due to chance

#### Acceptance Criteria
- [ ] In-sample vs out-of-sample comparison
- [ ] T-statistics and p-values calculated
- [ ] Bootstrap confidence intervals generated
- [ ] Overfitting diagnostics (if applicable)
- [ ] Sensitivity to parameters documented

#### Technical Notes
[Specific implementation guidance]

---

### [ ] US-007: Documentation & Reporting
**As a** quant researcher
**I want** comprehensive research documentation
**So that** findings can be reviewed and replicated

#### Acceptance Criteria
- [ ] Research notebook with methodology
- [ ] Performance tearsheet generated
- [ ] Risk report complete
- [ ] Code documentation complete
- [ ] Go/No-Go recommendation documented

#### Technical Notes
[Specific implementation guidance]
```

## JSON Conversion for Autonomous Execution

After QRD approval, convert to `qrd.json` for Ralph/autonomous loops:

```json
{
  "projectName": "[Research Name]",
  "version": "1.0",
  "hypothesis": "[Core hypothesis statement]",
  "userStories": [
    {
      "id": "US-001",
      "title": "Data Pipeline Setup",
      "description": "Clean, point-in-time data loaded and validated",
      "acceptanceCriteria": [
        "Raw data ingested from specified sources",
        "Corporate actions properly adjusted",
        "Missing data handled per specification"
      ],
      "status": "pending",
      "passes": false
    }
  ],
  "metrics": {
    "targetSharpe": 1.5,
    "maxDrawdown": 0.15,
    "minTStat": 2.0
  }
}
```

## Output Location

Save documents to: `tasks/qrd-[research-name].md`

## Tips for Effective QRDs

1. **Atomic Stories**: Each user story should be completable in one agent context window
2. **Testable Criteria**: Every acceptance criterion must be verifiable programmatically
3. **No Ambiguity**: Parameters, thresholds, and formulas must be explicit
4. **Bias Prevention**: Explicitly address look-ahead, survivorship, and overfitting
5. **Realistic Costs**: Conservative transaction cost assumptions
6. **Statistical Rigor**: Multiple testing adjustment if scanning many signals

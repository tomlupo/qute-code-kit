# Research to Production

> Full quantitative research pipeline from literature review to production model.

## Components

| Component | Source | Purpose |
|-----------|--------|---------|
| paper-reading | `paper-reading` skill | Three-pass academic paper analysis |
| qrd | `qrd` skill | Quant R&D specification documents |
| market-datasets | `market-datasets` skill | Multi-source market data |

## The Pipeline

```
Read → Specify → Fetch → Explore → Model → Explain → Track → Visualize → Document
```

### 1. Literature review

```
/paper-reading path/to/paper.pdf
```

Three-pass reading via Explore subagent (protects main context):
- **Pass 1**: Survey — title, abstract, section headers, conclusions
- **Pass 2**: Comprehend — key arguments, methodology, results
- **Pass 3**: Critique — assumptions, limitations, relation to your work

**Creative uses:**
- Stack multiple papers: read 3-5 papers, then ask for a synthesis
- Feed paper findings into your QRD spec as "prior art"
- Use with `/handoff` to carry literature insights across sessions

### 2. Define the research spec

```
/qrd
```

Interactive questionnaire → structured document covering:
- Hypothesis (falsifiable statement)
- Data requirements and sources
- Methodology and baselines
- Success criteria (quantitative)
- Risks and mitigation

**Why this matters:** Forces you to articulate what you're testing before writing code. The QRD becomes your contract with yourself.

### 3. Fetch data

Two main usage patterns:

#### Recent market data (prices, fundamentals, indicators)

```
/market-datasets SPY 2024-01-01 2024-12-31
/market-datasets PKOBP.PL 2024-01-01
/market-datasets BTC/USDT 2024-01-01
```

Auto-routes to the right source:
| Pattern | Source | Coverage |
|---------|--------|----------|
| US tickers | Yahoo Finance | Stocks, ETFs, indices |
| `.PL` suffix | Stooq | Warsaw Stock Exchange |
| Macro series | FRED | GDP, CPI, rates, employment |
| Crypto pairs | Binance | Spot and futures |
| Fundamentals | FinancialData.Net | Financials, ratios, options, insider |

Typical flow: fetch prices → validate with `not df.empty` → save to `data/raw/` → EDA.

#### Long-history construction (backtesting, risk calibration)

For multi-decade return series, use the **ETF-primary, academic-backfill** pattern:

```python
# 1. Primary: real fund data (highest quality, limited history)
vfinx = fetch_market_data('VFINX', start_date='1976-01-01')  # S&P 500 fund

# 2. Backfill: academic data (extends to 1928+)
# Shiller for monthly S&P + 10Y yield, Damodaran for annual series

# 3. Splice at fund inception — no blending
splice_date = vfinx.index.min()
backfill_part = shiller[shiller.index < splice_date]
equity = pd.concat([backfill_part, vfinx]).sort_index()
```

Standard proxies: VFINX (equity), VBMFX (bonds), Stooq XAUUSD (gold). See `references/long_history_construction.md` in the skill for splice methodology and validation.

### 4. Explore

The `exploratory-data-analysis` skill auto-detects 200+ formats and generates:
- Distribution profiles
- Missing data analysis
- Correlation matrices
- Outlier detection
- Feature type inference

**Tip:** Run EDA before modeling to catch data quality issues early. A 2-minute EDA prevents 2-hour debugging.

### 5. Model

| Task | Skill | When to use |
|------|-------|------------|
| Classification, regression, clustering | `scikit-learn` | Tabular data, quick iteration |
| Time series classification/forecasting | `aeon` | Temporal patterns, anomaly detection |
| Econometrics (OLS, ARIMA, GLM) | `statsmodels` | When you need p-values and diagnostics |
| Bayesian inference | `pymc` | Uncertainty quantification, priors matter |
| Deep learning | `pytorch-lightning` | Multi-GPU, complex architectures |

**Tip:** Start with scikit-learn even if you plan to use deep learning. A simple baseline you understand beats a complex model you don't.

### 6. Explain

```
Use shap to explain the model's predictions on the test set.
Show feature importance, dependence plots, and force plots for outlier predictions.
```

SHAP works with any model type. Use it to:
- Validate the model learned sensible relationships
- Identify features driving specific predictions
- Catch data leakage (suspiciously important features)

### 7. Track experiments

Use MLflow directly for experiment tracking and comparison:

```
Compare the last 5 MLflow experiments and identify which
hyperparameters most affect performance.
```

### 8. Document

```
/readme
```

Generates a project README in forked context (doesn't pollute your main session).

## Example: Momentum Factor Decay Study

```
1. /paper-reading papers/jegadeesh-titman-1993.pdf
2. /qrd → "Does cross-sectional momentum alpha decay >50% in 5 years?"
3. /market-datasets SPY → fetch S&P 500 constituents
4. Run EDA on returns data
5. scikit-learn: rolling portfolio construction + out-of-sample test
6. shap: what drives alpha decay?
7. /readme → project documentation
```

## Tips

- Start with `/qrd` even for exploratory work — it costs 5 minutes and saves hours
- Use `polars` over pandas for datasets >1GB (lazy evaluation, 10-100x faster)
- Keep `TASKS.md` updated at each pipeline stage
- Use `/handoff` between sessions to preserve research context

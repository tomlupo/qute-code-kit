---
name: mlflow
description: Analyze MLflow experiment data and model interpretability. Use when user asks to compare experiments, find best runs, analyze hyperparameter effects, understand SHAP values, interpret feature importance, or export experiment data. Triggers on MLflow, experiment comparison, SHAP, feature importance, or model interpretability.
---

# MLflow Analysis

## Quick Data Access

```python
import mlflow
import pandas as pd

mlflow.set_tracking_uri("mlruns")
df = mlflow.search_runs(experiment_names=["experiment_name"])
# Columns: run_id, params.*, metrics.*, tags.*, start_time, status, artifact_uri
```

## Directory Structure

When API unavailable, read filesystem directly:

```
mlruns/
├── {experiment_id}/
│   ├── meta.yaml              # experiment name, artifact_location
│   └── {run_id}/
│       ├── meta.yaml          # run metadata, status, timestamps
│       ├── params/            # one file per param (content = value)
│       ├── metrics/           # one file per metric (lines: timestamp step value)
│       ├── tags/              # one file per tag
│       └── artifacts/         # saved files (models, plots, etc.)
```

## Common Operations

| Task | Quick Pattern |
|------|---------------|
| Load runs | `mlflow.search_runs(experiment_names=["name"])` |
| Best by metric | `df.nlargest(5, "metrics.auc")` |
| Group by param | `df.groupby("params.window")["metrics.f1"].mean()` |
| Weighted metric | `np.average(df['auc'], weights=df['n_test'])` |

## ML Fundamentals Reference

### Walk-Forward Validation

Time-series cross-validation that respects temporal ordering:

```
Window 1: [Train: 2014-2017] [Embargo] [Test: Q1 2018]
Window 2: [Train: 2014-2017] [Embargo] [Test: Q2 2018]
...
Window N: [Train: 2019-2022] [Embargo] [Test: Q4 2024]
```

**Key parameters:**
- `train_window_years`: Training period length (3-7 years typical)
- `embargo_months`: Gap between train end and test start (prevents label leakage)
- `frequency`: Test period granularity (quarterly, monthly)

**Why embargo matters for forward-looking targets:**
With 12-month forward returns as target, training data from month T uses labels from T+12.
Without embargo, test period T+1 would overlap with training labels, causing data leakage.
Rule of thumb: `embargo_months = horizon // 2`

### Horizon-Specific Defaults

| Horizon | Min Window | Embargo | Rationale |
|---------|------------|---------|-----------|
| 3m | 3 years | 1 month | Short horizon, minimal data needed |
| 6m | 4 years | 3 months | Medium horizon |
| 12m | 5 years | 6 months | Long horizon, need more training data |

### Model Types & Objectives

| Objective | Model | Target Type | Primary Metrics |
|-----------|-------|-------------|-----------------|
| Classification | LightGBM (binary) | Binary (0/1) | AUC, Precision, Recall, F1 |
| Regression | LightGBM (regression) | Continuous | RMSE, MAE, Spearman |
| Ranking | LightGBM (lambdarank) | Relevance score | NDCG@K, Spearman |

**When to use each:**
- **Classification**: Clear thresholds (top quartile, beat median)
- **Regression**: Continuous outcomes, small groups where binary is noisy
- **Ranking**: Direct optimization of ranking quality within groups

### Key Metrics Interpretation

| Metric | Random Baseline | Good | Excellent |
|--------|-----------------|------|-----------|
| AUC | 0.50 | 0.58+ | 0.65+ |
| Lift (top decile) | 1.0x | 1.3x+ | 1.5x+ |
| Spearman | 0.00 | 0.25+ | 0.40+ |
| NDCG@10 | ~0.5 | 0.7+ | 0.85+ |
| RMSE (percentile) | ~29 | <25 | <20 |

### Feature Importance Methods

| Method | What it measures | Best for |
|--------|------------------|----------|
| `gain` | Total improvement from splits | Understanding predictive value |
| `split` | Number of times feature is used | Detecting broadly useful features |
| `SHAP` | Marginal contribution per sample | Explaining individual predictions |

### Common Issues & Solutions

| Problem | Symptoms | Solution |
|---------|----------|----------|
| Data leakage | AUC > 0.90, perfect metrics | Add embargo, check feature timing |
| Overfitting | Train >> Test performance | Reduce complexity, add regularization |
| Distribution shift | Test performance varies wildly | Use more walk-forward windows |
| Class imbalance | High precision, low recall | Use scale_pos_weight, stratified sampling |
| Small peer groups | Noisy binary labels | Use regression on percentile |

## Utility Scripts

**[list_experiments.py](scripts/list_experiments.py)** - List experiments with run counts and timestamps

```bash
python scripts/list_experiments.py                      # List all
python scripts/list_experiments.py --pattern "name/*"   # Filter by pattern
python scripts/list_experiments.py --with-runs --sort runs  # Sort by run count
python scripts/list_experiments.py --json               # JSON output
```

**[analyze_shap.py](scripts/analyze_shap.py)** - SHAP feature importance with direction analysis

```bash
# Basic usage with cached features
python scripts/analyze_shap.py --cache-file data/cache/features.parquet --transform perc

# Specify target column and output
python scripts/analyze_shap.py --cache-file data/cache/features.parquet \
    --target-col raw_return_12m --output output/shap_results.csv

# Custom date range
python scripts/analyze_shap.py --cache-file data/cache/features.parquet \
    --train-start 2018-01-01 --test-start 2024-01-01
```

Output includes:
- Feature importance ranking (by mean absolute SHAP)
- Direction classification (POSITIVE/NEGATIVE/MIXED)
- Mean SHAP values (signed, showing effect direction)
- Test AUC for model quality assessment

## References

Detailed patterns organized by task:

- **[experiment-management.md](references/experiment-management.md)** - List, delete, cleanup experiments and runs
- **[shap-analysis.md](references/shap-analysis.md)** - SHAP plots, direction analysis, feature interpretation
- **[code-patterns.md](references/code-patterns.md)** - Walk-forward artifacts, weighted metrics, comparison patterns
- **[metrics_guide.md](references/metrics_guide.md)** - Metric definitions, interpretation, red flags

## Project Documentation

See `docs/fund_ratings/README.md` for project-specific experiment configs and feature sets.

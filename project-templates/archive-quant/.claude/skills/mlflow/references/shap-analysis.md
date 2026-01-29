# SHAP Model Interpretability Reference

## TreeExplainer for LightGBM

```python
import shap

explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)

# For multi-class: shap_values is list of arrays, one per class
# shap_values[class_idx] has shape (n_samples, n_features)
```

## Common SHAP Plots

```python
# Global feature importance (all samples)
shap.summary_plot(shap_values, X_test, feature_names=feature_names)

# Bar plot of mean absolute SHAP values
shap.summary_plot(shap_values, X_test, plot_type="bar")

# Single prediction breakdown
shap.waterfall_plot(shap.Explanation(
    values=shap_values[sample_idx],
    base_values=explainer.expected_value,
    data=X_test.iloc[sample_idx],
    feature_names=feature_names
))

# Feature interaction/dependence
shap.dependence_plot("feature_name", shap_values, X_test)

# Force plot for single prediction
shap.force_plot(explainer.expected_value, shap_values[sample_idx], X_test.iloc[sample_idx])
```

## Plot Interpretation Guide

| Plot | Shows | Use For |
|------|-------|---------|
| Summary (dots) | Feature impact distribution | Which features matter, direction of effect |
| Summary (bar) | Mean absolute importance | Feature ranking |
| Waterfall | Single prediction breakdown | Explaining individual predictions |
| Dependence | Feature value vs SHAP value | Non-linear effects, interactions |
| Force | Prediction as sum of contributions | Stakeholder communication |

## SHAP with MLflow

```python
import mlflow

# Log SHAP summary plot as artifact
fig, ax = plt.subplots()
shap.summary_plot(shap_values, X_test, show=False)
mlflow.log_figure(fig, "shap_summary.png")

# Log feature importance
importance_df = pd.DataFrame({
    "feature": feature_names,
    "importance": np.abs(shap_values).mean(axis=0)
}).sort_values("importance", ascending=False)
mlflow.log_table(importance_df, "shap_importance.json")
```

## Feature Direction Analysis Across Windows

Analyze direction consistency across walk-forward windows.

```python
import shap
import numpy as np
import pandas as pd

# For each walk-forward window
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)

# For binary classification, take positive class
if isinstance(shap_values, list):
    shap_vals = shap_values[1]
else:
    shap_vals = shap_values

# Aggregate mean SHAP (with sign) and absolute SHAP (importance)
mean_shap = np.mean(shap_vals, axis=0)  # Direction (positive/negative)
abs_shap = np.mean(np.abs(shap_vals), axis=0)  # Importance (magnitude)

# Collect per-window results
results.append({
    'window': i,
    'test_year': test_year,
    'feature': feat,
    'mean_shap': mean_shap[j],
    'abs_shap': abs_shap[j],
})
```

## Direction Consistency Analysis

```python
# Aggregate across windows
overall = results_df.groupby('feature').agg({
    'mean_shap': 'mean',
    'abs_shap': 'mean',
}).reset_index()

# Classify direction
overall['direction'] = overall['mean_shap'].apply(
    lambda x: 'POSITIVE' if x > 0.01 else ('NEGATIVE' if x < -0.01 else 'MIXED')
)

# Pivot by year to see direction stability
yearly_direction = results_df.pivot_table(
    values='mean_shap',
    index='feature',
    columns='test_year',
    aggfunc='mean',
)

# Calculate consistency percentage per feature
for feat in features:
    row = yearly_direction.loc[feat].dropna()
    pos_years = (row > 0).sum()
    neg_years = (row < 0).sum()
    consistency = max(pos_years, neg_years) / len(row) * 100
```

## Interpreting Feature Direction

| Mean SHAP | Direction | Interpretation |
|-----------|-----------|----------------|
| > 0.01 | POSITIVE | Higher feature value increases prediction |
| < -0.01 | NEGATIVE | Higher feature value decreases prediction |
| else | MIXED | Effect varies by sample or time period |

## Momentum vs Mean Reversion

For return-based features:

| Feature Type | Direction | Interpretation |
|--------------|-----------|----------------|
| `raw_return_36m` | NEGATIVE | Mean reversion: past winners underperform |
| `zscore_return_36m` | POSITIVE | Momentum: peer outperformers continue |
| `raw_return_6m` | POSITIVE | Short-term momentum exists |

**Key insight**: Absolute returns often show mean reversion, while peer-relative returns (z-score) often show momentum (skill persistence).

## Risk Metric Direction Interpretation

Risk metrics have **natural direction** where higher values = worse:
- `abs_max_drawdown`: Higher = larger drop from peak = worse
- `volatility`: Higher = more volatile = worse
- `downside_volatility`: Higher = more downside risk = worse

**Interpreting SHAP Direction for Risk Metrics:**

| Direction | Raw Metric | Percentile Transform | Meaning |
|-----------|------------|---------------------|---------|
| POSITIVE | Higher risk → better future | Higher risk rank → better | **Mean reversion** (oversold recovery) |
| NEGATIVE | Lower risk → better future | Lower risk rank → better | **Risk aversion** (quality persists) |

**Key Insight - abs_max_drawdown POSITIVE:**
- Funds with larger historical drawdowns tend to outperform
- This is a **contrarian/value signal** - oversold funds recover
- NOT "lower drawdown = better" (that would be NEGATIVE direction)

**Common Mistake:**
Assuming risk metrics are inverted. Check `invert_perc` in config - if False (default),
higher percentile = higher risk = worse historical performance. A POSITIVE direction
for risk metrics indicates mean reversion, not that "lower risk is better."

## Consistency Indicator Direction

| Indicator | Expected Direction | Interpretation |
|-----------|-------------------|----------------|
| `hit_rate` | POSITIVE | Consistent beat-median predicts future success |
| `info_ratio` | MIXED/POSITIVE | Risk-adjusted outperformance may persist |
| `streaks` | POSITIVE | Consistency/momentum signal |

## Transform-Specific Patterns

The same indicator can show different directions depending on transform:

| Transform | Typical Pattern | Why |
|-----------|-----------------|-----|
| `raw` | Mean reversion | Absolute values capture extremes that revert |
| `zscore` | Momentum | Peer-relative rankings capture persistent skill |
| `perc` | Mixed | Percentile ranks are stable, may show either pattern |

**Example**: `volatility_12m`
- `raw_volatility_12m` POSITIVE → Mean reversion (high vol funds recover)
- `zscore_volatility_12m` NEGATIVE → Risk aversion (low vol peers outperform)

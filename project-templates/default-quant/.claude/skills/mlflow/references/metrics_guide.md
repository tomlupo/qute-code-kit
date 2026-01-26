# ML Metrics Guide

Quick reference for interpreting common metrics in MLflow experiments.

## Core Classification Metrics

| Metric | What it measures | When to prioritize | Good range |
|--------|------------------|-------------------|------------|
| `precision` | Of predicted positives, how many actually were | Cost of false positives is high | >0.3 (depends on class balance) |
| `recall` | Of actual positives, how many were found | Cost of missing positives is high | >0.3 (depends on class balance) |
| `f1` | Harmonic mean of precision/recall | Need balance between precision/recall | >0.3 |
| `auc` | Ranking quality (ROC-AUC) | Need probability calibration, ranking matters | >0.6 (0.5=random, 1.0=perfect) |
| `threshold` | Optimal classification threshold | Used to convert probabilities to binary predictions | Typically 0.2-0.4 for imbalanced data |

## Ranking & Correlation Metrics

| Metric | What it measures | When to prioritize | Good range |
|--------|------------------|-------------------|------------|
| `spearman` | Spearman rank correlation between predictions and actual ranks | Ranking quality matters more than classification | >0.3 |
| `lift` | Top decile positive rate / overall positive rate | Practical selection scenarios (top 10% vs random) | >1.5x (2x+ is strong) |

## Regression Metrics (for percentile targets)

| Metric | What it measures | When to prioritize | Good range |
|--------|------------------|-------------------|------------|
| `rmse` | Root mean squared error | Percentile prediction accuracy | <25 (random ~29) |
| `mae` | Mean absolute error | Percentile prediction accuracy | <20 |

**Note:** For regression on percentile (0-100), Spearman correlation is often more important than RMSE since the goal is ranking, not exact prediction.

## Top-K Metrics (Practical Selection Scenarios)

| Metric | What it measures | When to prioritize | Good range |
|--------|------------------|-------------------|------------|
| `precision_at_5` | Precision in top 5 predictions | Selecting small number of items | >0.4 |
| `precision_at_10` | Precision in top 10 predictions | Selecting top 10 items | >0.3 |
| `hit_rate_top5` | % of actual positives captured in top 5 | Coverage of positive class | >0.1 (depends on class balance) |
| `hit_rate_top10` | % of actual positives captured in top 10 | Coverage of positive class | >0.2 (depends on class balance) |
| `ndcg_at_10` | Normalized Discounted Cumulative Gain at 10 | Ranking quality with position weighting | >0.3 (1.0=perfect ranking) |

**NDCG Explanation:** Measures ranking quality by giving higher weight to correct predictions at top positions. Perfect ranking (all positives first) = 1.0.

## Aggregate Metrics (Across Walk-Forward Windows)

### Weighted Metrics (by test set size - most reliable)
- `weighted_auc`, `weighted_auc_std` - AUC weighted by test sample size
- `weighted_lift` - Lift weighted by test sample size
- `weighted_precision`, `weighted_recall`, `weighted_f1` - Classification metrics weighted
- `weighted_spearman` - Spearman correlation weighted
- `weighted_prec_at_5`, `weighted_prec_at_10` - Top-K precision weighted
- `weighted_hit_rate_top10` - Hit rate weighted
- `weighted_ndcg_at_10` - NDCG weighted

**Why weighted?** Test sets vary in size across windows. Weighting by sample size gives more reliable aggregate estimates.

### Mean Metrics (simple average)
- `mean_auc`, `mean_lift`, `mean_precision`, `mean_recall`, `mean_f1`
- `mean_spearman`, `mean_prec_at_10`, `mean_hit_rate_top10`, `mean_ndcg_at_10`

### Stability Metrics (std across windows - lower is better)
- `std_auc`, `std_lift`, `std_precision`, `std_f1`
- `std_spearman`, `std_prec_at_10`, `std_hit_rate_top10`

**Interpretation:** Low std = consistent performance across time periods. High std = model performance varies with conditions or data distribution.

### Distribution Metrics (from log_aggregate_metrics)
- `median_{metric}`, `min_{metric}`, `max_{metric}` - Distribution statistics for core metrics

## Per-Window Metrics

Each walk-forward window logs metrics in nested child runs:
- `auc`, `precision`, `recall`, `f1`, `threshold`
- `n_train`, `n_test` - Sample sizes
- `train_positive_rate`, `test_positive_rate` - Class distribution
- `spearman`, `lift` - Ranking metrics

Also logged at parent level with window suffix:
- `auc_{window_name}`, `lift_{window_name}`, `n_test_{window_name}`

## Data Quality Metrics

| Metric | What it measures | Red flags |
|--------|------------------|-----------|
| `train_positive_rate` | % of positive class in training data | <0.05 or >0.95 (severe imbalance) |
| `test_positive_rate` | % of positive class in test data | Very different from train (distribution shift) |
| `n_train`, `n_test` | Sample sizes | <100 train or <20 test (insufficient data) |

## Interpreting Multi-class Results

When metrics are logged per-class (e.g., `precision_0`, `precision_1`, `precision_2`):
- Class indices map to label encoder order (usually alphabetical or as defined)
- Check experiment tags or params for class mapping
- Minority class metrics often most important for imbalanced problems

## Comparing Runs

**Same experiment, different params:**
- Look at metric variance (`std_*` metrics) - high variance suggests instability
- Check if improvements are consistent across windows
- Compare `weighted_*` metrics (most reliable) and `mean_*` metrics

**Different experiments:**
- Ensure same evaluation data/splits
- Check for data leakage (suspiciously high metrics)
- Compare both weighted means and std of metrics
- For selection scenarios, prioritize `lift`, `precision_at_10`, `hit_rate_top10`

## Quality Assessment Tiers

For fund rating models (topq target, 25% base rate):

### Marginal (Barely beats random)
- AUC: 0.50-0.54 (1-4 points above random)
- Lift: 1.0-1.15x
- Prec@10: 25-30%
- **Action:** Investigate features, likely insufficient signal. Iterate before production.

### Acceptable (Useful but limited)
- AUC: 0.54-0.58
- Lift: 1.15-1.30x
- Prec@10: 30-35%
- **Action:** Usable for screening, not high-confidence picks. Use with caution.

### Good (Production-ready)
- AUC: 0.58-0.65
- Lift: 1.30-1.50x
- Prec@10: 35-45%
- **Action:** Reliable for fund selection. Ready for production.

### Strong (Exceptional)
- AUC: >0.65
- Lift: >1.50x
- Prec@10: >45%
- **Action:** Verify no data leakage. Deploy with confidence if validated.

## Red Flags

**Data Issues:**
- `auc` = 1.0 or near-perfect: likely data leakage or trivial problem
- `test_positive_rate` very different from `train_positive_rate`: distribution shift
- Metrics vary wildly across windows (`std_auc` > 0.1): unstable training or data issues

**Model Issues:**
- Large gap between train/val metrics: overfitting
- `precision` high but `recall` low: model too conservative
- `recall` high but `precision` low: model too aggressive

**Performance Issues (Fund Prediction):**
- `auc` < 0.52: Model barely beats random (random = 0.50)
- `lift` < 1.10x: Top decile not much better than random (random = 1.0x)
- `weighted_auc` < 0.54: Model is marginal, iterate before production
- AUC good but Lift poor: Model doesn't rank well at top (check Prec@10)

## Quick Assessment Checklist

When reviewing a model run:

1. **Beats random?**
   - AUC > 0.52 (vs 0.50 random)
   - Lift > 1.10x (vs 1.0x random)
   - Prec@10 > base rate (25% for topq)

2. **Production-ready?**
   - AUC > 0.58
   - Lift > 1.30x
   - std_auc < 0.05 (stable across windows)

3. **Red flags absent?**
   - No data leakage indicators
   - Consistent train/test distributions
   - Reasonable metric variance

## Best Practices

For binary classification with ranking/selection use cases:
- **Primary metrics:** `weighted_auc` (ranking quality), `weighted_lift` (practical value)
- **Selection metrics:** `weighted_prec_at_10`, `weighted_hit_rate_top10` (top-K selection)
- **Stability:** `std_auc` < 0.05 indicates consistent performance across time periods
- **Threshold:** `threshold` typically 0.2-0.4 for imbalanced classification problems

**Domain context:** Fund prediction is inherently noisy. AUC 0.54-0.58 is realistic for practical screening value. Don't expect stock-picking-level accuracy.

# MLflow Code Patterns Reference

## Walk-Forward Validation Artifacts

```python
# Common artifact structure for walk-forward validation
# artifacts/
#   summary_{run_name}.csv    - Per-window results
#   feature_importance_gain.json - LightGBM gain importance

# Load summary CSV from run
artifacts = client.list_artifacts(run_id)
for art in artifacts:
    if art.path.endswith('.csv') and 'summary' in art.path:
        summary_path = f'mlruns/{exp_id}/{run_id}/artifacts/{art.path}'
        df = pd.read_csv(summary_path)
```

## Year-by-Year Aggregation

```python
# Group walk-forward results by test year
yearly = df.groupby('test_year').agg({
    'auc': ['mean', 'std'],
    'lift': 'mean',
    'n_test': 'sum'
})
```

## Weighted Metrics

```python
import numpy as np

# Weighted AUC (weight by sample size)
weighted_auc = np.average(df['auc'], weights=df['n_test'])

# Weighted lift
weighted_lift = np.average(df['lift'], weights=df['n_test'])
```

## Feature Importance (JSON Format)

```python
import json

# MLflow logs feature importance as {"columns": [...], "data": [[...], ...]}
with open(f'mlruns/{exp_id}/{run_id}/artifacts/feature_importance_gain.json') as f:
    data = json.load(f)

# Convert to DataFrame
imp_df = pd.DataFrame(data['data'], columns=data['columns'])
imp_df = imp_df.sort_values('importance', ascending=False)

# Calculate percentage
total = imp_df['importance'].sum()
imp_df['pct'] = (imp_df['importance'] / total * 100).round(1)
```

## Multi-Experiment Comparison

### CLI Tool

```bash
# Compare transform strategies vs baseline
uv run python scripts/ml/compare_experiments.py --window-analysis --pattern "exp01,exp02" --baseline exp01

# Compare all exp03 (feature groups) variants
uv run python scripts/ml/compare_experiments.py --window-analysis --pattern "exp03" --baseline exp03g

# Save report to file
uv run python scripts/ml/compare_experiments.py --window-analysis --pattern "exp02" --output-dir reports/
```

### Python API

```python
from scripts.ml.compare_experiments import load_window_runs, window_analysis_report
from pathlib import Path

# Load window-level data
df = load_window_runs(Path("mlruns"), pattern="exp01,exp02")

# Generate report
report = window_analysis_report(df, baseline_pattern="exp01")
print(report)
```

### Direct MLflow API

```python
# Compare runs by name pattern
experiments_to_compare = ['exp_v1', 'exp_v2', 'exp_v3']
results = {}

for name in experiments_to_compare:
    runs = client.search_runs(
        experiment_ids=[exp_id],
        filter_string=f"tags.mlflow.runName LIKE '{name}%'",
        order_by=['start_time DESC'],
        max_results=1
    )
    if runs:
        results[name] = runs[0]

# Compare metrics
for name, run in results.items():
    print(f"{name}: AUC={run.data.metrics['mean_auc']:.4f}")
```

## Compare Runs by Parameter

```python
# Group by a parameter, show metric statistics
df.groupby("params.window_size")["metrics.f1_macro"].agg(["mean", "std", "max"])
```

## Find Best Runs

```python
# Top 5 by metric
df.nlargest(5, "metrics.precision_1")[["run_id", "params.model_type", "metrics.precision_1"]]
```

## Parameter Sensitivity

```python
# Pivot to see metric across parameter combinations
df.pivot_table(
    values="metrics.f1_macro",
    index="params.window_size",
    columns="params.class_weight",
    aggfunc="mean"
)
```

## Time-based Analysis

```python
df["start_time"] = pd.to_datetime(df["start_time"])
df.sort_values("start_time").plot(x="start_time", y="metrics.f1_macro")
```

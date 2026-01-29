# Experiment Management Reference

## List Experiments (Filesystem - Fast)

```python
import yaml
from pathlib import Path
from datetime import datetime

mlruns = Path('mlruns')
results = []

for exp_dir in mlruns.iterdir():
    if not exp_dir.is_dir() or exp_dir.name.startswith('.') or exp_dir.name == 'models':
        continue

    meta_file = exp_dir / 'meta.yaml'
    if not meta_file.exists():
        continue

    with open(meta_file) as f:
        meta = yaml.safe_load(f)

    name = meta.get('name', 'Unknown')
    runs = [d for d in exp_dir.iterdir() if d.is_dir() and (d / 'meta.yaml').exists()]

    if runs:
        run_times = []
        for run_dir in runs:
            run_meta = run_dir / 'meta.yaml'
            if run_meta.exists():
                with open(run_meta) as f:
                    rm = yaml.safe_load(f)
                    if rm and 'start_time' in rm:
                        run_times.append(rm['start_time'])

        if run_times:
            oldest = datetime.fromtimestamp(min(run_times)/1000).strftime('%Y-%m-%d %H:%M')
            newest = datetime.fromtimestamp(max(run_times)/1000).strftime('%Y-%m-%d %H:%M')
        else:
            oldest = newest = '-'
    else:
        oldest = newest = '-'

    results.append((name, len(runs), oldest, newest, exp_dir.name))

results.sort(key=lambda x: x[0])
print(f"{'Experiment':<55} {'Runs':>5} {'Oldest':>17} {'Newest':>17}")
print('-'*97)
for name, runs, oldest, newest, exp_id in results:
    print(f'{name:<55} {runs:>5} {oldest:>17} {newest:>17}')
```

## List Experiments (MLflow API)

```python
import mlflow
mlflow.set_tracking_uri('mlruns')
client = mlflow.tracking.MlflowClient()

experiments = client.search_experiments()
for exp in sorted(experiments, key=lambda x: x.name):
    if exp.lifecycle_stage == 'deleted':
        continue
    print(f'{exp.experiment_id:>20} | {exp.name}')
```

## Find Duplicate Experiment Names

```python
from collections import Counter

names = [exp.name for exp in experiments if exp.lifecycle_stage != 'deleted']
duplicates = [name for name, count in Counter(names).items() if count > 1]
print(f"Duplicate experiment names: {duplicates}")
```

## Delete Experiments

```python
import mlflow
mlflow.set_tracking_uri('mlruns')
client = mlflow.tracking.MlflowClient()

# Delete by experiment ID (moves to .trash/)
client.delete_experiment('experiment_id_here')

# Delete multiple
to_delete = ['id1', 'id2', 'id3']
for exp_id in to_delete:
    client.delete_experiment(exp_id)
    print(f'Deleted {exp_id}')
```

## Delete Runs from Experiment

```python
# Delete all runs from an experiment (e.g., Default bucket)
for run in client.search_runs('0'):  # '0' is Default experiment
    client.delete_run(run.info.run_id)
```

## Find Stale/Orphan Runs

```python
from datetime import datetime, timedelta

# Find runs older than 7 days
cutoff = datetime.now() - timedelta(days=7)
cutoff_ms = int(cutoff.timestamp() * 1000)

for exp in client.search_experiments():
    runs = client.search_runs(
        exp.experiment_id,
        filter_string=f"start_time < {cutoff_ms}",
        max_results=100
    )
    if runs:
        print(f"{exp.name}: {len(runs)} runs older than 7 days")
```

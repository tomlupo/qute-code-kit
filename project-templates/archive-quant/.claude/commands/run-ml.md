# Run ML Experiments and Analyze

Run ML experiments from a config file and analyze the results.

## Arguments
- $ARGUMENTS: Config file path or experiment name (e.g., `fio_baseline_refresh` or full path)

## Instructions

1. **Resolve config path**: If argument is a short name (e.g., `fio_baseline_refresh`), search for matching YAML in `config/experiments/` directories. Otherwise use the provided path.

2. **Run batch experiments** with parallel execution:
   ```bash
   uv run python scripts/ml/run_batch_experiments.py --config <CONFIG_PATH> --all --parallel 4
   ```

3. **Extract experiment name** from the config file's `experiment_name` field.

4. **Use mlflow-analyzer agent** for comprehensive analysis:
   - Launch the `mlflow-analyzer` subagent to analyze experiment results
   - Compare experiments, find best runs, analyze metrics
   - The agent has access to: Read, Grep, Glob, Bash tools

5. **Use mlflow skill** if needed:
   - Invoke the `mlflow` skill for deeper analysis of SHAP values, feature importance, or experiment comparison
   - Skill triggers: MLflow, experiment comparison, SHAP, feature importance, model interpretability

6. **Run comparison scripts** for structured output:
   ```bash
   uv run python scripts/ml/compare_experiments.py --experiment "<EXPERIMENT_NAME>" --pattern "<PARENT_RUN_PATTERN>*" --detailed
   uv run python scripts/ml/compare_experiments.py --window-analysis --experiment "<EXPERIMENT_NAME>" --pattern "<PARENT_RUN_PATTERN>*"
   ```

7. **SHAP feature analysis** (optional, if user requests or for significant experiments):
   ```bash
   # For batch configs with multiple experiments, use --experiment to select one
   uv run python scripts/ml/analyze_shap_features.py \
       --config <CONFIG_PATH> \
       --experiment <EXPERIMENT_NAME> \
       --output output/shap_analysis/<EXPERIMENT_NAME>_shap.xlsx

   # For single-experiment configs, omit --experiment
   uv run python scripts/ml/analyze_shap_features.py \
       --config <CONFIG_PATH> \
       --output output/shap_analysis/<EXPERIMENT_NAME>_shap.xlsx
   ```

   The script reads `feature_transforms` from the config automatically (no need for --transform flag).

8. **Summarize results** - provide a brief summary of:
   - Best performing configuration
   - Key metrics (AUC, Lift, Prec@10, NDCG@10)
   - Feature importance with direction (if SHAP analyzed).ml
   - Notable patterns or insights

## Research Questions

When analyzing results, consider these key questions:

### Feature Tier Comparison
- Which tier performs best (base vs extended vs full)?
- Does adding more features improve or hurt performance?
- Is there a point of diminishing returns?

### Transform Strategy
- Which transform works best for AUC vs top picks (Prec@10)?
- Does domain_driven outperform global transforms (zscore, perc)?
- Are certain transforms better for certain indicator types?

### Feature Selection
- Does selection improve full tier performance?
- What's the optimal top_k (15 vs 20 vs 25)?
- Which features consistently appear in top selections?

### Stability Analysis
- How stable is performance across years? (check std dev)
- Are there specific years where model fails?
- Does the winning config change by market regime?

## Notes
- Use `--parallel 4` to speed up experiment execution
- Filter parent runs only (exclude child window runs) using pattern matching
- SHAP analysis uses `--experiment` flag for batch configs (e.g., `--experiment full`)
- Save research reports to `output/fund_ratings/YYYY-MM-DD/` for significant findings

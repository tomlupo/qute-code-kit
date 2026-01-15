# /research:experiment

Document an experiment with setup, parameters, and results.

## Usage

```
/research:experiment <experiment-name> [--hypothesis <hypothesis-file>]
```

## Arguments

- `<experiment-name>` - Short identifier (e.g., "dropout-test-v1", "lr-sweep")
- `--hypothesis` - (Optional) Link to hypothesis being tested

## Behavior

1. **Generate filename**
   - Format: `YYYY-MM-DD_<experiment-name>.md`

2. **Create experiment document** at `docs/research/experiments/<filename>`:
   ```markdown
   # Experiment: <experiment-name>

   **Date**: YYYY-MM-DD
   **Status**: 🏃 Running | ✅ Complete | ❌ Failed

   ## Hypothesis
   <!-- Link to hypothesis if applicable -->
   Testing: [hypothesis-name](../hypotheses/YYYY-MM-DD_hypothesis.md)

   ## Objective
   <!-- What are we trying to learn? -->

   ## Setup

   ### Environment
   - Python: 3.x
   - Key packages: ...

   ### Parameters
   | Parameter | Value |
   |-----------|-------|
   | learning_rate | 0.001 |
   | batch_size | 32 |
   | epochs | 100 |

   ### Data
   - Dataset: ...
   - Train/Val/Test split: ...

   ## Procedure
   1. Step 1
   2. Step 2
   3. ...

   ## Results

   ### Metrics
   | Metric | Baseline | This Experiment |
   |--------|----------|-----------------|
   | Accuracy | 0.85 | 0.89 |
   | Loss | 0.32 | 0.28 |

   ### Observations
   - ...

   ### Artifacts
   - Model: `models/experiment-name/`
   - Logs: `logs/experiment-name/`
   - MLflow run: `run_id`

   ## Conclusions
   <!-- What did we learn? -->

   ## Next Steps
   - [ ] ...
   ```

3. **Update index.md**
   - Add entry under "Recent Experiments"

4. **Link to hypothesis** (if provided)
   - Add experiment reference to the hypothesis document

## Example

```
/research:experiment dropout-test-v1 --hypothesis dropout-overfitting

# Output:
✅ Experiment documented: docs/research/experiments/2026-01-13_dropout-test-v1.md

Linked to hypothesis: dropout-overfitting

Template created with sections for:
  - Setup & parameters
  - Procedure
  - Results & metrics
  - Conclusions
```

# /research:finding

Document a validated finding from your research.

## Usage

```
/research:finding "<finding-title>" [--confidence high|medium|low]
```

## Arguments

- `<finding-title>` - Clear, concise title for the finding
- `--confidence` - Confidence level (default: medium)

## Behavior

1. **Generate filename**
   - Format: `YYYY-MM-DD_<slug>.md`

2. **Create finding document** at `docs/research/findings/<filename>`:
   ```markdown
   # Finding: <title>

   **Date**: YYYY-MM-DD
   **Confidence**: 🟢 High | 🟡 Medium | 🔴 Low

   ## Summary
   <!-- One-paragraph summary of the finding -->

   ## Evidence

   ### Experiments
   - [Experiment 1](../experiments/YYYY-MM-DD_exp1.md) - Key result
   - [Experiment 2](../experiments/YYYY-MM-DD_exp2.md) - Supporting result

   ### Data
   - Dataset: ...
   - Sample size: ...
   - Statistical significance: p < 0.05

   ### Metrics
   | Metric | Before | After | Improvement |
   |--------|--------|-------|-------------|
   | ... | ... | ... | ... |

   ## Implications
   <!-- What does this mean for the project? -->

   ## Limitations
   <!-- What are the caveats? -->

   ## Next Steps
   - [ ] Apply finding to production
   - [ ] Document in project README
   - [ ] Share with team

   ## Related
   - Hypothesis: [link]
   - Papers: [link]
   ```

3. **Update hypothesis status** (if linked)
   - Mark hypothesis as ✅ Validated or ❌ Rejected

4. **Update index.md**
   - Add entry under "Key Findings"

## Confidence Levels

- 🟢 **High** - Multiple experiments confirm, statistically significant
- 🟡 **Medium** - Some evidence, needs more validation
- 🔴 **Low** - Preliminary observation, requires further testing

## Example

```
/research:finding "Dropout of 0.3 reduces overfitting by 18%" --confidence high

# Output:
✅ Finding documented: docs/research/findings/2026-01-13_dropout-reduces-overfitting.md

Confidence: 🟢 High

Added to research index under "Key Findings"
```

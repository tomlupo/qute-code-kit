# /research:hypothesis

Document a hypothesis to be tested through experiments.

## Usage

```
/research:hypothesis "<hypothesis-statement>"
```

## Arguments

- `<hypothesis-statement>` - Clear, testable statement (in quotes)

## Behavior

1. **Generate filename**
   - Format: `YYYY-MM-DD_<slug>.md`
   - Slug: lowercase, hyphens, from first few words

2. **Create hypothesis document** at `docs/research/hypotheses/<filename>`:
   ```markdown
   # Hypothesis: <title>

   **Date**: YYYY-MM-DD
   **Status**: 🔬 Testing

   ## Statement
   <hypothesis-statement>

   ## Rationale
   <!-- Why do we believe this might be true? -->

   ## Test Plan
   <!-- How will we validate/invalidate this? -->
   - [ ] Experiment 1: ...
   - [ ] Experiment 2: ...

   ## Results
   <!-- Link to experiments and outcomes -->

   ## Conclusion
   <!-- Final verdict: Validated / Rejected / Inconclusive -->
   ```

3. **Update index.md**
   - Add entry under "Active Hypotheses" section

4. **Output confirmation**:
   ```
   ✅ Hypothesis documented: <filename>

   Status: 🔬 Testing

   Next steps:
   - Define test plan in the document
   - Run experiments: /research:experiment <name>
   - Document findings: /research:finding <title>
   ```

## Example

```
/research:hypothesis "Adding dropout layers will reduce overfitting by 15%"

# Output:
✅ Hypothesis documented: docs/research/hypotheses/2026-01-13_dropout-overfitting.md

Status: 🔬 Testing

Next steps:
  - Edit the document to add rationale and test plan
  - /research:experiment dropout-baseline
```

## Status Values

- 🔬 **Testing** - Currently being validated
- ✅ **Validated** - Hypothesis confirmed by experiments
- ❌ **Rejected** - Hypothesis disproven
- ⏸️ **Paused** - Testing paused, needs more data

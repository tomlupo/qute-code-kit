# /research:start

Initialize a research topic and create the research folder structure.

## Usage

```
/research:start <topic-name>
```

## Arguments

- `<topic-name>` - Short identifier for the research topic (e.g., "feature-selection", "model-optimization")

## Behavior

1. **Check for existing structure**
   - Look for `docs/research/` in the current project
   - If it doesn't exist, create the full structure

2. **Create research directories**
   ```
   docs/research/
   ├── index.md
   ├── hypotheses/
   ├── experiments/
   ├── findings/
   └── papers/
   ```

3. **Initialize index.md** if not present:
   ```markdown
   # Research Index

   ## Active Hypotheses
   <!-- Auto-updated -->

   ## Recent Experiments
   <!-- Auto-updated -->

   ## Key Findings
   <!-- Auto-updated -->

   ## Papers Reviewed
   <!-- Auto-updated -->
   ```

4. **Create topic entry** in index.md under "Active Topics"

5. **Output confirmation**:
   ```
   ✅ Research structure initialized for: <topic-name>

   Next steps:
   - /research:hypothesis "Your hypothesis statement"
   - /research:experiment <experiment-name>
   - /research:paper <url-or-file>
   ```

## Example

```
/research:start model-ensemble

# Output:
✅ Research structure initialized for: model-ensemble

Created:
  docs/research/index.md
  docs/research/hypotheses/
  docs/research/experiments/
  docs/research/findings/
  docs/research/papers/

Next steps:
  /research:hypothesis "Ensemble methods will improve accuracy by 5%"
```

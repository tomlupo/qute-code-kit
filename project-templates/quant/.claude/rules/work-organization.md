# Work Organization

## Directory Structure

`/config/` - Configuration files (see Config/Output Symmetry below)
`/data/` - Datasets (see datasets.md for details)
`/output/` - Analysis results (see Config/Output Symmetry below)
`/reports/` - Polished deliverables (small collection)
`/analysis/` - Human exploratory work: `/{YYYYMMDD-name}/` (NOT for AI files)
`/scratch/` - Temporary exploration (gitignored): `/scratch/{agent-name}/`
`/docs/` - Documentation (see documentation.md for subdirectories)
`/src/` - Production code used across other files (imported/shared modules)
`/scripts/` - Standalone reusable scripts
`/app/` - Interactive web dashboard (if applicable)
`/models/` - Serialized model artifacts (not design docs - those live in `docs/models/`)
`/notebooks/` - Jupyter notebooks for exploration
`/tests/` - Test suite
`/mlruns/` - MLflow experiment tracking (auto-generated, gitignored)

Root-level files:
`TASKS.md` - Task tracking (Now/Next/Later/Completed)
`README.md` - Project overview

## File Placement Decision Tree

Input data? -> `/data/` (raw/intermediate/processed)
Analysis output? -> `/output/{analysis-name}/`
Polished deliverable? -> `/reports/`
Human exploratory work? -> `/analysis/{date-name}/`
AI exploration/scripts? -> `/scratch/{agent-name}/
Documentation? -> `/docs/` (appropriate subdirectory)
Reusable code? -> `/src/` (if used across files) or `/scripts/` (standalone)

When uncertain, ASK before creating files.

## Rule: Scratch First

ALL agent-generated files go in `scratch/{agent-name}/{artifact-name}/` first.

**Agent names**: Use the tool name - `claude`, `codex`, `cursor`, `gemini`, `copilot`, etc.

Examples:
- `scratch/claude/fiz-scraper/script.py`
- NOT `scripts/script.py`
- NOT `docs/notes.md`
- NOT `scratch/my-work/file.py` (missing agent-name)

Only create outside scratch if:
1. User explicitly specifies path: "Create X at Y"
2. Editing existing files (not new content)
3. User explicitly requests cleanup/organization of existing code

**After creation**: Notify user where work is located for review.

## When to Promote Files

- Data: Output becomes input to other analyses -> `/data/processed/{dataset-name}/`
- Code: Scratch becomes reusable -> `/src/` (if used across files) or `/scripts/` (standalone)
- Output: Report ready to share -> `/reports/`
- Reference: Output becomes reference material -> `/docs/reference/`

## Config/Output Symmetry

For artifact-specific pipelines, use matching folder names:

| Artifact | Config | Output |
|----------|--------|--------|
| tactical-signals | `config/tactical-signals/` | `output/tactical-signals/` |
| features | `config/features/` | `output/features/` |
| ml | `config/ml/` | `output/ml/` |

**Pattern**: Script reads `config/{artifact}/{name}.yaml`, writes to `output/{artifact}/{name}/`

**Benefits**:
- Easy to find config for any output
- Easy to find output for any config
- Clear artifact boundaries

## Common Mistakes

- Scripts in root, mixing raw/processed data, AI files in `/analysis/`, deep nesting, referencing `scratch/` from permanent docs
- Mismatched config/output paths (e.g., `config/research/tactical/` -> `output/feature_analysis/`)

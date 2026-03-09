# Worktrees for Data-Heavy Projects

Additional setup steps when working with worktrees for projects with large `data/` directories (quant, ML, data science).

## When to Use This Guide

Use these instructions after following the main worktree setup in [SKILL.md](SKILL.md) **only if**:
- The project has a `data/` directory (or similar: `datasets/`, `raw/`, `models/`)
- The data directory is large enough that duplicating it would be wasteful

If the project has no data directory or data is small (<100MB), skip these instructions.

## Symlink Data Directories

After creating the worktree, symlink data directories back to the main repo to avoid duplication:

```bash
cd .worktrees/<branch-name>

# Remove empty data dir (created by git if tracked, or mkdir'd by setup scripts)
rm -rf data

# Symlink to main repo's data directory
ln -s ../../data data
```

For multiple data directories:

```bash
for dir in data models artifacts; do
  if [ -d "../../$dir" ]; then
    rm -rf "$dir"
    ln -s "../../$dir" "$dir"
  fi
done
```

**Important:** Symlinked data is shared — changes in one worktree affect all others. This is usually what you want (one copy of truth), but be aware when running destructive data operations.

## Virtual Environments

Each worktree needs its own virtual environment — don't symlink `.venv`:

```bash
cd .worktrees/<branch-name>
uv venv
uv sync          # or: uv pip install -r requirements.txt
```

This is necessary because venvs contain absolute paths that break when shared across directories.

## MLflow / Experiment Tracking

If the project uses MLflow with a local tracking directory:

```bash
# Option A: Symlink to share experiment history
ln -s ../../mlruns mlruns

# Option B: Separate tracking (isolate experiments per worktree)
# Just let MLflow create a new mlruns/ — no action needed
```

Use Option A when comparing experiments across branches. Use Option B when experiments might conflict.

## Jupyter Notebooks

Notebooks with outputs can cause merge conflicts. In worktrees used for experimentation:

```bash
# Strip outputs before committing
uv run jupyter nbconvert --clear-output --inplace notebooks/*.ipynb
```

## Example Complete Workflow

```bash
# 1. Create worktree
git worktree add .worktrees/momentum-decay -b momentum-decay
cd .worktrees/momentum-decay

# 2. Symlink data directories
for dir in data models; do
  [ -d "../../$dir" ] && rm -rf "$dir" && ln -s "../../$dir" "$dir"
done

# 3. Create isolated venv
uv venv && uv sync

# 4. Share experiment tracking
ln -s ../../mlruns mlruns

# 5. Work
uv run python src/backtest.py --strategy momentum

# Later: clean up
cd ../..
git worktree remove .worktrees/momentum-decay
```

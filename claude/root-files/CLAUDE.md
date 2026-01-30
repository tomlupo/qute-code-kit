# @CLAUDE.md

<!-- Project-specific instructions only. Generic rules live in .claude/rules/ -->
Project-specific guidance for AI assistants. For non-Claude tools, see @AGENTS.md.

## Project Goal

[What the project does and its primary purpose. 1-3 sentences.]

## Documentation

**Start here:** @docs/README.md
<!-- Add more entry points as needed -->

[Brief map of docs/ subdirectories if the project has structured documentation.]

## Key Paths

| Purpose | Location |
|---------|----------|
| ... | `path/` |

<!-- List directories/files that are frequently needed but not obvious from the repo structure. -->

## Key Commands

<!-- Common workflows an assistant needs to know.
     Adapt the table below to your project's entry points. -->

| Task | Command |
|------|---------|
| Train model | `uv run python scripts/train.py --config <yaml>` |
| Score / predict | `uv run python scripts/score.py --config <yaml>` |
| Evaluate | `uv run python scripts/evaluate.py --experiment <name>` |
| Backtest | `uv run python scripts/research/backtest.py --experiment <name>` |
| Precompute features | `uv run python scripts/data/precompute.py --all` |
| View experiments | `uv run mlflow ui` |

<!-- Add project-specific commands, remove unused rows. -->

## Data Conventions

<!-- Column naming, ID schemes, join keys, date/frequency conventions, category systems.
     Quant projects almost always have column-name mismatches across modules —
     documenting them here prevents merge bugs. -->

<!-- Example — fund ID column varies by module:
| Module | ID Column | Notes |
|--------|-----------|-------|
| Features | `code` | Historical convention |
| Predictions | `fund_code` | Newer convention |

When merging across modules, rename as needed:
```python
df.rename(columns={'code': 'fund_code'})
```
-->

<!-- Example — category systems:
| System | Column | Values |
|--------|--------|--------|
| Broad asset class | `category` | 12 classes |
| Strategy group | `group` | 127 groups |
-->

<!-- Example — date conventions:
- All dates are month-end (`YYYY-MM-DD`, last business day)
- Frequency: monthly returns, quarterly fundamentals
- Lookback windows specified in months (e.g., `lookback: 36`)
-->

<!--
## Config System

Where configs live, inheritance rules, key parameters.
Useful for config-driven ML pipelines.

Example:
| Purpose | Path |
|---------|------|
| Shared defaults | `config/base/` |
| ML experiments | `config/research/ml/` |
| Scoring | `config/scoring/` |

Configs automatically inherit from `config/base/` files.
See [Config Format](docs/reference/config-format.md) for schema.
-->

<!--
## Experiment Tracking

MLflow / W&B setup, experiment naming, how to view results.

Example:
- Tool: MLflow (`mlruns/` directory, view with `uv run mlflow ui`)
- Experiment naming: `{pipeline}/{config_name}` (e.g., `fund_ratings/ml_all_features`)
- Key metrics logged: accuracy, precision, recall, coverage
- Artifacts: model files, feature importance, predictions
-->

## Domain Knowledge

<!-- Project-specific conventions, data quirks, gotchas.
     Things an AI assistant would get wrong without being told.
     Examples:
     - Historical vs current data mappings
     - Enum values or magic numbers
     - Performance caveats (e.g., small group sizes reduce reliability)
     - Module-specific assumptions
-->


<!--
## Companion files

.claude/rules/          - Generic coding rules (auto-loaded by Claude Code)
AGENTS.md               - Entry point for non-Claude tools (Codex, Cursor, Gemini)
-->

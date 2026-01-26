# Claude Skills Collection

Custom and curated skills for [Claude Code](https://claude.ai/code) to enhance AI-assisted development and research workflows.

## Overview

This repository contains skill files that guide Claude Code's behavior for specific tasks. Skills provide domain-specific knowledge, best practices, and patterns that Claude Code loads contextually to produce higher-quality outputs.

## Directory Structure

```
claude/skills/
├── external/           # Third-party skills (curated from open source)
│   ├── dignified-python-313/   # Python 3.13 coding standards
│   └── scientific-skills/      # 27+ scientific computing skills
└── my/                 # Custom skills (project-specific)
    ├── context-management/     # Token budget strategies
    ├── generating-commit-messages/  # Commit message standards
    ├── sql-patterns/           # SQL query templates
    └── worktrees/              # Git worktree workflows
```

## Skills

### Custom Skills (`my/`)

| Skill | Description | Triggers |
|-------|-------------|----------|
| **context-management** | Strategies for managing token budget in long conversations | Large codebases, extensive analysis, "running low on context" |
| **generating-commit-messages** | Standardized commit message format with detailed descriptions | Every git commit (mandatory) |
| **sql-patterns** | Query patterns for PostgreSQL/MySQL exploration and analysis | SQL, database queries, schema exploration |
| **worktrees** | Git worktree workflows for parallel development with agents | "Work in new worktree", isolated feature development |

### External Skills (`external/`)

#### Dignified Python 3.13

Source: [Dagster Labs](https://dagster.io/)

Python 3.13 coding standards covering:
- LBYL exception handling patterns
- Modern type syntax (`list[str]`, `str | None`)
- Pathlib operations
- ABC-based interfaces
- Explicit error boundaries

#### Scientific Skills

Source: [K-Dense-AI/claude-scientific-skills](https://github.com/K-Dense-AI/claude-scientific-skills)

27+ skills curated for quantitative finance and research:

**Machine Learning & Statistical Modeling**
- scikit-learn, pytorch-lightning, statsmodels, pymc, aeon, shap, transformers, scikit-survival, torch_geometric

**Optimization & Simulation**
- pymoo (multi-objective optimization), simpy (discrete event simulation), sympy (symbolic math)

**Data Processing**
- polars, dask, vaex

**Visualization**
- matplotlib, seaborn, plotly, scientific-visualization, networkx, umap-learn

**Research Tools**
- openalex-database, perplexity-search, literature-review, citation-management

See [scientific-skills/README.md](external/scientific-skills/README.md) for detailed use cases.

## Usage with Claude Code

### Reference in CLAUDE.md

Add skills to your project's `CLAUDE.md`:

```markdown
## Skills
- Use skills in `claude/skills/my/` for development workflows
- Use `claude/skills/external/scientific-skills/` for quantitative analysis
- ALWAYS use generating-commit-messages skill before any commit
```

### Direct Skill Reference

Reference skills directly in prompts:

```
@claude/skills/my/sql-patterns/SKILL.md Write a query to find duplicate orders
```

### Automatic Loading

Skills with clear triggers load automatically based on context. For example:
- Mentioning "git commit" triggers the commit message skill
- Working with Python 3.13 triggers dignified-python standards
- Database exploration triggers SQL patterns

## Adding New Skills

Skills follow a standard structure:

```
skill-name/
├── SKILL.md          # Main skill file (required)
├── references/       # Additional reference documentation
├── scripts/          # Helper scripts
└── assets/           # Templates, config files
```

SKILL.md frontmatter:

```yaml
---
name: skill-name
description: |
  Brief description of what the skill does.
  When to use it and trigger patterns.
---
```

## License

- Custom skills (`my/`): Personal use
- External skills: See individual skill directories for license information
  - scientific-skills: MIT License (from K-Dense-AI)
  - dignified-python-313: From Dagster Labs

# qute-ai-tools

A collection of AI tools and utilities for autonomous coding, skill creation, and Claude Code integration.

## Projects

### [Ralph](ralph/)

A minimal, file-based agent loop for autonomous coding. Each iteration starts fresh, reads on-disk state, and commits work for one story at a time. Supports multiple AI agents (Codex, Claude, Droid, OpenCode).

**Key Features:**
- PRD (JSON) defines stories, gates, and status
- Loop executes one story per iteration
- State persists in `.ralph/`
- Global CLI: `npm i -g @iannuttall/ralph`

### [SkillForge](SkillForge/)

A methodology for AI skill creation with a rigorous 4-phase architecture: Deep Analysis, Specification, Generation, and Multi-Agent Synthesis. Transforms skill creation from an art into an engineering discipline.

**Key Features:**
- Phase 0: Universal Skill Triage (v4.0)
- 11 thinking lenses for deep analysis
- Multi-agent synthesis panel with unanimous approval requirement
- Evolution & Timelessness scoring (≥7/10 required)
- Agentic capabilities with script integration

### [claude-marketplace](claude-marketplace/)

A personal Claude Code plugin marketplace. Register once, add plugins easily. Includes workflow management, research documentation, multi-model code review, and push notifications.

**Included Plugins:**
- **workflow-plugin** - Session, task, and context management
- **research-workflow** - Comprehensive research workflow for ML/data science
- **llm-external-review** - Multi-model code review (GPT-5, Gemini, etc.)
- **llm-council** - Multi-model LLM council for diverse AI perspectives
- **notifications** - Push notifications via ntfy.sh
- **forced-eval** - Forced evaluation and validation

### [claude-skills](claude-skills/)

Custom and curated skills for Claude Code to enhance AI-assisted development and research workflows.

**Custom Skills (`my/`):**
- **context-management** - Token budget strategies
- **generating-commit-messages** - Standardized commit message format
- **sql-patterns** - Query patterns for PostgreSQL/MySQL
- **worktrees** - Git worktree workflows

**External Skills (`external/`):**
- **dignified-python-313** - Python 3.13 coding standards (from Dagster Labs)
- **scientific-skills** - 27+ skills for quantitative finance and research:
  - Machine Learning: scikit-learn, pytorch-lightning, statsmodels, pymc, transformers, torch_geometric
  - Optimization: pymoo, simpy, sympy
  - Data Processing: polars, dask, vaex
  - Visualization: matplotlib, seaborn, plotly, scientific-visualization
  - Research Tools: openalex-database, perplexity-search, literature-review, citation-management

### [claude-agents](claude-agents/)

Custom and external agent definitions for specialized workflows.

**Custom Agents (`my/`):**
- **database-explorer** - Database exploration and analysis
- **mlflow-analyzer** - MLflow experiment tracking and analysis
- **obsidian-knowledge** - Obsidian knowledge base integration
- **research-paper-analyst** - Academic paper analysis and extraction

**External Agents (`external/`):**
- **code-refactorer** - Automated code refactoring
- **content-writer** - Content generation and writing
- **frontend-designer** - Frontend design and UI/UX
- **prd-writer** - Product Requirements Document generation
- **project-task-planner** - Project planning and task breakdown
- **security-auditor** - Security analysis and auditing
- **vibe-coding-coach** - Coding style and best practices
- **workflow-worktrees** - Git worktree workflow automation

## Quick Start

### Ralph

```bash
npm i -g @iannuttall/ralph
ralph prd  # Generate PRD
ralph build 1  # Run one iteration
```

### SkillForge

```bash
cp -r SkillForge ~/.claude/skills/
# Then use: SkillForge: {goal}
```

### Claude Marketplace

```bash
claude plugin install ~/projects/qute-ai-tools/claude-marketplace
# Or from GitHub:
claude plugin install github:twilc/claude-marketplace
```

### Claude Skills

Reference in your project's `CLAUDE.md`:

```markdown
## Skills
- Use skills in `claude-skills/my/` for development workflows
- Use `claude-skills/external/scientific-skills/` for quantitative analysis
- ALWAYS use generating-commit-messages skill before any commit
```

## Directory Structure

```
qute-ai-tools/
├── ralph/                    # File-based agent loop
├── SkillForge/               # Skill creation methodology
├── claude-marketplace/       # Claude Code plugin marketplace
│   ├── plugins/             # All plugins
│   ├── scripts/             # Management scripts
│   └── templates/           # Plugin templates
├── claude-skills/           # Claude Code skills
│   ├── my/                  # Custom skills
│   └── external/            # Third-party skills
└── claude-agents/           # Claude Code agents
    ├── my/                  # Custom agents
    └── external/            # Third-party agents
```

## Resources

- [EveryInc/compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) - Official Claude Code compound engineering plugin

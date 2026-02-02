# qute-code-kit

A collection of AI tools and utilities for autonomous coding, skill creation, and Claude Code integration.

## What's in this repo
- **Setup Script** (`setup-project.sh`): Bootstrap Claude Code projects with skills, agents, rules, and configs
- Ralph (`repos/ralph/README.md`): file-based agent loop for autonomous coding
- SkillForge (`repos/SkillForge/README.md`): 4-phase methodology for skill creation
- Claude Marketplace (`claude-marketplace/README.md`): personal Claude Code plugin marketplace
- Claude Skills (`claude/skills/README.md`): custom and external skills for Claude Code
- Claude Agents (`claude/agents/`): custom and external agent definitions
- Clawdbot (`clawdbot/`): auxiliary tools and skills for booking analysis
- Project Templates (`project-templates/`): starter templates and guidance
- Prompts (`prompts/`): prompt references and templates
- Resources (`resources/README.md`): external references and experiments
- Root Instructions (`CLAUDE.md`): repo-specific guidance for Claude Code

## Quick Start

### Setup a New Project

```bash
# Full quant/ML project with standard directories
./setup-project.sh ~/projects/new-fund --bundle quant --init

# Web development project
./setup-project.sh ~/projects/my-app --bundle webdev --init

# Minimal setup (rules + essential skills only)
./setup-project.sh ~/projects/quick-start --bundle minimal

# Preview what would be installed
./setup-project.sh ~/projects/test --bundle quant --diff
```

### Add Individual Components

```bash
# Add a single skill
./setup-project.sh ~/projects/app --add my:paper-reading

# Add a skill sub-bundle
./setup-project.sh ~/projects/app --add @skills/visualization

# Add multiple components
./setup-project.sh ~/projects/app --add my:sql-patterns --add my:gist-report

# Update existing project (overwrite)
./setup-project.sh ~/projects/app --update --bundle quant
```

### Browse Available Components

```bash
# List all skills, agents, commands, hooks, settings
./setup-project.sh --list

# List bundles and their contents
./setup-project.sh --list-bundles
```

### Bundles

| Bundle | Contents | Use For |
|--------|----------|---------|
| `minimal` | Rules, CLAUDE.md, AGENTS.md, commit messages, worktrees | Any project |
| `quant` | minimal + ML skills, scientific skills, MLflow, paper reading, gist skills | Data science, ML, quant |
| `webdev` | minimal + frontend agents, web settings, gist skills | Web apps, frontend |

Skill sub-bundles (use with `--add @skills/<name>`):

| Sub-bundle | Skills |
|------------|--------|
| `ml-core` | scikit-learn, shap, pytorch-lightning, aeon, EDA |
| `statistics` | statsmodels, pymc, scikit-survival, statistical-analysis |
| `visualization` | matplotlib, seaborn, plotly, networkx, umap-learn |
| `research-tools` | openalex, perplexity-search, literature-review, citations |
| `data-processing` | polars, dask, vaex |

### Plugins

| Plugin | Marketplace | global | quant | webdev |
|--------|-------------|:-:|:-:|:-:|
| context7 | claude-plugins-official | x | | |
| github | claude-plugins-official | x | | |
| commit-commands | claude-plugins-official | x | | |
| hookify | claude-plugins-official | x | | |
| code-simplifier | claude-plugins-official | x | | |
| pyright-lsp | claude-plugins-official | | x | |
| feature-dev | claude-plugins-official | | x | x |
| frontend-design | claude-plugins-official | | | x |
| agent-sdk-dev | claude-plugins-official | | | x |
| plugin-dev | claude-plugins-official | | | x |
| forced-eval | qute-marketplace | | x | x |
| llm-council | qute-marketplace | | x | |
| llm-external-review | qute-marketplace | | x | |
| datasets-guide | qute-marketplace | | x | |
| notifications | qute-marketplace | x | | |
| context-management | qute-marketplace | x | | |
| documentation-guide | qute-marketplace | x | | |
| compound-engineering | every-marketplace | | x | x |
| document-skills | anthropic-agent-skills | x | | |
| example-skills | anthropic-agent-skills | x | | |

### MCP Servers

| Server | Package | Bundle | Auth Required |
|--------|---------|--------|:---:|
| fetch | @anthropic/mcp-fetch | minimal | |
| sequential-thinking | @anthropic/mcp-sequential-thinking | minimal | |
| memory | @anthropic/mcp-memory | minimal | |
| firecrawl | firecrawl-mcp | quant | FIRECRAWL_API_KEY |
| postgres | @anthropic/mcp-postgres | quant | POSTGRES_CONNECTION_STRING |
| brave-search | @anthropic/mcp-brave-search | global | BRAVE_API_KEY |
| vercel | mcp.vercel.com (HTTP) | webdev | |
| chrome-devtools | [chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp) | webdev | |
| playwright | @anthropic/mcp-playwright | webdev | |
| docker | @anthropic/mcp-docker | webdev | |
| figma | @anthropic/mcp-figma | webdev | FIGMA_ACCESS_TOKEN |

### Skills

> **Note:** Slash commands and skills are now unified in Claude Code. Skills support invocation controls (`disable-model-invocation`, `user-invocable`), subagent delegation (`agent`), and context forking (`context: fork`). See `CLAUDE.md` for details.

| Skill | Bundles | Notes |
|-------|---------|-------|
| generating-commit-messages | minimal, quant, webdev | Mandatory for commits |
| worktrees | minimal, quant, webdev | Git worktree management |
| context-management | quant, webdev | Token budget management; `user-invocable: false` |
| paper-reading | quant | Research paper analysis; `agent: Explore` |
| sql-patterns | quant | SQL query patterns |
| market-data-fetcher | quant | Multi-source market data |
| qrd | quant | Quant R&D specs |
| gist-report | quant, webdev | Shareable HTML reports via gist; `disable-model-invocation: true` |
| gist-transcript | quant, webdev | Session transcript gist; `disable-model-invocation: true` |
| readme | -- | README generation; `context: fork` |
| pdf-skill | webdev | PDF extraction |
| garmin-skill | -- | Standalone (not in any bundle) |
| brand-dm-evo | -- | Project-specific |
| brand-rockbridge | -- | Project-specific |
| analizy-pl-data | -- | Polish fund data from analizy.pl |

#### External Skills

| Skill | Sub-bundle | Bundles |
|-------|------------|---------|
| scikit-learn | @skills/ml-core | quant |
| shap | @skills/ml-core | quant |
| pytorch-lightning | @skills/ml-core | quant |
| aeon | @skills/ml-core | quant |
| exploratory-data-analysis | @skills/ml-core | quant |
| statsmodels | @skills/statistics | quant |
| pymc | @skills/statistics | quant |
| scikit-survival | @skills/statistics | quant |
| statistical-analysis | @skills/statistics | quant |
| matplotlib | @skills/visualization | -- |
| seaborn | @skills/visualization | -- |
| plotly | @skills/visualization | -- |
| networkx | @skills/visualization | -- |
| scientific-visualization | @skills/visualization | -- |
| umap-learn | @skills/visualization | -- |
| openalex-database | @skills/research-tools | -- |
| perplexity-search | @skills/research-tools | -- |
| literature-review | @skills/research-tools | -- |
| citation-management | @skills/research-tools | -- |
| polars | @skills/data-processing | -- |
| dask | @skills/data-processing | -- |
| vaex | @skills/data-processing | -- |
| transformers | -- | -- |
| torch_geometric | -- | -- |
| sympy | -- | -- |
| simpy | -- | -- |
| pymoo | -- | -- |
| context7 | -- | -- |
| dignified-python-313 | -- | -- |
| nano-banana-pro | -- | -- |

### Other Tools

#### Ralph
```bash
npm i -g @iannuttall/ralph
ralph prd
ralph build 1
```

#### SkillForge
```bash
cp -r repos/SkillForge ~/.claude/skills/
# Then use: SkillForge: {goal}
```

#### Claude Marketplace
```bash
claude plugin install ~/projects/qute-code-kit/claude-marketplace
# Or from GitHub:
claude plugin install github:twilc/claude-marketplace
```

## Directory Map
```
qute-code-kit/
├── setup-project.sh           # Project setup script
├── setup-project.bat          # Windows wrapper (WSL)
├── CLAUDE.md                  # Repo-wide Claude guidance
├── claude/                    # ALL Claude source components
│   ├── skills/                #   my/ + external/
│   ├── agents/                #   my/ + external/
│   ├── commands/              #   Legacy slash commands (prefer skills)
│   ├── settings/              #   Settings profiles
│   ├── hooks/                 #   Reusable hooks
│   ├── mcp/                   #   MCP server configs
│   ├── bundles/               #   Bundle manifests
│   ├── rules/                 #   Rule templates (code-quality, general, python, work-org)
│   └── root-files/            #   CLAUDE.md, AGENTS.md templates
├── templates/                 # Non-Claude project scaffolding
│   ├── pyproject/             #   python-uv, quant-uv, webdev-uv
│   └── .gitignore.claude
├── project-templates/         # GENERATED example outputs
│   ├── archive-quant/         #   Legacy reference
│   ├── minimal/               #   setup-project.sh --bundle minimal
│   ├── quant/                 #   setup-project.sh --bundle quant
│   └── webdev/                #   setup-project.sh --bundle webdev
├── claude-marketplace/        # Claude Code plugin marketplace
├── clawdbot/                  # Clawdbot tools and skills
├── repos/                     # Subprojects (Ralph, SkillForge)
├── resources/                 # External links and experiments
└── prompts/                   # Prompt references
```

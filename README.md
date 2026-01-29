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
./setup-project.sh ~/projects/app --add my:sql-patterns --add commands/gist-report.md

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
| `quant` | minimal + ML skills, scientific skills, MLflow, paper reading | Data science, ML, quant |
| `webdev` | minimal + frontend agents, web settings | Web apps, frontend |

Skill sub-bundles (use with `--add @skills/<name>`):

| Sub-bundle | Skills |
|------------|--------|
| `ml-core` | scikit-learn, shap, pytorch-lightning, aeon, EDA |
| `statistics` | statsmodels, pymc, scikit-survival, statistical-analysis |
| `visualization` | matplotlib, seaborn, plotly, networkx, umap-learn |
| `research-tools` | openalex, perplexity-search, literature-review, citations |
| `data-processing` | polars, dask, vaex |

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
│   ├── commands/              #   Slash commands
│   ├── settings/              #   Settings profiles
│   ├── hooks/                 #   Reusable hooks
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

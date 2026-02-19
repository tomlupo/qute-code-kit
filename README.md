# qute-code-kit

Curated skills, agents, rules, and plugins for Claude Code. Three deployment profiles: **minimal** (any project), **quant** (data science/ML), **webdev** (frontend).

## Quick Start

### 1. Install a plugin

Plugins provide skills and agents. Pick your profile:

```bash
# Register the marketplace
claude plugin marketplace add tomlupo/qute-code-kit

# Install one
claude plugin install qute-minimal@qute-marketplace   # commit msgs, worktrees, readme, external review
claude plugin install qute-quant@qute-marketplace      # + 17 quant/ML skills, 3 agents, hooks
claude plugin install qute-webdev@qute-marketplace     # + PDF, 5 webdev agents
```

### 2. Copy rules to your project

Rules deploy separately (plugins can't install rules):

```bash
./scripts/copy-rules.sh ~/projects/my-app                    # minimal rules
./scripts/copy-rules.sh ~/projects/my-app --preset quant     # + python rules, datasets
./scripts/copy-rules.sh ~/projects/my-app --preset webdev    # + coding standards
```

### 3. Optional: install utility plugins

```bash
# Hook-based (run automatically in background)
claude plugin install forced-eval@qute-marketplace         # skill evaluation before coding
claude plugin install strategic-compact@qute-marketplace   # context compaction reminders
claude plugin install doc-enforcer@qute-marketplace        # doc update reminders
claude plugin install ruff-formatter@qute-marketplace      # auto-format Python on save

# Session management
claude plugin install session-persistence@qute-marketplace # save/restore sessions
claude plugin install notifications@qute-marketplace       # push notifications via ntfy.sh
claude plugin install adaptive-learning@qute-marketplace   # learn behavioral patterns
```

### 4. Optional: external plugins

```bash
python scripts/setup-externals.py        # fetch external plugins from manifest
python scripts/setup-externals.py --update   # update existing
```

## Documentation

| Doc | What it covers |
|-----|---------------|
| [Setup Guide](docs/setup.md) | Installation, bundles, work modes, configuration |
| [Workflows](docs/workflows.md) | Use cases: development, research, quant pipeline, code review |
| [Reference](docs/reference.md) | Complete inventory of skills, agents, plugins, MCP servers |
| [Tips & Troubleshooting](docs/tips.md) | Context management, headless mode, common issues |

## Directory Map

```
qute-code-kit/
├── claude/                    # Source components
│   ├── skills/my/             #   Custom skills (18)
│   ├── skills/external/       #   Curated external skills (12)
│   ├── agents/my/             #   Custom agents (4)
│   ├── agents/external/       #   External agents (6)
│   ├── rules/                 #   Rule templates
│   ├── bundles/               #   Bundle manifests
│   ├── settings/              #   Settings profiles
│   ├── hooks/                 #   Reusable hooks
│   ├── mcp/                   #   MCP server configs
│   └── root-files/            #   CLAUDE.md, AGENTS.md templates
├── plugins/                   # Installable plugins (marketplace source)
│   ├── qute-minimal/          #   Essential skills
│   ├── qute-quant/            #   Quant/ML skills + agents
│   └── qute-webdev/           #   Webdev skills + agents
├── scripts/                   # Tooling
│   ├── copy-rules.sh          #   Deploy rules to projects
│   ├── setup-project.sh       #   Bundle deployment (legacy)
│   └── build-marketplace.py   #   Plugin manifest builder
├── docs/                      # Documentation
├── project-templates/         # Generated example outputs
├── templates/                 # Non-Claude scaffolding
└── resources/                 # External references
```

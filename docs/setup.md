# Setup Guide

## Installation Options

### Option A: Plugins (recommended)

Plugins install skills and agents globally. Pick your profile:

```bash
claude plugin marketplace add tomlupo/qute-code-kit
claude plugin install qute-quant@qute-marketplace
```

Then copy rules to each project:

```bash
./scripts/copy-rules.sh ~/project --preset quant
```

### Option B: Bundles (legacy)

Bundles deploy everything (skills, agents, rules, MCP configs, settings) to a single project:

```bash
./setup-project.sh ~/project --bundle quant --init
```

| Bundle | Contents | Use for |
|--------|----------|---------|
| `minimal` | 5 rules, CLAUDE.md, AGENTS.md, 4 skills | Any project |
| `quant` | minimal + python rules, 17 ML/quant skills, 3 agents, MCP configs | Data science, ML, quant |
| `webdev` | minimal + coding standards, 4 skills, 5 agents, MCP configs | Web apps, frontend |

Bundle commands:

```bash
./setup-project.sh ~/project --bundle quant --init      # first-time setup with directories
./setup-project.sh ~/project --bundle quant --update     # update existing project
./setup-project.sh ~/project --bundle quant --diff       # preview changes
./setup-project.sh ~/project --add my:paper-reading      # add single component
./setup-project.sh ~/project --add @skills/visualization # add sub-bundle
./setup-project.sh --list                                # list available components
./setup-project.sh --list-bundles                        # list bundles and contents
```

## Work Modes

Set up CLI aliases to inject behavioral context:

```bash
# Add to ~/.bashrc or ~/.zshrc
alias claude-dev='claude --context ~/.claude/contexts/dev.md'
alias claude-research='claude --context ~/.claude/contexts/research.md'
alias claude-review='claude --context ~/.claude/contexts/review.md'
```

Create context files:

```bash
mkdir -p ~/.claude/contexts

cat > ~/.claude/contexts/dev.md << 'EOF'
# Development Mode
Prioritize working code over explanation. Write tests. Make atomic commits.
When in doubt, ship something working and iterate.
EOF

cat > ~/.claude/contexts/research.md << 'EOF'
# Research Mode
Read widely before concluding. Document sources and findings.
No code until requirements are crystal clear.
EOF

cat > ~/.claude/contexts/review.md << 'EOF'
# Review Mode
Read thoroughly before commenting. Prioritize issues by severity.
Check for security vulnerabilities. Be constructive.
EOF
```

| Mode | Alias | Behavior |
|------|-------|----------|
| Development | `claude-dev` | Code first, explain after. Tests, atomic commits. |
| Research | `claude-research` | Read widely, document findings. No code until clear. |
| Review | `claude-review` | Thorough reading, severity-based feedback, security checks. |

## Utility Plugins

Install separately from profile plugins. All are optional:

| Plugin | Type | What it does |
|--------|------|-------------|
| `forced-eval` | Hook | Evaluates skills/agents before every implementation (~50% → ~84% skill activation) |
| `strategic-compact` | Hook | Suggests `/compact` at 50 tool calls, then every 25 |
| `doc-enforcer` | Hook | Reminds when 3+ code files edited without doc updates |
| `ruff-formatter` | Hook | Auto-formats Python with ruff after edits |
| `skill-use-logger` | Hook | Logs skill invocations to `.claude/skill-use-log.jsonl` |
| `session-persistence` | Hook + Command | Auto-saves sessions, `/session-persistence:load` to restore |
| `notifications` | Hook + Command | Push notifications via ntfy.sh for long tasks |
| `adaptive-learning` | Hook + Command | Observes tool patterns, learns instincts, surfaces at session start |

## External Plugins

Third-party plugins tracked in `external-plugins.json`:

```bash
python scripts/setup-externals.py              # fetch all from manifest
python scripts/setup-externals.py --update     # update existing
python scripts/fetch-external.py github:user/repo  # add new one
python scripts/build-marketplace.py            # rebuild marketplace
```

| Plugin | Source | Description |
|--------|--------|-------------|
| compound-engineering | every-marketplace | Full dev lifecycle with knowledge compounding |
| superpowers | claude-plugins-official | Structured planning, TDD, debugging, code review |
| context7 | claude-plugins-official | Live framework docs (100+ frameworks) |

## Kit Development

```bash
# Create a new plugin
python scripts/create-plugin.py my-plugin

# Rebuild marketplace after plugin changes
python scripts/build-marketplace.py

# Regenerate project templates after component changes
./setup-project.sh project-templates/minimal --bundle minimal --update
./setup-project.sh project-templates/quant --bundle quant --update
./setup-project.sh project-templates/webdev --bundle webdev --update
```

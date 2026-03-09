# Setup Guide

## 1. Global Setup (once per machine)

### Add marketplaces

```bash
claude plugin marketplace add tomlupo/qute-code-kit
claude plugin marketplace add anthropics/claude-code-plugins
claude plugin marketplace add anthropics/example-agent-skills
claude plugin marketplace add every-ai-dev/compound-engineering
```

### Install plugins

```bash
# Essential hooks + universal skills (ruff, doc-enforcer, skill-eval, commits, worktrees, handoff, readme)
claude plugin install qute-essentials@qute-marketplace

# Recommended third-party
claude plugin install context7@claude-plugins-official
claude plugin install superpowers@claude-plugins-official
claude plugin install compound-engineering@every-marketplace
```

### Copy global settings

```bash
cp claude/settings/global-generic.json ~/.claude/settings.json
```

Edit to taste — this sets up tool permissions and plugin references.

## 2. Set Up a Project

### Option A: Script (recommended)

```bash
./scripts/setup-project.sh ~/project --bundle quant --init
```

This copies rules, skills, agents, MCP configs, settings, and root files to the target project.

| Bundle | What you get |
|--------|-------------|
| `minimal` | 4 rules, CLAUDE.md, AGENTS.md |
| `quant` | minimal + python/data rules, 14 skills, MCP (firecrawl, postgres), pyproject |
| `webdev` | minimal + typescript rules, 2 skills, MCP (vercel, playwright, docker, figma, chrome-devtools), pyproject |

Common commands:

```bash
./scripts/setup-project.sh ~/project --bundle quant --update    # update existing project
./scripts/setup-project.sh ~/project --bundle quant --diff      # preview changes
./scripts/setup-project.sh ~/project --add paper-reading        # add single component
./scripts/setup-project.sh --list                               # list available components
./scripts/setup-project.sh --list-bundles                       # list bundles and contents
```

### Option B: Manual

Copy what you need from `claude/` to your project's `.claude/`:

```bash
cp claude/rules/general-rules.md ~/project/.claude/rules/
cp -r claude/skills/paper-reading ~/project/.claude/skills/
cp claude/agents/research-synthesizer.md ~/project/.claude/agents/
```

## 3. Verify

In your project directory:

```bash
claude
# Then run: /check-setup
```

This audits your project against the kit and reports missing or outdated components.

## 4. Browse Documentation

| Doc | Purpose |
|-----|---------|
| `docs/reference.md` | Complete inventory of all components |
| `docs/cheatsheets/toolkit-reference.md` | Quick-reference card |
| `docs/playbooks/*.md` | End-to-end workflow guides |
| `docs/tips.md` | Practical usage tips |

# Getting Started

## Flow 1: Global Setup (one-time)

Install plugins and set up your user-level settings. This applies to all projects.

### 1a. Add marketplaces

```bash
claude plugin marketplace add tomlupo/qute-code-kit        # qute-marketplace
claude plugin marketplace add anthropics/claude-code-skills # anthropic-agent-skills
claude plugin marketplace add nichochar/compound-engineering # every-marketplace
```

### 1b. Install plugins

```bash
# Kit hooks + universal skills
claude plugin install qute-essentials@qute-marketplace

# Recommended plugins
claude plugin install context7@claude-plugins-official
claude plugin install superpowers@claude-plugins-official
claude plugin install compound-engineering@every-marketplace
claude plugin install commit-commands@claude-plugins-official
claude plugin install document-skills@anthropic-agent-skills
claude plugin install hookify@claude-plugins-official
claude plugin install code-review@claude-plugins-official
claude plugin install playground@claude-plugins-official
claude plugin install claude-md-management@claude-plugins-official
claude plugin install github@claude-plugins-official
claude plugin install code-simplifier@claude-plugins-official
claude plugin install claude-code-setup@claude-plugins-official
```

### 1c. User settings (optional)

Copy the global settings template to get the right plugin list:

```bash
cp claude/settings/global-generic.json ~/.claude/settings.json
```

Or just let Claude Code auto-detect your installed plugins.

### 1d. Verify

```bash
/check-setup user    # from within the kit repo
```

---

## Flow 2: Set Up a Project

Copy the components you need from the kit to your project.

### Option A: Manual copy (recommended)

Pick what you need:

```bash
# Rules (always start with these)
mkdir -p ~/project/.claude/rules
cp claude/rules/general-rules.md ~/project/.claude/rules/
cp claude/rules/work-organization.md ~/project/.claude/rules/
cp claude/rules/context-management.md ~/project/.claude/rules/
cp claude/rules/documentation.md ~/project/.claude/rules/

# Root files
cp claude/root-files/CLAUDE.md ~/project/CLAUDE.md
cp claude/root-files/AGENTS.md ~/project/AGENTS.md

# Python rules (for Python projects)
cp claude/rules/python-rules.md ~/project/.claude/rules/
cp claude/rules/datasets.md ~/project/.claude/rules/

# Skills (copy any you want)
cp -r claude/skills/paper-reading ~/project/.claude/skills/
cp -r claude/skills/sql-patterns ~/project/.claude/skills/

# MCP configs
mkdir -p ~/project/.mcp/firecrawl
cp claude/mcp/firecrawl.json ~/project/.mcp/firecrawl/.mcp.json

# Project settings (permissions template)
cp claude/settings/project-quant.json ~/project/.claude/settings.json
```

### Option B: Bundle script (bootstrap)

Installs everything from a bundle at once:

```bash
# New project
./scripts/setup-project.sh ~/project --bundle quant --init

# Update existing project
./scripts/setup-project.sh ~/project --bundle quant --update

# Add a single component
./scripts/setup-project.sh ~/project --add paper-reading

# Preview what would change
./scripts/setup-project.sh ~/project --bundle quant --diff
```

---

## Flow 3: Audit Your Setup

Check if a project's components are up to date with the kit.

```bash
# Audit a project against its bundle
/check-setup ~/project

# Audit with explicit bundle
/check-setup ~/project quant

# Audit global plugin settings
/check-setup user
```

---

## Flow 4: Browse Documentation

```bash
docs/
├── cheatsheets/           # Quick lookups
│   ├── toolkit-reference.md   # Full inventory of skills, agents, MCP, rules
│   ├── claude-cli.md          # CLI flags and usage
│   ├── prompt-engineering.md  # Prompting patterns
│   └── xml-prompting.md       # XML tag patterns
├── playbooks/             # Step-by-step workflows
├── prompts/               # Copy-paste prompts
└── resources.md           # External tools and links
```

---

## What Goes Where

| Scope | What | Where | How |
|-------|------|-------|-----|
| **Global** | Plugins (hooks, universal skills) | `~/.claude/` | `claude plugin install` |
| **Global** | Plugin settings | `~/.claude/settings.json` | Copy from `claude/settings/global-generic.json` |
| **Project** | Rules, skills, agents | `~/project/.claude/` | Manual copy or `setup-project.sh` |
| **Project** | MCP configs | `~/project/.mcp/` | Manual copy or `setup-project.sh` |
| **Project** | Permissions | `~/project/.claude/settings.json` | Copy from `claude/settings/project-*.json` |
| **Project** | Root files | `~/project/CLAUDE.md`, `AGENTS.md` | Manual copy |

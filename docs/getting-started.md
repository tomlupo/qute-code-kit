# Getting Started

## 1. Install plugins (global, one-time)

```bash
# Marketplaces
claude plugin marketplace add tomlupo/qute-code-kit
claude plugin marketplace add anthropics/claude-code-skills
claude plugin marketplace add nichochar/compound-engineering

# Essential plugins
claude plugin install qute-essentials@qute-marketplace
claude plugin install context7@claude-plugins-official
claude plugin install superpowers@claude-plugins-official
claude plugin install compound-engineering@every-marketplace
claude plugin install commit-commands@claude-plugins-official
claude plugin install document-skills@anthropic-agent-skills
claude plugin install hookify@claude-plugins-official
claude plugin install code-review@claude-plugins-official
claude plugin install playground@claude-plugins-official
claude plugin install claude-md-management@claude-plugins-official
```

## 2. Set up a project

**Option A: Manual copy** (most common)

```bash
# Copy rules you need
cp claude/rules/general-rules.md ~/project/.claude/rules/
cp claude/rules/python-rules.md ~/project/.claude/rules/

# Copy root files
cp claude/root-files/CLAUDE.md ~/project/CLAUDE.md
cp claude/root-files/AGENTS.md ~/project/AGENTS.md

# Copy skills you want
cp -r claude/skills/paper-reading ~/project/.claude/skills/

# Copy MCP configs
mkdir -p ~/project/.mcp/firecrawl
cp claude/mcp/firecrawl.json ~/project/.mcp/firecrawl/.mcp.json
```

**Option B: Bundle script** (bootstrap)

```bash
./setup-project.sh ~/project --bundle quant --init
```

## 3. Audit your setup

From within the kit repo:

```
/check-setup ~/project
/check-setup user          # audit global plugin settings
```

## Next Steps

- [Toolkit Reference](cheatsheets/toolkit-reference.md) — what's available
- [Bundles Explained](bundles-explained.md) — how bundles work
- [Plugins Explained](plugins-explained.md) — how plugins work
- [Playbooks](playbooks/) — step-by-step workflows

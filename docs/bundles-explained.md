# Understanding Bundles

Bundles define which rules, MCP configs, and settings to deploy to a project. Universal skills are installed via the `qute-essentials` plugin instead.

## What bundles include

- **Rules**: Path-scoped coding guidelines (auto-loaded by file type)
- **MCP configs**: External service integrations
- **Settings**: Project-specific configurations
- **Root files**: CLAUDE.md, AGENTS.md templates

## Available bundles

| Bundle | Rules | MCP Servers | Use for |
|--------|-------|-------------|---------|
| `minimal` | general, work-org, context-mgmt, docs | — | Any project |
| `quant` | minimal + python, datasets | firecrawl, postgres | Data science, ML |
| `webdev` | minimal + typescript | vercel, playwright, chrome-devtools, docker, figma | Web apps |

## Using bundles

```bash
# Bootstrap a new project
./setup-project.sh ~/myproject --bundle quant --init

# Preview changes
./setup-project.sh ~/myproject --bundle quant --diff

# Audit a project against bundle
/check-setup ~/myproject
```

## Manual copy (preferred)

Most users just copy what they need:

```bash
cp claude/rules/python-rules.md ~/myproject/.claude/rules/
cp -r claude/mcp/firecrawl.json ~/myproject/.mcp/firecrawl/.mcp.json
```

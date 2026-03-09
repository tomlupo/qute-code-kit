# Understanding Bundles

Bundles group related components for deployment to projects. Each bundle is a text file listing which rules, skills, MCP configs, and settings belong together.

## What bundles include

- **Rules**: Path-scoped coding guidelines (auto-loaded by file type)
- **Skills**: Domain knowledge and workflows
- **MCP configs**: External service integrations
- **Settings**: Project-specific permission templates
- **Root files**: CLAUDE.md, AGENTS.md templates

## Available bundles

| Bundle | Rules | Skills | MCP Servers | Use for |
|--------|-------|--------|-------------|---------|
| `minimal` | general, work-org, context-mgmt, docs | — | — | Any project |
| `quant` | minimal + python, datasets | 14 domain skills | firecrawl, postgres | Data science, ML |
| `webdev` | minimal + typescript | gist-report, gist-transcript | vercel, playwright, chrome-devtools, docker, figma | Web apps |

## Using bundles

### Manual copy (preferred)

Most users just copy what they need:

```bash
# Rules
cp claude/rules/general-rules.md ~/myproject/.claude/rules/
cp claude/rules/python-rules.md ~/myproject/.claude/rules/

# Skills
cp -r claude/skills/paper-reading ~/myproject/.claude/skills/

# MCP
mkdir -p ~/myproject/.mcp/firecrawl
cp claude/mcp/firecrawl.json ~/myproject/.mcp/firecrawl/.mcp.json

# Settings
cp claude/settings/project-quant.json ~/myproject/.claude/settings.json
```

### Script (bootstrap or sync)

```bash
# Bootstrap a new project
./scripts/setup-project.sh ~/myproject --bundle quant --init

# Update existing project
./scripts/setup-project.sh ~/myproject --bundle quant --update

# Add a single component
./scripts/setup-project.sh ~/myproject --add paper-reading

# Preview changes
./scripts/setup-project.sh ~/myproject --bundle quant --diff
```

### Audit a project against bundle

```bash
/check-setup ~/myproject
/check-setup ~/myproject quant
```

## Bundle format

Bundle files live in `claude/bundles/`. One component ref per line, `#` for comments, `@name` to inherit another bundle.

```
# Example: quant.txt
@minimal                      # inherit all minimal components
settings/project-quant.json
pyproject/quant-uv.toml
rules/python-rules.md
paper-reading                 # skill (bare name)
mcp:firecrawl                 # MCP server
```

# Understanding Bundles

Bundles are collections of Claude Code components deployed to projects.

## What bundles include

- **Skills**: Domain knowledge and workflows
- **Agents**: Specialized subagents for delegation
- **Rules**: Always-loaded guidelines
- **MCP configs**: External service integrations
- **Settings**: Project-specific configurations

## Using bundles

```bash
# Deploy a bundle to a new project
./setup-project.sh ~/myproject --bundle quant

# Update an existing project
./setup-project.sh ~/myproject --bundle quant --update

# Preview changes without applying
./setup-project.sh ~/myproject --bundle quant --diff
```

## Creating custom bundles

See `claude/bundles/` for bundle definitions.

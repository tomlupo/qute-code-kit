# Getting Started

qute-code-kit is a comprehensive Claude Code toolkit with:

- **Bundles**: Deploy skills, agents, rules, and MCP configs to projects
- **Plugins**: Runtime hooks and commands installed globally
- **Documentation**: Guides and tutorials for workflows

## Quick Start

### Install as a plugin (global)

```bash
claude plugin install github:tomlupo/qute-code-kit
```

### Deploy to a project (bundle)

```bash
./setup-project.sh ~/myproject --bundle minimal
```

### Available bundles

- `minimal` - Core skills and rules
- `quant` - Data science and ML workflows
- `webdev` - Frontend development

## Next Steps

- [Understanding Bundles](bundles-explained.md)
- [Understanding Plugins](plugins-explained.md)
- [Planning Workflows Comparison](workflows/planning-workflows-comparison.md)

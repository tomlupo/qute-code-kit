# Understanding Plugins

Plugins provide runtime hooks and commands that work across all projects.

## What plugins include

- **Hooks**: Lifecycle events (session start, tool use, etc.)
- **Commands**: Slash commands like `/plugin:command`
- **Skills**: Domain knowledge loaded on demand

## Installing plugins

See `docs/cheatsheets/toolkit-reference.md` for the full install list.

```bash
# Add the marketplace
claude plugin marketplace add tomlupo/qute-code-kit

# Install the essentials plugin
claude plugin install qute-essentials@qute-marketplace
```

## qute-essentials plugin

Merges all kit hooks and universal skills into one install:

**Hooks:** forced-eval, ruff-formatter, doc-enforcer, skill-use-logger, notifications

**Skills:** generating-commit-messages, worktrees, handoff, readme

## Creating plugins

```bash
python scripts/create-plugin.py my-plugin
```

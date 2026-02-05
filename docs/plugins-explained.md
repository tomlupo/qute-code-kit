# Understanding Plugins

Plugins provide runtime hooks and commands that work across all projects.

## What plugins include

- **Hooks**: Lifecycle events (session start, tool use, etc.)
- **Commands**: Slash commands like `/plugin:command`
- **Skills**: Domain knowledge loaded on demand
- **Rules**: Always-active guidelines

## Installing plugins

```bash
# Install the full marketplace
claude plugin install github:tomlupo/qute-code-kit

# Individual plugins are available via the marketplace
```

## Available plugins

| Plugin | Description |
|--------|-------------|
| doc-enforcer | Reminds when code changes need doc updates |
| forced-eval | Forces skill/tool evaluation before implementation |
| strategic-compact | Suggests /compact at token thresholds |
| notifications | Push notifications via ntfy.sh |
| session-persistence | Save/restore session state |
| skill-use-logger | Logs skill invocations |
| research-workflow | ML/DS research lifecycle |

## Creating plugins

```bash
python scripts/create-plugin.py my-plugin
```

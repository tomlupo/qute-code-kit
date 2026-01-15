# Forced Eval Plugin

Forces Claude to explicitly evaluate Skills, MCP Tools, and Agents before implementation.

## Why This Exists

Based on [Scott Spence's research](https://scottspence.com/posts/how-to-make-claude-code-skills-activate-reliably), Claude Code skills (and by extension, MCP tools and agents) fail to activate autonomously ~50% of the time. The "forced evaluation" pattern achieves **84% activation rate** by creating a commitment mechanism.

## How It Works

On every user prompt, this hook injects instructions requiring Claude to:

1. **EVALUATE** - Explicitly state YES/NO for each category (Skills, MCP, Agents)
2. **ACTIVATE** - Call tools marked YES before proceeding
3. **IMPLEMENT** - Only then proceed with the actual task

The key insight: making Claude verbalize its evaluation creates accountability that prevents skipping tools.

## What Gets Evaluated

| Category | Tool | When to Use |
|----------|------|-------------|
| **Skills** | `Skill(name)` | Task-specific workflows (commit, pdf, xlsx) |
| **MCP Tools** | `mcp__*` functions | External integrations (Context7 for docs) |
| **Agents** | `Task(subagent_type=...)` | Specialized work (Explore, code-reviewer) |

## Installation

### Via Marketplace (Recommended)

Already included when you install the claude-marketplace plugin.

### Standalone

```bash
# Copy hook to your project
cp scripts/forced_eval.sh ~/.claude/hooks/

# Register in ~/.claude/settings.json
{
  "hooks": {
    "UserPromptSubmit": [
      { "command": "sh ~/.claude/hooks/forced_eval.sh" }
    ]
  }
}
```

## Customization

Edit `scripts/forced_eval.sh` to:
- Add project-specific skill hints
- Remove categories you don't use
- Adjust the output format

## Performance

- Shell script: ~5ms execution time
- Runs on every prompt (acceptable overhead)

## License

MIT

---
name: guard-toggle
description: Toggle Lakera Guard (prompt injection screening) and Langfuse (tracing/eval) on or off. Use when asked to enable/disable guards, check guard status, or manage security hooks.
argument-hint: "[status|lakera on|lakera off|langfuse on|langfuse off|all on|all off]"
---

# /guard — Toggle Security Guards

Manage the Lakera Guard and Langfuse hooks.

## Usage

- `/guard` or `/guard status` — show current status
- `/guard lakera on` or `/guard lakera off` — toggle Lakera prompt injection screening
- `/guard langfuse on` or `/guard langfuse off` — toggle Langfuse tracing
- `/guard all on` or `/guard all off` — toggle both

## Instructions

Read the guards config file and apply the requested change:

```bash
cat ~/.claude/plugins/cache/qute-marketplace/qute-essentials/1.1.2/config/guards.json
```

**For status:** Show a table with each guard's name, enabled/disabled state, and whether its API key is configured (check the env var).

**For toggle:** Use python3 to update the JSON file:

```bash
python3 -c "
import json
config = json.load(open('$HOME/.claude/plugins/cache/qute-marketplace/qute-essentials/1.1.2/config/guards.json'))
config['GUARD_NAME']['enabled'] = BOOL_VALUE
json.dump(config, open('$HOME/.claude/plugins/cache/qute-marketplace/qute-essentials/1.1.2/config/guards.json', 'w'), indent=2)
print('Done')
"
```

Replace GUARD_NAME and BOOL_VALUE with the actual values.

After toggling, show the updated status table. Changes take effect immediately (hooks check the config on each invocation).

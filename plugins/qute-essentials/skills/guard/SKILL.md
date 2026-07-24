---
name: guard
description: Toggle qute-essentials security guards (lakera, langfuse, secrets, audit, destructive, provenance) or show status. Triggers — "guards on/off", "turn off lakera", "disable langfuse", "is X enabled", "guard status".
argument-hint: "[status | <name> <on|off> | all <on|off>]"
---

# /guard

Run the helper and print stdout verbatim:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/guard_toggle.py" $@
```

Pass through the user's args verbatim. The script handles config
resolution, state mutation, the status table, and edge cases.

For specific questions ("what does X actually block?", "why is
destructive sometimes a false positive?", "what env var skips a
single guard?"), invoke:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/guard_toggle.py" --help
```

…rather than answering from memory. The script's `--help` output is
the authoritative documentation — guard semantics, gotchas, env-var
overrides, and config-file resolution all live there. Reading it
once is cheaper than carrying it in this skill prose every turn.

## Related

- `~/.claude/qute-guards.json` — where user toggles are persisted (survives
  plugin updates); `config/guards.json` in the plugin holds shipped defaults only
- `config/ntfy.json` — notification (ntfy) settings, edited directly
- `scripts/guard_toggle.py` — the kernel this skill dispatches to
- `scripts/guard_config.py` — shared resolver (merge order + per-guard fail modes)

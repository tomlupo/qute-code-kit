---
name: config
description: View or update qute-essentials notification config (ntfy.sh server, topic, priority, event flags, command filters). Triggers — "show config", "set ntfy topic", "enable task_complete notifications", "disable build_failure", "set min duration to 60s". Do NOT use for security guards (lakera, langfuse, etc.) — that's `/guard`.
argument-hint: "[show | set <key>=<value> | enable <event> | disable <event> | filter <key>=<value>]"
---

# /config

Run the helper and print stdout verbatim:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/config_toggle.py" $@
```

Pass through the user's args verbatim. The script handles config
resolution, schema validation, mutation, and the pretty-printed view.

For specific questions ("which events are valid?", "what's the
ntfy.sh rate limit?", "why doesn't disabling an event silence
the hook?"), invoke:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/config_toggle.py" --help
```

…rather than answering from memory. The script's `--help` is the
authoritative reference — schema, valid keys, gotchas, and
config-file resolution all live there.

## Out of scope

Security guards (lakera, langfuse, secrets, audit, destructive,
malware) are managed by `/guard`, not here. `/config` is the
notification-and-future-non-guard entry point.

## Related

- `/guard` — security guards (guards.json)
- `scripts/config_toggle.py` — the kernel this skill dispatches to
- `scripts/notify.py` — actual ntfy delivery (consults this config)

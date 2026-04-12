---
name: guard
description: Toggle any qute-essentials security guard on or off, or show current status. Guards include lakera (prompt injection), langfuse (tracing), secrets (credential leak prevention), audit (dep CVE scanning), destructive (dangerous command blocking), malware (write scanning). Use when the user asks to enable/disable guards, check guard status, manage security hooks, or uses phrases like "guards on", "guards off", "disable secrets guard", "turn off langfuse", "is lakera enabled".
argument-hint: "[status | <lakera|langfuse|secrets|audit|destructive|malware|all> <on|off>]"
---

# /guard

Manage the Lakera Guard (prompt injection screening) and Langfuse (tracing /
evaluation) hooks. View current status or toggle guards on/off.

## Usage

```
/guard                       # show current status (same as /guard status)
/guard status                # show current status
/guard lakera on             # enable Lakera Guard
/guard lakera off            # disable Lakera Guard
/guard langfuse on           # enable Langfuse tracing
/guard langfuse off          # disable Langfuse tracing
/guard all on                # enable both
/guard all off               # disable both
```

## Task

Run the helper script with the user's arguments:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/guard_toggle.py <args>
```

Pass through the user's arguments verbatim. The script handles all the
logic: locating the config file, reading and updating state, and printing a
status table.

## Output

The script prints a status table like:

```
Guards config: /path/to/guards.json

Guard           Enabled    API key         Description
--------------- ---------- --------------- ------------------------------
Lakera Guard    yes        set             Prompt injection screening
Langfuse        no         missing (LANGFUSE_SECRET_KEY)  Tracing / evaluation
```

**For toggle commands**, the script updates the config file and then prints
the new status table. Report the change to the user in one sentence and
confirm whether the relevant API key is configured — if it's missing, the
guard is effectively off even if the config says "yes".

**For status queries**, just present the table.

Changes take effect immediately — hooks read the config on each invocation,
so no session restart is needed.

## Related

- `/config` — manages notification and other qute-essentials plugin settings
- `scripts/guard_toggle.py` — the helper script this skill invokes
- Hooks affected: `guard-screen.py` (Lakera), `langfuse-trace.py` (Langfuse)

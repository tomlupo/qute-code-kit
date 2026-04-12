---
name: guard
description: Toggle any qute-essentials security guard on or off, or show current status. Guards include lakera (prompt injection), langfuse (tracing), secrets (credential leak prevention), audit (dep CVE scanning), destructive (dangerous command blocking), malware (write scanning). Use when the user asks to enable/disable guards, check guard status, manage security hooks, or uses phrases like "guards on", "guards off", "disable secrets guard", "turn off langfuse", "is lakera enabled".
argument-hint: "[status | <lakera|langfuse|secrets|audit|destructive|malware|all> <on|off>]"
---

# /guard

Manage qute-essentials security guards. View current status or toggle any
guard on/off.

## Guards

| Name | What it blocks | Needs API key |
|---|---|---|
| `lakera` | Prompt injection in tool outputs (via Lakera Guard API) | Yes — `LAKERA_API_KEY` |
| `langfuse` | Tracing/evaluation (Langfuse) | Yes — `LANGFUSE_SECRET_KEY` |
| `secrets` | Writes that leak API keys, tokens, or credential files | No |
| `audit` | Auto-runs pip-audit after package installs (informational) | No |
| `destructive` | Dangerous shell commands (rm -rf, git reset --hard, DROP TABLE) | No |
| `malware` | File writes containing obfuscated code, crypto drainers, reverse shells | No |

## Usage

```
/guard                         # show current status
/guard status                  # show current status
/guard lakera on               # enable Lakera Guard
/guard lakera off              # disable Lakera Guard
/guard langfuse on             # enable Langfuse tracing
/guard langfuse off            # disable Langfuse tracing
/guard secrets on              # enable secrets guard
/guard secrets off             # disable secrets guard (session override)
/guard audit on                # enable dep-audit hook
/guard audit off               # disable dep-audit hook
/guard destructive on          # enable destructive-command guard
/guard destructive off         # disable destructive-command guard
/guard malware on              # enable malware-scan hook
/guard malware off             # disable malware-scan hook
/guard all on                  # enable all guards
/guard all off                 # disable all guards
```

## Task

Run the helper script with the user's arguments:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/guard_toggle.py <args>
```

Pass through the user's arguments verbatim. The script handles config
resolution, state mutation, and printing the status table.

## Output

```
Guards config: /path/to/guards.json

Guard              Enabled    API key         Description
------------------ ---------- --------------- ------------------------------
Lakera Guard       yes        set             Prompt injection screening
Langfuse           no         missing (LANGFUSE_SECRET_KEY) Tracing / evaluation
Secrets Guard      yes        n/a             Block credential leaks
Audit Guard        yes        n/a             Auto pip-audit after installs
Destructive Guard  yes        n/a             Block dangerous shell commands
Malware Guard      yes        n/a             Scan writes for malicious code
```

**For toggle commands**, report the change in one sentence. For API-key guards
(lakera, langfuse), note if the key is missing — the guard is effectively off
even when enabled.

Changes take effect immediately — hooks read the config on each invocation.

## Gotchas

- **API-key guards are effectively OFF even when "enabled"** if the key is missing — `lakera` and `langfuse` guards do nothing without `LAKERA_API_KEY` and `LANGFUSE_SECRET_KEY` respectively; the status table shows "missing" in the API key column
- **Guard state is session-persistent** — changes via `/guard` take effect immediately and persist across sessions (written to `guards.json`); there is no automatic reset
- **`CLAUDE_SKIP_GUARDS=1` bypasses ALL guards** regardless of `guards.json` config — never set this env var permanently in `.env` or shell profile
- **`destructive` guard may false-positive** on legitimate cleanup commands like `rm -rf dist/` or `git reset --hard` on a clean feature branch — temporarily disable with `/guard destructive off`, then re-enable
- **`secrets` guard may false-positive** on test fixtures containing fake API key patterns — add `# noqa: secrets` or temporarily disable for the specific write operation

## Related

- `/config` — manages notification settings
- `scripts/guard_toggle.py` — the helper script this skill invokes
- Hooks: `guard-screen.py` (lakera), `langfuse-trace.py` (langfuse), `secrets-guard.py` (secrets), `auto_audit.py` (audit), `destructive-guard.py` (destructive), `malware-scan.py` (malware)

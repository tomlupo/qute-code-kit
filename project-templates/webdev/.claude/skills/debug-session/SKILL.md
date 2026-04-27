---
name: debug-session
description: |
  Runbook for diagnosing and fixing Claude Code session problems.
  Use when: skills aren't triggering, hooks are failing or blocking all tool calls,
  context is overloaded (slow responses, repetition), guards are blocking legitimate
  commands, plugin cache is corrupt, or the session feels stuck or broken.
  Trigger phrases: "why isn't my skill working", "hooks are broken", "all tool calls fail",
  "plugin cache", "skill not triggering", "Claude is slow", "context too large",
  "guard is blocking", "Claude is stuck", "session is broken".
argument-hint: "[symptom description]"
allowed-tools: Read, Bash, Glob, Grep
---

# Debug Session Runbook

Diagnose and fix Claude Code session problems. Match your symptom, follow the fix.

## Symptom Index

| Symptom | Section |
|---------|---------|
| Every tool call fails immediately with a hook error | [Plugin Cache Corruption](#plugin-cache-corruption) |
| Skill invoked (`/skill-name`) but nothing happens | [Skill Not Triggering](#skill-not-triggering) |
| Hook fires but logs an error | [Hook Script Error](#hook-script-error) |
| Slow responses, repetition, losing context | [Context Overload](#context-overload) |
| Guard blocks a command you know is safe | [Guard False Positive](#guard-false-positive) |
| Session breaks after `/clear` or after ~2.5 hours | [Stop Hook Regression](#stop-hook-regression) |

---

## Plugin Cache Corruption

**Symptom**: Every tool call fails immediately. Error mentions a missing script path under `~/.claude/plugins/cache/`.

**Cause**: `enabledPlugins` in `settings.json` references plugins that are no longer in cache.

**Fix sequence — ORDER MATTERS** (wrong order makes it worse):

1. Clear `enabledPlugins` first:
   ```bash
   python3 -c "
   import json, os
   f = os.path.expanduser('~/.claude/settings.json')
   s = json.load(open(f))
   s['enabledPlugins'] = {}
   json.dump(s, open(f, 'w'), indent=2)
   print('enabledPlugins cleared')
   "
   ```

2. Then clear plugin cache:
   ```bash
   rm -rf ~/.claude/plugins/cache/
   ```

3. Reinstall plugins:
   ```bash
   claude plugin install qute-essentials@qute-marketplace
   ```

**Why this order**: if you clear the cache while `enabledPlugins` still references plugins, every hook fires and immediately errors — all tool calls fail until fixed.

---

## Skill Not Triggering

**Symptom**: User types `/skill-name` but Claude ignores it or applies generic behavior.

**Diagnosis steps**:

1. Verify the skill file exists in the project:
   ```bash
   ls .claude/skills/skill-name/SKILL.md
   ```

2. Check `forced-eval` hook is active (required for reliable skill activation):
   ```bash
   grep -r "forced" ~/.claude/plugins/cache/qute-marketplace/qute-essentials/*/hooks/hooks.json
   ```

3. Read the skill's `description` field — does it contain clear trigger phrases matching the user's exact wording?

**Fixes**:
- Missing skill file → copy from `claude/skills/skill-name/` or re-run `setup-project.sh`
- `forced-eval` absent → reinstall qute-essentials: `claude plugin install qute-essentials@qute-marketplace`
- Weak description → edit the `description:` frontmatter in `SKILL.md` to add more trigger phrases in the user's language

---

## Hook Script Error

**Symptom**: A hook fires but logs a Python error or missing-file error. Tool call may be blocked or proceed with a warning.

**Diagnosis**:
```bash
# Validate hooks.json is valid JSON
python3 -m json.tool ~/.claude/plugins/cache/qute-marketplace/qute-essentials/*/hooks/hooks.json

# List scripts to verify paths
ls ~/.claude/plugins/cache/qute-marketplace/qute-essentials/*/scripts/

# Test a suspect script directly
python3 ~/.claude/plugins/cache/qute-marketplace/qute-essentials/*/scripts/suspect-script.py
```

**Common causes**:
- Script path in `hooks.json` doesn't match actual filename (e.g., `track_edits.py` renamed to `doc_reminder.py`)
- Python script has a syntax error — run it directly to see the traceback
- Missing import — the script requires a package not in PATH

---

## Context Overload

**Symptom**: Responses slow down, Claude repeats itself, loses track of earlier instructions, or context window warning appears.

**Options in order of disruption**:

| Option | Command | When |
|--------|---------|------|
| Summarize in-place | `/compact` | Still in flow, just bulky context |
| Structured transition | `/handoff "what I was doing"` → new session → `/pickup` | Natural stopping point, multi-day work |
| Quick resume | `claude -c` | Short break, simple continuation |

**Signs context is the problem (not skill or hook issues)**:
- Same question answered differently than 30 messages ago
- Claude forgets a constraint set early in the session
- Tool calls taking noticeably longer than at session start

---

## Guard False Positive

**Symptom**: A security guard blocks a shell command or file write you know is safe.

**Diagnosis**:
```
/guard status
```

**Temporary fix**:
```
/guard <name> off
# ... do your operation ...
/guard <name> on
```

**Guards most likely to false-positive**:

| Guard | Common false positive |
|-------|----------------------|
| `destructive` | `rm -rf dist/`, `git reset --hard` on clean feature branch |
| `secrets` | Test fixtures with fake API key patterns |
| `malware` | Minified JS or base64-encoded assets in source files |

---

## Stop Hook Regression

**Symptom**: After `/clear` or after ~2.5 hours, end-of-session hooks stop firing (e.g., handoff not auto-created).

**Cause**: Known Claude Code regression — `Stop` event hooks fire once then break after `/clear` and after extended sessions.

**Workaround**: Don't rely on stop hooks for critical end-of-session actions. Always call `/handoff` explicitly before ending a session.

---

## Gotchas

- **Never clear plugin cache without first clearing `enabledPlugins`** — this is the #1 cause of catastrophic hook failures
- **Settings changes require a Claude Code restart** — edits to `settings.json` are not hot-reloaded; hooks are cached at session start
- **`CLAUDE_SKIP_GUARDS=1` bypasses ALL guards** — never set this in `.env` or shell profile permanently
- **`git worktree remove` fails on uncommitted changes** — stash or commit first; the error is non-obvious
- **After `claude plugin uninstall`, re-run `claude plugin install`** — uninstall clears the cache; the plugins entry in settings.json must also be updated

## Related

- `/guard` — toggle security guards, diagnose false positives
- `/guard status` — show current guard state including API key presence
- `/handoff` — proper session-end that survives stop hook regressions
- `/pickup` — load last handoff at session start

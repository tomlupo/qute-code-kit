# Tips & Troubleshooting

## Context Management

### Keep context lean

- **Search before read** — `Grep` for patterns, `Glob` for files, then read only what's relevant
- **Progressive disclosure** — start with overview (ls, README), sample patterns, then targeted reads
- **Save large outputs to files** — show summaries in chat, reference the file path
- **Use subagents** — `Task(Explore)` for codebase questions protects main context

### Compaction

| Trigger | Action |
|---------|--------|
| 50 tool calls | `strategic-compact` reminds you |
| Every 25 after | Repeated reminders |
| Major task done | Run `/compact` manually |
| Switching focus | `/strategic-compact:handoff <goal>` creates a handoff doc |

### Session handoffs

Create a handoff before ending a long session:

```
/strategic-compact:handoff "finishing API endpoints"
```

Resume in a new session:

```
Read .claude/handoffs/2024-01-15-api-endpoints.md and continue the work
```

## Headless Mode

Run Claude non-interactively for automation:

```bash
# Basic
claude -p "Run tests and summarize failures" --allowedTools "Bash,Read"

# JSON output
claude -p "Analyze src/" --allowedTools "Read,Grep,Glob" --output-format json > report.json

# Streaming
claude -p "Refactor deprecated calls" --allowedTools "Read,Edit,Grep" --output-format stream-json --verbose
```

| Flag | Purpose |
|------|---------|
| `-p "instruction"` | Non-interactive prompt |
| `--allowedTools "..."` | Grant tool permissions |
| `--dangerously-skip-permissions` | Skip all prompts (sandboxed environments only) |
| `--output-format json` | JSON output |
| `--output-format stream-json` | Streaming JSON (requires `--verbose` with `-p`) |

Use cases: CI pipelines, batch documentation updates, refactoring sweeps, scheduled tasks.

## System Prompt Injection

Rules in `.claude/rules/` auto-load every session. Skills load on demand.

For strict behavioral rules, inject via CLI:

```bash
claude --system-prompt "$(cat contexts/dev.md)"
```

Priority: **system prompt > user message > tool output**.

The work mode aliases (`claude-dev`, `claude-research`, `claude-review`) use this mechanism.

## Troubleshooting

### Skills not activating

Claude jumps to implementation without using available skills.

**Fix**: Install `forced-eval` plugin, or invoke skills explicitly with `/skill-name`. Check that the skill's `description` field contains matching trigger phrases.

### Context exhaustion

Claude loses track of earlier discussion, responses become generic.

**Fix**: Run `/compact`. Delegate research to subagents. Break large tasks into separate sessions. Use progressive disclosure.

### Lost work

Session ended, unsure what was completed.

**Fix**: Check `session-persistence` output at session start. Use `/gist-transcript` before ending important sessions. Review `git log`.

### Skill shows wrong behavior

Skill does something unexpected or uses outdated patterns.

**Fix**: Re-read the skill file (skills may have evolved). Check for conflicts with user instructions. Use explicit `/skill-name` to force fresh load.

### External plugins missing

Skills or agents from external plugins not available.

**Fix**: Run `python scripts/setup-externals.py` to fetch from manifest. Check `external-plugins.json` for entries.

### Hook not firing

Plugin hook doesn't seem to trigger.

**Fix**: Check `plugin.json` has correct `hooks` path. Verify the hook event name matches (e.g., `PostToolUse` not `post_tool_use`). Check hook script exits 0 on success.

# Workflow Guidelines

How to track work using available tools.

## Task Tracking Layers

| Layer | Tool | Scope | Purpose |
|-------|------|-------|---------|
| **Project** | TASKS.md | Weeks/months | What needs doing |
| **Task Docs** | docs/tasks/ | Task lifetime | Detailed planning |
| **Memory** | ledger.md | Persistent | Decisions & patterns |
| **Session** | .claude/sessions/ | Hours/days | Work context |
| **Handoff** | .claude/handoffs/ | Per-compaction | State snapshots |

## TASKS.md Structure

- **Now**: Current focus (1-2 items)
- **Next**: Ready to pick up (3-5 items)
- **Later**: Backlog
- **Completed**: Done work

Format: `- [ ] Task Name` or `- [ ] Task Name -> docs/tasks/task-name.md`

## Session Workflow

### Starting Work
1. Check TASKS.md for current focus
2. `/workflow:session [name]` - loads ledger + handoffs
3. Break down with TodoWrite

### During Work
- File changes auto-logged
- `/workflow:session-update` for milestones
- Ledger context injected every message

### Finishing Work
1. `/workflow:session-finish`
2. Generate TL;DR
3. Track outcome (SUCCEEDED/PARTIAL/FAILED)
4. Update ledger
5. Archive to archive.md

## Ledger Maintenance

Keep `.claude/memory/ledger.md` under 50 lines:
- Current Goal: What you're working on
- Active Files: Files being modified
- Recent Decisions: Max 5, with dates
- Proven Patterns: Max 3, validated 3+ times

Rotate old items to `.claude/memory/archive.md`.

## Auto-Handoffs

When context fills, PreCompact hook:
1. Generates handoff to `.claude/handoffs/`
2. Blocks degraded compaction
3. Prompts `/clear` instead
4. Handoff auto-loads on resume

## Key Principles

- **TASKS.md** = what to do
- **ledger.md** = what we know
- **Sessions** = what happened
- **Handoffs** = state snapshots
- **TodoWrite** = what I'm doing now

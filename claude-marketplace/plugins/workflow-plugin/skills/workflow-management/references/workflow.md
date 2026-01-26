# Workflow Reference

Detailed procedures for workflow management.

## Task Tracking Layers

| Layer | Tool | Scope | Purpose |
|-------|------|-------|---------|
| **Project** | TASKS.md | Weeks/months | What needs doing |
| **Task Docs** | docs/tasks/ | Task lifetime | Detailed planning |
| **Memory** | ledger.md | Persistent | Decisions & patterns |
| **Session** | .claude/sessions/ | Hours/days | Work context |
| **Handoff** | .claude/handoffs/ | Per-compaction | State snapshots |

## Session Lifecycle

### Starting Work

1. Check TASKS.md for current focus
2. `/workflow:session [name]` - loads:
   - Latest handoff (if < 24h old)
   - Session ledger (always)
   - Active session (if binding)
3. If task has `docs/tasks/` link, read task doc
4. Use TodoWrite for immediate breakdown

### During Work

- File changes auto-logged to session
- Use `/workflow:session-update` for milestones
- Ledger injected on every message (survives compaction)

### Context Filling Up

PreCompact hook automatically:
1. Blocks manual `/compact`
2. Generates handoff with current state
3. Prompts to use `/clear` instead
4. Handoff loads on restart

### Finishing Work

`/workflow:session-finish`:
1. Generate TL;DR (1-2 sentences)
2. Track outcome (SUCCEEDED/PARTIAL/FAILED)
3. Ask: Mark task complete?
4. Archive task doc if exists
5. Update ledger (rotate old decisions)
6. Add TL;DR to archive.md

## Ledger Maintenance

### Adding Decisions

```markdown
## Recent Decisions (max 5)
- [New decision] (YYYY-MM-DD)
- [Older decision] (YYYY-MM-DD)
```

When adding 6th decision:
1. Move oldest to `.claude/memory/archive.md`
2. Add new decision at top

### Adding Patterns

Only add patterns validated 3+ times:
```markdown
## Proven Patterns (max 3)
- Simple momentum beats complex ML
- Cross-sectional signals more robust than absolute
```

### Total Line Limit

Keep ledger.md under 50 lines. If over:
1. Move oldest items to archive.md
2. Keep only essential current context

## Task Documentation

Create `docs/tasks/task-name.md` when:
- Task has multiple phases
- Task requires research or decisions
- Task has dependencies

### Task Doc vs Session

- **Task doc** = what to build (planning, architecture)
- **Session** = how it was built (work log, debugging)

### Archiving

When `/workflow:session-finish` completes a task:
1. Add completion header (date, summary, outcomes)
2. Move to `docs/tasks/completed/`

## Directory Structure

```
.claude/
├── memory/
│   ├── ledger.md      # Hot - always loaded
│   └── archive.md     # Cold - never auto-loaded
├── sessions/
│   ├── .active-sessions  # JSON list
│   └── YYYY-MM-DD-HHMM-name.md
└── handoffs/
    └── YYYY-MM-DD-HHMM.md  # Auto-generated

docs/tasks/
├── task-name.md       # Active task docs
└── completed/         # Archived task docs

TASKS.md               # Task overview
```

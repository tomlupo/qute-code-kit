Show context, tasks, and sessions overview.

**Usage:** `/workflow:sessions`

## Output

```
## Ledger (from .claude/memory/ledger.md)
- Goal: [current goal]
- Active Files: [list]
- Decisions: [recent decisions]
- Patterns: [proven patterns]

## Tasks (from TASKS.md)
### Now
- [ ] Cross-sectional momentum ranking ← SESSION: momentum-ranking

### Next
- [ ] Run foundational_suite.yaml
- [ ] Compare trainer types

## Sessions
- momentum-ranking (2h ago) ← BOUND
- auth-fix (completed Dec 18) [SUCCEEDED]

## Recent Handoffs
- 2025-12-29 15:30 - feature analysis

## Commands
- /workflow:session [name] - Start/bind session
- /workflow:session-update [notes] - Add progress
- /workflow:session-finish - End session
```

## Implementation

1. Read `.claude/memory/ledger.md` - show goal, active files, decisions, patterns
2. Read `TASKS.md` - show Now section + first 3 from Next
3. Read `.claude/sessions/.active-sessions` for active sessions
4. Read `.claude/handoffs/` - show 2 most recent
5. Show task↔session links
6. Show bound session if any
7. Show 2 most recent completed sessions with outcomes

## Task Doc Indicator

When listing sessions, check for matching `docs/tasks/{slug}.md`:
```
- feature-selection-pipeline 📋  (2h ago) ← BOUND
```
📋 = has docs/tasks/ planning file

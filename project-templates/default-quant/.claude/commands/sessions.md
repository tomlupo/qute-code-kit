Show context, tasks, and sessions overview.

**Usage:** `/sessions`

## Output

```
## Context (from .claude/memory/context.md)
- Focus: Feature Selection Pipeline, Session management
- Decisions: XSMOM baseline (IR 0.48), Classification > Regression
- Patterns: Simple momentum beats complex ML

## Tasks (from TASKS.md)
### Now
- [ ] Cross-sectional momentum ranking ← SESSION: momentum-ranking

### Next
- [ ] Run foundational_suite.yaml
- [ ] Compare trainer types

## Sessions
- momentum-ranking (2h ago) ← BOUND
- auth-fix (completed Dec 18)

## Commands
- /session [name] - Start/bind session
- /session-update [notes] - Add progress
- /session-finish - End session
```

## Implementation

1. Read `.claude/memory/context.md` - show focus, key decisions, patterns (compact format)
2. Read `TASKS.md` - show Now section + first 3 from Next
3. Read `.claude/sessions/.active-sessions` for active sessions
4. Show task↔session links (match by name similarity)
5. Show bound session if any
6. Show 2 most recent completed sessions

Initialize workflow management in a project.

**Usage:** `/workflow:init`

## Purpose

Scaffold the workflow directory structure and files for a new project.

## Created Files

```
.claude/
├── memory/
│   ├── ledger.md      # Session ledger (replaces context.md)
│   └── archive.md     # Cold storage for history
├── sessions/
│   └── .active-sessions  # JSON: {"sessions": []}
└── handoffs/          # Auto-handoff directory

.ai/
├── workflow.md        # Workflow guidelines
└── documentation.md   # Documentation standards

docs/
└── tasks/
    └── completed/     # Archived task docs

TASKS.md               # Task tracking file
```

## Behavior

1. **Check existing files:**
   - For each file, check if it already exists
   - If exists: Skip with message "✓ Already exists: [path]"
   - If not: Create with template content

2. **Create directories:**
   - `.claude/memory/`
   - `.claude/sessions/`
   - `.claude/handoffs/`
   - `.ai/`
   - `docs/tasks/completed/`

3. **Create ledger.md** with template:
```markdown
# Session Ledger

## Current Goal
[Not set - use /workflow:session to start]

## Active Task
- Task: None
- Session: None

## Active Files
[No files tracked]

## Constraints
- [Add project constraints here]

## Recent Decisions (max 5)
[No decisions recorded]

## Proven Patterns (max 3)
[No patterns validated yet]

## Quick Reference
- Start session: `/workflow:session [name]`
- View overview: `/workflow:sessions`
```

4. **Create archive.md** with template:
```markdown
# Archive

DO NOT READ unless explicitly asked. This is cold storage.

## Archived Decisions
[Rotated from ledger when over limit]

## Session Summaries
[TL;DRs from completed sessions]
```

5. **Create .active-sessions:**
```json
{"sessions": []}
```

6. **Create TASKS.md** with template:
```markdown
# Tasks

## Now
- [ ] [Add your current focus here]

## Next
- [ ] [Add upcoming tasks]

## Later
- [ ] [Add backlog items]

## Completed
```

## Confirmation

```
Workflow initialized:
✓ Created .claude/memory/ledger.md
✓ Created .claude/memory/archive.md
✓ Created .claude/sessions/.active-sessions
✓ Created .claude/handoffs/
✓ Created docs/tasks/completed/
✓ Created TASKS.md (or already exists)

Run `/workflow:session [name]` to start working.
```

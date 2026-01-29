# Workflow Guidelines

How to track work across different time horizons using the available tools.

## Task Tracking Layers

| Layer | Tool | Persistence | Time Scope | Purpose |
|-------|------|-------------|------------|---------|
| **Project** | BACKLOG.md / IN_PROGRESS.md | Git-tracked | Weeks/months | What the project needs |
| **Session** | .claude/sessions/ | Markdown files | Hours/days | What happened in a work session |
| **Conversation** | TodoWrite | Context window | Minutes/hours | What I'm doing right now |
| **Immediate** | Memory | Context window | Seconds/minutes | Current context |

## When to Use Each

### BACKLOG.md
- Ideas and future work
- Non-urgent bugs
- Research topics
- "Parking lot" for ideas that interrupt flow

### IN_PROGRESS.md
- Currently active project-level tasks
- Only major items, not granular subtasks
- Updated when starting/completing significant work

### Sessions (.claude/sessions/)
- Development work history
- Detailed context for future conversations
- Git changes, decisions made, issues found
- Start when beginning significant work, end when done
- Commands: `/session-start`, `/session-update`, `/session-end`, `/session-help`

### TodoWrite
- Immediate task breakdown
- Granular execution tracking
- Updated frequently during work
- Cleared when conversation ends

### CHANGELOG.md
- **When:** Only on `main` branch, after commit or merge
- **What:** User-facing changes (features, fixes, improvements)
- **Not:** Internal refactors, dev tooling, documentation updates
- **Format:** Keep It Simple - date + brief description

## Workflows

### Starting Work
1. Check IN_PROGRESS.md for active project tasks
2. `/session-start [name]` to begin tracking
3. TodoWrite breaks down immediate work

### During Work
- TodoWrite: Track granular progress
- `/session-update`: Capture milestones (optional)
- IN_PROGRESS.md: Update only for major completions

### Ending Work
1. Complete todos in TodoWrite
2. `/session-end` with summary
3. Update IN_PROGRESS.md if project task complete
4. New ideas → BACKLOG.md

### After Merge to Main
1. Update CHANGELOG.md with user-facing changes
2. Keep entries brief and meaningful

### Resuming Work (New Conversation)
1. Check IN_PROGRESS.md for context
2. `/session-bind [name]` if continuing session
3. Read session file for history
4. TodoWrite picks up remaining work

## Key Principles

- **Don't duplicate**: TodoWrite items ≠ IN_PROGRESS.md items
- **Right granularity**: Project tasks are broad, todos are specific
- **Sessions are history**: Capture what happened, not just what's left
- **BACKLOG is parking**: Move ideas there to maintain focus
- **CHANGELOG is for users**: Only meaningful, shipped changes on main

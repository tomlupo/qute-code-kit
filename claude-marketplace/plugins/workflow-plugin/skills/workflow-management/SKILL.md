---
name: workflow-management
description: |
  Session, task, and context management for Claude Code. Use when:
  (1) Starting work on a task - use /workflow:session
  (2) Tracking progress during work - use /workflow:session-update
  (3) Finishing work - use /workflow:session-finish
  (4) Viewing current status - use /workflow:sessions
  (5) Initializing workflow in new project - use /workflow:init

  The workflow system prevents context degradation through auto-handoffs
  and maintains a structured ledger of goals, decisions, and patterns.
---

# Workflow Management

Manage sessions, tasks, and context across Claude Code conversations.

## Quick Start

```bash
# Initialize in new project
/workflow:init

# Start working
/workflow:session feature-name

# During work
/workflow:session-update "completed X, starting Y"

# Finish
/workflow:session-finish
```

## Core Concepts

### Session Ledger (`.claude/memory/ledger.md`)

Structured context that persists across sessions:
- **Current Goal**: What you're working on
- **Active Files**: Files being modified with context
- **Constraints**: Project-specific rules
- **Recent Decisions**: Max 5, with dates
- **Proven Patterns**: Max 3, validated 3+ times

### Auto-Handoffs (`.claude/handoffs/`)

When context fills up, the PreCompact hook automatically:
1. Captures current state (goal, files, changes, decisions)
2. Saves to `.claude/handoffs/YYYY-MM-DD-HHMM.md`
3. Keeps 5 most recent handoffs

On session resume, the latest handoff is auto-loaded.

### Task Binding

Sessions link to TASKS.md via `@session:name` annotation:
```markdown
- [ ] My task `@session:feature-name`
```

## Commands

| Command | Purpose |
|---------|---------|
| `/workflow:session [name]` | Start or bind to session |
| `/workflow:session-update [notes]` | Add progress notes |
| `/workflow:session-finish` | End session with summary |
| `/workflow:sessions` | View status overview |
| `/workflow:init` | Initialize in new project |

## Session Outcomes

Track outcomes when finishing sessions:
- **SUCCEEDED**: Goal fully achieved
- **PARTIAL**: Some progress, work remains
- **FAILED**: Blocked or abandoned

See `references/workflow.md` for detailed procedures.

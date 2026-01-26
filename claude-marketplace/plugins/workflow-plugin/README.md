# Workflow Manager Plugin

Session, task, and context management for Claude Code with auto-handoff to prevent context degradation.

## Features

- **Session Management** - Track work across conversations
- **Auto-Handoffs** - Preserve state before context clears (inspired by Continuous-Claude)
- **Structured Ledger** - Systematic context persistence
- **Task Integration** - Link sessions to TASKS.md
- **Session Outcomes** - Track SUCCEEDED/PARTIAL/FAILED
- **Worktree Support** - Parallel development

## Installation

```bash
### From GitHub (when published)
claude plugin install workflow-manager@twilc

### Local installation
claude plugin install ~/projects/workflow-plugin
```

## Quick Start

```bash
### Initialize in new project
/workflow:init

### Start working
/workflow:session feature-name

### During work
/workflow:session-update "completed X, starting Y"

### Finish
/workflow:session-finish

### View status
/workflow:sessions
```

## Commands

| Command | Purpose |
|---------|---------|
| `/workflow:init` | Initialize workflow in project |
| `/workflow:session [name]` | Start or bind to session |
| `/workflow:session-update [notes]` | Add progress notes |
| `/workflow:session-finish` | End session with summary |
| `/workflow:sessions` | View status overview |

## Key Innovation: Auto-Handoffs

When context fills up, the PreCompact hook automatically:
1. Captures current state (goal, files, changes, decisions)
2. Saves structured handoff to `.claude/handoffs/`
3. Prompts to use `/clear` instead of `/compact`
4. Auto-loads handoff on next session start

This prevents signal degradation from repeated compaction ("summaries of summaries").

## Directory Structure

After `/workflow:init`:

```
.claude/
├── memory/
│   ├── ledger.md      # Session ledger (hot)
│   └── archive.md     # Historical data (cold)
├── sessions/
│   └── YYYY-MM-DD-HHMM-name.md
└── handoffs/
    └── YYYY-MM-DD-HHMM.md

docs/tasks/
├── task-name.md       # Active task docs
└── completed/         # Archived task docs

TASKS.md               # Task overview
```

## Skills Included

- **workflow-management** - Session and task management
- **context-management** - Token budget strategies
- **worktrees** - Parallel development with git worktrees

## Credits

Inspired by [Continuous-Claude](https://github.com/parcadei/Continuous-Claude-v2) for the PreCompact/handoff concept.

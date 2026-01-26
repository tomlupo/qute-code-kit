# Workflow Implementation

Technical reference for the session-based workflow system.

## Commands

| Command | Purpose |
|---------|---------|
| `/session [name]` | Start/bind session, load context.md |
| `/session-update [notes]` | Add progress notes to session |
| `/session-finish` | End session, prune context, archive TL;DR |
| `/sessions` | Show tasks and sessions overview |

See `.claude/commands/` for detailed specifications.

## Directory Structure

```
.claude/
├── commands/           # Slash command specifications
│   ├── session.md
│   ├── session-update.md
│   ├── session-finish.md
│   └── sessions.md
├── hooks/              # Python hooks
│   ├── session_remind.py   # UserPromptSubmit - context injection
│   ├── session_start.py    # SessionStart - initial context load
│   └── track_changes.py    # PostToolUse - file change logging
├── sessions/           # Session files
│   ├── .active-sessions    # JSON: {"sessions": ["name1", "name2"]}
│   └── YYYY-MM-DD-HHMM-name.md
├── memory/             # Persistent context
│   ├── context.md      # Hot - loaded on /session
│   └── archive.md      # Cold - never auto-loaded
└── docs/
    └── workflow-implementation.md  # This file
```

## Hooks

### session_remind.py (UserPromptSubmit)
- Fires on every user message
- Injects: `[Session: name] Task: description`
- Survives context compaction in long sessions

### session_start.py (SessionStart)
- Fires when Claude Code CLI starts
- Loads TASKS.md Now section
- Shows active sessions

### track_changes.py (PostToolUse)
- Fires after Write/Edit tools
- Logs to `.claude/hooks/changes.log`
- Auto-appends to active session file

## Session File Format

```markdown
# Session: [name]

**Started:** YYYY-MM-DD HH:MM
**Task:** [linked task from TASKS.md]

## Progress

- created: `path/to/file`
- modified: `path/to/file`

---

## TL;DR
[1-2 sentence summary]

## Ended: YYYY-MM-DD HH:MM (Xh duration)

### Done
- [completed items]

### Git
- Files: X added, Y modified, Z deleted

### Next
- [remaining work]
```

## Context Files

### context.md (Hot)
- Loaded by `/session` command
- Max 50 lines
- Limits: 2 focus, 5 decisions, 3 patterns

### archive.md (Cold)
- Header: "DO NOT READ unless explicitly asked"
- Contains: archived decisions, patterns, session TL;DRs
- Only load on explicit user request

## Task Binding

Sessions link to TASKS.md via `@session:name` annotation:
```markdown
- [ ] Task Name `@session:session-name`
```

- Added by `/session` when task matches
- Removed by `/session-finish`
- Enables multi-agent coordination (grep for bound tasks)

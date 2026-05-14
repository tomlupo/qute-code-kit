---
name: board
description: Show open tasks for the current repo. Auto-detects backend (Paperclip or TASKS.md). Use when user says "what's on the board", "show tasks", "what do I have open", or wants to glance at the backlog.
argument-hint: ""
---

# /board

Quick view of open tasks in this repo's task source.

## When to use

- "what's on the board?", "show tasks", "what's open here", "backlog"
- Glance before starting / picking what to work on

Do NOT invoke for:
- Cross-branch git state — use `/status`
- Single-task focus context — use `/pickup`

## Behavior

```bash
bash "$CLAUDE_PLUGIN_ROOT/scripts/tasks/board.sh" "$@"
```

Print stdout verbatim. The script handles backend routing.

## Output

- **paperclip:** lists open issues for this repo's Paperclip project, grouped by status (`in_progress` first, then `todo`, then `blocked`, then `in_review`).
- **tasks-md:** prints the file (or just the unchecked items if you pass `--open`).

No editing; read-only.

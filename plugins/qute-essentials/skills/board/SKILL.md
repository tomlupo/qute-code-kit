---
name: board
description: Unified task view for the current repo — MERGES TASKS.md, GitHub Issues (gh), and Paperclip into one picture and flags likely duplicates. Use when user says "board", "what's on the board", "show tasks", "what's open", "what do I have", or wants one glance across local notes, GitHub, and Paperclip before starting work.
argument-hint: ""
---

# /board

One picture of every task source in this repo. Powered by the shared task engine
(`pulse.sh`), which merges all sources that are present and surfaces overlap.

## When to use

- "board", "show tasks", "what's open here", "backlog", "what do I have"
- Before planning / picking what to work on
- To spot the same task tracked twice across systems

Do NOT invoke for:
- Pure git/worktree state — use `/status`
- Loading one task's session context — use `/pickup`
- Adding or closing a task — use `/task`

## Behavior

```bash
bash "$CLAUDE_PLUGIN_ROOT/scripts/tasks/pulse.sh" report
```

Print stdout verbatim. Read-only.

## Sources (auto-detected, all optional)

- **TASKS.md** in the repo root → unchecked `- [ ]` items.
- **GitHub Issues** via `gh` (needs `gh auth login`) → open issues for the repo.
- **Paperclip** → open issues for the project whose `codebase.localFolder`
  matches the repo (needs `~/.paperclip/auth.json`). Reuses `lib.sh`.

Output groups by source and ends with a `WARN possible duplicates` block when
the same normalized title appears in more than one source. Missing sources are
dropped silently — `/board` works even with only `TASKS.md`.

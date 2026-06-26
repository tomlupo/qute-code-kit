---
name: board
description: Show this repo's open tasks from its single ACTIVE store — a plain TASKS.md checklist (Tier 1) or GitHub Issues via `gh` (Tier 2), auto-detected. Use when the user says "board", "what's on the board", "show tasks", "what's open", "what do I have", or wants one glance at the backlog before starting work.
argument-hint: ""
---

# /board

One picture of this repo's open tasks. Powered by the shared tiered task engine
(`pulse.sh`), which reads whichever store is live — TASKS.md or GitHub Issues —
and never both at once.

## When to use

- "board", "show tasks", "what's open here", "backlog", "what do I have"
- Before planning / picking what to work on

Do NOT invoke for:
- Pure git/worktree state — use `/repo-status`
- Loading one task's session context — use `/pickup`
- Adding or closing a task — use `/task`

## Behavior

```bash
bash "$CLAUDE_PLUGIN_ROOT/scripts/tasks/pulse.sh" report
```

Print stdout verbatim. Read-only.

## The active store (auto-detected)

A repo has exactly **one live task store** — `/board` shows that one:

- **Tier 1 — TASKS.md:** unchecked `- [ ]` items in the repo root. The default
  for small/new repos or any repo without a GitHub remote.
- **Tier 2 — GitHub Issues:** open issues via `gh` (needs `gh auth login`). The
  store once a repo has graduated.

The header line names which store is live (`[store: tasks-md]` or
`[store: github]`). Resolution precedence: a `## Task source:` line in CLAUDE.md
wins; else a tombstoned TASKS.md means the repo graduated to Issues; else a live
TASKS.md is Tier 1; else a GitHub repo with open issues is Tier 2; else Tier 1.

There is no merge across stores and no Paperclip backend — one store, one list.

## Migration proposal

When the live store is TASKS.md, the repo is on GitHub, and the open count
crosses the threshold (default 12, tunable), `report` appends a one-time
proposal to graduate to GitHub Issues. Surface it; route the user to
`/task migrate` (accept) or `/task decline` (stay local, silence the nag).
See the `/task` skill for the mechanics.

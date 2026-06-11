---
name: task
description: Add or complete a task in this repo's tracker(s) — TASKS.md, GitHub Issues, or Paperclip. Auto-routes to the right backend (declared `## Task source` in CLAUDE.md, or the single source present), or target one explicitly. Use when user says "new task", "add task", "create issue", "track this", "mark done", "close that", or pastes work that needs a home.
argument-hint: "<title> [body...]  |  done <ref>  |  --to <backend> <title>"
---

# /task

Write half of the task engine. Adds or completes a task in whichever backend this
repo uses, sharing one engine (`pulse.sh`) with `/board`. No backend ceremony —
just give it a title; it routes for you.

## When to use

- "new task X", "add to backlog", "track this", "create issue"
- "mark done", "close <ref>", "complete that"
- After a discussion that produced a unit of work

Do NOT invoke for:
- Viewing the backlog — use `/board`
- Pure git state / session context — use `/repo-status`, `/pickup`

## Behavior

Add (auto-routes when `--to` is omitted):

```bash
bash "$CLAUDE_PLUGIN_ROOT/scripts/tasks/pulse.sh" add "<title>" [body...]
bash "$CLAUDE_PLUGIN_ROOT/scripts/tasks/pulse.sh" add --to <github|paperclip|tasks-md> "<title>" [body...]
```

Complete:

```bash
bash "$CLAUDE_PLUGIN_ROOT/scripts/tasks/pulse.sh" close --in <github|paperclip> <id> [comment...]
```

Print stdout verbatim.

## Routing (when `--to` is omitted)

1. `## Task source: <github|paperclip|tasks-md>` in CLAUDE.md → wins.
2. Otherwise, if exactly one source is present in the repo → use it.
3. Multiple or none present → asks you to pass `--to`.

## What it writes

- **tasks-md:** appends `- [ ] **<title>** - <body>` to TASKS.md.
- **github:** `gh issue create` → prints the new issue URL.
- **paperclip:** `POST /api/companies/:id/issues` (`status=todo`, `priority=medium`)
  in the matching project → prints `<identifier> <title>`.

One backend per call — no silent mirroring across sources.

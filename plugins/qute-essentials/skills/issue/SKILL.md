---
name: issue
description: Create a new task in the current repo's task source. Auto-detects backend (Paperclip if a project matches the repo, TASKS.md if file exists, declared `## Task source` in CLAUDE.md wins). Use when user says "new issue", "create task", "add to backlog", "track this", or pastes a description that needs a home.
argument-hint: "<title> [description...]"
---

# /issue

Adds a task to whichever backend this repo uses. **No backend ceremony** — just give it a title.

## When to use

- "create issue X", "new task", "add to backlog", "track this"
- After a discussion that produced a unit of work
- Anything you'd otherwise jot in TASKS.md or open Paperclip UI for

## Behavior

```bash
bash "$CLAUDE_PLUGIN_ROOT/scripts/tasks/issue.sh" "$@"
```

Print stdout verbatim. The script handles backend routing.

## Backend detection (handled by the script)

1. **`## Task source: paperclip|tasks-md` in CLAUDE.md** → use that.
2. **Otherwise auto-detect:**
   - Paperclip project's `codebase.localFolder` matches `git rev-parse --show-toplevel` → paperclip
   - `TASKS.md` exists in repo root → tasks-md
3. **Both** → ambiguous; refuses with "add `## Task source` to CLAUDE.md".
4. **Neither** → "no task source" message with setup instructions.

## What it writes

- **paperclip:** creates an issue in the matching project (`status=todo`, `priority=medium` defaults). Prints `<identifier> <title>`.
- **tasks-md:** appends `- [ ] <title> — <description>` to the end of TASKS.md. Prints `appended to TASKS.md`.

No frontmatter, no plan files, no scaffolding. The issue body is exactly what you type.

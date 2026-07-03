---
name: pickup
description: Resume work — find and load the latest handoff for this repo from ~/.claude/handoffs/, summarize state. Use when user says "resume", "pickup", "where were we", "continue".
argument-hint: "[slug]"
---

# /pickup

Loads the most recent handoff matching this repo and briefs you on it.

## When to use

- "resume", "pickup", "where were we", "continue"
- Session start, after context reset

Do NOT invoke for:
- Cross-branch git state — use `/repo-status`
- Listing tasks — use `/repo-status` (its Open tasks section)

## Behavior

1. Find candidates in `~/.claude/handoffs/` (machine-local, not git).
2. Filter to handoffs matching the current repo (their first line should mention repo + branch).
3. If `[slug]` given: pick the handoff whose filename contains the slug. Otherwise: most recent by mtime.
4. Read that handoff and brief: 100-200 words covering Summary, Next, and any References.

```bash
ls -t ~/.claude/handoffs/*.md 2>/dev/null | head -10
```

Use the file's first line (repo + branch + date) to filter to this repo. Stop after loading **one** handoff — `/pickup` is a brief, not a full ramp-up.

If no matching handoff exists: print *"no recent handoff for this repo. Start fresh."*

## What `/pickup` does NOT do

- Read multiple handoffs / build a history.
- Read methodology docs, plan files, or anything proactively beyond the chosen handoff.
- Run tests, lint, or any command "to check state."
- Auto-execute a "next action" (the lean handoff doesn't carry executable `cmd:` fields).
- Edit files.

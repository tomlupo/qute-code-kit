---
description: "Show workflow lifecycle overview — active plan, tasks, ideas, completed plans"
---

# /flow:status

Display the current state of the workflow lifecycle.

## Behavior

When the user invokes `/flow:status`:

1. **Active plan** (from `.flow-state`):
   - If active: show plan path, goal, current phase, phase progress (e.g. 2/5 complete)
   - If none: show "No active plan"

2. **TASKS.md summary** (if exists):
   - Count items in Now / Next / Later / Completed sections
   - Show the Now items in full

3. **Ideas** (from `docs/ideas/`):
   - Count of idea files
   - List the 3 most recent by filename

4. **Plans** (from `docs/plans/`):
   - Count of active plans
   - List them with dates

5. **Completed** (from `docs/plans/completed/`):
   - Count of archived plans

## Output Format

```
Flow Status
===========

Active Plan: docs/plans/2026-02-20-feat-auth-plan.md
  Goal: Implement user authentication
  Phase: 3/5 (Implementation)

Tasks (TASKS.md):
  Now:  1 | Next: 3 | Later: 5 | Done: 8

Ideas: 4 in docs/ideas/
  - 2026-02-18-caching-strategy.md
  - 2026-02-15-notification-system.md
  - 2026-02-10-api-v2.md

Plans: 2 active in docs/plans/
Completed: 6 in docs/plans/completed/
```

If no workflow files exist at all, show:

```
Flow Status: No workflow files found.

Run /flow:idea to capture your first idea, or /flow:activate to track an existing plan.
```

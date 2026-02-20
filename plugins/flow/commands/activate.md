---
description: "Set the active plan for discipline hooks. Hooks will re-read this plan before decisions."
---

# /flow:activate

Activate a plan so discipline hooks track it.

## Behavior

When the user invokes `/flow:activate [path]`:

1. **Resolve the plan path**:
   - If `[path]` provided, use it directly
   - If omitted, list files in `docs/plans/` and ask the user to pick one
   - Validate the file exists

2. **Create `.flow-state`** in the project root:
   ```
   active_plan: <resolved-path>
   activated_at: <ISO timestamp>
   ```

3. **Read the plan** and display a brief status:
   - Goal
   - Current phase
   - Total phases and their status

4. **Confirm**: "Plan activated. Hooks will re-read it before Write/Edit/Bash decisions."

## Arguments

- `[path]` — (Optional) Path to the plan file, e.g. `docs/plans/2026-02-20-feat-auth-plan.md`

## Notes

- Only one plan can be active at a time per project root
- Use `/flow:deactivate` to clear without archiving
- Use `/flow:complete` to archive and clear
- In git worktrees, each worktree has its own `.flow-state`

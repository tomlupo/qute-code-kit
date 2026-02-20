---
description: "Clear the active plan without archiving. Hooks go silent."
---

# /flow:deactivate

Deactivate the current plan. Hooks stop firing.

## Behavior

When the user invokes `/flow:deactivate`:

1. **Check** if `.flow-state` exists
   - If not, inform user: "No active plan."
   - If yes, read it and show which plan was active

2. **Remove** `.flow-state`

3. **Confirm**: "Plan deactivated. Hooks are now silent."

## Notes

- This does NOT archive the plan — it stays in `docs/plans/`
- Use `/flow:complete` instead if the plan is finished and should be archived
- Use `/flow:activate` to re-activate later

---
description: "Archive the active plan to docs/plans/completed/, update TASKS.md, clear .flow-state"
---

# /flow:complete

Mark the active plan as done. Archives it and updates task tracking.

## Behavior

When the user invokes `/flow:complete`:

1. **Check `.flow-state`**:
   - If no active plan, inform user and exit
   - Read the active plan path

2. **Validate completion**:
   - Read the plan file
   - Check if all phases are marked complete
   - If incomplete phases remain, warn the user and ask for confirmation:
     "Plan has X incomplete phases. Archive anyway?"

3. **Archive the plan**:
   ```bash
   mkdir -p docs/plans/completed
   mv <plan-path> docs/plans/completed/
   ```

4. **Update TASKS.md**:
   - Find the task referencing this plan path
   - Move it to the `## Completed` section
   - Mark the checkbox: `- [x]`
   - Update the path reference to `docs/plans/completed/<filename>`

5. **Remove `.flow-state`**

6. **Confirm** with summary:
   - What was archived and where
   - Updated TASKS.md entry
   - "Hooks are now silent. Run /flow:activate to start the next plan."

## Notes

- If TASKS.md doesn't reference the plan, just archive the plan file without modifying TASKS.md
- The plan file is moved, not copied — keeps docs/plans/ clean

End session with summary and outcome tracking.

**Usage:** `/workflow:session-finish`

## Session Selection

1. Bound session takes priority
2. Auto-select if exactly 1 active
3. Error if 0 or multiple

## Summary Content

Append to session file:

```markdown
---

## TL;DR
<!-- 1-2 sentence summary of what was accomplished -->

## Outcome: [SUCCEEDED | PARTIAL | FAILED]

## Ended: YYYY-MM-DD HH:MM (Xh duration)

### Done
- [What was completed]

### Git
- Files: X added, Y modified, Z deleted

### Next
- [What remains]
```

**Important:**
- Generate a concise 1-2 sentence TL;DR
- Track outcome for learning:
  - **SUCCEEDED**: Goal fully achieved
  - **PARTIAL**: Some progress, work remains
  - **FAILED**: Blocked or abandoned

## Task Update

If session was linked to a TASKS.md task:
1. Ask: "Mark task complete? (y/n)"
2. If yes: Change `- [ ]` to `- [x]`, remove annotation, move to Completed section
3. If no: Remove annotation, task stays in Now

## Task File Archiving

If `docs/tasks/{task-slug}.md` exists:

1. **Add completion header** to the TOP of the file:
   ```markdown
   ---
   ## Completed: YYYY-MM-DD

   ### Summary
   [1-2 sentence summary from session TL;DR]

   ### Key Outcomes
   - [From session Done list]
   ---
   ```

2. **Move file** to `docs/tasks/completed/`

3. **Confirm**: `✓ Archived to docs/tasks/completed/{task-slug}.md`

## Ledger Maintenance

Maintain `.claude/memory/ledger.md`:

1. **Clear session-specific fields:**
   - Reset Current Goal
   - Clear Active Files
   - Clear Active Task section

2. **Preserve persistent content:**
   - Keep Recent Decisions (max 5, rotate oldest to archive)
   - Keep Proven Patterns (max 3)
   - Keep Constraints, Quick Reference

3. **Scan session for suggestions:**
   - Look for: "decided:", "conclusion:", "chose X over Y"
   - Look for: explicit metrics with context
   - Present suggestions: "Potential ledger additions:"

4. **Add TL;DR to archive:** Append session summary to `.claude/memory/archive.md`

## Cleanup

1. Remove from `.claude/sessions/.active-sessions`
2. Update TASKS.md
3. Clear binding: **SESSION ENDED: [name]**

## Confirmation

- Session saved with outcome
- Task status updated (if linked)
- Ledger updated
- Suggest next task from TASKS.md

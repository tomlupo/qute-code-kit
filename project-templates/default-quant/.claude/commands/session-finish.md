End session with summary.

**Usage:** `/session-finish`

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

## Ended: YYYY-MM-DD HH:MM (Xh duration)

### Done
- [What was completed]

### Git
- Files: X added, Y modified, Z deleted

### Next
- [What remains]
```

**Important:** Generate a concise 1-2 sentence TL;DR summarizing the session's main accomplishment.

## Task Update

If session was linked to a TASKS.md task:
1. Ask: "Mark task complete? (y/n)"
2. If yes: Change `- [ ]` to `- [x]`, remove `` `@session:name` ``, move to Completed section
3. If no: Remove `` `@session:name` `` annotation, task stays in Now

## Context Maintenance

Before cleanup, maintain `.claude/memory/context.md`:

1. **Review existing content:**
   - Is Current Focus still accurate? Update if needed
   - Any decisions now obsolete? Remove or move to archive.md
   - Any patterns disproven? Remove

2. **Scan session for suggestions** (conservative extraction):
   - Look for: "decided:", "conclusion:", "chose X over Y"
   - Look for: explicit metrics with context (e.g., "IR 0.48 is baseline")
   - Look for: "pattern:", "consistently" (only if appears 3+ times)
   - Ignore: general progress notes, todos, file change logs

3. **Present suggestions** (if found):
   ```
   Potential context.md additions:

   Key Decisions:
   - [extracted decision] (YYYY-MM-DD)

   Patterns (only if validated 3+ times):
   - [extracted pattern]

   Add, edit, or skip?
   ```

4. **If no suggestions found:** Ask "Anything to add to context.md?"

5. **Enforce limits when adding:**
   - Current Focus: max 2 items
   - Key Decisions: max 5 (rotate oldest to archive.md)
   - Proven Patterns: max 3 (rotate oldest to archive.md)
   - Always add date: `- New decision (YYYY-MM-DD)`

6. **If over 50 lines:** Move oldest items to `.claude/memory/archive.md`

7. **Add TL;DR to archive:** Append session TL;DR to archive.md Session Summaries section

## Cleanup

1. Remove from `.claude/sessions/.active-sessions`
2. Update TASKS.md (remove `@session:name` annotation or complete task)
3. Clear binding:
> **SESSION ENDED: [name]**

## Confirmation

- Session saved
- Task status updated (if linked)
- Context.md updated (if changes made)
- Suggest next task from TASKS.md

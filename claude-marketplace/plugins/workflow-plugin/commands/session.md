Start a new session OR bind to an existing one.

**Usage:** `/workflow:session [name] [--create-task]`

**Flags:**
- `--create-task`: If no matching task found in TASKS.md, create a new task in Now section

## Behavior

**With name argument:**
1. Check `.claude/sessions/.active-sessions` for existing session matching `[name]`
2. If found → **bind** to it
3. If not found → **create** new session
4. If `--create-task` flag is present and no matching task found → create task in TASKS.md

**Without argument (Session Picker):**
1. Read TASKS.md Now section
2. Read `.active-sessions` for any active
3. Display numbered picker:
```
Sessions:
[1] Feature Selection Pipeline (Now)
[2] Test assessment framework (Now)
[3] tactical-pipeline (active)

Enter number or type new name: _
```
4. If number selected: bind to that task/session
5. If text entered: create new session with that name

## Creating New Session

1. Create `.claude/sessions/YYYY-MM-DD-HHMM-[name].md`:
```markdown
# Session: [name]
Started: YYYY-MM-DD HH:MM
Agent: [claude|codex|cursor|gemini]
Task: [matching task from TASKS.md if found]

## Progress
```

2. Add to `.claude/sessions/.active-sessions`

3. **Link to TASKS.md** (if task matches or `--create-task` flag):
   - Find task in TASKS.md matching session name
   - **If match found:** Add `` `@session:name` `` annotation to end of task line
   - **If no match and `--create-task` flag:** Create new task in Now section
   - **If no match and no flag:** Session created without task link

4. Set binding:
> **BOUND: [session-name]**

## Load Project Context

After creating/binding session, load context in priority order:

1. **Check for recent handoff** in `.claude/handoffs/`:
   - If handoff exists < 24h old → load and display it
   - Display: "Resuming from handoff: YYYY-MM-DD HH:MM"

2. **Always load ledger** from `.claude/memory/ledger.md`:
   - Display current goal, active files, recent decisions
   - Note: Do NOT read `archive.md` (cold storage - only on explicit request)

3. **Load active session** file if binding to existing

## Load Task Documentation

After loading context, check for task documentation in `docs/tasks/`:

1. **Convert session name to slug**: lowercase, spaces/underscores → hyphens
2. **Check `docs/tasks/{slug}.md`**
3. **If found**, display: `📋 Task doc: docs/tasks/{slug}.md`

## Confirmation

- Show session name
- Show linked task (if any)
- Show project context summary
- Remind: `/workflow:session-update`, `/workflow:session-finish`

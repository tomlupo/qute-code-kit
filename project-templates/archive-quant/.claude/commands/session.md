Start a new session OR bind to an existing one.

**Usage:** `/session [name] [--create-task]`

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
   - **If no match and `--create-task` flag:**
     - Create new task in Now section: `- [ ] [name] \`@session:name\``
     - Use session name as task name (user can edit later if needed)
   - **If no match and no flag:** Session created without task link (Task field left empty)
   - Example: `- [ ] My task \`@session:my-session\``

4. Set binding:
> **BOUND: [session-name]**

## Task Linking

**Default behavior:** Sessions only link to existing tasks. They do not create new tasks unless `--create-task` flag is used.

**When session name matches a task in TASKS.md:**
- Session file records the task
- TASKS.md shows `` `@session:name` `` annotation on the task line
- Other agents can grep for `@session:` to find bound tasks
- `/session-finish` removes annotation or completes task

**When session name does NOT match any task:**

*Without `--create-task` flag (default):*
- Session is created successfully
- Task field in session file is empty/omitted
- No changes to TASKS.md
- User can manually add task to TASKS.md later if needed

*With `--create-task` flag:*
- Session is created successfully
- New task created in TASKS.md Now section: `- [ ] [session-name] \`@session:name\``
- Task field in session file records the newly created task
- Task is immediately linked and bound

## Load Project Context

After creating/binding session, load project context:
1. Read `.claude/memory/context.md`
2. Display contents to establish project state
3. Note: Do NOT read `archive.md` (cold storage - only on explicit user request)

## Confirmation

- Show session name
- Show linked task (if any)
- Show project context summary
- If task was created: "Created new task in TASKS.md"
- Remind: `/session-update`, `/session-finish`

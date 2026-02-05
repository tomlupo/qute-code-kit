# /session-persistence:load

Load a previous session's context into the current conversation.

## Behavior

1. **If no argument provided**: read `~/.claude/sessions/` and load the most recent `.tmp` file

2. **If a filename or date is provided**: find and load the matching session file

3. **Read the session file** and report:
   - Session title and date
   - In-progress items (as a task list)
   - Notes for this session
   - Files listed under "Context to Load" — read each one to bring them into context

4. **Summarize** what was loaded:
   ```
   Loaded session: my-project (2026-02-04)
   - 2 items in progress
   - 1 note for this session
   - 3 files loaded into context
   ```

## Arguments

- `[session]` - (Optional) Session filename, date (YYYY-MM-DD), or partial match. If omitted, loads the most recent session.

## Example

```
/session-persistence:load

Loaded session: my-project (2026-02-04)

In Progress:
- [ ] Implement auth middleware
- [ ] Add rate limiting tests

Notes:
- Check edge case where token expires mid-request

Context loaded:
- src/middleware/auth.ts
- src/tests/rate-limit.test.ts
- src/config/security.ts
```

```
/session-persistence:load 2026-02-01

Loaded session: other-project (2026-02-01)
...
```

# /session-persistence:list

List saved sessions from previous Claude conversations.

## Behavior

1. **Read the sessions directory** at `~/.claude/sessions/`

2. **List all `.tmp` files**, sorted by date (most recent first)

3. **Parse each file** and display a table:

   | Date | Title | In Progress | Notes |
   |------|-------|-------------|-------|
   | 2026-02-04 | project-name | 3 items | Remember edge case X |
   | 2026-02-03 | project-name | 0 items | Completed refactor |

4. **Show the last 10 sessions** by default

5. If a number is provided as an argument (e.g., `/session-persistence:list 20`), show that many sessions instead

## Arguments

- `[count]` - (Optional) Number of sessions to display (default: 10)

## Example

```
/session-persistence:list

Recent Sessions (last 10):

| Date       | Title        | In Progress | Notes                    |
|------------|--------------|-------------|--------------------------|
| 2026-02-04 | my-project   | 2 items     | Check auth edge case     |
| 2026-02-03 | my-project   | 0 items     | Refactor complete        |
| 2026-02-01 | other-proj   | 1 item      | Needs test coverage      |
```

Add progress notes to the active session.

**Usage:** `/workflow:session-update [notes]`

## Session Selection

1. If conversation is bound → use bound session
2. If 1 active session → use it automatically
3. If 0 active → error: "No active session. Use `/workflow:session [name]` to start."
4. If multiple active → error: "Multiple sessions. Use `/workflow:session [name]` to bind first."

## Update Format

Append to session file:

```markdown
### [HH:MM] [brief summary]
[user's notes or auto-summary of recent work]

**Changes:** [files modified since last update]
```

Keep it brief. User controls detail level.

## Confirmation

Just confirm: `Updated [session-name]`

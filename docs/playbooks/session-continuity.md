# Session Continuity

> Clean transitions between Claude Code sessions without losing context.

## Components

| Component | Source | Purpose |
|-----------|--------|---------|
| `/handoff` | qute-essentials | Create structured handoff at session end |
| `/pickup` | qute-essentials | Load latest handoff at session start, audit ADR health |
| `/decision` | qute-essentials | Record ADRs — handoff auto-links to ones touched this session |
| `claude -c` | Built-in | Quick continue (last session, no structured context) |
| TASKS.md | work-organization rule | Track Now/Next/Later/Done across sessions |

## When to Use

- Ending a long session with work in progress
- Context window getting large (sluggish responses, repetition)
- Switching between projects or tasks
- Handing off to a fresh session after `/compact`

## Steps

### Ending a session

**Option A: Quick continue later**

Just use `claude -c` next time. Built-in, no setup needed. Works for simple continuations.

**Option B: Structured handoff**

When the session has important context that `claude -c` might lose:

```
/handoff "finishing the API endpoints"
```

This creates `.claude/handoffs/YYYY-MM-DD-slug.md` with:
- What was accomplished
- Key decisions and rationale
- Git state (branch, modified files)
- Blockers requiring user action
- Specific next steps

### Starting a new session

**Structured resume (recommended):**

```
/pickup
```

Loads the latest handoff, verifies referenced ADRs are still Accepted (not superseded), summarises TASKS.md Now/Next, and flags stale handoffs. Read-only — nothing is modified.

**Quick continue:**

```bash
claude -c   # resumes last conversation, no handoff processing
```

**Manual:**

```
Read .claude/handoffs/2026-03-09-api-endpoints.md and continue
```

### Tracking work across sessions

Keep `TASKS.md` updated:

```markdown
## Now
- [ ] Finish API rate limiting

## Next
- [ ] Add integration tests
- [ ] Update API docs

## Later
- [ ] Caching layer for /search endpoint

## Completed
- [x] Basic CRUD endpoints
- [x] Authentication middleware
```

Move items between sections as priorities change. Keep Now to 1-3 items.

## Tips

- `/pickup` → `/handoff` is the full structured loop — use it for multi-day work
- `claude -c` is better for "I just need to keep going right now"
- When a significant design choice is made mid-session, call `/decision` immediately — `/handoff` will auto-link it
- Update TASKS.md at natural breakpoints, not after every change
- For ideas that need detail, create `docs/ideas/YYYY-MM-DD-slug.md` and link from Later

## See also

- `workflow-qute.md` — full dev session lifecycle using qute-essentials end-to-end

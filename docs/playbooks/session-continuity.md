# Session Continuity

> Clean transitions between Claude Code sessions without losing context.

## Components

| Component | Source | Purpose |
|-----------|--------|---------|
| /handoff | `handoff` skill (qute-essentials plugin) | Create structured handoff document |
| `claude -c` | Built-in | Continue last session |
| TASKS.md | Convention (work-organization rule) | Track what's Now/Next/Later/Done |

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

**From handoff:**

```
Read .claude/handoffs/2026-03-09-api-endpoints.md and continue
```

**From TASKS.md:**

```
Read TASKS.md and pick up the next item from Now
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

- `/handoff` is better than `claude -c` when you've made decisions that need preserving
- `claude -c` is better for "I just need to keep going where I left off"
- Update TASKS.md at natural breakpoints, not after every change
- For ideas that need detail, create `docs/ideas/YYYY-MM-DD-slug.md` and link from Later

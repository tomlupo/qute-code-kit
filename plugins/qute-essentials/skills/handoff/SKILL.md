---
name: handoff
description: >-
  End-of-session writer. Diffs the session, identifies the TASKS.md row,
  writes a structured handoff with mandatory `task:` frontmatter, updates
  the TASKS.md row in the same commit, lands on dev. Use when user says
  "handoff", "save state", "wrap up", "session end".
argument-hint: "[alias-or-slug]"
---

# /handoff

Captures a session into `.claude/handoffs/{date}-{slug}.md`, links it back to TASKS.md::Now, prints commands to commit on dev.

Per DR-010 the skill is structured: mandatory `task:` frontmatter prevents orphan handoffs at birth. STATUS.md is no longer touched — it does not exist.

## When to use

- Session is wrapping up and another agent (or future you) will need to resume.
- User says "handoff", "save state", "wrap up", "session end", "record what we did".
- Long sessions (deep design, multi-day work). Skip for trivial single-edit sessions.

## Arguments

- `[alias-or-slug]` (optional) — names the TASKS.md row this handoff belongs to. If omitted, infer from current branch name; if ambiguous, ask.

## Behavior

### 1. Identify the task — mandatory

Resolution order:
1. **Explicit arg** — if `[alias-or-slug]` matches a TASKS.md::Now row (or its slug in a cited plan path), use it.
2. **Branch inference** — if current branch is `feat/{alias}-{slug}` or `research/{alias}-{slug}`, search Now rows for `{alias}-{slug}` substring. Exactly one match → use it.
3. **Ask the user** — single prompt listing TASKS.md::Now row titles. User picks one, OR types `__exploratory__` for sessions with no current row.

Refuse to proceed with no resolution. The `task:` field is the orphan-prevention anchor; missing it would defeat the design.

### 2. Diff the session — fast

```bash
git diff --stat HEAD~5 2>/dev/null  # paths + line counts only; cheap
```

Files touched go in `files_touched:`. If >20 files, list directories not files. Don't read full diffs unless the next step explicitly needs them — handoff describes outcomes, not contents.

### 3. Synthesize handoff body — keep it terse

Required:
- **Summary** (2-4 sentences max): what was tried, the outcome.
- **Next steps** (numbered list): mirrors the `next:` frontmatter list, same order.

Optional (only when there's something non-obvious worth recording):
- **Decisions**: non-trivial choices the resumer needs to know.
- **Risks / open questions**: blockers or unknowns.

Skip the optional sections when the work was straightforward — they exist to capture *non-obvious* state, not to fill a template.

### 4. Write the handoff file

Path: `.claude/handoffs/{YYYY-MM-DD}-{slug}.md` where `{slug}` matches the TASKS.md row's slug (or the user-provided arg).

Mandatory frontmatter:

```yaml
---
task: <slug>                         # or __exploratory__
date: YYYY-MM-DD
session_branch: <branch>
status: in-progress | concluded | abandoned
files_touched:
  - path/to/file
  - ...
next:
  - action: "Human-readable next step"
    cmd: "optional shell command"     # if present, /pickup --continue can run it
    file: "optional file the action targets"
  - action: "..."
---
```

`status:` semantics:
- `in-progress` — task is ongoing; row stays in `## Now`.
- `concluded` — work is done; this skill moves the TASKS.md row to `## Completed`.
- `abandoned` — tried, didn't work — handoff stays for history but is removed from `→ handoff:` citation in TASKS.md.

### 5. Update TASKS.md row (same commit)

- Replace any prior `→ handoff: ...` line with the new filename.
- Update or insert a `Latest:` one-liner under the row title:
  `Latest: YYYY-MM-DD — <one-line status>`.
- If `status: concluded`: move the row to `## Completed`.
- If `status: abandoned`: remove `→ handoff:` line; row stays where it is.

### 6. Commit on dev — print commands, do not auto-run

The dm-evo `pre-commit` hook (DR-010) blocks TASKS.md edits on `feat/*` and `research/*` branches. The skill does NOT auto-switch branches across worktrees — the user runs the commands in the canonical clone:

```
# In the canonical dev clone (not a worktree):
cd $(git rev-parse --show-toplevel | sed 's|/.worktrees/[^/]*$||')
git checkout dev
git pull --rebase
git add .claude/handoffs/{file} TASKS.md
git commit -m "chore(handoff): {slug} — {one-line summary}"
git push
```

For `__exploratory__` handoffs: TASKS.md is not modified; only the handoff file is added.

### 7. Print one-line confirmation

```
Handoff: 2026-05-04-{slug}.md  ·  Task: {slug} ✓ linked  ·  Next: {next[0].action}
```

## What `/handoff` does NOT do

- Write to STATUS.md (DR-010 — file deleted).
- Auto-commit across worktrees (would require branch switching with potentially-dirty trees).
- Sweep old handoffs to archive — that's `/ship`'s job.
- Generate ADRs — that's `/decision`'s job.

## Notes on slug alignment

If a handoff describes work tracked by `docs/tasks/{slug}.md`, the handoff slug **matches the task slug**. Mechanical cross-ref: `/pickup` finds the latest handoff for a task by slug glob: `ls .claude/handoffs/*-{slug}.md | sort | tail -1`.

For exploratory sessions: handoff slug is freeform; `task: __exploratory__` keeps `/status` from flagging it as orphan.

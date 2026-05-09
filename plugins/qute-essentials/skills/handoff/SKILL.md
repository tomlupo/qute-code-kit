---
name: handoff
description: >-
  End-of-session writer. Diffs the session, identifies the task, writes a
  structured handoff with mandatory `task:` frontmatter, updates the
  TASKS.md row, auto-commits on the current branch. Use when user says
  "handoff", "save state", "wrap up", "session end".
argument-hint: "[alias-or-slug]"
---

# /handoff

Captures a session into `.claude/handoffs/{date}-{slug}.md` on the **current branch** with mandatory `task:` frontmatter, updates the TASKS.md row, auto-commits, pushes.

Drift-on-branches model: handoffs and TASKS.md updates live on whichever branch the work happened on. They reach `dev` via PR merge. `/status` scans across worktrees to surface in-flight state from any branch.

## When to use

- Session is wrapping up and another agent (or future you) will need to resume.
- User says "handoff", "save state", "wrap up", "session end", "record what we did".
- Long sessions (deep design, multi-day work). Skip for trivial single-edit sessions.

## Arguments

- `[alias-or-slug]` (optional) — names the task this handoff belongs to. If omitted, infer from current branch name; if ambiguous, ask.

## Behavior

### 1. Identify the task — mandatory

Resolution order:
1. **Explicit arg** — if `[alias-or-slug]` matches a TASKS.md row (Now or Later) or a `docs/tasks/{slug}.md` plan file, use it.
2. **Branch inference** — if current branch is `feat/{slug}` or `research/{slug}`, derive `{slug}` and verify it matches a plan file or Now row.
3. **Ask the user** — single prompt listing recent task slugs (from `docs/tasks/*.md` and TASKS.md::Now). User picks one, OR types `__exploratory__` for sessions with no current row.

Refuse to proceed with no resolution. The `task:` field is the orphan-prevention anchor.

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

Path: `.claude/handoffs/{YYYY-MM-DD}-{slug}.md` (in the **current** worktree, not main checkout).

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

For `__exploratory__`: TASKS.md is not touched; only the handoff file is added.

### 6. Auto-commit on current branch

```bash
git add .claude/handoffs/{file} [TASKS.md]
git commit -m "chore(handoff): {slug} — {one-line summary}"
git push 2>/dev/null || echo "WARN: push failed; handoff committed locally"
```

The commit lands on whichever branch you're on. When that branch eventually merges to `dev` (via PR), the handoff + TASKS.md updates flow into dev's history naturally.

**No cross-tree dance.** Don't try to commit on dev from a worktree — the worktree's branch IS the right home for this commit. Cross-branch state surfacing happens in `/status`, not at handoff time.

**Pre-flight check:** if the current worktree has unstaged edits to `.claude/handoffs/` or `TASKS.md` (other than the ones this skill is making), refuse with: "Pre-existing unstaged edits to {path} — commit/stash first, then re-run /handoff."

**Push failure:** leave the local commit, surface the error. Don't retry silently.

### 7. Print one-line confirmation

```
Handoff: 2026-05-04-{slug}.md  ·  Task: {slug} ✓  ·  Branch: {branch}  ·  Next: {next[0].action}
```

## What `/handoff` does NOT do

- Auto-switch to dev or any other branch — the handoff lives on the current branch.
- Write to multiple branches — single commit, single branch.
- Sweep old handoffs to archive — that's `/ship`'s job.
- Generate ADRs — that's `/decision`'s job.
- Resolve which worktree is "canonical" — there isn't one under the drift-on-branches model. `/status` does the cross-branch view.

## Notes on slug alignment

If a handoff describes work tracked by `docs/tasks/{slug}.md`, the handoff slug **matches the task slug**. Mechanical cross-ref: `/status` finds handoffs by walking `git worktree list` and reading each tree's `.claude/handoffs/`.

For exploratory sessions: handoff slug is freeform; `task: __exploratory__` keeps `/status` from flagging it as orphan.

## Filename collision (rare)

Two branches handing off on the same day with the same slug produce identical filenames. When both eventually merge to dev, git sees an add/add conflict. Rare in solo work (different tasks ≠ same slug); resolve manually if it happens. The cleaner upstream fix is to keep one task slug = one branch in flight at a time.

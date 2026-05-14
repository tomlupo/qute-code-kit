---
name: handoff
description: Compact the current conversation into a handoff document so a fresh agent (or future-you) can pick up. Writes to ~/.claude/handoffs/. Use when user says "handoff", "save state", "wrap up", "session end".
argument-hint: "[focus]"
---

# /handoff

Write a short summary of the current session to `~/.claude/handoffs/{YYYY-MM-DD}-{slug}.md` so the next session can resume cold.

- **Path:** `~/.claude/handoffs/{YYYY-MM-DD}-{slug}.md` (machine-local, NOT committed).
- **Slug:** derive from current repo name + branch, or from the optional `[focus]` arg if given.
- **Read before write** — if a file at the target path already exists, read it and merge instead of overwriting.

Write a short markdown doc with:

- **Repo + branch + date** in the first line, so the resumer knows where it lived.
- **Summary** — 2-4 sentences: what was tried, the outcome.
- **Next** — numbered list of concrete next actions.
- **References** — links/paths to PRs, issues, ADRs, docs, plan files — *don't duplicate their content*. If a Paperclip issue is checked out by an agent in this repo, mention its identifier (e.g. `TOM-12`).

Optional:
- **Decisions** — only when there's a non-obvious choice the resumer needs to know.
- **Open questions** — only when there's a blocker or unknown.

Skip the optional sections when the work was straightforward.

If `[focus]` is given, treat it as a description of what the next session will focus on and tailor the doc accordingly (e.g. *"continue debugging the extraction NAV mismatch"*).

## What `/handoff` does NOT do

- No frontmatter requirement, no `task:` field.
- No `git commit`, no `git push`. Handoffs are machine-local.
- No TASKS.md / Paperclip mutation. Use `/issue` to create work items; `/handoff` records session state.
- Doesn't sweep old handoffs. Manage retention yourself (`rm ~/.claude/handoffs/*-old.md`) or live with the directory growing.

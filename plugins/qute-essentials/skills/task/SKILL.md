---
name: task
description: Add or complete a task in this repo's tracker. Tiered, auto-detecting — manages a plain TASKS.md checklist by default (Tier 1), and uses GitHub Issues via `gh` once a repo graduates (Tier 2). Use when the user says "new task", "add task", "create issue", "track this", "mark done", "close that", or pastes work that needs a home.
argument-hint: "<title> [body...]  |  close <ref> [comment...]  |  migrate  |  decline"
---

# /task

Write half of the tiered task engine. Adds or completes a task in whichever
store this repo uses, sharing one engine (`pulse.sh`) with `/board`. No backend
ceremony — give it a title; it routes for you.

## When to use

- "new task X", "add to backlog", "track this", "create issue"
- "mark done", "close <ref>", "complete that"
- After a discussion that produced a unit of work

Do NOT invoke for:
- Viewing the backlog — use `/board`
- Pure git state / session context — use `/repo-status`, `/pickup`

## The tiered model (generic, project-agnostic)

This skill is part of the public qute-essentials plugin, so it stays generic —
two tiers, nothing project-specific:

- **Tier 1 (default):** `TASKS.md` in the repo root — a plain markdown
  checklist. Zero setup. Used for small/new/just-init repos, or any repo with
  no GitHub remote. The skill manages the file directly.
- **Tier 2 (graduate):** plain **GitHub Issues** via the `gh` CLI. A repo earns
  this once BOTH hold: (a) it has a GitHub remote `gh` can reach, AND (b) the
  list outgrows a flat file — open-task count past the threshold (default 12,
  tunable), or a task needs what a checklist can't give: labels, assignees,
  sub-issues, or durability across sessions.

A repo has exactly **one live store** — TASKS.md OR Issues, never both. After
migration TASKS.md becomes a tombstone pointing at the Issues tab; the engine
reads that tombstone to know the live store is now GitHub.

## Behavior

Add (auto-routes to the active store when `--to` is omitted):

```bash
bash "$CLAUDE_PLUGIN_ROOT/scripts/tasks/pulse.sh" add "<title>" [body...]
bash "$CLAUDE_PLUGIN_ROOT/scripts/tasks/pulse.sh" add --to <github|tasks-md> "<title>" [body...]
```

Complete:

```bash
bash "$CLAUDE_PLUGIN_ROOT/scripts/tasks/pulse.sh" close <ref> [comment...]
bash "$CLAUDE_PLUGIN_ROOT/scripts/tasks/pulse.sh" close --in github <number> [comment...]
```

Print stdout verbatim.

- **tasks-md add:** creates `TASKS.md` on first use, appends
  `- [ ] **<title>** - <body>`.
- **tasks-md close:** there's no API — check the box directly in the file
  (`- [ ]` → `- [x]`); the engine reminds you of this.
- **github add:** `gh issue create` → prints the new issue URL.
- **github close:** `gh issue close <number>` (optionally with a comment).

## Migration (Tier 1 → Tier 2)

When the active store is TASKS.md, the repo is on GitHub, and the open count
crosses the threshold, `pulse.sh` appends a **one-time proposal** to its output.
Surface it to the user. If they accept:

```bash
bash "$CLAUDE_PLUGIN_ROOT/scripts/tasks/pulse.sh" migrate
```

This is mechanical: each open `- [ ]` item becomes a `gh issue create`, then
TASKS.md is replaced with a short tombstone pointing at the Issues tab. From
then on `/task` and `/board` route to Issues automatically.

If the user prefers to stay local, silence the nag for good:

```bash
bash "$CLAUDE_PLUGIN_ROOT/scripts/tasks/pulse.sh" decline
```

This writes a `keep-local` marker (an HTML comment) into TASKS.md so the
proposal never fires again for this repo. Respect it.

You may also propose migration **judgement-first** — without waiting for the
count — when a task the user is adding clearly needs labels, assignees, or
sub-issues. That's a call you make from the task text, not the counter.

## Routing precedence (active store)

1. `## Task source: <github|tasks-md>` in CLAUDE.md → explicit override.
2. TASKS.md present and tombstoned → **github**.
3. TASKS.md present (live) → **tasks-md**.
4. No TASKS.md, but a GitHub remote with ≥1 open issue → **github**.
5. Otherwise → **tasks-md** (Tier-1 default; `add` creates the file).

## Tuning

- Threshold default is **12** open items. Override with the
  `QUTE_TASKS_THRESHOLD` env var, or a `## Task threshold: <N>` line in
  CLAUDE.md.

One store per call — no silent mirroring.

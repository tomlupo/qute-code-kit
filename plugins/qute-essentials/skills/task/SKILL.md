---
name: task
description: Add or complete a task in this repo's tracker. Tiered, auto-detecting — manages a plain TASKS.md checklist by default (Tier 1), and uses GitHub Issues via `gh` once a repo graduates (Tier 2). Use when the user says "new task", "add task", "create issue", "track this", "mark done", "close that", or pastes work that needs a home.
argument-hint: "<title> [body...]  |  close <ref> [comment...]  |  migrate  |  decline"
---

# /task

Write half of the tiered task engine. Adds or completes a task in whichever
store this repo uses, sharing one engine (`pulse.sh`) with `/repo-status`. No backend
ceremony — give it a title; it routes for you.

## When to use

- "new task X", "add to backlog", "track this", "create issue"
- "mark done", "close <ref>", "complete that"
- After a discussion that produced a unit of work

Do NOT invoke for:
- Viewing the backlog — use `/repo-status` (its Open tasks section)
- Pure git state / session context — use `/repo-status`, `/pickup`

## The tiered model (generic, project-agnostic)

This skill is part of the public qute-essentials plugin, so it stays generic —
tiers, nothing project-specific:

- **Tier 1 (default):** `TASKS.md` in the repo root — a plain markdown
  checklist. Zero setup. Used for small/new/just-init repos, or any repo with
  no GitHub remote. The skill manages the file directly.
- **Tier 2 (graduate):** plain **GitHub Issues** via the `gh` CLI. A repo earns
  this once BOTH hold: (a) it has a GitHub remote `gh` can reach, AND (b) the
  list outgrows a flat file — open-task count past the threshold (default 12,
  tunable), or a task needs what a checklist can't give: labels, assignees,
  sub-issues, or durability across sessions.
- **Tier 3 (task source = Linear):** declared via
  `docs/agents/issue-tracker.md` (see binding below). **Linear is the task
  source** — all work items live there (Jimek monitors it for assigned tasks).
  **GitHub Issues track issues, not tasks**: bugs/defects/debt records attached
  to the code; an issue becomes work only when a Linear task references it
  ("fix issue #X") — never treat the Issues list as a queue. The engine has a
  native Linear backend (`linear.py`, stdlib-only): auth via `LINEAR_API_KEY`,
  team bound by the `<!-- qute-tracker: linear team=ABC -->` marker in
  `docs/agents/issue-tracker.md`. `add`/`close`/`report` route to Linear
  automatically; keep `--to github` for filing/closing issue records.
  **Orchestrated workspaces** (Jimek / Symphony-Elixir style): the API key is
  held host-side and stripped from the agent env by design — use the
  orchestrator's advertised `linear` tool for state changes/comments; the qute
  backend is the interactive/local path.

A repo has exactly **one live task source** — TASKS.md OR GitHub Issues OR
Linear (where Issues are then only an issue record, not a queue), never
parallel boards. After Tier 1→2 migration TASKS.md
becomes a tombstone pointing at the Issues tab; the engine reads that tombstone
to know the live store is now GitHub.

## Tracker binding (`docs/agents/issue-tracker.md`)

If the repo has `docs/agents/issue-tracker.md` (Matt Pocock's
`setup-matt-pocock-skills` convention, also stamped by `/adopt-matt-workflow`),
that file **wins over auto-detection**. The engine routes on its machine-readable
marker — `<!-- qute-tracker: <linear|github|tasks-md> [team=ABC] -->` — and the
prose declares auth notes and workflow specifics for agents. Template:
`templates/docs/agents-issue-tracker.md` in qute-code-kit. Ideas never live in the tree (`RESEARCH_IDEAS.md`,
`docs/tasks/`, TODO lists in handoffs) — they go to the declared store.

## Behavior

Add (auto-routes to the active store when `--to` is omitted):

```bash
bash "$CLAUDE_PLUGIN_ROOT/scripts/tasks/pulse.sh" add "<title>" [body...]
bash "$CLAUDE_PLUGIN_ROOT/scripts/tasks/pulse.sh" add --to <github|tasks-md> "<title>" [body...]
bash "$CLAUDE_PLUGIN_ROOT/scripts/tasks/pulse.sh" add --type <t> [--structure <s>] "<title>" [body...]
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
- **github add:** `gh issue create` → prints the new issue URL. With
  `--type`/`--structure` it also applies the label taxonomy after create
  (see below). No flags → no labels (back-compat).
- **github close:** `gh issue close <number>` (optionally with a comment). The
  comment is posted as-is — no attribution prefix (see "Agent attribution" below).

## Label taxonomy (TYPE + STRUCTURE only)

The `github` backend applies labels from `config/task-taxonomy.json`, which has
**exactly two dimensions** (per obsidian-vaults#177):

- **TYPE** (pick one): `feature`, `fix`, `infra`, `refactor`, `research`,
  `docs`, `chore` — via `--type <t>`.
- **STRUCTURE** (pick one, optional): `epic`, `task` — via `--structure <s>`.

Each value carries a hex color + description; labels are created (idempotently,
via `gh label create --force`) before being applied with `gh issue edit`.

`--type`/`--structure` are **GitHub-label flags** — they require the `github`
backend. On the Tier 1 `tasks-md` checklist they have no meaning, so `add`
rejects them with a hint to pass `--to github` rather than silently dropping the
classification.

**Deliberately NOT label dimensions:** status, priority, and owner. `owner` is
the board's **Agent** field; `status`/`priority` are board fields managed via
**gh-track**. Keeping them off issue labels avoids two sources of truth — adding
a status/priority/owner label is a design violation, not a missing feature.

```bash
# feature epic (taxonomy flags require the github backend)
pulse.sh add --to github --type feature --structure epic "Payments v2"
# bug fix, no structure
pulse.sh add --to github --type fix "Login 500 on empty password"
```

## Agent attribution

The `task` verb does **not** add an `[agent:<name>]` comment prefix. Attribution
is owned by **gh-track** (the fleet board verb, obsidian-vaults#177): agent
GitHub writes flow through gh-track, which applies the prefix. The `task` verb is
a general consumer tool — humans included — so it stays attribution-neutral
rather than stamping a misleading `[agent:<cwd>]` on non-agent sessions.

## Migration (Tier 1 → Tier 2)

When the active store is TASKS.md, the repo is on GitHub, and the open count
crosses the threshold, `pulse.sh` appends a **one-time proposal** to its output.
Surface it to the user. If they accept:

```bash
bash "$CLAUDE_PLUGIN_ROOT/scripts/tasks/pulse.sh" migrate
```

This is mechanical: each open `- [ ]` item becomes a `gh issue create`, then
TASKS.md is replaced with a short tombstone pointing at the Issues tab. From
then on `/task` and `/repo-status` route to Issues automatically.

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

0. `docs/agents/issue-tracker.md` present → its declaration wins (may be
   `linear`, in which case route per that file, not `pulse.sh`).
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

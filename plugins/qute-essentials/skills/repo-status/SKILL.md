---
name: repo-status
description: Pure git/worktree dashboard. Walks `git worktree list`, surfaces latest release, per-subsystem last change (when CLAUDE.md has a Subsystems table), orphan stashes, and worktrees with merged PRs. Pure bash, no LLM, sub-second. Use when user says "status", "where are we", "what branches are live", "what's stale".
argument-hint: "[alias]"
---

# /repo-status

Sub-second git/worktree dashboard **plus a read-only open-tasks glance**. **No LLM body** — exec the bash script and print stdout verbatim.

Scope: git state + a read of this repo's open task list (folded in from the retired `/board` skill — auto-detects TASKS.md Tier 1 vs GitHub Issues Tier 2, via the shared `pulse.sh` engine). **Mutating tasks lives in `/task`** (add/close). **Session state lives in `~/.claude/handoffs/`** (use `/pickup` to load latest).

## When to use

- Mid-session: "what branches are live across this repo?"
- Before changing something: "is there an in-flight worktree on this?"
- Cleanup pass: orphan stashes, merged-PR worktrees ready to prune
- User says "status", "where are we", or names a subsystem (filters subsystem table)
- "what's on the board", "show tasks", "what's open" — the open-tasks read now lives here

Do NOT invoke for:
- Adding or closing a task — use `/task`
- Loading session context — use `/pickup`
- Writing session state — use `/handoff`

## Arguments

- `[alias]` (optional) — restrict subsystem-changes section to a single subsystem (`taa`, `selection`, etc.). Worktree list always shows everything.

## Behavior

Single bash invocation:

```bash
bash "$CLAUDE_PLUGIN_ROOT/scripts/lifecycle/status.sh" $1
```

Fall back to skill-relative path if `$CLAUDE_PLUGIN_ROOT` is unset:

```bash
bash "$(dirname "$0")/../../scripts/lifecycle/status.sh" $1
```

Print stdout verbatim. Surface non-zero exit as a warning.

## Output anatomy

```
{project} @ {branch}{dirty?}  ·  {last commit}
Latest release: vX.Y.Z (YYYY-MM-DD)  ·  N commits ahead on dev

⚠ Orphan stashes (when present):
  stash@{N} → branch 'X' is deleted

⚠ Worktrees with merged PRs (when present, requires `gh`):
  some-name  [feat/x]  PR #123 merged

Subsystem    Last change                                        Active branch
  taa        2026-04-29 b12a6a0 docs(taa): mark v6/v7 super...  research/taa-v6
  selection  2026-05-08 089072d feat(fundsel): manual_pick ...  feat/selection-aum
  ...

Active worktrees:
  dm-evo                         [dev]
  dm-evo-taa-migration           [feat/taa-migration]

Open tasks:
  pulse · {project}  [store: tasks-md | github]
    open  L3   Wire up the retry backoff
    open  #42  Migrate config loader to pydantic
```

Empty sections are silently dropped. The Subsystems section only appears when CLAUDE.md has an `| Alias |` markdown table. The **Open tasks** section reads whichever store is live — a root `TASKS.md` checklist (Tier 1) or open GitHub Issues via `gh` (Tier 2) — via the shared `pulse.sh` engine; it is skipped silently when the store is empty or `pulse.sh` errors, and a migration proposal may append when a TASKS.md repo crosses the graduation threshold (route to `/task migrate`).

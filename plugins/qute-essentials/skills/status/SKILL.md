---
name: status
description: Cross-branch lifecycle dashboard. Walks `git worktree list` to surface in-flight handoffs + Now items from every active branch, plus latest release tag, per-subsystem last change, orphan-handoff warnings, and TASKS.md::Now row-size lint. Pure bash, no LLM, sub-second. Use when user says "status", "where are we", "what's live", "what's everyone working on", or names a subsystem.
argument-hint: "[alias]"
---

# /status

Sub-second cross-branch dashboard. **No LLM body** — exec the bash script and print stdout verbatim.

Drift-on-branches model: handoffs and TASKS.md edits live on the branch where the work happened (`feat/*`, `research/*`, or `dev`). They reach `dev` via PR merge. `/status` doesn't depend on dev being canonical — it walks `git worktree list` and reads each tree's filesystem directly.

## When to use

- Mid-session: "wait, what's actually in-flight across all my branches?"
- Before proposing a change: "is this already the way it works?"
- Resuming after time away: "where was I?"
- User says "status", "where are we", "what's live", or names a subsystem.

Do NOT invoke for:
- Loading handoff context into the LLM — use `/pickup` (this skill is read-only summary).
- Writing state — use `/handoff`.

## Arguments

- `[alias]` (optional) — restrict subsystem-changes section to a single subsystem (`taa`, `selection`, etc.). Worktree dashboard always shows everything.

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

The script reads:
- `$CLAUDE_PROJECT_DIR/CLAUDE.md` Subsystems table (alias + production paths from column 3)
- `git tag --list 'v*'` (latest release; single namespace)
- `git log --first-parent -1 -- {paths}` (last change per subsystem)
- `git worktree list` (every active worktree of this repo)
- Each worktree's `.claude/handoffs/*.md` (latest by mtime, frontmatter parsed for `status:` and `next[0].action`)
- Each worktree's `TASKS.md::Now`
- Each worktree's `docs/tasks/*.md` (slug list, for orphan-handoff cross-reference)

The skill MUST NOT call other skills, write files, or perform LLM synthesis.

## Output anatomy

```
{project} @ {branch}{dirty?}  ·  {last commit}
Latest release: vX.Y.Z (YYYY-MM-DD)  ·  N commits ahead on dev

Subsystem    Last change                                        Active branch
  taa        2026-04-29 b12a6a0 docs(taa): mark v6/v7 super...  research/taa-v6
  selection  2026-05-08 089072d feat(fundsel): manual_pick ...  feat/selection-aum
  saa        (research-only)                                    —
  ...

Active worktrees:
  dm-evo                         [dev]
    handoff: 2026-05-09-workflow-simplification.md · concluded · next: Push dm-evo dev to origin
  dm-evo-taa-migration           [feat/taa-migration]
    handoff: 2026-05-10-taa-migration.md · in-progress · next: Phase 1 audit
  dm-evo-fundsel-aum             [feat/fundsel-aum]
    handoff: 2026-05-08-fundsel-aum.md · in-progress · next: rebase + retest

Now (per branch):
  on dev:
    Selection pipeline rerun on new taxonomy (L1 sleeves + ALT umbrella)
    Q1 2026 fund holdings — full accuracy review across all providers
  on feat/taa-migration:
    Phase 1 audit + classify

Orphan handoffs:
  2026-05-04-some-handoff.md on feat/foo (task: foo — no plan, status: in-progress)
```

Sections that are empty (no orphans, no Now items, no subsystems registry, no row-size violations) are silently dropped.

## TASKS.md row-size lint

Per `work-organization.md::Row-size discipline`, ## Now entries should be terse — pointer-shape (header + → plan: + → handoff: + Latest: = 4 lines) when the task has a plan file, or 1-3 inline lines for small tasks without a plan. The lint walks each `### Title` block under ## Now (skipping blank lines) and flags entries with 5+ lines as candidates for promotion to `docs/tasks/{slug}.md`.

Lint applies to ## Now only. ## Next and ## Later are buffer queues where bullet-cluster entries (multiple short bullets under one `### Cluster name`) are legitimate organization, not drift.

## Notes on the cross-branch scan

- `git worktree list` returns every worktree of this repo, including the main checkout. Each entry's path points at a filesystem tree where the branch is currently checked out — reading `.claude/handoffs/` on that path gives the *current* state of that branch's handoffs.
- Same for TASKS.md: each worktree has its branch's view. Drift between branches is expected and informative.
- Orphan-handoff detection cross-references handoff `task:` against the **union of `docs/tasks/*.md` slugs across all worktrees** — a plan file in any worktree counts as a known task.

## Notes on parsing

YAML frontmatter is parsed by simple awk — first `---` block, top-level scalar fields only. The `next:` list extracts only the first item's `action:` for the dashboard. Skill is forgiving: missing fields produce blank columns, not errors.

Per-file parse cost is ~1ms. With ~3 worktrees × ~5 handoffs each, total filesystem walk + parse stays well under 500ms.

## Migration note

This skill replaced the previous per-subsystem-tag inventory (`{alias}-vX.Y.Z` tags) with `git log` against subsystem paths from `CLAUDE.md::Subsystems` column 3. Per-subsystem tags retired alongside `/promote` in qute-essentials 1.15.0.

This skill replaced the dev-only handoffs/TASKS.md scan with the cross-worktree walk in qute-essentials 1.18.0, when the workflow moved to the drift-on-branches model.

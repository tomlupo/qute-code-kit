---
name: to-slices
description: Break a stress-tested PRD/plan into small, independently-grabbable VERTICAL slices, each delivering one PR, staged as Paperclip child tasks in dependency order. Use after grill — "break this into slices/tasks/tickets", "decompose the PRD", "to-issues". Adapted from mattpocock/skills `to-issues`, rebound to Paperclip child tasks. Stage 3 of the engineering workflow (docs/engineering-workflow.md).
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
---

# to-slices — PRD → vertical-slice child tasks

## Role
Stage 3 of `docs/engineering-workflow.md`. Turn the PRD (a Paperclip epic) into
**child tasks**, each a thin end-to-end cut delivering **one PR**.

## Slice rules

> ⚠️ **#1 RULE — DISJOINT FILES (hard-learned, dm-evo 2026-06-14).** Two slices that
> edit the **same file collide.** Orchestrators auto-advance child slices off bare `dev`
> — they do NOT stack branches or wait for the prior to merge — so each slice re-creates
> the prior's file and every PR add/add-conflicts. **Before slicing, list each slice's
> file footprint; if any two overlap, MERGE them into one task.** Sequential work that
> builds ONE module (a single `.py`) = ONE task, never N slices. A 6-slice same-module
> fan-out became 12 colliding PRs; the 1-task-per-module redo worked first try.
> (See `feedback_vertical_slices_disjoint_files`.)

- **Vertical / tracer-bullet, NOT horizontal — *and disjoint*.** Each slice cuts through
  every layer it touches (config → engine rule → test → surfaced output), is independently
  demoable, AND touches files **no sibling slice touches**. Reject "all the tests" /
  "all the config" single-layer slices AND same-module increments. **Many thin slices beat
  few thick ones *only when file-disjoint*** — else fewer, module-sized tasks win.
- **One PR per slice.** Branch `paperclip/TOM-NNN-<slug>`; PR body `Closes TOM-NNN`;
  base `dev` (dm-evo) / `main` (dm-evo-lab).
- **HITL vs AFK.** Tag each slice: AFK (an agent can land it unattended — preferred)
  or HITL (needs a human judgment/backtest read — most methodology slices).
- **Dependency-ordered.** Publish in build order; record blockers per slice.
- **Pick the execution variant** per slice (workflow §6): deterministic-TDD /
  methodology-gate / exploratory-spike. State it in the slice so `triage`/`tdd` know.

## Each slice carries
- parent = the epic (`parentId` PATCHed after create — create is minimal-only).
- **What to build** (end-to-end behavior, not file paths).
- **Acceptance criteria** checklist (the observable behavior + which gate proves it).
- **Blockers** (other slice ids).
- HITL/AFK + execution-variant tags.

## Output
Child tasks under the epic, in dependency order. **Writes need Tom's OK** — until
then draft the slice list in the PRD/`research/<line>/` and present for approval.
Then hand to `triage`.

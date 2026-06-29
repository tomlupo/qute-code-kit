---
name: to-prd
description: Turn the current conversation + codebase context into a Product Requirements Document and stage it as a Paperclip EPIC task. Use when a build idea has been discussed and is ready to be specified before any code — "write a PRD", "spec this", "turn this into a PRD/epic". Adapted from mattpocock/skills `to-prd`, rebound to the Paperclip tracker (NOT GitHub Issues). Stage 1 of the engineering workflow (docs/engineering-workflow.md).
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
---

# to-prd — synthesize a PRD → Paperclip epic

## Role
Stage 1 of `docs/engineering-workflow.md`. **Synthesize** existing context into a
PRD; do **not** interview the user (interrogation is `grill`, run next). Explore the
codebase first and use its domain vocabulary.

## Method
1. **Explore the seam.** Identify the highest-level existing testing/extension seam
   the work plugs into (e.g. `src/fund_scoring/allocation/editorial.py` for E/W,
   `config/fund-selection/*.yaml` for config). **Validate the seam with the user
   before writing.**
2. **Write the PRD** with these fixed sections (no file paths in the body):
   1. **Problem statement** (user POV)
   2. **Solution** (user POV)
   3. **User stories** — "As a [actor], I want [feature], so that [benefit]"
   4. **Implementation decisions** — modules / interfaces / schema / contracts
   5. **Testing decisions** — observable behavior, which execution variant per §6 of
      the workflow (deterministic-TDD / methodology-gate / exploratory-spike), prior-art tests
   6. **Out of scope**
   7. **Further notes**
3. **Classify** the dominant change type → which TDD variant the slices will use.

## Output — Paperclip epic (the PRD's home)
- The PRD body becomes a **Paperclip epic task** (parent). Per the tracker binding
  (`docs/agents/issue-tracker.md`): create is minimal-only (`projectId/title/
  description/priority`); set `parentId`/labels by PATCH after.
- **dm-evo work → dm-evo project** (execution-wired). **Lab research → dm-evo-lab
  project** (author only; not execution-wired).
- **Writes need Tom's explicit OK.** Until then, write the PRD to
  `research/<line>/prd-<slug>.md` (or `docs/`) and present it for approval; create
  the epic only on the go-ahead.

## Next
Hand the PRD to `grill` (stress test) → `to-slices` (decompose). Do not skip grill.

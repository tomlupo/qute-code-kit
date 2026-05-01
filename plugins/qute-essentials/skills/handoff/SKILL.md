---
name: handoff
description: Prepare a handoff document at session end and GC the bounded state stores. Auto-edits TASKS.md (move completed Now/In-Progress items to Completed; demote Now overflow to Next) and root STATUS.md (prepend a dated Notes line; bump tag column if a tag was cut). All three artifacts land in one revertable commit. Use when the user says "handoff", "save state", "wrap up", "session end", or asks to record what just happened. Pairs with /pickup (reads the handoff at session start) and /decision (creates ADRs the handoff links).
argument-hint: "[--no-commit] [--push] [goal]"
---

# /handoff

Prepare a handoff document to continue work in a new session. Captures what matters for resuming — context, decisions, blockers, and environment state.

## Behavior

When the user invokes `/handoff [goal]`:

1. **Gather environment state** automatically:
   - Run `git diff --name-only` and `git status --short` to detect modified/staged files
   - Note current branch, working directory
   - Check for running background tasks or services relevant to the work

2. **Detect ADRs touched this session**:
   - Scan `docs/decisions/*.md` for files created or modified during the session
   - Use git: `git status --short docs/decisions/` to find new or modified ADR files
   - For each ADR found, note: number, title, status (Accepted / Superseded by / Proposed), and whether it's new or an existing one whose status changed
   - If the `decision` skill was invoked this session, those ADRs will appear here
   - If no ADRs were touched, this section is omitted or says "none"

3. **Update TASKS.md** (if it exists at repo root) — auto-edit, then snapshot:
   - **Validate format first**: run `${CLAUDE_PLUGIN_ROOT}/hooks/run-hook ${CLAUDE_PLUGIN_ROOT}/scripts/validate_tasks.py`. If it exits non-zero, surface the violations to the user and **skip the auto-edit** (writing into a malformed file would compound the drift). Continue with the rest of the handoff. The validator also scans `docs/tasks/*.md` for half-frontmatter dispatchable plans — surface those too.
   - Read `TASKS.md` and parse the sections: `## Now`, `## Next`, `## Later`, then one or more `## Completed[*]` sections (dated-batch headers like `## Completed (2026-04-30 — Phase B/C)` are allowed).
   - **Move completed items.** For each item under `## Now` or `## In Progress`, check whether it's plausibly done this session (its described change appears in `git diff` / `git log` / conversation context). If yes, move the bullet from Now → Completed with `[x]` and an inline ` (handoff YYYY-MM-DD)` suffix. Never delete an item — only move.
   - **Demote stale Now overflow.** If `## Now` still has more than 3 items after the move, demote the oldest items (in file order, last entries first) to the top of `## Next` until Now ≤ 3.
   - **Add discovered work** mentioned in the conversation that the user asked to track. Prepend to `## Next` as a new bullet. Skip if no clear candidate.
   - Show the diff to the user before saving (`git diff TASKS.md`-style preview). On confirm: write the file. On reject: skip the auto-edit and use the file as-is.
   - Capture the final state of Now / Next into the handoff body for `/pickup` to read.

   This step is the GC for `TASKS.md`. Skipping it means the file rots and `/pickup` warnings about the Now-cap accumulate. Keep the diff small and reviewable — one section move per item, no rewrites of user prose.

4. **Detect production-code edits on a research branch** (discipline check — only fires on research branches):
   - If the current branch name matches `research/*`:
     - Run `git diff --name-only dev...HEAD` (or `main...HEAD` if no dev) to list changed files vs the integration branch.
     - Identify production paths by convention: `src/`, `pipelines/`, `config/`. No config file is read — these prefixes are universal.
     - Also include uncommitted changes: `git diff --name-only HEAD` + `git ls-files --others --exclude-standard`.
     - If any production files were touched on a research branch, flag it in the handoff under a `⚠️ Production code edits on research branch` section and include:
       - list of files
       - reminder that these must be cherry-picked to a `feat/{alias}-{slug}` branch off `dev` before promotion
       - reference to `.claude/rules/research-workflow.md` if present
   - If not a research branch, skip silently.

5. **Analyze current conversation context**:
   - What was accomplished in this session
   - Important decisions made and their rationale (link to ADR numbers from step 2 where applicable)
   - Any blockers, failures, or issues requiring user action
   - Unanswered questions or unresolved ambiguity

6. **Generate a handoff document** with these sections:
   - **Goal**: What the next session should accomplish (from arg, or inferred from conversation)
   - **Context Summary**: Brief summary of session work (NOT a transcript)
   - **ADRs touched this session**: New or superseded ADRs from step 2, with file paths and status changes. Omit the section if none.
   - **⚠️ Production code edits on research branch**: From step 4 (only if production files were touched on a research branch). Omit if not applicable.
   - **Key Decisions**: Conversational decisions and rationale. Reference ADR numbers where a formal decision was recorded.
   - **Environment State**: Branch, directory, modified files, running services
   - **TASKS.md state at handoff**: Snapshot of Now / In Progress / Next sections from step 3. Omit if TASKS.md doesn't exist.
   - **Modified Files**: Auto-detected from git + conversation context, with why each matters
   - **Blockers**: Things that must be resolved before continuing (separate from notes — these require action)
   - **Next Steps**: Ordered, specific, actionable items
   - **Notes**: Caveats, gotchas, things to watch out for

7. **Save the handoff** to `.claude/handoffs/<YYYY-MM-DD>-<slug>.md`

8. **Offer EXPERIMENTS.md append (opt-in, if the session looks like an experiment)**:
   - Trigger: the session touched any of `research/{subsystem}/docs/*.md`, `research/{subsystem}/validation/`, `research/{subsystem}/experiments/`, or production paths under `src/{subsystem}/`, `pipelines/{subsystem}/`, `config/{subsystem}/`.
   - Identify the subsystem from the touched paths (the basename under `research/` or the first segment after `src/` etc.). If multiple match, ask the user.
   - If `research/{subsystem}/EXPERIMENTS.md` exists, propose appending a structured entry:
     ```markdown
     ## YYYY-MM-DD — <inferred title>

     **Branch:** <current branch>
     **Hypothesis:** <ask user one-liner>
     **What changed:** <auto-generated from git diff summary>
     **Results:** <from conversation context — fill what's known>
     **Decision:** <accepted | candidate-pending-backtest | rejected | iterate>
     **Artifacts:** <dashboard link, handoff file, MLflow run if any>
     ```
   - Show the proposed entry, ask user to confirm/edit/skip.
   - On confirm: prepend to top of the EXPERIMENTS.md file (newest at top convention).
   - Skip silently if no EXPERIMENTS.md exists for the subsystem or no qualifying paths were touched. No config file is read.

9. **Update root STATUS.md Notes (auto-edit, append-only)**:
   - Skip silently if root `STATUS.md` doesn't exist.
   - Find the `## Notes` section. If absent, append it at the file end.
   - Prepend a new dated bullet to the section: `- YYYY-MM-DD: <one-line session takeaway>` — e.g. parked-pending change, new in-flight work, blocker raised this session, version bumped.
   - **Append-only.** Never edit, reorder, or delete existing lines under `## Notes`. The user prunes by hand. Cap on size lives with the user, not the skill.
   - If the session produced a tag (i.e. `/promote` or `/ship` ran in this session), also update the relevant subsystem row in the `## Subsystems` table (column for the new tag) — same append-only discipline: replace only the version cell of the matching row, never touch other cells.
   - Show the diff to the user before saving. On confirm: write. On reject: skip the auto-edit.

   This step is the GC for root `STATUS.md`. Skipping it means `/pickup` warnings about "STATUS.md older than latest tag" accumulate.

10. **Display the handoff** for the user to review

11. **Commit handoff + state edits (default behavior)**: one commit per handoff for clean revert.
   - Stage: the handoff file, plus `TASKS.md` and `STATUS.md` if either was auto-edited in steps 3 / 9. Do NOT stage other WIP — only the state-tracking files this skill owns.
     ```bash
     git add .claude/handoffs/<file>.md
     [ -n "$tasks_changed" ] && git add TASKS.md
     [ -n "$status_changed" ] && git add STATUS.md
     ```
   - Commit: `git commit -m "handoff: <goal-slug>"` — the handoff body lists what TASKS.md / STATUS.md edits the commit contains, so reverting one commit reverts the whole bookkeeping pass cleanly.
   - The commit lands on the CURRENT branch (alongside the WIP it describes), not a dedicated `handoff/*` branch.
   - Report the resulting commit SHA to the user — anchor for drift detection on resume.
   - Skip this step if `--no-commit` was passed; the auto-edits to TASKS.md / STATUS.md still apply on disk but stay unstaged.
   - Skip silently if the repo is not a git repository.

12. **Push to remote (opt-in via `--push`)**: when `--push` was passed, push the current branch after the commit:
   - `git push -u origin HEAD`
   - If push fails due to network, retry with exponential backoff (2s, 4s, 8s, 16s)
   - Without `--push`, the commit lives only locally — push later on your normal cadence

## Arguments

- `[goal]` - (Optional) What the next session should accomplish. If omitted, infer from conversation context.
- `--no-commit` - (Optional flag) Write the handoff doc to disk only; don't commit. Use when the session may be discarded or you don't want a handoff commit on the branch yet.
- `--push` - (Optional flag) Push the handoff commit to remote (`git push -u origin HEAD`) after committing. Implies committing — has no effect with `--no-commit`.

## Output Format

```markdown
# Handoff: <goal-slug>

**Created**: <ISO timestamp>
**Goal**: <goal — stated or inferred>
**Previous**: <link to prior handoff if one exists, else "none">

## Context Summary

<2-5 sentences summarizing what happened this session>

## ADRs touched this session

(Omit section if none.)

- **ADR-NNNN** `docs/decisions/NNNN-slug.md` — new, `Status: Accepted`
- **ADR-MMMM** `docs/decisions/MMMM-slug.md` — status changed to `Superseded by ADR-NNNN`

## Key Decisions

- **<Decision>**: <rationale> *(recorded as ADR-NNNN)*
- **<Decision>**: <rationale>

## Environment State

- **Directory**: <working directory>
- **Branch**: <current git branch, or "not a git repo">
- **Modified files**: <list from git diff, or "none">
- **Running services**: <any relevant background processes>

## TASKS.md state at handoff

(Omit section if TASKS.md doesn't exist at repo root. Snapshot taken after
any pre-handoff updates the user agreed to.)

**Now / In Progress**:
- [ ] <item>
- [ ] <item>

**Next**:
- [ ] <item>
- [ ] <item>

## Files to Load

These files provide necessary context for the next session:
- `path/to/file` — <one-line reason>
- `path/to/file` — <one-line reason>

## Blockers

Items that require user action before work can continue:
- <blocker and what's needed to resolve it>

(If no blockers, write "None — ready to continue.")

## Next Steps

1. <Specific actionable step>
2. <Specific actionable step>
3. <Specific actionable step>

## Notes

- <Caveats, gotchas, or context that's easy to forget>
```

## Conventions

- Keep the whole document under 100 lines (was 80 before ADR + TASKS.md sections) — concise beats comprehensive
- Use imperative voice in Next Steps ("Install caddy", not "Caddy should be installed")
- Blockers are things the USER must do; Next Steps are things CLAUDE will do
- If the session had no meaningful progress, say so honestly — don't pad
- **Do not duplicate rationale from ADRs**. If a decision was formally recorded via the `decision` skill, reference the ADR number in Key Decisions — don't copy its content. Rationale lives in the ADR, state lives in the handoff.
- **Reference, don't snapshot, ADR content**. The handoff's "ADRs touched this session" section is a pointer list, not a copy of the ADR bodies.

## Auto-edit invariants (TASKS.md + STATUS.md)

This skill is the GC for two bounded inventories. Auto-edits happen in steps 3 and 9; both end up in the same handoff commit so a single revert undoes the whole pass.

- **Append-only on user prose.** Never delete or edit a line the user wrote in `STATUS.md ## Notes` or in any TASKS.md item body. The skill only *moves* TASKS.md bullets between sections (Now → Completed, Now overflow → Next) and *prepends* dated lines to STATUS.md.
- **Show the diff first.** Before writing TASKS.md or STATUS.md, present the proposed diff. On user reject: skip the auto-edit; the handoff itself still saves and commits.
- **One commit per handoff.** All three artifacts (handoff, TASKS.md, STATUS.md) land in one `handoff: <slug>` commit. Easy to inspect, easy to `git revert`.
- **`--no-commit` doesn't disable auto-edit.** The disk writes still happen; they're just left unstaged for the user to handle. This preserves the GC behavior even when the user wants to defer the commit.

## Coherence with `decision` and `pickup`

The `handoff` skill writes session state; the `pickup` skill reads it on the
receiving side; the `decision` skill creates ADRs that both sides link to.
Together they form a closed loop:

```
Session end:  /handoff  → writes handoff, GC-edits TASKS.md + STATUS.md, links ADRs, one commit
Session start: /pickup  → reads handoff, audits ADRs/drift/inventory, echoes STATUS.md Notes
Mid-session:  /decision → creates/supersedes ADRs, which the next /handoff auto-links
```

When these three skills are used together, rationale lives in ADRs (immutable),
session-level state lives in handoffs (ephemeral),
task progress lives in TASKS.md (mutable, GC'd by /handoff),
and cross-session production state lives in root STATUS.md (mutable, GC'd by /handoff).
Each piece has one source of truth and one writer.

## Resuming from a Handoff

In a new session:

```
Load the handoff from .claude/handoffs/<filename>.md and continue
```

When resuming, **check for drift** — files listed in the handoff may have changed since it was written, invalidating the planned approach:

1. **Read the handoff doc** and extract its "Files to Load", "Modified files", and "Next Steps" sections.

2. **Find the commit that introduced the handoff** (handoffs are committed by default since v1.10.0; older handoffs and `--no-commit` runs may be untracked):
   ```bash
   HANDOFF_SHA=$(git log --diff-filter=A --format=%H -- .claude/handoffs/<file>.md | tail -1)
   ```
   `--diff-filter=A` narrows to the commit that *added* the file, so later edits to the doc don't shift the anchor. `tail -1` picks the oldest match if there are multiple. If empty, the handoff was written with `--no-commit` or predates v1.10.0 — fall through to step 6.

3. **List files changed since the handoff**:
   ```bash
   git diff --name-only "$HANDOFF_SHA"..HEAD
   ```
   Also include unstaged changes: `git diff --name-only HEAD`.

4. **Cross-reference** the changed files against the handoff's "Files to Load" and "Modified files" lists. For each overlap:
   - Show a short diff: `git diff "$HANDOFF_SHA"..HEAD -- <file>`
   - Flag the affected "Next Steps" items — their assumptions may be stale.

5. **Tell the user before proceeding**: "N files referenced by this handoff have changed since it was written: [list]. Review before continuing?" If nothing drifted, say "No drift — handoff is current" and proceed.

6. If the handoff has no git history (untracked — written with `--no-commit` or pre-v1.10.0), skip drift detection and proceed with Next Steps as written.

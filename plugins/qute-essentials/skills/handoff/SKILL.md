---
name: handoff
description: Prepare a handoff document to continue work in a new session. Captures context, decisions, blockers, environment state, ADRs touched during the session, and a TASKS.md snapshot for seamless session transitions. Pairs with the `pickup` skill which reads the handoff on the receiving side, and with the `decision` skill which creates the ADRs that handoff auto-links.
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

3. **Snapshot TASKS.md** (if it exists at repo root):
   - Read `TASKS.md` and extract the Now / In Progress / Next sections
   - **Before capturing the snapshot**, check if any items in Now/In Progress look completed based on session work (e.g. their described changes appear in `git diff`). If so, prompt the user once: *"N items in Now/In Progress look completed this session. Update TASKS.md before handoff?"* — do not update TASKS.md automatically; let the user decide
   - After the user either updates or declines, capture the final state of Now/Next into the handoff

4. **Detect production-code edits on a research branch** (discipline check — opt-in):
   - If the current branch name matches `research/*` OR the repo has `.claude/promote.config.yaml`:
     - Run `git diff --name-only dev...HEAD` (or `main...HEAD` if no dev) to list changed files vs the integration branch.
     - Identify production paths: `src/`, `pipelines/`, `config/` — or, if `promote.config.yaml` exists, the union of `src_paths` across subsystems.
     - Also include uncommitted changes: `git diff --name-only HEAD` + `git ls-files --others --exclude-standard`.
     - If any production files were touched on a research branch, flag it in the handoff under a `⚠️ Production code edits on research branch` section and include:
       - list of files
       - reminder that these must be cherry-picked to a `feat/{subsystem}-{slug}` branch off `dev` before promotion
       - reference to `.claude/rules/research-workflow.md` if present
   - If not a research branch (or the repo has no promote.config.yaml and isn't on a research/* branch), skip silently.

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
   - If `.claude/promote.config.yaml` exists AND the session touched any of: spec docs (`research/*/docs/*.md`), validation analyses (`research/*/validation/`), dashboard rebuilds (`research/*/validation/output/`), or production paths listed in any subsystem's `src_paths`:
     - Identify the most-likely subsystem (from which paths were touched)
     - If the subsystem has an `experiments_file` configured in promote.config.yaml, propose appending a structured entry:
       ```markdown
       ## YYYY-MM-DD — <inferred title>

       **Branch:** <current branch>
       **Hypothesis:** <ask user one-liner>
       **What changed:** <auto-generated from git diff summary>
       **Results:** <from conversation context — fill what's known>
       **Decision:** <accepted | candidate-pending-backtest | rejected | iterate>
       **Artifacts:** <dashboard link, handoff file, MLflow run if any>
       ```
     - Show the proposed entry, ask user to confirm/edit/skip
     - On confirm: prepend to top of `experiments_file` (newest at top convention)
     - Skip silently if no promote.config.yaml or no qualifying paths touched

9. **Display the handoff** for the user to review

10. **Commit the handoff (default behavior)**: persist the handoff to git on the current branch so `/pickup` can use the introducing commit as a drift-detection anchor.
   - Stage only the handoff file: `git add .claude/handoffs/<file>.md` (do NOT stage other WIP)
   - Commit: `git commit -m "handoff: <goal-slug>"`
   - The handoff commits onto the CURRENT branch (alongside the WIP it describes), not a dedicated `handoff/*` branch
   - Report the resulting commit SHA to the user — this is the anchor for drift detection on resume
   - Skip this step if `--no-commit` was passed (e.g. session may be discarded; user wants the doc on disk only)
   - Skip silently if the repo is not a git repository

11. **Push to remote (opt-in via `--push`)**: when `--push` was passed, push the current branch after the commit:
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

## Coherence with `decision` and `pickup`

The `handoff` skill writes session state; the `pickup` skill reads it on the
receiving side; the `decision` skill creates ADRs that both sides link to.
Together they form a closed loop:

```
Session end:  /handoff  → writes handoff + links ADRs touched + snapshots TASKS.md
Session start: /pickup  → reads handoff, verifies ADR statuses, diffs TASKS.md against current
Mid-session:  /decision → creates/supersedes ADRs, which the next /handoff auto-links
```

When these three skills are used together, rationale lives in ADRs (immutable),
state lives in handoffs (ephemeral), and task progress lives in TASKS.md
(mutable). Each piece has one source of truth.

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

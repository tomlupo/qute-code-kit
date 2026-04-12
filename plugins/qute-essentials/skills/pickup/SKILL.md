---
name: pickup
description: Resume work from a previous session by loading the latest handoff and auditing its health. Use when the user is resuming or picking up work — triggers include phrases like "continue from", "pick up where we left off", "resume", "what's the state", "where were we", "load the handoff"; or when the user references a .claude/handoffs/*.md file by name; or when the user asks about current work state, stale handoffs, or pending ADRs. Reads the latest active handoff, verifies referenced ADRs are still Accepted (not Superseded), summarises TASKS.md Now/Next, lists handoffs that look like archive candidates, and flags ADRs stuck in Proposed status. Read-only — does not modify any files. Pairs with the /handoff skill which writes handoffs at session end.
argument-hint: "[handoff-filename-or-path]"
---

# /pickup

Resume work from a previous session. Loads the latest active handoff, audits its health (ADR references, referenced files, TASKS.md state), and reports a compact work-state summary so you can continue with full context and no surprises.

Pairs with `/handoff`: `/handoff` writes a handoff at session end, `/pickup` reads and audits it at session start.

## When to use

Invoke this skill when:
- The user is resuming work from a previous session
- The user says phrases like "continue from", "pick up", "resume", "where were we", "what's the state"
- The user references a handoff filename (e.g. "load 2026-04-10-treatment-c...")
- The user asks about pending ADRs, stale handoffs, or current TASKS.md status
- The agent needs to orient at session start on an existing work thread

Do NOT invoke for:
- Brand new work with no prior context
- One-off questions unrelated to a current work thread

## Arguments

- `[handoff-filename-or-path]` — (optional) specific handoff to load. If omitted, picks the newest active handoff (non-archived, no ⚠️ superseded banner).

## Behavior

1. **Find the handoff to load**:
   - If an argument was passed, resolve it to a file in `.claude/handoffs/`
   - Otherwise, list `.claude/handoffs/*.md` (excluding anything in `archive/` subdirectory), sort by mtime, pick the newest
   - If none exist, report "No active handoffs found" and stop

2. **Read the handoff** and extract:
   - Goal, Context Summary, Next Steps, Files to Load, Blockers
   - Any `ADR-NNNN` references (grep pattern `ADR-\d{4}`)
   - Any referenced file paths (from "Files to Load" section and inline `file_path` mentions)
   - Any reference to a predecessor handoff (to trace the chain)

3. **Verify ADR references are current**:
   - For each `ADR-NNNN` mentioned, locate `docs/decisions/NNNN-*.md`
   - Read its `## Status` section
   - If `Superseded by ADR-MMMM`: warn that the handoff references a stale decision and point at the successor
   - If `Deprecated`: warn
   - If `Proposed`: note that the decision hasn't been finalised yet
   - If the ADR file doesn't exist at all: warn

4. **Check drift on referenced files** (only if handoff was pushed to git):
   - Extract `HANDOFF_SHA` via `git log --diff-filter=A --format=%H -- .claude/handoffs/<file>.md | tail -1`
   - Run `git diff --name-only "$HANDOFF_SHA"..HEAD`
   - Cross-reference against the handoff's "Files to Load" list
   - Flag any overlap as potential drift — the next-step assumptions may be stale

5. **Summarise TASKS.md** (if it exists at repo root):
   - Extract Now / In Progress / Next / Backlog sections
   - Report the top 3-5 active items
   - Note any items flagged as blocked or needing attention

6. **List archive candidates**:
   - Handoffs in `.claude/handoffs/` (non-archive) that are **not** the latest and **not** referenced as predecessors of the latest
   - These are candidates for moving to `.claude/handoffs/archive/` to keep the active folder tidy
   - Do not move anything — just list

7. **Flag pending ADRs**:
   - Grep `docs/decisions/*.md` for `Status: Proposed`
   - These are decisions in-flight that might need finalising before work resumes

8. **Print a compact work-state report** (see Output Format below)

## Output Format

```markdown
## Work State Report

**Latest handoff**: `.claude/handoffs/<filename>.md`
**Goal**: <handoff goal>
**Predecessor**: <previous handoff filename or "none">

### Referenced ADRs
- ✅ ADR-NNNN: <title> — Accepted
- ⚠️  ADR-MMMM: <title> — **Superseded by ADR-PPPP** — review the successor before proceeding
- ❓ ADR-QQQQ: <title> — Proposed (not yet finalised)

### Drift check
<"No drift — handoff is current" OR list of changed files and affected next-steps>

### TASKS.md
- **Now**: <top 3 active items>
- **Next**: <top 3 queued items>

### Housekeeping
- **Archive candidates**: <list of handoffs not referenced by the latest chain, or "none">
- **Pending ADRs** (Status: Proposed): <list with paths, or "none">

### Ready to continue
<short summary: "X next steps, Y blockers to resolve first, Z ADRs to review before proceeding">
```

## Conventions

- **Read-only** — never move files, update ADRs, or modify the handoff. This skill is a diagnostic only.
- **Compact output** — aim for under 40 lines in the report. Detail lives in the handoff itself.
- **Actionable warnings** — if a referenced ADR is superseded, name the successor and point at the file path. Don't just say "stale".
- **Fail-soft** — if `git` isn't available, skip drift check and note that. If `TASKS.md` doesn't exist, skip that section. If no handoff exists, report cleanly and stop.

## Example

```
/pickup
```

Loads the newest handoff (e.g. `.claude/handoffs/2026-04-10-treatment-c-methodology-and-step-a.md`), checks ADR-0004 is still Accepted, verifies that the files it references haven't drifted since the handoff was written, summarises TASKS.md Now/Next, and prints the report so the agent can continue with full context.

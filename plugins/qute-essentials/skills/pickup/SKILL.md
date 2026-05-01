---
name: pickup
description: Resume work from a previous session. Loads the latest handoff, audits ADR statuses + file drift since the handoff was written, summarises TASKS.md Now/Next, reads root STATUS.md, and surfaces a one-block inventory check (worktree count, Now-cap, STATUS.md freshness). Use when the user says "continue", "pick up", "resume", "where were we", "what's the state", or names a handoff file. Read-only — does not modify files. Pairs with /handoff which writes the handoff at session end.
argument-hint: "[handoff-filename-or-path]"
---

# /pickup

Resume work from a previous session. Loads the latest active handoff, audits its health (ADRs, drift, TASKS.md, root STATUS.md, inventory), and reports a compact work-state summary so you can continue with full context and no surprises.

Pairs with `/handoff`: `/handoff` writes a handoff at session end, `/pickup` reads + audits at session start.

## When to use

- User is resuming work — "continue from", "pick up", "resume", "where were we", "what's the state"
- User references a handoff filename
- User asks about pending ADRs, stale handoffs, TASKS.md state, current versions

Do NOT invoke for:
- Brand new work with no prior context
- One-off questions

## Arguments

- `[handoff-filename-or-path]` (optional) — specific handoff to load. If omitted, picks the newest non-archived handoff under `.claude/handoffs/`.

## Behavior

1. **Find the handoff:**
   - With argument: resolve to file in `.claude/handoffs/`.
   - Otherwise: list `.claude/handoffs/*.md` (skip `archive/`), sort by mtime, pick newest.
   - If none: report "No active handoffs found" and continue with the rest of the audit (handoff is one of several signals, not the only one).

2. **Read the handoff** and extract:
   - Goal, Context Summary, Next Steps, Files to Load, Blockers
   - `ADR-NNNN` references (regex `ADR-\d{4}`)
   - File paths from "Files to Load" and inline `path/to/file` mentions
   - Predecessor handoff link (to trace the chain)

3. **Verify ADR references:**
   - For each `ADR-NNNN`, locate `docs/decisions/NNNN-*.md`, read its `## Status` section.
   - Flag: `Superseded by ADR-MMMM` (point at successor), `Deprecated`, `Proposed` (not finalised), or missing file.

4. **Drift check on referenced files** (only if handoff is committed):
   - `HANDOFF_SHA=$(git log --diff-filter=A --format=%H -- .claude/handoffs/<file>.md | tail -1)`
   - `git diff --name-only "$HANDOFF_SHA"..HEAD` + `git diff --name-only HEAD` (uncommitted)
   - Cross-reference against the handoff's "Files to Load" / "Modified files".
   - For overlap, flag the affected Next Steps as potentially stale.
   - If `HANDOFF_SHA` is empty (handoff is untracked), skip silently.

5. **Summarise root TASKS.md** (if it exists):
   - Extract Now / Next sections, top 3-5 each.
   - Flag if `Now` exceeds the soft cap of 3 items (per `general-rules.md`).

6. **Read root STATUS.md** (single source — no per-subsystem STATUS.md):
   - If present, echo the `## Notes` section (cap ~15 lines).
   - Freshness: STATUS.md mtime vs newest tag mtime. If `mtime(STATUS.md) < mtime(newest tag)`, flag `⚠️ STATUS.md older than latest tag — dashboard may be stale`.
   - If missing, skip silently.

7. **Inventory check** (one block, light — these are the bounded stores `git-workflow.md` says to police):
   - **Format violations:** run `${CLAUDE_PLUGIN_ROOT}/hooks/run-hook ${CLAUDE_PLUGIN_ROOT}/scripts/validate_tasks.py`. Surface any output as warnings (TASKS.md section drift, Now-cap, half-frontmatter dispatchable plans). Read-only — never block the audit on this.
   - **Worktrees:** `git worktree list` count. Hard cap 3 (per `git-workflow.md`); warn if ≥3, flag if >3.
   - **Handoffs (active):** count `.claude/handoffs/*.md` (excluding `archive/`); list as archive candidates anything that's not the latest and not in the predecessor chain.
   - **Pending ADRs:** grep `docs/decisions/*.md` for `Status: Proposed`; list count + paths.
   - **Stale spec frontmatter:** any LOCKED spec under `research/*/docs/*.md` whose `date_locked` is older than its declared `spec_date_max_age_days` (default 90) — count + list. Skip silently if no specs.

8. **Print compact report** (see Output Format).

## Output Format

```markdown
## Work State Report

**Latest handoff**: `.claude/handoffs/<filename>.md`
**Goal**: <handoff goal>
**Predecessor**: <previous handoff filename or "none">

### Referenced ADRs
- ✅ ADR-NNNN: <title> — Accepted
- ⚠️  ADR-MMMM: <title> — **Superseded by ADR-PPPP**
- ❓ ADR-QQQQ: <title> — Proposed

### Drift check
<"No drift — handoff is current" OR list of changed files mapping to affected Next Steps>

### TASKS.md
- **Now** (3): <items>      [or "⚠️ Now has 5 items — over soft cap"]
- **Next**: <items>

### STATUS.md (root)
<echo of ## Notes block, ≤15 lines>
[or "⚠️ STATUS.md older than latest tag (taa-v5.1.0 tagged 2026-04-30) — may be stale"]

### Inventory
- Worktrees: 2 / 3
- Pending ADRs (Proposed): 0
- Stale specs (date_locked > 90d): 0
- Archive candidates: <list of handoffs not in predecessor chain, or "none">

### Ready to continue
<short summary: "X next steps, Y blockers, Z things to review first">
```

## Conventions

- **Read-only** — never writes. Audits are diagnostic; the user (or `/handoff`) does any cleanup.
- **Compact** — under 40 lines. Detail lives in the handoff itself.
- **Actionable warnings** — name the thing (file, ADR successor, count over cap), don't just say "stale".
- **Fail-soft** — missing STATUS.md / TASKS.md / handoff / git → skip the relevant block, never abort the whole report.
- **Fast** — single git tag query + single mtime comparison + handoff read. No repo-wide diff. Sub-2s.
- **No config-file reads** — the skill discovers subsystems from filesystem + tags, not from any `.claude/promote.config.yaml`.

## Example

```
/pickup
```

Loads newest handoff, verifies ADRs, drift-checks Files to Load, summarises TASKS.md Now/Next, echoes root STATUS.md Notes, runs inventory check (worktrees, ADRs, archive candidates), prints the report. Under 2 seconds.

## See also

- `/handoff` — writes the handoff `/pickup` reads
- `/status` — quick "what's where" without the full audit
- `/decision` — creates the ADRs both sides link to

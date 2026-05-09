---
name: pickup
description: Resume work — runs /status, picks a focus task (explicit or smart), loads its plan + latest handoff, emits a 150-word brief. Optional --continue flag executes the latest handoff's next[0] action with confirm-to-proceed. Use when user says "resume", "pickup", "continue", "where were we".
argument-hint: "[slug] [--continue]"
---

# /pickup

Briefs you on where work left off. Thin wrapper over `/status` plus context loading for the focus task. Default: brief only. Opt-in `--continue`: execute the latest handoff's `next[0]` action.

## When to use

- Session start: "where did I leave off?"
- After context reset: "what was the focus?"
- User says "resume", "pickup", "continue", "where were we".

Do NOT invoke for:
- Quick state lookup — use `/status` (no LLM, sub-second).
- Writing state at session end — use `/handoff`.

## Arguments

- `[slug]` (optional) — task slug to focus on (matches `docs/tasks/{slug}.md` or a handoff's `task:` field). If omitted: smart-pick.
- `--continue` — opt-in auto-execute. **Requires explicit `[slug]`** (no smart-pick). Subject to staleness check (<48h) and Enter-to-confirm.

## Behavior

### 1. Run `/status` first

Echo its output verbatim. This is the cross-branch situational anchor — sub-second, always do it. It already shows latest handoffs per worktree, Now items per branch, orphans.

### 2. Determine focus

- **If `[slug]` given (explicit):** find the latest handoff across all worktrees with `task: {slug}`, plus `docs/tasks/{slug}.md` if it exists. (Use `/status`'s scan output, or re-walk worktrees.)
- **If no slug (smart):** pick the latest in-progress handoff from `/status`'s output (most recent `date:` with `status: in-progress`). If none in-progress, pick the most recent regardless. Tie-break: prefer the worktree whose branch we're currently on.

Refuse `--continue` without explicit slug: *"Auto-continue requires explicit slug. Try: /pickup taa-migration --continue"*.

### 3. Load context

Read the focus task's:
- **Plan file** (`docs/tasks/{slug}.md`) if it exists — gives the goal + acceptance criteria.
- **Latest handoff** for that task — gives the most recent state.

**Hard cap: 2 files / ~2000 tokens.** Don't load older handoffs or related files. Pickup is a brief, not a full ramp-up.

### 4. Brief (~150 words, structured)

- **Resuming {project} @ {branch}. Focus: {plan title or task slug}.**
- **Where you left off (handoff {date}, {status}):** 2-3 bullets summarizing the handoff body.
- **Next from handoff:** the `next:` list items.
- **Worktree note:** if focus task lives in a different worktree than current cwd, note it (e.g., *"Switch to dm-evo-taa-migration to continue"*).

### 5. Auto-continue (only if `--continue`)

- Read handoff frontmatter `next:` and `date:`.
- **Staleness check:** if `date` is older than 48h, print *"Handoff is {N}d old; brief only. Re-run without --continue if intentional."* Stop.
- If `next[0].cmd` present:
  ```
  → Auto-continuing: {next[0].action}
    cmd: {next[0].cmd}
  Press Enter to run, or describe a different intent.
  ```
- If only `next[0].action` (no cmd): print *"→ Brief only — first action is prose, no command to execute. {action}"*.
- On Enter / no-redirect: execute via Bash. On user input: treat as new intent.

## What `/pickup` does NOT do (deliberate)

- Read methodology docs proactively.
- Run tests / lint to "check the state".
- Walk git log.
- Load all recent handoffs (only the focus task's latest).
- Edit any files.

The agent does these when the work demands them. `/pickup` is a brief, not a full ramp-up.

## Notes

Drift-on-branches model: `/pickup` reads handoffs from whichever worktree the focus task lives in (via `/status`'s scan), not from a "canonical" main checkout. Handoffs reach dev via PR merge.

For exploratory sessions: handoffs with `task: __exploratory__` are still discoverable by `/status` and pickup-able by full filename.

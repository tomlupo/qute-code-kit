---
name: pickup
description: Resume work — runs /status, loads the focus task's plan + latest handoff, emits a 150-word brief. Optional --continue flag executes the latest handoff's next[0] action with confirm-to-proceed. Use when user says "resume", "pickup", "continue", "where were we".
argument-hint: "[alias] [--continue]"
---

# /pickup

Briefs you on where work left off. Default: brief only. Opt-in `--continue`: execute the latest handoff's `next[0]` action.

## When to use

- Session start: "where did I leave off?"
- After context reset: "what was the focus?"
- User says "resume", "pickup", "continue", "where were we".

Do NOT invoke for:
- Quick state lookup — use `/status` (no LLM, sub-second).
- Writing state at session end — use `/handoff`.

## Arguments

- `[alias]` (optional) — subsystem alias to focus on. If omitted, focus on the first row in TASKS.md::Now.
- `--continue` — opt-in auto-execute. **Requires explicit `[alias]`** (no inference). Subject to staleness check (<48h) and Enter-to-confirm.

## Behavior

1. **Run `/status` first.** Echo its output. This is the situational anchor — already cheap (sub-second), so always do it.

2. **Determine focus.**
   - If `[alias]` given: filter to that row.
   - Else: take first row in `## Now`.
   - Refuse `--continue` without explicit alias: "Auto-continue requires explicit alias. Try: /pickup taa --continue".

3. **Load context** by exec-ing the helper:
   ```bash
   bash "$CLAUDE_PLUGIN_ROOT/scripts/lifecycle/pickup-ctx.sh" $1
   ```
   It returns tab-separated `<kind>\t<path>` lines for the focus row. Read each cited file (handoff, plan). Cap: 4 files / ~3000 tokens.

4. **Brief** (~150 words, structured):
   - **Resuming {project} @ {branch}. Focus: {row title}.**
   - **Where you left off (handoff {date}):** 2-3 bullets summarizing the handoff body + `status:` field.
   - **Next from TASKS.md::Now:** the unchecked items from the row.
   - **Worktree note:** current branch state if relevant (e.g. "Worktree dm-evo-taa is on research/...; switch to feat/* after spec edit lands on dev").

5. **Auto-continue** (only if `--continue`):
   - Read handoff frontmatter `next:` and `date:`.
   - Staleness check: if `date` is older than 48h: print "Handoff is {N}d old; brief only. Re-run without --continue if intentional." Stop.
   - If `next[0].cmd` present: print
     ```
     → Auto-continuing: {next[0].action}
       cmd: {next[0].cmd}
     Press Enter to run, or describe a different intent.
     ```
   - If only `next[0].action` (no cmd): print "→ Brief only — first action is prose, no command to execute. {action}"
   - On Enter / no-redirect: execute via Bash. On user input: treat as new intent.

6. **What `/pickup` does NOT do** (deliberate):
   - Read methodology docs proactively.
   - Run tests / lint to "check the state".
   - Walk git log.
   - Load all recent handoffs (only the cited one).
   - Edit any files.

The agent does these when the work demands them. `/pickup` is a brief, not a full ramp-up.

## Notes

Per DR-010, `STATUS.md` is no longer read — `/status` regenerates equivalent dashboard from git. Handoffs MUST have `task:` frontmatter for `--continue` to resolve which row in TASKS.md::Now is the target.

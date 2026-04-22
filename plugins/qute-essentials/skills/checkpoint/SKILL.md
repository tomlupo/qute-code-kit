---
name: checkpoint
description: Atomic handoff → /clear → /pickup → auto-resume cycle for continuing the same work thread in a fresh context window. Use when the context is bloated, stale, or the model is drifting, and you want to reset without losing the work thread. Runs the handoff skill (saves + pushes a handoff doc), then /clear, then pickup in the fresh session, then resumes work on the provided task (or "continue current/next task" by default). Pairs with handoff (writer) and pickup (reader).
argument-hint: "[resume-task]"
---

# /checkpoint

A context-reset ritual that preserves the work thread **and keeps working**. Runs four phases atomically:

1. **Handoff** — save session state to `.claude/handoffs/<YYYY-MM-DD>-<slug>.md` and push it to the current branch so it's git-anchored.
2. **Clear** — wipe the context window via `/clear`.
3. **Pickup** — in the fresh context, load the just-saved handoff and audit its health.
4. **Resume** — after pickup reports, immediately continue working on `$ARGUMENTS` (or `"continue current/next task"` if no argument was given).

Use this when:
- The conversation is long and the model's attention is degrading
- You're at a natural stopping point and want a clean slate without losing context
- You want an automated checkpoint before a risky operation so you can resume cheaply if needed

## Arguments

- `[resume-task]` — Optional. What to work on immediately after pickup completes. Serves dual duty: passed to handoff as the `[goal]` (what the next session should accomplish) and used as the post-pickup continuation prompt in phase 4.
  - Default: `"continue current/next task"` — resume from the handoff's Next Steps / TASKS.md "Now" items without extra steering.
  - Typical values: `"finish the auth refactor"`, `"pick up step 3 of the migration"`, `"address review comments"`.

Resolve `$ARGUMENTS` at invocation time:

```
RESUME_TASK = $ARGUMENTS if non-empty else "continue current/next task"
```

## Behavior

Execute the four phases in order. Do **not** skip phase 1 — the whole point of checkpoint is that the clear is safe because the state was just saved.

### Phase 1 — Handoff

Invoke the `handoff` skill with `--push` and the resolved `RESUME_TASK` as the goal:

```
/handoff --push {RESUME_TASK}
```

If `RESUME_TASK` is the literal default `"continue current/next task"`, pass no goal argument so handoff falls back to inferring from conversation context.

Wait for completion. Capture the handoff filename (e.g. `.claude/handoffs/2026-04-22-refactor-api.md`) and the commit SHA — these are the anchor for phase 3 drift detection.

If handoff fails (e.g. git push blocked, no network, dirty tree that handoff refuses to stage), **stop**. Do not proceed to `/clear`. Report the failure and let the user resolve it — clearing with no saved state would lose the session.

### Phase 2 — Clear

Once handoff has pushed successfully, invoke `/clear` to wipe the context window.

Use the SlashCommand tool if available. Otherwise instruct the user to type `/clear` manually.

After clear, the model's context is empty. The next turn starts fresh.

### Phase 3 — Pickup

In the fresh context, invoke the `pickup` skill to load the handoff just written:

```
/pickup
```

With no argument, pickup selects the newest handoff — which is the one checkpoint just created. It will:
- Read the handoff's Goal, Context Summary, Next Steps, Files to Load
- Verify referenced ADRs are still Accepted
- Diff TASKS.md against the snapshot
- Run drift detection against the handoff's pushed commit

You are now oriented in a fresh context with the full work thread intact.

### Phase 4 — Resume

Immediately after pickup's report, **continue working** on `RESUME_TASK`. Do not wait for the user to prompt again.

- If `RESUME_TASK == "continue current/next task"` (the default), pick up the first unchecked item in the handoff's "Next Steps" section (falling back to TASKS.md "Now / In Progress" if Next Steps is empty). Announce which item you're starting and begin executing it.
- If `RESUME_TASK` is user-specified, treat it as the working instruction for this turn and act on it directly. It should take precedence over the handoff's Next Steps when they conflict — the user passed it deliberately.
- If pickup flagged blockers, drift, or superseded ADRs, **stop and surface those first** before resuming. Auto-resume is convenience, not recklessness.
- If the handoff has no actionable next steps and the user gave no resume task, report ready-to-continue state and ask the user for direction — do not invent work.

## Limitations

- **`/clear` interrupts tool chains**: if the harness cannot chain `/clear` then `/pickup` within one user turn, phases 3 and 4 must be invoked by the user (or by a SessionStart hook) in the fresh session. Before clearing, print both the `/pickup` command and the resolved `RESUME_TASK` so the user can paste them into the fresh session verbatim.
- **Requires git-pushable branch**: handoff's `--push` commits to the current branch and pushes. If the branch can't be pushed (e.g. detached HEAD, no remote), handoff will report the failure and checkpoint stops at phase 1.
- **Does not update TASKS.md**: if Now/In Progress items look completed, handoff prompts the user to update TASKS.md before snapshotting — checkpoint inherits that behavior. Expect a prompt mid-phase-1 if the session made visible progress.

## When NOT to use

- Mid-task with in-flight ambiguity — finalise the decision first (via `/decision`), then checkpoint
- Very short sessions with no meaningful state — unnecessary ceremony, just `/clear`
- When the work isn't worth saving (exploratory dead-ends) — prefer plain `/clear`
- When you want to end the session entirely — use `/handoff` alone

## Conventions

- Always use `--push` in phase 1. The whole point is that pickup in phase 3 can do drift detection against a git-anchored handoff. A non-pushed handoff breaks the cycle.
- Phase 1 is blocking. Phase 2 is destructive. Do not reverse them.
- The skill does not modify TASKS.md or ADRs itself — it only delegates to handoff and pickup.

## Coherence with `handoff` and `pickup`

```
/handoff   → writes handoff, pushes, links ADRs, snapshots TASKS
/clear     → wipes context
/pickup    → reads handoff, audits ADRs, runs drift check
/checkpoint = handoff → clear → pickup → resume, in order, as one command
```

Checkpoint is a thin orchestrator plus an auto-resume step. The three underlying primitives do the real work; phase 4 is just "keep going on $ARGUMENTS (or the next queued task)".

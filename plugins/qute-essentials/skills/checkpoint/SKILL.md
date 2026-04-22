---
name: checkpoint
description: Atomic handoff → /clear → /pickup cycle for continuing the same work thread in a fresh context window. Use when the context is bloated, stale, or the model is drifting, and you want to reset without losing the work thread. Runs the handoff skill (saves + pushes a handoff doc), then /clear, then pickup in the fresh session. Pairs with handoff (writer) and pickup (reader).
argument-hint: "[goal]"
---

# /checkpoint

A context-reset ritual that preserves the work thread. Runs three phases atomically:

1. **Handoff** — save session state to `.claude/handoffs/<YYYY-MM-DD>-<slug>.md` and push it to the current branch so it's git-anchored.
2. **Clear** — wipe the context window via `/clear`.
3. **Pickup** — in the fresh context, load the just-saved handoff and audit its health.

Use this when:
- The conversation is long and the model's attention is degrading
- You're at a natural stopping point and want a clean slate without losing context
- You want an automated checkpoint before a risky operation so you can resume cheaply if needed

## Arguments

- `[goal]` — Optional. What the next phase of work should accomplish. Passed through to the handoff skill. If omitted, handoff infers the goal from conversation context.

## Behavior

Execute the three phases in order. Do **not** skip phase 1 — the whole point of checkpoint is that the clear is safe because the state was just saved.

### Phase 1 — Handoff

Invoke the `handoff` skill with `--push` and the provided goal:

```
/handoff --push [goal]
```

Wait for completion. Capture the handoff filename (e.g. `.claude/handoffs/2026-04-22-refactor-api.md`) and the commit SHA from the handoff output — these are the anchor for phase 3 drift detection.

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

## Limitations

- **`/clear` interrupts tool chains**: if the harness cannot chain `/clear` then `/pickup` within one user turn, phase 3 must be invoked by the user (or by a SessionStart hook) in the fresh session. The skill should print the pickup command before clearing so the user knows exactly what to type next.
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
/checkpoint = all three, in order, as one command
```

Checkpoint is the thin orchestrator. All real work happens in the three underlying primitives.

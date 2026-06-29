---
name: triage
description: Move a slice/task through a state machine — assign the right Paperclip status + dispatch label, reproduce bugs, request missing info, and prepare a task for an AFK agent or a human. Use for "triage this", "is this ready for an agent?", "prep the backlog", "what state is this in". Adapted from mattpocock/skills `triage`, mapped onto Paperclip's status enum. Stage 4 of the engineering workflow (docs/engineering-workflow.md).
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
---

# triage — slice → Paperclip status + dispatch

## Role
Stage 4 of `docs/engineering-workflow.md`. Decide each slice's readiness and set its
Paperclip status so the right actor (agent or human) picks it up.

## The state machine (workflow §5; binding in docs/agents/issue-tracker.md)
| Triage state | Paperclip status | Trigger |
|---|---|---|
| needs-triage | `backlog` | new task, not yet evaluated |
| needs-info | `blocked` + note | missing a decision/input; state the facts + the *specific* question |
| ready-for-agent | `todo` + `assigneeAgentId` + `auto-dev`/`auto-research` | fully specified, AFK-able |
| ready-for-human | `in_review` w/ user participant | needs a human judgment/backtest read (HITL) |
| wontfix | `cancelled` | |

## Method (5 steps)
1. **Gather context** — read the full slice + any prior triage notes; explore the code.
2. **Recommend** a category (bug/enhancement, as a title prefix — no Paperclip field)
   + a target state, with reasoning.
3. **Reproduce** (bugs only) — attempt to verify before labelling.
4. **Grill** — if under-specified, invoke `grill` to resolve before `ready-for-agent`.
5. **Apply** — set status / post the agent brief or the needs-info question.

## Rules
- **NEVER parallel-dispatch same-module slices.** Do not mark two slices that touch the
  same file(s) `ready-for-agent` at once — the orchestrator auto-advances them off bare
  `dev` and they collide (see `to-slices` #1 rule). One module in flight at a time, or
  consolidate to one task. Releasing a dependent slice before the prior **merges** (not
  just "done") branches it off a `dev` missing the prerequisite → conflict.
- **`ready-for-agent` means truly AFK-ready:** acceptance criteria + execution variant
  + the gate that proves it are all present. A methodology slice that needs a human
  backtest read is `ready-for-human`, not `ready-for-agent`.
- **needs-info templates state established facts + a specific actionable question** —
  never a vague "please clarify".
- **Any AI-posted triage comment opens with a disclaimer** that it was AI-generated.
- **Writes (status changes, comments) need Tom's OK.** Recommend the transition; apply
  on the go-ahead. Mind the self-wake gotcha (close `done` with no comment).

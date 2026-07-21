# ADR-0004: Linear is the task source; GitHub Issues are an issue record

**Status:** Accepted
**Date:** 2026-07-18

## Supersedes

[ADR-0003](0003-task-tracking-tiers-linear-jimek.md) — its "GitHub Issues as backlog"
clause. The tier structure (TASKS.md | Linear) and Jimek's Linear-monitoring stand.

## Context

ADR-0003 described GitHub Issues as "the repo-local backlog" under Linear. That keeps two
work queues alive — the duplicate-boards disease the regime exists to kill. The operator's
actual division: Linear is where work comes from; GitHub is where code problems are
recorded.

## Options Considered

1. **Issues as backlog under Linear** (ADR-0003 wording) — two pull surfaces
2. **Linear = task source; Issues = issue record only** — one queue, issues are data

## Decision

Option 2. **Linear is the task source**: all work items (tasks, planning, priority, agent
assignment) originate and live in Linear; Jimek monitors Linear for assigned tasks and
reads `jimek.yml` for how to run them; humans and agents pull work from Linear only.
**GitHub Issues track issues, not tasks**: bugs, defects, technical debt attached to the
code. An issue becomes work only when a Linear task references it ("fix issue #X") — the
Issues list is never a queue to pull from. TASKS.md Tier 1 for simple repos is unchanged
(there, the checklist IS the task source).

## Consequences

- (+) One work queue per repo, fleet-wide; Issues regain their meaning as a defect record
- (+) `/task`'s `github` backend stays useful — for filing/closing issue records
- (-) Filing a bug and scheduling it are two steps (issue + Linear task) — accepted;
  the separation is the point

## Amendment (2026-07-21): who talks to Linear directly vs via the dispatcher gateway

Credential ownership decides the path. **Fleet agents** (quark / iris / coach,
conductor workers, heartbeat, `fleet-track`) hold no Linear key and MUST write
through the dispatcher `/board` gateway — it is the single credential holder,
enforces the status vocabulary, fails closed, and dedups with the conductor's
claim logic. **Humans and interactive sessions acting as Tom** (Linear
app/MCP/API under Tom's own auth, PR magic-word linking) go to Linear directly;
the gateway is an agent surface, not a universal chokepoint. Also for the
record: `jimek.yml` in the Decision above is now `conductor.yml` (dispatcher
contract rename).

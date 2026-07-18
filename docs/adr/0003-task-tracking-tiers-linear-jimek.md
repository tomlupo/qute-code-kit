# ADR-0003: Task-tracking tiers — TASKS.md or Linear, with GitHub Issues as backlog

**Status:** Accepted
**Date:** 2026-07-18

## Context

Idea/task intake was scattered across five stores (Paperclip, GitHub Issues, vault
hypothesis notes, `research-topics.md`, per-line `RESEARCH_IDEAS.md`). Paperclip is
retired. Jimek is becoming the workflow conductor and needs one machine-watchable
assignment surface (the fleet board moves from GitHub to Linear).

## Options Considered

1. **GitHub Issues everywhere** — single system, but weak as a human planning board
2. **Linear everywhere** — heavy for tiny personal repos
3. **Tiered: TASKS.md | Linear, GitHub Issues as repo-local backlog** — per-repo choice
   declared in `docs/agents/issue-tracker.md`

## Decision

Option 3. Per repo, declared in `docs/agents/issue-tracker.md` (Matt's convention — his
skills and qute's `/task`/`/repo-status` read the same binding):

- **Simple/personal repos:** `TASKS.md` checklist (qute Tier 1). No remote ceremony.
- **Serious repos:** **Linear** is the human planning board and the agent-assignment
  surface. **GitHub Issues remain the repo-local backlog** — a Linear task may be
  "do issue #X"; issues hold the code-adjacent detail, Linear holds priority and flow.
- **Jimek:** reads `jimek.yml`/`jimek.yaml` to know *how* to run a declared agentic
  workflow, and **monitors Linear for assigned tasks** to know *what* to pick up.
  Trackers are the human/agent interface; jimek.yml is the execution contract.
- Paperclip bindings (e.g. dm-evo-lab's TOM-*) migrate to Linear per-repo.

One live store per repo for tasks; ideas never live in the research tree or in loose
markdown — they go to the declared tracker.

## Consequences

- (+) One intake per repo, one fleet board (Linear), one execution contract (jimek.yml)
- (+) `/task` stays useful in both tiers; Matt's `to-tickets`/`triage` bind to the same file
- (-) `/task`'s `pulse.sh` engine needs a Linear backend (follow-up); until then Linear
  routing is manual via MCP/API with the binding documented in `issue-tracker.md`
- (-) Linear↔GitHub cross-references are by convention (text links), not structured sync

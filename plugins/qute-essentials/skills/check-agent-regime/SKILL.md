---
name: check-agent-regime
description: >-
  Audit whether the repo has one clean agent regime or several competing ones. Concrete file
  checks: duplicate task stores, missing/contradictory docs/agents bindings, ADR location split,
  giant boot files, research-tree drift, idea files outside the tracker. Use when a repo feels
  messy, before onboarding, or when the user says "check the regime", "why is this repo a mess",
  "audit the agent setup". Read-only; reports verdict + fixes, never rewrites.
argument-hint: "[--json]"
---

# /check-agent-regime

Detect competing regimes with file evidence, not vibes. Read-only.

## Checks (all concrete)

**Task stores — exactly one live store:**
- `TASKS.md` live (unchecked items, no tombstone) *and* open GitHub Issues → duplicated
- `docs/agents/issue-tracker.md` missing while any tracker is in active use → unbound
- `issue-tracker.md` declares a system (Linear/GitHub/TASKS.md) that contradicts reality
  (e.g. declares Linear but retired Paperclip refs, or live TASKS.md alongside) → stale binding
- idea files in the tree (`RESEARCH_IDEAS.md`, `research-topics.md`, `docs/tasks/`,
  TODO-lists inside handoffs) → ideas outside the tracker

**Docs bindings (Matt conventions):**
- serious repo (remote + CI or >30 files) with no `docs/agents/` → unbound
- `CONTEXT.md` containing process/methodology instead of glossary → misused
- both `AGENTS.md` and `CLAUDE.md` with overlapping instructions → split boot
- boot file > ~150 lines of rules that belong in `docs/agents/*.md` → giant boot file
- ADRs split across `docs/adr/` and `docs/decisions/` (or scattered) without routing → split

**Planning ownership:**
- Matt skills installed but qute docs/skills claiming spec/ticket ownership → competing
- neither Matt nor an explicit standalone declaration in the boot file → unknown owner
  (fine for small repos; flag only with other messiness)

**Research repos (when `research/` exists):**
- delegate to `/research-status` and fold its drift findings in (stale index, unregistered
  lines, loose dated files, deliverables under `research/`)

**Orchestration:**
- `jimek.yml`/`jimek.yaml` present → tracker must be Linear or explicitly declared;
  GitHub bot/PR identity logic embedded in repo-local skills instead of Jimek → flag

## Output

```text
Agent regime: healthy | messy | broken

Planning owner:   matt | standalone | competing | unknown
Task store:       linear | github-issues | tasks-md | duplicated | unbound
Research regime:  standard | drifting | n/a
Orchestration:    jimek | none | misplaced

Findings (evidence per line: file → what's wrong)
Recommended fixes (ordered; name the skill that applies each: /setup-qute-repo,
/research-status --fix, /task migrate, manual)
```

`--json`: append a machine-readable object after the human summary.

## Do not

- Rewrite, move, or delete anything — this skill only reports.
- Create tracker items or issues automatically.
- Flag standalone mode (no Matt) as a defect on its own.

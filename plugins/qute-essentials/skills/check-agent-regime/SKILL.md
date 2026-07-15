---
name: check-agent-regime
description: >-
  Audit whether the current repo's agent setup is clean or messy, especially when qute-essentials is
  used together with Matt Pocock-style skills. Checks task-store duplication, qute-agent.yml policy,
  AGENTS/CLAUDE routing, CONTEXT.md, docs/agents, ADR location, handoff sprawl, and whether qute is
  competing with Matt for planning. Produces a health verdict and concrete cleanup actions.
argument-hint: "[--json]"
---

# /check-agent-regime

Audit the repo's agent operating model.

## Goal

Detect whether agents have one clear regime or several competing regimes.

Healthy target:

```text
Matt = planning
qute = runtime
docs/agents = repo rules
GitHub Issues or TASKS.md = one canonical task store
Jimek = GitHub PR/bot orchestration, if installed
```

## Checks

Inspect:

- `AGENTS.md`
- `CLAUDE.md`
- `.github/qute-agent.yml`
- `.github/qute-pr.yml`
- `CONTEXT.md`
- `docs/agents/`
- `docs/decisions/` or `docs/adr/`
- `TASKS.md`
- `docs/tasks/`
- `.claude/handoffs/`
- open GitHub Issues if available

## Flag as messy

Report an issue when:

1. `TASKS.md` and GitHub Issues are both active canonical stores.
2. Long-lived task boards exist in `docs/tasks/`, handoff files, and GitHub Issues at the same time.
3. `planningOwner: matt` is absent or unclear while Matt skills are expected.
4. qute docs imply qute owns generic specs/ticket decomposition.
5. `CONTEXT.md` is missing or contains process/methodology instead of glossary terms.
6. `docs/agents/` is missing in a serious repo.
7. `docs/agents/` contains methodology instead of behavior rules.
8. ADRs are split across multiple incompatible locations without routing rules.
9. handoff/pickup notes are not linked to canonical issues/specs.
10. GitHub PR/bot operations are embedded in qute core instead of routed to Jimek or a GitHub-flow plugin.

## Output

Return:

```text
Agent regime: healthy | messy | broken

Canonical planning owner: matt | qute | custom | unknown
Canonical task store: github-issues | tasks-md | unknown | duplicated
Runtime owner: qute | unknown
GitHub orchestration owner: jimek | qute | unknown

Findings
1. ...

Recommended fixes
1. ...
```

If `--json` is passed, emit a final machine-readable JSON object after the human summary.

## Do not

- Do not rewrite files automatically unless the user explicitly asks.
- Do not create issues automatically.
- Do not delete task files.
- Do not migrate tasks without human approval.

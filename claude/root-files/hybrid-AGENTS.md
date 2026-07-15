# AGENTS.md

This repo uses a Matt + qute hybrid agent model.

## Operating model

- Matt-style skills organize engineering work: clarify, spec, tickets, implement, TDD, code review.
- qute-essentials provides safety, observability, task tracking, handoff, review, audit, and release tooling.
- Repo-local docs under `docs/agents/` define task-specific rules of engagement.

## Read first

Before changing code, read:

- `CONTEXT.md` — domain glossary, if present
- `docs/agents/README.md` — agent-rule index, if present
- the relevant task-specific rule file under `docs/agents/`

If this repo has no `docs/agents/` yet, use `docs/architecture/matt-qute-hybrid-stack.md` from qute-code-kit as the intended pattern.

## Skill ownership

Use Matt-style skills for:

- grilling / clarification
- spec creation
- ticket decomposition
- implementation orchestration
- TDD
- architecture review
- code review against a spec

Use qute skills for:

- guards and safety checks
- repo status and task tracking
- test and audit execution
- ADR creation via `/decision`
- handoff and pickup
- independent review
- release via `/ship`

## Task tracking

There must be one canonical task store.

- Small repos: `TASKS.md` via qute `/task`
- Serious repos: GitHub Issues
- Temporary Matt tickets: drafting artifacts only until promoted

Do not keep duplicate long-lived task lists.

## Workflow defaults

For fuzzy work:

```text
/grill-with-docs
/to-spec
/to-tickets
```

Then publish accepted tickets into the canonical task store.

For small work:

```text
/task
/test
/ship
```

For durable decisions:

```text
/decision
```

For release:

```text
/test
/audit
/qute-review
/ship
```

## Safety

qute guards remain active underneath all Matt-style workflows. Do not bypass destructive, secret, audit, or PR-flow guards unless the user explicitly approves the bypass and the reason is documented.

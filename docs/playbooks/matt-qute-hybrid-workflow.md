# Matt + qute Hybrid Workflow

Use this playbook when a repository should be organized by Matt-style engineering skills while keeping qute as the safety and release layer.

## Mental model

```text
1. Matt clarifies and decomposes work.
2. qute tracks, guards, audits, reviews, and ships it.
3. Repo-local docs/agents tell both systems how to behave in this domain.
```

## Setup in a target repo

### 1. Install qute-essentials globally

```bash
claude plugin marketplace add tomlupo/qute-code-kit
claude plugin install qute-essentials@qute-marketplace
```

Use qute for:

- `/guard`
- `/test`
- `/audit`
- `/decision`
- `/task`
- `/repo-status`
- `/handoff`
- `/pickup`
- `/qute-review`
- `/ship`

### 2. Install Matt skills per repo

Use Matt's installer or plugin, then run his setup skill.

```bash
npx skills@latest add mattpocock/skills
```

Then in the agent:

```text
/setup-matt-pocock-skills
```

Use Matt for:

- `/grill-with-docs`
- `/to-spec`
- `/to-tickets`
- `/implement`
- `/tdd`
- `/code-review`
- `/improve-codebase-architecture`
- `/wayfinder`

### 3. Add repo-local agent rules

Create:

```text
docs/agents/
  README.md
  domain.md
  issue-tracker.md
  task-tracking.md
  change-management.md
```

For investment/advisory repos, add:

```text
docs/agents/
  advisory-process.md
  data-contracts.md
  daily-production.md
  output-controls.md
  compliance-boundaries.md
```

## Daily workflow

### Small task

Use qute only.

```text
/task "Fix report typo"
/test
/qute-review   # optional
/ship          # if releasable
```

### Feature or methodology change

Use Matt first, qute second.

```text
/grill-with-docs
/to-spec
/to-tickets
```

Then publish the accepted tickets into the canonical task store:

```text
/task "Implement accepted ticket 1"
/repo-status
```

Implementation:

```text
/implement
/test
/audit
/code-review
/qute-review
/ship
```

### Huge ambiguous project

```text
/wayfinder
```

Use the result to create investigation issues. Track them with qute/GitHub, not separate long-lived local plans.

### Production bug

Use the domain-specific diagnostic skill if available. Otherwise:

```text
/diagnosing-bugs
/task "Fix production run issue"
/test
/qute-review
/ship
```

For investment/advisory repos, prefer a specific skill such as:

```text
/diagnose-production-run
```

## Canonical task store

Choose one canonical task store per repo.

Recommended:

| Repo type | Canonical task store |
|---|---|
| Small personal repo | `TASKS.md` via qute `/task` |
| Serious production repo | GitHub Issues |
| Advisory / investment repo | GitHub Issues |
| Temporary spike | scratch/spec files, then promote or delete |

Matt ticket files are drafting artifacts unless explicitly promoted.

## Avoid this

```text
Matt tickets
+ TASKS.md
+ GitHub Issues
+ handoff todo list
+ docs/tasks plan
```

That creates five boards and no truth.

## Good handoff rule

A qute handoff should reference canonical tasks, not duplicate them.

Good:

```text
Continue GitHub issues #42, #43. Current branch: feat/selection-quality-gate.
```

Bad:

```text
TODO: rewrite all ticket contents in the handoff.
```

## Release closure

Use qute `/ship` as the release boundary.

Before `/ship`:

- accepted tickets are implemented
- tests pass or bypass is explicitly documented
- audit is run where relevant
- qute review has passed or human chose to bypass
- decisions have ADRs if material

After `/ship`:

- changelog/tag is canonical release record
- completed `TASKS.md` sections may be wiped by qute in Python mode
- GitHub Issues should be closed or linked from release notes

## Hybrid command table

| Situation | Start with | Finish with |
|---|---|---|
| Fuzzy feature | Matt `/grill-with-docs` | qute `/task`, `/ship` |
| Clear small fix | qute `/task` | qute `/test`, `/ship` |
| Architecture mess | Matt `/improve-codebase-architecture` | selected tickets tracked by qute |
| Production bug | diagnostic skill or Matt `/diagnosing-bugs` | qute `/test`, `/qute-review` |
| Durable decision | Matt may discover it | qute `/decision` records it |
| PR/release | qute | qute |

## Summary

The hybrid rule is simple:

```text
Matt owns planning clarity.
qute owns operational reliability.
Repo docs own local domain rules.
```

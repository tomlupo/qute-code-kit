# Task Tracking

This repo uses one canonical task store.

## Canonical store

Choose one:

```text
TASKS.md
```

or:

```text
GitHub Issues
```

Do not use both as active sources of truth.

## Matt + qute rule

Matt-style skills may create draft specs and draft tickets.

Accepted tickets must be promoted into the canonical task store before implementation.

```text
Matt /to-spec, /to-tickets
  -> draft tickets
  -> accepted tickets
  -> qute /task or GitHub Issues
```

qute owns ongoing tracking via:

- `/task`
- `/repo-status`
- `/handoff`
- `/pickup`
- `/ship`

## Temporary artifacts

Allowed temporary artifacts:

- scratch specs
- draft ticket breakdowns
- investigation notes
- handoff summaries

Temporary artifacts must link to canonical tasks once work is accepted.

## Handoff rule

Handoffs should reference canonical task IDs instead of copying the task board.

Good:

```text
Continue GitHub issues #12 and #13. Branch: feat/example.
```

Bad:

```text
Duplicate the full issue descriptions into the handoff and treat them as new tasks.
```

## Release closure

When work ships:

- close or link shipped issues
- let `/ship` produce the changelog/tag where supported
- do not maintain separate completed-task archives unless the repo explicitly requires them

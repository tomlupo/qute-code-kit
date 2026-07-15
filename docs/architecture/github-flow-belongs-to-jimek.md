# GitHub verbs belong under Jimek workflows

## Decision

`qute-essentials` should not be the long-term owner of GitHub PR transport, bot identity, or review-gate orchestration.

Those concerns should live under **Jimek** when they are part of a declared autonomous workflow. Jimek is the workflow conductor driven by `jimek.yml` / `jimek.yaml`; GitHub PR and review operations are one verb family inside that conductor, not Jimek's whole identity.

## Why

`qute-essentials` should remain the universal local runtime layer:

- guards
- observability
- tests and audits
- task-store operations
- handoff / pickup
- ADR writing
- local independent review
- release hygiene

Jimek owns autonomous workflow orchestration:

- workflow graph from `jimek.yml` / `jimek.yaml`
- agent assignment
- dependency ordering
- parallel work
- run status
- multi-agent handoff
- PR creation as a workflow action
- native review-object posting as a workflow action
- review-gate orchestration

GitHub bot identity and PR posting have the same shape as the rest of Jimek:

- a workflow step needs to open or update a PR
- another step needs an independent review
- the conductor needs machine-readable state
- identity must fail loud instead of falling back to a human account
- repo policy controls merge/review behavior

That is workflow orchestration, not core local runtime.

## Consequence

Keep `/qute-review` in qute-essentials as a local-first independent review skill.

Treat `/qute-coder` and `/qute-reviewer` as transitional compatibility bridges until Jimek owns equivalent verbs inside `jimek.yml` workflows:

- PR creation transport
- bot-authored review posting
- `.github/qute-pr.yml` / successor policy mapping
- review-gate orchestration
- conductor-friendly JSON verb contracts

## Target split

```text
qute-essentials
  /qute-review      # local-first review analysis/verdict
  /test             # verification
  /audit            # dependency/security audit
  /ship             # release hygiene
  /decision         # ADRs
  /task             # canonical task-store operations
  guards/hooks      # safety + observability

jimek
  reads jimek.yml / jimek.yaml
  assigns agents
  runs workflow graph
  coordinates dependencies and handoffs
  opens PRs as workflow actions
  posts native review objects as workflow actions
  checks review gates as workflow actions
  exposes machine-readable workflow state
```

## Example relationship

```yaml
workflow:
  name: implement-feature
  repo: tomlupo/dm-evo

steps:
  - id: plan
    run: matt.to-spec
  - id: tickets
    run: matt.to-tickets
  - id: implement
    run: agent.implementer
  - id: local_review
    run: qute.review
  - id: open_pr
    run: github.open-pr
  - id: post_review
    run: github.post-review
```

In that example, `github.open-pr` and `github.post-review` are Jimek-executed verbs inside a declared workflow.

## Transition rule

Until Jimek has the equivalent flow, qute may keep compatibility shims, but documentation should describe them as **workflow/GitHub bridges for Jimek**, not qute core.

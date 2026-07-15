# GitHub flow belongs to Jimek

## Decision

`qute-essentials` should not be the long-term owner of GitHub PR transport, bot identity, or review-gate orchestration.

Those concerns belong to **Jimek** or a dedicated GitHub-flow plugin owned by Jimek.

## Why

`qute-essentials` should remain the universal runtime layer:

- guards
- observability
- tests and audits
- task-store operations
- handoff / pickup
- ADR writing
- local independent review
- release hygiene

GitHub bot identity and PR posting are orchestration concerns:

- open PR as an app/bot identity
- post a native review object as a different bot identity
- assign/request human review
- enforce review-gate CI
- coordinate dispatcher/local execution modes
- emit machine-readable verb contracts for a conductor

Those are Jimek-shaped responsibilities.

## Consequence

Keep `/qute-review` in qute-essentials as a local-first independent review skill.

Treat `/qute-coder` and `/qute-reviewer` as transitional GitHub-flow bridges until Jimek owns:

- PR creation transport
- bot-authored review posting
- `.github/qute-pr.yml` / successor policy
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
  create PR as bot
  post review as bot
  assign/request human review
  enforce PR gate
  coordinate dispatcher/local execution
  expose machine-readable GitHub verbs
```

## Transition rule

Until Jimek has the equivalent flow, qute may keep compatibility shims, but documentation should describe them as **GitHub-flow bridges**, not qute core.

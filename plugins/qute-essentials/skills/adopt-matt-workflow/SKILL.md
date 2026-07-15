---
name: adopt-matt-workflow
description: >-
  Configure the current repo so qute-essentials works as the runtime layer under a Matt Pocock-style
  planning workflow. Use when a repo should use Matt skills for grilling/specs/tickets/implementation
  and qute for guards, task store, handoff, ADRs, review, tests, audits, and release. Creates or updates
  qute-agent.yml, AGENTS.md routing, docs/agents/task-tracking.md, and docs/agents/domain.md as needed.
argument-hint: "[--task-store github-issues|tasks-md] [--dry-run]"
---

# /adopt-matt-workflow

Configure a repo for the hybrid regime:

```text
Matt = planning and engineering flow
qute = runtime, safety, tracking, review, release
docs/agents = repo-specific operating rules
```

## Behavior

1. Inspect the repo for:
   - `AGENTS.md`
   - `CLAUDE.md`
   - `CONTEXT.md`
   - `docs/agents/`
   - `.github/qute-agent.yml`
   - `TASKS.md`
   - GitHub remote / issue usage
2. Choose a task store:
   - `github-issues` for production, advisory, or team repos
   - `tasks-md` for small/private repos
   - explicit `--task-store` wins
3. Create or update:
   - `.github/qute-agent.yml`
   - `docs/agents/task-tracking.md`
   - `docs/agents/domain.md`
   - `AGENTS.md` routing block
4. Preserve existing project-specific instructions. Do not overwrite without showing a diff.
5. Report what changed and what still needs a human decision.

## Required policy

When `planningOwner: matt`:

- qute skills must not invent a parallel generic planning system.
- `/task` publishes or tracks accepted tickets; it does not decompose unclear work.
- `/repo-status` reads the canonical task store; it does not maintain a separate board.
- `/handoff` links to canonical issues/specs; it does not become a second roadmap.
- `/decision` remains the ADR writer for durable choices.
- `/qute-review` remains local-first independent review.
- GitHub PR/bot identity operations belong to Jimek or another GitHub-flow plugin, not qute-essentials core.

## Suggested `AGENTS.md` block

```md
## Hybrid agent regime

This repo uses Matt skills for planning and engineering flow, and qute-essentials for runtime safety,
tracking, review, and release.

Before material work, read:

- `CONTEXT.md`
- `.github/qute-agent.yml`
- `docs/agents/task-tracking.md`
- `docs/agents/domain.md`
- task-specific files under `docs/agents/`

Use Matt-style skills for unclear or material work:

- `/grill-with-docs`
- `/to-spec`
- `/to-tickets`
- `/implement`
- `/tdd`
- `/code-review`

Use qute for runtime operations:

- `/guard`
- `/task`
- `/repo-status`
- `/handoff`
- `/pickup`
- `/decision`
- `/test`
- `/audit`
- `/qute-review`
- `/ship`
```

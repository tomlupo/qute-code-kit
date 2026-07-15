# Lean qute target

This document defines the target organization for `qute-code-kit` after adopting Matt-compatible mode.

## Goal

Make qute feel like a small, dependable runtime layer rather than a competing workflow framework.

Target mental model:

```text
Matt skills        = planning, spec, tickets, implementation discipline
qute-essentials   = safety, observability, task-store operations, test/audit, review, release
Jimek             = GitHub transport, bot identities, native review objects, orchestration
qute personal kit = optional specialist tools copied into repos only when needed
```

## Keep qute-essentials core small

The plugin core should be only what is broadly useful in almost every coding repo.

### Core hooks

- destructive guard
- secrets guard
- Lakera prompt-injection guard
- Langfuse tracing
- auto-audit after dependency changes
- ntfy notifications
- ruff formatting
- skill-use logging

### Core skills

- `/guard`
- `/test`
- `/audit`
- `/decision`
- `/task`
- `/repo-status`
- `/handoff`
- `/pickup`
- `/ship`
- `/qute-review`
- `/adopt-matt-workflow`
- `/check-agent-regime`
- `generating-commit-messages`

These are runtime, continuity, review, release, and safety tools.

## Transitional skills

These remain available for backward compatibility but should not be treated as qute core:

- `/qute-coder`
- `/qute-reviewer`
- `/jimek-onboard`

Target owner: Jimek.

Transition approach:

1. Keep them in qute until Jimek has working replacements.
2. Mark them as compatibility bridges in docs and plugin description.
3. Move GitHub App token logic, PR creation, native review-object posting, and review-gate orchestration into Jimek.
4. Leave small qute wrappers only if useful, for example `/jimek-open-pr` that calls Jimek.

## Personal kit should become bundles, not a grab bag

Current `claude/` contents are useful, but target repos should not copy everything.

Organize conceptually into bundles:

```text
claude/bundles/
  quant-research.md
  advisory-production.md
  python-engineering.md
  web-product.md
  visual-design.md
```

Each bundle should list:

- recommended skills
- optional agents
- optional MCP configs
- settings profile
- when not to install the bundle

This keeps `INVENTORY.md` as the full catalog, while bundles become the decision layer.

## Stop adding framework-like features to qute

Avoid adding qute-native versions of:

- generic spec generation
- ticket decomposition
- architecture planning
- product discovery
- implementation process
- long-form roadmap management

Those belong to Matt skills or repo-local `docs/agents` rules.

## Reduce duplicate review concepts

Review layers should be clearly separated:

```text
Matt /code-review
  = spec correctness + code standards during implementation

qute /qute-review
  = independent local review before merge/release, optionally domain-aware

Jimek github.post-review
  = post a native GitHub review object using bot identity
```

`/gbu` should either:

- remain a lightweight critique helper, or
- be deprecated in favor of `/qute-review` for serious review.

It should not become a second full review framework.

## Task tracking rule

qute may operate the task store, but it should not invent the plan.

```text
Matt may draft specs/tickets.
qute publishes or updates the canonical task store.
GitHub Issues or TASKS.md are the source of truth.
```

Small repo:

```text
TASKS.md is canonical.
```

Production/advisory repo:

```text
GitHub Issues are canonical.
TASKS.md is absent or a pointer.
```

## Documentation target

Top-level docs should answer distinct questions:

```text
README.md
  what this repo is and how to install/use it

INVENTORY.md
  full catalog of all kit pieces

docs/architecture/
  ownership, target structure, boundaries

docs/playbooks/
  how to operate workflows

docs/cheatsheets/
  reference only

docs/prompts/
  reusable prompt snippets

claude/root-files/
  starter AGENTS.md / CLAUDE.md files for target repos

templates/
  files copied into target repos
```

## Recommended cleanup sequence

1. Merge the Matt-compatible mode PR.
2. Merge the Jimek GitHub-flow ownership PR.
3. Add bundle manifests for the personal kit.
4. Mark `/qute-coder`, `/qute-reviewer`, and `/jimek-onboard` as transitional in plugin docs.
5. Adjust `/task`, `/repo-status`, `/handoff`, and `/pickup` docs to obey `qute-agent.yml`.
6. Decide whether `/gbu` stays as lightweight critique or is deprecated.
7. Only then remove or move code.

Do not delete working GitHub-flow pieces before Jimek replacements exist.
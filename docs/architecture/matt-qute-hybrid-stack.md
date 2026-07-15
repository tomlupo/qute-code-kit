# Matt + qute Hybrid Stack

This document defines the intended relationship between Matt Pocock-style skills and qute-code-kit.

The goal is to make qute complementary to a more organized Matt-style engineering workflow, not a competing process framework.

## Design principle

Use Matt-style skills for work definition and decomposition.

Use qute-essentials for runtime safety, release hygiene, observability, PR controls, and session continuity.

Use domain-specific qute skills only where the generic Matt workflow needs subject-matter guardrails.

```text
Matt skills       = planning and engineering method
qute-essentials   = safe agent runtime and release system
qute domain kit   = quant / investment / UX / data specializations
repo docs/agents  = local rules of engagement
```

## Layer model

| Layer | Owner | Purpose | Examples |
|---|---|---|---|
| 1. Runtime safety | qute-essentials | Block or trace dangerous agent behavior | `/guard`, destructive guard, secrets guard, Lakera, Langfuse, ntfy |
| 2. Work shaping | Matt skills | Turn intent into a clean engineering plan | `/grill-with-docs`, `/to-spec`, `/to-tickets`, `/wayfinder` |
| 3. Implementation discipline | Matt + qute | Build with feedback loops and review | Matt `/implement`, `/tdd`, `/code-review`; qute `/test`, `/audit`, `/qute-review` |
| 4. Repo operation | qute | Track work, hand off context, ship releases | `/task`, `/repo-status`, `/handoff`, `/pickup`, `/ship` |
| 5. Domain controls | qute personal kit / repo-local skills | Add investment, quant, data, brand, or UX-specific checks | `investment-research-formal`, `backtest`, `review-model-portfolio-change` |

## Default command ownership

| Job | Preferred owner | Notes |
|---|---|---|
| Clarify fuzzy work | Matt `/grill-with-docs` | qute should not replace this with ad-hoc prompting |
| Create a spec | Matt `/to-spec` or qute `qrd` when quant-specific | Matt owns the generic flow; qute may provide domain template depth |
| Break into tickets | Matt `/to-tickets` | Tickets should become canonical qute/GitHub tasks after acceptance |
| Track small todos | qute `/task` | qute owns the board, not the plan-generation process |
| Show repo status | qute `/repo-status` | Reads task store and git/worktree state |
| Implement | Matt `/implement` | qute guards and hooks remain active underneath |
| Run tests | qute `/test` | Matt may request tests, qute owns common test execution conventions |
| Dependency/security audit | qute `/audit` | Runtime/release concern |
| Record durable decision | qute `/decision` | Matt/domain-modeling may discover the need; qute writes ADRs consistently |
| Code review | Matt `/code-review` then qute `/qute-review` | Local spec review first; independent adversarial gate second |
| Release | qute `/ship` | qute owns changelog/version/tag/release hygiene |
| Session continuation | qute `/handoff` and `/pickup` | Avoid duplicate handoff systems |

## Task tracking rule

Matt may generate specs and tickets, but qute owns the canonical task store.

Recommended default:

```text
Matt /to-spec, /to-tickets
  -> accepted tickets
  -> qute /task or GitHub Issues
  -> qute /repo-status reads canonical board
```

Avoid long-lived duplicate task lists across `TASKS.md`, GitHub Issues, local Matt ticket files, handoffs, and scratch plans.

## Docs layout in target repos

Target repos should use this split:

```text
AGENTS.md / CLAUDE.md
  = boot instructions and routing

CONTEXT.md
  = domain glossary only

docs/agents/*.md
  = agent behavior rules

docs/methodology/*.md
  = actual methodology / process

docs/decisions/*.md
  = durable decisions and trade-offs

docs/runbooks/*.md
  = operational procedures
```

This is the point where Matt's organization style should influence qute-managed repos: qute should stop growing giant CLAUDE files and instead route the agent to small rule files.

## What qute should not do

qute should not become a second planning framework.

Avoid adding qute skills that duplicate these Matt roles:

- generic grilling
- generic spec creation
- generic ticket decomposition
- generic implementation orchestration
- generic domain-modeling loop

qute skills should be added when they provide one of:

- safety enforcement
- release or PR mechanics
- session continuity
- domain-specific checks
- data/source integrations
- quant or investment templates
- visual/UX assets

## Migration direction

When a qute repo feels messy, the fix is not more qute skills. The fix is:

1. Install qute-essentials for guards and lifecycle.
2. Install Matt skills for planning and engineering flow.
3. Add `docs/agents/` rules so the repo decides which docs matter.
4. Keep qute domain skills narrow and explicit.
5. Promote only the qute skills that are universally useful into the plugin.

## Summary

The hybrid stack is:

```text
Matt creates the plan.
qute makes execution safe, observable, reviewable, and shippable.
Repo-local docs/agents keep both aligned with the actual domain.
```

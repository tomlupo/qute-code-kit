# Skill router — which skill, when

The one file to follow for discipline (the `ask-matt` pattern, extended to the whole
stack). Read top-down: find your situation, run what's listed, in order.
Doctrine behind it: ADR-0001..0004 in `docs/adr/`.

```text
Matt skills   = planning spine (grill → spec → tickets → implement → TDD → review)
qute          = runtime (guards, tests, ADRs, review, release, continuity, research)
fleet-track   = the task board (Linear behind the dispatcher gateway)
Jimek         = autonomous dispatch (assign on the board; it does the rest)
```

## Starting work

| Situation | Run |
|---|---|
| Fuzzy / underspecified feature | Matt `/grill-with-docs` → `/to-spec` → `/to-tickets` → publish accepted tickets: `fleet-track new … --agent X --priority PN` (`--epic` / `--standalone` / `--is-epic`) |
| Clear small fix | `fleet-track new` (or grab the existing task) → just do it |
| Huge ambiguous project | Matt `/wayfinder` → investigation tasks on the board |
| Bug in production | Matt `/diagnosing-bugs` (or the repo's domain diagnostic) → `fleet-track new` |
| New research question (lab repo) | `/research-line <name>` — never analyze outside a registered line |
| Delegate to an agent | `fleet-track new … --agent <name>` — Todo + assignment is the doorbell; Jimek/heartbeat takes it from there |
| Resuming a previous session | `/pickup`; check `fleet-track board` |

## During work

| Situation | Run |
|---|---|
| Implementing a spec'd change | Matt `/implement` (+ `/tdd` for logic-heavy) — qute guards stay on underneath |
| Branch naming | `<you>/TOM-<n>-<slug>` — Linear auto-links the PR and drives issue state |
| A durable decision crystallizes ("let's lock in…") | `/decision` → `docs/adr/` |
| Research result lands | `/finding` — the ONLY way results are written (forces a verdict, updates the index) |
| Need tests run / diagnosed | `/test` |
| Dependency or security concern | `/audit` |
| Lost in a research repo | `/research-status` — regenerates the index, flags drift |
| Repo feels like it has competing regimes | `/check-agent-regime` |

## Finishing work

| Situation | Run |
|---|---|
| Code review, spec-aware (during dev) | Matt `/code-review` |
| Independent pre-merge review | `/qute-review` (the review-gate verdict) |
| PR merged, task done | automatic via branch magic words; else `fleet-track done <repo> <n>` |
| Confirmed research finding, material | `/promote` → ADR + prod PR / wiki |
| Release | `/ship` (plugin or Python mode auto-detected) |
| Session ending mid-work | `/handoff` — reference board tasks, never duplicate them |

## Setup & meta

| Situation | Run |
|---|---|
| New repo onboarding | Matt `/setup-matt-pocock-skills` → qute `/adopt-matt-workflow` (adds qute deltas; `--research` for lab repos) |
| Where do ideas go | The board (`fleet-track new`, Backlog) — never loose markdown, never a GitHub issue |
| GitHub Issues | Records only (bugs/defects/evidence; `--to github` in `/task`) — NEVER a queue to pull from |
| Something feels off with the assistant | `/wtf` (captures the failure into guardrails) |
| Blunt critique of an artifact | `/gbu` |

## Anti-patterns (the sprawl this file exists to prevent)

- Analysis files outside `research/<line>/` → route through `/research-line` + `/finding`
- A second task list (TASKS.md next to the board, TODOs in handoffs, `RESEARCH_IDEAS.md`) → one store per repo, board for the fleet
- Talking to Linear/GitHub tracker APIs directly → everything goes through `fleet-track` / the dispatcher gateway
- Ever-growing CLAUDE.md rules → move rules to `docs/agents/*.md`, ADRs to `docs/adr/`

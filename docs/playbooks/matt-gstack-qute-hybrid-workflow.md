# Matt + gstack + qute hybrid workflow

Use this playbook when Matt Pocock skills, gstack, and qute-essentials are all available in the same repo.

## Goal

Use each system for what it does best without creating duplicate plans, reviews, task boards, or release flows.

```text
Matt skills      = primary engineering workflow
gstack           = product, design, browser QA, DX, security specialists
qute-essentials  = local safety, test/audit, independent review, release hygiene
Jimek/Symphony   = optional autonomous orchestration
```

## Core rule

Do not run Matt and gstack as competing end-to-end workflows for the same task.

Choose one owner for:

- planning
- implementation flow
- final shipping

Recommended default:

```text
Matt owns planning and implementation.
gstack provides specialist reviews and browser-driven work.
qute provides runtime safety and final validation.
```

## Responsibility map

| Need | Primary tool | Notes |
|---|---|---|
| Clarify engineering work | Matt `/grill-with-docs` | Default for material repo work |
| Product reframing | gstack `/office-hours` | Use before Matt only when product framing is genuinely unclear |
| Engineering spec | Matt `/to-spec` | Avoid a second gstack-generated generic plan |
| Ticket decomposition | Matt `/to-tickets` | Publish accepted tickets into the canonical task store |
| Implementation loop | Matt `/implement` | Use `/tdd` where practical |
| Engineering code review | Matt `/code-review` | Spec correctness and code standards |
| Product/CEO challenge | gstack `/plan-ceo-review` | Optional specialist review |
| Design review | gstack `/plan-design-review`, `/design-review` | Best for UI-facing work |
| Browser QA | gstack `/qa`, `/qa-only` | Use against a real local/staging URL |
| Debugging | Pick one: gstack `/investigate` or Matt `/diagnosing-bugs` | Do not run both unless the first investigation was inconclusive |
| Security review | gstack `/cso` | Threat model and application-security review |
| Tests and dependency audit | qute `/test`, `/audit` | Final local verification |
| Independent domain-aware review | qute `/qute-review` | Final acceptance gate before PR/release |
| Versioned package/plugin release | qute `/ship` | Prefer for changelog/version/tag workflows |
| Autonomous multi-agent run | Jimek or Symphony | Executes declared workflows; does not replace repo methodology |

## Avoid duplicate workflow commands

Do not stack all planning commands together:

```text
/office-hours
/grill-with-docs
/autoplan
/to-spec
/plan-eng-review
/to-tickets
```

That produces overlapping plans and stale documents.

Recommended choices:

```text
Engineering-first task:
  /grill-with-docs -> /to-spec -> /to-tickets

Product-first web task:
  /office-hours -> /to-spec -> /to-tickets
```

Do not use gstack `/autoplan` when a Matt spec/ticket flow is already active.

## Recommended workflows

### 1. Normal engineering feature

```text
Matt /grill-with-docs
Matt /to-spec
Matt /to-tickets
publish tickets to Linear, GitHub Issues, or TASKS.md
Matt /implement
Matt /code-review
qute /test
qute /audit
qute /qute-review
open PR through the repo's configured transport
```

Use this for:

- data pipelines
- APIs
- portfolio logic
- fund-selection logic
- internal tooling
- refactors with clear acceptance criteria

### 2. Web or dashboard feature

```text
gstack /office-hours                 # only if product framing is unclear
Matt /to-spec

gstack /plan-design-review          # UI-specific plan review
Matt /to-tickets
Matt /implement
Matt /code-review

gstack /qa                           # real browser test
gstack /design-review                # optional visual/design correction
qute /test
qute /audit
qute /qute-review
```

Use gstack specialists without handing over the entire workflow.

### 3. Production bug

Choose one diagnosis method:

```text
gstack /investigate
```

or:

```text
Matt /diagnosing-bugs
```

Then:

```text
Matt /implement
Matt /code-review
qute /test
qute /qute-review
```

For quant/advisory production issues, combine this with repo-local diagnostics rules in `docs/agents/`.

### 4. Security-sensitive change

```text
Matt /grill-with-docs
Matt /to-spec
Matt /to-tickets
Matt /implement
Matt /code-review

gstack /cso
qute /audit
qute /test
qute /qute-review
```

Examples:

- authentication
- secrets and credential handling
- broker/exchange adapters
- production deployment changes
- client data
- external tool or webhook ingestion

### 5. Research-to-production change

```text
repo-specific /promote-research-to-production
Matt /grill-with-docs
Matt /to-spec
Matt /to-tickets
Matt /implement
Matt /code-review
repo-specific investment review
qute /test
qute /audit
qute /qute-review
```

Use gstack only where it adds specialist value, such as browser QA for dashboards or `/cso` for a new external integration.

### 6. Small chore

Do not invoke the full stack.

```text
qute /task
make the small change
qute /test
```

Examples:

- typo
- small documentation correction
- narrow configuration fix
- known one-line bug

### 7. Architecture cleanup

```text
Matt /improve-codebase-architecture
choose one bounded improvement
Matt /to-spec
Matt /to-tickets
Matt /implement
Matt /code-review
qute /test
qute /qute-review
```

Do not combine this with gstack `/autoplan` or another broad redesign pass.

## Review layers

Keep each review layer distinct:

```text
Matt /code-review
  Did the implementation satisfy the spec cleanly?

gstack specialist review
  Is the product, design, browser behavior, DX, or security good?

qute /qute-review
  Should this repo accept the change under its domain, data, and production rules?
```

Running all three is appropriate only for material changes. For ordinary backend work, Matt plus qute is usually enough.

## Shipping ownership

gstack and qute both expose `/ship`, but they solve different problems.

Recommended convention:

```text
gstack /ship
  PR-oriented application flow when explicitly selected

qute /ship
  versioned release flow: changelog, package/plugin version, tag, release hygiene
```

A repo should document one default shipping owner in `docs/agents/` or `AGENTS.md`.

Do not run both `/ship` commands automatically for the same task.

## Root instruction snippet

Add something like this to `AGENTS.md` or `CLAUDE.md`:

```md
## Agent workflow

Use Matt Pocock skills as the default planning and implementation workflow.

Use gstack selectively for:

- product and CEO review
- design planning and review
- browser QA
- developer-experience testing
- security review

Do not use gstack `/autoplan` when a Matt spec/ticket workflow is already active.
Do not create a second plan, spec, or task board for the same work.

Use qute-essentials for guards, task-store operations, tests, audits, ADRs,
independent review, handoff/pickup, and release hygiene.
```

## Quant and advisory repos

Recommended gstack subset:

```text
/investigate
/cso
/qa
/qa-only
/browse
/retro
```

For UI/dashboard modules, also consider:

```text
/plan-design-review
/design-review
/plan-devex-review
/devex-review
```

Usually skip these when Matt owns the workflow:

```text
/autoplan
/plan-eng-review
/review
/ship
```

unless the task explicitly selects gstack as the workflow owner.

## Final mental model

```text
Matt      organizes the engineering work.
gstack     supplies specialist product/design/browser/security roles.
qute       protects and validates the local execution.
Jimek or Symphony orchestrates autonomous runs when configured.
```

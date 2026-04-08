---
paths:
  - "docs/decisions/**/*"
---

# Decision Records

Lightweight decision records (ADRs) for capturing significant choices — architectural, methodological, data, or research.

## When to Record a Decision

Record a decision when:
- Choosing between competing libraries, frameworks, or tools
- Defining data models, schemas, or API contracts
- Picking an architectural pattern (monolith vs. microservice, sync vs. async, etc.)
- Selecting a data source or processing approach (provider, cleaning method, frequency)
- Choosing a statistical or modelling methodology (winsorization vs. trimming, rolling vs. expanding window)
- Defining research protocol or evaluation criteria (backtest design, benchmark selection)
- Making trade-offs with lasting consequences (performance vs. simplicity, buy vs. build, accuracy vs. interpretability)
- Establishing conventions that the team must follow going forward
- Deprecating or replacing an earlier decision

Do NOT record routine choices (variable names, minor refactors, obvious defaults, one-off exploratory experiments).

## Format

File: `docs/decisions/NNN-short-title.md` (zero-padded three-digit sequence)

```markdown
# ADR-NNN: Short Title

**Status:** Proposed | Accepted | Deprecated | Superseded by ADR-XXX
**Date:** YYYY-MM-DD

## Context

What problem or question prompted this decision? Keep it brief — 2-5 sentences.

## Options Considered

1. **Option A** — one-line summary
2. **Option B** — one-line summary
3. **Option C** — one-line summary (if applicable)

## Decision

State the choice and the core reason. 1-3 sentences.

## Consequences

- (+) Positive outcome
- (-) Trade-off or risk accepted
```

## Rules

- **Immutable once Accepted** — never edit the Context/Options/Decision sections of an accepted ADR. To reverse or change a decision, create a new ADR that supersedes it and update the old one's status.
- **Sequential numbering** — check `docs/decisions/` for the next available number before creating.
- **One decision per record** — if a choice bundles multiple independent decisions, split them.
- **Link from code** — when a decision directly affects implementation, add a brief comment pointing to it (e.g., `# See ADR-012`).
- **Keep it short** — a good ADR is under 50 lines. If you need more, the decision may need splitting.

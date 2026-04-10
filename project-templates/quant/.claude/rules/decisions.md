---
paths:
  - "docs/decisions/**/*"
---

# Decision Records — Edit-Time Policy

You are editing a file in `docs/decisions/`. This rule covers policy for
existing ADRs. For **creating new ADRs**, use the `decision` skill which
owns the template and handles numbering, slug generation, and supersede
mechanics.

## Immutability (most important)

Once an ADR has `Status: Accepted`, the following sections are **immutable**:

- Context
- Options Considered
- Decision
- Consequences

**Only the Status field may be edited** on an accepted ADR (to mark it as
Superseded or Deprecated). To change the substance of a decision, create a
**new ADR** that supersedes the old one — do not edit the old ADR's content.

## Status transitions

- `Proposed` → `Accepted` (when finalised)
- `Accepted` → `Superseded by ADR-NNNN` (when replaced — link to successor)
- `Accepted` → `Deprecated` (when no longer valid but not replaced)

## Sequential numbering

ADR filenames use zero-padded 4-digit prefixes: `0001-title.md`, `0002-title.md`, ….
Check existing `docs/decisions/` for the highest number before creating a new
one. The `decision` skill does this automatically.

## One decision per ADR

If a change bundles multiple independent decisions, split them into separate
ADRs.

## Link from code

When a decision directly affects implementation, add a comment near the
relevant code: `# See ADR-NNNN`. This creates a two-way trail from code to
rationale.

## Creating new ADRs

Do not hand-write new ADRs. Use `/decision "short title"` — it handles
numbering, template, and supersede protocol correctly. For supersede:
`/decision "new title" --supersedes NNNN`.

## When to record a decision

Record when:
- Competing libraries / frameworks / tools
- Data models, schemas, API contracts
- Architectural patterns with lasting consequences
- Statistical / methodological choices
- Research protocol / evaluation criteria
- Team conventions going forward
- Deprecating an earlier decision

Do **not** record routine choices (variable names, minor refactors, one-off
experiments, reversible tactical choices).

## Format reference

See `decision` skill (in `qute-essentials` plugin) for the canonical ADR
template. This rule deliberately does not duplicate the template — single
source of truth lives in the skill.

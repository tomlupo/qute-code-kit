---
name: decision
description: Record an architecture, methodology, or design decision as an ADR (Architecture Decision Record). Use when a non-trivial design choice has been finalized in conversation — triggers include phrases like "let's lock in", "we've decided", "the decision is", "let's go with option X", "supersede ADR-NNNN", or when a methodology discussion concludes with a concrete chosen approach, or when the user explicitly asks to record a decision. Creates docs/decisions/NNNN-title.md with auto-numbering and supports superseding existing ADRs by updating their Status field. Do NOT trigger on routine code choices, variable names, minor refactors, one-off experiments, or reversible exploratory choices.
argument-hint: "[--supersedes NNNN] <title>"
---

# /decision

Record an architecture, methodology, or design decision as an ADR (Architecture Decision Record) in `docs/decisions/`.

## When to use

Invoke this skill when:
- A non-trivial design or methodology decision has been finalized in conversation
- The user says phrases like "let's lock in", "we've decided", "the decision is", "let's go with X"
- A methodology discussion concludes with a concrete chosen approach
- An existing ADR needs superseding due to a design change
- The user explicitly requests to record an ADR

Do NOT invoke for:
- Routine code choices, variable names, minor refactors
- One-off experiments or exploration
- Reversible tactical choices with no lasting consequences

## Arguments

- `<title>` — short descriptive title for the decision (natural language or kebab-case)
- `--supersedes NNNN` — (optional) number of an existing ADR this one supersedes

## Behavior

1. **Auto-number the ADR**: scan `docs/decisions/*.md` for the highest existing NNNN, compute next (zero-padded 4-digit, e.g. `0004`). If `docs/decisions/` doesn't exist, create it.

2. **Derive a slug** from the title: lowercase, non-alphanumeric → dashes, collapse repeats, trim to ~50 chars.

3. **Create the new ADR** at `docs/decisions/<NNNN>-<slug>.md` using the **ADR template** below:
   - Populate frontmatter: `Status: Accepted`, `Date: <today ISO>`
   - Include the template sections (Context, Options Considered, Decision, Consequences)
   - If `--supersedes NNNN` was passed, add a `## Supersedes` section pointing to the old ADR

4. **Update the superseded ADR** (if `--supersedes` provided):
   - Find `docs/decisions/<NNNN>-*.md` matching the provided number
   - Update its `## Status` section **only** to: `Superseded by [ADR-<new-NNNN>](<new-filename>) (<today ISO>)`
   - Preserve all other sections — ADRs are **immutable once Accepted**, only the Status field may be edited

5. **Report** to the user:
   - Path of the new ADR file
   - If supersede: confirm the old ADR's Status was updated
   - Prompt the user to fill in Context / Options Considered / Decision / Consequences (the skill creates the scaffold; the user/agent fills the content)
   - Suggest a commit message: `docs: add ADR-NNNN <title>` (`generating-commit-messages` skill handles it on commit)

## ADR template

This skill is the **single source of truth** for ADR format in the qute-essentials kit. Project-level `.claude/rules/decisions.md` covers edit-time policy (immutability, status transitions) but does not duplicate this template.

```markdown
# ADR-NNNN: <Short Title>

**Status:** Accepted
**Date:** YYYY-MM-DD

## Context

What problem or question prompted this decision? 2-5 sentences.

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

## Conventions

- **One decision per ADR** — if a choice bundles multiple independent decisions, create separate ADRs
- **Keep it short** — target under 50 lines; longer decisions may need splitting
- **Immutable once Accepted** — never edit Context/Options/Decision on an accepted ADR; create a new one to reverse (this skill handles supersede via `--supersedes`)
- **Link from code** when the decision directly affects implementation: add a comment `# See ADR-NNNN`
- **Sequential numbering** — always check existing `docs/decisions/` before creating (this skill does it automatically)

## Example

```
/decision "futures decomposition via treatment C" --supersedes 0003
```

Creates `docs/decisions/0004-futures-decomposition-via-treatment-c.md` with `Status: Accepted`, adds a `## Supersedes` section pointing to ADR-0003, and updates `docs/decisions/0003-*.md` Status to `Superseded by ADR-0004`.

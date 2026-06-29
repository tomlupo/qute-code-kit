---
name: grill
description: Adversarially stress-test a plan or PRD ONE question at a time against the project's domain model and documented decisions, surfacing edge cases and contradictions before any code. Use after a PRD/plan exists and before decomposing it — "grill this", "stress-test the plan", "find the edge cases", "poke holes". Adapted from mattpocock/skills `grill-with-docs`. Stage 2 of the engineering workflow (docs/engineering-workflow.md).
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
---

# grill — adversarial stress test (one question at a time)

## Role
Stage 2 of `docs/engineering-workflow.md`. Ruthlessly question the PRD/plan until the
design is sound and unambiguous. This is where edge cases are found — *before* slices.

## Method
- **One question at a time.** Ask, wait for the answer, then ask the next. Never dump
  a list. Walk the design's decision-tree in dependency order.
- **Investigate before asking.** If a question is answerable from the codebase, ADRs,
  or `research/REPRODUCIBILITY.md`, go read it instead of asking the user to speculate.
- **Offer a recommended answer** alongside each question.
- **Quant-specific grilling angles** (this domain): lookahead / PIT-correctness,
  the freshness gate, cohort/z-score grain (L1+ccy vs L2), the compliance wall
  (does any client surface leak Score vs ETF / ML?), thin-group behavior, coverage
  invariant, FX/hedging axis, methodology-doc version bump.
- **Surface code-vs-stated-behavior contradictions immediately.**

## Side effects (sparingly)
- Sharpen fuzzy terms to canonical vocabulary; if a term is load-bearing and recurring,
  add it to the line's glossary / `findings.md`.
- A hard-to-reverse decision with a genuine trade-off → record an ADR
  (`docs/decisions/`), not for routine choices.

## Done when
Every decision-tree branch is explored, dependencies resolved, edge cases validated,
and language is canonical. Output = a stress-tested plan ready for `to-slices`.

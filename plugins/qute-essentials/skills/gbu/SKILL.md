---
name: gbu
description: >-
  Produces a Good / Bad / Ugly (GBU) review: three sections for what works, what
  fails, and what is messy or risky. Use when the user asks for GBU, "good bad
  ugly," blunt review, no-BS feedback, or harsh honesty on code, docs, design,
  decisions, plans, or prior assistant output.
argument-hint: "[what to review — e.g. last answer, path, PR]"
---

# /gbu

## When to apply

The user wants **structured, direct** critique—not a pep talk. Scope is whatever they name (or the immediately preceding assistant output if unspecified).

## Semantics

| Section | Meaning |
|--------|---------|
| **Good** | Correct, clear, reusable, well-scoped—worth keeping. |
| **Bad** | Wrong, missing, misleading, or below bar for the stated goal. Tag severity: *must* / *should* / *could*. |
| **Ugly** | Not necessarily broken today: fragile, opaque, embarrassing, or a foot-gun under scale, time, or production. |

**Ugly ≠ Bad:** Bad = fails or misleads now. Ugly = survives but will cost you later.

## Output format

Always use these headings, in order:

```markdown
## Good

- …

## Bad

- …

## Ugly

- …
```

## Rules

- **Anchor evidence** — Reference paths, symbols, line ranges, or short quotes when reviewing artifacts.
- **Avoid duplicate scoring** — Do not praise the same failure in Good; split *intent* (Good) vs *execution* (Bad) only when both are true.
- **Default depth** — About 3–7 bullets per section unless the user asks for deeper.
- **LLM output as target** — Good: meets constraints, factual, useful structure. Bad: hallucination, wrong API, bloat. Ugly: confident but unverified, risky ops without guardrails.

## Close

End with **one** of: ordered fix list, minimal patch plan, or a single clarifying question.

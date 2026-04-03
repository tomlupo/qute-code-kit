---
name: gbu
description: >-
  Produce a Good / Bad / Ugly structured review of code, docs, design, plans, decisions, or prior
  assistant output. Use when the user asks for GBU, "good bad ugly," blunt review, no-BS feedback,
  or harsh honesty on any artifact.
  Triggers: /gbu, good bad ugly, blunt review, no-BS feedback, be harsh, be brutal, honest review.
argument-hint: "[what to review — e.g. last answer, path/to/file, PR, plan]"
---

# /gbu

Produce a structured three-section critique: what works, what fails now, and what will cost you later.

## Scope

Default to the immediately preceding assistant output if no argument is given. Otherwise review the named artifact — read it with tools before judging.

## Section semantics

| Section | Meaning |
|---------|---------|
| **Good** | Correct, clear, reusable, or well-scoped. Worth keeping as-is. |
| **Bad** | Wrong, missing, misleading, or below bar for the stated goal. Tag each item: `must` / `should` / `could`. |
| **Ugly** | Not broken today — fragile, opaque, embarrassing, or a foot-gun under scale, time, or production stress. |

**Ugly ≠ Bad.** Bad fails or misleads now. Ugly survives but will cost you later.

## Output format

Always use exactly these headings, in order:

```markdown
## Good

- …

## Bad

- …

## Ugly

- …
```

## Rules

- **Read before judging** — use tools to read any file, path, or artifact named in the argument before writing the review.
- **Anchor evidence** — reference file paths, symbol names, line ranges, or short quotes. Vague criticism is not criticism.
- **No duplicate scoring** — don't praise what you also flag as Bad. Split *intent* (Good) vs *execution* (Bad) only when both are genuinely true.
- **Depth** — 3–7 bullets per section unless the user asks for more or less.
- **LLM output as target** — Good: meets constraints, factual, useful structure. Bad: hallucination, wrong API, bloat. Ugly: confident but unverified, risky ops without guardrails.

## Close

End with exactly one of:
- Ordered fix list (if Bad/Ugly items are clear and independently actionable)
- Minimal patch plan (if changes are interconnected)
- One clarifying question (if the most important issue is ambiguous)

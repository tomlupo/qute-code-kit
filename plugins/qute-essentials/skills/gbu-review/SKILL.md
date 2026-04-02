---
name: gbu-review
description: >-
  Delivers a Good / Bad / Ugly (GBU) review of code, design, documents, model
  outputs, or decisions. Three buckets—what worked, what failed, what is
  messy or risky. Use when the user asks for a GBU review, "good bad ugly,"
  or blunt structured feedback without sugar-coating.
---

# GBU review (Good / Bad / Ugly)

## Purpose

Give **honest, scannable** feedback in three fixed sections. "Ugly" is not "worst ever"—it means **messy, fragile, embarrassing, or high-risk** even if it "works."

## Output template

Use this structure every time (markdown headings):

```markdown
## Good

- What is correct, clear, well-scoped, or reusable.
- What you would keep unchanged.

## Bad

- What is wrong, missing, misleading, or below standard.
- What should be fixed for the stated goal (with severity: must / should / could).

## Ugly

- Hacks, unclear ownership, hidden assumptions, foot-guns.
- Debt that will bite later; things that look fine until production or scale.
- **Optional**: one line each for *why it is ugly* and *what would de-uglify it*.
```

## Rules

1. **Be specific** — Tie bullets to files, functions, lines, or quoted snippets when reviewing artifacts.
2. **No overlap spam** — If something is "Bad" (broken), do not also praise it in "Good" unless you separate **intent** (good) from **execution** (bad).
3. **Ugly ≠ Bad** — Bad = fails or misleads now. Ugly = survives but is painful, opaque, or dangerous.
4. **Order** — Good → Bad → Ugly keeps the read constructive; do not bury the useful parts.
5. **Length** — Default to **3–7 bullets per section**. Expand only if the user asks for depth.

## When the target is LLM output

- **Good**: Requirements met, structure, correct facts, useful next steps.
- **Bad**: Hallucinations, wrong API, ignored constraints, verbosity without value.
- **Ugly**: Confident tone on weak claims, missing verification, advice that could cause data loss or security issues.

## After the GBU

End with **one** of: prioritized fix list, minimal patch plan, or a single clarifying question—whichever unblocks the user fastest.

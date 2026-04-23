---
name: skill-assessment
description: |
  Audit and assess skills against best practices from Anthropic's skill engineering guide.
  Use when the user says "assess skills", "audit skills", "skill review", "skill quality",
  "rate my skills", or wants to evaluate skill coverage, quality, and structure.
  Analyzes individual skills or the entire skill universe.
argument-hint: "[skill-name | all]"
allowed-tools: Read, Glob, Grep, Bash, Agent
user-invocable: true
---

# Skill Assessment Tool

Evaluate skills against Anthropic's best practices for skill engineering. Produces a structured assessment with category classification, quality scores, gap analysis, and actionable recommendations.

## Quick Start

1. If `$ARGUMENTS` is a specific skill name, assess only that skill
2. If `$ARGUMENTS` is "all" or empty, assess the entire skill universe

## Assessment Workflow

### Phase 1: Discovery

Scan the skill directories to build an inventory:

```bash
ls -d .claude/skills/*/
```

For each skill, read:
- `SKILL.md` (frontmatter + content)
- Directory listing (scripts/, references/, assets/, data files)
- Any supporting files referenced in the SKILL.md

### Phase 2: Classify

Classify each skill into one or more of the **9 skill categories** defined in `references/framework.md`. A well-focused skill fits cleanly into ONE category. Flag skills that straddle multiple categories as potentially needing refactoring.

### Phase 3: Score

Rate each skill on the **8 quality dimensions** from `references/framework.md`, using the scoring rubric (0-2 per dimension, max 16). Read the framework file for full criteria.

### Phase 4: Gap Analysis

Compare the skill universe against all 9 categories. Identify:
- **Missing categories** — no skills at all in that category
- **Thin categories** — only 1 skill, could benefit from more
- **Over-represented** — many similar skills that could be consolidated

### Phase 5: Report

Produce a structured report with these sections:

#### Per-Skill Assessment Table

| Skill | Category | Score | Top Strength | Top Issue | Priority Fix |
|-------|----------|-------|--------------|-----------|--------------|

#### Category Coverage Matrix

Show which of the 9 categories are covered, thin, or missing.

#### Top 5 Recommendations

Ranked by impact. Each recommendation should include:
- What to do
- Which skill(s) it applies to
- Expected improvement
- Effort estimate (quick / medium / significant)

#### Skill Improvement Briefs

For any skill scoring below 10/16, write a 3-5 line improvement brief with specific, actionable changes.

## Scoring Interpretation

| Range | Label | Meaning |
|-------|-------|---------|
| 14-16 | Excellent | Exemplary skill, share widely |
| 10-13 | Good | Solid skill, minor improvements possible |
| 6-9 | Needs Work | Functional but missing key best practices |
| 0-5 | Weak | Needs significant rework |

## Important Guidelines

- **Don't state the obvious**: Focus assessment on what Claude wouldn't know by default. A skill that just restates common knowledge should be flagged.
- **Value gotchas highly**: The presence of a well-maintained gotchas/pitfalls section is one of the strongest quality signals.
- **Reward progressive disclosure**: Skills that use folder structure (references/, scripts/, assets/) to layer information score higher than monolithic SKILL.md files.
- **Check descriptions for model-targeting**: The description field should tell the MODEL when to trigger, not just describe what the skill does to humans.
- **Assess composition potential**: Note where skills could reference or depend on each other more effectively.

---
description: "Prepare a flow-aware handoff document for continuing work in a new session"
---

# /flow:handoff

Prepare a handoff document that captures flow state alongside session context. This extends the standard handoff with plan-aware information.

## Behavior

When the user invokes `/flow:handoff [goal]`:

1. **Gather environment state** automatically:
   - Run `git diff --name-only` and `git status --short` to detect modified/staged files
   - Note current branch, working directory
   - Check for running background tasks or services

2. **Gather flow state**:
   - Read `.flow-state` for active plan path
   - If active plan exists, extract: goal, current phase, phase progress, recent decisions
   - Read `TASKS.md` for Now section items
   - Count pending ideas in `docs/ideas/`

3. **Analyze current conversation context**:
   - What was accomplished in this session
   - Important decisions made and rationale
   - Blockers, failures, or issues requiring user action
   - Unanswered questions or unresolved ambiguity

4. **Generate a handoff document** with these sections:
   - **Goal**: What the next session should accomplish (from arg, or inferred)
   - **Flow State**: Active plan, phase progress, TASKS.md snapshot
   - **Context Summary**: Brief summary of session work
   - **Key Decisions**: Choices made and why
   - **Environment State**: Branch, directory, modified files
   - **Files to Load**: Key files the next session needs
   - **Blockers**: Things requiring user action
   - **Next Steps**: Ordered, specific, actionable items
   - **Notes**: Caveats, gotchas

5. **Save the handoff** to `.claude/handoffs/<YYYY-MM-DD>-<slug>.md`

6. **Display the handoff** for the user to review

## Arguments

- `[goal]` — (Optional) What the next session should accomplish. If omitted, infer from conversation + active plan.

## Output Format

```markdown
# Handoff: <goal-slug>

**Created**: <ISO timestamp>
**Goal**: <goal — stated or inferred>

## Flow State

- **Active plan**: <path or "none">
- **Phase**: <current>/<total> (<phase name>)
- **TASKS.md Now**: <list of current items>
- **Pending ideas**: <count>

## Context Summary

<2-5 sentences summarizing what happened this session>

## Key Decisions

- **<Decision>**: <rationale>

## Environment State

- **Directory**: <working directory>
- **Branch**: <current git branch>
- **Modified files**: <list from git diff>

## Files to Load

- `path/to/file` — <one-line reason>

## Blockers

<items requiring user action, or "None — ready to continue.">

## Next Steps

1. <Specific actionable step>
2. <Specific actionable step>

## Notes

- <Caveats or context easy to forget>
```

## Conventions

- Keep the whole document under 100 lines
- Imperative voice in Next Steps
- Blockers = user action required; Next Steps = Claude action
- Always include flow state even if "No active plan"

---
name: handoff
description: Prepare a handoff document to continue work in a new session. Captures context, decisions, blockers, and environment state for seamless session transitions.
argument-hint: "[goal]"
---

# /handoff

Prepare a handoff document to continue work in a new session. Captures what matters for resuming — context, decisions, blockers, and environment state.

## Behavior

When the user invokes `/handoff [goal]`:

1. **Gather environment state** automatically:
   - Run `git diff --name-only` and `git status --short` to detect modified/staged files
   - Note current branch, working directory
   - Check for running background tasks or services relevant to the work

2. **Analyze current conversation context**:
   - What was accomplished in this session
   - Important decisions made and their rationale
   - Any blockers, failures, or issues requiring user action
   - Unanswered questions or unresolved ambiguity

3. **Generate a handoff document** with these sections:
   - **Goal**: What the next session should accomplish (from arg, or inferred from conversation)
   - **Context Summary**: Brief summary of session work (NOT a transcript)
   - **Key Decisions**: Choices made and why
   - **Environment State**: Branch, directory, modified files, running services
   - **Modified Files**: Auto-detected from git + conversation context, with why each matters
   - **Blockers**: Things that must be resolved before continuing (separate from notes — these require action)
   - **Next Steps**: Ordered, specific, actionable items
   - **Notes**: Caveats, gotchas, things to watch out for

4. **Save the handoff** to `.claude/handoffs/<YYYY-MM-DD>-<slug>.md`

5. **Display the handoff** for the user to review

## Arguments

- `[goal]` - (Optional) What the next session should accomplish. If omitted, infer from conversation context.

## Output Format

```markdown
# Handoff: <goal-slug>

**Created**: <ISO timestamp>
**Goal**: <goal — stated or inferred>
**Previous**: <link to prior handoff if one exists, else "none">

## Context Summary

<2-5 sentences summarizing what happened this session>

## Key Decisions

- **<Decision>**: <rationale>
- **<Decision>**: <rationale>

## Environment State

- **Directory**: <working directory>
- **Branch**: <current git branch, or "not a git repo">
- **Modified files**: <list from git diff, or "none">
- **Running services**: <any relevant background processes>

## Files to Load

These files provide necessary context for the next session:
- `path/to/file` — <one-line reason>
- `path/to/file` — <one-line reason>

## Blockers

Items that require user action before work can continue:
- <blocker and what's needed to resolve it>

(If no blockers, write "None — ready to continue.")

## Next Steps

1. <Specific actionable step>
2. <Specific actionable step>
3. <Specific actionable step>

## Notes

- <Caveats, gotchas, or context that's easy to forget>
```

## Conventions

- Keep the whole document under 80 lines — concise beats comprehensive
- Use imperative voice in Next Steps ("Install caddy", not "Caddy should be installed")
- Blockers are things the USER must do; Next Steps are things CLAUDE will do
- If the session had no meaningful progress, say so honestly — don't pad

## Resuming from a Handoff

In a new session:

```
Load the handoff from .claude/handoffs/<filename>.md and continue
```

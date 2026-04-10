---
name: handoff
description: Prepare a handoff document to continue work in a new session. Captures context, decisions, blockers, and environment state for seamless session transitions.
argument-hint: "[--push] [goal]"
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

6. **If `--push` flag was passed**, persist the handoff to git:
   - Stage only the handoff file: `git add .claude/handoffs/<file>.md` (do NOT stage other WIP)
   - Commit: `git commit -m "handoff: <goal-slug>"`
   - Push current branch: `git push -u origin HEAD`
   - If push fails due to network, retry with exponential backoff (2s, 4s, 8s, 16s)
   - Report the resulting commit SHA to the user — this is the anchor for drift detection on resume
   - The handoff commits onto the CURRENT branch (alongside the WIP it describes), not a dedicated `handoff/*` branch

## Arguments

- `[goal]` - (Optional) What the next session should accomplish. If omitted, infer from conversation context.
- `--push` - (Optional flag) After saving, commit the handoff file to the current branch and push. Only the handoff doc is committed — any other WIP stays unstaged.

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

When resuming, **check for drift** — files listed in the handoff may have changed since it was written, invalidating the planned approach:

1. **Read the handoff doc** and extract its "Files to Load", "Modified files", and "Next Steps" sections.

2. **Find the commit that introduced the handoff** (only if it was pushed — i.e. the file is tracked in git):
   ```bash
   HANDOFF_SHA=$(git log --diff-filter=A --format=%H -- .claude/handoffs/<file>.md | tail -1)
   ```
   `--diff-filter=A` narrows to the commit that *added* the file, so later edits to the doc don't shift the anchor. `tail -1` picks the oldest match if there are multiple.

3. **List files changed since the handoff**:
   ```bash
   git diff --name-only "$HANDOFF_SHA"..HEAD
   ```
   Also include unstaged changes: `git diff --name-only HEAD`.

4. **Cross-reference** the changed files against the handoff's "Files to Load" and "Modified files" lists. For each overlap:
   - Show a short diff: `git diff "$HANDOFF_SHA"..HEAD -- <file>`
   - Flag the affected "Next Steps" items — their assumptions may be stale.

5. **Tell the user before proceeding**: "N files referenced by this handoff have changed since it was written: [list]. Review before continuing?" If nothing drifted, say "No drift — handoff is current" and proceed.

6. If the handoff was never pushed (no git history for the file), skip drift detection and proceed with Next Steps as written.

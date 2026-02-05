# /strategic-compact:handoff

Prepare a handoff document to continue work in a new session. Unlike `/compact` which summarizes context in-place, handoff explicitly captures what matters for a specific next task.

## Behavior

When the user invokes `/strategic-compact:handoff <goal>`:

1. **Analyze current context** to understand:
   - What was accomplished in this session
   - What files were modified or are relevant
   - Important decisions made
   - Any blockers or issues encountered

2. **Generate a handoff document** containing:
   - **Goal**: The user's specified objective for the new session
   - **Context Summary**: Brief summary of what was done (not a full transcript)
   - **Key Decisions**: Important choices made and their rationale
   - **Relevant Files**: Files the new session should load for context
   - **Next Steps**: Specific actionable items to continue the work
   - **Notes**: Any caveats, blockers, or things to watch out for

3. **Save the handoff** to `.claude/handoffs/<timestamp>-<slug>.md`

4. **Display the handoff** for the user to review and optionally edit

## Arguments

- `<goal>` - (Required) Description of what the next session should accomplish

## Output Format

```markdown
# Handoff: <goal-slug>

**Created**: <timestamp>
**Goal**: <user's goal>

## Context Summary

<Brief summary of current session's work>

## Key Decisions

- <Decision 1 and rationale>
- <Decision 2 and rationale>

## Relevant Files

Load these files to continue:
- `path/to/file1.ts` — <why it's relevant>
- `path/to/file2.ts` — <why it's relevant>

## Next Steps

1. <Specific actionable step>
2. <Specific actionable step>
3. <Specific actionable step>

## Notes

- <Any caveats or things to watch out for>
```

## Examples

```
/strategic-compact:handoff implement error handling for the API endpoints

Handoff saved to: .claude/handoffs/2026-02-05-api-error-handling.md

# Handoff: api-error-handling

**Created**: 2026-02-05T14:30:00Z
**Goal**: Implement error handling for the API endpoints

## Context Summary

Added new user authentication endpoints (login, register, refresh).
Basic CRUD operations are working but lack proper error responses.

## Key Decisions

- Using Zod for request validation (matches existing patterns)
- Returning RFC 7807 problem details format for errors
- Auth errors use 401, validation errors use 422

## Relevant Files

Load these files to continue:
- `src/api/auth.ts` — New endpoints needing error handling
- `src/middleware/error-handler.ts` — Central error handler to extend
- `src/types/errors.ts` — Error type definitions
- `src/api/users.ts` — Reference for existing error patterns

## Next Steps

1. Add try-catch blocks to auth endpoint handlers
2. Create specific error classes (ValidationError, AuthError)
3. Update error-handler middleware to format RFC 7807 responses
4. Add tests for error scenarios

## Notes

- The refresh token endpoint has a race condition to address
- Consider rate limiting on login endpoint (not implemented yet)
```

```
/strategic-compact:handoff fix the remaining test failures

Handoff saved to: .claude/handoffs/2026-02-05-fix-test-failures.md
...
```

## Usage Tips

- Use handoff when switching focus areas or ending a long session
- More specific goals produce better handoff documents
- Review the handoff before starting a new session - edit if needed
- Combine with `/session-persistence:load` to restore context

## Starting a New Session with a Handoff

In a new session, tell Claude:

```
Load the handoff from .claude/handoffs/2026-02-05-api-error-handling.md and continue the work
```

Or use with session-persistence if installed:

```
/session-persistence:load
```

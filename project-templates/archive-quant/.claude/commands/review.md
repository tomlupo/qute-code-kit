# Code Review

Review the following code changes: $ARGUMENTS

## Review Process

1. **Read the changes first** - Understand what was modified before providing feedback
2. **Check for bugs** - Logic errors, edge cases, null handling
3. **Check for security** - Input validation, injection risks, authentication issues
4. **Check performance** - Unnecessary loops, N+1 queries, memory leaks
5. **Check conventions** - Adherence to project style (see CLAUDE.md, .ai/code-quality.md)
6. **Check tests** - Are changes adequately tested?

## Output Format

Provide feedback in this structure:

### Critical Issues
<!-- Must fix before merge -->

### Suggestions
<!-- Recommended improvements -->

### Positive Notes
<!-- What was done well -->

If no specific files are mentioned, review the current staged changes (`git diff --staged`).

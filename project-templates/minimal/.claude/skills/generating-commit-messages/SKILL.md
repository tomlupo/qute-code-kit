---
name: generating-commit-messages
description: MANDATORY skill for ALL commits. Must be used EVERY TIME before creating any git commit. No exceptions.
---

# Generating Commit Messages

**Use this skill before every `git commit`.**

## Process

1. Run `git diff --staged` to review all staged changes
2. Analyze what changed and why
3. Write a commit message following the format below

## Format

**Summary line** (under 50 characters):
- Present tense imperative mood ("Add feature", not "Added feature")
- Start with action verb: Add, Update, Fix, Remove, Refactor, etc.
- Be specific about what component is affected

**Detailed description** (blank line after summary):
- What was changed
- Why it was changed
- Affected components/files
- Important context

## Example

```
Refactor authentication for improved security

- Replace deprecated JWT library with jose
- Add input validation for user credentials
- Update auth middleware to handle malformed requests
- Fix memory leak in session management

Resolves production crashes from malformed auth tokens.
```

## Rules

- **Never** include "Generated with Claude Code" or "Co-Authored-By: Claude"
- **Never** use generic messages like "Update files" or "Fix issues"
- Include the "why" not just the "what"

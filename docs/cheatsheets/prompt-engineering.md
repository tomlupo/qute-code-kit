# Prompt Engineering Guide

Best practices for writing effective prompts when working with Claude Code and AI assistants.

## Core Principle

Specificity beats vagueness. Detailed instructions with clear constraints produce better first-attempt results.

## Specificity Examples

| Vague | Specific |
|-------|----------|
| "Add tests for foo.py" | "Write a test case for foo.py covering the edge case where user is logged out. Avoid mocks." |
| "Fix the bug" | "Fix the null pointer exception in user_service.py:45 when email is empty" |
| "Make it faster" | "Optimize the database query in get_orders() - it's taking 3s, should be under 500ms" |
| "Clean up this code" | "Extract the validation logic in process_order() into a separate validate_order() function" |

## Thinking Modes

Use progressive computation budgets for complex problems:

| Command | When to Use |
|---------|-------------|
| `think` | Default reasoning for straightforward tasks |
| `think hard` | Complex problems requiring careful analysis |
| `think harder` | Multi-step problems with many considerations |
| `ultrathink` | Architectural decisions, debugging complex issues |

**Example**:
```
think hard about the best way to implement caching for our API.
Consider Redis vs in-memory, invalidation strategies, and our current architecture.
```

## Planning Before Coding

Request exploration and planning phases before implementation:

```
Before writing any code:
1. Read the relevant files to understand current implementation
2. List the files you'll need to modify
3. Explain your approach
4. Wait for my approval before making changes
```

## Visual References

Provide visual context when relevant:
- Paste screenshots of UIs to replicate
- Share design mocks for new features
- Include error screenshots for debugging
- Drag images directly into the conversation

Claude typically improves substantially after 2-3 visual iteration cycles.

## Context Management

### Clear Between Tasks
Use `/clear` between unrelated tasks to reset context and maintain focus.

### Focused Requests
Instead of one large request, break into focused steps:
```
# Instead of:
"Build a complete user auth system"

# Do:
"Let's build user auth. First, show me the current auth-related files in the codebase."
# ... review
"Now create the user model with email/password fields"
# ... review
"Add the login endpoint"
```

### Provide Constraints
State what you don't want:
```
Implement the feature with these constraints:
- No new dependencies
- Must work with Python 3.9+
- Keep backward compatibility with existing API
- Don't modify the database schema
```

## Multi-Claude Workflows

For complex work, run multiple Claude instances in parallel:

| Instance 1 | Instance 2 |
|------------|------------|
| Write implementation | Review code |
| Feature A (worktree 1) | Feature B (worktree 2) |
| Backend changes | Frontend changes |

Separation often yields better results than single-instance handling.

## Course Correction

- **Escape**: Interrupt any phase while preserving context
- **Double Escape**: Edit previous prompts to explore alternatives
- **Request plan**: Ask for approach before coding to verify direction

## Effective Patterns

### Explore-Plan-Code-Commit
```
1. "Read the files related to [feature] without making changes"
2. "Create a plan for implementing [change]"
3. "Implement the plan"
4. "Create a commit with these changes"
```

### Test-Driven Development
```
1. "Write tests for [feature] based on these expected behaviors: [list]"
2. "Run the tests - they should fail"
3. "Commit the tests"
4. "Implement the code to make tests pass"
```

### Codebase Q&A
Ask questions like you would during pair programming:
- "How does logging work in this codebase?"
- "Where are the API endpoints defined?"
- "Explain what this function does"
- "What's the Python equivalent of [code in another language]?"

## Headless/Automation

For CI/CD and scripts:
```bash
# Non-interactive prompt
claude -p "Run the test suite and fix any failures"

# Streaming JSON output for pipelines
claude --output-format stream-json -p "Generate changelog"
```

## Common Mistakes

### Too Vague
```
# Bad
"Improve the code"

# Good
"Reduce the complexity of calculate_totals() by extracting the discount logic"
```

### Too Much at Once
```
# Bad
"Build user auth, add OAuth, implement password reset, add 2FA, and write tests"

# Good
"Let's start with basic email/password auth. We'll add other features after."
```

### No Success Criteria
```
# Bad
"Make the tests pass"

# Good
"Make the tests pass. Currently 3/10 are failing. Show me the output after fixes."
```

### Missing Context
```
# Bad
"Fix the error"

# Good
"Fix this error I'm seeing:
[paste full error message]
It happens when I run `npm test` after the latest changes to user_service.js"
```

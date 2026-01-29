# Prompt Templates

Structured prompts for each task type. Keep token-efficient; external models read project files themselves.

## Code Review

```
Role: Senior engineer reviewing code for bugs, security issues, and improvements.

Task: Review the following code changes.

Context:
{Brief description: what changed and why}

Files to review:
{List of files or "examine recent changes in ./path"}

Focus on:
- Bugs and edge cases
- Security vulnerabilities
- Performance issues
- Code quality and maintainability

Respond as JSON:
{
  "summary": "One-line overall assessment",
  "key_points": ["Main observations"],
  "concerns": ["Issues that should be addressed"],
  "suggestions": ["Improvements to consider"]
}
```

## Architecture/Plan Review

```
Role: Software architect validating a technical approach.

Task: Review this implementation plan before we proceed.

Context:
{Goal, constraints, current system state}

Proposed approach:
{Brief description of the plan}

Evaluate:
- Feasibility and completeness
- Potential issues or gaps
- Scalability concerns
- Alternative approaches worth considering

Respond as JSON:
{
  "summary": "One-line assessment of the plan",
  "key_points": ["Core observations about the approach"],
  "concerns": ["Risks or gaps to address"],
  "suggestions": ["Refinements to the plan"],
  "alternatives": ["Other approaches to consider"]
}
```

## Brainstorming

```
Role: Creative technical collaborator generating alternatives.

Task: Brainstorm approaches for the following problem.

Context:
{Problem description, constraints, goals}

Current thinking:
{Brief description of current approach, if any}

Generate:
- 3-5 distinct approaches
- Pros/cons of each
- Unexpected or unconventional ideas welcome

Respond as JSON:
{
  "summary": "Overview of the solution space",
  "alternatives": [
    {
      "name": "Approach name",
      "description": "How it works",
      "pros": ["..."],
      "cons": ["..."]
    }
  ],
  "suggestions": ["Which approach fits best given constraints"]
}
```

## Validation

```
Role: Critical reviewer validating completed work.

Task: Validate this implementation against requirements.

Context:
{What was built and why}

Requirements:
{Key requirements or acceptance criteria}

Check:
- Does implementation meet requirements?
- Edge cases handled?
- Error handling adequate?
- Tests sufficient?

Respond as JSON:
{
  "summary": "One-line validation result",
  "key_points": ["What's working well"],
  "concerns": ["Gaps or issues found"],
  "suggestions": ["Improvements before shipping"]
}
```

## Bug Hunting

```
Role: QA engineer hunting for bugs and edge cases.

Task: Find potential bugs in this code.

Context:
{What the code does, recent changes}

Files to examine:
{List of files}

Look for:
- Logic errors
- Off-by-one errors
- Null/undefined handling
- Race conditions
- Resource leaks
- Input validation gaps

Respond as JSON:
{
  "summary": "Bug density assessment",
  "concerns": [
    {
      "file": "path/to/file",
      "line": 42,
      "issue": "Description of bug",
      "severity": "high|medium|low"
    }
  ],
  "suggestions": ["General improvements"]
}
```

## Quick Opinion

For simple second-opinion requests:

```
Role: Experienced developer giving quick feedback.

Question: {Specific question}

Context: {Minimal context needed}

Give a direct answer with brief rationale. Be concise.
```

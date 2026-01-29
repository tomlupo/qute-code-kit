# General Rules

## Before Starting Any Task

**ALWAYS follow this sequence:**

1. **Check project structure** - Understand where files belong (see work-organization.md)
2. **Check current work status** - Know what's currently in progress:
   - Check task tracking files (e.g., `IN_PROGRESS.md`, `BACKLOG.md` if they exist)
   - Review recent git commits to understand recent changes
   - Check current uncommitted changes in files to see what's being worked on
3. **Review relevant documentation** - Read project-specific guides, methodology docs, knowledge base, and agent-specific instructions
4. **Confirm file paths** - State full path and verify it matches project structure before creating files
5. **When uncertain** - Ask before proceeding rather than making assumptions

## Communication Style

- Be concise and direct
- Avoid unnecessary pleasantries
- Focus on technical accuracy
- Provide actionable recommendations
- Ask clarifying questions when ambiguous or facing architectural decisions with multiple valid approaches        
- Prefer asking over guessing for irreversible actions

## File Operations

- Always check if directories exist before creating files in them
- Create necessary parent directories automatically
- Preserve existing content when editing
- Follow existing code style and conventions in the project

## Problem Solving

When the user highlights a problem (e.g., types "analyze problem", "fix error", "debug this", "this is broken", or shares unexpected output):

1. Identify 5–7 plausible root causes, including edge cases, configuration issues, data problems, and logic errors.
2. Narrow down to the 1–2 most likely causes using recent context and prior steps.
3. Insert diagnostics, print statements, or logs to validate assumptions before proposing or implementing a fix.

## Proactive Use of Capabilities

- Proactively use all available capabilities such as MCP servers, skills, and other tools
- When working with technologies/libraries/frameworks, automatically fetch latest documentation via MCP tools (e.g., Context7) when relevant
- Detect technology mentions in prompts, `docs/prd.md`, `README.md`, or `pyproject.toml` and fetch relevant docs
- Use available skills and tools to enhance responses rather than relying solely on training data
- Avoid repeating documentation fetches for the same technology during the same session unless specifically requested

### Claude Code Specific

When using Claude Code, leverage specialized subagents:
- `Explore` agent for codebase understanding questions
- `code-reviewer` agent after significant code changes
- `prd-writer` for product requirements documents
- Let Claude Code select appropriate agents automatically when uncertain
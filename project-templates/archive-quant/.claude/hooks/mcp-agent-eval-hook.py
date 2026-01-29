#!/usr/bin/env python3
"""
UserPromptSubmit hook that encourages proactive MCP and agent usage.

This hook reminds Claude to consider available MCP tools and specialized agents
before diving into implementation, preventing missed opportunities for better context.
"""

import sys

HOOK_OUTPUT = """
REMINDER: PROACTIVE TOOL & AGENT EVALUATION

Before proceeding, quickly consider:

## MCP Tools Available
- Context7 (mcp__context7__*): Library/framework documentation lookup
  → Use when: Working with any library, framework, or API
  → Trigger: User mentions tech stack, sees imports, reads pyproject.toml

- IDE tools (mcp__ide__*): Diagnostics, code execution
  → Use when: Need IDE integration, running Jupyter code

## Specialized Agents (Task tool)
- Explore: Codebase understanding, finding patterns, answering "how does X work?"
- code-reviewer: After significant code changes
- prd-writer: Product requirements documents
- security-auditor: Security review of code
- claude-code-guide: Questions about Claude Code itself

## Quick Check
Ask yourself:
1. Am I working with a library/framework? → Consider Context7 for docs
2. Is this an exploration question? → Consider Explore agent
3. Did I just write significant code? → Consider code-reviewer agent

Proceed with your response, using these tools proactively where relevant.
"""

if __name__ == "__main__":
    # Ensure UTF-8 output for cross-platform compatibility
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print(HOOK_OUTPUT)
    sys.exit(0)

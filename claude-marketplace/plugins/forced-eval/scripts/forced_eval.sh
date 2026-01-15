#!/bin/sh
# Claude Code Forced Eval Hook
# Forces explicit evaluation of Skills, MCP Tools, and Agents before implementation.
#
# Based on Scott Spence's research showing forced evaluation achieves 84% activation
# vs ~50% baseline: https://scottspence.com/posts/how-to-make-claude-code-skills-activate-reliably

cat << 'EOF'

╔══════════════════════════════════════════════════════════════════════════════╗
║  MANDATORY: TOOL ACTIVATION SEQUENCE                                         ║
╚══════════════════════════════════════════════════════════════════════════════╝

## Step 1: EVALUATE

### Skills (Skill tool)
For each skill: [name] → YES/NO → [reason]
  (See available skills in Skill tool description)
IF YES → Use `Skill(skill-name)` tool

### MCP Tools (mcp__* functions)
For each relevant tool: [name] → YES/NO → [reason]
  Common MCP tools:
    - Context7 (mcp__*context7*): Library/framework documentation
    - IDE tools (mcp__ide__*): Diagnostics, execution
IF YES → Call the MCP tool function

### Agents (Task tool)
For each relevant agent: [name] → YES/NO → [reason]
  Common agents (Task tool):
    - Explore: Codebase understanding, "how does X work?"
    - code-reviewer: After significant code changes
    - Plan: Design implementation approach
IF YES → Use `Task(subagent_type=agent-name)`

## Step 2: ACTIVATE
For EACH item marked YES above → Call the corresponding tool NOW

## Step 3: IMPLEMENT
Only after Step 2 is complete → Proceed with implementation

╔══════════════════════════════════════════════════════════════════════════════╗
║  ⚠ CRITICAL: Evaluation WITHOUT activation is WORTHLESS.                     ║
║  Do NOT skip to implementation. Call tools marked YES first.                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
EOF

# AGENTS.md

## Agent Instructions

This repository uses Claude Code–style rules and skills as the primary source of agent behavior.

All coding agents (Codex, Claude, etc.) should follow the instructions
defined in the following files:

- `CLAUDE.md`
- `.claude/skills/*`
- `.claude/rules/*`

Treat those files as the canonical specification for:

- coding style
- architecture conventions
- workflows
- testing and validation

If instructions conflict, prefer the Claude rules.

## How to work in this repo

1. Read `CLAUDE.md` first.
2. Load relevant skills from `.claude/skills/`.
3. Apply rules from `.claude/rules/`.
4. Then explore the repository and implement changes.

Do not invent new conventions if they are defined in the Claude rules.
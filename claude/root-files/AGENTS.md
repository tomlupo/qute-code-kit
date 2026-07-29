# AGENTS.md

## Agent Instructions

This repository uses Claude Code–style rules and skills as the primary source of agent behavior.

All coding agents (Codex, Claude, etc.) should follow the instructions
defined in the following files:

- `CLAUDE.md` — the behavioral contract; the canonical, always-loaded source
- `.claude/skills/*`
- `.claude/rules/*` — `paths:`-scoped rules only, when the repo carries any; an
  unscoped rule file belongs in `CLAUDE.md` instead

Treat those files as the canonical specification for:

- coding style
- architecture conventions
- workflows
- testing and validation

If instructions conflict, prefer `CLAUDE.md`.

## How to work in this repo

1. Read `CLAUDE.md` first — it carries the contract.
2. Load relevant skills from `.claude/skills/`.
3. Apply any `paths:`-scoped rules in `.claude/rules/` whose globs match the
   files you are touching. Often there are none; that is normal.
4. Then explore the repository and implement changes.

Do not invent new conventions if they are already defined in `CLAUDE.md`.
# AGENTS.md

Universal guidance for AI coding assistants (Claude Code, Codex, Cursor, Gemini, OpenCode, Ampcode).

This file provides a single source of truth for all AI tools working with this codebase.
Tool-specific overrides: see `CLAUDE.md` (Claude Code) or `GEMINI.md` (Gemini).

## Project Overview

[What the project does. 1-3 sentences.]

## Key Paths

| Purpose | Location |
|---------|----------|
| Source code | `src/` |
| Tests | `tests/` |
| Documentation | `docs/` |
| Configuration | `config/` |

## Key Commands

| Task | Command |
|------|---------|
| Run tests | `...` |
| Build | `...` |
| Lint | `...` |
| Format | `...` |

## Coding Conventions

- Follow existing patterns in the codebase
- Write tests for new functionality
- Keep functions focused and small
- Use meaningful names for variables and functions

## File Organization

- New features go in `src/`
- Tests mirror source structure in `tests/`
- Temporary/experimental work goes in `scratch/`
- Configuration files go in `config/`

## Domain Knowledge

[Project-specific conventions, data quirks, gotchas that an AI assistant would get wrong without being told.]

## Skills and Commands

Skills in `.agents/skills/` (or `.claude/skills/`) provide domain-specific knowledge.
Commands in `.agents/commands/` (or `.claude/commands/`) provide reusable workflows.

## References

- See `CLAUDE.md` for Claude Code-specific overrides
- See `.claude/rules/` for detailed coding rules (auto-loaded by Claude Code)

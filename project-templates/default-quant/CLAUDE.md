# @CLAUDE.md

This file provides **project-specific** guidance for AI coding assistants working in this repository.

**⚠️ IMPORTANT:** This file contains project-specific rules and guidelines that override or supplement the generic guidance in `AGENTS.md`.

See: @AGENTS.md

## Project-Specific Overrides

<!-- Add rules unique to this project that aren't covered by AGENTS.md -->

## Common Commands

<!-- Document frequently used bash commands for this project -->
<!-- Examples:
```bash
# Run tests
uv run pytest

# Start development server
uv run python -m src.main

# Format code
uv run black src/ && uv run isort src/
```
-->

## Code Style

<!-- Project-specific style preferences beyond what's in .ai/python-rules.md -->
<!-- Examples:
- Use dataclasses over dicts for structured data
- Prefer composition over inheritance
- Max function length: 50 lines
-->

## Testing

<!-- How to run tests and what testing patterns to follow -->
<!-- Examples:
- Run `uv run pytest` before committing
- Each module should have corresponding test file in tests/
- Use pytest fixtures for shared test setup
-->

## Environment Setup

<!-- Environment variables, dependencies, or setup steps -->
<!-- Examples:
- Copy `.env.example` to `.env` and fill in values
- Requires Python 3.11+
- Run `uv sync` to install dependencies
-->

## Troubleshooting
<!-- How to troubleshoot issues and what to check -->
<!-- Examples:
- Check logs in /logs/
- Run `uv run pytest` to check for test failures
- Check .env file for missing variables
- Check .gitignore for ignored files